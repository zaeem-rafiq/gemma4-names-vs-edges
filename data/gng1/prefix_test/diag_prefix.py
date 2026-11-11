"""GNG-1 diagnostic, outside the package: letter mass on the pilot prompts of the smoke test
(same 40 A-D and 40 A-J prompts) when the model turn is pre-filled with an answer prefix.
Reads the package code and data read-only; writes only next to this file."""
import gc
import json
import os
import random
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.dirname(HERE)
PKG = os.path.join(P, "gemma4-paper-code")
sys.path.insert(0, os.path.join(PKG, "src"))
from ngraph import runner as rn  # noqa: E402

MODELS = [("E2B", "gemma-4-E2B_q4_0-it.gguf"), ("E4B", "gemma-4-E4B_q4_0-it.gguf"),
          ("12B", "gemma-4-12b-it-qat-q4_0.gguf")]
PREFIXES = [("none", ""), ("answer_colon", "Answer:"), ("correct_option_is", "The correct option is")]


def prompts():
    man = json.load(open(os.path.join(PKG, "data", "repos_manifest.json")))
    pilots = {r["label"] for r in man["repos"] if r["role"] == "pilot"}
    items = rn.load_items(os.path.join(PKG, "data", "items"), pilots)
    rng = random.Random(0)  # as in runner.smoke (seed 0, n 40)
    pick = rng.sample(items, min(40, len(items)))
    ad = [{"text": it["versions"]["G1"]["text"], "correct_letter": it["versions"]["G1"]["correct"]} for it in pick]
    aj = rn.ten_option_prompts(items, 40, 0)
    return sorted(pilots), ad, aj


def score(scorer, text, letters, prefix):
    prompt = scorer.render(text) + prefix
    toks = scorer.tokenize(prompt, special=True)
    if toks[0] != scorer.bos_id or toks.count(scorer.bos_id) != 1:
        raise RuntimeError("BOS check failed")
    logits = scorer.next_logits(toks)
    return rn.summarise(logits, scorer.letter_ids(letters), scorer._token_text, len(toks), 0.0, top_k=10,
                        watch_ids=scorer.watch_ids), toks


def summary(rows, letter_texts):
    masses = [r["letter_mass"] for r in rows]
    other = {}
    for r in rows:
        for tok, p in r["top"]:
            if tok not in letter_texts:
                other[tok] = other.get(tok, 0.0) + p / len(rows)
    ch = [r["p_watch"].get(rn.CHANNEL_TOKEN) for r in rows if r.get("p_watch")]
    return {"n": len(rows), "share_mass_ge_0.9": float(np.mean([m >= 0.9 for m in masses])),
            "mean_mass": float(np.mean(masses)), "min_mass": float(min(masses)),
            "accuracy": float(np.mean([r["correct"] for r in rows])),
            "p_channel_mean": float(np.mean(ch)) if ch else None,
            "top_other_tokens": sorted(([t, round(p, 4)] for t, p in other.items()), key=lambda x: -x[1])[:6]}


def main():
    pilots, ad, aj = prompts()
    out = {"pilots": pilots, "n_AD": len(ad), "n_AJ": len(aj), "prefixes": dict(PREFIXES), "models": {}}
    for tag, fname in MODELS:
        path = os.path.join(P, "models", fname)
        own = rn.thought_mode_for(tag)
        scorer = rn.LetterScorer(path, n_ctx=4096, thought_block=own)
        res = {"own_setting": own, "settings": {}, "tail_tokens": {}}
        for mode in (own, "on" if own == "off" else "off"):
            scorer.thought_block = mode
            res["settings"][mode] = {}
            for pname, prefix in PREFIXES:
                t0 = time.time()
                block = {}
                for set_name, prs, letters in (("AD", ad, rn.LETTERS4), ("AJ", aj, rn.LETTERS10)):
                    rows = []
                    for p in prs:
                        r, toks = score(scorer, p["text"], letters, prefix)
                        r["correct"] = int(r["pred_letter"] == p["correct_letter"])
                        rows.append(r)
                    if set_name == "AD" and mode == own:
                        res["tail_tokens"][pname] = [scorer._token_text(t) for t in toks[-8:]]
                    texts = {v for L in letters for v in (L, " " + L)}
                    block[set_name] = summary(rows, texts)
                block["passes"] = bool(block["AD"]["share_mass_ge_0.9"] >= 0.95 and block["AJ"]["share_mass_ge_0.9"] >= 0.95)
                block["secs"] = round(time.time() - t0, 1)
                res["settings"][mode][pname] = block
                print(tag, mode, pname, "passes" if block["passes"] else "fails",
                      "AD", round(block["AD"]["share_mass_ge_0.9"], 3), round(block["AD"]["mean_mass"], 3),
                      "AJ", round(block["AJ"]["share_mass_ge_0.9"], 3), round(block["AJ"]["mean_mass"], 3),
                      "top other AD:", block["AD"]["top_other_tokens"][:3], flush=True)
        out["models"][tag] = res
        del scorer
        gc.collect()
    with open(os.path.join(HERE, "diag_prefix_results.json"), "w") as fh:
        json.dump(out, fh, indent=1)


if __name__ == "__main__":
    main()
