#!/bin/bash
# Encode the rendered frames to H.264 (this ffmpeg build has OpenH264, not x264), then mix.py adds the sound.
# usage: bash explainer/video/encode.sh <frames.mkv> <silent.mp4>
set -e
ffmpeg -hide_banner -v error -y -i "$1" -vf "scale=in_range=pc:out_range=tv:out_color_matrix=bt709,format=yuv420p" \
  -c:v libopenh264 -profile:v high -b:v 12M -maxrate 16M -qmin 12 -qmax 20 -g 60 -r 30 \
  -colorspace bt709 -color_primaries bt709 -color_trc bt709 -color_range tv -movflags +faststart "$2"
