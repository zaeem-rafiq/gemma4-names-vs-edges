# For each task's base_commit, check the commit exists in its clone; one fetch attempt if missing.
import json, os, shutil, subprocess, sys
P = sys.argv[1]; repos = os.path.join(P, "lite-repos"); env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
tasks = []
for s in ("test", "dev"):
    with open(os.path.join(P, "lite", f"swebench_lite_{s}.jsonl"), encoding="utf-8") as f:
        for l in f:
            t = json.loads(l); tasks.append((s, t["instance_id"], t["repo"], t["base_commit"]))
has = lambda d, sha: subprocess.run(["git", "-C", d, "cat-file", "-e", sha + "^{commit}"], capture_output=True, env=env).returncode == 0
res = {}; missing = []
for s, iid, repo, sha in tasks:
    if repo == "psf/requests": continue
    d = os.path.join(repos, repo.replace("/", "__"))
    r = res.setdefault(repo, {"test": 0, "dev": 0, "found": 0, "missing": 0, "fetched": 0})
    r[s] += 1
    ok = has(d, sha)
    if not ok:
        p = subprocess.run(["git", "-C", d, "fetch", "origin", sha], capture_output=True, text=True, env=env)
        ok = has(d, sha); missing.append({"id": iid, "sha": sha, "fetch_exit": p.returncode, "after_fetch": ok, "stderr_tail": p.stderr[-300:]})
        if ok: r["fetched"] += 1
    r["found" if ok else "missing"] += 1
for repo, r in res.items():
    d = os.path.join(repos, repo.replace("/", "__"))
    r["size_kb"] = int(subprocess.run(["du", "-sk", d], capture_output=True, text=True).stdout.split()[0])
out = {"repos": dict(sorted(res.items())), "missing_events": missing, "total_kb": int(subprocess.run(["du", "-sk", repos], capture_output=True, text=True).stdout.split()[0]),
       "free": subprocess.run(["df", "-h", P], capture_output=True, text=True).stdout.splitlines()[-1]}
json.dump(out, open(os.path.join(P, "run_log", "studyb_commits.json"), "w"), indent=1)
print(json.dumps(out, indent=1))
