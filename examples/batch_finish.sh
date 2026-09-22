#!/usr/bin/env bash
# Finish every clip in a folder: ./batch_finish.sh raw_clips/
set -euo pipefail
for f in "${1:-.}"/*.mp4; do
  reelkit finish "$f" --zoom 1.05
done
