"""reelkit command line: `reelkit <command> input.mp4 [-o output.mp4]`."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__, core


def _out(args, suffix: str) -> Path:
    return Path(args.output) if args.output else core.default_out(Path(args.input), suffix)


def cmd_strip(args):
    dst = _out(args, "clean")
    core.run(core.strip_cmd(Path(args.input), dst))
    print(f"stripped metadata -> {dst}")


def cmd_faststart(args):
    dst = _out(args, "fs")
    core.run(core.faststart_cmd(Path(args.input), dst))
    print(f"faststart -> {dst}")


def cmd_vertical(args):
    dst = _out(args, "9x16")
    core.run(core.vertical_cmd(Path(args.input), dst, zoom=args.zoom, crf=args.crf))
    print(f"1080x1920 -> {dst}")


def cmd_loud(args):
    dst = _out(args, "loud")
    stats = core.loudnorm(Path(args.input), dst)
    print(f"input {stats['input_i']} LUFS -> {core.TARGET_LUFS} LUFS -> {dst}")


def cmd_info(args):
    info = core.probe(Path(args.input))
    checks = core.checklist(info)
    for ok, msg in checks:
        print(f"  [{'ok' if ok else '!!'}] {msg}")
    ready = all(ok for ok, _ in checks)
    print("ready to post" if ready else "run `reelkit finish` to fix")
    return 0 if ready else 2


def cmd_thumb(args):
    src = Path(args.input)
    dst = Path(args.output) if args.output else src.with_name(f"{src.stem}.cover.jpg")
    core.run(core.thumb_cmd(src, dst, at=args.at))
    print(f"cover frame @ {args.at}s -> {dst}")


def cmd_finish(args):
    """vertical -> loudnorm -> strip, the full delivery chain. Accepts a folder."""
    inputs = core.collect_inputs(Path(args.input))
    if not inputs:
        raise core.FFmpegError(f"no videos found in {args.input}")
    if len(inputs) > 1 and args.output:
        raise core.FFmpegError("-o can't be used with a folder; outputs go next to each input")
    for i, src in enumerate(inputs, 1):
        if len(inputs) > 1:
            print(f"[{i}/{len(inputs)}] {src.name}")
        _finish_one(src, Path(args.output) if args.output else core.default_out(src, "final"), args.zoom)


def _finish_one(src: Path, final: Path, zoom: float):
    tmp1, tmp2 = final.with_suffix(".tmp1.mp4"), final.with_suffix(".tmp2.mp4")
    try:
        core.run(core.vertical_cmd(src, tmp1, zoom=zoom))
        core.loudnorm(tmp1, tmp2)
        core.run(core.strip_cmd(tmp2, final))
    finally:
        for t in (tmp1, tmp2):
            t.unlink(missing_ok=True)
    print(f"ready to post -> {final}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="reelkit", description="Finish short-form video for TikTok / Reels / Shorts.")
    p.add_argument("--version", action="version", version=f"reelkit {__version__}")
    p.add_argument("--dry-run", action="store_true", help="print the ffmpeg commands instead of running them")
    sub = p.add_subparsers(dest="command", required=True)

    def add(name, fn, help_):
        sp = sub.add_parser(name, help=help_)
        sp.add_argument("input")
        sp.add_argument("-o", "--output")
        sp.set_defaults(func=fn)
        return sp

    add("strip", cmd_strip, "remove all metadata (no re-encode)")
    add("faststart", cmd_faststart, "move moov atom to front for instant playback")
    v = add("vertical", cmd_vertical, "scale/crop to 1080x1920")
    v.add_argument("--zoom", type=float, default=1.0)
    v.add_argument("--crf", type=int, default=18)
    add("loud", cmd_loud, "two-pass loudnorm to -14 LUFS")
    i = sub.add_parser("info", help="check a clip against the TikTok/Reels/Shorts spec")
    i.add_argument("input")
    i.set_defaults(func=cmd_info)
    t = add("thumb", cmd_thumb, "export a cover frame as JPG")
    t.add_argument("--at", type=float, default=0.0, help="timestamp in seconds")
    f = add("finish", cmd_finish, "vertical + loudnorm + strip in one go (file or folder)")
    f.add_argument("--zoom", type=float, default=1.0)
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    core.DRY_RUN = args.dry_run
    try:
        return args.func(args) or 0
    except core.FFmpegError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
