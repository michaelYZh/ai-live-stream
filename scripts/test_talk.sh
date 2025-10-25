#!/usr/bin/env bash

set -euo pipefail

# Simple helper to hit the /talk endpoint and save the returned audio.
# Usage: ./scripts/test_talk.sh "Custom script (optional)" output.wav

API_BASE=${API_BASE:-http://localhost:8000}
SCRIPT=${1:-}
OUTPUT=${2:-talk_output.wav}

if ! command -v curl >/dev/null 2>&1; then
  echo "curl is required but not installed" >&2
  exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "jq is required but not installed" >&2
  exit 1
fi

if ! command -v base64 >/dev/null 2>&1; then
  echo "base64 utility is required but not installed" >&2
  exit 1
fi

echo "Calling ${API_BASE}/talk ..."
if [[ -n "${SCRIPT}" ]]; then
  payload=$(jq -n --arg script "${SCRIPT}" '{script: $script}')
else
  payload="{}"
fi

response=$(curl -sS -X POST "${API_BASE}/talk" \
  -H "Content-Type: application/json" \
  -d "${payload}")

script=$(echo "${response}" | jq -r '.script')
audio_b64=$(echo "${response}" | jq -r '.audio_base64')
mime=$(echo "${response}" | jq -r '.mime_type')

if [[ -z "${audio_b64}" || "${audio_b64}" == "null" ]]; then
  echo "No audio returned. Raw response:"
  echo "${response}"
  exit 1
fi

echo "${audio_b64}" | base64 --decode > "${OUTPUT}"
printf "Saved audio to %s (%s)\n" "${OUTPUT}" "${mime}"
printf "Script used:\n%s\n" "${script}"
