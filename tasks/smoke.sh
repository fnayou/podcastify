#!/bin/sh
set -eu

IMAGE="$1"
PORT="${2:-18083}"
NAME="podcastify-smoke-$$"
WORK="$(mktemp -d)"

INDEX_NAME="${NAME}-index"

stop() {
  docker exec "$1" sh -c 'rm -rf /app/public/* /app/public/.[!.]*' >/dev/null 2>&1 || true
  docker rm -f "$1" >/dev/null 2>&1 || true
}

cleanup() {
  stop "$NAME"
  stop "$INDEX_NAME"
  rm -rf "$WORK"
}
trap cleanup EXIT

fail() {
  echo "smoke: $1" >&2
  docker logs "$NAME" >&2 || true
  docker logs "$INDEX_NAME" >&2 || true
  exit 1
}

status() {
  curl -sS --max-time 2 -o /dev/null -w '%{http_code}' "$1"
}

fetch() {
  curl -fsS --retry 30 --retry-delay 1 --retry-connrefused --retry-all-errors --max-time 2 "$@"
}

mkdir -p "$WORK/podcasts" "$WORK/public/smoke"
cp "$(dirname "$0")/../tests/fixtures/audio/cbr.mp3" "$WORK/public/smoke/ep01.mp3"
cat > "$WORK/podcasts/smoke-podcast.yaml" <<'EOF'
name: "smoke"
title: "Smoke"
author-name: "CI"
author-email: "ci@example.com"
description: "Smoke test feed"
language: "en"
explicit: false
categories:
  - "Technology"
episodes:
  - file: "ep01.mp3"
    title: "Episode"
    description: "Episode"
    pub_date: "2025-01-01T08:00:00Z"
EOF

docker run -d --name "$NAME" \
  -p "127.0.0.1:${PORT}:8080" \
  -e PUBLIC_BASE_URL="http://localhost:${PORT}" \
  -v "$WORK/podcasts:/app/podcasts" \
  -v "$WORK/public:/app/public" \
  "$IMAGE" >/dev/null

fetch -o /dev/null "http://127.0.0.1:${PORT}/healthz" || fail "/healthz did not return 200 within 30 s"
fetch "http://127.0.0.1:${PORT}/smoke.xml" > "$WORK/smoke.xml" || fail "/smoke.xml not served"
grep -q '<rss' "$WORK/smoke.xml" || fail "/smoke.xml is not an RSS feed"
grep -q '<itunes:duration>0:01</itunes:duration>' "$WORK/smoke.xml" || fail "episode duration not read from the media file"
fetch -o /dev/null "http://127.0.0.1:${PORT}/smoke/ep01.mp3" || fail "episode media not served"

owner="$(docker exec "$NAME" sh -c 'stat -c %u /proc/$(pidof caddy)')"
[ "$owner" = "1000" ] || fail "caddy runs as uid ${owner}, expected 1000"

code="$(status "http://127.0.0.1:${PORT}/")"
[ "$code" = "404" ] || fail "/ answered ${code} by default, expected 404"

# Same mounts, so the feed from the first run is already there and this start is quick.
docker rm -f "$NAME" >/dev/null
docker run -d --name "$INDEX_NAME" \
  -p "127.0.0.1:${PORT}:8080" \
  -e PUBLIC_BASE_URL="http://localhost:${PORT}" \
  -e PUBLISH_INDEX=true \
  -v "$WORK/podcasts:/app/podcasts" \
  -v "$WORK/public:/app/public" \
  "$IMAGE" >/dev/null

fetch -o /dev/null "http://127.0.0.1:${PORT}/healthz" || fail "/healthz did not return 200 with PUBLISH_INDEX=true"
fetch "http://127.0.0.1:${PORT}/" > "$WORK/index.html" || fail "/ not served with PUBLISH_INDEX=true"
grep -q "http://localhost:${PORT}/smoke.xml" "$WORK/index.html" || fail "/ does not link the smoke feed"

echo "smoke: ok"
