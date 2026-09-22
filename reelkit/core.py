"""Thin, testable wrappers around ffmpeg for short-form video finishing."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

# TikTok / Reels / Shorts delivery target
TARGET_W, TARGET_H = 1080, 1920
TARGET_LUFS = -14.0
TARGET_TP = -1.5
TARGET_LRA = 11.0
# MP4 file-type atoms every muxer writes; not identifying metadata
BRAND_TAGS = {"major_brand", "minor_version", "compatible_brands"}


class FFmpegError(RuntimeError):
    pass


def ffmpeg_bin() -> str:
    path = shutil.which("ffmpeg")
    if not path:
        raise FFmpegError("ffmpeg not found on PATH")
    return path


DRY_RUN = False


def run(args: list[str]) -> subprocess.CompletedProcess:
    if DRY_RUN:
        print(" ".join(f'"{a}"' if " " in a else a for a in args))
        return subprocess.CompletedProcess(args, 0, "", "")
    proc = subprocess.run(args, capture_output=True, text=True)
    if proc.returncode != 0:
        raise FFmpegError(proc.stderr.strip().splitlines()[-1] if proc.stderr else "ffmpeg failed")
    return proc


def strip_cmd(src: Path, dst: Path) -> list[str]:
    """Remove all container/stream metadata and chapters without re-encoding."""
    return [
        ffmpeg_bin(), "-y", "-i", str(src),
        "-map", "0", "-map_metadata", "-1", "-map_chapters", "-1",
        "-fflags", "+bitexact", "-flags:v", "+bitexact", "-flags:a", "+bitexact",
        "-c", "copy", "-movflags", "+faststart", str(dst),
    ]


def faststart_cmd(src: Path, dst: Path) -> list[str]:
    """Move the moov atom to the front so the clip starts playing instantly."""
    return [ffmpeg_bin(), "-y", "-i", str(src), "-c", "copy", "-movflags", "+faststart", str(dst)]


def vertical_cmd(src: Path, dst: Path, zoom: float = 1.0, crf: int = 18) -> list[str]:
    """Scale/crop any input to 1080x1920, with an optional static punch-in."""
    w, h = int(TARGET_W * zoom), int(TARGET_H * zoom)
    vf = (
        f"scale={w}:{h}:force_original_aspect_ratio=increase,"
        f"crop={TARGET_W}:{TARGET_H},setsar=1"
    )
    return [
        ffmpeg_bin(), "-y", "-i", str(src), "-vf", vf,
        "-c:v", "libx264", "-preset", "slow", "-crf", str(crf), "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(dst),
    ]


def loudnorm_filter(measured: dict | None = None) -> str:
    base = f"loudnorm=I={TARGET_LUFS}:TP={TARGET_TP}:LRA={TARGET_LRA}"
    if measured is None:
        return base + ":print_format=json"
    return (
        base
        + f":measured_I={measured['input_i']}:measured_TP={measured['input_tp']}"
        + f":measured_LRA={measured['input_lra']}:measured_thresh={measured['input_thresh']}"
        + f":offset={measured['target_offset']}:linear=true"
    )


def parse_loudnorm(stderr: str) -> dict:
    """Pull the JSON block ffmpeg prints at the end of a loudnorm analysis pass."""
    start = stderr.rfind("{")
    end = stderr.rfind("}")
    if start == -1 or end == -1:
        raise FFmpegError("no loudnorm stats in ffmpeg output")
    return json.loads(stderr[start : end + 1])


def loudnorm(src: Path, dst: Path) -> dict:
    """Two-pass EBU R128 normalisation to -14 LUFS. Returns the first-pass stats."""
    analyse = [ffmpeg_bin(), "-hide_banner", "-i", str(src), "-af", loudnorm_filter(), "-f", "null", "-"]
    if DRY_RUN:
        run(analyse)
        stats = {k: "<measured>" for k in ("input_i", "input_tp", "input_lra", "input_thresh", "target_offset")}
    else:
        stats = parse_loudnorm(subprocess.run(analyse, capture_output=True, text=True).stderr)
    run([
        ffmpeg_bin(), "-y", "-i", str(src), "-af", loudnorm_filter(stats),
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-movflags", "+faststart", str(dst),
    ])
    return stats


def thumb_cmd(src: Path, dst: Path, at: float = 0.0) -> list[str]:
    """Grab one full-quality frame (e.g. a cover image) at `at` seconds."""
    return [
        ffmpeg_bin(), "-y", "-ss", f"{at:.3f}", "-i", str(src),
        "-frames:v", "1", "-q:v", "2", "-map_metadata", "-1", str(dst),
    ]


VIDEO_EXTS = {".mp4", ".mov", ".m4v", ".mkv", ".webm"}


def collect_inputs(path: Path) -> list[Path]:
    """A single file, or every video in a folder (skipping reelkit's own outputs)."""
    if path.is_dir():
        return sorted(
            p for p in path.iterdir()
            if p.suffix.lower() in VIDEO_EXTS and ".final" not in p.stem
        )
    return [path]


def default_out(src: Path, suffix: str) -> Path:
    return src.with_name(f"{src.stem}.{suffix}{src.suffix}")


def probe(src: Path) -> dict:
    """Resolution, duration, fps and loudness of a clip, for a quick pre-post check."""
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise FFmpegError("ffprobe not found on PATH")
    meta = json.loads(run_capture([
        ffprobe, "-v", "error", "-show_streams", "-show_format", "-of", "json", str(src),
    ]))
    video = next((s for s in meta["streams"] if s["codec_type"] == "video"), {})
    has_audio = any(s["codec_type"] == "audio" for s in meta["streams"])
    num, den = (video.get("r_frame_rate") or "0/1").split("/")
    info = {
        "width": video.get("width"),
        "height": video.get("height"),
        "fps": round(int(num) / int(den), 2) if int(den) else 0,
        "duration": round(float(meta["format"].get("duration", 0)), 2),
        "tags": sorted(meta["format"].get("tags", {})),
        "lufs": None,
    }
    if has_audio:
        stderr = subprocess.run(
            [ffmpeg_bin(), "-hide_banner", "-i", str(src), "-af", loudnorm_filter(), "-vn", "-f", "null", "-"],
            capture_output=True, text=True,
        ).stderr
        info["lufs"] = float(parse_loudnorm(stderr)["input_i"])
    return info


def checklist(info: dict) -> list[tuple[bool, str]]:
    """Pass/fail checks against the short-form delivery spec."""
    extra = sorted(set(info["tags"]) - BRAND_TAGS)
    checks = [
        (info["width"] == TARGET_W and info["height"] == TARGET_H,
         f"resolution {info['width']}x{info['height']} (want {TARGET_W}x{TARGET_H})"),
        (0 < info["duration"] <= 180, f"duration {info['duration']}s (want <= 180s)"),
        (not extra, f"metadata tags present: {', '.join(extra)}" if extra else "metadata clean"),
    ]
    if info["lufs"] is None:
        checks.append((False, "no audio track"))
    else:
        checks.append((abs(info["lufs"] - TARGET_LUFS) <= 1.0, f"loudness {info['lufs']} LUFS (want {TARGET_LUFS})"))
    return checks


def run_capture(args: list[str]) -> str:
    proc = subprocess.run(args, capture_output=True, text=True)
    if proc.returncode != 0:
        raise FFmpegError(proc.stderr.strip() or "ffprobe failed")
    return proc.stdout
