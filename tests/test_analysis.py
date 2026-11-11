"""Tests for the analysis code on simulated data (no model outputs involved)."""

import math

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from ngraph import analysis as an
from ngraph import simulate as sim


def test_holm_known_example():
    adj = an.holm({"a": 0.01, "b": 0.04, "c": 0.03})
    assert adj == pytest.approx({"a": 0.03, "c": 0.06, "b": 0.06})


def test_add_scores_softmax_and_ties():
    df = pd.DataFrame({
        "logit_A": [2.0, 1.0, 0.0], "logit_B": [0.0, 1.0, 0.0], "logit_C": [0.0, 0.0, 0.0], "logit_D": [0.0, 0.0, 5.0],
        "correct_letter": ["A", "A", "C"],
    })
    out = an.add_scores(df)
    e = math.exp(2.0)
    assert out["p_correct"].iloc[0] == pytest.approx(e / (e + 3))
    assert out["correct"].tolist() == [1, 0, 0]  # row 2 is a tie between A and B: counted wrong
    assert out["pred_letter"].tolist()[2] == "D"


def test_calibration_hits_target():
    b = sim.calibrate_intercept(0.8, 1.2)
    z = np.random.default_rng(0).normal(size=400_000)
    assert float(np.mean(1 / (1 + np.exp(-(b + 1.2 * z))))) == pytest.approx(0.8, abs=0.003)


def test_a1_pandas_path_matches_array_path():
    kw = dict(n_repos=8, n_items=6, delta=0.05, seed=11)
    arrays = sim.simulate_a_arrays(**kw)
    df = sim.simulate_a_df(**kw)
    res = an.a1(df, n_boot=500)
    assert res["estimate"] == pytest.approx(float(sim.a1_from_arrays(arrays).mean()))
    assert res["n_clusters"] == 8
    lo, hi = res["ci95_boot"]
    assert lo <= res["estimate"] <= hi


def test_a1_type_one_error_near_nominal():
    rej = 0
    n = 300
    for s in range(n):
        v = sim.a1_from_arrays(sim.simulate_a_arrays(seed=10_000 + s, delta=0.0, readability=0.03))
        rej += stats.ttest_1samp(v, 0.0).pvalue < 0.05
    assert 0.02 <= rej / n <= 0.09, rej / n


def test_a1_estimate_is_unbiased():
    est = [sim.a1_from_arrays(sim.simulate_a_arrays(seed=20_000 + s, delta=0.06)).mean() for s in range(200)]
    assert float(np.mean(est)) == pytest.approx(0.06, abs=0.006)


def test_a2_a3_run_on_simulated_data():
    df = sim.simulate_a_df(n_repos=8, n_items=6, delta=0.05, seed=3)
    r2 = an.a2(df, n_boot=500)
    assert r2["n_familiar"] == 4 and r2["n_fresh"] == 4
    r3 = an.a3(df, {"E2B": 2.3e9, "E4B": 4.5e9, "12B": 11.95e9, "31B": 30.7e9}, n_boot=500, bound=0.05)
    assert r3["n_clusters"] == 8 and "tost" in r3


def test_a1_gee_runs():
    df = sim.simulate_a_df(n_repos=6, n_items=5, delta=0.05, seed=5)
    fit = an.a1_gee(df)
    assert any("names_real:edges_swap" in k for k in fit.params.index)


def test_tost_and_sign_flip():
    rng = np.random.default_rng(0)
    near_zero = rng.normal(0.0, 0.02, size=32)
    assert an.tost_mean(near_zero, 0.05)["equivalent_at_0.05"]
    assert not an.tost_mean(near_zero + 0.1, 0.05)["equivalent_at_0.05"]
    assert an.sign_flip_p(rng.normal(0, 1, size=200), 2000) > 0.01
    assert an.sign_flip_p(rng.normal(0.5, 1, size=200), 2000) < 0.01


def test_study_b_recovers_effects():
    df = sim.simulate_b_df(discount=0.07, graph_gain_opaque=0.09, seed=1)
    r1 = an.b1(df, n_boot=1000, n_perm=1000)
    r2 = an.b2(df, n_boot=1000, n_perm=1000)
    assert r1["estimate"] == pytest.approx(0.07, abs=0.05)
    assert r2["estimate"] == pytest.approx(0.09, abs=0.08)
    assert r1["n_tasks"] == 118 + 300
    res = an.confirmatory(sim.simulate_a_df(n_repos=8, n_items=6, delta=0.05, seed=2), df, n_boot=500, n_perm=500)
    assert set(res["holm"]) == {"A1", "B1", "B2"}


def test_study_b_type_one_error():
    rej, n = 0, 60
    for s in range(n):
        df = sim.simulate_b_df(discount=0.0, graph_gain_opaque=0.0, seed=500 + s)
        rej += an.b1(df, n_boot=200, n_perm=200)["p"] < 0.05
    assert rej / n <= 0.15, rej / n


def test_run_files_to_study_a_report(tmp_path, capsys):
    """Runner output -> load_runs -> report, on fake scores with a built-in names x edges effect."""
    import json

    from ngraph import runner as rn

    repos = {"fa": "familiar", "fb": "familiar", "fc": "familiar", "xa": "fresh", "xb": "fresh", "xc": "fresh"}
    man = {"repos": [{"label": r, "group": g, "role": "confirmatory"} for r, g in repos.items()]
           + [{"label": "pilot", "group": "fresh", "role": "pilot"}]}
    mpath = tmp_path / "manifest.json"
    mpath.write_text(json.dumps(man))
    jobs = []
    for r in list(repos) + ["pilot"]:
        for i in range(6):
            for v in ("G0", "G1", "G2", "G3", "G4"):
                jobs.append({"item_id": f"{r}/{i:03d}", "repo": r, "group": None, "qtype": "A", "size": 12,
                             "version": v, "perm": 1, "correct_letter": "ABCD"[i % 4], "text": f"{r} {i} {v}"})

    class Scorer:
        def __init__(self, strength):
            self.strength = strength

        def score(self, text, letters="ABCD"):
            r, i, v = text.split()
            j = next(x for x in jobs if x["text"] == text)
            # correct unless (G3 or G2) for some items: creates a positive names x edges interaction
            right = not (v == "G3" and int(i) < 3) and not (v == "G2" and int(i) < 1)
            target = j["correct_letter"] if right else "ABCD"[(int(i) + 1) % 4]
            out = {f"logit_{L}": (self.strength if L == target else 0.0) for L in letters}
            out.update({"n_tokens": 10, "secs": 0.0, "letter_mass": 0.95, "pred_letter": target})
            return out

    paths = []
    for m, s in (("e4b", 2.0), ("31B", 3.0)):  # a lower-case tag, as it may be typed for the runner
        p = str(tmp_path / f"run_{m}.jsonl")
        rn.run_jobs(Scorer(s), jobs, p, m, {"model_tag": m, "model_file": f"{m}.gguf", "n_jobs": len(jobs),
                                             "settings": {"thought_block": "on"}}, log_every=10_000)
        paths.append(p)
    df, report = an.load_runs(paths, str(mpath))
    assert set(df["repo"]) == set(repos) and df["group"].notna().all()
    assert set(df["model"]) == {"E4B", "31B"}
    assert all(r["complete"] for r in report.values())
    # item files for the A1 sensitivity check: item 0 of every repository is parity-flagged
    items = tmp_path / "items"
    items.mkdir()
    for r in list(repos) + ["pilot"]:
        (items / f"{r}.json").write_text(json.dumps({"repo": r, "items": [
            {"item_id": f"{r}/{i:03d}", "token_parity": {"G2_minus_G1": 3 if i == 0 else 1}} for i in range(6)]}))
    res = an.study_a_report(df, {"E4B": 4.5e9, "31B": 30.7e9}, n_boot=200)
    # per item: G1-G2 = 1 for item 0, G3-G4 = -1 for items 0-2 -> I averaged over 6 items = (1 + 3) / 6
    assert res["A1"]["estimate"] == pytest.approx(4 / 6)
    assert res["A2"]["n_familiar"] == 3 and "A3" in res
    json.dumps(an._jsonable(res))
    # registered defaults: TOST on A2 and A3; A3 on the effective-parameter axis plus the GGUF sensitivity axis
    res = an.study_a_report(df, n_boot=200)
    assert "tost" in res["A2"] and "tost" in res["A3"] and "tost" in res["A3_sensitivity"]
    assert res["A3"]["axis"] == {"31B": 30.7e9, "E4B": 4.5e9}
    assert res["A3_sensitivity"]["axis"] == {"31B": 30_697_345_596, "E4B": 7_463_013_674}
    json.dumps(an._jsonable(res))
    # the command line: the A3 bound-unit switch, the written report and the console summary
    out = tmp_path / "report.json"
    capsys.readouterr()
    an.main(["--runs", *paths, "--manifest", str(mpath), "--n-boot", "200", "--out", str(out),
             "--a3-bound-unit", "decade", "--items-dir", str(items)])
    rep = json.loads(out.read_text())
    assert rep["A3"]["tost"]["bound_unit"] == "decade" == rep["A3_sensitivity"]["tost"]["bound_unit"]
    assert rep["excluded_models"] == [] and rep["A1"]["estimate"] == pytest.approx(4 / 6)
    # without item 0 (I = 2): items 1 and 2 have I = 1, items 3 to 5 I = 0 -> 2 / 5
    assert rep["A1_excluding_parity_flagged"]["estimate"] == pytest.approx(2 / 5)
    assert rep["parity_flagged_items"] == {"n": 6, "rule": an.PARITY_FLAG_RULE}  # pilot/000 is not in the rows
    for p in paths:
        assert {"thought_block", "answer_prefix", "answer_prefix_source", "model_sha256", "package"} <= set(
            rep["files"][p])
    printed = capsys.readouterr().out
    for k in ('"A3"', '"A3_sensitivity"', '"excluded_models"', '"axis"', '"estimate"', '"bound_unit": "decade"',
              '"A1_excluding_parity_flagged"', '"parity_flagged_items"'):
        assert k in printed, k
    with pytest.raises(SystemExit):
        an.main(["--runs", *paths, "--manifest", str(mpath), "--out", str(out), "--a3-bound-unit", "per-decade",
                 "--items-dir", str(items)])
    # the item folder is required: the check without parity-flagged items is registered
    with pytest.raises(SystemExit) as e:
        an.main(["--runs", *paths, "--manifest", str(mpath), "--out", str(out), "--items-dir", str(tmp_path / "no")])
    assert e.value.code == 2 and "--items-dir: no folder" in capsys.readouterr().err


class _AllRight:
    """Fake scorer: every prompt answered "A" (the correct letter in _jobs_a)."""

    def score(self, text, letters="ABCD"):
        out = {f"logit_{L}": float(L == "A") for L in letters}
        out.update({"n_tokens": 10, "secs": 0.0, "letter_mass": 0.95, "pred_letter": "A"})
        return out


def _jobs_a(repos=("fa", "xa"), n_items=2):
    return [{"item_id": f"{r}/{i:03d}", "repo": r, "group": None, "qtype": "A", "size": 12, "version": v, "perm": 1,
             "correct_letter": "A", "text": f"{r} {i} {v}"} for r in repos for i in range(n_items) for v in an.VERSIONS]


def test_load_runs_refuses_a_second_file_for_a_model(tmp_path):
    import json

    from ngraph import runner as rn

    man = tmp_path / "manifest.json"
    man.write_text(json.dumps({"repos": [{"label": "fa", "group": "familiar", "role": "confirmatory"},
                                         {"label": "xa", "group": "fresh", "role": "confirmatory"}]}))
    jobs = _jobs_a()

    def run(name, tag, **header):
        p = str(tmp_path / name)
        head = {"model_tag": tag, "n_jobs": len(jobs), "settings": {"thought_block": "off", "answer_prefix": ""},
                "answer_prefix_source": {"rule": "ANSWER_PREFIX"}, "model_gguf": {"sha256": "e" * 64},
                "package": {"items_folder": "data/items", "items_digest": "a" * 64}}
        rn.run_jobs(_AllRight(), jobs, p, tag, {**head, **header}, log_every=10_000)
        return p

    e4b, b31 = run("studyA_E4B.jsonl", "E4B"), run("studyA_31B.jsonl", "31B")
    df, report = an.load_runs([e4b, b31], str(man))  # one file per model
    assert set(df["model"]) == {"E4B", "31B"} and len(df) == 2 * len(jobs)
    assert report[e4b]["thought_block"] == "off" and report[e4b]["answer_prefix"] == ""
    assert report[e4b]["answer_prefix_source"] == {"rule": "ANSWER_PREFIX"} and report[e4b]["model_sha256"] == "e" * 64
    assert report[e4b]["package"] == {"items_folder": "data/items", "items_digest": "a" * 64}
    # a pilot or restarted file of the same model, also under a lower-case tag, is refused
    pilot = run("studyA_E4B_pilot.jsonl", "E4B", settings={"thought_block": "off", "answer_prefix": "Answer:"})
    lower = run("run_e4b.jsonl", "e4b")
    for paths in ([e4b, pilot, b31], [lower, e4b]):
        with pytest.raises(ValueError, match="2 run files for model E4B") as e:
            an.load_runs(paths, str(man))
        assert all(p in str(e.value) for p in paths if p != b31) and b31 not in str(e.value)
    # a header without model_tag: the rows' model counts
    untagged = run("untagged.jsonl", "E4B", model_tag=None)
    with pytest.raises(ValueError, match="2 run files for model E4B"):
        an.load_runs([untagged, e4b], str(man))
    # no header line
    no_header = tmp_path / "no_header.jsonl"
    with open(e4b) as fh:
        no_header.write_text("".join(fh.readlines()[1:]))
    with pytest.raises(ValueError, match="no_header.jsonl has no header line"):
        an.load_runs([str(no_header), b31], str(man))
    # rows of two models in one file, and rows of a model other than the header's
    mixed = str(tmp_path / "mixed.jsonl")
    head = {"model_tag": "E2B", "n_jobs": len(jobs), "settings": {"thought_block": "off"}}
    rn.run_jobs(_AllRight(), jobs[:5], mixed, "E2B", head, log_every=10_000)
    rn.run_jobs(_AllRight(), jobs, mixed, "12B", head, log_every=10_000)
    with pytest.raises(ValueError, match=r"mixed.jsonl carry more than one model \(12B, E2B\)"):
        an.load_runs([mixed], str(man))
    other = run("other.jsonl", "12B", model_tag="E2B")
    with pytest.raises(ValueError, match="other.jsonl are for 12B, its header for E2B"):
        an.load_runs([other], str(man))


def test_report_refuses_an_item_folder_the_runs_did_not_use(tmp_path, capsys):
    """--items-dir is compared with the item folder recorded in each run file's first line."""
    import json
    import os

    from ngraph import runner as rn

    repos = {"fa": "familiar", "fb": "familiar", "xa": "fresh", "xb": "fresh"}
    man = tmp_path / "manifest.json"
    man.write_text(json.dumps({"repos": [{"label": r, "group": g, "role": "confirmatory"} for r, g in repos.items()]}))
    items = tmp_path / "items"
    items.mkdir()
    original = json.dumps({"repo": "fa", "items": [{"item_id": "fa/000", "token_parity": {"G2_minus_G1": 3}}]})
    (items / "fa.json").write_text(original)
    st = rn.items_state(str(items))
    assert st["items_folder"] == "outside the package" and len(st["items_digest_outside"]) == 64
    jobs = _jobs_a(tuple(repos))

    def run(name, tag, package):
        p = str(tmp_path / name)
        rn.run_jobs(_AllRight(), jobs, p, tag, {"model_tag": tag, "n_jobs": len(jobs), "package": package,
                                                "settings": {"thought_block": "off"}}, log_every=10_000)
        return p

    e4b, b31 = run("studyA_E4B.jsonl", "E4B", st), run("studyA_31B.jsonl", "31B", {"items_error": "no digest"})
    out = tmp_path / "report.json"
    an.main(["--runs", e4b, b31, "--manifest", str(man), "--n-boot", "50", "--items-dir", str(items),
             "--out", str(out)])
    files = json.loads(out.read_text())["files"]
    assert files[e4b]["items_dir_matches"] is True and files[b31]["items_dir_matches"] is None
    assert an.items_dir_matches({"x": {}}, str(items)) == {"x": None}  # a header without package
    # an edited copy of the item files is refused, and so is the package's own item folder for these runs
    (items / "fa.json").write_text(original + "\n")
    assert an.items_dir_matches({e4b: {"package": st}}, str(items)) == {e4b: False}
    capsys.readouterr()
    with pytest.raises(SystemExit) as e:
        an.main(["--runs", e4b, b31, "--manifest", str(man), "--items-dir", str(items), "--out", str(out)])
    err = capsys.readouterr().err
    assert e.value.code == 2 and "holds other item files than the run files" in err and e4b in err and b31 not in err
    own = os.path.join(rn.PKG_ROOT, "data", "items")
    if os.path.isdir(own):
        assert an.items_dir_matches({e4b: {"package": st}}, own) == {e4b: False}


def _two_repo_manifest(tmp_path):
    import json

    man = tmp_path / "manifest.json"
    man.write_text(json.dumps({"repos": [{"label": "fa", "group": "familiar", "role": "confirmatory"},
                                         {"label": "xa", "group": "fresh", "role": "confirmatory"}]}))
    items = tmp_path / "items"
    items.mkdir()
    (items / "fa.json").write_text(json.dumps({"repo": "fa", "items": [
        {"item_id": "fa/000", "token_parity": {"G2_minus_G1": 0}}]}))
    return man, items


def test_report_lists_sessions_and_warns(tmp_path, capsys):
    """Each run file's sessions (its first line and its _resume lines) are in the report; a file begun before
    any freeze, a file written with more than one code hash, and a session whose code did not match
    CODE_SHA256.txt are warned about on stderr."""
    import json

    from ngraph import runner as rn

    man, items = _two_repo_manifest(tmp_path)
    st = rn.items_state(str(items))
    jobs = _jobs_a()
    frozen = {"prereg/MANIFEST_prereg-v1.0.txt": "e" * 64}

    def head(tag, code, current=True, manifests=frozen):
        return {"model_tag": tag, "n_jobs": len(jobs), "settings": {"thought_block": "off"},
                "package": dict(st, code_hash=code, code_sha256_current=current, manifests=manifests)}

    e4b, b31 = str(tmp_path / "studyA_E4B.jsonl"), str(tmp_path / "studyA_31B.jsonl")
    rn.run_jobs(_AllRight(), jobs[:3], e4b, "E4B", head("E4B", "c" * 64), log_every=10_000)
    rn.run_jobs(_AllRight(), jobs, e4b, "E4B", head("E4B", "d" * 64, current=False), log_every=10_000)
    rn.run_jobs(_AllRight(), jobs, b31, "31B", head("31B", "c" * 64, manifests={}), log_every=10_000)
    df, report = an.load_runs([e4b, b31], str(man))
    ss = report[e4b]["sessions"]
    assert [s["code_hash"] for s in ss] == ["c" * 64, "d" * 64] and ss[0]["utc"] is None and ss[1]["utc"]
    assert ss[1]["code_sha256_current"] is False and ss[1]["manifests"] == frozen
    assert report[b31]["sessions"] == [{"utc": None, "code_hash": "c" * 64, "code_sha256_current": True,
                                        "manifests": {}}]
    warnings = an.session_warnings(report)
    assert warnings == [
        f"{e4b}: written in sessions with 2 different code hashes (cccccccccccc..., dddddddddddd...; see its sessions)",
        f"{e4b}: in session(s) 2 of 2 the code did not match CODE_SHA256.txt (code_sha256_current not true)",
        f"{b31}: its first line records no manifest in prereg/ (begun before any freeze: a pilot)"]
    out = tmp_path / "new_folder" / "report.json"  # the report's folder is made
    an.main(["--runs", e4b, b31, "--manifest", str(man), "--n-boot", "50", "--items-dir", str(items),
             "--out", str(out)])
    captured = capsys.readouterr()
    assert all(f"warning: {w}" in captured.err for w in warnings)
    assert json.loads(out.read_text())["files"][e4b]["sessions"][1]["code_hash"] == "d" * 64
    assert '"sessions"' not in captured.out  # the console summary leaves them out


def test_report_refuses_an_item_folder_that_cannot_be_digested(tmp_path, capsys):
    import os

    from ngraph import runner as rn

    man, items = _two_repo_manifest(tmp_path)
    jobs = _jobs_a()
    e4b = str(tmp_path / "studyA_E4B.jsonl")
    rn.run_jobs(_AllRight(), jobs, e4b, "E4B", {"model_tag": "E4B", "n_jobs": len(jobs), "settings": {
        "thought_block": "off"}, "package": rn.items_state(str(items))}, log_every=10_000)
    try:
        os.symlink(items / "fa.json", items / "link.txt")  # refused by the digest; not an item file (*.json)
    except (OSError, NotImplementedError):
        pytest.skip("symbolic links are not available here")
    assert rn.items_state(str(items))["items_error"]
    with pytest.raises(SystemExit) as e:
        an.main(["--runs", e4b, "--manifest", str(man), "--items-dir", str(items), "--out", str(tmp_path / "r.json")])
    err = capsys.readouterr().err
    assert e.value.code == 2 and "cannot be digested" in err and e4b in err


def test_parity_flagged_items(tmp_path, capsys):
    import json

    assert an.PARITY_TOL == 2  # the registered tolerance, taken from ngraph.items
    gaps = {"fa": [3, -2, 0, 2], "xa": [-3, 2, 5, -1]}
    for repo, gs in gaps.items():
        (tmp_path / f"{repo}.json").write_text(json.dumps({"repo": repo, "items": [
            {"item_id": f"{repo}/{i:03d}", "token_parity": {"G2_minus_G1_before": 9, "G2_minus_G1": g, "draws": 4,
                                                            "G4_minus_G3": 7}} for i, g in enumerate(gs)]}))
    (tmp_path / "notes.txt").write_text("not an item file")
    assert an.parity_flagged_items(str(tmp_path)) == {"fa/000", "xa/000", "xa/002"}
    with pytest.raises(FileNotFoundError, match="no folder"):
        an.parity_flagged_items(str(tmp_path / "missing"))
    (tmp_path / "empty").mkdir()
    with pytest.raises(FileNotFoundError, match="no item files"):
        an.parity_flagged_items(str(tmp_path / "empty"))
    # a JSON file that is not an item file is named, also by the report's command line
    (tmp_path / "zz_other.json").write_text(json.dumps({"repos": []}))
    with pytest.raises(ValueError, match=r"zz_other.json is not an item file \(no items with "
                                         r"token_parity.G2_minus_G1; KeyError"):
        an.parity_flagged_items(str(tmp_path))
    with pytest.raises(SystemExit) as e:
        an.main(["--runs", "x.jsonl", "--manifest", "m.json", "--items-dir", str(tmp_path),
                 "--out", str(tmp_path / "r.json")])
    assert e.value.code == 2 and "zz_other.json is not an item file" in capsys.readouterr().err


def test_a1_excluding_parity_flagged_items():
    """Constructed example: I = 1 for item 0 of every repository (G2 wrong) and for item 1 of fa and xa
    (G3 wrong), else 0. A1 = mean(1/2, 1/4, 1/2, 1/4) = 3/8; without item 0: mean(1/3, 0, 1/3, 0) = 1/6."""
    rows = []
    for repo, group in (("fa", "familiar"), ("fb", "familiar"), ("xa", "fresh"), ("xb", "fresh")):
        for i in range(4):
            for model in ("E4B", "31B"):
                for v in an.VERSIONS:
                    wrong = (i == 0 and v == "G2") or (i == 1 and repo in ("fa", "xa") and v == "G3")
                    rows.append({"model": model, "repo": repo, "group": group, "item_id": f"{repo}/{i:03d}",
                                 "version": v, "perm": 1, "correct": int(not wrong), "p_correct": float(not wrong),
                                 "letter_mass": 0.95})
    df = pd.DataFrame(rows)
    flagged = {f"{r}/000" for r in ("fa", "fb", "xa", "xb")} | {"elsewhere/000"}
    res = an.study_a_report(df, n_boot=200, flagged_items=flagged)
    assert res["A1"]["estimate"] == pytest.approx(3 / 8)
    assert res["A1_excluding_parity_flagged"]["estimate"] == pytest.approx(1 / 6)
    assert res["A1_excluding_parity_flagged"]["n_clusters"] == 4
    assert res["parity_flagged_items"] == {"n": 4, "rule": an.PARITY_FLAG_RULE}
    assert "PARITY_TOL (2)" in an.PARITY_FLAG_RULE
    res0 = an.study_a_report(df, n_boot=200)
    assert "A1_excluding_parity_flagged" not in res0 and "parity_flagged_items" not in res0
    assert res0["A1"] == res["A1"]


def test_tost_matches_statsmodels():
    """Our TOST p-values against statsmodels' implementations (one-sample and Welch two-sample)."""
    from statsmodels.stats.weightstats import DescrStatsW, ttost_ind

    rng = np.random.default_rng(8)
    v = rng.normal(0.01, 0.06, 32)
    assert an.tost_mean(v, 0.05)["p_tost"] == pytest.approx(DescrStatsW(v).ttost_mean(-0.05, 0.05)[0], rel=1e-9)
    a, b = rng.normal(0.01, 0.05, 16), rng.normal(-0.005, 0.08, 16)
    r = an.tost_two_sample(a, b, 0.05)
    assert r["p_tost"] == pytest.approx(ttost_ind(a, b, -0.05, 0.05, usevar="unequal")[0], rel=1e-9)
    assert r["ci90"][0] < float(a.mean() - b.mean()) < r["ci90"][1]
    assert not an.tost_two_sample(a + 0.2, b, 0.05)["equivalent_at_0.05"]
    assert an.TOST_BOUND == 0.05


def test_tost_two_sample_unequal_n_matches_statsmodels():
    """Welch TOST with unequal group sizes and variances: p, 90% CI and Welch-Satterthwaite df."""
    from statsmodels.stats.weightstats import CompareMeans, DescrStatsW, ttost_ind

    rng = np.random.default_rng(21)
    a, b = rng.normal(0.01, 0.03, 7), rng.normal(-0.01, 0.09, 19)
    r = an.tost_two_sample(a, b, 0.05)
    cm = CompareMeans(DescrStatsW(a), DescrStatsW(b))
    assert r["p_tost"] == pytest.approx(ttost_ind(a, b, -0.05, 0.05, usevar="unequal")[0], rel=1e-9)
    assert r["ci90"] == pytest.approx(cm.tconfint_diff(alpha=0.10, usevar="unequal"), rel=1e-9)
    assert r["df_welch"] == pytest.approx(cm.dof_satt(), rel=1e-12)
    assert 0.001 < r["p_tost"] < 0.999  # not at an edge, so the comparison is informative


def test_tost_two_sample_constant_groups():
    """One constant group: df = n_other - 1 and p as statsmodels. Both constant: deterministic verdict."""
    from statsmodels.stats.weightstats import ttost_ind

    other, const = np.random.default_rng(22).normal(0.01, 0.06, 19), np.zeros(7)
    for a, b in ((const, other), (other, const)):
        r = an.tost_two_sample(a, b, 0.05)
        assert r["df_welch"] == pytest.approx(len(other) - 1)
        assert r["p_tost"] == pytest.approx(ttost_ind(a, b, -0.05, 0.05, usevar="unequal")[0], rel=1e-9)
    r = an.tost_two_sample(np.full(5, 0.02), np.zeros(9), 0.05)
    assert r["p_tost"] == 0.0 and r["equivalent_at_0.05"] and r["ci90"] == pytest.approx((0.02, 0.02))
    assert "df_welch" not in r
    r = an.tost_two_sample(np.full(5, 0.08), np.zeros(9), 0.05)
    assert r["p_tost"] == 1.0 and not r["equivalent_at_0.05"]


def test_tost_mean_ci90_matches_statsmodels():
    from statsmodels.stats.weightstats import DescrStatsW

    v = np.random.default_rng(23).normal(0.01, 0.05, 11)
    r = an.tost_mean(v, 0.05)
    assert r["ci90"] == pytest.approx(DescrStatsW(v).tconfint_mean(alpha=0.10), rel=1e-9)
    assert r["p_tost"] == pytest.approx(DescrStatsW(v).ttost_mean(-0.05, 0.05)[0], rel=1e-9)


def _reference_slopes(df, params):
    """Per-repository A3 slopes computed independently: CC = G4 - G3 per item and model (permutations
    averaged), mean per repository and model, then scipy's linregress on log10(parameters)."""
    d = df[df["model"].isin(params)]
    s = d.groupby(["repo", "group", "item_id", "model", "version"])["correct"].mean().unstack("version")
    cc = (s["G4"] - s["G3"]).groupby(["repo", "group", "model"]).mean().reset_index(name="CC")
    out = {}
    for (repo, group), g in cc.groupby(["repo", "group"]):
        x = np.log10(g["model"].map(params).astype(float).to_numpy())
        out[repo] = (group, float(stats.linregress(x, g["CC"].to_numpy()).slope))
    return out


def test_a3_slopes_bound_units_and_descriptive_difference():
    from statsmodels.stats.weightstats import CompareMeans, DescrStatsW

    df = sim.simulate_a_df(n_repos=8, n_items=6, seed=4)
    params = an.A3_PARAMS_EFFECTIVE
    ref = _reference_slopes(df, params)
    sl = an.a3_slopes(df, params).set_index("repo")
    assert sorted(sl.index) == sorted(ref)
    for repo, (group, slope) in ref.items():
        assert sl.loc[repo, "group"] == group
        assert sl.loc[repo, "slope"] == pytest.approx(slope, rel=1e-9, abs=1e-12)
    slopes = np.array([s for _, s in ref.values()])
    span = math.log10(30.7e9 / 2.3e9)  # E2B to 31B on the effective axis: 1.1254 decades
    assert an.A3_BOUND_UNIT == "span"
    for unit, b in (("span", 0.05 / span), ("decade", 0.05)):
        r = an.a3(df, params, n_boot=200, bound=0.05, bound_unit=unit)
        assert r["estimate"] == pytest.approx(slopes.mean(), rel=1e-9)
        t = r["tost"]
        assert t["p_tost"] == pytest.approx(DescrStatsW(slopes).ttost_mean(-b, b)[0], rel=1e-9)
        assert t["bound_unit"] == unit and t["span_decades"] == pytest.approx(span)
        assert t["bound_slope_per_decade"] == pytest.approx(b)
        assert t["bound_cc_change_over_span"] == pytest.approx(b * span)
    assert an.a3(df, params, n_boot=200)["tost"]["bound_unit"] == "span"  # the default
    # familiar minus fresh: descriptive, Welch 95% CI on the difference of mean slopes, no p-value
    fam = np.array([s for g, s in ref.values() if g == "familiar"])
    fre = np.array([s for g, s in ref.values() if g == "fresh"])
    fmf = r["familiar_minus_fresh"]
    assert fmf["descriptive"] is True and "p" not in fmf
    assert fmf["estimate"] == pytest.approx(fam.mean() - fre.mean(), rel=1e-9)
    ci = CompareMeans(DescrStatsW(fam), DescrStatsW(fre)).tconfint_diff(alpha=0.05, usevar="unequal")
    assert fmf["ci95"] == pytest.approx(ci, rel=1e-9)
    # E2B, E4B and 12B only: the span is that of the models present
    three = df[df["model"].isin(["E2B", "E4B", "12B"])]
    span3 = math.log10(11.95e9 / 2.3e9)  # 0.7156 decades
    r3 = an.a3(three, params, n_boot=200)
    assert r3["tost"]["span_decades"] == pytest.approx(span3)
    assert r3["tost"]["bound_cc_change_over_span"] == pytest.approx(0.05)
    slopes3 = np.array([s for _, s in _reference_slopes(three, params).values()])
    assert r3["tost"]["p_tost"] == pytest.approx(DescrStatsW(slopes3).ttost_mean(-0.05 / span3, 0.05 / span3)[0],
                                                 rel=1e-9)
    r3g = an.a3(three, an.A3_PARAMS_GGUF_TEXT, n_boot=200)
    assert r3g["tost"]["span_decades"] == pytest.approx(math.log10(11_907_350_576 / 4_628_569_635))  # 0.4104
    with pytest.raises(ValueError):
        an.a3(df, params, n_boot=200, bound_unit="per-decade")
    with pytest.raises(ValueError):  # one parameter value: no slope
        an.a3(df[df["model"] == "E4B"], params, n_boot=200)


def test_study_a_report_tags_registered_models_and_bound_unit(capsys):
    df = sim.simulate_a_df(n_repos=6, n_items=5, delta=0.05, seed=6)
    df["letter_mass"] = 0.95
    # lower-case tags are normalised: A3 runs on both axes and nothing is excluded
    res = an.study_a_report(df.assign(model=df["model"].str.lower()), n_boot=200)
    assert res["models"] == sorted(an.REGISTERED_MODELS) and res["excluded_models"] == []
    assert sorted(res["A3"]["axis"]) == sorted(an.REGISTERED_MODELS)
    assert res["A3"]["role"] == "registered axis: decides 'flat'"
    assert res["A3_sensitivity"]["role"] == "sensitivity axis: reported next to A3; does not decide 'flat'"
    assert res["A3"]["models_not_on_axis"] == [] and res["A3_sensitivity"]["models_not_on_axis"] == []
    assert res["A3"]["tost"]["bound_unit"] == "span" == res["A3_sensitivity"]["tost"]["bound_unit"]
    assert capsys.readouterr().err == ""
    # an unregistered model (26B-A4B, backup B-3), even with a parameter count on the axis:
    # descriptive tables only, a warning on stderr
    extra = df[df["model"] == "31B"].assign(model="26b-a4b", correct=1, p_correct=0.99)
    res2 = an.study_a_report(pd.concat([df, extra], ignore_index=True),
                             params={**an.A3_PARAMS_EFFECTIVE, "26B-A4B": 25.2e9}, n_boot=200)
    assert "26B-A4B" in capsys.readouterr().err
    assert res2["excluded_models"] == ["26B-A4B"] and "26B-A4B" in res2["models"]
    assert res2["accuracy"]["26B-A4B"]["G3"] == 1.0 and "26B-A4B" in res2["letter_mass_share_ge_0.9"]
    for key in ("A1", "A1_p_correct", "A2", "A3", "A3_sensitivity"):
        assert res2[key]["estimate"] == pytest.approx(res[key]["estimate"]), key
    assert "26B-A4B" not in res2["A1"]["per_model"] and "26B-A4B" not in res2["A3"]["axis"]
    assert "error" not in res2["A1_gee"] and res2["A1_gee"] == res["A1_gee"]
    # the switch applies to both axes; an axis that lacks a registered model says so
    res3 = an.study_a_report(df, params={"E2B": 2.3e9, "E4B": 4.5e9, "31B": 30.7e9}, n_boot=200,
                             bound_unit="decade")
    assert res3["A3"]["tost"]["bound_unit"] == "decade" == res3["A3_sensitivity"]["tost"]["bound_unit"]
    assert res3["A3"]["tost"]["bound_slope_per_decade"] == 0.05
    assert res3["A3"]["models_not_on_axis"] == ["12B"] and res3["A3_sensitivity"]["models_not_on_axis"] == []
    # fewer than two parameter values on an axis: that A3 is left out
    res4 = an.study_a_report(df, params_sensitivity={"e4b": 7_463_013_674}, n_boot=200)
    assert "A3" in res4 and "A3_sensitivity" not in res4
    with pytest.raises(ValueError):
        an.study_a_report(df, n_boot=200, bound_unit="per-decade")
