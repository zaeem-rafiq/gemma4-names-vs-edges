# Gemma 4 vocabulary file

`ggml-vocab-gemma-4.gguf` is copied unchanged from the llama.cpp repository
(https://github.com/ggml-org/llama.cpp), file `models/ggml-vocab-gemma-4.gguf` at commit
`31424b7cf14604ca65a9195123da1413f31c4472` (committed 2026-11-06), under llama.cpp's MIT licence
(`LICENSE` in this folder).

- SHA-256: `58b1ba0b57f3b4d7c468ba4ffd91ad85190346a3d7ad7e71d1cabaae8a14bb65`
- Size: 15.8 MB; vocabulary only (no weights), 262,144 tokens, with the Gemma 4 chat template.
- Use here: counting tokens when neutral names are generated, and the tokenizer check in the
  smoke test. With llama-cpp-python 0.3.36 it reproduced all 46 of llama.cpp's own tokenizer test
  vectors for this file (checked 7 Nov 2026).
- Its metadata describes a mixture-of-experts configuration (128 experts), so it was probably
  exported from the 26B-A4B model. That is a guess from the metadata, not documented.

Origin and licence of the content: the vocabulary and the chat template in this file are those of
Google's Gemma 4 models. The file itself carries no licence key in its metadata. The Gemma 4 model
files we run give `general.license` = `apache-2.0` and `general.license.link` =
`https://ai.google.dev/gemma/docs/gemma_4_license` in their metadata (recorded in
`data/gng1/first_run_no_prefix/smoke_*.json`). llama.cpp's conversion and distribution of the file
are under llama.cpp's MIT licence (`LICENSE` in this folder). A copy of the Apache License 2.0 is in
`LICENSE-Apache-2.0.txt` in this folder: the text at https://www.apache.org/licenses/LICENSE-2.0.txt,
fetched on 8 Nov 2026 (SHA-256 `cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30`, the same
bytes as Debian's `/usr/share/common-licenses/Apache-2.0`). The Gemma 4 licence page that the metadata links
was not read for this note. This note records what the files state; it is not a legal opinion.
