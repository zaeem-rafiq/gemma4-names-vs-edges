#!/bin/bash
# Study B runs, one model at a time, from the unpacked prereg-v1.1 snapshot. Each step's exit code and UTC
# start/end go to runs/studyb_runs.exit; a failed step is recorded and the script goes on. Runs are resumable.
P="${P:?set P to the project folder}"; cd "$P/studyB-v1.1" || exit 9
source ../gemma4-paper-code/.venv/bin/activate; export PYTHONPATH=src
EX=runs/studyb_runs.exit
echo "start pid=$$ $(date -u +%FT%TZ)" >> "$EX"
OFF=(--set official --tasks "$P/studyb-frozen/official/tasks.json" --data "$P/competition-data")
LITE=(--set lite --tasks "$P/studyb-frozen/lite/tasks.json" --lite-test "$P/lite/swebench_lite_test.jsonl" --lite-dev "$P/lite/swebench_lite_dev.jsonl" --repos-dir "$P/lite-repos")
E4B=(--model ../models/gemma-4-E4B_q4_0-it.gguf --tag E4B)
M31=(--model ../models/gemma-4-31B_q4_0-it.gguf --tag 31B --prefix-from data/gng2/final/gng1_rename3_31B.json)
M12=(--model ../models/gemma-4-12b-it-qat-q4_0.gguf --tag 12B)
step(){ n=$1; shift; s=$(date -u +%FT%TZ); caffeinate -i python -m ngraph.studyb run "$@" >> "runs/log_$n.txt" 2>&1; c=$?; echo "$n exit=$c start=$s end=$(date -u +%FT%TZ)" >> "$EX"; }
step studyB_official_E4B "${OFF[@]}" "${E4B[@]}" --out runs/studyB_official_E4B.jsonl
step studyB_official_31B "${OFF[@]}" "${M31[@]}" --out runs/studyB_official_31B.jsonl
step studyB_lite_E4B "${LITE[@]}" "${E4B[@]}" --out runs/studyB_lite_E4B.jsonl
step studyB_wm_official_E4B "${OFF[@]}" "${E4B[@]}" --cells within_module --repeat 0 --out runs/studyB_wm_official_E4B.jsonl
step studyB_wm_official_31B "${OFF[@]}" "${M31[@]}" --cells within_module --repeat 0 --out runs/studyB_wm_official_31B.jsonl
step studyB_wm_lite_E4B "${LITE[@]}" "${E4B[@]}" --cells within_module --repeat 0 --out runs/studyB_wm_lite_E4B.jsonl
step studyB_official_12B "${OFF[@]}" "${M12[@]}" --out runs/studyB_official_12B.jsonl
step studyB_lite_31B "${LITE[@]}" "${M31[@]}" --out runs/studyB_lite_31B.jsonl
echo "all done $(date -u +%FT%TZ)" >> "$EX"
