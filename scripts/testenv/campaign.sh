#!/usr/bin/env bash
# Run validate_logic.py for several games sequentially (test code only).
#   scripts/testenv/campaign.sh RUNS "Game 1" "Game 2" ...
#   EXTRA_ARGS="--goal-needs" SUMMARY=needs scripts/testenv/campaign.sh 1 "Jak 3"   (options of validate_logic.py)
# Output: test-output/logs/<SUMMARY>-<slug>.log, summary line per game in test-output/logs/<SUMMARY>.summary
# (SUMMARY defaults to "campaign")
set -u
cd "$(dirname "$0")/../.."
runs="$1"; shift
first="${FIRST_RUN:-1}"
name="${SUMMARY:-campaign}"
mkdir -p test-output/logs
for game in "$@"; do
  slug="$(echo "$game" | tr 'A-Z' 'a-z' | tr -c 'a-z0-9' '_' | cut -c1-40)"
  log="test-output/logs/$name-$slug.log"
  # shellcheck disable=SC2086  # EXTRA_ARGS: several options
  timeout 7200 .venv/bin/python scripts/testenv/validate_logic.py "$game" --runs "$runs" --first-run "$first" \
    ${EXTRA_ARGS:-} 2>&1 | grep -E '^(OK |KO |GEN|NC )' >> "$log"
  ok=$(grep -c '^OK ' "$log"); ko=$(grep -c '^KO ' "$log")
  gen=$(grep -c '^GEN' "$log"); nc=$(grep -c '^NC ' "$log")
  echo "$(date -Iseconds) | $game | OK=$ok KO=$ko GENFAIL=$gen NOT_COMPARABLE=$nc" >> "test-output/logs/$name.summary"
done
