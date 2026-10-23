#!/bin/sh
set -eu

TAG="${1:?usage: release_range.sh TAG [FIRST_COMMIT]}"
FIRST_COMMIT="${2:-f1e964de}"

if git rev-parse -q --verify "refs/tags/${TAG}" >/dev/null; then
  END="${TAG}"
  SELF="$(printf '%s' "${TAG}" | sed 's/\./\\./g')"
  TAG_PATTERN="^${SELF}\$"
else
  END=HEAD
  TAG_PATTERN='^$'
fi

case "${TAG}" in
  *-*) PATTERN='^v20[0-9]{2}\.[0-9]+\.[0-9]+(-.*)?$' ;;
  *) PATTERN='^v20[0-9]{2}\.[0-9]+\.[0-9]+$' ;;
esac

PREV="$(git log --simplify-by-decoration --format=%D "${END}^" 2>/dev/null | tr ',' '\n' | sed -n 's/^ *tag: //p' | grep -E "${PATTERN}" | head -n 1 || true)"
START="${PREV:-${FIRST_COMMIT}}"

echo "Notes range: ${START}..${END}" >&2
printf "%s\n" "--tag-pattern '${TAG_PATTERN}' ${START}..${END}"
