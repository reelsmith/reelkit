# Contributing

Issues and pull requests are welcome.

1. Fork the repo and create a branch.
2. `pip install -e ".[dev]"`
3. Make your change and add a test in `tests/`. The tests check the ffmpeg commands reelkit builds, so they don't need any video files.
4. Run `pytest` and open a PR describing what it changes and why.

Please keep new commands in the same style: one small function in `core.py` that builds the ffmpeg command, and a thin wrapper in `cli.py`.
