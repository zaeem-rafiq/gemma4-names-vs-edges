"""Letter-logit runner (Study A now; Study B reuses LetterScorer) on llama-cpp-python.

One forward pass per prompt. The prompt is the model's own chat template (read from the GGUF)
with thinking off. The next-token logits at the answer position are read for the answer letters,
with and without a leading space, and combined per letter with log-sum-exp.

Empty thought block. With thinking off, Google's per-size chat templates end the generation
prompt with the empty thought block "<|channel>thought\\n<channel|>" for 12B, 26B-A4B and 31B and
without it for E2B and E4B (Google's thinking page, ai.google.dev/gemma/docs/capabilities/thinking,
and the templates in the Hugging Face repositories and in Google's QAT GGUF files, checked 7 Nov
2026). The template in llama.cpp's vocab file is the large-model template, so it appends the block
for every size and says nothing about E2B and E4B. `--thought-block auto` follows the per-size rule;
`template` keeps whatever the model's own GGUF template renders (the same prompts with Google's
files); `on`/`off` force it. The smoke test scores the pilot prompts under both settings and
reports the probability of the "<|channel>" token at the answer position, so the rule is checked on
each model before any confirmatory run.

Answer prefix. The model's turn can be pre-filled with a short text, appended after the thought-block
handling. Rule (pre-registration, section 7): a model gets no prefix if it passes the GNG-1
letter-mass check without one; otherwise the first of PREFIX_CANDIDATES under which it passes with
its per-size thought-block setting. Chosen on the pilot prompts by letter mass alone and registered
per model in ANSWER_PREFIX; the smoke test re-checks the rule (`prefix_scan`, `prefix_rule_choice`).
A model without an entry in ANSWER_PREFIX takes the rule's choice from its own GNG-1 smoke file
(`study-a --prefix-from`, checked by `prefix_from_smoke`; for this the smoke output records the tag,
the model file's SHA-256, the pilot prompts' count and seed, and the repositories). That file must
have been run with the choice, so that its GNG-1 verdict is for the prefix the run uses: smoke runs
first with no prefix, and when the rule chooses another candidate, a second time with
`--answer-prefix <the choice>`, and the second file is the one given. Any other prefix,
given with `--answer-prefix`, is a deviation. The run header records the prefix
(settings.answer_prefix) and where it came from (`answer_prefix_source`), and a run file is never
extended with a different prefix.

Run files and the frozen package. The first line of a Study A run file (and the smoke output)
records `package` (the output of `package_state`): the SHA-256 of CODE_SHA256.txt and whether it
still matches the code, the digest of the item folder (`python -m ngraph.commit digest data/items`
gives the same value) and the SHA-256 of each MANIFEST_*.txt anywhere under prereg/. A run made with
the frozen files records the code hash and item digest that a posted manifest lists; a code hash in
no posted manifest, or code_sha256_current false, means that other code ran. An item folder whose
real path (symbolic links resolved) lies outside the package's real path is recorded as "outside
the package", with a digest of its files under `items_digest_outside`. A session that would extend
a run file is refused when its header differs from the file's first line in the model tag, the
model file's name or SHA-256, any key of `settings` (n_ctx, n_batch, n_ubatch, n_gpu_layers,
flash_attn, enable_thinking, thought_block, answer_prefix, llama_cpp_python), the jobs (perms,
repos, versions, n_jobs) or the item folder (items_folder, items_digest, items_digest_outside); a
value recorded in only one of the two counts as a difference, except that a header without
answer_prefix counts as no prefix. It is also refused when either header records an items_error
(the item folder could not be digested, so the item files cannot be compared), and when the file
was begun before a freeze whose manifest is now in prereg/, or under a manifest that is now missing
or changed. A change of code, platform, Python version or the source of the answer prefix is only
recorded: each resumed session appends a "_resume" line with its utc, todo, package, model_sha256,
settings, answer_prefix_source, platform and python, and the Study A report lists each session's
code hash.

Checked against the llama-cpp-python 0.3.36 source on 7 Nov 2026 (verify again if the pinned
version changes):
  * Llama.eval() does NOT copy logits into Llama.scores unless logits_all=True (that branch is
    commented out in 0.3.36). logits_all=True would allocate n_ctx x 262,144 floats, so we read
    the last position with llama_cpp.llama_get_logits_ith(llm.ctx, -1) right after eval().
  * llm.reset() sets n_tokens to 0 and eval() then clears the KV cache from position 0, so each
    prompt is scored from scratch. No prefix reuse: Gemma 4 uses sliding-window attention, and a
    partial KV-cache removal is not safe there unless swa_full is set.
  * The Gemma 4 chat template emits "<bos>" itself, so prompts are tokenized with add_bos=False
    and special=True; we assert exactly one BOS at position 0.
The vocab-only checks (tokenizer, template, letter ids, token counts) run anywhere; the logits
path needs model weights and is exercised by `smoke` on the machine that runs the models.
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import json
import math
import os
import platform
import random
import sys
import time

import numpy as np

LETTERS4 = "ABCD"
LETTERS10 = "ABCDEFGHIJ"
THOUGHT_BLOCK = "<|channel>thought\n<channel|>"
CHANNEL_TOKEN = "<|channel>"  # opens a thought channel; its probability is logged
NO_BLOCK_MODELS = ("E2B", "E4B")  # Google's per-size templates (see the module docstring)
# Text pre-filled at the start of the model's turn, after the thought-block handling (rule in the module
# docstring), registered from the GNG-1 pilot of 7 Nov 2026 by the per-model rule that the author chose on
# 8 Nov 2026. A model without an entry here (31B) takes the rule's choice from its own GNG-1 smoke file,
# the run made with that choice (study-a --prefix-from; prefix_from_smoke).
PREFIX_CANDIDATES = ("", "Answer:", "The correct option is")
ANSWER_PREFIX = {"E2B": "Answer:", "E4B": "", "12B": "Answer:"}
# The GNG-1 pilot prompts (pre-registration, section 7): `smoke` draws GNG1_N A-D prompts and up to
# GNG1_N A-J prompts with seed GNG1_SEED from the manifest's pilot repositories.
GNG1_N, GNG1_SEED = 40, 0


def answer_prefix_for(tag: str, given: str | None = None, required: bool = False) -> str:
    """The prefix to use: the one given on the command line, else the registered one for the tag.
    An unregistered tag gets "" (the first candidate) unless `required` (Study A runs), which exits
    and names the two ways on (--prefix-from, --answer-prefix)."""
    if given is not None:
        return given
    if tag.upper() in ANSWER_PREFIX:
        return ANSWER_PREFIX[tag.upper()]
    if required:
        raise SystemExit(f"no registered answer prefix for {tag.upper()!r}: pass --prefix-from <its GNG-1 smoke "
                         "file> (the pre-registered rule's choice) or --answer-prefix (a deviation)")
    return PREFIX_CANDIDATES[0]


def read_smoke(smoke_path: str, tag: str, check_tag: bool = True) -> tuple[bytes, dict]:
    """The bytes and the JSON object of a GNG-1 smoke output given to `study-a --prefix-from`. Exits
    (SystemExit) when the tag has an entry in ANSWER_PREFIX, the file cannot be read or holds no JSON
    object, or (with `check_tag`) it was written for another tag (model_tag). `main` calls it before
    the model file is hashed, so these mistakes show at once; `prefix_from_smoke` checks the rest."""
    tag = tag.upper()
    if tag in ANSWER_PREFIX:
        raise SystemExit(f"{tag} has a registered answer prefix ({ANSWER_PREFIX[tag]!r}); --prefix-from is only "
                         "for a model without one")
    try:
        with open(smoke_path, "rb") as fh:
            raw = fh.read()
    except OSError as e:
        raise SystemExit(f"--prefix-from: cannot read {smoke_path} ({e.strerror or e})") from None
    try:
        smoke = json.loads(raw)
    except ValueError as e:
        raise SystemExit(f"{smoke_path} is not a JSON smoke output: {e}") from None
    if not isinstance(smoke, dict):
        raise SystemExit(f"{smoke_path} is not a smoke output (no JSON object)")
    if check_tag and smoke.get("model_tag") != tag:
        raise SystemExit(f"{os.path.basename(smoke_path)} cannot set the answer prefix of {tag}: it was written for "
                         f"model_tag {smoke.get('model_tag')!r}, not {tag!r}")
    return raw, smoke


def prefix_from_smoke(smoke_path: str, tag: str, model_sha256: str | None, thought_block: str, package: dict,
                      pilot_repos) -> tuple[str, dict]:
    """For `study-a --prefix-from`: the answer prefix that the pre-registered rule chose at the model's
    own GNG-1 (`prefix_rule_choice` in its smoke output), and the `answer_prefix_source` for the run
    header. Exits (SystemExit) as `read_smoke` does; otherwise exits, listing every problem, unless the
    smoke file
      * was written for this tag (model_tag, upper case) and for a model file with SHA-256
        `model_sha256` (model_file.sha256, which must be present);
      * passed its checks: checks_ok true, and tokenizer_probe present with ok true;
      * used the run's thought-block mode (settings.thought_block equal to `thought_block`);
      * scored the registered GNG-1 pilot prompts: prompts.n GNG1_N and prompts.seed GNG1_SEED, on
        the manifest's pilot repositories (`pilot_repos`, from the run's --manifest; None, a run
        without --manifest, is a problem), drawn from the run's item files (its package items_folder,
        items_digest and items_digest_outside equal to those in `package`, the run's package_state,
        and no items_error in either);
      * tried PREFIX_CANDIDATES in order (prefix_scan), with prefix_rule_choice the first candidate
        that passed, and not null (when no candidate passes, see the GNG-1 fallback in the
        pre-registration's section 7);
      * was run with that choice (settings.answer_prefix equal to prefix_rule_choice, and
        prefix_matches_rule true), so that its GNG-1 verdict is for the prefix the run will use: when
        the rule chooses a prefix other than the first candidate, smoke is run a second time with
        --answer-prefix <the choice>, and that second file is the one given here; and its GNG-1
        verdict is a pass (gng1_pass true)."""
    tag = tag.upper()
    raw, smoke = read_smoke(smoke_path, tag, check_tag=False)
    name = os.path.basename(smoke_path)

    def field(*keys):
        v = smoke
        for k in keys:
            v = v.get(k) if isinstance(v, dict) else None
        return v

    problems = []
    if field("model_tag") != tag:
        problems.append(f"it was written for model_tag {field('model_tag')!r}, not {tag!r}")
    sha = field("model_file", "sha256")
    if not sha:
        problems.append("it records no SHA-256 of its model file (model_file.sha256)")
    elif sha != model_sha256:
        problems.append(f"it was written for a model file with SHA-256 {_brief(sha)}, not {_brief(model_sha256)}")
    if field("checks_ok") is not True:
        problems.append("its checks did not pass (checks_ok is not true)")
    if field("tokenizer_probe", "ok") is not True:
        problems.append("it has no passed tokenizer probe (tokenizer_probe missing or not ok; run smoke with --probe)")
    if field("settings", "thought_block") != thought_block:
        problems.append(f"it used thought-block mode {field('settings', 'thought_block')!r}, not the run's "
                        f"{thought_block!r}")
    if (field("prompts", "n"), field("prompts", "seed")) != (GNG1_N, GNG1_SEED):
        problems.append(f"it did not score the registered GNG-1 pilot prompts (prompts n {field('prompts', 'n')!r} "
                        f"and seed {field('prompts', 'seed')!r}; registered {GNG1_N} and {GNG1_SEED}: run smoke "
                        "without --n)")
    if pilot_repos is None:
        problems.append("the run has no --manifest, so the smoke file's repositories cannot be checked against the "
                        "pilot repositories")
    elif field("repos") != sorted(pilot_repos):
        problems.append(f"it used the repositories {field('repos')!r}, not the manifest's pilot repositories "
                        f"{sorted(pilot_repos)!r}")
    s_pkg, r_pkg = (p if isinstance(p, dict) else {} for p in (field("package"), package))
    if s_pkg.get("items_error") or r_pkg.get("items_error"):
        problems.append("an item folder could not be digested (items_error), so the smoke file's item files cannot "
                        "be compared with the run's")
    else:
        diff = [k for k in ("items_folder", "items_digest", "items_digest_outside") if s_pkg.get(k) != r_pkg.get(k)]
        if diff:
            problems.append("it was written with other item files than the run's ("
                            + "; ".join(f"{k} {_brief(s_pkg.get(k))}, run {_brief(r_pkg.get(k))}" for k in diff) + ")")
    choice, scan = field("prefix_rule_choice"), field("prefix_scan")
    scan = [x for x in scan if isinstance(x, dict)] if isinstance(scan, list) else []
    used, matches = field("settings", "answer_prefix"), field("prefix_matches_rule")
    prefix_ok = False
    if [x.get("prefix") for x in scan] != list(PREFIX_CANDIDATES):
        problems.append(f"its prefix_scan did not try PREFIX_CANDIDATES {PREFIX_CANDIDATES} in order")
    elif choice != next((x["prefix"] for x in scan if x.get("passes") is True), None):
        problems.append("its prefix_rule_choice is not the first candidate that passed in its prefix_scan")
    elif choice is None:
        problems.append("no candidate prefix passed with its thought-block setting (prefix_rule_choice is null): "
                        "see the GNG-1 fallback in the pre-registration's section 7")
    elif used != choice or matches is not True:
        problems.append(f"it was not run with the rule's choice {choice!r} (settings.answer_prefix {used!r}, "
                        f"prefix_matches_rule {matches!r}), so its GNG-1 verdict is not for that prefix: run smoke "
                        f"again with --answer-prefix {choice!r} (the GNG-1 rerun with the chosen prefix) and give "
                        "that file")
    else:
        prefix_ok = True
    if prefix_ok and field("checks_ok") is True and field("gng1_pass") is not True:
        problems.append("its GNG-1 verdict is not a pass (gng1_pass is not true)")
    if problems:
        raise SystemExit(f"{name} cannot set the answer prefix of {tag}: " + "; ".join(problems))
    return choice, {"rule": "smoke file", "smoke_file": name, "smoke_sha256": hashlib.sha256(raw).hexdigest(),
                    "prefix_rule_choice": choice}


def _brief(v) -> str:
    """A header value for a message: a SHA-256 shortened to 12 characters; None as 'none recorded'."""
    if v is None:
        return "none recorded"
    return f"{v[:12]}..." if isinstance(v, str) and len(v) == 64 else repr(v)


def _short(v, n: int = 150) -> str:
    """A header value for a message, at most about n characters; None as 'none recorded'."""
    if v is None:
        return "none recorded"
    r = repr(v)
    return r if len(r) <= n else r[:n] + "..."


RUN_KEY = ("item_id", "version", "perm")
PKG_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def package_state(items_dir: str | None, root: str = PKG_ROOT) -> dict:
    """Hashes that tie a run to the frozen package (module docstring). The item folder is inside the
    package when its real path (symbolic links resolved) lies under the real path of `root`; then
    items_folder is its path from there and items_digest its digest, the one `python -m ngraph.commit
    digest <items_folder>` prints when run from the package root. Otherwise items_folder is "outside
    the package", items_digest None, and items_digest_outside the digest of the folder taken from its
    parent folder (file paths start with the folder's name), the one `python -m ngraph.commit --root
    <parent> digest <name>` prints. code_hash is the SHA-256 of CODE_SHA256.txt as it is on disk, and
    code_sha256_current whether that file still matches the code; paths the commit tool refuses (such
    as symbolic links) are left out of that check and listed under code_refused. Errors are recorded,
    not raised."""
    from . import commit

    out = {}
    try:
        out["code_hash"] = commit.code_hash(root)
    except Exception as e:  # noqa: BLE001 - recorded in the run file
        out["code_error"] = str(e)[:300]
    try:
        refused = {}  # a symbolic link or similar anywhere in the package is recorded, not fatal
        out["code_sha256_current"] = commit.check_code_sha256(root, refused)["ok"]
        if refused:
            out["code_refused"] = sorted(refused.values())[:20]
    except Exception as e:  # noqa: BLE001
        out["code_check_error"] = str(e)[:300]
    if items_dir:
        out.update(items_state(items_dir, root))
    try:
        out["manifests"] = commit.earlier_manifests(root)
    except Exception as e:  # noqa: BLE001
        out["manifests_error"] = str(e)[:300]
    return out


def items_state(items_dir: str, root: str = PKG_ROOT) -> dict:
    """The item-folder part of `package_state`: items_folder, items_digest and, for a folder outside
    the package, items_digest_outside; or items_error when the folder cannot be digested. The Study A
    report compares its --items-dir with the run files through this."""
    from . import commit

    out = {}
    try:
        real, real_root = os.path.realpath(items_dir), os.path.realpath(root)
        rel = os.path.relpath(real, real_root).replace(os.sep, "/")
        if rel == ".." or rel.startswith("../"):
            out["items_digest"] = None
            out["items_folder"] = "outside the package"
            out["items_digest_outside"] = commit.digest(os.path.dirname(real), os.path.basename(real))["digest"]
        else:
            out["items_digest"] = commit.digest(real_root, rel)["digest"]
            out["items_folder"] = rel
    except Exception as e:  # noqa: BLE001 - recorded in the run file
        out["items_error"] = str(e)[:300]
    return out


# ------------------------------------------------------------------ template
def render_prompt(template: str, user_text: str, bos_token: str, enable_thinking: bool = False) -> str:
    """Render one user turn with the model's chat template and the generation prompt."""
    from jinja2.sandbox import ImmutableSandboxedEnvironment

    env = ImmutableSandboxedEnvironment(trim_blocks=True, lstrip_blocks=True, extensions=["jinja2.ext.loopcontrols"])

    def raise_exception(msg):
        raise ValueError(msg)

    env.globals["raise_exception"] = raise_exception
    return env.from_string(template).render(
        messages=[{"role": "user", "content": user_text}], bos_token=bos_token,
        add_generation_prompt=True, enable_thinking=enable_thinking)


def apply_thought_block(prompt: str, mode: str) -> str:
    """'template' keeps the rendered prompt; 'on' makes it end with the empty thought block;
    'off' removes a trailing one."""
    if mode == "template":
        return prompt
    has = prompt.endswith(THOUGHT_BLOCK)
    if mode == "on":
        return prompt if has else prompt + THOUGHT_BLOCK
    if mode == "off":
        return prompt[: -len(THOUGHT_BLOCK)] if has else prompt
    raise ValueError(f"unknown thought-block mode {mode!r}")


def template_appends_block(template: str) -> bool:
    """Whether the template, with thinking off, ends the generation prompt with the empty thought
    block (rendered, because the template source writes the newline as an escape)."""
    try:
        return render_prompt(template, "x", "<bos>").endswith(THOUGHT_BLOCK)
    except Exception:  # noqa: BLE001 - a template that cannot render is reported as False
        return False


def thought_mode_for(tag: str, mode: str = "auto") -> str:
    if mode != "auto":
        return mode
    return "off" if tag.upper() in NO_BLOCK_MODELS else "on"


def _logsumexp(x: np.ndarray) -> float:
    m = float(np.max(x))
    return m + math.log(float(np.sum(np.exp(x - m))))


def _sha256_file(path: str, chunk: int = 1 << 24) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            b = fh.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def gguf_info(path: str, sha: bool = True) -> dict:
    """File name, size, optional SHA-256, the general.* metadata and the chat template's SHA-256."""
    from .gguf_meta import read_metadata

    meta = read_metadata(path)
    tmpl = meta.get("tokenizer.chat_template") or ""
    out = {"file": os.path.basename(path), "bytes": os.path.getsize(path),
           "general": {k: v for k, v in meta.items() if k.startswith("general.")},
           "chat_template_sha256": hashlib.sha256(tmpl.encode("utf-8")).hexdigest(),
           "template_appends_thought_block": template_appends_block(tmpl) if tmpl else None}
    if sha:
        out["sha256"] = _sha256_file(path)
    return out


# -------------------------------------------------------------------- scorer
class LetterScorer:
    """Wraps a llama_cpp.Llama model. With vocab_only=True only tokenization is available."""

    def __init__(self, model_path: str, n_ctx: int = 4096, n_batch: int = 512, n_ubatch: int = 512,
                 n_gpu_layers: int = -1, flash_attn: bool = False, vocab_only: bool = False,
                 thought_block: str = "template", enable_thinking: bool = False, verbose: bool = False,
                 answer_prefix: str = ""):
        import llama_cpp
        from llama_cpp import Llama

        if thought_block not in ("template", "on", "off"):
            raise ValueError(f"thought_block must be template, on or off, not {thought_block!r}")
        self.llama_cpp = llama_cpp
        self.model_path = model_path
        self.llm = Llama(model_path=model_path, n_ctx=n_ctx, n_batch=n_batch, n_ubatch=n_ubatch,
                         n_gpu_layers=n_gpu_layers, flash_attn=flash_attn, logits_all=False,
                         vocab_only=vocab_only, verbose=verbose)
        self.n_ctx = n_ctx
        self.n_vocab = self.llm.n_vocab()
        # llama.cpp's parameter count of the loaded file (A3 sensitivity axis); None when not available
        self.n_params = None
        if not vocab_only:
            try:
                self.n_params = int(self.llm._model.n_params())
            except Exception:  # noqa: BLE001 - recorded as missing, never estimated
                self.n_params = None
        self.enable_thinking = enable_thinking
        self.thought_block = thought_block
        self.answer_prefix = answer_prefix
        self.template = self.llm.metadata.get("tokenizer.chat_template")
        if not self.template:
            from .gguf_meta import read_metadata

            self.template = read_metadata(model_path).get("tokenizer.chat_template")
        if not self.template:
            raise RuntimeError("no chat template in the GGUF metadata")
        self.bos_id = self.llm.token_bos()
        ch = self.tokenize(CHANNEL_TOKEN, special=True)
        self.watch_ids = {CHANNEL_TOKEN: ch[0]} if len(ch) == 1 else {}
        self.bos_text = self.llm.detokenize([self.bos_id], special=True).decode("utf-8")
        self._letter_cache: dict[str, dict] = {}
        self.settings = {"n_ctx": n_ctx, "n_batch": n_batch, "n_ubatch": n_ubatch, "n_gpu_layers": n_gpu_layers,
                         "flash_attn": flash_attn, "enable_thinking": enable_thinking,
                         "thought_block": thought_block, "answer_prefix": answer_prefix,
                         "llama_cpp_python": getattr(llama_cpp, "__version__", "unknown")}

    # -- tokens
    def tokenize(self, text: str, special: bool) -> list[int]:
        return self.llm.tokenize(text.encode("utf-8"), add_bos=False, special=special)

    def letter_ids(self, letters: str) -> dict:
        """{letter: [id of "L", id of " L"]}; every variant must be a single token."""
        if letters not in self._letter_cache:
            out = {}
            for L in letters:
                ids = []
                for v in (L, " " + L):
                    t = self.tokenize(v, special=False)
                    if len(t) != 1:
                        raise RuntimeError(f"letter variant {v!r} is {len(t)} tokens: {t}")
                    ids.append(t[0])
                out[L] = ids
            self._letter_cache[letters] = out
        return self._letter_cache[letters]

    def render_base(self, user_text: str) -> str:
        """The chat-template prompt with the thought-block setting applied, without the answer prefix."""
        return apply_thought_block(render_prompt(self.template, user_text, self.bos_text, self.enable_thinking),
                                   self.thought_block)

    def render(self, user_text: str) -> str:
        return self.render_base(user_text) + self.answer_prefix

    def prompt_tokens(self, user_text: str) -> tuple[str, list[int]]:
        prompt = self.render(user_text)
        toks = self.tokenize(prompt, special=True)
        if not toks or toks[0] != self.bos_id or toks.count(self.bos_id) != 1:
            raise RuntimeError(f"expected exactly one BOS at position 0, got {toks[:4]} (count {toks.count(self.bos_id)})")
        return prompt, toks

    # -- logits
    def next_logits(self, toks: list[int]) -> np.ndarray:
        llm = self.llm
        llm.reset()
        llm.eval(toks)
        ptr = self.llama_cpp.llama_get_logits_ith(llm.ctx, -1)
        if not ptr:
            raise RuntimeError("llama_get_logits_ith returned NULL")
        return np.ctypeslib.as_array(ptr, shape=(self.n_vocab,)).astype(np.float64).copy()

    def score(self, user_text: str, letters: str = LETTERS4, top_k: int = 5) -> dict:
        _, toks = self.prompt_tokens(user_text)
        if len(toks) >= self.n_ctx - 1:
            raise RuntimeError(f"prompt of {len(toks)} tokens does not fit n_ctx={self.n_ctx}")
        t0 = time.time()
        logits = self.next_logits(toks)
        secs = time.time() - t0
        return summarise(logits, self.letter_ids(letters), self._token_text, len(toks), secs, top_k,
                         watch_ids=getattr(self, "watch_ids", None))

    def _token_text(self, tid: int) -> str:
        return self.llm.detokenize([int(tid)], special=True).decode("utf-8", errors="replace")


def summarise(logits: np.ndarray, letter_ids: dict, token_text, n_tokens: int, secs: float, top_k: int = 5,
              watch_ids: dict | None = None) -> dict:
    """Letter logits (plain and space-prefixed variants combined), letter mass, top tokens, and the
    probability of each token in watch_ids (for example "<|channel>")."""
    lse = _logsumexp(logits)
    out = {"n_tokens": n_tokens, "secs": round(secs, 4)}
    mass = 0.0
    raw = {}
    for L, ids in letter_ids.items():
        v = logits[ids]
        raw[L] = [float(x) for x in v]
        out[f"logit_{L}"] = _logsumexp(v)
        mass += float(np.sum(np.exp(v - lse)))
    out["raw"] = raw
    out["letter_mass"] = mass
    top = np.argsort(-logits)[:top_k]
    out["top"] = [[token_text(int(t)), float(math.exp(logits[t] - lse))] for t in top]
    best = max(letter_ids, key=lambda L: out[f"logit_{L}"])
    out["pred_letter"] = best
    if watch_ids:
        out["p_watch"] = {name: float(math.exp(logits[tid] - lse)) for name, tid in watch_ids.items()}
    return out


# ------------------------------------------------------------------- jobs
def load_items(items_dir: str, repos=None) -> list:
    out = []
    for p in sorted(glob.glob(os.path.join(items_dir, "*.json"))):
        with open(p) as fh:
            d = json.load(fh)
        if repos is not None and d["repo"] not in repos:
            continue
        out.extend(d["items"])
    return out


def study_a_jobs(items: list, versions=("G0", "G1", "G2", "G3", "G4"), perms=(1,), groups: dict | None = None):
    for it in items:
        for perm in perms:
            vs = it["versions"] if perm == 1 else it["versions_perm2"]
            for v in versions:
                yield {"item_id": it["item_id"], "repo": it["repo"], "group": (groups or {}).get(it["repo"]),
                       "qtype": it["qtype"], "size": it["size_target"], "version": v, "perm": perm,
                       "correct_letter": vs[v]["correct"], "text": vs[v]["text"]}


def ten_option_prompts(items: list, n: int, seed: int = 0) -> list:
    """Synthetic A-J prompts for the letter-mass check: 'which option does X call directly?'
    with one true callee and nine other nodes of the shown (true) subgraph."""
    rng = random.Random(seed)
    out = []
    pool = [it for it in items if len(it["nodes"]) >= 11]
    rng.shuffle(pool)
    for it in pool:
        edges = {tuple(e) for e in it["edges_true"]}
        callers = sorted({s for s, _ in edges})
        if not callers:
            continue
        x = rng.choice(callers)
        callees = sorted(t for s, t in edges if s == x)
        others = sorted(n for n in it["nodes"] if n != x and n not in callees)
        if len(others) < 9:
            continue
        ans = rng.choice(callees)
        opts = rng.sample(others, 9) + [ans]
        rng.shuffle(opts)
        graph = it["versions"]["G1"]["text"].split("\n\nQuestion:")[0]
        lines = [f"{LETTERS10[i]}. {o}" for i, o in enumerate(opts)]
        text = (f"{graph}\n\nQuestion: According to this call graph, which of the following functions does {x} "
                f"call directly?\n" + "\n".join(lines) + "\n\nAnswer with the letter of the correct option only.")
        out.append({"item_id": it["item_id"] + "/ten", "text": text, "correct_letter": LETTERS10[opts.index(ans)]})
        if len(out) >= n:
            break
    return out


# ---------------------------------------------------------------- run files
def _read_header(path: str):
    with open(path) as fh:
        first = fh.readline()
    try:
        return json.loads(first).get("_header")
    except (json.JSONDecodeError, AttributeError):
        return None


def _ensure_trailing_newline(path: str) -> None:
    """After an interruption the last line can be cut off without its newline; start a new line
    so the next row is not glued onto the fragment."""
    if os.path.exists(path) and os.path.getsize(path) > 0:
        with open(path, "rb+") as fh:
            fh.seek(-1, os.SEEK_END)
            if fh.read(1) != b"\n":
                fh.seek(0, os.SEEK_END)
                fh.write(b"\n")


def _done_keys(path: str) -> set:
    """Keys with a successful row. Rows with an error are retried on the next run."""
    keys = set()
    if os.path.exists(path):
        with open(path) as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue  # a line cut off by an interruption is redone
                if "item_id" in r and "error" not in r:
                    keys.add(tuple(r[k] for k in RUN_KEY))
    return keys


def load_results(path: str) -> tuple[list, dict]:
    """First successful row per (item_id, version, perm) of one run file, plus a report of
    errors that were never resolved, duplicates and unreadable lines, the header (first line) and
    the "_resume" lines of later sessions (`resumes`, in file order)."""
    header, rows, seen, errors, resumes = None, [], set(), {}, []
    n_dup = n_bad = n_err_rows = 0
    with open(path) as fh:
        for line in fh:
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                n_bad += 1
                continue
            if "_header" in r:
                header = header or r["_header"]
                continue
            if "_resume" in r:
                resumes.append(r["_resume"])
                continue
            if "item_id" not in r:
                continue
            key = tuple(r[k] for k in RUN_KEY)
            if "error" in r:
                n_err_rows += 1
                errors[key] = r["error"]
                continue
            if key in seen:
                n_dup += 1
                continue
            seen.add(key)
            rows.append(r)
    unresolved = {k: v for k, v in errors.items() if k not in seen}
    return rows, {"header": header, "resumes": resumes, "rows": len(rows), "error_rows": n_err_rows,
                  "unresolved_errors": len(unresolved), "unresolved_examples": list(unresolved.items())[:5],
                  "duplicates": n_dup, "broken_lines": n_bad}


def run_jobs(scorer, jobs: list, out_path: str, model_tag: str, header: dict, letters: str = LETTERS4,
             log_every: int = 25) -> dict:
    """Score every job not yet done in out_path. Resumable: rerun the same command after an
    interruption. Extending a file is refused (RuntimeError) when its first line is not a header, or
    when `header` differs from that header in model_tag, model_file, the model file's SHA-256
    (model_gguf.sha256), any key of settings (a header without answer_prefix counts as no prefix), the
    jobs (perms, repos, versions and n_jobs) or the item folder (package items_folder, items_digest and
    items_digest_outside); a value present in only one of the two headers counts as a difference. It
    is also refused when either header records an items_error: the item folder could not be digested,
    so the item files cannot be compared. And it is refused when package.manifests in `header` names a
    manifest while the file's first line names none (a file begun before the freeze is a pilot), or
    when a manifest named in the first line is missing from `header` or has another SHA-256; a later
    manifest (the addendum) may be added. Code, platform, Python version and the source of the answer
    prefix are only recorded: each resumed session appends a "_resume" line with utc, todo, and
    package, model_sha256, settings, answer_prefix_source, platform and python from `header`. Other
    header fields are neither compared nor recorded again."""
    if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
        old = _read_header(out_path)
        if old is None:
            raise RuntimeError(f"{out_path} has no header line; refusing to append")
        for k in ("model_tag", "model_file"):
            if old.get(k) != header.get(k):
                raise RuntimeError(f"{out_path} was written for {k}={old.get(k)!r}, not {header.get(k)!r}")
        old_sha, new_sha = ((h.get("model_gguf") or {}).get("sha256") for h in (old, header))
        if old_sha != new_sha:
            raise RuntimeError(f"{out_path} was written with another model file (SHA-256 {_brief(old_sha)}, "
                               f"now {_brief(new_sha)})")
        old_set, new_set = ({"answer_prefix": "", **(h.get("settings") or {})} for h in (old, header))
        if old_set.get("thought_block") != new_set.get("thought_block"):
            raise RuntimeError(f"{out_path} was written with a different thought-block setting")
        if old_set["answer_prefix"] != new_set["answer_prefix"]:
            raise RuntimeError(f"{out_path} was written with a different answer prefix")
        diff = sorted(k for k in old_set.keys() | new_set.keys() if old_set.get(k) != new_set.get(k))
        if diff:
            raise RuntimeError(f"{out_path} was written with other settings: "
                               + "; ".join(f"{k} {old_set.get(k)!r}, now {new_set.get(k)!r}" for k in diff))
        diff = [k for k in ("perms", "repos", "versions", "n_jobs") if old.get(k) != header.get(k)]
        if diff:
            raise RuntimeError(f"{out_path} was written for other jobs: "
                               + "; ".join(f"{k} {_short(old.get(k))}, now {_short(header.get(k))}" for k in diff))
        old_pkg, new_pkg = (h.get("package") or {} for h in (old, header))
        if old_pkg.get("items_error") or new_pkg.get("items_error"):
            raise RuntimeError(f"{out_path}: the item folder could not be digested, so the item files cannot be "
                               f"compared (items_error {_brief(old_pkg.get('items_error'))}, now "
                               f"{_brief(new_pkg.get('items_error'))})")
        diff = [k for k in ("items_folder", "items_digest", "items_digest_outside") if old_pkg.get(k) != new_pkg.get(k)]
        if diff:
            raise RuntimeError(f"{out_path} was written with other item files ("
                               + "; ".join(f"{k} {_brief(old_pkg.get(k))}, now {_brief(new_pkg.get(k))}" for k in diff)
                               + ")")
        old_man, new_man = ((p.get("manifests") or {}) for p in (old_pkg, new_pkg))
        if (new_man and not old_man) or any(new_man.get(k) != v for k, v in old_man.items()):
            def names(m):
                return ", ".join(f"{k} {_brief(v)}" for k, v in sorted(m.items())) or "none"
            raise RuntimeError(f"{out_path} was begun when prereg/ held other manifests (first line: {names(old_man)}; "
                               f"now: {names(new_man)}). A file begun before a freeze is a pilot and is not continued "
                               "after it, and a manifest recorded in its first line must still be there unchanged: "
                               "start a new file (another --out)")
    done = _done_keys(out_path)
    todo = [j for j in jobs if tuple(j[k] for k in RUN_KEY) not in done]
    new_file = not os.path.exists(out_path) or os.path.getsize(out_path) == 0
    _ensure_trailing_newline(out_path)
    t_start, n_tok, n_err = time.time(), 0, 0
    with open(out_path, "a") as fh:
        if new_file:
            fh.write(json.dumps({"_header": header}) + "\n")
        else:
            resume = {"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "todo": len(todo),
                      "package": header.get("package"), "model_sha256": (header.get("model_gguf") or {}).get("sha256"),
                      "settings": header.get("settings"), "answer_prefix_source": header.get("answer_prefix_source"),
                      "platform": header.get("platform"), "python": header.get("python")}
            fh.write(json.dumps({"_resume": resume}) + "\n")
        for i, j in enumerate(todo):
            row = {k: v for k, v in j.items() if k != "text"}
            row["model"] = model_tag
            try:
                row.update(scorer.score(j["text"], letters))
                n_tok += row["n_tokens"]
            except Exception as e:  # noqa: BLE001 - recorded and retried on the next run, never dropped
                row["error"] = str(e)[:300]
                n_err += 1
            fh.write(json.dumps(row) + "\n")
            fh.flush()
            if (i + 1) % log_every == 0 or i + 1 == len(todo):
                el = time.time() - t_start
                rate = n_tok / el if el else 0.0
                eta = (len(todo) - i - 1) * el / (i + 1)
                print(f"[{model_tag}] {i + 1}/{len(todo)} done, {rate:.0f} prompt tok/s, "
                      f"{n_err} errors, about {eta / 3600:.2f} h left", flush=True)
    return {"scored": len(todo), "skipped_done": len(jobs) - len(todo), "errors": n_err}


# -------------------------------------------------------------------- checks
def token_parity(lens: dict) -> dict:
    """lens: {(item_id, perm, version): n_tokens}. Paired token differences G2-G1 and G4-G3."""
    out = {}
    for a, b in (("G1", "G2"), ("G3", "G4")):
        d = [lens[(i, p, b)] - lens[(i, p, a)] for (i, p, v) in lens if v == a and (i, p, b) in lens]
        if d:
            out[f"{b}-{a}"] = {"n": len(d), "mean": float(np.mean(d)), "mean_abs": float(np.mean(np.abs(d))),
                               "min": int(min(d)), "max": int(max(d))}
    return out


def count_tokens(scorer, jobs: list) -> dict:
    lens = {}
    by_version: dict[str, list] = {}
    for j in jobs:
        n = len(scorer.prompt_tokens(j["text"])[1])
        lens[(j["item_id"], j["perm"], j["version"])] = n
        by_version.setdefault(j["version"], []).append(n)
    allv = list(lens.values())
    return {"prompts": len(allv), "prompt_tokens": int(sum(allv)), "max_tokens": int(max(allv)),
            "mean_tokens": float(np.mean(allv)),
            "mean_by_version": {v: float(np.mean(x)) for v, x in sorted(by_version.items())},
            "parity": token_parity(lens)}


def tokenizer_probe(scorer, items: list, n_names: int = 4000, n_prompts: int = 20, seed: int = 0) -> dict:
    """Strings whose tokenization must match between the vocab file used to build the items and
    each model file: identifiers (real and neutral) and some full prompts."""
    rng = random.Random(seed)
    names = set()
    for it in items:
        for k, v in it.get("neutral_map", {}).items():
            names.add(k)
            names.add(v)
    names = sorted(names)
    rng.shuffle(names)
    names = sorted(names[:n_names])
    pick = rng.sample(items, min(n_prompts, len(items)))
    prompts = [it["versions"]["G2"]["text"] for it in pick] + [it["versions"]["G1"]["text"] for it in pick]
    strings = names + prompts
    return {"strings": strings, "ids": [scorer.tokenize(s, special=False) for s in strings]}


def check_probe(scorer, probe: dict) -> dict:
    bad = [s for s, ids in zip(probe["strings"], probe["ids"]) if scorer.tokenize(s, special=False) != ids]
    return {"n": len(probe["strings"]), "mismatches": len(bad), "examples": bad[:5], "ok": not bad}


def _mass_summary(rows: list, letters: str) -> dict:
    masses = [r["letter_mass"] for r in rows]
    return {"n": len(rows), "share_mass_ge_0.9": float(np.mean([m >= 0.9 for m in masses])) if rows else None,
            "min_mass": min(masses) if masses else None, "mean_mass": float(np.mean(masses)) if rows else None,
            "accuracy": float(np.mean([r["correct"] for r in rows])) if rows else None,
            "pred_letter_counts": {L: sum(r["pred_letter"] == L for r in rows) for L in letters},
            "prompt_tok_per_s": float(sum(r["n_tokens"] for r in rows) / max(sum(r["secs"] for r in rows), 1e-9)),
            "mean_tokens": float(np.mean([r["n_tokens"] for r in rows])) if rows else None,
            "examples_top": [r["top"] for r in rows[:3]],
            "p_channel": _watch_summary(rows, CHANNEL_TOKEN)}


def _watch_summary(rows: list, name: str) -> dict | None:
    vals = [r["p_watch"][name] for r in rows if name in r.get("p_watch", {})]
    if not vals:
        return None
    return {"n": len(vals), "mean": float(np.mean(vals)), "median": float(np.median(vals)), "max": float(max(vals)),
            "share_gt_0.1": float(np.mean([v > 0.1 for v in vals]))}


def smoke(scorer, items: list, n: int = GNG1_N, seed: int = GNG1_SEED, n_repeat: int = 10, n_alt: int | None = None,
          probe: dict | None = None, prefix_candidates=PREFIX_CANDIDATES) -> dict:
    """GNG-1 checks: BOS and special tokens, tokenizer against the probe file, letter mass for
    A-D and A-J prompts, the same under the other thought-block setting (n_alt prompts each,
    default all), the probability of "<|channel>" at the answer position, repeatability, and the
    letter mass under each answer-prefix candidate with the own setting (`prefix_scan`).

    Pre-registered rules: the per-size setting stays if it passes the letter-mass criterion; only if
    it fails and the other setting passes is the setting switched, and the switch is logged as a
    deviation before any confirmatory run. The answer prefix is the first candidate, in order, under
    which the model passes with its own setting (`prefix_rule_choice`); `prefix_matches_rule` says
    whether the prefix in use is that one."""
    rng = random.Random(seed)
    pick = rng.sample(items, min(n, len(items)))
    ad = [{"item_id": it["item_id"], "text": it["versions"]["G1"]["text"], "correct_letter": it["versions"]["G1"]["correct"]}
          for it in pick]
    aj = ten_option_prompts(items, n, seed)
    res = {"settings": scorer.settings, "model": os.path.basename(scorer.model_path),
           "answer_prefix": getattr(scorer, "answer_prefix", ""),
           "prompts": {"n": n, "seed": seed, "n_alt": n_alt, "AD": len(ad), "AJ": len(aj)}}
    prompt, toks = scorer.prompt_tokens(ad[0]["text"])
    res["prompt_tail"] = prompt[-80:]
    base = scorer.render_base(ad[0]["text"])
    res["template_appends_thought_block"] = template_appends_block(scorer.template)
    res["bos_ok"] = toks[0] == scorer.bos_id and toks.count(scorer.bos_id) == 1
    turn = scorer.tokenize("<|turn>", special=True)
    res["special_tokens_ok"] = len(turn) == 1 and toks.count(turn[0]) >= 2
    res["letter_ids_AD"] = scorer.letter_ids(LETTERS4)
    res["letter_ids_AJ"] = scorer.letter_ids(LETTERS10)
    res["tokenizer_probe"] = check_probe(scorer, probe) if probe else None

    def run(prompts, letters):
        rows = []
        for p in prompts:
            r = scorer.score(p["text"], letters)
            r["correct"] = int(r["pred_letter"] == p["correct_letter"])
            rows.append(r)
        return rows

    res["AD"] = _mass_summary(run(ad, LETTERS4), LETTERS4)
    res["AJ"] = _mass_summary(run(aj, LETTERS10), LETTERS10)
    # the other thought-block setting, on the same A-D and A-J prompts
    mode = scorer.thought_block
    alt = "off" if (mode == "on" or (mode == "template" and base.endswith(THOUGHT_BLOCK))) else "on"
    k = len(ad) if n_alt is None else n_alt
    scorer.thought_block = alt
    try:
        res["AD_other_thought_block"] = dict(_mass_summary(run(ad[:k], LETTERS4), LETTERS4), mode=alt)
        res["AJ_other_thought_block"] = dict(_mass_summary(run(aj[:k], LETTERS10), LETTERS10), mode=alt)
    finally:
        scorer.thought_block = mode
    diffs, agree = [], 0
    for p in ad[:n_repeat]:
        a = scorer.score(p["text"])
        b = scorer.score(p["text"])
        diffs.append(max(abs(a[f"logit_{L}"] - b[f"logit_{L}"]) for L in LETTERS4))
        agree += a["pred_letter"] == b["pred_letter"]
    res["repeat"] = {"n": len(diffs), "argmax_agreement": agree / max(len(diffs), 1),
                     "max_abs_logit_diff": max(diffs) if diffs else None}
    res["checks_ok"] = bool(res["bos_ok"] and res["special_tokens_ok"]
                            and (probe is None or res["tokenizer_probe"]["ok"]))
    # answer-prefix rule: own thought-block setting, candidates in the registered order
    own_prefix, scan = getattr(scorer, "answer_prefix", ""), []
    try:
        for cand in prefix_candidates:
            if cand == own_prefix:
                sad, saj = res["AD"], res["AJ"]
            else:
                scorer.answer_prefix = cand
                sad, saj = _mass_summary(run(ad, LETTERS4), LETTERS4), _mass_summary(run(aj, LETTERS10), LETTERS10)
            scan.append({"prefix": cand, "AD_share_mass_ge_0.9": sad["share_mass_ge_0.9"],
                         "AJ_share_mass_ge_0.9": saj["share_mass_ge_0.9"],
                         "AD_mean_mass": sad["mean_mass"], "AJ_mean_mass": saj["mean_mass"],
                         "passes": bool(_mass_ok(sad) and _mass_ok(saj))})
    finally:
        scorer.answer_prefix = own_prefix
    res["prefix_scan"] = scan
    res["prefix_rule_choice"] = next((x["prefix"] for x in scan if x["passes"]), None)
    res["prefix_matches_rule"] = bool(scan) and res["prefix_rule_choice"] == own_prefix
    res["own_setting_passes"] = bool(_mass_ok(res["AD"]) and _mass_ok(res["AJ"]))
    res["other_setting_passes"] = bool(_mass_ok(res["AD_other_thought_block"]) and _mass_ok(res["AJ_other_thought_block"]))
    # the thought-block decision rests on the letter-mass criterion only; a token or probe failure
    # is a different problem and is not fixed by switching the setting
    res["thought_block_decision"] = ("keep" if res["own_setting_passes"] else
                                     "switch (log a deviation)" if res["other_setting_passes"] else "neither passes")
    res["gng1_pass"] = res["checks_ok"] and res["own_setting_passes"]
    return res


def _mass_ok(summary: dict) -> bool:
    """GNG-1 letter-mass criterion: mass of at least 0.9 on at least 95% of the prompts."""
    return (summary.get("share_mass_ge_0.9") or 0) >= 0.95


# ---------------------------------------------------------------------- CLI
def _load_manifest(path: str | None):
    if not path:
        return None, None
    with open(path) as fh:
        man = json.load(fh)
    groups = {r["label"]: r["group"] for r in man["repos"]}
    roles = {r["label"]: r["role"] for r in man["repos"]}
    return groups, roles


def main(argv=None):
    ap = argparse.ArgumentParser(description="Letter-logit runner (llama-cpp-python)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("smoke", "study-a", "count", "make-probe"):
        s = sub.add_parser(name)
        s.add_argument("--model", required=True, help="GGUF file (a vocab-only file works for count and make-probe)")
        s.add_argument("--tag", required=True, help="short model name used in outputs: E2B, E4B, 12B, 31B, or 'vocab'")
        s.add_argument("--items-dir", required=True)
        s.add_argument("--repos", help="comma-separated repository labels (default: by role from --manifest, else all)")
        s.add_argument("--manifest", help="repos_manifest.json: adds the familiar/fresh group and selects repos by role")
        s.add_argument("--thought-block", default="auto", choices=("auto", "template", "on", "off"),
                       help="auto: none for E2B/E4B, pre-filled for other sizes (Google's per-size templates)")
        s.add_argument("--n-ctx", type=int, default=4096)
        s.add_argument("--n-batch", type=int, default=512)
        s.add_argument("--n-gpu-layers", type=int, default=-1)
        s.add_argument("--flash-attn", action="store_true")
        s.add_argument("--perms", default=None, help="'1' or '1,2' (default: 1,2 for E2B/E4B, else 1)")
        prefix_opts = s.add_mutually_exclusive_group()
        prefix_opts.add_argument("--answer-prefix", default=None,
                                 help="text pre-filled at the start of the model's turn (default: the one registered "
                                      "for --tag in ANSWER_PREFIX; none for a tag without one, for which study-a needs "
                                      "--prefix-from or this option). A prefix other than the registered one or the "
                                      "GNG-1 rule's choice is a deviation; study-a records a prefix given here as "
                                      "'given (a deviation)'")
        if name == "study-a":
            prefix_opts.add_argument("--prefix-from", metavar="SMOKE_JSON",
                                     help="the model's GNG-1 smoke output: use its prefix_rule_choice (the "
                                          "pre-registered rule's choice) for a tag without an entry in ANSWER_PREFIX; "
                                          "refused unless that file is for this --tag and model file (SHA-256), its "
                                          "checks and tokenizer probe passed, it used this run's thought-block mode, "
                                          "the registered pilot prompts (needs --manifest) and this run's item files, "
                                          "a candidate passed, and it was run with that choice and passed GNG-1 "
                                          "(when the choice is not the first candidate: the smoke rerun with "
                                          "--answer-prefix <the choice>; all checks: runner.prefix_from_smoke)")
        s.add_argument("--out", required=True)
    sub.choices["study-a"].add_argument("--versions", default="G0,G1,G2,G3,G4")
    sub.choices["smoke"].add_argument("--n", type=int, default=GNG1_N,
                                      help=f"A-D pilot prompts, and at most as many A-J prompts (registered for "
                                           f"GNG-1: {GNG1_N}; study-a --prefix-from refuses another value)")
    sub.choices["smoke"].add_argument("--n-alt", type=int, default=None,
                                      help="prompts scored under the other thought-block setting (default: all)")
    sub.choices["smoke"].add_argument("--probe", help="tokenizer_probe.json written by make-probe")
    a = ap.parse_args(argv)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)  # a fresh copy has no runs/ folder

    groups, roles = _load_manifest(a.manifest)
    default_role = "pilot" if a.cmd == "smoke" else "confirmatory"
    if a.repos:
        repos = set(a.repos.split(","))
    elif roles:
        repos = {k for k, v in roles.items() if v == default_role}
    else:
        repos = None
    items = load_items(a.items_dir, repos)
    if not items:
        sys.exit("no items found")
    tb = thought_mode_for(a.tag, a.thought_block)
    perms = tuple(int(x) for x in (a.perms or ("1,2" if a.tag.upper() in NO_BLOCK_MODELS else "1")).split(","))
    vocab_only = a.cmd in ("count", "make-probe")
    prefix_from = getattr(a, "prefix_from", None)  # a study-a option
    if prefix_from:
        read_smoke(prefix_from, a.tag)  # a missing file or another tag shows before the model file is hashed
    prefix = None if prefix_from else answer_prefix_for(a.tag, a.answer_prefix, required=(a.cmd == "study-a"))
    model_gguf = gguf_info(a.model) if a.cmd == "study-a" else None  # hashed once, before the scorer is built
    pkg = package_state(a.items_dir) if a.cmd == "study-a" else None
    if prefix_from:
        pilot = None if roles is None else [k for k, v in roles.items() if v == "pilot"]
        prefix, prefix_source = prefix_from_smoke(prefix_from, a.tag, model_gguf.get("sha256"), tb, pkg, pilot)
    else:  # recorded in the study-a header only
        prefix_source = {"rule": "ANSWER_PREFIX" if a.answer_prefix is None else "given (a deviation)"}
    scorer = LetterScorer(a.model, n_ctx=a.n_ctx, n_batch=a.n_batch, n_gpu_layers=a.n_gpu_layers,
                          flash_attn=a.flash_attn, vocab_only=vocab_only, thought_block=tb, answer_prefix=prefix)

    if a.cmd == "make-probe":
        probe = tokenizer_probe(scorer, items)
        probe["source"] = gguf_info(a.model)
        with open(a.out, "w") as fh:
            json.dump(probe, fh)
        print(json.dumps({"strings": len(probe["strings"]), "source": probe["source"]["file"]}))
        return
    if a.cmd == "count":
        res = count_tokens(scorer, list(study_a_jobs(items, perms=perms, groups=groups)))
        res.update({"thought_block": tb, "perms": list(perms), "repos": sorted({it["repo"] for it in items})})
        with open(a.out, "w") as fh:
            json.dump(res, fh, indent=1)
        print(json.dumps({k: v for k, v in res.items() if k != "repos"}))
        return
    if a.cmd == "smoke":
        probe = None
        if a.probe:
            with open(a.probe) as fh:
                probe = json.load(fh)
        res = smoke(scorer, items, n=a.n, n_alt=a.n_alt, probe=probe)
        res["model_tag"] = a.tag.upper()  # checked by study-a --prefix-from, with the model file's SHA-256
        res["repos"] = sorted({it["repo"] for it in items})  # and the pilot repositories
        res["model_file"] = gguf_info(a.model, sha=True)
        res["package"] = package_state(a.items_dir)
        res["model_n_params"] = getattr(scorer, "n_params", None)
        if roles:  # projected Study A hours for this model on the confirmatory repositories
            conf = load_items(a.items_dir, {k for k, v in roles.items() if v == "confirmatory"})
            c = count_tokens(scorer, list(study_a_jobs(conf, perms=perms)))
            tps = res["AD"]["prompt_tok_per_s"]
            res["projection"] = {"perms": list(perms), "prompts": c["prompts"], "prompt_tokens": c["prompt_tokens"],
                                 "tok_per_s": tps, "hours_x1.3": c["prompt_tokens"] / max(tps, 1e-9) * 1.3 / 3600}
        with open(a.out, "w") as fh:
            json.dump(res, fh, indent=1)
        keys = ("gng1_pass", "checks_ok", "own_setting_passes", "other_setting_passes", "thought_block_decision",
                "bos_ok", "special_tokens_ok", "template_appends_thought_block", "answer_prefix",
                "prefix_rule_choice", "prefix_matches_rule", "prompt_tail", "model_n_params")
        print(json.dumps({k: res[k] for k in keys}), json.dumps(res["tokenizer_probe"])[:300],
              json.dumps({k: v for k, v in res["AD"].items() if k != "examples_top"}),
              json.dumps({k: v for k, v in res["AJ"].items() if k != "examples_top"}),
              json.dumps({k: v for k, v in res["AD_other_thought_block"].items() if k != "examples_top"}),
              json.dumps({k: v for k, v in res["AJ_other_thought_block"].items() if k != "examples_top"}),
              json.dumps(res["repeat"]), json.dumps(res.get("projection")), json.dumps(res["prefix_scan"]), sep="\n")
        return
    versions = a.versions.split(",")
    jobs = list(study_a_jobs(items, versions=tuple(versions), perms=perms, groups=groups))
    tag = a.tag.upper()  # the analysis matches tags to the registered model names
    header = {"model_tag": tag, "model_file": os.path.basename(a.model), "settings": scorer.settings,
              "answer_prefix_source": prefix_source, "model_gguf": model_gguf, "model_n_params": scorer.n_params,
              "package": pkg,
              "perms": list(perms), "versions": versions,
              "letter_ids": scorer.letter_ids(LETTERS4), "repos": sorted({it["repo"] for it in items}),
              "platform": platform.platform(), "python": sys.version.split()[0], "n_jobs": len(jobs),
              "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    print(json.dumps(run_jobs(scorer, jobs, a.out, tag, header)))


if __name__ == "__main__":
    main()
