#!/bin/sh
# Regenerates tests/fixtures/audio/ (maintainers only, not run in CI).
# ffmpeg runs inside a throwaway alpine container, so nothing is installed on the host.
# Needs Docker. Usage: tests/fixtures/make_audio.sh
# Every tone file is 1 s, mono, 24 kHz, low bitrate, so each stays a few KB.
set -eu

IMAGE="alpine:3.22"
OUT="$(cd "$(dirname "$0")" && pwd)/audio"
mkdir -p "$OUT"

docker run --rm -i -v "$OUT:/out" "$IMAGE" sh -s <<'EOF'
set -eu
apk add --no-cache ffmpeg >/dev/null
cd /out
rm -f ./*

TONE="ffmpeg -v error -y -f lavfi -i sine=frequency=440:duration=1:sample_rate=24000 -ac 1"

$TONE -c:a libmp3lame -b:a 32k cbr.mp3
$TONE -c:a libmp3lame -b:a 32k -write_xing 0 cbr-noxing.mp3
$TONE -c:a libmp3lame -q:a 9 vbr-xing.mp3
$TONE -c:a aac -b:a 24k tone.m4a
$TONE -c:a aac -b:a 24k -f mp4 tone.mp4
$TONE -c:a libvorbis -q:a -1 tone.ogg
$TONE -c:a libopus -b:a 16k tone.opus

ffmpeg -v error -y -f lavfi -i color=c=red:s=16x16 -frames:v 1 /tmp/cover.png
$TONE -i /tmp/cover.png -map 0:a -map 1:v -c:a libmp3lame -b:a 32k -c:v png \
  -id3v2_version 3 -metadata title=Fixture id3-cover.mp3

head -c 2048 cbr.mp3 > truncated.mp3
: > zero-byte.mp3
yes "this is not audio" | head -c 4096 > garbage.mp3
EOF
