"""Token counting with Gemma 4's own tokenizer, read from a GGUF file through llama-cpp-python.

A vocab-only GGUF is enough (llama.cpp ships models/ggml-vocab-gemma-4.gguf for its tokenizer
tests); a full model GGUF works too. Checked on 7 Nov 2026 with llama-cpp-python 0.3.36:
the vocab file reproduces all 46 of llama.cpp's tokenizer test vectors. The tokenizer in the
model files actually used for the runs must be checked against it (`same_tokenizer`).
"""

from __future__ import annotations

import functools
import hashlib
import os


class GemmaCounter:
    def __init__(self, gguf_path: str):
        from llama_cpp import Llama  # imported here so the rest of the package has no hard dependency

        self.path = gguf_path
        self.llm = Llama(model_path=gguf_path, vocab_only=True, verbose=False)
        self.__name__ = "gemma4_gguf_tokenizer"

    @functools.lru_cache(maxsize=1_000_000)
    def __call__(self, s: str) -> int:
        return len(self.llm.tokenize(s.encode("utf-8"), add_bos=False, special=False))

    @functools.cached_property
    def sha256(self) -> str:
        h = hashlib.sha256()
        with open(self.path, "rb") as fh:
            for b in iter(lambda: fh.read(1 << 24), b""):
                h.update(b)
        return h.hexdigest()

    def record(self) -> dict:
        """What the item files store about the tokenizer: file name and SHA-256 (no local path)."""
        return {"file": os.path.basename(self.path), "sha256": self.sha256}

    def uncached(self, s: str) -> int:
        """Token count without the cache (for whole prompts, which are rarely repeated)."""
        return len(self.llm.tokenize(s.encode("utf-8"), add_bos=False, special=False))

    def tokens(self, s: str, special: bool = True) -> list[int]:
        return self.llm.tokenize(s.encode("utf-8"), add_bos=False, special=special)


def same_tokenizer(a: GemmaCounter, b: GemmaCounter, probes) -> bool:
    """True when both files tokenize every probe string identically."""
    return all(a.tokens(p) == b.tokens(p) for p in probes)
