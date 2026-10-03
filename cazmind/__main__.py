"""Command line: python -m cazmind index ... | ask ..."""

import argparse
import json
import os
import sys

from . import __version__
from . import config as config_mod
from .access import answer
from .corpus import load_corpus
from .search import Index


def _index(args, cfg):
    passages = load_corpus(args.corpus_dir, cfg["default_sensitivity"], cfg["max_chars"])
    Index.build(passages).save(args.output)
    docs = len({p["doc_id"] for p in passages})
    print(f"Indexed {len(passages)} passages from {docs} documents -> {args.output}")
    return 0


def _ask(args, cfg):
    result = answer(Index.load(args.index), cfg, args.role, args.question, args.k)
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    elif result["refused"]:
        print(result["message"])
    elif not result["results"]:
        print("No results.")
    else:
        for n, r in enumerate(result["results"], 1):
            where = f"{r['title']} > {r['heading']}" if r["heading"] else r["title"]
            print(f"{n}. {where}  [{r['doc_id']}]  score {r['score']:.3f}")
            meta = [x for x in (r["source"] and f"source: {r['source']}",
                                r["updated"] and f"updated: {r['updated']}") if x]
            if meta:
                print("   " + "  ".join(meta))
            print(f"   {r['snippet']}")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="cazmind", description="Permission-aware search over a markdown corpus."
    )
    parser.add_argument("--version", action="version", version=f"cazmind {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_index = sub.add_parser("index", help="build an index from a corpus folder")
    p_index.add_argument("corpus_dir")
    p_index.add_argument("-o", "--output", default="index.json")
    p_index.add_argument("--config")

    p_ask = sub.add_parser("ask", help="ask a question as a role")
    p_ask.add_argument("question")
    p_ask.add_argument("--index", default="index.json")
    p_ask.add_argument("--config")
    p_ask.add_argument("--role", default="staff")
    p_ask.add_argument("-k", type=int, default=5)
    p_ask.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)
    if args.command == "ask" and args.k < 1:
        parser.error("-k must be at least 1")
    # An explicit --config that does not exist is a usage error, so a typo
    # cannot silently drop the refusal rules.
    if args.config and not os.path.exists(args.config):
        parser.error(f"config file not found: {args.config}")
    try:
        cfg = config_mod.load(args.config)
        return _index(args, cfg) if args.command == "index" else _ask(args, cfg)
    except (OSError, ValueError) as exc:
        print(f"cazmind: error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
