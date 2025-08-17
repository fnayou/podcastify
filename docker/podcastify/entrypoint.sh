#!/bin/sh
set -e

echo "🔧 Podcastify container starting..."

if [ "${RUN_ON_START:-true}" = "true" ]; then
  echo "🎙️  Running generator at startup..."
  if ! python /app/app.py generate; then
    echo "⚠️  Generator exited non-zero; continuing to serve existing content"
  fi
fi

echo "🌐 Starting Caddy on : $PUBLIC_BASE_URL"

exec /usr/bin/supervisord -c /etc/supervisord.conf
