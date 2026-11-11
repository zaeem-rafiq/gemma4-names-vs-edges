#!/bin/bash
# Study B timing pilots (tune tasks only; never confirmatory). Run with nohup from anywhere.
P="${P:?set P to the project folder}"; cd "$P/studyB-v1.1" || exit 9
source ../gemma4-paper-code/.venv/bin/activate; export PYTHONPATH=src
EX=runs/pilot_timing.exit
IDS=(marshmallow-code__marshmallow-1343 marshmallow-code__marshmallow-1359 pvlib__pvlib-python-1072)
LITE=(--set lite --tasks "$P/studyb-frozen/lite/tasks.json" --lite-test "$P/lite/swebench_lite_test.jsonl" --lite-dev "$P/lite/swebench_lite_dev.jsonl" --repos-dir "$P/lite-repos")
step(){ n=$1; shift; s=$(date -u +%FT%TZ); "$@" >> "runs/log_$n.txt" 2>&1; c=$?; echo "$n exit=$c start=$s end=$(date -u +%FT%TZ)" >> "$EX"; }
step pilot_timing_E4B caffeinate -i python -m ngraph.studyb run "${LITE[@]}" --roles tune --only "${IDS[@]}" --repeat 0 --model ../models/gemma-4-E4B_q4_0-it.gguf --tag E4B --out runs/pilot_timing_E4B.jsonl
step pilot_timing_31B caffeinate -i python -m ngraph.studyb run "${LITE[@]}" --roles tune --only "${IDS[@]}" --repeat 0 --model ../models/gemma-4-31B_q4_0-it.gguf --tag 31B --prefix-from data/gng2/final/gng1_rename3_31B.json --out runs/pilot_timing_31B.jsonl
echo "done $(date -u +%FT%TZ)" >> "$EX"
