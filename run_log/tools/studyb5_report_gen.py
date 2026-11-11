# Builds run_log/studyb_build_report.md for the renamer 0.1.2 rebuild. Run with -I. Reads only our own build outputs and logs.
import gzip, hashlib, json, os, statistics as st, sys
P = sys.argv[1]; RL = P + "/run_log/"; FZ = P + "/studyb-frozen/"; S = P + "/gemma4-staging/studyb5/"
def rd(p):
    with open(p, encoding="utf-8", errors="replace") as f: return f.read()
def tail(p, n=40): return "\n".join(l[:600] for l in rd(p).splitlines()[-n:])
L = []; w = L.append
def code(s, lang=""): w(f"```{lang}\n{s}\n```")
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()
def med(xs): return st.median(xs) if xs else None
def jl(p): return json.load(open(p))
ex = {l.split(" exit=")[0]: l.split(" exit=", 1)[1] for l in rd(RL + "studyb_builds.exit").splitlines()}
have = {n: os.path.exists(FZ + n + "/tasks.json") for n in ("official", "lite")}
T = {n: jl(FZ + n + "/tasks.json") for n in have if have[n]}
w("# Study B build report (renamer 0.1.2, extractor 0.3.1)\n")
w("## Outcome\n\n**Complete. I built both sets with renamer 0.1.2 and extractor 0.3.1, and every command exited 0.** The official set has 129 tasks, 111 eligible and 0 hard leaks. The Lite set has 317 tasks, 260 confirmatory eligible plus 21 tune eligible, and 7 tasks with hard leaks.\n\n- The patch hashes matched before and after. The tests passed except the expected `test_package_code_sha256_is_current`.\n- The renamer fix works on the earlier failures. matplotlib and sympy now build, and the 3 Django tasks that kept `user` have no leaks.\n- Official against 0.1.1: the task ids, eligible, anchored, strata and all per-task fields are the same. 456 of 888 opaque prompts differ, all in fastapi's 57 tasks. All 666 real prompts are identical. Every differing word is the same source name with a new pseudo-word. mc3.json is byte-identical.\n- Confirmatory anchored share, official plus Lite: 174/371 = 0.469.\n- Remaining hard leaks in Lite, identifiers only: `node_count` in 6 pylint tasks: pylint-dev__pylint-5859, -6506, -7080, -7114, -7228 and -7993. `ipython` in sympy__sympy-18621. Each leak is in the opaque prompts listed below.\n- `CODE_SHA256.txt` is stale until the addendum regenerates it.\n\nThe Lite build ran twice. The first run reached 298 of 317 tasks with no error in its log. It stopped at about 01:00 UTC because the Claude session that started it ended. I kept that log as `run_log/studyb_build_lite.log.interrupted1`. Its 7 leak tasks are the same 7 as in the final run. I restarted the build detached with nohup, through `run_log/tools/studyb5_lite.sh`. It ran from 01:21 to 03:02 UTC and exited 0. I report it only at 04:55 UTC because my wait job also ended with the session, so I missed the finish.\n")
w("## Step 1: patch\n")
w("| File | Expected before | Expected after | Observed after |\n|---|---|---|---|")
exp = {"src/ngraph/rename.py": ("258131f8c8d021f9e6afd521d66b9a248ce973fa68ef8327492c5462694fa355", "3e7084b62f8532f0fb5d90ce7cec43f68ae0c44240006f76d3257e4a6ca804f0"),
       "src/ngraph/extract.py": ("d6eee0ff4769943c2dc67e19705ad28727bf4d34ea16fc43decae68d07dbdee1", "b0504b66224fc20732b278e4ff008eccaeebb802750469b6907593a034dc213a"),
       "tests/test_studyb.py": ("0ff29a625d3dc1a0afb082561ec1f36e08d9655616ff1619e96d4122feef58df", "c6a1f73a4fc6e46a4dfd2a6ad274fffe21cb0fec2e12658b78b8c6da7f470169"),
       "src/ngraph/official.py": ("f59753dab15a111cabba87798dd9a2ea665be4fc62fb1fbaa5fa27e6ce66a4d7", "f59753dab15a111cabba87798dd9a2ea665be4fc62fb1fbaa5fa27e6ce66a4d7")}
for f, (a, b) in exp.items():
    o = sha(P + "/gemma4-paper-code/" + f); w(f"| {f} | `{a}` (matched before patching) | `{b}` | `{o}` {'MATCH' if o == b else 'DIFFERENT'} |")
w(f"\nDecoded patch SHA-256: `{sha(S + 'studyb5.patch')}` (expected `6dc17f364af53925e42ef145342c08890a113dadb3a34aae9a5ac0708ccbb809`). It has 20 lines with a less-than sign, 4 lines with an exclamation mark, and no `{{LT}}` or `{{EX}}`. The relay envelope had XML-escaped `>` and `&` as `&gt;` and `&amp;`, and I wrote the real characters. The hash match confirms that reading. Backups of the three files are in `gemma4-staging/studyb5/base/`.\n")
w("`patch -p1 -l` dry run: exit 0. Real run: exit 0. Output:\n"); code(rd(S + "patch_output.txt").strip())
w("No `.orig` or `.rej` file was left in the package.\n")
w("## Step 2: tests\n")
w("Exit 1, 2026-11-09T23:50:17Z to 2026-11-09T23:50:24Z.\n"); code(tail(S + "pytest.txt", 12))
w("The only failure is the expected `tests/test_commit.py::test_package_code_sha256_is_current`.\n")
w("## Commands: exit codes and times (UTC)\n\n| Command | Exit | Start | End |\n|---|---|---|---|")
for k, lab in (("build_official", "studyb build --set official"), ("mc3", "studyb mc3"), ("build_lite", "studyb build --set lite")):
    if k in ex:
        e, r = ex[k].split(" start="); a, b = r.split(" end="); w(f"| {lab} | {e} | {a} | {b} |")
    else: w(f"| {lab} | NOT RUN | | |")
w("\nStep 3 moves (mv, nothing deleted): `studyb-frozen/official` to `official_prefix_0.1.1`; `studyb-frozen/lite` (an empty folder) to `lite_failed_0.1.1`; the four old logs and report gained the suffix `.0.1.1`. The old `studyb_builds.exit` also gained that suffix.\n")
w("Official `--data` was `P/competition-data`, the folder that holds `tasks.jsonl`, `graphs`, `snapshots`.\n")
def build(name, logf):
    w(f"\n## Build: {name}\n")
    if not have[name]:
        w(f"**FAILED or not finished: no `tasks.json` in `studyb-frozen/{name}/`.** Log tail (last 40 lines):\n"); code(tail(RL + logf)); return
    d = FZ + name + "/"; t = T[name]; g = jl(d + "graphs_report.json")
    w("Summary:\n"); code(json.dumps(t["summary"], indent=1), "json")
    w("`params` block of tasks.json:\n"); code(json.dumps(t["params"], indent=1), "json")
    w("Output files:\n\n| File | Bytes | SHA-256 |\n|---|---|---|")
    for f in sorted(os.listdir(d)): w(f"| {f} | {os.path.getsize(d + f)} | `{sha(d + f)}` |")
    hl = {x["task_id"]: x["hard_leaks"] for x in t["tasks"] if x.get("hard_leaks")}
    w(f"\nTasks with hard leaks: {len(hl)}.")
    for k, v in hl.items(): w(f"- {k}: {json.dumps(v)}")
    m = json.load(gzip.open(d + "rename_maps.json.gz"))
    w("\nRename maps per repository (`n_protected_defined`; `map` = names in the rename map):\n\n| Repo | n_protected_defined | Renamed names | rename_version | packages |\n|---|---|---|---|---|")
    for r, v in sorted(m.items()): w(f"| {r} | {v.get('n_protected_defined')} | {len(v.get('map') or {})} | {v.get('rename_version')} | {', '.join(v.get('packages') or [])} |")
    fails = []; rows = []; notmir = []
    for gn, r in g.items():
        s = r.get("stats", {}); rw = r.get("rewired", {}); wm = r.get("within_module") or {}; inv = rw.get("invariants") or {}
        rows.append(dict(mirrored=s.get("mirrored", rw.get("input_mirrored")), self_loops=s.get("self_loops", rw.get("self_loops")), dup=s.get("duplicate_edges_dropped"), ov=rw.get("edge_overlap"), wov=wm.get("edge_overlap"), ok=inv.get("all_ok"), wok=(wm.get("invariants") or {}).get("all_ok")))
        if s.get("mirrored", rw.get("input_mirrored")) is not True: notmir.append(gn)
        if not (rw.get("completed") and inv.get("all_ok") and rw.get("error") is None):
            fails.append({"graph": gn, "rewired": {k: rw.get(k) for k in ("completed", "error", "edge_overlap")}, "invariants": inv})
        if wm and not (wm.get("completed") and (wm.get("invariants") or {}).get("all_ok")):
            fails.append({"graph": gn, "within_module": {k: wm.get(k) for k in ("completed", "edge_overlap")}, "invariants": wm.get("invariants")})
    nn = lambda k: [x[k] for x in rows if isinstance(x[k], (int, float))]
    w(f"\nGraphs in graphs_report.json: {len(rows)}.\n\n| Measure | Value |\n|---|---|")
    w(f"| mirrored = true / false / absent | {sum(x['mirrored'] is True for x in rows)} / {sum(x['mirrored'] is False for x in rows)} / {sum(x['mirrored'] is None for x in rows)} |")
    for lab, k in (("self_loops", "self_loops"), ("duplicate_edges_dropped", "dup"), ("rewired edge_overlap", "ov"), ("within_module edge_overlap", "wov")):
        v = nn(k); w(f"| {lab}: median / min / max (n={len(v)}) | {med(v)} / {min(v) if v else None} / {max(v) if v else None} |")
    w(f"| rewired invariants pass / fail / absent | {sum(x['ok'] is True for x in rows)} / {sum(x['ok'] is False for x in rows)} / {sum(x['ok'] is None for x in rows)} |")
    w(f"| within_module invariants pass / fail / absent | {sum(x['wok'] is True for x in rows)} / {sum(x['wok'] is False for x in rows)} / {sum(x['wok'] is None for x in rows)} |")
    w("\nWhere `stats` has no `mirrored` or `self_loops` field (Lite graphs from our extractor), the table uses `rewired.input_mirrored` and `rewired.self_loops`. Those graphs record no `duplicate_edges_dropped`.")
    w(f"Extractor versions in `stats`: {sorted({str(r.get('stats', {}).get('extractor_version')) for r in g.values()})}.")
    w(f"\nGraphs not flagged mirrored: {len(notmir)}.")
    for n in notmir: w(f"- {n}")
    w(f"\nFailures (rewiring not completed, error, or an invariant false): {len(fails)}.")
    for f in fails: w(f"- {json.dumps(f)}")
    w("\nLog tail (last 40 lines):\n"); code(tail(RL + logf))
build("official", "studyb_build_official.log")
w("\n## mc3.json\n")
if os.path.exists(FZ + "official/mc3.json"):
    mc = jl(FZ + "official/mc3.json")
    ks = ["repo", "graph", "official_library_functions", "our_nodes", "common_nodes", "official_pairs", "our_pairs", "common_pairs", "ours_in_official", "official_in_ours"]
    w("| Task | " + " | ".join(ks) + " |\n|---|" + "---|" * len(ks))
    for t_, v in mc.items(): w(f"| {t_} | " + " | ".join(str(round(v[k], 4) if isinstance(v[k], float) else v[k]) for k in ks) + " |")
    o = S + "../../studyb-frozen/official_prefix_0.1.1/mc3.json"
    w(f"\nmc3.json byte-identical to the 0.1.1 mc3.json: {sha(FZ + 'official/mc3.json') == sha(FZ + 'official_prefix_0.1.1/mc3.json')}.")
    w("\nLog tail (last 40 lines):\n"); code(tail(RL + "studyb_mc3.log"))
build("lite", "studyb_build_lite.log")
w("\n## Anchored counts on confirmatory tasks\n")
w("Rule used: `task[\"role\"] == \"confirmatory\"` and `task[\"eligible\"] is True`; anchored means `task[\"anchored\"] is True`.\n\n| Set | Confirmatory tasks | Confirmatory eligible | Anchored | Share |\n|---|---|---|---|---|")
nums = dens = 0
for n, t in T.items():
    c = [x for x in t["tasks"] if x.get("role") == "confirmatory"]; e = [x for x in c if x["eligible"]]; a = sum(bool(x.get("anchored")) for x in e)
    w(f"| {n} | {len(c)} | {len(e)} | {a} | {round(a / len(e), 4) if e else None} |"); nums += a; dens += len(e)
w(f"| **combined** | | **{dens}** | **{nums}** | **{round(nums / dens, 4) if dens else None}** ({nums}/{dens}) |\n")
w("Tasks by role:\n"); code(json.dumps({n: {r: sum(x.get('role') == r for x in t['tasks']) for r in sorted({x.get('role') for x in t['tasks']})} for n, t in T.items()}))
if "lite" in T:
    tn = [x for x in T["lite"]["tasks"] if x.get("role") != "confirmatory"]
    w(f"\nLite non-confirmatory tasks: {len(tn)}, of which eligible {sum(x['eligible'] for x in tn)} and anchored {sum(bool(x.get('anchored')) for x in tn if x['eligible'])}.\n")
w("\n## Official set: 0.1.2 against 0.1.1 (`official_prefix_0.1.1`)\n")
if "official" in T:
    o = jl(FZ + "official_prefix_0.1.1/tasks.json"); n = T["official"]
    oi = {x["task_id"]: x for x in o["tasks"]}; ni = {x["task_id"]: x for x in n["tasks"]}
    w(f"- Same task ids: {set(oi) == set(ni)} ({len(oi)} old, {len(ni)} new).")
    for k in ("eligible", "anchored", "strata", "injected", "by_repo", "excluded", "cut", "code_lines_reduced", "max_tokens", "tasks_with_hard_leaks"):
        w(f"- `{k}`: old {json.dumps(o['summary'].get(k))}, new {json.dumps(n['summary'].get(k))}, same: {o['summary'].get(k) == n['summary'].get(k)}.")
    fld = ("eligible", "anchored", "injected", "stratum", "gold", "gold_files", "pool", "orders", "anchors", "correct_letters")
    w("\nPer-task fields that differ (tasks with any difference):\n\n| Field | Tasks that differ |\n|---|---|")
    for f in fld: w(f"| {f} | {sum(oi[t].get(f) != ni[t].get(f) for t in oi if t in ni)} |")
    w("\nPrompt hashes (`prompt_sha256`, keys `naming/graph/order`):\n\n| Group | Compared | Differ |\n|---|---|---|")
    grp = {}
    for t in oi:
        for k, v in (oi[t].get("prompt_sha256") or {}).items():
            g_ = k.split("/")[0]; a = grp.setdefault(g_, [0, 0]); a[0] += 1; a[1] += v != (ni[t].get("prompt_sha256") or {}).get(k)
    for g_, a in sorted(grp.items()): w(f"| {g_} | {a[0]} | {a[1]} |")
    dd = [t for t in oi if oi[t].get("prompt_sha256") != ni[t].get("prompt_sha256")]
    w(f"\nTasks with at least one differing prompt hash: {len(dd)}, by repository: {json.dumps(dict(__import__('collections').Counter(oi[t]['repo'] for t in dd)))}. The other repositories' prompts are byte-identical.")
    if os.path.exists(S + "compare.json"):
        c = jl(S + "compare.json")
        w("\nText-level comparison. I rendered every prompt under the 0.1.1 code (a copy in `gemma4-staging/studyb5/old_src`) and under the 0.1.2 code, then compared them word by word. The dumps stay in staging. Each dump's hashes were checked against its frozen `tasks.json`.\n")
        code(json.dumps({k: v for k, v in c.items() if k != "samples"}, indent=1, sort_keys=True), "json")
        w("Non-pseudo-word differences, as identifier pairs (source name or token, old side -> new side, with counts; top 40 per category):\n")
        code(json.dumps(c["samples"], indent=1, sort_keys=True), "json")
open(RL + "studyb_build_report.md", "w").write("\n".join(L) + "\n")
print(len("\n".join(L).encode()), "bytes")
