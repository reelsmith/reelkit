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
| `thumb` | Saves a full-quality cover frame as a JPG at any timestamp |
| `info` | Checks a clip against the spec and says whether it's ready to post |

## Example

A landscape export straight out of an editor, checked before and after:

```text
$ reelkit info IMG_4471.mp4
  [!!] resolution 1920x1080 (want 1080x1920)
  [ok] duration 8.0s (want <= 180s)
  [!!] metadata tags present: encoder, title
  [!!] loudness -21.85 LUFS (want -14.0)
run `reelkit finish` to fix

$ reelkit finish IMG_4471.mp4 --zoom 1.05
ready to post -> IMG_4471.final.mp4

$ reelkit info IMG_4471.final.mp4
  [ok] resolution 1080x1920 (want 1080x1920)
  [ok] duration 8.1s (want <= 180s)
  [ok] metadata clean
  [ok] loudness -13.99 LUFS (want -14.0)
ready to post
```

## Why I built this

I post a lot of short-form product videos, and every clip went through the same manual routine: reframe to 9:16, fix the loudness so it didn't sound quiet next to everything else in the feed, strip the editor and camera metadata, and make sure it starts playing instantly. I kept a text file of ffmpeg commands and pasted them in one by one. reelkit is that text file turned into one command.

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
reelkit finish raw_clips/             # every video in the folder
reelkit thumb raw.final.mp4 --at 1.2   # cover image from 1.2s in
reelkit info final.mp4                 # pass/fail checklist, exit code 0 = ready
reelkit --dry-run finish raw.mp4       # print the ffmpeg commands without running them
```

If you don't pass `-o`, the output is written next to the input with a suffix, for example `clip.clean.mp4` or `clip.9x16.mp4`.

`finish` accepts a folder too. It processes every `.mp4`, `.mov`, `.m4v`, `.mkv` and `.webm` inside it and skips files it has already finished.

## How it works

```
raw clip ──► vertical ──► loud (measure) ──► loud (correct) ──► strip ──► clip.final.mp4
             1080x1920    LUFS + true peak   linear gain, -14    no metadata, faststart
```

- **Reframe:** scales to cover 1080×1920, then center-crops, so there are never black bars. `--zoom 1.05` scales 5% larger before cropping for a subtle punch-in.
- **Encode:** H.264 `-preset slow -crf 18`, `yuv420p` for maximum compatibility, AAC 192 kbps at 48 kHz.
- **Strip:** a stream copy with `-map_metadata -1 -map_chapters -1` and bit-exact flags, so it doesn't lose any quality.
- Temporary files are cleaned up even if a step fails.

You can also run it without installing: `python -m reelkit finish raw.mp4`.

## Why -14 LUFS?

TikTok, Instagram and YouTube all turn loud uploads down and leave quiet ones quiet. If you master to about -14 LUFS integrated with a -1.5 dBTP ceiling, your audio plays back as you mixed it, without getting squashed or sounding thin next to other videos in the feed. `reelkit` runs ffmpeg's `loudnorm` twice. The first pass measures the audio and the second applies a linear correction, so the dynamics aren't pumped.

## FAQ

**Does `strip` re-encode my video?** No. It only rewrites the container, so it's instant and doesn't lose any quality.

**Will this change how my video looks?** `vertical` and `finish` re-encode at CRF 18, which is visually lossless for social media. `strip`, `faststart` and `thumb` never touch the pixels.

**Why exit code 2 from `info`?** So you can use it in scripts: `0` means ready, `2` means it needs fixing, `1` means an error.

## Roadmap

- [ ] Burned-in captions from an `.srt` file, in TikTok-style fonts
- [ ] Safe-zone aware caption placement (see [safezone](https://github.com/reelsmith/safezone))
- [ ] Per-platform presets (`--for tiktok`, `--for shorts`)
- [ ] Install from PyPI with `pip install reelkit`

## Development

```bash
pip install -e ".[dev]"
pytest
```

The tests check the ffmpeg commands reelkit builds, so they don't need any video files.

## License

MIT
