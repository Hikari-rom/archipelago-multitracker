#!/usr/bin/env bash
# Run validate_logic.py for several games sequentially (test code only).
#   scripts/testenv/campaign.sh RUNS "Game 1" "Game 2" ...
# Output: test-output/logs/campaign-<slug>.log, summary line per game in test-output/logs/campaign.summary
set -u
cd "$(dirname "$0")/../.."
runs="$1"; shift
mkdir -p test-output/logs
for game in "$@"; do
  slug="$(echo "$game" | tr 'A-Z' 'a-z' | tr -c 'a-z0-9' '_' | cut -c1-40)"
  timeout 7200 .venv/bin/python scripts/testenv/validate_logic.py "$game" --runs "$runs" \
    2>&1 | grep -E '^(OK |KO |GEN)' > "test-output/logs/campaign-$slug.log"
  ok=$(grep -c '^OK ' "test-output/logs/campaign-$slug.log"); ko=$(grep -c '^KO ' "test-output/logs/campaign-$slug.log")
  gen=$(grep -c '^GEN' "test-output/logs/campaign-$slug.log")
  echo "$(date -Iseconds) | $game | OK=$ok KO=$ko GENFAIL=$gen" >> test-output/logs/campaign.summary
done
