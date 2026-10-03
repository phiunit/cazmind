"""Okapi BM25 index over passages, with JSON save/load."""

import json
import math
import re
from collections import Counter

K1 = 1.2
B = 0.75
SNIPPET_CHARS = 240
FORMAT = "cazmind-index"

WORD_RE = re.compile(r"\w+")
STOPWORDS = frozenset(
    """
    an and are as at be but by can do does for from has have how if in into
    is it its no not of on or our so that the their them then there these
    they this to was we were what when where which who why will with you your
    """.split()
)


def tokenize(text):
    """Lowercase \\w+ tokens, minus 1-char tokens and stopwords. No stemming."""
    return [
        t for t in WORD_RE.findall(text.lower())
        if len(t) > 1 and t not in STOPWORDS
    ]


def _passage_tokens(p):
    # Title counted twice so title matches weigh more.
    return (
        tokenize(p.get("title", "")) * 2
        + tokenize(p.get("heading", ""))
        + tokenize(p.get("text", ""))
    )


def make_snippet(text, terms, width=SNIPPET_CHARS):
    """Up to about `width` chars of text around the first query-term hit."""
    flat = " ".join(text.split())
    start = hit = 0
    for match in WORD_RE.finditer(flat):
        if match.group().lower() in terms:
            hit = match.start()
            start = max(0, hit - width // 4)
            break
    if start > 0:
        space = flat.find(" ", start, hit)
        if space != -1:
            start = space + 1
    end = start + width
    if end < len(flat):
        space = flat.rfind(" ", start, end)
        if space > start:
            end = space
    return ("..." if start else "") + flat[start:end] + ("..." if end < len(flat) else "")


class Index:
    def __init__(self, passages):
        self.passages = list(passages)
        self._tf = []
        self._len = []
        self._df = Counter()
        for p in self.passages:
            tokens = _passage_tokens(p)
            tf = Counter(tokens)
            self._tf.append(tf)
            self._len.append(len(tokens))
            self._df.update(tf.keys())
        self.n = len(self.passages)
        self.avgdl = sum(self._len) / self.n if self.n else 0.0
        self._subindexes = {}

    @classmethod
    def build(cls, passages):
        return cls(passages)

    def save(self, path):
        # Stats are cheap to recompute, so only passages are stored.
        with open(path, "w", encoding="utf-8") as f:
            json.dump(
                {"format": FORMAT, "version": 1, "passages": self.passages},
                f, ensure_ascii=False, indent=1,
            )

    @classmethod
    def load(cls, path):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict) or data.get("format") != FORMAT:
            raise ValueError(f"{path}: not a cazmind index file")
        return cls(data["passages"])

    def search(self, query, k=5, allowed=None):
        """Top-k BM25 results, best first. Zero-score passages are excluded.

        With `allowed`, both the candidates and the corpus statistics come
        only from allowed passages: the search runs on a sub-index built
        from them, so hidden passages cannot affect visible scores.
        """
        if allowed is not None:
            keep = tuple(i for i, p in enumerate(self.passages) if allowed(p))
            if len(keep) < self.n:
                sub = self._subindexes.get(keep)
                if sub is None:
                    sub = Index([self.passages[i] for i in keep])
                    self._subindexes[keep] = sub
                return sub.search(query, k)

        terms = sorted(set(tokenize(query)))
        if not terms or not self.n:
            return []
        idf = {}
        for t in terms:
            df = self._df.get(t, 0)
            idf[t] = math.log(1 + (self.n - df + 0.5) / (df + 0.5))

        scored = []
        for i, tf in enumerate(self._tf):
            norm = K1 * (1 - B + B * self._len[i] / self.avgdl)
            score = 0.0
            for t in terms:
                f = tf.get(t, 0)
                if f:
                    score += idf[t] * f * (K1 + 1) / (f + norm)
            if score > 0:
                scored.append((score, i))
        scored.sort(key=lambda pair: (-pair[0], pair[1]))

        results = []
        for score, i in scored[:k]:
            p = self.passages[i]
            results.append({
                "score": score,
                "doc_id": p["doc_id"],
                "title": p.get("title", ""),
                "heading": p.get("heading", ""),
                "source": p.get("source", ""),
                "updated": p.get("updated", ""),
                "snippet": make_snippet(p.get("text", ""), set(terms)),
            })
        return results
