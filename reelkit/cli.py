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


def cmd_finish(args):
    """vertical -> loudnorm -> strip, the full delivery chain."""
    src = Path(args.input)
    final = _out(args, "final")
    tmp1, tmp2 = final.with_suffix(".tmp1.mp4"), final.with_suffix(".tmp2.mp4")
    try:
        core.run(core.vertical_cmd(src, tmp1, zoom=args.zoom))
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
    f = add("finish", cmd_finish, "vertical + loudnorm + strip in one go")
    f.add_argument("--zoom", type=float, default=1.0)
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    core.DRY_RUN = args.dry_run
    try:
        args.func(args)
    except core.FFmpegError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
