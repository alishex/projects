#!/usr/bin/env bash
set -e
cd -- "$(dirname -- "$0")"
if ! command -v node >/dev/null 2>&1; then
  echo 'Node.js 24 ni https://nodejs.org dan o‘rnating.'
  exit 1
fi
exec node server.mjs
