#!/bin/bash
P="${P:?set P to the project folder}"; X="$P/exploratory-v1.1"; cd "$P/studyB-v1.1" || exit 9
source ../gemma4-paper-code/.venv/bin/activate; export PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1
step(){ n=$1; shift; s=$(date -u +%FT%TZ); caffeinate -i -s python "$X/e3_run.py" "$@" >> "$X/log_$n.txt" 2>&1; echo "$n exit=$? start=$s end=$(date -u +%FT%TZ)" >> "$X/run.exit"; }
step e3_E4B "$X/e3_prompts.jsonl" "$X/e3_E4B.jsonl" ../models/gemma-4-E4B_q4_0-it.gguf E4B
step e3_31B "$X/e3_prompts.jsonl" "$X/e3_31B.jsonl" ../models/gemma-4-31B_q4_0-it.gguf 31B --prefix-from data/gng2/final/gng1_rename3_31B.json
