# Fetch SWE-bench Lite parquet files (pinned commit) and JSONL via the rows API. stdlib only; run with -I.
import datetime, hashlib, json, os, sys, time, urllib.parse, urllib.request
P = sys.argv[1]
DS = "princeton-nlp/SWE-bench_Lite"
UA = {"User-Agent": "research-data-fetch/1.0"}
now = lambda: datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
def get(url, tries=12):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
                return r.read(), r.geturl()
        except Exception as e:
            if i == tries - 1: raise
            print("retry", url, repr(e), flush=True); time.sleep(min(60, 2 ** (i + 1)))
meta = json.loads(get(f"https://huggingface.co/api/datasets/{DS}")[0])
sha = meta["sha"]
if meta.get("gated") or meta.get("private"): sys.exit(f"gated/private: {meta.get('gated')} {meta.get('private')}")
lite = os.path.join(P, "lite"); raw = os.path.join(lite, "raw"); os.makedirs(raw, exist_ok=True)
out = {"sha": sha, "gated": meta.get("gated"), "lastModified": meta.get("lastModified"), "license": meta.get("license"),
       "card_license": (meta.get("cardData") or {}).get("license"), "siblings": [s["rfilename"] for s in meta["siblings"]], "files": {}, "splits": {}}
for split in ("test", "dev"):
    name = f"{split}-00000-of-00001.parquet"
    url = f"https://huggingface.co/datasets/{DS}/resolve/{sha}/data/{name}"
    t = now(); b, final = get(url)
    with open(os.path.join(raw, name), "wb") as f: f.write(b)
    out["files"][name] = {"url": url, "bytes": len(b), "sha256": hashlib.sha256(b).hexdigest(), "utc": t, "starts_PAR1": b[:4] == b"PAR1", "ends_PAR1": b[-4:] == b"PAR1"}
q = urllib.parse.quote(DS, safe="")
base = "https://datasets-server.huggingface.co"
size = json.loads(get(f"{base}/size?dataset={q}")[0])
info = json.loads(get(f"{base}/info?dataset={q}&config=default")[0])
out["size_api"] = size.get("size", {}).get("splits")
out["info_splits"] = info.get("dataset_info", {}).get("splits")
out["info_features"] = info.get("dataset_info", {}).get("features")
out["partial"] = info.get("partial")
out["server_git_revision"] = (json.loads(get(f"{base}/parquet?dataset={q}")[0]).get("parquet_files") or [{}])[0].get("url")
bad = {}; all_rows = {}
for split in ("test", "dev"):
    rows = []; total = None; off = 0
    while total is None or off < total:
        d = json.loads(get(f"{base}/rows?dataset={q}&config=default&split={split}&offset={off}&length=100")[0])
        if total is None: total = d["num_rows_total"]; out["splits"][split] = {"num_rows_total": total, "num_rows_per_page": d.get("num_rows_per_page"), "partial": d.get("partial"), "features": [f["name"] for f in d["features"]]}
        elif d["num_rows_total"] != total: sys.exit("num_rows_total changed")
        if not d["rows"]: sys.exit(f"empty page at {off}")
        for r in d["rows"]:
            if r["row_idx"] != len(rows): sys.exit(f"row_idx gap at {len(rows)}: {r['row_idx']}")
            if r.get("truncated_cells"): bad.setdefault(split, []).append({"row_idx": r["row_idx"], "fields": r["truncated_cells"]})
            rows.append(r["row"])
        off += len(d["rows"]); print(split, off, "/", total, flush=True); time.sleep(0.3)
    all_rows[split] = rows
if bad:
    out["truncated"] = bad; json.dump(out, open(os.path.join(lite, "fetch_meta.json"), "w"), indent=1)
    print("TRUNCATED", json.dumps(bad)); sys.exit(3)
for split, rows in all_rows.items():
    p = os.path.join(lite, f"swebench_lite_{split}.jsonl")
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        for r in rows: f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(p, "rb") as f: b = f.read()
    n = b.count(b"\n")
    if n != out["splits"][split]["num_rows_total"]: sys.exit(f"{split}: wrote {n}")
    ids = [json.loads(l)["instance_id"] for l in b.decode().splitlines()]
    if len(set(ids)) != n: sys.exit(f"{split}: duplicate ids")
    by = {}
    for r in rows: by[r["repo"]] = by.get(r["repo"], 0) + 1
    out["splits"][split].update(jsonl_lines=n, jsonl_bytes=len(b), jsonl_sha256=hashlib.sha256(b).hexdigest(), by_repo=dict(sorted(by.items())), field_sets=sorted({tuple(r) for r in map(lambda x: list(x), rows)}))
out["fetched_utc"] = now()
json.dump(out, open(os.path.join(lite, "fetch_meta.json"), "w"), indent=1)
print("OK")
