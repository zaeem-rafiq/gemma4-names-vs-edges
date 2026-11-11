#!/bin/bash
# Runs Study A one model at a time from the unpacked prereg-v1.0 snapshot.
# Stops at the first non-zero exit. Each command is resumable: rerun this script after an interruption.
set -u
P="${P:?set P to the project folder}"
LOG="$P/run_log"
TIMES="$LOG/studyA_times.tsv"
STATUS="$LOG/studyA_status.txt"

cd "$P/studyA-v1.0" || exit 1
source ../gemma4-paper-code/.venv/bin/activate
export PYTHONPATH=src
mkdir -p runs

echo "RUNNING pid=$$ $(date -u +%FT%TZ)" > "$STATUS"
[ -f "$TIMES" ] || printf 'tag\tstart_utc\tend_utc\texit\n' > "$TIMES"

step() {
  local tag="$1"; shift
  local start end rc
  start=$(date -u +%FT%TZ)
  "$@" >> "runs/log_${tag}.txt" 2>&1
  rc=$?
  end=$(date -u +%FT%TZ)
  printf '%s\t%s\t%s\t%s\n' "$tag" "$start" "$end" "$rc" >> "$TIMES"
  if [ "$rc" -ne 0 ]; then
    echo "FAILED tag=$tag exit=$rc $end" > "$STATUS"
    exit "$rc"
  fi
}

ITEMS=(--items-dir data/items --manifest data/repos_manifest.json)

step E2B python -m ngraph.runner study-a --model ../models/gemma-4-E2B_q4_0-it.gguf --tag E2B "${ITEMS[@]}" --out runs/studyA_E2B.jsonl
step E4B python -m ngraph.runner study-a --model ../models/gemma-4-E4B_q4_0-it.gguf --tag E4B "${ITEMS[@]}" --out runs/studyA_E4B.jsonl
step 12B python -m ngraph.runner study-a --model ../models/gemma-4-12b-it-qat-q4_0.gguf --tag 12B "${ITEMS[@]}" --out runs/studyA_12B.jsonl
step 31B python -m ngraph.runner study-a --model ../models/gemma-4-31B_q4_0-it.gguf --tag 31B "${ITEMS[@]}" --prefix-from data/gng2/final/gng1_rename3_31B.json --out runs/studyA_31B.jsonl
step analysis python -m ngraph.analysis --runs runs/studyA_E2B.jsonl runs/studyA_E4B.jsonl runs/studyA_12B.jsonl runs/studyA_31B.jsonl --manifest data/repos_manifest.json --items-dir data/items --out runs/studyA_report.json

echo "DONE $(date -u +%FT%TZ)" > "$STATUS"
