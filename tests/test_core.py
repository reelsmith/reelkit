from pathlib import Path

import pytest

from reelkit import core
from reelkit.cli import build_parser


@pytest.fixture(autouse=True)
def fake_ffmpeg(monkeypatch):
    monkeypatch.setattr(core, "ffmpeg_bin", lambda: "ffmpeg")


def test_strip_drops_metadata_without_reencode():
    cmd = core.strip_cmd(Path("a.mp4"), Path("b.mp4"))
    assert "-map_metadata" in cmd and cmd[cmd.index("-map_metadata") + 1] == "-1"
    assert cmd[cmd.index("-c") + 1] == "copy"


def test_vertical_zoom_scales_before_crop():
    cmd = core.vertical_cmd(Path("a.mp4"), Path("b.mp4"), zoom=1.1)
    vf = cmd[cmd.index("-vf") + 1]
    assert "scale=1188:2112" in vf and "crop=1080:1920" in vf


def test_loudnorm_second_pass_uses_measured_values():
    measured = {"input_i": "-20.1", "input_tp": "-3.0", "input_lra": "6.2",
                "input_thresh": "-30.4", "target_offset": "0.3"}
    f = core.loudnorm_filter(measured)
    assert "measured_I=-20.1" in f and "linear=true" in f


def test_parse_loudnorm_reads_trailing_json():
    stderr = 'noise\n[Parsed_loudnorm_0 @ 0x0]\n{\n "input_i" : "-19.5",\n "target_offset" : "0.1"\n}\n'
    assert core.parse_loudnorm(stderr)["input_i"] == "-19.5"


def test_default_out_naming():
    assert core.default_out(Path("clips/hook.mp4"), "clean") == Path("clips/hook.clean.mp4")


def test_dry_run_prints_instead_of_running(monkeypatch, capsys):
    monkeypatch.setattr(core, "DRY_RUN", True)
    core.run(core.faststart_cmd(Path("a.mp4"), Path("b.mp4")))
    assert "+faststart" in capsys.readouterr().out


def test_cli_parses_finish():
    args = build_parser().parse_args(["finish", "in.mp4", "--zoom", "1.05"])
    assert args.command == "finish" and args.zoom == 1.05


def test_checklist_flags_wrong_resolution_and_loudness():
    info = {"width": 1280, "height": 720, "duration": 12.0, "tags": ["encoder"], "lufs": -22.0}
    results = dict((msg.split()[0], ok) for ok, msg in core.checklist(info))
    assert results == {"resolution": False, "duration": True, "metadata": False, "loudness": False}


def test_checklist_passes_finished_clip():
    info = {"width": 1080, "height": 1920, "duration": 9.5,
            "tags": ["compatible_brands", "major_brand", "minor_version"], "lufs": -14.2}
    assert all(ok for ok, _ in core.checklist(info))


def test_collect_inputs_skips_non_video_and_finished(tmp_path):
    for name in ("b.mp4", "a.MOV", "notes.txt", "a.final.mp4"):
        (tmp_path / name).write_bytes(b"")
    assert [p.name for p in core.collect_inputs(tmp_path)] == ["a.MOV", "b.mp4"]


def test_thumb_seeks_before_input_for_speed():
    cmd = core.thumb_cmd(Path("a.mp4"), Path("a.jpg"), at=1.5)
    assert cmd.index("-ss") < cmd.index("-i") and "1.500" in cmd
