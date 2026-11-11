"""Hash-only time-stamp: manifest gates, verify, chain, digest, CODE_SHA256.txt, snapshot and CLI."""

import hashlib
import json
import os
import shutil
import subprocess
import tarfile

import pytest

from ngraph import commit as cm

PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DRAFT = "prereg/PREREGISTRATION.md"


def _tree(tmp_path, status="prereg-v1.0"):
    root = tmp_path / "pkg"
    files = {
        "README.md": "readme\n",
        "CODE_SHA256.txt": "",
        "src/ngraph/a.py": "x = 1\n",
        "tests/test_a.py": "def test(): pass\n",
        "data/items/r1.json": '{"a": 1}',
        "data/items/r2.json": '{"a": 2}',
        DRAFT: f"Status: {status}, frozen 8 Nov 2026 (UTC)\n\nplan [TBD-B: pools]\n",
        "runs/.keep": "",
        "runs/out.jsonl": "{}\n",
        ".venv/bin/python": "binary",
        "src/ngraph/__pycache__/a.cpython-313.pyc": "pyc",
        "data/.DS_Store": "finder",
        ".pytest_cache/v": "cache",
    }
    for rel, text in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    _refresh_code(root)
    return root


def _refresh_code(root):
    (root / "CODE_SHA256.txt").write_text(cm.code_sha256_text(str(root)))


def _manifest_files(root):
    return sorted(p.name for p in (root / "prereg").iterdir() if p.name.startswith("MANIFEST_"))


def test_list_files_skips_outputs_caches_and_venv(tmp_path):
    root = _tree(tmp_path)
    assert cm.list_files(str(root)) == ["CODE_SHA256.txt", "README.md", "data/items/r1.json", "data/items/r2.json",
                                        DRAFT, "src/ngraph/a.py", "tests/test_a.py"]
    code = (root / "CODE_SHA256.txt").read_text().splitlines()
    assert [x.split("  ")[1] for x in code] == ["./README.md", "./src/ngraph/a.py", "./tests/test_a.py"]
    assert cm.skipped_counts(str(root)) == {".venv/": 1, "runs/": 2}


def test_symlinks_line_breaks_and_large_files_are_refused(tmp_path, monkeypatch):
    root = _tree(tmp_path)
    files = cm.list_files(str(root))
    os.symlink(root / "README.md", root / "link.md")
    with pytest.raises(ValueError, match="symbolic link"):
        cm.list_files(str(root))
    (root / "link.md").unlink()
    (root / "data" / "Icon\r").write_text("")  # what Finder writes for a custom folder icon
    with pytest.raises(ValueError, match="line break"):
        cm.list_files(str(root))
    (root / "data" / "Icon\r").unlink()
    for name in ("a\x0cb.json", "notes\u2028"):  # any character at which str.splitlines() splits, also at the end
        (root / "data" / name).write_text("")
        with pytest.raises(ValueError, match="file name with a line break"):
            cm.list_files(str(root))
        (root / "data" / name).unlink()
    (root / "data" / "old\u2028").mkdir()
    with pytest.raises(ValueError, match="folder name with a line break"):
        cm.list_files(str(root))
    # with a dict, each refused path is recorded as "path: reason" and left out
    os.symlink(root / "README.md", root / "link.md")
    (root / "data" / "Icon\r").write_text("")
    refused = {}
    assert cm.list_files(str(root), refused=refused) == files
    assert refused == {"data/Icon\r": "'data/Icon\\r': file name with a line break (Finder makes 'Icon\\r' for a "
                                      "custom folder icon; remove it)",
                       "data/old\u2028": "'data/old\\u2028': folder name with a line break",
                       "link.md": "link.md: symbolic link"}
    monkeypatch.setattr(cm, "MAX_FILE_BYTES", 10)
    with pytest.raises(ValueError, match="stay outside this folder"):
        cm.list_files(str(root))


def test_manifest_verify_and_post(tmp_path):
    root = _tree(tmp_path)
    res = cm.write_manifest(str(root), "prereg-v1.0")
    path = root / "prereg" / "MANIFEST_prereg-v1.0.txt"
    assert res["manifest"] == "prereg/MANIFEST_prereg-v1.0.txt" and res["files"] == 7
    assert res["manifest_sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert res["tbd_markers_left"] == [f"{DRAFT}:3: [TBD-B: pools]"]
    assert res["code_hash"] == hashlib.sha256((root / "CODE_SHA256.txt").read_bytes()).hexdigest()
    assert res["items_digest"] == cm.digest(str(root), "data/items")["digest"]
    assert res["skipped_not_hashed"] == {".venv/": 1, "runs/": 2}
    text = path.read_text()
    assert text.startswith(cm.HEADER_TITLE + "\n# label: prereg-v1.0\n# files: 7\n")
    body = [x for x in text.splitlines() if not x.startswith("#")]
    for line in body:  # sha256sum format
        h, rel = line.split("  ", 1)
        assert h == hashlib.sha256((root / rel).read_bytes()).hexdigest()
    ok = cm.verify(str(root), str(path), expect=res["manifest_sha256"].upper())
    assert ok["ok"] and ok["not_listed"] == [] and ok["matches_expected"] and ok["chain_ok"]
    post = cm.post_text(str(path))
    assert "NEW TOPIC" in post and "Title: Pre-registration hash" in post
    assert res["manifest_sha256"] in post and "prereg-v1.0" in post
    assert "graph" not in post.lower() and "gemma" not in post.lower()
    with pytest.raises(ValueError):  # the first manifest is not a reply
        cm.post_text(str(path), reply=True)
    with pytest.raises(FileExistsError) as exists:  # a manifest is never rewritten
        cm.write_manifest(str(root), "prereg-v1.0")
    assert cm.write_manifest(str(root), "prereg-v1.0", check_only=True)["problems"] == [str(exists.value)]
    assert cm.write_manifest(str(root), "prereg-v1.0", check_only=True, force=True)["ok"]
    # outputs and caches can change without touching the commitment
    (root / "runs" / "more.json").write_text("{}")
    assert cm.verify(str(root), str(path))["ok"]
    # a changed, a removed and a new file
    (root / "data" / "items" / "r1.json").write_text('{"a": 9}')
    (root / "tests" / "test_a.py").unlink()
    (root / "notes.md").write_text("later\n")
    bad = cm.verify(str(root), str(path), expect=res["manifest_sha256"])
    assert not bad["ok"] and bad["mismatched"] == ["data/items/r1.json"] and bad["missing"] == ["tests/test_a.py"]
    assert bad["not_listed"] == ["notes.md"]
    assert not cm.verify(str(root), str(path), expect="0" * 64)["matches_expected"]
    assert cm.diff(str(root), str(path)) == {"since": "prereg-v1.0", "changed": ["data/items/r1.json"],
                                             "added": ["notes.md"], "removed": ["tests/test_a.py"]}


def _sparse(path, size=101 * 1024 * 1024):
    with open(path, "wb") as fh:  # takes no disk space
        fh.truncate(size)


def test_verify_reports_refused_paths_that_are_not_listed(tmp_path, capsys):
    root = _tree(tmp_path)
    res = cm.write_manifest(str(root), "prereg-v1.0")
    (tmp_path / "models").mkdir()
    os.symlink(tmp_path / "models", root / "models")  # a convenience link to a folder
    os.symlink(root / "README.md", root / "link.md")
    _sparse(root / "model.gguf")
    v = cm.verify(str(root), res["manifest"], expect=res["manifest_sha256"])
    assert v["ok"] and v["not_listed"] == [] and v["matches_expected"]
    assert sorted(v["not_listed_refused"]) == [
        "link.md: symbolic link",
        "model.gguf: larger than 100 MB (model files and competition data stay outside this folder)",
        "models: symbolic link to a folder"]
    assert cm.main(["post", "--root", str(root), "--manifest", res["manifest"]]) == 0
    assert res["manifest_sha256"] in capsys.readouterr().out
    # a listed file that became a symbolic link is missing, not refused
    (root / "README.md").rename(root / "README.txt")
    os.symlink(root / "README.txt", root / "README.md")
    v = cm.verify(str(root), res["manifest"])
    assert not v["ok"] and v["missing"] == ["README.md"] and v["not_listed"] == ["README.txt"]
    assert not any(t.startswith("README.md:") for t in v["not_listed_refused"])


def test_freeze_gates_refuse_and_write_nothing(tmp_path):
    root = _tree(tmp_path)
    draft = root / DRAFT
    readme = root / "README.md"

    def problems(**kw):
        res = cm.write_manifest(str(root), "prereg-v1.0", check_only=True, **kw)
        assert not (root / "prereg" / "MANIFEST_prereg-v1.0.txt").exists()
        return res["problems"]

    assert problems() == []
    draft.write_text("Status: prereg-v1.0, frozen\nsizes [TBD: pilot]\nmore [TBD-B: pools]\n")
    assert problems() == [f"{DRAFT}:2: [TBD: pilot]"]
    assert problems(allow_tbd=True) == []
    draft.write_text("**DRAFT v0, not posted.**\n## 13. Open before posting\n")
    out = problems()
    assert any("starts with 'Status: prereg-v1.0'" in p for p in out)
    assert any(p.startswith(f"{DRAFT}:1: draft-only text left: 'DRAFT v0'") for p in out)
    assert any(p.startswith(f"{DRAFT}:2: draft-only text left: 'Open before posting'") for p in out)
    for line in ("Status: prereg-v1.0-rc, frozen", "Status: prereg-v1.0.1"):  # another label does not count
        draft.write_text(line + "\n")
        assert any("must not run on into more letters, digits, underscores, hyphens or dotted parts" in p
                   for p in problems())
    for line in ("Status: prereg-v1.0.", "**Status: prereg-v1.0.** Frozen 8 Nov 2026 (UTC)."):  # sentence ends
        draft.write_text(line + "\n")
        assert problems() == []
    draft.write_text("Status: prereg-v1.0, frozen\n")
    readme.write_text("Draft pre-registration (v0, not posted)\n")
    _refresh_code(root)
    assert problems() == ["README.md:1: draft-only text left: 'v0, not posted'"]
    with pytest.raises(RuntimeError, match="manifest not written"):
        cm.write_manifest(str(root), "prereg-v1.0")
    assert _manifest_files(root) == []


def test_check_only_lists_every_problem(tmp_path, capsys):
    root = _tree(tmp_path)
    (root / DRAFT).write_text("no status line\n")
    os.symlink(root / "README.md", root / "src" / "link.md")
    (root / "prereg" / "Icon\r").write_text("")  # in prereg/, which the text and chain checks walk too
    _sparse(root / "data" / "items" / "big.bin")
    res = cm.write_manifest(str(root), "prereg-v1.0", check_only=True)
    assert not res["ok"] and len(res["problems"]) == 4
    assert res["problems"][:3] == [
        "refused: data/items/big.bin: larger than 100 MB (model files and competition data stay outside this folder)",
        "refused: 'prereg/Icon\\r': file name with a line break (Finder makes 'Icon\\r' for a custom folder icon; "
        "remove it)",
        "refused: src/link.md: symbolic link"]
    assert res["problems"][3].startswith("no line in prereg/*.md starts with 'Status: prereg-v1.0'")
    assert cm.main(["--root", str(root), "manifest", "--label", "prereg-v1.0", "--check-only"]) == 1
    assert json.loads(capsys.readouterr().out)["problems"] == res["problems"]
    with pytest.raises(RuntimeError) as e:  # the real run lists them all and writes nothing
        cm.write_manifest(str(root), "prereg-v1.0")
    assert all(p in str(e.value) for p in res["problems"]) and _manifest_files(root) == []


def test_hidden_files_block_the_freeze(tmp_path):
    """A listed file or folder whose name starts with "." would be hashed and released with the paper."""
    root = _tree(tmp_path)
    for rel in (".env", "src/.github/workflows/ci.yml", "src/.github/README", "data/items/.notes.json"):
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("x\n")
    _refresh_code(root)
    problems = cm.write_manifest(str(root), "prereg-v1.0", check_only=True)["problems"]
    assert problems == [f"hidden file or folder: {h} (move it outside the package: every listed file is hashed "
                        "and released)" for h in (".env", "data/items/.notes.json", "src/.github/")]
    with pytest.raises(RuntimeError, match="hidden file or folder: .env "):
        cm.write_manifest(str(root), "prereg-v1.0")
    assert _manifest_files(root) == []
    assert cm.hidden_paths(["a/b", ".x", "a/.y/z", "a/.y/w", "a/b.c"]) == [".x", "a/.y/"]


def test_cli_errors_are_messages(tmp_path, capsys):
    """Every command prints an error as one message with the command's name, not a traceback."""
    root = _tree(tmp_path)
    assert cm.main(["verify", "--root", str(root), "--manifest", "prereg/MANIFEST_missing.txt"]) == 1
    err = capsys.readouterr().err
    assert err.startswith("verify: ") and "MANIFEST_missing.txt" in err and "Traceback" not in err
    res = cm.write_manifest(str(root), "prereg-v1.0")
    (root / "README.md").write_text("changed\n")
    out = tmp_path / "frozen" / "v1.tar.gz"
    assert cm.main(["snapshot", "--root", str(root), "--manifest", res["manifest"], "--out", str(out)]) == 1
    err = capsys.readouterr().err
    assert ("snapshot: snapshot not written: the files no longer match the manifest (mismatched (1): README.md); "
            "run verify for the full report") in err
    assert not out.exists() and not os.path.exists(str(out) + ".part")


def test_pending_text_in_code_files_blocks_the_freeze(tmp_path):
    root = _tree(tmp_path)
    (root / "src" / "ngraph" / "analysis.py").write_text("x = 1\n# Open before posting: settle the axis\n")
    (root / "src" / "ngraph" / "runner.py").write_text("# Open before posting\n")
    # commit.py holds the strings as constants and is never scanned
    (root / "src" / "ngraph" / "commit.py").write_text('DRAFT_ONLY = ("DRAFT v0", "Open before posting")\n')
    _refresh_code(root)
    assert cm.write_manifest(str(root), "prereg-v1.0", check_only=True)["problems"] == [
        "src/ngraph/analysis.py:2: draft-only text left: 'Open before posting'",
        "src/ngraph/runner.py:1: draft-only text left: 'Open before posting'"]


def test_cited_hashes_must_be_current(tmp_path):
    root = _tree(tmp_path)
    code = cm.code_hash(str(root))
    items = cm.digest(str(root), "data/items")["digest"]
    readme = hashlib.sha256((root / "README.md").read_bytes()).hexdigest()
    r1 = hashlib.sha256((root / "data" / "items" / "r1.json").read_bytes()).hexdigest()
    draft = root / DRAFT
    good = (f"Status: prereg-v1.0, frozen\n"
            f"| Code | `CODE_SHA256.txt` | `{code}` |\n"
            f"| Items | `data/items/` (`python -m ngraph.commit digest data/items`) | `{items}` |\n"
            f"`data/items/` (`python -m ngraph.commit digest data/items`) | {items}\n"
            f"Item digest: data/items {items}\n"
            f"One item: `data/items/r1.json` {r1}\n"  # an item file, not the folder
            f"One item: data/items/r1.json {r1}\n"
            f"README `README.md` {readme.upper()}\n"
            f"| E2B | `gemma-4-E2B_q4_0-it.gguf` | `{'a' * 64}` |\n"  # outside the package: not checked
            f"earlier code hash {code[:12]}... (shortened, not checked)\n")
    draft.write_text(good)
    assert cm.write_manifest(str(root), "prereg-v1.0", check_only=True)["problems"] == []
    (root / "src" / "ngraph" / "a.py").write_text("x = 2\n")
    _refresh_code(root)  # the code hash changes, the draft still cites the old one
    out = cm.write_manifest(str(root), "prereg-v1.0", check_only=True)["problems"]
    assert out == [f"{DRAFT}:2: cites {code[:12]}... for CODE_SHA256.txt, but its current hash is "
                   f"{cm.code_hash(str(root))[:12]}... (write an earlier value shortened)"]
    draft.write_text(f"Status: prereg-v1.0, frozen\n`CODE_SHA256.txt` and `data/items/`: `{items}`\n")
    out = cm.write_manifest(str(root), "prereg-v1.0", check_only=True)["problems"]
    assert out == [f"{DRAFT}:2: a hash next to several package files (CODE_SHA256.txt, data/items); "
                   "give each its own line"]
    draft.write_text(f"Status: prereg-v1.0, frozen\nItem digest: data/items {'0' * 64}\n")
    out = cm.write_manifest(str(root), "prereg-v1.0", check_only=True)["problems"]
    assert out == [f"{DRAFT}:2: cites {'0' * 12}... for data/items, but its current hash is {items[:12]}... "
                   "(write an earlier value shortened)"]


def test_stale_or_crlf_code_hashes_block_the_manifest(tmp_path):
    root = _tree(tmp_path)
    (root / "src" / "ngraph" / "a.py").write_text("x = 2\n")
    assert not cm.check_code_sha256(str(root))["ok"]
    with pytest.raises(RuntimeError, match="CODE_SHA256.txt is not current"):
        cm.write_manifest(str(root), "prereg-v1.0")
    _refresh_code(root)
    assert cm.check_code_sha256(str(root))["ok"]
    crlf = (root / "CODE_SHA256.txt").read_bytes().replace(b"\n", b"\r\n")
    (root / "CODE_SHA256.txt").write_bytes(crlf)
    res = cm.check_code_sha256(str(root))
    assert not res["ok"] and "line endings" in res["note"]
    with pytest.raises(ValueError):
        cm.manifest_text(str(root), "bad label")


def test_addendum_follows_the_posted_hash_and_lists_changes(tmp_path):
    root = _tree(tmp_path)
    first = cm.write_manifest(str(root), "prereg-v1.0")
    h1 = first["manifest_sha256"]
    (root / "src" / "ngraph" / "a.py").write_text("x = 2\n")
    _refresh_code(root)
    (root / "prereg" / "ADDENDUM.md").write_text("Status: prereg-v1.1, frozen 9 Nov 2026 (UTC)\nstudy B\n")
    with pytest.raises(RuntimeError, match="needs --follows .*; delete a trial manifest only if it was never posted"):
        cm.write_manifest(str(root), "prereg-v1.1")
    with pytest.raises(RuntimeError, match="no manifest in prereg/ has the SHA-256") as e:
        cm.write_manifest(str(root), "prereg-v1.1", follows="0" * 64)
    assert f"({'0' * 64}; found: prereg/MANIFEST_prereg-v1.0.txt {h1})" in str(e.value)  # both hashes in full
    with pytest.raises(RuntimeError, match=r"\[TBD-B: pools\]"):  # at the addendum no marker may stay
        cm.write_manifest(str(root), "prereg-v1.1", follows=h1)
    (root / DRAFT).write_text("Status: prereg-v1.0, frozen 8 Nov 2026 (UTC)\n\nplan: pools in the addendum\n")
    second = cm.write_manifest(str(root), "prereg-v1.1", follows=h1.upper())
    path2 = root / "prereg" / "MANIFEST_prereg-v1.1.txt"
    text = path2.read_text()
    assert f"# follows: prereg-v1.0 {h1}\n" in text
    assert "# changes since prereg-v1.0: 3 changed, 1 added, 0 removed\n" in text
    assert second["changes"] == {"changed": ["CODE_SHA256.txt", DRAFT, "src/ngraph/a.py"],
                                 "added": ["prereg/ADDENDUM.md"], "removed": []}
    assert "# changed: src/ngraph/a.py\n# added: prereg/ADDENDUM.md\n" in text
    assert f"{h1}  prereg/MANIFEST_prereg-v1.0.txt" in text and "MANIFEST_prereg-v1.1.txt" not in text
    v2 = cm.verify(str(root), str(path2), expect=second["manifest_sha256"])
    assert v2["ok"] and v2["chain_ok"] and v2["changes_match_header"] and v2["follows"]["sha256"] == h1
    reply = cm.post_text(str(path2))
    assert "REPLY" in reply and second["manifest_sha256"] in reply and "prereg-v1.1 (addendum)" in reply
    with pytest.raises(ValueError):  # an addendum is never a new topic
        cm.post_text(str(path2), reply=False)
    v1 = cm.verify(str(root), str(root / "prereg" / "MANIFEST_prereg-v1.0.txt"))
    assert not v1["ok"] and set(v1["mismatched"]) >= {"CODE_SHA256.txt", "src/ngraph/a.py"}
    assert v1["not_listed"] == ["prereg/ADDENDUM.md", "prereg/MANIFEST_prereg-v1.1.txt"]
    # the posted v1.0 cannot be replaced once v1.1 follows it
    with pytest.raises(RuntimeError, match="follows prereg/MANIFEST_prereg-v1.0.txt"):
        cm.write_manifest(str(root), "prereg-v1.0", force=True, allow_tbd=True)
    # a hand-edited list of changes is caught
    lines = text.splitlines(keepends=True)
    path2.write_text("".join(x for x in lines if not x.startswith("# added: ")))
    assert not cm.verify(str(root), str(path2))["chain_ok"]


def test_trial_manifest_blocks_the_real_one(tmp_path):
    root = _tree(tmp_path, status="trial")
    cm.write_manifest(str(root), "trial")
    (root / DRAFT).write_text("Status: prereg-v1.0, frozen\n")
    with pytest.raises(RuntimeError, match="delete a trial manifest"):
        cm.write_manifest(str(root), "prereg-v1.0")
    # moved into a subfolder of prereg/, it is still found, and never counts as part of the chain
    trial = root / "prereg" / "old" / "MANIFEST_trial.txt"
    trial.parent.mkdir()
    os.rename(root / "prereg" / "MANIFEST_trial.txt", trial)
    h = cm.sha256_file(str(trial))
    assert cm.earlier_manifests(str(root)) == {"prereg/old/MANIFEST_trial.txt": h}
    nested = ("prereg/old/MANIFEST_trial.txt: a manifest belongs directly in prereg/; delete a trial manifest or "
              "move it out of the package")
    assert cm.write_manifest(str(root), "prereg-v1.0", check_only=True)["problems"] == [nested]
    out = cm.write_manifest(str(root), "prereg-v1.1", follows=h, check_only=True)["problems"]
    assert nested in out and any(p.startswith("no manifest in prereg/ has the SHA-256") for p in out)
    with pytest.raises(RuntimeError, match="belongs directly in prereg/"):
        cm.write_manifest(str(root), "prereg-v1.0")
    os.remove(trial)
    (root / "prereg" / "__pycache__").mkdir()  # cache folders are skipped
    (root / "prereg" / "__pycache__" / "MANIFEST_x.txt").write_text("")
    assert cm.earlier_manifests(str(root)) == {}
    assert cm.write_manifest(str(root), "prereg-v1.0")["files"] == 7


def test_tampered_manifest_lines_are_caught(tmp_path):
    root = _tree(tmp_path)
    res = cm.write_manifest(str(root), "prereg-v1.0")
    path = root / res["manifest"]
    lines = path.read_text().splitlines(keepends=True)
    path.write_text("".join(lines[:4] + lines[5:]))  # drop one entry: count no longer matches
    assert not cm.verify(str(root), str(path))["ok"]
    path.write_text("".join(lines[:4] + list(reversed(lines[4:]))))  # unsorted
    assert not cm.verify(str(root), str(path))["sorted"]
    path.write_text("".join(lines[:3] + ["# changed: README.md\n"] + lines[3:]))  # changes without "follows"
    assert not cm.verify(str(root), str(path))["chain_ok"]
    summary = "# changes since prereg-v0.9: 0 changed, 0 added, 0 removed\n"
    path.write_text("".join(lines[:3] + [summary] + lines[3:]))  # a count line without "follows"
    assert not cm.verify(str(root), str(path))["chain_ok"]
    path.write_bytes("".join(lines).replace("\n", "\r\n").encode())
    with pytest.raises(ValueError):
        cm.verify(str(root), str(path))
    # an addendum's header: the count line and the label in "# follows:"
    path.write_text("".join(lines))
    (root / "src" / "ngraph" / "a.py").write_text("x = 2\n")
    _refresh_code(root)
    (root / "prereg" / "ADDENDUM.md").write_text("Status: prereg-v1.1, frozen\n")
    second = cm.write_manifest(str(root), "prereg-v1.1", follows=res["manifest_sha256"], allow_tbd=True)
    path2 = root / second["manifest"]
    text = path2.read_text()
    v = cm.verify(str(root), str(path2))
    assert v["ok"] and v["changes_count_matches_header"] and v["follows_label_matches"] and v["chain_ok"]
    summary = "# changes since prereg-v1.0: 2 changed, 1 added, 0 removed\n"
    follows = f"# follows: prereg-v1.0 {res['manifest_sha256']}\n"
    assert summary in text and follows in text
    for edited in (text.replace(summary, summary.replace("2 changed", "9 changed")),  # count changed
                   text.replace(summary, ""),  # count line deleted
                   text.replace(summary, summary + summary)):  # count line twice
        path2.write_text(edited)
        v = cm.verify(str(root), str(path2))
        assert not v["ok"] and not v["chain_ok"] and not v["changes_count_matches_header"]
    path2.write_text(text.replace(follows, follows.replace("prereg-v1.0", "prereg-v9.9")))  # wrong label
    v = cm.verify(str(root), str(path2))
    assert not v["ok"] and not v["follows_label_matches"] and not v["changes_count_matches_header"]
    path2.write_text(text.replace("prereg-v1.0 ", "prereg-v9.9 ").replace("since prereg-v1.0:", "since prereg-v9.9:"))
    v = cm.verify(str(root), str(path2))  # the count line agrees, but the followed manifest says prereg-v1.0
    assert not v["ok"] and not v["follows_label_matches"] and v["changes_count_matches_header"]


def test_digest_matches_shell_tools(tmp_path):
    root = _tree(tmp_path)
    d = cm.digest(str(root), "data/items")
    lines = "".join(f"{hashlib.sha256((root / 'data/items' / f).read_bytes()).hexdigest()}  data/items/{f}\n"
                    for f in ("r1.json", "r2.json"))
    assert d == {"folder": "data/items", "files": 2, "digest": hashlib.sha256(lines.encode()).hexdigest()}
    assert cm.digest(str(root), "./data/items/") == d
    if not all(shutil.which(t) for t in ("find", "sort", "xargs", "sha256sum")):
        pytest.skip("sha256sum not available")
    out = subprocess.run("find data/items -type f | LC_ALL=C sort | xargs sha256sum | sha256sum", shell=True,
                         cwd=root, capture_output=True, text=True, check=True, env={**os.environ, "LC_ALL": "C"})
    assert out.stdout.split()[0] == d["digest"]


def test_snapshot_is_reproducible_streamed_and_verifies(tmp_path):
    root = _tree(tmp_path)
    res = cm.write_manifest(str(root), "prereg-v1.0")
    for inside in (root / "snap.tar.gz", root / "..frozen" / "s.tar.gz"):  # never inside the package
        with pytest.raises(ValueError):
            cm.snapshot(str(root), str(root / res["manifest"]), str(inside))
    a = cm.snapshot(str(root), res["manifest"], str(tmp_path / "a" / "v1.tar.gz"))
    b = cm.snapshot(str(root), str(root / res["manifest"]), str(tmp_path / "b" / "v1.tar.gz"))
    assert a["archive_sha256"] == b["archive_sha256"] and a["files"] == 8
    assert not (tmp_path / "a" / "v1.tar.gz.part").exists()
    out = tmp_path / "unpacked"
    with tarfile.open(tmp_path / "a" / "v1.tar.gz") as tar:
        tar.extractall(out, filter="data")
    v = cm.verify(str(out), res["manifest"], expect=res["manifest_sha256"])
    assert v["ok"] and v["not_listed"] == []


def test_snapshot_archives_only_the_checked_bytes(tmp_path, monkeypatch, capsys):
    root = _tree(tmp_path)
    res = cm.write_manifest(str(root), "prereg-v1.0")
    manifest, test_a, readme = root / res["manifest"], root / "tests" / "test_a.py", root / "README.md"
    original, readme_bytes = manifest.read_bytes(), readme.read_bytes()
    out = tmp_path / "frozen" / "v1.tar.gz"
    real_verify, real_addfile, real_snapshot = cm.verify, tarfile.TarFile.addfile, cm._snapshot

    def then(real, save):  # call the real function, then save a file as an editor would
        def wrapped(*args, **kw):
            result = real(*args, **kw)
            save()
            return result
        return wrapped

    def save_test_a():
        test_a.write_text("def test(): assert 0\n")

    def save_manifest():
        manifest.write_bytes(original + b"# edited\n")

    def refused(match):
        with pytest.raises(RuntimeError, match=match):
            cm.snapshot(str(root), res["manifest"], str(out))
        assert not out.exists() and not os.path.exists(str(out) + ".part")
        monkeypatch.undo()
        test_a.write_text("def test(): pass\n")
        manifest.write_bytes(original)
        readme.unlink()
        readme.write_bytes(readme_bytes)

    def link_readme_and_save_test_a():  # README.md keeps its bytes, but behind a symbolic link
        (tmp_path / "README.copy").write_bytes(readme_bytes)
        readme.unlink()
        readme.symlink_to(tmp_path / "README.copy")
        save_test_a()

    # a file listed after the manifest is saved after verify() passed, or while the archive is written
    monkeypatch.setattr(cm, "verify", then(real_verify, save_test_a))
    refused("tests/test_a.py changed after it was checked")
    monkeypatch.setattr(tarfile.TarFile, "addfile", then(real_addfile, save_test_a))
    refused("tests/test_a.py changed after it was checked")
    # every such file is named
    monkeypatch.setattr(cm, "verify", then(real_verify, link_readme_and_save_test_a))
    refused("README.md is missing, a symbolic link or not a regular file; tests/test_a.py changed after it was checked")
    # the manifest is saved after verify() passed: neither snapshot nor post goes on
    monkeypatch.setattr(cm, "verify", then(real_verify, save_manifest))
    refused("the manifest changed while it was checked")
    monkeypatch.setattr(cm, "verify", then(real_verify, save_manifest))
    assert cm.main(["post", "--root", str(root), "--manifest", res["manifest"]]) == 1
    captured = capsys.readouterr()
    assert "the manifest changed while it was checked" in captured.err and "SHA-256:" not in captured.out
    monkeypatch.undo()
    manifest.write_bytes(original)
    # the post printed after a snapshot comes from the archived manifest, not from a new read
    monkeypatch.setattr(cm, "_snapshot", then(real_snapshot, save_manifest))
    assert cm.main(["snapshot", "--root", str(root), "--manifest", res["manifest"], "--out", str(out)]) == 0
    printed = capsys.readouterr().out
    assert f"SHA-256: {res['manifest_sha256']}" in printed and cm.sha256_file(str(manifest)) not in printed


def test_cli_root_post_and_snapshot(tmp_path, capsys):
    root = _tree(tmp_path)
    assert cm.main(["--root", str(root), "manifest", "--label", "prereg-v1.0", "--check-only"]) == 0
    assert json.loads(capsys.readouterr().out)["ok"]
    assert cm.main(["manifest", "--root", str(root), "--label", "prereg-v1.0"]) == 0
    out = capsys.readouterr().out
    assert "Title:" not in out and "Post nothing before the snapshot exists" in out
    h = cm.sha256_file(str(root / "prereg" / "MANIFEST_prereg-v1.0.txt"))
    snap = tmp_path / "frozen" / "prereg-v1.0.tar.gz"
    assert cm.main(["snapshot", "--root", str(root), "--manifest", "prereg/MANIFEST_prereg-v1.0.txt",
                    "--out", str(snap)]) == 0
    out = capsys.readouterr().out
    assert "Title: Pre-registration hash" in out and h in out
    unpacked = tmp_path / "unpacked"
    with tarfile.open(snap) as tar:
        tar.extractall(unpacked, filter="data")
    # --root before or after the subcommand; a relative --manifest is read from --root
    for argv in (["verify", "--root", str(unpacked)], ["--root", str(unpacked), "verify"]):
        assert cm.main(argv + ["--manifest", "prereg/MANIFEST_prereg-v1.0.txt", "--expect", h]) == 0
        res = json.loads(capsys.readouterr().out)
        assert res["ok"] and res["not_listed"] == []
    assert cm.main(["post", "--root", str(root), "--manifest", "prereg/MANIFEST_prereg-v1.0.txt"]) == 0
    assert h in capsys.readouterr().out
    assert cm.main(["post", "--root", str(root), "--manifest", "prereg/MANIFEST_prereg-v1.0.txt", "--reply"]) == 1
    (root / "README.md").write_text("changed\n")
    assert cm.main(["post", "--root", str(root), "--manifest", "prereg/MANIFEST_prereg-v1.0.txt"]) == 1
    captured = capsys.readouterr()
    assert "nothing to post" in captured.err and "SHA-256:" not in captured.out
    assert cm.main(["manifest", "--root", str(root), "--label", "prereg-v1.0"]) == 1  # exists
    assert "never rewritten" in capsys.readouterr().err


def test_package_code_sha256_is_current():
    """CODE_SHA256.txt must match the code and docs; regenerate with `python -m ngraph.commit code-sha256`."""
    res = cm.check_code_sha256(PKG)
    assert res["ok"], res
