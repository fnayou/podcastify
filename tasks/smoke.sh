#!/bin/sh
set -eu

IMAGE="$1"
PORT="${2:-18083}"
NAME="podcastify-smoke-$$"
WORK="$(mktemp -d)"

cleanup() {
  docker rm -f "$NAME" >/dev/null 2>&1 || true
  rm -rf "$WORK"
}
trap cleanup EXIT

fail() {
  echo "smoke: $1" >&2
  docker logs "$NAME" >&2 || true
  exit 1
}

fetch() {
  curl -fsS --retry 30 --retry-delay 1 --retry-connrefused --retry-all-errors --max-time 2 "$@"
}

mkdir -p "$WORK/podcasts" "$WORK/public/smoke"
printf 'ID3' > "$WORK/public/smoke/ep01.mp3"
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
fetch "http://127.0.0.1:${PORT}/smoke.xml" | grep -q '<rss' || fail "/smoke.xml is not an RSS feed"
fetch -o /dev/null "http://127.0.0.1:${PORT}/smoke/ep01.mp3" || fail "episode media not served"

owner="$(docker exec "$NAME" sh -c 'stat -c %u /proc/$(pidof caddy)')"
[ "$owner" = "1000" ] || fail "caddy runs as uid ${owner}, expected 1000"

echo "smoke: ok"
