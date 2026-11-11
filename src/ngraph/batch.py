"""Generate Study A items for every repository in the manifest with Gemma 4's tokenizer.

    python -m ngraph.batch --manifest data/repos_manifest.json --graphs-dir data/graphs \\
        --tokenizer-gguf third_party/llama.cpp/ggml-vocab-gemma-4.gguf \\
        --out-dir <new folder> --summary <new file>

With the package's files this writes the 44 question files of data/items and data/items_summary.json again,
byte for byte (with the default --roles and --per-cell). One tokenizer instance (and its cache) is shared by
all repositories. Each graph's pinned commit must match the manifest. The run time per repository is
printed, not stored, so that the summary file can be reproduced.
"""

from __future__ import annotations

import argparse
import json
import os
import time

from .items import generate
from .tok import GemmaCounter


def summarise_items(res: dict) -> dict:
    n_comp = n_mis = 0
    for it in res["items"]:
        n_comp += len(it["neutral_map"])
        n_mis += len(it["neutral_token_mismatch"])
    return {"repo": res["repo"], "n_items": res["n_items"], "made_per_cell": res["made_per_cell"],
            "components": n_comp, "token_mismatched_components": n_mis}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Generate Study A items for the repositories in the manifest")
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--graphs-dir", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--tokenizer-gguf", required=True)
    ap.add_argument("--roles", default="confirmatory,pilot,reserve")
    ap.add_argument("--per-cell", type=int, default=5)
    ap.add_argument("--summary", required=True, help="JSON summary (kept outside --out-dir)")
    a = ap.parse_args(argv)
    roles = set(a.roles.split(","))
    with open(a.manifest) as fh:
        man = json.load(fh)
    counter = GemmaCounter(a.tokenizer_gguf)
    os.makedirs(a.out_dir, exist_ok=True)
    rows = []
    for r in man["repos"]:
        if r["role"] not in roles:
            continue
        with open(os.path.join(a.graphs_dir, r["label"] + ".json")) as fh:
            g = json.load(fh)
        if g["graph"]["commit"] != r["commit"]:
            raise SystemExit(f"{r['label']}: graph commit {g['graph']['commit']} != manifest {r['commit']}")
        t0 = time.time()
        res = generate(g, per_cell=a.per_cell, count_tokens=counter)
        with open(os.path.join(a.out_dir, r["label"] + ".json"), "w") as fh:
            json.dump(res, fh, indent=1)
        s = dict(summarise_items(res), group=r["group"], role=r["role"])
        rows.append(s)
        print(json.dumps(dict(s, secs=round(time.time() - t0, 1))), flush=True)
    out = {"tokenizer": counter.record(), "per_cell": a.per_cell, "roles": sorted(roles), "repos": rows,
           "total_items": sum(x["n_items"] for x in rows),
           "token_mismatched_components": sum(x["token_mismatched_components"] for x in rows),
           "components": sum(x["components"] for x in rows)}
    with open(a.summary, "w") as fh:
        json.dump(out, fh, indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != "repos"}))


if __name__ == "__main__":
    main()
