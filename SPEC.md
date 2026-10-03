# CazMind engine v0.1: functional spec

Written 2026-10-03 from public, textbook techniques only (Okapi BM25, RFC 2104 HMAC, base64url). This spec is the ONLY input the implementer gets. It describes behavior, not any prior code.

## Goal
A small, dependency-free Python library + CLI that turns a folder of markdown files into a permission-aware, searchable company brain with citations. Python 3.10+, standard library only.

## Layout
```
engine/
  cazmind/__init__.py      version = "0.1.0"
  cazmind/corpus.py        load + parse markdown, split into passages
  cazmind/search.py        BM25 index, JSON save/load, query
  cazmind/access.py        sensitivity levels, roles, topic refusals
  cazmind/session.py       signed session tokens
  cazmind/config.py        load cazmind.json
  cazmind/__main__.py      CLI
  examples/riverbend/      fictional company corpus + cazmind.json
  tests/                   unittest suite
  README.md  .gitignore
```

## 1. Corpus (`corpus.py`)
- Walk a directory recursively for `*.md`. Ignore files and folders starting with `.` or `_`.
- Optional frontmatter: a first line of `---`, then `key: value` lines, then `---`. Parse by hand (no YAML lib). Values are strings; `tags` may be a comma-separated list or `[a, b]`.
- Known fields: `title` (default: first `# ` heading, else filename stem), `sensitivity` (default from config, else `internal`), `source` (URL or free text, optional), `updated` (free text date, optional), `tags`.
- Split the body into passages at `#`/`##`/`###` headings. Each passage keeps: `doc_id` (path relative to corpus root, forward slashes), `title`, `heading` (nearest heading text, may be empty), `text`, `sensitivity`, `source`, `updated`, `tags`. If a section is longer than `max_chars` (default 1500), split it on paragraph boundaries into chunks under the limit (a single oversized paragraph may stand alone).
- Skip passages whose text is empty after stripping.

## 2. Search (`search.py`)
- Tokenizer: lowercase, split on a Unicode word regex (`\w+`), drop tokens of length 1 and a short English stopword list (~40 common words). No stemming.
- Okapi BM25 with k1 = 1.2, b = 0.75, IDF = ln(1 + (N - df + 0.5) / (df + 0.5)). Index the title and heading along with the text (title tokens counted twice to weight them).
- `Index.build(passages)`, `index.save(path)` / `Index.load(path)` as JSON (passages + whatever stats you need; keep it rebuildable).
- `index.search(query, k=5, allowed=None)` → list of results `{score, doc_id, title, heading, source, updated, snippet}`, best first, zero-score hits excluded. `snippet` = up to ~240 chars of the passage around the first query-term hit.
- **Privacy property (must hold, must be tested):** when `allowed` (a predicate on passages) is given, BOTH the candidate set AND the corpus statistics (N, document frequencies, average length) come only from allowed passages. A passage a role can't see must never appear and must never change the ranking or scores of passages it can see. Simplest correct approach: build a sub-index over the allowed passages (cache it per clearance level).

## 3. Access (`access.py`)
- Ordered sensitivity levels, default `["public", "internal", "restricted", "confidential"]`, overridable in config.
- Roles map to a clearance level (`{"guest": "public", "staff": "internal", "lead": "restricted", "admin": "confidential"}` by default). Unknown role → `public`. Unknown sensitivity label on a document → treated as the HIGHEST level (fail closed).
- `can_see(role, passage) -> bool`, and a helper returning the predicate for `Index.search(allowed=...)`.
- Topic refusals: config list of `{ "name", "roles": [...], "match_any": [phrases], "message" }`. `check_question(role, question)` returns the first rule whose roles include the role and any phrase appears in the lowercased question (whole-word-ish match), else None. A refusal means: don't search, return the message.
- `answer(index, config, role, question, k)` convenience: refusal check, then filtered search. Returns `{"refused": bool, "message": str|None, "results": [...]}`.

## 4. Session tokens (`session.py`)
- Token = `base64url(json_payload) + "." + base64url(HMAC_SHA256(secret, payload_part))`, no padding.
- Payload: `sub` (email, normalized lowercase/stripped), `role`, `exp` (unix seconds), optional `name`. `issue(secret, sub, role, ttl=12h, name=None)`, `verify(secret, token) -> payload | None`. Verify uses `hmac.compare_digest`, rejects malformed tokens, bad signatures, missing or past `exp`. Never raises on bad input; returns None.
- Secret resolution `resolve_secret(explicit=None)`: explicit arg, else env `CAZMIND_SESSION_SECRET`. Must be at least 32 bytes, else raise `ValueError`. If neither is set: if env `CAZMIND_DEV == "1"`, return a RANDOM per-process secret (`secrets.token_bytes(32)`) and emit a one-time warning to stderr; otherwise raise `RuntimeError`. There is NO hardcoded fallback secret anywhere in the code.

## 5. Config (`config.py`)
- `load(path=None)`: reads `cazmind.json` if given; missing file → defaults. Keys: `org_name`, `levels`, `roles`, `default_sensitivity`, `max_chars`, `refusals`. Validate: every role's level and `default_sensitivity` must be in `levels` (raise `ValueError` with a clear message).

## 6. CLI (`python -m cazmind`)
- `index <corpus_dir> [-o index.json] [--config cazmind.json]` → builds and saves; prints passage and document counts.
- `ask "<question>" [--index index.json] [--config cazmind.json] [--role staff] [-k 5] [--json]` → prints refusal message, or numbered results with title, heading, source, and snippet. `--json` prints the `answer()` dict.
- Exit code 0 on success, 2 on usage errors.

## 7. Example corpus (`examples/riverbend/`)
A FICTIONAL company, "Riverbend Bike Co" (12-person bike shop + repair). 6 to 8 short markdown docs with frontmatter: onboarding (public or internal), repair intake SOP (internal), returns policy (public), vendor list (internal), pricing & margins (restricted), salary bands (confidential), a meeting note (internal). Plus `cazmind.json` with one refusal rule (e.g. guest/staff asking about salaries gets "Ask the owner directly."). No real people, companies, emails, or domains except `example.com`.

## 8. Tests (`tests/`, unittest, run with `python -m unittest discover -s tests` from `engine/`)
Must cover at least: frontmatter parsing incl. missing frontmatter; heading split + long-section chunking; BM25 ranks the obviously relevant passage first on the example corpus; save/load round-trip gives identical results; **privacy property** (a hidden passage never appears AND visible-passage scores equal those from an index built only from visible passages); unknown sensitivity fails closed; unknown role gets public only; refusal fires for the right role only; token issue/verify, tamper, wrong secret, expiry, malformed input; secret resolution raises with nothing set, random with CAZMIND_DEV=1, rejects short secrets; config validation; CLI index + ask smoke test via subprocess on the example corpus.

## 9. README.md
For an outside developer. What it is (one paragraph), quickstart against the example corpus, the corpus format, the permission model incl. the privacy property, session tokens + the secret rule, what it is NOT (no embeddings, no LLM call; it's the retrieval + governance layer you put under one), "License: Apache-2.0". Plain voice, short paragraphs, no em dashes, no marketing language.
