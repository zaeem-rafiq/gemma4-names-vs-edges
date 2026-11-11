"""Study A item generator: counterfactual call-graph questions in five versions.

Question types
  QT-A (one hop, reverse lookup): "Which of the following functions calls Y?"
  QT-B (two hops):                "X calls a function that in turn calls which option?"

Options (four, all shown in the subgraph)
  QT-A: the answer B (a caller of Y); a direction trap (a callee of Y that does not
        call Y) when one exists; the non-caller whose name is most similar to Y's;
        and the swap partner C (a random non-caller within 3 hops of Y that has an
        out-edge C->Z usable for the swap).
  QT-B: the answer B (reachable from X by exactly one two-step path X->M->B, and not
        called by X directly); a hop trap (a direct callee of X that is not two steps
        away) when one exists; the most name-similar non-answer; and the swap partner C.
  If a trap does not exist, a random non-answer fills the fourth slot.

Versions (identical option set; only the correct letter can move)
  G0  no graph                      correct = B
  G1  true edges, real names        correct = B
  G2  true edges, neutral names     correct = B
  G3  one swap, real names          correct = C
  G4  one swap, neutral names       correct = C

The swap is a degree-preserving double-edge swap inside the shown subgraph:
  QT-A: B->Y, C->Z  become  C->Y, B->Z
  QT-B: M->B, P->C  become  M->C, P->B   (P is not called by X)
In the rendered text the replaced target keeps its position in the line, so G1 and
G3 differ in exactly two edge targets.

Subgraph: the focal node, the options and the swap endpoints, then breadth-first
expansion (undirected, up to 4 hops, layer order shuffled by seed), then nodes of
the focal node's module, until `target` nodes. Items that cannot reach the target
are ineligible at that size. Edges shown are the induced edges of the full graph.

Distractors are checked against the FULL graph (not only the shown part), so the
"true" versions never contradict the real code.
"""

from __future__ import annotations

import difflib
import hashlib
import json
import random
from collections import Counter

from .names import (STD_DUNDERS, WHOLE_WORD_BLOCKED, NeutralNamer, approx_token_count, offensive,
                    split_subtokens)

SEED = 20261108
GENERATOR_VERSION = "0.4.0"

HEADER = ("Below is part of the static call graph of the Python repository {repo}. "
          "Each line \"F -> G, H\" means that function F calls functions G and H. "
          "\"F -> (none)\" means that F calls none of the functions shown.")
Q_A = "Question: According to this call graph, which of the following functions calls {focal}?"
Q_B = ("Question: According to this call graph, {focal} calls a function that in turn "
       "calls which of the following functions?")
G0_HEADER = "Question about the Python repository {repo}."
G0_Q_A = "Question: Which of the following functions calls {focal}?"
G0_Q_B = "Question: {focal} calls a function that in turn calls which of the following functions?"
FOOTER = "Answer with the letter of the correct option only."
LETTERS = "ABCD"
PARITY_TOL = 2      # tokens; |tokens(G2) - tokens(G1)| target for each item
PARITY_TRIES = 900  # single sub-token re-draws per item (the last two thirds with freer lengths)
OFFENSIVE_RETRIES = 20  # new naming attempts for a question with an offensive name (see offensive_naming)


def _pkg_version(name: str) -> str:
    try:
        from importlib.metadata import version

        return version(name)
    except Exception:  # noqa: BLE001
        return "unknown"


def stable_seed(*parts) -> int:
    return int(hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()[:12], 16)


class Graph:
    def __init__(self, g: dict, links_key: str = "links"):
        self.nodes = sorted(n["id"] for n in g["nodes"])
        self.meta = {n["id"]: n for n in g["nodes"]}
        self.out = {n: set() for n in self.nodes}
        self.inn = {n: set() for n in self.nodes}
        for e in g[links_key]:
            s, t = e["source"], e["target"]
            if s == t or s not in self.out or t not in self.out:
                continue
            self.out[s].add(t)
            self.inn[t].add(s)
        self.repo = g["graph"].get("repo")
        self.commit = g["graph"].get("commit")

    def und(self, n):
        return self.out[n] | self.inn[n]

    def r2(self, x) -> set:
        s = set()
        for m in self.out[x]:
            s |= self.out[m]
        return s

    def ball(self, center, hops: int) -> set:
        seen, frontier = {center}, {center}
        for _ in range(hops):
            nxt = set()
            for u in frontier:
                nxt |= self.und(u)
            nxt -= seen
            seen |= nxt
            frontier = nxt
        return seen


def label(qname: str) -> str:
    parts = qname.split(".")
    for p in reversed(parts):
        if not (p.startswith("__") and p.endswith("__")):
            return p
    return parts[-1]


def name_sim(a: str, b: str) -> float:
    la, lb = label(a), label(b)
    ta, tb = set(split_subtokens(la)), set(split_subtokens(lb))
    jac = len(ta & tb) / len(ta | tb) if (ta | tb) else 0.0
    return jac + difflib.SequenceMatcher(None, la.lower(), lb.lower()).ratio()


def expand(G: Graph, center: str, core: list, target: int, rng: random.Random, max_hops: int = 4) -> list:
    S = list(dict.fromkeys(core))
    have = set(S)
    seen, frontier = {center}, {center}
    for _ in range(max_hops):
        if len(S) >= target:
            break
        nxt = set()
        for u in frontier:
            nxt |= G.und(u)
        nxt -= seen
        seen |= nxt
        layer = sorted(nxt)
        rng.shuffle(layer)
        for v in layer:
            if len(S) >= target:
                break
            if v not in have:
                S.append(v)
                have.add(v)
        frontier = nxt
    if len(S) < target:
        mod = G.meta[center]["module"]
        same = sorted(n for n in G.nodes if G.meta[n]["module"] == mod and n not in have)
        rng.shuffle(same)
        for v in same:
            if len(S) >= target:
                break
            S.append(v)
            have.add(v)
    return S


def induced(G: Graph, S: list) -> set:
    Sset = set(S)
    return {(s, t) for s in S for t in G.out[s] if t in Sset}


def callers_among(edges: set, focal: str, options: list) -> set:
    return {o for o in options if (o, focal) in edges}


def two_step_among(edges: set, focal: str, options: list) -> set:
    out = {}
    for s, t in edges:
        out.setdefault(s, set()).add(t)
    reach = set()
    for m in out.get(focal, ()):
        reach |= out.get(m, set())
    return {o for o in options if o in reach}


def correct_set(qtype: str, edges: set, focal: str, options: list) -> set:
    return callers_among(edges, focal, options) if qtype == "A" else two_step_among(edges, focal, options)


# --------------------------------------------------------------- candidates
def try_qta(G: Graph, Y: str, B: str, rng: random.Random, target: int):
    callers = G.inn[Y]
    traps = sorted(d for d in G.out[Y] if d not in callers and d not in (B, Y))
    D_trap = rng.choice(traps) if traps else None
    c_cands = []
    for C in sorted(G.ball(Y, 3)):
        if C in callers or C in (Y, B, D_trap):
            continue
        zs = sorted(z for z in G.out[C] if z not in (Y, B, C) and z not in G.out[B])
        if zs:
            c_cands.append((C, zs))
    if not c_cands:
        return None
    C, zs = rng.choice(c_cands)
    Z = rng.choice(zs)
    pool = [d for d in G.nodes if d not in callers and d not in (Y, B, C, D_trap)]
    if not pool:
        return None
    D_lex = max(pool, key=lambda d: name_sim(d, Y))
    options = [B, D_lex, C]
    roles = {B: "answer", D_lex: "lexical", C: "swap_partner"}
    if D_trap:
        options.append(D_trap)
        roles[D_trap] = "direction_trap"
    else:
        extra = sorted(d for d in pool if d != D_lex)
        if not extra:
            return None
        R = rng.choice(extra)
        options.append(R)
        roles[R] = "random"
    swap = {"remove": [[B, Y], [C, Z]], "add": [[C, Y], [B, Z]]}
    core = [Y, B, C, Z] + options
    return dict(qtype="A", focal=Y, answer_true=B, answer_swapped=C, options=options,
                roles=roles, swap=swap, core=core)


def try_qtb(G: Graph, X: str, M: str, B: str, rng: random.Random, target: int):
    if B == X or B in G.out[X] or M == B:
        return None
    via = [m for m in G.out[X] if B in G.out[m]]
    if via != [M]:
        return None
    R2 = G.r2(X)
    hop_traps = sorted(d for d in G.out[X] if d not in R2 and d not in (X, B, M))
    D_hop = rng.choice(hop_traps) if hop_traps else None
    c_cands = []
    for C in sorted(G.ball(X, 3)):
        if C in R2 or C in (X, M, B, D_hop) or C in G.out[X]:
            continue
        ps = sorted(p for p in G.inn[C]
                    if p not in G.out[X] and p not in (X, B, M, C) and B not in G.out[p])
        if ps:
            c_cands.append((C, ps))
    if not c_cands:
        return None
    C, ps = rng.choice(c_cands)
    P = rng.choice(ps)
    excluded = R2 | G.out[X] | {X, B, C, M, D_hop}
    pool = [d for d in G.nodes if d not in excluded]
    if not pool:
        return None
    D_lex = max(pool, key=lambda d: name_sim(d, X))
    options = [B, D_lex, C]
    roles = {B: "answer", D_lex: "lexical", C: "swap_partner"}
    if D_hop:
        options.append(D_hop)
        roles[D_hop] = "hop_trap"
    else:
        extra = sorted(d for d in pool if d != D_lex)
        if not extra:
            return None
        R = rng.choice(extra)
        options.append(R)
        roles[R] = "random"
    swap = {"remove": [[M, B], [P, C]], "add": [[M, C], [P, B]], "via": M, "p": P}
    core = [X, M, B, C, P] + options
    return dict(qtype="B", focal=X, answer_true=B, answer_swapped=C, options=options,
                roles=roles, swap=swap, core=core)


# ---------------------------------------------------------------- rendering
def render_lines(S: list, edges: set, line_order: list, target_order: dict, rename=lambda q: q) -> str:
    out_map = {}
    for s, t in edges:
        out_map.setdefault(s, set()).add(t)
    lines = []
    for s in line_order:
        ts = [t for t in target_order[s] if t in out_map.get(s, set())]
        lines.append(f"{rename(s)} -> {', '.join(rename(t) for t in ts) if ts else '(none)'}")
    return "\n".join(lines)


TWO_LETTER_ZIPF = 4.5


def common_word_filter(zipf_min: float = 3.0, zipf_min_two_letters: float = TWO_LETTER_ZIPF):
    """Predicate: True for strings that are common English words (wordfreq Zipf >= zipf_min).
    Two-letter strings use a higher bar: in wordfreq 3.1.1 all but 7 of the 140 consonant-vowel
    and vowel-consonant pairs reach Zipf 3 (abbreviations and fragments), so Zipf 3 would leave
    almost no two-letter pseudo-words; Zipf 4.5 still rejects to, of, in, is, be, go, no, re, id, ma
    and the like. wordfreq is a required dependency for item generation (no silent fallback)."""
    import functools

    from wordfreq import zipf_frequency

    @functools.lru_cache(maxsize=None)
    def is_common(w: str) -> bool:
        return zipf_frequency(w, "en") >= (zipf_min_two_letters if len(w) == 2 else zipf_min)

    return is_common


def build_versions(item: dict, G: Graph, rng: random.Random, count_tokens=approx_token_count, reject=None) -> dict:
    S, focal, qtype = item["nodes"], item["focal"], item["qtype"]
    true_edges = {tuple(e) for e in item["edges_true"]}
    sw_edges = {tuple(e) for e in item["edges_swapped"]}
    # line order and per-line target order are fixed per item and shared by all versions
    line_order = list(S)
    rng.shuffle(line_order)
    target_order = {}
    for s in S:
        ts = sorted({t for (a, t) in true_edges if a == s})
        rng.shuffle(ts)
        target_order[s] = ts
    # in-place replacement for the swapped targets
    swapped_target_order = {s: list(v) for s, v in target_order.items()}
    for (a, old), (a2, new) in zip(item["swap"]["remove"], _paired_adds(item)):
        assert a == a2
        lst = swapped_target_order[a]
        lst[lst.index(old)] = new
    forbidden = set(split_subtokens(G.repo or ""))
    for q in S:
        for c in q.split("."):
            forbidden |= set(split_subtokens(c))

    def text(graph_txt, repo_name, rename, with_graph, opts):
        f = rename(focal)
        if with_graph:
            head = HEADER.format(repo=repo_name)
            q = (Q_A if qtype == "A" else Q_B).format(focal=f)
            body = f"{head}\n\n{graph_txt}\n\n{q}"
        else:
            head = G0_HEADER.format(repo=repo_name)
            q = (G0_Q_A if qtype == "A" else G0_Q_B).format(focal=f)
            body = f"{head}\n\n{q}"
        opt_lines = "\n".join(f"{LETTERS[i]}. {rename(o)}" for i, o in enumerate(opts))
        return f"{body}\n{opt_lines}\n\n{FOOTER}"

    ident = lambda q: q  # noqa: E731
    ntok = getattr(count_tokens, "uncached", count_tokens)
    opts1 = [item["options"][i] for i in item["perm"]]
    n_g1 = ntok(text(render_lines(S, true_edges, line_order, target_order, ident), G.repo, ident, True, opts1))
    g1_text = text(render_lines(S, true_edges, line_order, target_order, ident), G.repo, ident, True, opts1)

    # Neutral names, then prompt-level token parity. If the finished names contain an offensive substring
    # (names.OFFENSIVE_SUBSTRINGS) or a pseudo-word in names.WHOLE_WORD_BLOCKED, both steps are redone with
    # the next seeds; attempt 0 uses the original seeds, so a question whose names are clean is exactly as
    # before.
    for attempt in range(OFFENSIVE_RETRIES + 1):
        extra = (attempt,) if attempt else ()
        namer = NeutralNamer(stable_seed(SEED, "neutral", item["item_id"], *extra), count_tokens, forbidden,
                             reject=reject)
        namer.fit([c for q in S for c in q.split(".")] + [NeutralNamer.handle_component(G.repo or "repo")])

        # prompt-level token parity: names are matched per name part above, but in context the
        # tokenizer merges across dots, so re-draw single sub-tokens while |tokens(G2) - tokens(G1)|
        # falls (option order 1), until it is at most PARITY_TOL or PARITY_TRIES draws are used
        def parity_gap():
            neut_ = namer.neutral_qname
            g2 = text(render_lines(S, true_edges, line_order, target_order, neut_),
                      namer.neutral_handle(G.repo or "repo"), neut_, True, opts1)
            return ntok(g2) - n_g1

        gap0 = gap = parity_gap()
        prng = random.Random(stable_seed(SEED, "parity", item["item_id"], *extra))
        subs = sorted(namer.sub_map)
        # draw sub-tokens in proportion to how often they appear in the G1 text
        weight = {t: 0 for t in subs}
        for c in namer.map:
            if c in namer._shapes:
                k = g1_text.count(c)
                for t in set(namer._subs(c)):
                    weight[t] = weight.get(t, 0) + k
        wts = [weight[t] + 1 for t in subs]
        tries = 0
        while abs(gap) > PARITY_TOL and tries < PARITY_TRIES and subs:
            tries += 1
            t = prng.choices(subs, wts)[0]
            old_w, w = namer.sub_map[t], namer.propose(t, wide=tries > PARITY_TRIES // 3)
            if w is None or not namer.set_sub(t, w):
                continue
            new_gap = parity_gap()
            if abs(new_gap) < abs(gap):
                gap = new_gap
            else:
                assert namer.set_sub(t, old_w)
        if not offensive_naming(namer, G.repo or "repo"):
            break
    else:
        raise RuntimeError(f"{item['item_id']}: every naming attempt left an offensive name")
    handle = namer.neutral_handle(G.repo or "repo")
    neut = namer.neutral_qname
    g_true_real = render_lines(S, true_edges, line_order, target_order, ident)
    g_true_neut = render_lines(S, true_edges, line_order, target_order, neut)
    g_sw_real = render_lines(S, sw_edges, line_order, swapped_target_order, ident)
    g_sw_neut = render_lines(S, sw_edges, line_order, swapped_target_order, neut)
    def render_all(perm):
        opts = [item["options"][i] for i in perm]
        letter = {o: LETTERS[i] for i, o in enumerate(opts)}
        return letter, {
            "G0": {"text": text(None, G.repo, ident, False, opts), "correct": letter[item["answer_true"]]},
            "G1": {"text": text(g_true_real, G.repo, ident, True, opts), "correct": letter[item["answer_true"]]},
            "G2": {"text": text(g_true_neut, handle, neut, True, opts), "correct": letter[item["answer_true"]]},
            "G3": {"text": text(g_sw_real, G.repo, ident, True, opts), "correct": letter[item["answer_swapped"]]},
            "G4": {"text": text(g_sw_neut, handle, neut, True, opts), "correct": letter[item["answer_swapped"]]},
        }

    letter, versions = render_all(item["perm"])
    letter2, versions_perm2 = render_all(item["perm2"])
    return {
        "versions": versions,
        "versions_perm2": versions_perm2,
        "option_letters_perm2": letter2,
        "line_order": line_order,
        "neutral_map": dict(namer.map),
        "neutral_subtoken_map": dict(namer.sub_map),
        "neutral_repo": handle,
        "neutral_token_mismatch": {k: list(v) for k, v in namer.mismatch.items()},
        "neutral_widened": dict(namer.widened),
        "token_parity": {"G2_minus_G1_before": gap0, "G2_minus_G1": gap, "draws": tries,
                         "G4_minus_G3": ntok(versions["G4"]["text"]) - ntok(versions["G3"]["text"])},
        "option_letters": letter,
        **({"neutral_naming_attempt": attempt} if attempt else {}),
    }


def offensive_naming(namer: NeutralNamer, repo: str) -> bool:
    """True if a pseudo-word, a new name or the neutral repository handle of `namer` contains one of
    names.OFFENSIVE_SUBSTRINGS, or a pseudo-word equals one of names.WHOLE_WORD_BLOCKED (in lower case)."""
    return (any(offensive(w) or w.lower() in WHOLE_WORD_BLOCKED for w in namer.sub_map.values())
            or any(offensive(new) for real, new in namer.map.items() if real not in STD_DUNDERS)
            or offensive(namer.neutral_handle(repo)))


def _paired_adds(item):
    """Pair each removed edge with the added edge that starts at the same node."""
    adds = {tuple(a)[0]: tuple(a) for a in item["swap"]["add"]}
    return [adds[r[0]] for r in item["swap"]["remove"]]


# ------------------------------------------------------------------ driver
def finalize(G: Graph, cand: dict, target: int, rng: random.Random):
    S = expand(G, cand["focal"], cand["core"], target, rng)
    if len(S) != target:
        return None
    true_edges = induced(G, S)
    rem = {tuple(e) for e in cand["swap"]["remove"]}
    add = {tuple(e) for e in cand["swap"]["add"]}
    if not rem <= true_edges or add & true_edges:
        return None
    sw_edges = (true_edges - rem) | add
    opts = cand["options"]
    if correct_set(cand["qtype"], true_edges, cand["focal"], opts) != {cand["answer_true"]}:
        return None
    if correct_set(cand["qtype"], sw_edges, cand["focal"], opts) != {cand["answer_swapped"]}:
        return None
    item = {k: v for k, v in cand.items() if k != "core"}
    item["nodes"] = S
    item["edges_true"] = sorted(list(e) for e in true_edges)
    item["edges_swapped"] = sorted(list(e) for e in sw_edges)
    return item


def generate(graph_json: dict, per_cell: int = 5, sizes=(12, 24), count_tokens=approx_token_count,
             links_key: str = "links", seed: int = SEED, common_word_zipf: float | None = 3.0) -> dict:
    G = Graph(graph_json, links_key)
    reject = common_word_filter(common_word_zipf) if common_word_zipf is not None else None
    repo = G.repo
    rng = random.Random(stable_seed(seed, repo, "candidates"))
    qa = [(y, b) for y in G.nodes for b in sorted(G.inn[y])]
    rng.shuffle(qa)
    qb = []
    for x in G.nodes:
        for m in sorted(G.out[x]):
            for b in sorted(G.out[m]):
                qb.append((x, m, b))
    rng.shuffle(qb)
    used_focal = set()
    items, eligible = [], Counter()
    for qtype, cands in (("A", qa), ("B", qb)):
        for size in sizes:
            made = 0
            for tup in cands:
                if made >= per_cell:
                    break
                focal = tup[0]
                if focal in used_focal:
                    continue
                r = random.Random(stable_seed(seed, repo, qtype, size, *tup))
                cand = try_qta(G, *tup, r, size) if qtype == "A" else try_qtb(G, *tup, r, size)
                if cand is None:
                    continue
                item = finalize(G, cand, size, r)
                if item is None:
                    continue
                used_focal.add(focal)
                idx = len(items)
                item["item_id"] = f"{repo}/{qtype}/S{size}/{idx:03d}"
                item["repo"], item["commit"], item["size_target"] = repo, G.commit, size
                perm = list(range(4))
                random.Random(stable_seed(seed, item["item_id"], "perm1")).shuffle(perm)
                perm2 = list(range(4))
                random.Random(stable_seed(seed, item["item_id"], "perm2")).shuffle(perm2)
                item["perm"], item["perm2"] = perm, perm2
                names_pick = max(item["options"], key=lambda o: name_sim(o, item["focal"]))
                item["name_match_pick"] = names_pick
                item["name_solvable_true"] = names_pick == item["answer_true"]
                item["name_solvable_swapped"] = names_pick == item["answer_swapped"]
                item.update(build_versions(item, G, random.Random(stable_seed(seed, item["item_id"], "render")),
                                           count_tokens, reject))
                items.append(item)
                made += 1
            eligible[(qtype, size)] = made
    return {
        "repo": repo,
        "commit": G.commit,
        "generator_version": GENERATOR_VERSION,
        "seed": seed,
        "token_counter": getattr(count_tokens, "__name__", "custom"),
        "token_counter_file": count_tokens.record() if hasattr(count_tokens, "record") else None,
        "common_word_filter": None if common_word_zipf is None else {
            "source": "wordfreq " + _pkg_version("wordfreq"), "lang": "en", "zipf_min": common_word_zipf,
            "zipf_min_two_letters": TWO_LETTER_ZIPF},
        "n_items": len(items),
        "made_per_cell": {f"{k[0]}-S{k[1]}": v for k, v in eligible.items()},
        "items": items,
    }


def eligibility_counts(graph_json: dict, sizes=(12, 24), links_key: str = "links", seed: int = SEED,
                       max_per_focal: int = 3) -> dict:
    """Number of distinct focal nodes for which at least one valid item exists, per type and size."""
    G = Graph(graph_json, links_key)
    out = {}
    for size in sizes:
        okA = set()
        for y in G.nodes:
            for b in sorted(G.inn[y])[:max_per_focal]:
                r = random.Random(stable_seed(seed, "elig", y, b, size))
                c = try_qta(G, y, b, r, size)
                if c and finalize(G, c, size, r):
                    okA.add(y)
                    break
        okB = set()
        for x in G.nodes:
            done = False
            for m in sorted(G.out[x])[:max_per_focal]:
                for b in sorted(G.out[m])[:max_per_focal]:
                    r = random.Random(stable_seed(seed, "elig", x, m, b, size))
                    c = try_qtb(G, x, m, b, r, size)
                    if c and finalize(G, c, size, r):
                        okB.add(x)
                        done = True
                        break
                if done:
                    break
        out[f"A-S{size}"] = len(okA)
        out[f"B-S{size}"] = len(okB)
    return out


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Generate Study A items from an extracted graph")
    ap.add_argument("graph")
    ap.add_argument("--out", required=True)
    ap.add_argument("--per-cell", type=int, default=5)
    ap.add_argument("--eligibility", action="store_true")
    ap.add_argument("--tokenizer-gguf", help="match neutral-name token counts with this GGUF's tokenizer "
                                             "(needs llama-cpp-python); default is the rough stand-in counter")
    a = ap.parse_args()
    g = json.load(open(a.graph))
    if a.eligibility:
        print(json.dumps({"repo": g["graph"]["repo"], **eligibility_counts(g)}))
    counter = approx_token_count
    if a.tokenizer_gguf:
        from .tok import GemmaCounter
        counter = GemmaCounter(a.tokenizer_gguf)
    res = generate(g, per_cell=a.per_cell, count_tokens=counter)
    with open(a.out, "w") as fh:
        json.dump(res, fh, indent=1)
    print(f"{res['repo']}: {res['n_items']} items {res['made_per_cell']}")
