#!/bin/bash
# Waits for the E4c preparation, checks it, then scores E4B and 31B. Run with nohup.
P="${P:?set P to the project folder}"; X="$P/exploratory-v1.1"
until [ "$(grep -c '^e4c_prepare' "$X/run.exit")" -ge ${WAIT_N:-3} ]; do sleep 30; done
[ "$(grep '^e4c_prepare' "$X/run.exit" | tail -1 | cut -d' ' -f2)" = "exit=0" ] || { echo "e4c_gate exit=1 reason=prepare_failed $(date -u +%FT%TZ)" >> "$X/run.exit"; exit 1; }
python3 -I - "$X" <<'PY' || { echo "e4c_gate exit=1 reason=checks_failed $(date -u +%FT%TZ)" >> "$X/run.exit"; exit 1; }
import json, sys
X = sys.argv[1]; d = json.load(open(X + "/e4c_checks.json")); s = d["summary"]; t = d["tasks"]
ok = (d["n_tasks"] == 174 and d["exact_counts"]["dense_eq_true"] == 174 and d["exact_counts"]["thinned_eq_rewired"] >= 171
      and s["random_dense"]["gold_anchor_edge_share"] == 0
      and s["random_dense"]["neighbour_list_consistent_share"] == 1 and s["true_thinned"]["neighbour_list_consistent_share"] == 1)
n = sum(1 for _ in open(X + "/e4c_prompts.jsonl"))
print(json.dumps({"checks_ok": ok, "prompts": n, "summary": s, "exact_counts": d["exact_counts"]}))
sys.exit(0 if ok and n == 696 else 1)
PY
echo "e4c_gate exit=0 $(date -u +%FT%TZ)" >> "$X/run.exit"
cd "$P/studyB-v1.1" || exit 9
source ../gemma4-paper-code/.venv/bin/activate; export PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1
step(){ n=$1; shift; s=$(date -u +%FT%TZ); caffeinate -i -s python "$X/e3_run.py" "$@" >> "$X/log_$n.txt" 2>&1; echo "$n exit=$? start=$s end=$(date -u +%FT%TZ)" >> "$X/run.exit"; }
step e4c_E4B "$X/e4c_prompts.jsonl" "$X/e4c_E4B.jsonl" ../models/gemma-4-E4B_q4_0-it.gguf E4B --study E4c
step e4c_31B "$X/e4c_prompts.jsonl" "$X/e4c_31B.jsonl" ../models/gemma-4-31B_q4_0-it.gguf 31B --study E4c --prefix-from data/gng2/final/gng1_rename3_31B.json
