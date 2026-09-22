# reelkit

**Finish short-form video for TikTok, Instagram Reels and YouTube Shorts in one command.**

Raw clips from phones, editors and AI video tools come out in the wrong shape, at random loudness, and full of metadata. `reelkit` turns them into post-ready 1080×1920 MP4s:

| Step | What it does |
|---|---|
| `vertical` | Scales and crops any clip to 1080×1920 (9:16), with an optional punch-in zoom |
| `loud` | Two-pass EBU R128 loudness normalisation to **-14 LUFS / -1.5 dBTP** (the level the platforms play back at) |
| `strip` | Removes all container and stream metadata and chapters, without re-encoding |
| `faststart` | Moves the `moov` atom to the front so the video starts playing instantly |
| `finish` | Runs `vertical`, then `loud`, then `strip` in one go |

## Install

You need **Python 3.9+** and **[ffmpeg](https://ffmpeg.org/download.html)** on your PATH.

```bash
# Windows
winget install Gyan.FFmpeg
# macOS
brew install ffmpeg
# Linux
sudo apt install ffmpeg
```

Then install reelkit directly from GitHub:

```bash
pip install git+https://github.com/reelsmith/reelkit.git
```

Or clone it and install locally:

```bash
git clone https://github.com/reelsmith/reelkit.git
cd reelkit
pip install .
```

## Usage

```bash
reelkit finish raw.mp4                 # -> raw.final.mp4, ready to upload
reelkit finish raw.mp4 --zoom 1.05     # add a subtle 5% punch-in
reelkit vertical landscape.mov -o out.mp4
reelkit loud voiceover_mix.mp4
reelkit strip export.mp4
reelkit faststart export.mp4
```

If you don't pass `-o`, the output is written next to the input with a suffix, for example `clip.clean.mp4` or `clip.9x16.mp4`.

To process a whole folder, see [`examples/batch_finish.sh`](examples/batch_finish.sh).

You can also run it without installing: `python -m reelkit finish raw.mp4`.

## Why -14 LUFS?

TikTok, Instagram and YouTube all turn loud uploads down and leave quiet ones quiet. If you master to about -14 LUFS integrated with a -1.5 dBTP ceiling, your audio plays back as you mixed it, without getting squashed or sounding thin next to other videos in the feed. `reelkit` runs ffmpeg's `loudnorm` twice. The first pass measures the audio and the second applies a linear correction, so the dynamics aren't pumped.

## Development

```bash
pip install -e ".[dev]"
pytest
```

The tests check the ffmpeg commands reelkit builds, so they don't need any video files.

## License

MIT
