"""Hash-only public time-stamp of the pre-registration (method chosen on 7 Nov 2026).

At each freeze, `manifest` lists every file of this package with its SHA-256 in one plain-text
file, prereg/MANIFEST_<label>.txt. Only the SHA-256 of that manifest file is posted on the
competition forum; the files themselves are released with the paper, and `verify` recomputes
every file hash and the manifest hash from them. The Study B addendum gets its own manifest
(label prereg-v1.1), written with `--follows <the hash posted first>`: it lists the earlier
manifest, names it with its hash in its header, and lists in its header every file that changed,
was added or was removed since, so the two posts form a chain that shows what changed.

Commands (run from the package root, or give --root; a relative --manifest is read from --root):
    python -m ngraph.commit code-sha256 [--check]   write (or check) CODE_SHA256.txt; prints its hash
    python -m ngraph.commit digest data/items       one SHA-256 for a folder
    python -m ngraph.commit manifest --label prereg-v1.0 --check-only    what still blocks the freeze
    python -m ngraph.commit manifest --label prereg-v1.0
    python -m ngraph.commit verify --manifest prereg/MANIFEST_prereg-v1.0.txt [--expect HASH]
    python -m ngraph.commit snapshot --manifest prereg/MANIFEST_prereg-v1.0.txt --out ../frozen/prereg-v1.0.tar.gz
    python -m ngraph.commit post --manifest prereg/MANIFEST_prereg-v1.0.txt
    python -m ngraph.commit diff --manifest prereg/MANIFEST_prereg-v1.0.txt     files changed since
    python -m ngraph.commit manifest --label prereg-v1.1 --follows HASH_OF_THE_FIRST_POST

Checks made before a manifest is written. `manifest --check-only` runs all of them and lists every
problem found, with its file and, where there is one, its line. `manifest` runs the same checks (an
existing manifest stops it at once) and writes nothing if any problem is found; its error lists them all.
A bad argument, or a file that a check cannot read or parse (prereg/*.md and the DRAFT_ONLY_FILES must
be UTF-8 text), stops either one with an error instead. Every command prints such an error as a
message, without a traceback, and exits with status 1.
- Outside the paths left out (below), the package holds no symbolic link, no file or folder name
  with a line break (any character at which str.splitlines() splits, such as \\n, \\r, \\f or
  U+2028), no file larger than 100 MB (model files and competition data stay outside) and nothing
  else that is not a regular file. Each such path is listed as refused. The other checks leave
  refused paths, and what a refused folder holds, out of every folder they walk, and skip a cited
  or DRAFT_ONLY_FILES path that is itself refused.
- No listed path has a hidden part (a file or folder whose name starts with ".", such as .env or
  .github/): every listed file is hashed and released with the paper, so such a file is moved
  outside the package first. Each is listed once, by its first hidden part. (.DS_Store files and
  the left-out folders below are skipped, not listed.)
- The manifest to be written does not exist yet, unless --force is given (only for a manifest that
  was never posted; one that a later manifest follows is never replaced).
- CODE_SHA256.txt matches the files, byte for byte.
- Every 64-hex value on a prereg/*.md line that names one file or folder of this package (in
  backticks, or CODE_SHA256.txt, data/items or repos_manifest.json written plainly) equals that
  file's SHA-256 or that folder's digest. Earlier values belong in the text shortened.
- A prereg/*.md line starts with "Status: <label>", for example "Status: prereg-v1.0, frozen 8 Nov
  2026 (UTC)". The label may end a sentence but must not run on into more letters, digits,
  underscores, hyphens or dotted parts: "Status: prereg-v1.0." counts, "Status: prereg-v1.0.1" does not.
- No "[TBD" marker is left in prereg/*.md, except "[TBD-B" markers (fixed by the Study B addendum)
  at the first freeze; --allow-tbd skips this check only.
- No draft-only text (DRAFT_ONLY below) is left in prereg/*.md or in the DRAFT_ONLY_FILES:
  README.md, src/ngraph/analysis.py and src/ngraph/runner.py.
- The manifests already in prereg/ form one chain that ends at the --follows hash; a first freeze
  finds none (a trial manifest must be deleted first). A manifest in a subfolder of prereg/ is a
  problem in itself and never counts as part of the chain.

Keep the snapshot (outside the package) of every freeze, and a second copy off the computer:
later edits to the README or code make an earlier manifest impossible to re-check from the live
folder. To re-check a snapshot, unpack it into an empty folder, go there and run
    PYTHONPATH=src python -m ngraph.commit verify --manifest prereg/MANIFEST_prereg-v1.0.txt --expect HASH

Formats, chosen so that standard tools give the same answers:
- Each manifest entry is a `sha256sum` line, "<64 hex>  <path>", with paths relative to the
  package root, sorted bytewise (as `LC_ALL=C sort`), LF line ends. Lines starting with "#" are
  a header and are part of the hashed text. `grep -v '^#' MANIFEST | sha256sum -c` re-checks the
  files (`shasum -a 256 -c` where sha256sum is missing); `sha256sum MANIFEST` gives the posted hash.
- `digest data/items` equals `find data/items -type f | LC_ALL=C sort | xargs sha256sum | sha256sum`
  run from the package root, with the folder typed exactly so, when the folder holds none of the
  files that `digest` skips (files in cache folders, .DS_Store and *.pyc files) and for file names
  without spaces, quotes or backslashes (true for data/items). `digest` hashes whatever folder it is
  given; only files listed in a manifest are covered by a posted hash.
- CODE_SHA256.txt keeps its earlier format: "<64 hex>  ./<path>" for every file outside data/,
  third_party/ and prereg/ (the pre-registration cites this file's hash, so it leaves prereg/
  out), without CODE_SHA256.txt itself.

Left out of CODE_SHA256.txt and of every manifest: the manifest being written, the top-level
runs/ (model outputs), .venv/ and .git/ folders, caches (__pycache__, .pytest_cache, .mypy_cache,
.ruff_cache) at any depth, and .DS_Store and *.pyc files. Symbolic links, names containing a line
break (such as the "Icon\\r" file that Finder makes for a custom folder icon), files over 100 MB and
anything else that is not a regular file are refused, so every listed path is a regular file.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import os
import re
import sys
import tarfile

TOP_LEVEL_SKIP = {"runs", ".venv", ".git"}
ANY_LEVEL_SKIP = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
SKIP_FILES = {".DS_Store"}
MAX_FILE_BYTES = 100 * 1024 * 1024
CODE_SHA256_NAME = "CODE_SHA256.txt"
CODE_SHA256_SKIP_TOP = {"data", "third_party", "prereg"}
MANIFEST_DIR = "prereg"
MANIFEST_RE = re.compile(r"^MANIFEST_(.+)\.txt$")
HEADER_TITLE = "# ngraph pre-registration manifest"
LABEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
POST_TITLE = "Pre-registration hash"
POST_SENTENCE = ("Time-stamp of a pre-registered analysis plan. The hashed files will be released with our "
                 "writeup, with a script that recomputes this hash.")
HEX64_RE = re.compile(r"(?<![0-9a-fA-F])[0-9a-fA-F]{64}(?![0-9a-fA-F])")
BACKTICK_RE = re.compile(r"`([^`\n]+)`")
# Package artifacts that the pre-registration may cite without backticks.
PLAIN_CITED = {"CODE_SHA256.txt": re.compile(r"(?<![\w./-])CODE_SHA256\.txt(?!\w)"),
               "data/items": re.compile(r"(?<![\w./-])data/items(?![\w.]|/[\w.-])"),
               "data/repos_manifest.json": re.compile(r"(?<![\w-])repos_manifest\.json(?!\w)")}
TBD_MARK = "[TBD"
TBD_STUDY_B = "[TBD-B"
# Text that only the unfrozen draft carries; the freeze replaces it. It is looked for in prereg/*.md and
# in DRAFT_ONLY_FILES, never in this file (which holds it as constants).
DRAFT_ONLY = ("DRAFT v0", "Open before posting", "v0, not posted")
DRAFT_ONLY_FILES = ("README.md", "src/ngraph/analysis.py", "src/ngraph/runner.py")
MULTI_KEYS = ("changed", "added", "removed")


def sha256_file(path: str, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            b = fh.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _posix_rel(path: str, root: str) -> str:
    return os.path.relpath(path, root).replace(os.sep, "/")


def _inside(path: str, root: str) -> bool:
    path, root = os.path.abspath(path), os.path.abspath(root)
    return os.path.commonpath([path, root]) == root


def _line_break(name: str) -> bool:
    """True if `name` holds a character at which str.splitlines() splits (\\n, \\r, \\v, \\f, \\x1c, \\x1d,
    \\x1e, \\x85, U+2028 or U+2029); the "x" added at the end makes a trailing one count too. Such a
    name would break its manifest line."""
    return len((name + "x").splitlines()) != 1


def list_files(root: str, under: str = "", refused: dict | None = None) -> list[str]:
    """Relative POSIX paths of the package's files (exclusions in the module docstring), sorted
    bytewise. `under` limits the walk to one folder of the package. A symbolic link, a file or folder
    name with a line break, a file over MAX_FILE_BYTES or anything else that is not a regular file
    raises ValueError at the first one found. If `refused` is a dict, each such path is added to it
    instead, mapped to the text "path: reason" (the path written with repr() if it holds a line
    break), and left out, with everything in a refused folder."""
    root = os.path.abspath(root)
    start = os.path.join(root, under) if under else root
    if not os.path.isdir(start):
        raise FileNotFoundError(f"no folder {start}")

    def refuse(rel: str, text: str, message: str) -> None:
        if refused is None:
            raise ValueError(message)
        refused[rel] = text

    out = []
    for dirpath, dirnames, filenames in os.walk(start, followlinks=False):
        rel_dir = os.path.relpath(dirpath, root)
        keep = []
        for d in sorted(dirnames):
            full = os.path.join(dirpath, d)
            if d in ANY_LEVEL_SKIP or (rel_dir == "." and d in TOP_LEVEL_SKIP):
                continue
            rel = _posix_rel(full, root)
            if _line_break(d):
                refuse(rel, f"{rel!r}: folder name with a line break", f"folder name with a line break: {rel!r}")
            elif os.path.islink(full):
                refuse(rel, f"{rel}: symbolic link to a folder", f"symbolic link to a folder: {rel}")
            else:
                keep.append(d)
        dirnames[:] = keep
        for f in sorted(filenames):
            if f in SKIP_FILES or f.endswith(".pyc"):
                continue
            full = os.path.join(dirpath, f)
            rel = _posix_rel(full, root)
            if _line_break(f):
                hint = "(Finder makes 'Icon\\r' for a custom folder icon; remove it)"
                refuse(rel, f"{rel!r}: file name with a line break {hint}",
                       f"file name with a line break: {rel!r} {hint}")
            elif os.path.islink(full):
                refuse(rel, f"{rel}: symbolic link", f"symbolic link: {rel}")
            elif not os.path.isfile(full):
                refuse(rel, f"{rel}: not a regular file", f"not a regular file: {rel}")
            elif os.path.getsize(full) > MAX_FILE_BYTES:
                mb, why = MAX_FILE_BYTES // (1024 * 1024), "model files and competition data stay outside this folder"
                refuse(rel, f"{rel}: larger than {mb} MB ({why})", f"{rel} is larger than {mb} MB: {why}")
            else:
                out.append(rel)
    return sorted(out, key=lambda p: p.encode("utf-8"))


def hidden_paths(paths) -> list[str]:
    """The first hidden part (a name starting with ".") of each path in `paths`, once each and in
    order: "x/.env" for a file, "x/.github/" for a folder. write_manifest refuses to list them."""
    out = []
    for p in paths:
        parts = p.split("/")
        i = next((i for i, part in enumerate(parts) if part.startswith(".")), None)
        if i is not None:
            h = "/".join(parts[: i + 1]) + ("/" if i < len(parts) - 1 else "")
            if h not in out:
                out.append(h)
    return out


def skipped_counts(root: str) -> dict:
    """Number of files in the top-level folders that no posted hash covers (runs/, .venv/, .git/)."""
    out = {}
    for d in sorted(TOP_LEVEL_SKIP):
        full = os.path.join(root, d)
        if os.path.isdir(full) and not os.path.islink(full):
            out[d + "/"] = sum(len(fs) for _, _, fs in os.walk(full))
    return out


def entry_lines(root: str, paths: list[str], prefix: str = "") -> str:
    return "".join(f"{sha256_file(os.path.join(root, p))}  {prefix}{p}\n" for p in paths)


# ------------------------------------------------------------------ CODE_SHA256.txt
def code_sha256_text(root: str, refused: dict | None = None) -> str:
    """The text of CODE_SHA256.txt; `refused` is passed to list_files."""
    paths = [p for p in list_files(root, refused=refused)
             if p.split("/", 1)[0] not in CODE_SHA256_SKIP_TOP and p != CODE_SHA256_NAME]
    return entry_lines(root, paths, prefix="./")


def code_hash(root: str) -> str | None:
    """SHA-256 of CODE_SHA256.txt as it is on disk (the value the pre-registration cites)."""
    path = os.path.join(root, CODE_SHA256_NAME)
    return sha256_file(path) if os.path.isfile(path) else None


def check_code_sha256(root: str, refused: dict | None = None) -> dict:
    """Compare CODE_SHA256.txt, byte for byte, with what `code-sha256` would write now (with
    `refused`, passed to list_files, refused paths are left out instead of raising)."""
    path = os.path.join(root, CODE_SHA256_NAME)
    want = code_sha256_text(root, refused).encode("utf-8")
    have = b""
    if os.path.exists(path):
        with open(path, "rb") as fh:
            have = fh.read()
    if have == want:
        return {"ok": True, "code_hash": hashlib.sha256(have).hexdigest()}
    wl = set(want.decode("utf-8").splitlines())
    hl = set(have.decode("utf-8", errors="replace").splitlines())
    res = {"ok": False, "stale_or_missing": sorted(x.split("  ", 1)[1] for x in wl - hl if "  " in x),
           "no_longer_matching": sorted(x.split("  ", 1)[1] if "  " in x else x for x in hl - wl)}
    if not res["stale_or_missing"] and not res["no_longer_matching"]:
        res["note"] = "same entries but different bytes (line endings or order); run code-sha256 again"
    return res


# ---------------------------------------------------------------------- manifest
def manifest_path_for(root: str, label: str) -> str:
    return os.path.join(root, MANIFEST_DIR, f"MANIFEST_{label}.txt")


def earlier_manifests(root: str, exclude: str | None = None) -> dict:
    """{relative path: SHA-256} of the MANIFEST_*.txt files anywhere under prereg/ (cache folders
    skipped), except `exclude`. Paths that list_files refuses, such as symbolic links, are left out
    without an error (write_manifest lists them)."""
    out = {}
    if os.path.isdir(os.path.join(root, MANIFEST_DIR)):
        for rel in list_files(root, MANIFEST_DIR, refused={}):
            if MANIFEST_RE.match(rel.rsplit("/", 1)[-1]) and rel != exclude:
                out[rel] = sha256_file(os.path.join(root, rel))
    return out


def _texts(root: str, draft_files: bool = False, refused: dict | None = None) -> list[tuple[str, list[str]]]:
    """(path, lines) of every prereg/*.md file, and of the DRAFT_ONLY_FILES if asked. `refused` is
    passed to list_files; a DRAFT_ONLY_FILES path recorded in it is skipped."""
    def lines(p):
        with open(os.path.join(root, p), "rb") as fh:
            data = fh.read()
        try:
            return data.decode("utf-8").splitlines()
        except UnicodeDecodeError as e:
            raise ValueError(f"{p} is not UTF-8 text ({e.reason} at byte {e.start}); save it as UTF-8") from None

    out = []
    if os.path.isdir(os.path.join(root, MANIFEST_DIR)):
        for p in list_files(root, MANIFEST_DIR, refused=refused):
            if p.endswith(".md"):
                out.append((p, lines(p)))
    if draft_files:
        for p in DRAFT_ONLY_FILES:
            if os.path.isfile(os.path.join(root, p)) and p not in (refused or {}):
                out.append((p, lines(p)))
    return out


def tbd_markers(root: str, refused: dict | None = None) -> list[dict]:
    """Every "[TBD" marker in prereg/*.md, with its file, line and text up to the closing bracket
    (`refused` as in _texts)."""
    out = []
    for p, lines in _texts(root, refused=refused):
        for i, line in enumerate(lines, 1):
            start = line.find(TBD_MARK)
            while start >= 0:
                end = line.find("]", start)
                text = line[start:end + 1] if end >= 0 else line[start:]
                out.append({"file": p, "line": i, "text": text, "study_b": text.startswith(TBD_STUDY_B)})
                start = line.find(TBD_MARK, start + 1)
    return out


def _norm_rel(rel: str) -> str:
    rel = rel.strip().strip("/")
    while rel.startswith("./"):
        rel = rel[2:]
    return rel


def _artifact_hash(root: str, rel: str, cache: dict, refused: dict | None = None) -> str | None:
    """SHA-256 of a package file, the digest of a package folder, or None if `rel` is neither (or
    lies in a folder that no posted hash covers, or is recorded in `refused`, which is passed to digest)."""
    rel = _norm_rel(rel)
    if (not rel or rel == ".." or rel.startswith("../") or rel.split("/", 1)[0] in TOP_LEVEL_SKIP
            or rel in (refused or {})):
        return None
    if rel not in cache:
        full = os.path.join(root, rel)
        if not _inside(full, root) or os.path.islink(full):
            cache[rel] = None
        elif os.path.isfile(full):
            cache[rel] = sha256_file(full)
        elif os.path.isdir(full):
            cache[rel] = digest(root, rel, refused)["digest"]
        else:
            cache[rel] = None
    return cache[rel]


def check_citations(root: str, refused: dict | None = None) -> list[str]:
    """Hashes cited in prereg/*.md must be current: on a line with a 64-hex value, every value must
    equal the hash of the one package file or folder that the line names (`refused` as in _texts)."""
    problems, cache = [], {}
    for p, lines in _texts(root, refused=refused):
        for i, line in enumerate(lines, 1):
            hexes = [h.lower() for h in HEX64_RE.findall(line)]
            if not hexes:
                continue
            named = {}
            for tok in BACKTICK_RE.findall(line):
                h = _artifact_hash(root, tok, cache, refused)
                if h is not None:
                    named[_norm_rel(tok)] = h
            for rel, rx in PLAIN_CITED.items():
                if rel not in named and rx.search(line):
                    h = _artifact_hash(root, rel, cache, refused)
                    if h is not None:
                        named[rel] = h
            if not named:
                continue
            if len(named) > 1:
                problems.append(f"{p}:{i}: a hash next to several package files ({', '.join(sorted(named))}); "
                                "give each its own line")
                continue
            (rel, want), = named.items()
            for h in hexes:
                if h != want:
                    problems.append(f"{p}:{i}: cites {h[:12]}... for {rel}, but its current hash is {want[:12]}... "
                                    "(write an earlier value shortened)")
    return problems


def _status_re(label: str) -> re.Pattern:
    # The label may end a sentence ("prereg-v1.0.") but not run on ("prereg-v1.0.1", "prereg-v1.0-rc").
    return re.compile(r"^\**Status:\**\s*" + re.escape(label) + r"(?![\w-]|\.\w)")


def check_freeze_text(root: str, label: str, follows: str | None, allow_tbd: bool = False,
                      refused: dict | None = None) -> tuple[list, list]:
    """Problems in the pre-registration text for a freeze under `label`, and the [TBD markers left
    (`refused` as in _texts)."""
    problems = []
    texts = _texts(root, draft_files=True, refused=refused)
    rx = _status_re(label)
    if not any(rx.match(line) for p, lines in texts if p.startswith(MANIFEST_DIR + "/") for line in lines):
        problems.append(f"no line in {MANIFEST_DIR}/*.md starts with 'Status: {label}' (the label must not run on "
                        "into more letters, digits, underscores, hyphens or dotted parts; for example "
                        f"'Status: {label}, frozen <date> (UTC)')")
    for p, lines in texts:
        for i, line in enumerate(lines, 1):
            for s in DRAFT_ONLY:
                if s in line:
                    problems.append(f"{p}:{i}: draft-only text left: {s!r}")
    markers = tbd_markers(root, refused)
    blocking = [m for m in markers if not (m["study_b"] and follows is None)]
    if blocking and not allow_tbd:
        for m in blocking:
            problems.append(f"{m['file']}:{m['line']}: {m['text']}")
    return problems, markers


def _parse_follows(value: str | None) -> tuple[str | None, str | None]:
    parts = (value or "").split()
    return (parts[0], parts[1]) if len(parts) == 2 else (None, None)


def check_chain(root: str, rel_out: str, follows: str | None) -> tuple[list, str | None]:
    """The manifests already in prereg/ must form one chain that ends at the manifest whose SHA-256
    is `follows`. A manifest in a subfolder of prereg/ is a problem and never part of the chain.
    Returns (problems, path of the followed manifest)."""
    earlier = earlier_manifests(root, exclude=rel_out)
    nested = sorted(rel for rel in earlier if rel.count("/") > 1)
    problems = [f"{rel}: a manifest belongs directly in {MANIFEST_DIR}/; delete a trial manifest or move it out "
                "of the package" for rel in nested]
    earlier = {rel: h for rel, h in earlier.items() if rel not in nested}
    if follows is None:
        if earlier:
            problems.append(f"{MANIFEST_DIR}/ already holds {', '.join(sorted(earlier))}: an addendum needs "
                            "--follows <the hash in the first post>; delete a trial manifest only if it was "
                            "never posted")
        return problems, None
    by_hash = {h: rel for rel, h in earlier.items()}
    if follows not in by_hash:
        found = "; ".join(f"{rel} {h}" for rel, h in sorted(earlier.items())) or "none"
        return (problems + [f"no manifest in {MANIFEST_DIR}/ has the SHA-256 given with --follows ({follows}; "
                            f"found: {found}); copy the hash from the forum post, and restore the posted "
                            "manifest from its snapshot if it was changed"], None)
    chain, cur = [], by_hash[follows]
    while cur and cur not in chain:
        chain.append(cur)
        head, _ = parse_manifest(os.path.join(root, cur))
        _, h = _parse_follows(head.get("follows"))
        cur = by_hash.get(h) if h else None
        if h and cur is None:
            return problems + [f"{chain[-1]} follows a manifest that is not in {MANIFEST_DIR}/ ({h[:12]}...)"], None
    stray = sorted(set(earlier) - set(chain))
    if stray:
        return problems + [f"not part of the posted chain: {', '.join(stray)} (delete trial manifests)"], None
    return problems, by_hash[follows]


def changes_between(old_entries: list, new_entries: list, ignore: set) -> dict:
    old, new = {r: d for d, r in old_entries}, {r: d for d, r in new_entries}

    def key(p):
        return p.encode("utf-8")

    return {"changed": sorted((r for r in new if r in old and new[r] != old[r]), key=key),
            "added": sorted((r for r in new if r not in old and r not in ignore), key=key),
            "removed": sorted((r for r in old if r not in new), key=key)}


def build_manifest(root: str, label: str, leave_out: str | None = None, follows_path: str | None = None) -> tuple:
    """(text, entries, changes) of a manifest; nothing is written."""
    if not LABEL_RE.match(label):
        raise ValueError(f"label must be letters, digits, '.', '_' or '-': {label!r}")
    paths = [p for p in list_files(root) if p != leave_out]
    body = entry_lines(root, paths)
    entries = [(line[:64], line[66:]) for line in body.splitlines()]
    head = f"{HEADER_TITLE}\n# label: {label}\n# files: {len(paths)}\n"
    changes = None
    if follows_path:
        f_head, f_entries = parse_manifest(os.path.join(root, follows_path))
        f_label = f_head.get("label", "?")
        changes = changes_between(f_entries, entries, ignore={follows_path})
        head += f"# follows: {f_label} {sha256_file(os.path.join(root, follows_path))}\n"
        head += (f"# changes since {f_label}: {len(changes['changed'])} changed, {len(changes['added'])} added, "
                 f"{len(changes['removed'])} removed\n")
        for k in MULTI_KEYS:
            head += "".join(f"# {k}: {r}\n" for r in changes[k])
    head += ("# each line: SHA-256, two spaces, path from the package root; sorted bytewise; "
             "this header is part of the hashed text\n")
    return head + body, entries, changes


def manifest_text(root: str, label: str, leave_out: str | None = None) -> str:
    return build_manifest(root, label, leave_out)[0]


def write_manifest(root: str, label: str, out: str | None = None, force: bool = False,
                   follows: str | None = None, allow_tbd: bool = False, check_only: bool = False) -> dict:
    """Check the package (module docstring) and write prereg/MANIFEST_<label>.txt. With
    check_only=True every check runs, nothing is written and every problem is returned, refused
    paths included. Otherwise an existing manifest raises FileExistsError at once unless force=True
    (only for a manifest never posted); then every check runs the same way, and any problem raises
    RuntimeError listing them all before anything is written."""
    root = os.path.abspath(root)
    if not LABEL_RE.match(label):
        raise ValueError(f"label must be letters, digits, '.', '_' or '-': {label!r}")
    out = os.path.abspath(out or manifest_path_for(root, label))
    if not _inside(out, root) or out == root:
        raise ValueError("the manifest must be written inside the package")
    rel_out = _posix_rel(out, root)
    if follows is not None:
        follows = follows.strip().lower()
        if not re.fullmatch(r"[0-9a-f]{64}", follows):
            raise ValueError("--follows takes the 64-character SHA-256 of the earlier manifest")
    problems = []
    exists = os.path.exists(out)
    if exists and not force:
        message = (f"{rel_out} exists; a manifest is never rewritten (use a new label, or --force only if this "
                   "manifest was never posted)")
        if not check_only:
            raise FileExistsError(message)
        problems.append(message)
    refused = {}
    listed = list_files(root, refused=refused)  # every refused path in the package, for the checks below too
    problems += [f"refused: {text}" for text in refused.values()]
    problems += [f"hidden file or folder: {h} (move it outside the package: every listed file is hashed and "
                 "released)" for h in hidden_paths(p for p in listed if p != rel_out)]
    if exists and force:
        old_hash = sha256_file(out)
        users = [r for r in earlier_manifests(root, exclude=rel_out)
                 if _parse_follows(parse_manifest(os.path.join(root, r))[0].get("follows"))[1] == old_hash]
        if users:
            problems.append(f"{', '.join(users)} follows {rel_out}; it cannot be replaced")
    code = check_code_sha256(root, refused)
    if not code["ok"]:
        problems.append(f"{CODE_SHA256_NAME} is not current: run `python -m ngraph.commit code-sha256`, then update "
                        f"every place the pre-registration cites its hash ({code})")
    problems += check_citations(root, refused)
    text_problems, markers = check_freeze_text(root, label, follows, allow_tbd, refused)
    problems += text_problems
    chain_problems, follows_path = check_chain(root, rel_out, follows)
    problems += chain_problems
    items = (digest(root, "data/items", refused)["digest"] if os.path.isdir(os.path.join(root, "data", "items"))
             else None)
    report = {"manifest": rel_out, "label": label, "code_hash": code_hash(root), "items_digest": items,
              "follows": follows_path,
              "tbd_markers_left": [f"{m['file']}:{m['line']}: {m['text']}" for m in markers],
              "skipped_not_hashed": skipped_counts(root)}
    if check_only:
        return dict(report, ok=not problems, problems=problems)
    if problems:
        raise RuntimeError("manifest not written:\n- " + "\n- ".join(problems))
    text, entries, changes = build_manifest(root, label, leave_out=rel_out, follows_path=follows_path)
    parse_manifest_text(text, rel_out)  # the same checks verify makes, before anything is written
    replaced = sha256_file(out) if exists else None
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    report.update(files=len(entries), manifest_sha256=sha256_file(out))
    if changes is not None:
        report["changes"] = changes
    if replaced:
        report["replaced_manifest_sha256"] = replaced
    return report


def parse_manifest_text(text: str, name: str = "manifest") -> tuple[dict, list[tuple[str, str]]]:
    head, entries = {k: [] for k in MULTI_KEYS}, []
    for line in text.splitlines(keepends=True):
        if not line.endswith("\n") or line.endswith("\r\n"):
            raise ValueError(f"line without a plain LF ending in {name}: {line!r}")
        line = line[:-1]
        if line.startswith("#"):
            if line.startswith("# ") and ": " in line:
                k, v = line[2:].split(": ", 1)
                if k in MULTI_KEYS:
                    head[k].append(v)
                else:
                    head[k] = v
            continue
        dig, sep, rel = line.partition("  ")
        if not sep or not re.fullmatch(r"[0-9a-f]{64}", dig) or not rel:
            raise ValueError(f"bad manifest line in {name}: {line!r}")
        entries.append((dig, rel))
    return head, entries


def parse_manifest(path: str) -> tuple[dict, list[tuple[str, str]]]:
    with open(path, encoding="utf-8", newline="") as fh:
        return parse_manifest_text(fh.read(), path)


def _resolve(root: str, manifest: str) -> str:
    return manifest if os.path.isabs(manifest) else os.path.join(root, manifest)


def verify(root: str, manifest: str, expect: str | None = None) -> dict:
    """Recompute every listed file's SHA-256 and the manifest's own SHA-256 (of the same bytes that
    are parsed); a relative `manifest` is read from `root`. A listed path that is gone, a symbolic
    link or not a regular file counts as `missing`. Files present in the package but not listed are
    reported as `not_listed` (expected after a later freeze adds files), and unlisted paths that
    list_files refuses as `not_listed_refused` ("path: reason"); neither makes the check fail.
    `chain_ok` is false if change lists or a "# changes since" line appear without "# follows". For
    an addendum it needs: the followed manifest listed with the hash named in "# follows"; exactly
    one "# changes since <the label named in # follows>: N changed, M added, K removed" line whose
    counts are the lengths of the change lists (`changes_count_matches_header`); and, if the followed
    manifest is intact, its own "# label" equal to the label named in "# follows"
    (`follows_label_matches`) and change lists that match the two manifests (`changes_match_header`)."""
    root = os.path.abspath(root)
    manifest = _resolve(root, manifest)
    with open(manifest, "rb") as fh:
        data = fh.read()
    text = data.decode("utf-8")
    head, entries = parse_manifest_text(text, manifest)
    bad, missing = [], []
    for dig, rel in entries:
        full = os.path.join(root, rel)
        if not os.path.isfile(full) or os.path.islink(full):
            missing.append(rel)
        elif sha256_file(full) != dig:
            bad.append(rel)
    listed = {rel for _, rel in entries}
    rel_manifest = _posix_rel(os.path.abspath(manifest), root)
    refused = {}
    not_listed = [p for p in list_files(root, refused=refused) if p not in listed and p != rel_manifest]
    m_hash = hashlib.sha256(data).hexdigest()
    order_ok = [rel for _, rel in entries] == sorted(listed, key=lambda p: p.encode("utf-8"))
    count_ok = head.get("files") == str(len(entries))
    res = {"label": head.get("label"), "files": len(entries), "manifest_sha256": m_hash,
           "mismatched": bad, "missing": missing, "not_listed": not_listed,
           "not_listed_refused": [t for p, t in refused.items() if p not in listed and p != rel_manifest],
           "sorted": order_ok, "count_matches_header": count_ok}
    summary = [line[2:] for line in text.splitlines() if line.startswith("# changes since ")]
    chain_ok = not any(head[k] for k in MULTI_KEYS) and not summary  # these only make sense with "follows"
    if head.get("follows"):
        f_label, f_hash = _parse_follows(head["follows"])
        f_rel = next((r for d, r in entries if d == f_hash and r.startswith(MANIFEST_DIR + "/MANIFEST_")), None)
        res["follows"] = {"label": f_label, "sha256": f_hash, "listed_as": f_rel}
        counts = ", ".join(f"{len(head[k])} {k}" for k in MULTI_KEYS)
        res["changes_count_matches_header"] = summary == [f"changes since {f_label}: {counts}"]
        chain_ok = f_rel is not None and res["changes_count_matches_header"]
        if f_rel is not None and f_rel not in missing and f_rel not in bad:
            f_head, f_entries = parse_manifest(os.path.join(root, f_rel))
            got = changes_between(f_entries, entries, ignore={f_rel})
            res["follows_label_matches"] = f_head.get("label") == f_label
            res["changes_match_header"] = all(got[k] == head[k] for k in MULTI_KEYS)
            chain_ok = chain_ok and res["follows_label_matches"] and res["changes_match_header"]
    res["chain_ok"] = chain_ok
    if expect is not None:
        res["expected_sha256"] = expect.strip().lower()
        res["matches_expected"] = m_hash == res["expected_sha256"]
    res["ok"] = (not bad and not missing and order_ok and count_ok and chain_ok
                 and res.get("matches_expected", True))
    return res


def diff(root: str, manifest: str) -> dict:
    """Files changed, added or removed since a manifest (later manifests count as added)."""
    root = os.path.abspath(root)
    manifest = _resolve(root, manifest)
    head, old = parse_manifest(manifest)
    rel_manifest = _posix_rel(os.path.abspath(manifest), root)
    new = [(sha256_file(os.path.join(root, p)), p) for p in list_files(root) if p != rel_manifest]
    return {"since": head.get("label"), **changes_between(old, new, ignore=set())}


def digest(root: str, folder: str, refused: dict | None = None) -> dict:
    """One SHA-256 for a folder: the SHA-256 of its `sha256sum` lines (paths from the package root).
    `refused` is passed to list_files."""
    folder = _norm_rel(folder)
    paths = list_files(root, folder, refused=refused)
    return {"folder": folder, "files": len(paths), "digest": sha256_text(entry_lines(root, paths))}


def _read_listed(path: str) -> tuple[bytes | None, str | None]:
    """(the file's bytes, None), or (None, why) for a file that cannot go into a snapshot."""
    if os.path.islink(path) or not os.path.isfile(path):
        return None, "is missing, a symbolic link or not a regular file"
    try:
        with open(path, "rb") as fh:
            data = fh.read(MAX_FILE_BYTES + 1)
    except OSError as e:
        return None, f"could not be read ({e.strerror or e})"
    if len(data) > MAX_FILE_BYTES:
        return None, f"is larger than {MAX_FILE_BYTES // (1024 * 1024)} MB"
    return data, None


def snapshot(root: str, manifest: str, out: str) -> dict:
    """Write a gzipped tar of the manifest and every file it lists to a path outside the package,
    after verify() passes. The manifest's bytes are read once; they must have the SHA-256 that
    verify() computed, and the entries are parsed from them. Each listed file is then read into
    memory once, checked against its manifest entry and written from those bytes, so the archive
    holds exactly the checked bytes. If the manifest changed, or a listed file no longer has its
    manifest hash, is gone, is a symbolic link or not a regular file, cannot be read or is over
    100 MB, RuntimeError names it (every such file), the partial archive is deleted and nothing is
    left at `out`. Entries are sorted and carry no owner names or times, so the same files always
    give the same archive; the archive itself is streamed to disk."""
    return _snapshot(root, manifest, out)[0]


def _snapshot(root: str, manifest: str, out: str) -> tuple[dict, str]:
    """snapshot(), and the text of the manifest it archived (main prints the post from it)."""
    root = os.path.abspath(root)
    manifest = _resolve(root, manifest)
    out = os.path.abspath(out)
    if _inside(out, root):
        raise ValueError("write the snapshot outside the package, so later manifests do not list it")
    if os.path.exists(out):
        raise FileExistsError(f"{out} exists")
    check = verify(root, manifest)
    if not check["ok"]:
        why = [f"{k} ({len(check[k])}): {', '.join(check[k][:20])}{' ...' if len(check[k]) > 20 else ''}"
               for k in ("mismatched", "missing") if check[k]]
        why += [f"{k} is false" for k in ("sorted", "count_matches_header", "chain_ok") if not check[k]]
        raise RuntimeError("snapshot not written: the files no longer match the manifest ("
                           + "; ".join(why or ["see verify"]) + "); run verify for the full report")
    with open(manifest, "rb") as fh:
        m_data = fh.read()
    m_hash = hashlib.sha256(m_data).hexdigest()
    if m_hash != check["manifest_sha256"]:
        raise RuntimeError("snapshot not written: the manifest changed while it was checked")
    text = m_data.decode("utf-8")
    _, entries = parse_manifest_text(text, manifest)
    rel_manifest = _posix_rel(os.path.abspath(manifest), root)
    want = {rel: dig for dig, rel in entries}
    want[rel_manifest] = m_hash
    names = sorted(want, key=lambda p: p.encode("utf-8"))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    part = out + ".part"
    bad = []
    try:
        with open(part, "wb") as raw, gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as gz, \
                tarfile.open(fileobj=gz, mode="w", format=tarfile.PAX_FORMAT) as tar:
            for rel in names:
                data, why = (m_data, None) if rel == rel_manifest else _read_listed(os.path.join(root, rel))
                if why is None and hashlib.sha256(data).hexdigest() != want[rel]:
                    why = "changed after it was checked"
                if why:
                    bad.append(f"{rel} {why}")
                    continue
                info = tarfile.TarInfo(rel)
                info.size = len(data)
                info.mode = 0o644
                info.mtime = 0
                info.uid = info.gid = 0
                info.uname = info.gname = ""
                tar.addfile(info, io.BytesIO(data))
        if bad:
            raise RuntimeError("snapshot not written: " + "; ".join(bad))
        os.replace(part, out)
    except BaseException:
        if os.path.exists(part):
            os.remove(part)
        raise
    return ({"snapshot": out, "files": len(names), "manifest_sha256": m_hash, "archive_sha256": sha256_file(out)},
            text)


def post_text(manifest: str, reply: bool | None = None, text: str | None = None) -> str:
    """The forum post: a plain title that does not reveal the topic, and the label and hash only.
    A manifest that follows an earlier one is posted as a reply in the first post's topic. The label
    and hash come from `text`, the manifest's text as it was checked (`post` and `snapshot` pass the
    text of the bytes they checked); without it, the file `manifest` is read."""
    if text is None:
        with open(manifest, "rb") as fh:
            text = fh.read().decode("utf-8")
    head, _ = parse_manifest_text(text, manifest)
    label, h = head.get("label", "?"), sha256_text(text)
    follows = head.get("follows")
    if reply is None:
        reply = bool(follows)
    if reply and not follows:
        raise ValueError("this manifest follows no earlier one: it is the first post, not a reply")
    if not reply and follows:
        raise ValueError(f"this manifest follows {follows.split()[0]}: post it as a reply in the first post's topic")
    if reply:
        return (f'Post as a REPLY in the topic "{POST_TITLE}" (do not start a new topic). Text:\n\n'
                f"{label} (addendum)\nSHA-256: {h}")
    return (f"Post as a NEW TOPIC on the paper-track forum.\n\nTitle: {POST_TITLE}\n\nText:\n\n"
            f"{label}\nSHA-256: {h}\n\n{POST_SENTENCE}")


# ---------------------------------------------------------------------------- CLI
def main(argv=None) -> int:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--root", default=argparse.SUPPRESS, help="package root (default: current folder)")
    # --root may come before or after the subcommand. The option object is shared by every parser
    # built from `common`, so its default stays SUPPRESS and "." is applied after parsing.
    ap = argparse.ArgumentParser(description="Hash-only time-stamp of the pre-registration", parents=[common])
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("code-sha256", parents=[common], help="write CODE_SHA256.txt (or check it with --check)")
    c.add_argument("--check", action="store_true")
    m = sub.add_parser("manifest", parents=[common], help="check the package and write prereg/MANIFEST_<label>.txt")
    m.add_argument("--label", required=True, help="e.g. prereg-v1.0")
    m.add_argument("--follows", help="for an addendum: the SHA-256 in the first post, copied from the forum")
    m.add_argument("--check-only", action="store_true", help="list what blocks the freeze; write nothing")
    m.add_argument("--allow-tbd", action="store_true", help="skip the [TBD marker check (a deviation)")
    m.add_argument("--out", help="default: prereg/MANIFEST_<label>.txt")
    m.add_argument("--force", action="store_true", help="replace a manifest that was never posted")
    v = sub.add_parser("verify", parents=[common], help="recompute the hashes listed in a manifest")
    v.add_argument("--manifest", required=True, help="path from --root, or absolute")
    v.add_argument("--expect", help="the SHA-256 that was posted, copied from the forum")
    d = sub.add_parser("digest", parents=[common], help="one SHA-256 for a folder of the package")
    d.add_argument("folder")
    p = sub.add_parser("post", parents=[common], help="verify a manifest, then print its forum post")
    p.add_argument("--manifest", required=True)
    p.add_argument("--reply", action="store_true", help="refuse unless the manifest is an addendum")
    s = sub.add_parser("snapshot", parents=[common], help="archive the manifest and its files outside the package")
    s.add_argument("--manifest", required=True)
    s.add_argument("--out", required=True, help="a .tar.gz path outside the package")
    f = sub.add_parser("diff", parents=[common], help="files changed, added or removed since a manifest")
    f.add_argument("--manifest", required=True)
    a = ap.parse_args(argv)
    root = getattr(a, "root", ".")
    try:
        return _run(a, root)
    except (RuntimeError, ValueError, OSError) as e:  # a message, not a traceback
        print(f"{a.cmd}: {e}", file=sys.stderr)
        return 1


def _run(a, root: str) -> int:
    import json

    if a.cmd == "code-sha256":
        if a.check:
            res = check_code_sha256(root)
            print(json.dumps(res, indent=1))
            return 0 if res["ok"] else 1
        text = code_sha256_text(root)
        with open(os.path.join(root, CODE_SHA256_NAME), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        print(json.dumps({"written": CODE_SHA256_NAME, "files": text.count("\n"), "code_hash": code_hash(root)}))
        return 0
    if a.cmd == "manifest":
        res = write_manifest(root, a.label, a.out, force=a.force, follows=a.follows, allow_tbd=a.allow_tbd,
                             check_only=a.check_only)
        print(json.dumps(res, indent=1))
        if a.check_only:
            return 0 if res["ok"] else 1
        print(f"\nNext: verify --manifest {res['manifest']}, then snapshot (it prints the post text). "
              "Post nothing before the snapshot exists.")
        return 0
    if a.cmd == "verify":
        res = verify(root, a.manifest, a.expect)
        print(json.dumps(res, indent=1))
        return 0 if res["ok"] else 1
    if a.cmd == "digest":
        print(json.dumps(digest(root, a.folder)))
        return 0
    if a.cmd in ("post", "snapshot"):
        # The post is made from the manifest bytes that were checked (and archived), not from a new read.
        mpath = _resolve(os.path.abspath(root), a.manifest)
        if a.cmd == "snapshot":
            res, text = _snapshot(root, mpath, a.out)
            print(json.dumps(res, indent=1))
        else:
            res = verify(root, mpath)
            if not res["ok"]:
                print(json.dumps(res, indent=1))
                print("the files do not match this manifest: nothing to post", file=sys.stderr)
                return 1
            with open(mpath, "rb") as fh:
                data = fh.read()
            if hashlib.sha256(data).hexdigest() != res["manifest_sha256"]:
                print("the manifest changed while it was checked: nothing to post", file=sys.stderr)
                return 1
            text = data.decode("utf-8")
        head, _ = parse_manifest_text(text, mpath)
        if head.get("follows"):
            f_label, f_hash = _parse_follows(head["follows"])
            print(f"\nThis manifest follows {f_label} with SHA-256 {f_hash}: check that this is the hash in "
                  "the first post.")
        try:
            print("\n" + post_text(mpath, reply=True if getattr(a, "reply", False) else None, text=text))
        except ValueError as e:
            print(str(e), file=sys.stderr)
            return 1
        return 0
    if a.cmd == "diff":
        print(json.dumps(diff(root, a.manifest), indent=1))
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
