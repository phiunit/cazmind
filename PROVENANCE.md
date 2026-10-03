# Provenance

How this code was written, recorded on the day it was written (2026-10-03).

1. **Spec first.** `SPEC.md` was written from public, textbook techniques only: Okapi BM25 (Robertson and Zaragoza), HMAC-SHA256 (RFC 2104), base64url encoding. It describes behavior, not any earlier code.
2. **Isolated implementation.** The code in `cazmind/`, `tests/`, and `examples/` was written by an AI coding agent (Claude) whose only design input was `SPEC.md`. It was told to work only inside this folder and not to open, search, or read any other project, earlier implementation, or the web. Its report confirmed it did not.
3. **Overlap check.** After the build, every source line of 25 characters or more was compared against an earlier internal implementation of similar techniques. Result: 0 identical lines of 232. Shared 8-word sequences: 4 of 2,461 (0.2%), all of them standard-library import lists (`import base64, hashlib, hmac, json, os`).
4. **Design differences from the earlier work**, chosen fresh: sensitivity labels live in each file's frontmatter; search statistics are computed only over passages the caller may see; there is no hardcoded fallback secret anywhere (dev mode uses a random per-process secret); unknown sensitivity labels and unknown roles fail closed.
5. **No third-party content.** The example company (Riverbend Bike Co) and its documents are fictional, and the only domain used is example.com.

Copyright: Phi Unit Research Partners Inc. License: Apache-2.0.
