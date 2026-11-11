"""Tests for the letter-logit runner that need no model weights.

The tokenizer tests need llama-cpp-python and the Gemma 4 vocab GGUF; point
NGRAPH_TOKENIZER_GGUF at that file (they are skipped otherwise).
"""

import hashlib
import json
import os

import numpy as np
import pytest

from ngraph import runner as rn

VOCAB = os.environ.get("NGRAPH_TOKENIZER_GGUF", "")
needs_vocab = pytest.mark.skipif(not (VOCAB and os.path.exists(VOCAB)),
                                 reason="set NGRAPH_TOKENIZER_GGUF to the Gemma 4 vocab GGUF")


def test_thought_block_modes():
    head = "<bos><|turn>user\nQ<turn|>\n<|turn>model\n"
    with_block = head + rn.THOUGHT_BLOCK
    assert rn.apply_thought_block(with_block, "off") == head
    assert rn.apply_thought_block(head, "off") == head
    assert rn.apply_thought_block(head, "on") == with_block
    assert rn.apply_thought_block(with_block, "on") == with_block
    assert rn.apply_thought_block(with_block, "template") == with_block
    with pytest.raises(ValueError):
        rn.apply_thought_block(head, "maybe")
    assert rn.thought_mode_for("E2B") == "off" and rn.thought_mode_for("e4b") == "off"
    assert rn.thought_mode_for("12B") == "on" and rn.thought_mode_for("31B") == "on"
    assert rn.thought_mode_for("E2B", "template") == "template"


def test_summarise_combines_space_variants():
    logits = np.full(30, -6.0)
    logits[[3, 10]] = [2.0, 0.5]   # A, " A"
    logits[[4, 11]] = [1.0, 1.2]   # B, " B"
    logits[20] = 3.0               # a non-letter token
    ids = {"A": [3, 10], "B": [4, 11], "C": [5, 12], "D": [6, 13]}
    out = rn.summarise(logits, ids, lambda t: f"t{t}", 100, 0.1, top_k=3)
    lse = rn._logsumexp(logits)
    assert out["logit_A"] == pytest.approx(np.log(np.exp(2.0) + np.exp(0.5)))
    assert out["logit_B"] == pytest.approx(np.log(np.exp(1.0) + np.exp(1.2)))
    assert out["pred_letter"] == "A"
    expected_mass = sum(np.exp(logits[i] - lse) for v in ids.values() for i in v)
    assert out["letter_mass"] == pytest.approx(expected_mass)
    assert out["top"][0][0] == "t20"
    assert "p_watch" not in out
    out = rn.summarise(logits, ids, lambda t: f"t{t}", 100, 0.1, top_k=3, watch_ids={"<|channel>": 20})
    assert out["p_watch"]["<|channel>"] == pytest.approx(np.exp(3.0 - lse))
    rows = [dict(out, correct=1), dict(out, correct=0)]
    summ = rn._mass_summary(rows, "ABCD")
    assert summ["p_channel"]["n"] == 2 and summ["p_channel"]["max"] == pytest.approx(np.exp(3.0 - lse))
    assert rn._mass_summary([dict(out, correct=1, p_watch={})], "ABCD")["p_channel"] is None


class FakeScorer:
    def __init__(self, fail_on=()):
        self.fail_on = set(fail_on)
        self.seen = []

    def score(self, text, letters="ABCD"):
        self.seen.append(text)
        if text in self.fail_on:
            raise RuntimeError("simulated failure")
        h = sum(map(ord, text)) % len(letters)
        out = {"n_tokens": len(text), "secs": 0.0, "letter_mass": 0.99, "pred_letter": letters[h]}
        out.update({f"logit_{L}": float(i == h) for i, L in enumerate(letters)})
        return out


def _jobs(n):
    return [{"item_id": f"r/{i:03d}", "repo": "r", "group": None, "qtype": "A", "size": 12, "version": v,
             "perm": 1, "correct_letter": "A", "text": f"prompt {i} {v}"} for i in range(n) for v in ("G1", "G2")]


def test_run_jobs_resume_retry_and_header(tmp_path):
    out = str(tmp_path / "run.jsonl")
    header = {"model_tag": "T", "model_file": "m.gguf", "settings": {"thought_block": "on"}}
    jobs = _jobs(5)
    r1 = rn.run_jobs(FakeScorer(fail_on={"prompt 2 G2"}), jobs, out, "T", header, log_every=1000)
    assert r1 == {"scored": 10, "skipped_done": 0, "errors": 1}
    # an interruption cuts the last row in half (no trailing newline)
    with open(out) as fh:
        txt = fh.read()
    with open(out, "w") as fh:
        fh.write(txt[:-20])
    s2 = FakeScorer()
    r2 = rn.run_jobs(s2, jobs, out, "T", header, log_every=1000)
    assert r2 == {"scored": 2, "skipped_done": 8, "errors": 0}
    assert sorted(s2.seen) == ["prompt 2 G2", "prompt 4 G2"]
    rows, rep = rn.load_results(out)
    assert rep["rows"] == 10 and rep["unresolved_errors"] == 0 and rep["error_rows"] == 1
    assert rep["broken_lines"] == 1 and rep["duplicates"] == 0 and rep["header"]["model_tag"] == "T"
    assert sorted((r["item_id"], r["version"]) for r in rows) == sorted((j["item_id"], j["version"]) for j in jobs)
    assert all("text" not in r and r["model"] == "T" for r in rows)
    assert rn.run_jobs(FakeScorer(), jobs, out, "T", header)["scored"] == 0
    with pytest.raises(RuntimeError):
        rn.run_jobs(FakeScorer(), jobs, out, "U", dict(header, model_tag="U"))
    with pytest.raises(RuntimeError):
        rn.run_jobs(FakeScorer(), jobs, out, "T", dict(header, settings={"thought_block": "off"}))
    with pytest.raises(RuntimeError):  # same file, different answer prefix
        rn.run_jobs(FakeScorer(), jobs, out, "T", dict(header, settings={"thought_block": "on", "answer_prefix": "Answer:"}))
    assert rn.run_jobs(FakeScorer(), jobs, out, "T", dict(header, settings={"thought_block": "on", "answer_prefix": ""}))["scored"] == 0


def test_run_files_are_tied_to_the_item_files(tmp_path):
    out = str(tmp_path / "run.jsonl")
    pkg = {"code_hash": "c" * 64, "items_digest": "a" * 64}
    header = {"model_tag": "T", "model_file": "m.gguf", "settings": {"thought_block": "on"}, "package": pkg}
    jobs = _jobs(3)
    rn.run_jobs(FakeScorer(fail_on={"prompt 1 G1"}), jobs, out, "T", header, log_every=1000)
    with pytest.raises(RuntimeError, match="other item files"):
        rn.run_jobs(FakeScorer(), jobs, out, "T", dict(header, package=dict(pkg, items_digest="b" * 64)))
    # other code is allowed and recorded in the resume line
    new_pkg = dict(pkg, code_hash="d" * 64)
    assert rn.run_jobs(FakeScorer(), jobs, out, "T", dict(header, package=new_pkg))["scored"] == 1
    with open(out) as fh:
        lines = [json.loads(x) for x in fh]
    assert lines[0]["_header"]["package"] == pkg
    assert [x["_resume"]["package"] for x in lines if "_resume" in x] == [new_pkg]


def test_package_state_matches_the_commit_tool(tmp_path):
    from ngraph import commit as cm

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    st = rn.package_state(os.path.join(root, "data", "items"))
    assert st["items_folder"] == "data/items"
    assert st["items_digest"] == cm.digest(root, "data/items")["digest"]
    assert st["code_hash"] == cm.code_hash(root) and isinstance(st["code_sha256_current"], bool)
    assert isinstance(st["manifests"], dict)
    outside = rn.package_state(str(tmp_path))
    assert outside["items_digest"] is None and outside["items_folder"] == "outside the package"


def test_package_state_keeps_the_code_hash_when_a_path_is_refused(tmp_path):
    from ngraph import commit as cm

    root = tmp_path / "pkg"
    (root / "src").mkdir(parents=True)
    (root / "src" / "a.py").write_text("x = 1\n")
    (root / "CODE_SHA256.txt").write_text(cm.code_sha256_text(str(root)))
    try:
        os.symlink(root / "src" / "a.py", root / "src" / "link.py")
    except (OSError, NotImplementedError):
        pytest.skip("symbolic links are not available here")
    st = rn.package_state(None, root=str(root))
    assert st["code_hash"] == cm.code_hash(str(root)) and len(st["code_hash"]) == 64
    assert st["code_sha256_current"] is True and "code_check_error" not in st and "code_error" not in st
    assert len(st["code_refused"]) == 1 and "src/link.py" in st["code_refused"][0]


def _header(**changes):
    """A run header with the fields that run_jobs compares or records on resume, some of them changed."""
    settings = {"n_ctx": 4096, "n_batch": 512, "n_ubatch": 512, "n_gpu_layers": -1, "flash_attn": False,
                "enable_thinking": False, "thought_block": "on", "answer_prefix": "Answer:",
                "llama_cpp_python": "0.3.36"}
    h = {"model_tag": "31B", "model_file": "m.gguf", "settings": settings, "model_gguf": {"sha256": "1" * 64},
         "package": {"code_hash": "c" * 64, "items_folder": "data/items", "items_digest": "a" * 64},
         "platform": "macOS-15.1-arm64", "python": "3.12.7"}
    for k, v in changes.items():
        if k in settings:
            h["settings"] = dict(h["settings"], **{k: v})
        else:
            h[k] = v
    return h


def test_resume_refuses_another_model_file_or_other_settings(tmp_path):
    out = str(tmp_path / "run.jsonl")
    jobs = _jobs(3)
    rn.run_jobs(FakeScorer(), jobs[:2], out, "31B", _header(), log_every=1000)
    with open(out) as fh:
        first = fh.read()
    refused = [(dict(_header(), model_gguf={"sha256": "2" * 64}), "another model file"),
               ({k: v for k, v in _header().items() if k != "model_gguf"}, "another model file"),
               (_header(flash_attn=True), "flash_attn"), (_header(llama_cpp_python="0.3.40"), "llama_cpp_python"),
               (_header(n_gpu_layers=0), "n_gpu_layers"), (_header(n_ctx=8192), "n_ctx"),
               (_header(n_batch=256), "n_batch"), (_header(n_ubatch=256), "n_ubatch"),
               (_header(enable_thinking=True), "enable_thinking"),
               (_header(thought_block="off"), "thought-block"), (_header(answer_prefix=""), "answer prefix")]
    for h, msg in refused:
        with pytest.raises(RuntimeError, match=msg):
            rn.run_jobs(FakeScorer(), jobs, out, "31B", h)
    with open(out) as fh:
        assert fh.read() == first  # nothing was written by a refused session
    # another platform, then another Python version: recorded in the _resume lines, not refused
    new = _header(platform="Linux-6.8-x86_64")
    assert rn.run_jobs(FakeScorer(), jobs, out, "31B", new)["scored"] == 4
    assert rn.run_jobs(FakeScorer(), jobs, out, "31B", dict(new, python="3.13.1"))["scored"] == 0
    with open(out) as fh:
        lines = [json.loads(x) for x in fh]
    assert lines[0]["_header"]["platform"] == "macOS-15.1-arm64"
    r1, r2 = [x["_resume"] for x in lines if "_resume" in x]
    assert set(r1) == {"utc", "todo", "package", "model_sha256", "settings", "answer_prefix_source", "platform",
                       "python"}
    assert r1["platform"] == "Linux-6.8-x86_64" and r1["python"] == "3.12.7" and r1["todo"] == 4
    assert r1["model_sha256"] == "1" * 64 and r1["settings"] == new["settings"] and r1["package"] == new["package"]
    assert r2["python"] == "3.13.1" and r2["todo"] == 0


def test_resume_refuses_other_jobs(tmp_path):
    out = str(tmp_path / "run.jsonl")
    jobs = _jobs(3)
    base = _header(perms=[1], repos=["r"], versions=["G1", "G2"], n_jobs=len(jobs))
    rn.run_jobs(FakeScorer(), jobs[:2], out, "31B", base, log_every=1000)
    for k, v in (("perms", [1, 2]), ("repos", ["r", "s"]), ("versions", ["G1"]), ("n_jobs", 4)):
        with pytest.raises(RuntimeError, match=f"written for other jobs: {k} "):
            rn.run_jobs(FakeScorer(), jobs, out, "31B", dict(base, **{k: v}))
    with pytest.raises(RuntimeError, match=r"versions \['G1', 'G2'\], now none recorded"):
        rn.run_jobs(FakeScorer(), jobs, out, "31B", {k: v for k, v in base.items() if k != "versions"})
    assert rn.run_jobs(FakeScorer(), jobs, out, "31B", base)["scored"] == 4


def test_resume_refuses_a_file_begun_before_a_freeze(tmp_path):
    jobs = _jobs(3)
    v10, v11 = "prereg/MANIFEST_prereg-v1.0.txt", "prereg/MANIFEST_prereg-v1.1.txt"

    def head(manifests):
        h = _header()
        return dict(h, package=dict(h["package"], manifests=manifests))

    pilot = str(tmp_path / "pilot.jsonl")
    rn.run_jobs(FakeScorer(), jobs[:2], pilot, "31B", head({}), log_every=1000)
    with pytest.raises(RuntimeError, match=r"begun when prereg/ held other manifests \(first line: none; now: "
                                           r"prereg/MANIFEST_prereg-v1.0.txt eeeeeeeeeeee...\)"):
        rn.run_jobs(FakeScorer(), jobs, pilot, "31B", head({v10: "e" * 64}))
    assert rn.run_jobs(FakeScorer(), jobs, pilot, "31B", head({}))["scored"] == 4  # still before the freeze
    # a file begun after the freeze goes on after the addendum, not after its manifest changed or went missing
    out = str(tmp_path / "run.jsonl")
    rn.run_jobs(FakeScorer(), jobs[:2], out, "31B", head({v10: "e" * 64}), log_every=1000)
    for manifests in ({}, {v10: "0" * 64}, {v11: "f" * 64}):
        with pytest.raises(RuntimeError, match="other manifests"):
            rn.run_jobs(FakeScorer(), jobs, out, "31B", head(manifests))
    assert rn.run_jobs(FakeScorer(), jobs, out, "31B", head({v10: "e" * 64, v11: "f" * 64}))["scored"] == 4


def test_resume_refuses_other_items_outside_the_package(tmp_path):
    from ngraph import commit as cm

    items = tmp_path / "items"
    items.mkdir()
    original = '{"repo": "r", "items": []}'
    (items / "r.json").write_text(original)
    st = rn.package_state(str(items))
    assert st["items_folder"] == "outside the package" and st["items_digest"] is None
    assert st["items_digest_outside"] == cm.digest(str(tmp_path), "items")["digest"]
    out = str(tmp_path / "run.jsonl")
    jobs = _jobs(3)
    rn.run_jobs(FakeScorer(), jobs[:2], out, "31B", _header(package=st), log_every=1000)
    (items / "r.json").write_text(original + "\n")  # an edited copy of the items
    edited = rn.package_state(str(items))
    assert edited["items_digest_outside"] != st["items_digest_outside"]
    with pytest.raises(RuntimeError, match="other item files.*items_digest_outside"):
        rn.run_jobs(FakeScorer(), jobs, out, "31B", _header(package=edited))
    # the package's own items in the next session: a digest recorded in only one header is a difference
    with pytest.raises(RuntimeError, match="other item files.*items_folder.*items_digest"):
        rn.run_jobs(FakeScorer(), jobs, out, "31B", _header())
    (items / "r.json").write_text(original)  # the first session's files again, the folder spelled differently
    again = rn.package_state(str(items) + os.sep)
    assert again["items_digest_outside"] == st["items_digest_outside"]
    assert rn.run_jobs(FakeScorer(), jobs, out, "31B", _header(package=again))["scored"] == 4


def test_resume_refuses_items_that_cannot_be_digested(tmp_path):
    """An item folder that cannot be digested leaves no digest in either header; the session is refused."""
    items = tmp_path / "items"
    items.mkdir()
    (items / "r.json").write_text('{"repo": "r", "items": []}')
    try:
        (items / "Icon\r").write_text("")  # Finder's custom-icon file: a name with a line break, refused
    except OSError:
        pytest.skip("a file name with a line break is not allowed here")
    st = rn.package_state(str(items))
    assert st["items_folder"] == "outside the package" and "items_digest_outside" not in st and st["items_error"]
    out = str(tmp_path / "run.jsonl")
    jobs = _jobs(3)
    rn.run_jobs(FakeScorer(), jobs[:2], out, "31B", _header(package=st), log_every=1000)
    (items / "r.json").write_text('{"repo": "r", "items": [], "edited": true}')
    with pytest.raises(RuntimeError, match="could not be digested, so the item files cannot be compared"):
        rn.run_jobs(FakeScorer(), jobs, out, "31B", _header(package=rn.package_state(str(items))))


def test_package_state_resolves_symbolic_links(tmp_path):
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    link = tmp_path / "pkglink"
    try:
        os.symlink(root, link, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symbolic links are not available here")
    plain = rn.package_state(os.path.join(root, "data", "items"))
    for st in (rn.package_state(os.path.join(str(link), "data", "items")),  # items through the link
               rn.package_state(os.path.join(root, "data", "items"), root=str(link))):  # package root through it
        assert st["items_folder"] == "data/items" and "items_digest_outside" not in st
        assert st["items_digest"] == plain["items_digest"] and len(plain["items_digest"]) == 64


def test_token_parity():
    lens = {("a", 1, "G1"): 100, ("a", 1, "G2"): 103, ("a", 1, "G3"): 100, ("a", 1, "G4"): 98,
            ("b", 1, "G1"): 50, ("b", 1, "G2"): 50}
    p = rn.token_parity(lens)
    assert p["G2-G1"] == {"n": 2, "mean": 1.5, "mean_abs": 1.5, "min": 0, "max": 3}
    assert p["G4-G3"]["n"] == 1 and p["G4-G3"]["mean"] == -2.0


def _toy_item():
    nodes = [f"pkg.m.f{i}" for i in range(14)]
    edges = [[nodes[0], nodes[1]], [nodes[0], nodes[2]], [nodes[3], nodes[4]], [nodes[5], nodes[0]]]
    graph = "Below is part of a call graph.\n" + "\n".join(f"{s} -> {t}" for s, t in edges)
    text = graph + "\n\nQuestion: which?\nA. x\nB. y\nC. z\nD. w\n\nAnswer with the letter of the correct option only."
    return {"item_id": "toy/000", "nodes": nodes, "edges_true": edges, "versions": {"G1": {"text": text, "correct": "A"}}}


def test_ten_option_prompts_have_one_true_callee():
    for seed in range(20):
        (p,) = rn.ten_option_prompts([_toy_item()], 1, seed)
        it = _toy_item()
        lines = [ln for ln in p["text"].splitlines() if len(ln) > 2 and ln[1:3] == ". " and ln[0] in rn.LETTERS10]
        assert [ln[0] for ln in lines] == list(rn.LETTERS10)
        x = p["text"].split("functions does ")[1].split(" call directly")[0]
        callees = {t for s, t in it["edges_true"] if s == x}
        opts = [ln[3:] for ln in lines]
        assert sum(o in callees for o in opts) == 1 and x not in opts
        assert opts[rn.LETTERS10.index(p["correct_letter"])] in callees


@needs_vocab
def test_template_rendering_from_vocab_file():
    from ngraph.gguf_meta import read_metadata

    tmpl = read_metadata(VOCAB)["tokenizer.chat_template"]
    p = rn.render_prompt(tmpl, "Q?", "<bos>")
    assert p == "<bos><|turn>user\nQ?<turn|>\n<|turn>model\n" + rn.THOUGHT_BLOCK
    assert rn.template_appends_block(tmpl)
    assert rn.gguf_info(VOCAB, sha=False)["template_appends_thought_block"] is True
    p_think = rn.render_prompt(tmpl, "Q?", "<bos>", enable_thinking=True)
    assert p_think == "<bos><|turn>system\n<|think|><turn|>\n<|turn>user\nQ?<turn|>\n<|turn>model\n"


@needs_vocab
def test_tokens_letters_and_bos_with_vocab_file():
    pytest.importorskip("llama_cpp")
    s = rn.LetterScorer(VOCAB, vocab_only=True, thought_block="on")
    assert s.bos_id == 2 and s.bos_text == "<bos>"
    assert s.letter_ids(rn.LETTERS4) == {"A": [236776, 562], "B": [236799, 603], "C": [236780, 565], "D": [236796, 622]}
    ids10 = s.letter_ids(rn.LETTERS10)
    assert len({i for v in ids10.values() for i in v}) == 20
    p_on, t_on = s.prompt_tokens("Question?\nA. x\nB. y")
    assert t_on[0] == 2 and t_on.count(2) == 1 and t_on[1] == 105 and t_on.count(105) == 2
    assert t_on[-4:] == [100, 45518, 107, 101]  # <|channel> thought \n <channel|>
    s.thought_block = "off"
    p_off, t_off = s.prompt_tokens("Question?\nA. x\nB. y")
    assert p_on == p_off + rn.THOUGHT_BLOCK and t_on[: len(t_off)] == t_off and t_off[-1] != 101


@needs_vocab
def test_probe_round_trip(tmp_path):
    pytest.importorskip("llama_cpp")
    s = rn.LetterScorer(VOCAB, vocab_only=True)
    item = _toy_item()
    item["neutral_map"] = {"pkg.m.f0": "zor.ka.vemit", "pkg.m.f1": "zor.ka.dulo"}
    item["versions"]["G2"] = item["versions"]["G1"]
    probe = rn.tokenizer_probe(s, [item], n_prompts=1)
    assert len(probe["strings"]) == 4 + 2
    assert rn.check_probe(s, probe)["ok"]
    probe["ids"][0] = probe["ids"][0] + [1]
    assert rn.check_probe(s, probe)["mismatches"] == 1


@needs_vocab
def test_smoke_pipeline_with_fake_logits():
    """Runs the whole GNG-1 smoke check on real pilot items with the real tokenizer and chat
    template; only the forward pass is replaced (all probability on the letter "A")."""
    pytest.importorskip("llama_cpp")
    items_dir = os.environ.get("NGRAPH_ITEMS_DIR")
    path = os.path.join(items_dir or "", "trio.json")
    if not os.path.exists(path):
        pytest.skip("set NGRAPH_ITEMS_DIR to the folder with trio.json")
    with open(path) as fh:
        items = json.load(fh)["items"]
    s = rn.LetterScorer(VOCAB, vocab_only=True, thought_block="on")
    a_id = s.letter_ids(rn.LETTERS10)["A"][0]

    def fake_next_logits(toks):
        x = np.full(s.n_vocab, -20.0)
        x[a_id] = 10.0
        return x

    s.next_logits = fake_next_logits
    probe = rn.tokenizer_probe(s, items[:5], n_prompts=2)
    res = rn.smoke(s, items, n=12, n_repeat=3, n_alt=3, probe=probe)
    assert res["bos_ok"] and res["special_tokens_ok"] and res["tokenizer_probe"]["ok"] and res["checks_ok"]
    assert res["template_appends_thought_block"] and res["prompt_tail"].endswith(rn.THOUGHT_BLOCK)
    assert res["AD"]["n"] == 12 and res["AD"]["share_mass_ge_0.9"] == 1.0
    assert res["AJ"]["n"] >= 10 and res["AJ"]["pred_letter_counts"]["A"] == res["AJ"]["n"]
    assert res["AD_other_thought_block"]["mode"] == "off" and s.thought_block == "on"
    assert res["AJ_other_thought_block"]["mode"] == "off"
    assert res["AD_other_thought_block"]["n"] == 3 and res["AJ_other_thought_block"]["n"] == 3
    assert res["AD"]["p_channel"]["n"] == 12 and res["AD"]["p_channel"]["max"] < 1e-6
    assert res["own_setting_passes"] and res["other_setting_passes"]
    assert res["thought_block_decision"] == "keep"
    assert res["repeat"]["argmax_agreement"] == 1.0 and res["gng1_pass"]


@needs_vocab
def test_smoke_switch_rule_when_only_the_other_setting_passes():
    """Fake forward pass that, after the empty thought block, puts its mass on "<|channel>" (as a
    model that wants to open a thought channel would) and otherwise on "A". With the block on, the
    letter mass fails, the setting without it passes, and the pre-registered rule says switch. A
    failed tokenizer probe on its own does not trigger a switch."""
    pytest.importorskip("llama_cpp")
    items_dir = os.environ.get("NGRAPH_ITEMS_DIR")
    path = os.path.join(items_dir or "", "trio.json")
    if not os.path.exists(path):
        pytest.skip("set NGRAPH_ITEMS_DIR to the folder with trio.json")
    with open(path) as fh:
        items = json.load(fh)["items"]
    s = rn.LetterScorer(VOCAB, vocab_only=True, thought_block="on")
    a_id = s.letter_ids(rn.LETTERS10)["A"][0]
    ch_id = s.watch_ids[rn.CHANNEL_TOKEN]
    end_block = s.tokenize("<channel|>", special=True)[0]

    def fake_next_logits(toks):
        x = np.full(s.n_vocab, -20.0)
        x[ch_id if toks[-1] == end_block else a_id] = 10.0
        return x

    s.next_logits = fake_next_logits
    res = rn.smoke(s, items, n=8, n_repeat=2, n_alt=4)
    assert res["checks_ok"] and not res["own_setting_passes"] and res["other_setting_passes"]
    assert res["thought_block_decision"] == "switch (log a deviation)" and not res["gng1_pass"]
    assert res["AD"]["p_channel"]["share_gt_0.1"] == 1.0
    assert res["AD_other_thought_block"]["p_channel"]["max"] < 1e-6

    def all_on_a(toks):
        x = np.full(s.n_vocab, -20.0)
        x[a_id] = 10.0
        return x

    s.next_logits = all_on_a
    probe = rn.tokenizer_probe(s, items[:3], n_prompts=1)
    probe["ids"][0] = probe["ids"][0] + [1]
    res = rn.smoke(s, items, n=8, n_repeat=2, n_alt=4, probe=probe)
    assert not res["checks_ok"] and res["own_setting_passes"]
    assert res["thought_block_decision"] == "keep" and not res["gng1_pass"]


@needs_vocab
def test_answer_prefix_follows_the_thought_block():
    pytest.importorskip("llama_cpp")
    s = rn.LetterScorer(VOCAB, vocab_only=True, thought_block="on", answer_prefix="Answer:")
    assert s.settings["answer_prefix"] == "Answer:"
    p_on, t_on = s.prompt_tokens("Question?\nA. x\nB. y")
    assert p_on.endswith("<|turn>model\n" + rn.THOUGHT_BLOCK + "Answer:")
    tail = s.tokenize("Answer:", special=False)
    assert t_on[-len(tail):] == tail and t_on[-len(tail) - 1] == 101  # <channel|> then the prefix
    assert s.render_base("Q") + "Answer:" == s.render("Q")
    s.thought_block = "off"
    assert s.render("Q").endswith("<|turn>model\nAnswer:")
    plain = rn.LetterScorer(VOCAB, vocab_only=True, thought_block="on")
    assert plain.answer_prefix == "" and plain.render("Q") == plain.render_base("Q")


def test_registered_prefixes_and_resolution():
    assert rn.PREFIX_CANDIDATES[0] == "" and "Answer:" in rn.PREFIX_CANDIDATES
    assert rn.ANSWER_PREFIX == {"E2B": "Answer:", "E4B": "", "12B": "Answer:"}
    assert rn.answer_prefix_for("e2b") == "Answer:" and rn.answer_prefix_for("E4B") == ""
    assert rn.answer_prefix_for("E4B", "Answer:") == "Answer:"  # explicit value wins (a deviation)
    assert rn.answer_prefix_for("31B") == ""  # smoke on an unregistered model starts with no prefix
    with pytest.raises(SystemExit, match=r"'31B': pass --prefix-from .*rule's choice.* or --answer-prefix \(a dev"):
        rn.answer_prefix_for("31b", required=True)


def _smoke_output(**changes):
    """The fields of a 31B smoke output that study-a --prefix-from reads: "Answer:" is the rule's choice, and
    this is the GNG-1 rerun made with it (settings.answer_prefix "Answer:", prefix_matches_rule and gng1_pass)."""
    res = {"model_tag": "31B", "model_file": {"file": "m.gguf", "sha256": "f" * 64}, "checks_ok": True,
           "tokenizer_probe": {"n": 4040, "mismatches": 0, "examples": [], "ok": True},
           "settings": {"thought_block": "on", "answer_prefix": "Answer:"},
           "prefix_scan": [{"prefix": "", "passes": False}, {"prefix": "Answer:", "passes": True},
                           {"prefix": "The correct option is", "passes": True}],
           "prefix_rule_choice": "Answer:", "prefix_matches_rule": True, "gng1_pass": True,
           "prompts": {"n": 40, "seed": 0, "n_alt": None, "AD": 40, "AJ": 36}, "repos": ["langextract", "trio"],
           "package": {"code_hash": "c" * 64, "items_folder": "data/items", "items_digest": "a" * 64}}
    res.update(changes)
    return res


RUN_PACKAGE = {"code_hash": "d" * 64, "items_folder": "data/items", "items_digest": "a" * 64}  # other code is fine
PILOT = ["trio", "langextract"]


def test_prefix_from_smoke(tmp_path):
    path = tmp_path / "smoke_31B.json"

    def check(tag="31B", sha="f" * 64, thought_block="on", run_package=RUN_PACKAGE, pilot=PILOT, **changes):
        path.write_text(json.dumps(_smoke_output(**changes)))
        return rn.prefix_from_smoke(str(path), tag, sha, thought_block, run_package, pilot)

    prefix, source = check(tag="31b")
    assert prefix == "Answer:"
    assert source == {"rule": "smoke file", "smoke_file": "smoke_31B.json",
                      "smoke_sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "prefix_rule_choice": "Answer:"}
    with pytest.raises(SystemExit, match="E4B has a registered answer prefix"):
        check(tag="e4b", model_tag="E4B")
    with pytest.raises(SystemExit, match="model_tag '26B-A4B', not '31B'"):
        check(model_tag="26B-A4B")
    with pytest.raises(SystemExit, match="model file with SHA-256 ffffffffffff..., not eeeeeeeeeeee..."):
        check(sha="e" * 64)
    with pytest.raises(SystemExit, match="records no SHA-256"):  # a smoke file from before the SHA-256 was kept
        check(model_file={"file": "m.gguf"})
    with pytest.raises(SystemExit, match="thought-block mode 'on', not the run's 'off'"):
        check(thought_block="off")
    with pytest.raises(SystemExit, match="checks did not pass"):
        check(checks_ok=False)
    with pytest.raises(SystemExit, match="no passed tokenizer probe"):
        check(tokenizer_probe=None)
    with pytest.raises(SystemExit, match="no passed tokenizer probe"):
        check(tokenizer_probe={"n": 4040, "mismatches": 3, "ok": False})
    with pytest.raises(SystemExit, match="no candidate prefix passed with its thought-block setting .*GNG-1 "
                                         "fallback in the pre-registration's section 7"):
        check(prefix_scan=[{"prefix": p, "passes": False} for p in rn.PREFIX_CANDIDATES], prefix_rule_choice=None)
    with pytest.raises(SystemExit, match="not the first candidate that passed"):
        check(prefix_rule_choice="The correct option is")
    with pytest.raises(SystemExit, match="did not try PREFIX_CANDIDATES"):
        check(prefix_scan=[{"prefix": "Answer:", "passes": True}])
    with pytest.raises(SystemExit, match="did not try PREFIX_CANDIDATES"):  # not a list: listed, not a crash
        check(prefix_scan=5)
    with pytest.raises(SystemExit) as e:  # a candidate passed, but no choice is recorded: no claim that none passed
        check(prefix_rule_choice=None)
    assert "not the first candidate that passed" in str(e.value) and "no candidate prefix passed" not in str(e.value)
    # the file given is the GNG-1 run made with the rule's choice: the first run, without a prefix, is refused
    with pytest.raises(SystemExit, match=r"not run with the rule's choice 'Answer:' \(settings.answer_prefix '', "
                                         r"prefix_matches_rule False\), .*smoke again with --answer-prefix 'Answer:'"
                       ) as e:
        check(settings={"thought_block": "on", "answer_prefix": ""}, prefix_matches_rule=False, gng1_pass=False)
    assert "gng1_pass" not in str(e.value)
    with pytest.raises(SystemExit, match="prefix_matches_rule None"):  # a smoke file without the field
        check(prefix_matches_rule=None)
    with pytest.raises(SystemExit, match=r"its GNG-1 verdict is not a pass \(gng1_pass is not true\)"):
        check(gng1_pass=False)
    # when the first candidate (no prefix) passes, the first run is the one
    first = [{"prefix": p, "passes": True} for p in rn.PREFIX_CANDIDATES]
    assert check(prefix_scan=first, prefix_rule_choice="", settings={"thought_block": "on", "answer_prefix": ""}
                 )[0] == ""
    # the registered GNG-1 pilot prompts, from the run's item files
    with pytest.raises(SystemExit, match=r"registered GNG-1 pilot prompts \(prompts n 6 and seed 0; registered 40 and 0"):
        check(prompts={"n": 6, "seed": 0})
    with pytest.raises(SystemExit, match="prompts n None and seed None"):  # a smoke file from before they were kept
        check(prompts=None)
    with pytest.raises(SystemExit, match="seed 1;"):
        check(prompts={"n": 40, "seed": 1})
    with pytest.raises(SystemExit, match=r"repositories \['trio'\], not the manifest's pilot repositories"):
        check(repos=["trio"])
    with pytest.raises(SystemExit, match="no --manifest"):
        check(pilot=None)
    with pytest.raises(SystemExit, match=r"other item files than the run's \(items_digest aaaaaaaaaaaa..., run bbbb"):
        check(run_package=dict(RUN_PACKAGE, items_digest="b" * 64))
    with pytest.raises(SystemExit, match="items_folder none recorded, run 'data/items'; items_digest none recorded"):
        check(package=None)  # a smoke file from before the item digest was kept
    with pytest.raises(SystemExit, match="could not be digested"):
        check(run_package={"items_folder": "outside the package", "items_digest": None, "items_error": "x"})
    with pytest.raises(SystemExit, match="could not be digested"):
        check(package={"items_error": "y"})
    # every problem is listed
    with pytest.raises(SystemExit, match="model_tag.*SHA-256.*checks did not pass.*pilot prompts.*other item files"):
        check(model_tag="12B", sha="e" * 64, checks_ok=False, prompts={"n": 6, "seed": 0},
              run_package=dict(RUN_PACKAGE, items_digest="b" * 64))


def test_read_smoke_fails_before_the_model_file_is_hashed(tmp_path, monkeypatch):
    path = tmp_path / "smoke_31B.json"
    with pytest.raises(SystemExit, match="--prefix-from: cannot read .*smoke_31B.json"):
        rn.read_smoke(str(path), "31B")
    path.write_text(json.dumps(_smoke_output()))
    raw, sm = rn.read_smoke(str(path), "31b")
    assert raw == path.read_bytes() and sm["model_tag"] == "31B"
    with pytest.raises(SystemExit, match="model_tag '31B', not '26B-A4B'"):
        rn.read_smoke(str(path), "26B-A4B")
    assert rn.read_smoke(str(path), "26B-A4B", check_tag=False)[1] == sm
    with pytest.raises(SystemExit, match="E2B has a registered answer prefix"):
        rn.read_smoke(str(path), "E2B")
    path.write_text("[1, 2]")
    with pytest.raises(SystemExit, match="no JSON object"):
        rn.read_smoke(str(path), "31B")
    # through main(): refused before the model file is hashed or the scorer is built
    calls = []
    monkeypatch.setattr(rn, "gguf_info", lambda *a, **k: calls.append(a) or {})
    monkeypatch.setattr(rn, "LetterScorer", lambda *a, **k: calls.append(a))
    items = tmp_path / "items"
    items.mkdir()
    (items / "r.json").write_text(json.dumps({"repo": "r", "items": [{"item_id": "r/000"}]}))
    for smoke_file, msg in ((tmp_path / "missing.json", "cannot read"), (path, "no JSON object")):
        with pytest.raises(SystemExit, match=msg):
            rn.main(["study-a", "--model", "m.gguf", "--tag", "31B", "--items-dir", str(items),
                     "--prefix-from", str(smoke_file), "--out", str(tmp_path / "o.jsonl")])
    assert calls == []


def test_study_a_prefix_options_exclude_each_other(tmp_path, capsys):
    with pytest.raises(SystemExit) as e:
        rn.main(["study-a", "--model", "m.gguf", "--tag", "31B", "--items-dir", str(tmp_path), "--out", "o.jsonl",
                 "--prefix-from", "smoke_31B.json", "--answer-prefix", "Answer:"])
    assert e.value.code == 2 and "not allowed with argument" in capsys.readouterr().err
    with pytest.raises(SystemExit) as e:  # --prefix-from is a study-a option
        rn.main(["smoke", "--model", "m.gguf", "--tag", "31B", "--items-dir", str(tmp_path), "--out", "o.json",
                 "--prefix-from", "smoke_31B.json"])
    assert e.value.code == 2 and "unrecognized arguments: --prefix-from" in capsys.readouterr().err


@needs_vocab
def test_prefix_from_smoke_end_to_end(tmp_path, monkeypatch):
    """make-probe, smoke and study-a through main() on the vocab file, with a fake forward pass that
    gives letters only after "Answer:": the first smoke file's rule choice is "Answer:", the GNG-1 rerun
    with --answer-prefix "Answer:" passes, and study-a --prefix-from runs 31B with it (the first file is
    refused) and records where it came from."""
    pytest.importorskip("llama_cpp")
    items_dir = os.environ.get("NGRAPH_ITEMS_DIR")
    if not os.path.exists(os.path.join(items_dir or "", "trio.json")):
        pytest.skip("set NGRAPH_ITEMS_DIR to the folder with trio.json")

    class VocabScorer(rn.LetterScorer):
        def __init__(self, *args, **kw):
            super().__init__(*args, **dict(kw, vocab_only=True))
            self.colon = self.tokenize("Answer:", special=False)[-1]
            self.the = self.tokenize("The", special=False)[0]

        def next_logits(self, toks):
            x = np.full(self.n_vocab, -20.0)
            x[self.letter_ids(rn.LETTERS10)["A"][1] if toks[-1] == self.colon else self.the] = 10.0
            return x

    monkeypatch.setattr(rn, "LetterScorer", VocabScorer)
    monkeypatch.setattr(rn, "GNG1_N", 6)  # a short stand-in for the registered 40 prompts, used by smoke and study-a
    # the package's manifest cut to its pilot repositories and one confirmatory repository, which keeps
    # the smoke test's projection of Study A hours short
    with open(os.path.join(rn.PKG_ROOT, "data", "repos_manifest.json")) as fh:
        repos = json.load(fh)["repos"]
    pilot = sorted(r["label"] for r in repos if r["role"] == "pilot")
    manifest = str(tmp_path / "repos_manifest.json")
    with open(manifest, "w") as fh:
        json.dump({"repos": [r for r in repos if r["role"] == "pilot" or r["label"] == "rich"]}, fh)
    common = ["--model", VOCAB, "--items-dir", items_dir, "--manifest", manifest]
    runs = tmp_path / "runs"  # not there yet, as in a fresh copy of the package: the runner makes it
    probe, first_file, smoke_file = (str(tmp_path / "probe.json"), str(runs / "smoke_31B_no_prefix.json"),
                                     str(runs / "smoke_31B.json"))
    rn.main(["make-probe", *common, "--repos", "trio", "--tag", "vocab", "--out", probe])
    # the registered GNG-1 prompts: the pilot repositories (from the manifest), GNG1_N prompts, seed 0; first
    # with no prefix
    rn.main(["smoke", *common, "--tag", "31b", "--n-alt", "2", "--probe", probe, "--out", first_file])
    with open(first_file) as fh:
        sm = json.load(fh)
    vocab_sha = rn._sha256_file(VOCAB)
    assert sm["model_tag"] == "31B" and sm["model_file"]["sha256"] == vocab_sha and sm["repos"] == pilot
    assert sm["prompts"]["n"] == 6 and sm["prompts"]["seed"] == rn.GNG1_SEED and sm["prompts"]["AD"] == 6
    assert sm["prefix_rule_choice"] == "Answer:" and sm["checks_ok"] and sm["tokenizer_probe"]["ok"]
    assert sm["prefix_matches_rule"] is False and sm["gng1_pass"] is False  # its verdict is for no prefix
    # then the GNG-1 rerun with the rule's choice, whose verdict is for the prefix the run uses
    rn.main(["smoke", *common, "--tag", "31b", "--n-alt", "2", "--probe", probe, "--answer-prefix", "Answer:",
             "--out", smoke_file])
    with open(smoke_file) as fh:
        sm = json.load(fh)
    assert sm["settings"]["answer_prefix"] == "Answer:" and sm["prefix_rule_choice"] == "Answer:"
    assert sm["prefix_matches_rule"] is True and sm["gng1_pass"] is True
    calls = []
    real_info = rn.gguf_info
    monkeypatch.setattr(rn, "gguf_info", lambda path, sha=True: calls.append(path) or real_info(path, sha))
    out = str(tmp_path / "studyA_31B.jsonl")
    common += ["--repos", "trio"]  # a small run
    with pytest.raises(SystemExit, match=r"smoke_31B_no_prefix.json cannot set .*not run with the rule's choice"):
        rn.main(["study-a", *common, "--tag", "31B", "--versions", "G1", "--prefix-from", first_file, "--out", out])
    assert not os.path.exists(out)
    calls.clear()
    rn.main(["study-a", *common, "--tag", "31B", "--versions", "G1", "--prefix-from", smoke_file, "--out", out])
    assert calls == [VOCAB]  # the model file is hashed once
    rows, rep = rn.load_results(out)
    head = rep["header"]
    with open(smoke_file, "rb") as fh:
        smoke_sha = hashlib.sha256(fh.read()).hexdigest()
    assert head["answer_prefix_source"] == {"rule": "smoke file", "smoke_file": "smoke_31B.json",
                                            "smoke_sha256": smoke_sha, "prefix_rule_choice": "Answer:"}
    assert head["settings"]["answer_prefix"] == "Answer:" and head["model_gguf"]["sha256"] == vocab_sha
    assert rep["rows"] == 20 and all(r["pred_letter"] == "A" and r["letter_mass"] > 0.99 for r in rows)
    assert head["versions"] == ["G1"] and head["perms"] == [1] and head["repos"] == ["trio"]
    with pytest.raises(RuntimeError, match=r"other jobs: perms \[1\], now \[1, 2\]; n_jobs 20, now 40"):
        rn.main(["study-a", *common, "--tag", "31B", "--versions", "G1", "--perms", "1,2", "--prefix-from",
                 smoke_file, "--out", out])
    # a smoke file is checked against the run's manifest: without one, it is refused
    no_manifest = [x for x in common if x not in ("--manifest", manifest)]
    with pytest.raises(SystemExit, match="no --manifest"):
        rn.main(["study-a", *no_manifest, "--tag", "31B", "--versions", "G1", "--prefix-from", smoke_file,
                 "--out", str(tmp_path / "other.jsonl")])
    # a registered tag records ANSWER_PREFIX; a prefix given on the command line is recorded as a deviation
    for extra, rule in (([], "ANSWER_PREFIX"), (["--answer-prefix", "Answer:"], "given (a deviation)")):
        out = str(tmp_path / f"studyA_12B_{len(extra)}.jsonl")
        rn.main(["study-a", *common, "--tag", "12B", "--versions", "G1", *extra, "--out", out])
        assert rn.load_results(out)[1]["header"]["answer_prefix_source"] == {"rule": rule}
    with pytest.raises(SystemExit, match="registered answer prefix"):
        rn.main(["study-a", *common, "--tag", "12B", "--versions", "G1", "--prefix-from", smoke_file, "--out", out])


@needs_vocab
def test_smoke_with_prefix_and_template_mode():
    """With the template's own thought block and a prefix, the other setting is still 'off'."""
    pytest.importorskip("llama_cpp")
    items_dir = os.environ.get("NGRAPH_ITEMS_DIR")
    path = os.path.join(items_dir or "", "trio.json")
    if not os.path.exists(path):
        pytest.skip("set NGRAPH_ITEMS_DIR to the folder with trio.json")
    with open(path) as fh:
        items = json.load(fh)["items"]
    s = rn.LetterScorer(VOCAB, vocab_only=True, thought_block="template", answer_prefix="Answer:")
    a_id = s.letter_ids(rn.LETTERS10)["A"][1]  # " A"

    def fake_next_logits(toks):
        x = np.full(s.n_vocab, -20.0)
        x[a_id] = 10.0
        return x

    s.next_logits = fake_next_logits
    res = rn.smoke(s, items, n=6, n_repeat=2, n_alt=2)
    assert res["answer_prefix"] == "Answer:" and res["prompt_tail"].endswith(rn.THOUGHT_BLOCK + "Answer:")
    assert res["AD_other_thought_block"]["mode"] == "off" and s.thought_block == "template"
    assert res["own_setting_passes"] and res["gng1_pass"]
    # every candidate passes with this fake, so the rule picks the first one (no prefix)
    assert [x["prefix"] for x in res["prefix_scan"]] == list(rn.PREFIX_CANDIDATES)
    assert res["prefix_rule_choice"] == "" and not res["prefix_matches_rule"] and s.answer_prefix == "Answer:"


@needs_vocab
def test_prefix_scan_picks_the_first_prefix_that_passes():
    """Fake model that answers with a letter only after "Answer:" and otherwise starts a sentence."""
    pytest.importorskip("llama_cpp")
    items_dir = os.environ.get("NGRAPH_ITEMS_DIR")
    path = os.path.join(items_dir or "", "trio.json")
    if not os.path.exists(path):
        pytest.skip("set NGRAPH_ITEMS_DIR to the folder with trio.json")
    with open(path) as fh:
        items = json.load(fh)["items"]
    s = rn.LetterScorer(VOCAB, vocab_only=True, thought_block="off", answer_prefix="Answer:")
    colon = s.tokenize("Answer:", special=False)[-1]
    a_id = s.letter_ids(rn.LETTERS10)["A"][1]
    the_id = s.tokenize("The", special=False)[0]

    def fake_next_logits(toks):
        x = np.full(s.n_vocab, -20.0)
        x[a_id if toks[-1] == colon else the_id] = 10.0
        return x

    s.next_logits = fake_next_logits
    res = rn.smoke(s, items, n=6, n_repeat=2, n_alt=2)
    scan = {x["prefix"]: x["passes"] for x in res["prefix_scan"]}
    assert scan == {"": False, "Answer:": True, "The correct option is": False}
    assert res["prefix_rule_choice"] == "Answer:" and res["prefix_matches_rule"] and res["gng1_pass"]
    assert s.answer_prefix == "Answer:"
