# CazMind engine

CazMind turns a folder of markdown files into a searchable company brain that respects permissions. Every document carries a sensitivity level, every user has a role, and a search only ever sees what that role is cleared for. Results come back with citations: document, title, heading, source and date. It is pure Python 3.10+ with no dependencies outside the standard library.

## Quickstart

From this directory, index the fictional example company and ask it a few questions:

```sh
python3 -m cazmind index examples/riverbend -o /tmp/rb.json --config examples/riverbend/cazmind.json

python3 -m cazmind ask "repair turnaround times" --index /tmp/rb.json --config examples/riverbend/cazmind.json --role staff
python3 -m cazmind ask "what are the salary bands?" --index /tmp/rb.json --config examples/riverbend/cazmind.json --role guest
python3 -m cazmind ask "salary bands for mechanics" --index /tmp/rb.json --config examples/riverbend/cazmind.json --role admin --json
```

The guest is refused on salaries. The admin gets the confidential salary document.

Run the tests with:

```sh
python3 -m unittest discover -s tests -v
```

From Python:

```python
from cazmind import config
from cazmind.access import answer
from cazmind.corpus import load_corpus
from cazmind.search import Index

cfg = config.load("examples/riverbend/cazmind.json")
index = Index.build(load_corpus("examples/riverbend", cfg["default_sensitivity"], cfg["max_chars"]))
print(answer(index, cfg, "staff", "how long does a tune-up take?", k=3))
```

## Corpus format

Any folder of `*.md` files, walked recursively. Files and folders whose names start with `.` or `_` are skipped, so `_drafts/` stays out of the index.

A file may start with simple frontmatter:

```markdown
---
title: Repair Intake SOP
sensitivity: internal
source: https://wiki.example.com/repair-intake
updated: 2026-09-02
tags: repairs, sop
---
# Repair Intake SOP
...
```

- `title`: defaults to the first `# ` heading, then the file name.
- `sensitivity`: defaults to `default_sensitivity` in the config, which defaults to `internal`.
- `source`, `updated`: free text, shown with results.
- `tags`: `a, b` or `[a, b]`.

The body is split into passages at `#`, `##` and `###` headings. A section longer than `max_chars` (default 1500) is split again on blank lines. Search is Okapi BM25 (k1 1.2, b 0.75) over title, heading and text, with the title counted twice.

## Permission model

Sensitivity levels are ordered. The defaults are `public`, `internal`, `restricted`, `confidential`. Each role maps to the highest level it may see:

| role  | sees up to   |
|-------|--------------|
| guest | public       |
| staff | internal     |
| lead  | restricted   |
| admin | confidential |

Two rules fail closed. A role the config does not know gets the lowest level only. A document with a sensitivity label the config does not know is treated as the highest level.

**Privacy property.** A passage a role cannot see never appears in its results, and it also never changes the ranking or the scores of the passages it can see. BM25 scores depend on corpus statistics (passage count, document frequencies, average length), so filtering results after a full search would leak: a pile of hidden documents about a topic would shift every visible score for that topic. The engine instead searches a sub-index built only from the passages the role may see, cached per visible set. The test suite checks that scores match an index built from the visible passages alone.

**Topic refusals.** The config can list rules like this:

```json
{
  "name": "compensation",
  "roles": ["guest", "staff"],
  "match_any": ["salary", "salaries", "wages"],
  "message": "Ask the owner directly."
}
```

If the asking role is listed and any phrase appears as a whole word in the question, the engine does not search at all and returns the message. Refusals are a courtesy layer for questions a role should take elsewhere. The sensitivity levels are the actual access control.

## Config (`cazmind.json`)

Keys: `org_name`, `levels`, `roles`, `default_sensitivity`, `max_chars`, `refusals`. Anything missing uses the default. Loading fails with a clear `ValueError` if a role or the default sensitivity names a level that is not in `levels`. The CLI treats a `--config` path that does not exist as a usage error, so a typo cannot silently drop your refusal rules.

## Session tokens

`cazmind.session` issues and verifies signed tokens for an app that sits in front of the engine:

```
base64url(json payload) + "." + base64url(HMAC-SHA256(secret, payload part))
```

The payload holds `sub` (email, lowercased), `role`, `exp` (unix seconds) and an optional `name`. `issue(secret, sub, role, ttl=12h, name=None)` makes one. `verify(secret, token)` returns the payload, or `None` for anything malformed, tampered, signed with another secret, or expired. It never raises.

`resolve_secret()` picks the signing secret: an explicit argument, else the `CAZMIND_SESSION_SECRET` environment variable. It must be at least 32 bytes. If neither is set and `CAZMIND_DEV=1`, you get a random secret for the life of the process (with a warning, and every session dies on restart). Otherwise it raises. There is no built-in fallback secret, on purpose: a default secret in source code is a secret everyone has.

## CLI

```
python3 -m cazmind index <corpus_dir> [-o index.json] [--config cazmind.json]
python3 -m cazmind ask "<question>" [--index index.json] [--config cazmind.json] [--role staff] [-k 5] [--json]
```

Exit code 0 on success, 2 on usage errors (bad arguments, missing files, invalid config).

## What it is not

There are no embeddings and no LLM calls. CazMind is the retrieval and governance layer: it decides what a given person is allowed to see and finds the best passages with citations. Put a language model on top of it if you want generated answers, and hand the model only what `answer()` returns. There is also no web server, user store, or login flow; the session module gives you the token piece only.

## Install

```sh
pip install git+https://github.com/phiunit/cazmind.git
cazmind --help
```

Or clone it and run `python3 -m cazmind` from the repo root. There's nothing else to install.

## Contributing and security

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md); commits need a DCO sign-off (`git commit -s`). Please report security issues privately, per [SECURITY.md](SECURITY.md). How this code was written is recorded in [PROVENANCE.md](PROVENANCE.md).

## Who runs this

The engine is free. If you'd rather not build and maintain a company brain yourself, [CazMind](https://cazmind.phiunit.com) does it for you: ingesting your docs, curating them, setting the permissions, and keeping the brain current.

## License

Apache-2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
