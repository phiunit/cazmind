import os
import tempfile
import unittest

from cazmind import config
from cazmind.access import allowed_for, can_see
from cazmind.corpus import load_corpus
from cazmind.search import Index, make_snippet, tokenize

from helpers import RIVERBEND, RIVERBEND_CONFIG


def riverbend():
    cfg = config.load(RIVERBEND_CONFIG)
    return cfg, load_corpus(RIVERBEND, cfg["default_sensitivity"], cfg["max_chars"])


class TokenizeTests(unittest.TestCase):
    def test_tokenize(self):
        self.assertEqual(tokenize("The Bike's tune-up: a 2x B"), ["bike", "tune", "up", "2x"])


class RankingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg, cls.passages = riverbend()
        cls.index = Index.build(cls.passages)

    def test_relevant_passage_first(self):
        cases = {
            "how long is the turnaround for a tune-up": ("sops/repair-intake.md", "Turnaround times"),
            "can I return installed parts": ("returns-policy.md", "Parts and accessories"),
            "who supplies our tires and tubes": ("vendors.md", "Parts distributors"),
            "labor rate per hour": ("pricing-margins.md", "Labor pricing"),
        }
        for query, (doc_id, heading) in cases.items():
            top = self.index.search(query, k=1)[0]
            self.assertEqual((top["doc_id"], top["heading"]), (doc_id, heading), query)

    def test_result_shape_and_order(self):
        results = self.index.search("repair intake", k=5)
        self.assertTrue(results)
        self.assertEqual(
            set(results[0]),
            {"score", "doc_id", "title", "heading", "source", "updated", "snippet"},
        )
        scores = [r["score"] for r in results]
        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertTrue(all(s > 0 for s in scores))

    def test_no_hits_and_stopword_query(self):
        self.assertEqual(self.index.search("zzzqqq"), [])
        self.assertEqual(self.index.search("the and of"), [])

    def test_k_limits(self):
        self.assertLessEqual(len(self.index.search("bike", k=2)), 2)

    def test_save_load_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "index.json")
            self.index.save(path)
            loaded = Index.load(path)
        self.assertEqual(loaded.passages, self.index.passages)
        for q in ["repair intake", "salary bands", "returns within 30 days", "tires"]:
            self.assertEqual(loaded.search(q, k=10), self.index.search(q, k=10))
            pred = allowed_for("staff", self.cfg)
            self.assertEqual(loaded.search(q, k=10, allowed=pred),
                             self.index.search(q, k=10, allowed=pred))

    def test_load_rejects_other_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "x.json")
            with open(path, "w") as f:
                f.write('{"hello": 1}')
            with self.assertRaises(ValueError):
                Index.load(path)


class PrivacyTests(unittest.TestCase):
    """Hidden passages never appear and never change visible scores."""

    QUERIES = [
        "salary bands for mechanics",
        "bench lead",
        "tune-up price and labor",
        "repair intake rack",
        "floor lead discount",
        "bike",
    ]

    def setUp(self):
        self.cfg, self.passages = riverbend()

    def check_role(self, role, passages):
        full = Index.build(passages)
        visible = [p for p in passages if can_see(role, p, self.cfg)]
        hidden_ids = {p["doc_id"] for p in passages if not can_see(role, p, self.cfg)}
        self.assertTrue(hidden_ids, "test needs at least one hidden doc")
        only_visible = Index.build(visible)
        pred = allowed_for(role, self.cfg)
        for q in self.QUERIES:
            got = full.search(q, k=100, allowed=pred)
            self.assertFalse({r["doc_id"] for r in got} & hidden_ids, (role, q))
            self.assertEqual(got, only_visible.search(q, k=100), (role, q))

    def test_privacy_on_example_corpus(self):
        for role in ["guest", "staff", "lead", "nobody"]:
            self.check_role(role, self.passages)

    def test_hidden_flood_does_not_shift_scores(self):
        # A pile of confidential passages stuffed with query words must not
        # move a single visible score.
        flood = [
            dict(doc_id=f"secret/{i}.md", title="Bench lead tune-up bike",
                 heading="", text="bench lead bike tune-up labor price " * 5,
                 sensitivity="confidential", source="", updated="", tags=[])
            for i in range(20)
        ]
        self.check_role("staff", self.passages + flood)

    def test_subindex_cached_per_visible_set(self):
        index = Index.build(self.passages)
        index.search("bike", allowed=allowed_for("staff", self.cfg))
        index.search("tires", allowed=allowed_for("staff", self.cfg))
        index.search("bike", allowed=allowed_for("guest", self.cfg))
        self.assertEqual(len(index._subindexes), 2)


class SnippetTests(unittest.TestCase):
    def test_snippet_centers_on_hit(self):
        text = "filler " * 100 + "derailleur hanger alignment " + "more " * 100
        snip = make_snippet(text, {"derailleur"})
        self.assertIn("derailleur", snip)
        self.assertTrue(snip.startswith("...") and snip.endswith("..."))
        self.assertLessEqual(len(snip), 240 + 6)

    def test_short_text_whole(self):
        self.assertEqual(make_snippet("Short  text\nhere.", {"zzz"}), "Short text here.")


if __name__ == "__main__":
    unittest.main()
