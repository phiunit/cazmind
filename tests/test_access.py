import unittest

from cazmind import config
from cazmind.access import allowed_for, answer, can_see, check_question
from cazmind.corpus import load_corpus
from cazmind.search import Index

from helpers import RIVERBEND, RIVERBEND_CONFIG


def passage(sensitivity):
    return {"doc_id": "x.md", "title": "t", "heading": "", "text": "x", "sensitivity": sensitivity}


class VisibilityTests(unittest.TestCase):
    def test_role_ladder(self):
        expected = {
            "guest": ["public"],
            "staff": ["public", "internal"],
            "lead": ["public", "internal", "restricted"],
            "admin": ["public", "internal", "restricted", "confidential"],
        }
        for role, ok in expected.items():
            for level in config.DEFAULT_LEVELS:
                self.assertEqual(can_see(role, passage(level)), level in ok, (role, level))

    def test_unknown_sensitivity_fails_closed(self):
        for role in ["guest", "staff", "lead"]:
            self.assertFalse(can_see(role, passage("top-secret")))
            self.assertFalse(can_see(role, passage("")))
        self.assertTrue(can_see("admin", passage("top-secret")))

    def test_unknown_role_gets_public_only(self):
        self.assertTrue(can_see("intern", passage("public")))
        self.assertFalse(can_see("intern", passage("internal")))
        self.assertFalse(can_see(None, passage("internal")))

    def test_predicate_matches_can_see(self):
        pred = allowed_for("lead")
        for level in config.DEFAULT_LEVELS + ["weird"]:
            self.assertEqual(pred(passage(level)), can_see("lead", passage(level)))

    def test_custom_levels(self):
        cfg = config.validate(dict(config.defaults(), levels=["open", "closed"],
                                   roles={"member": "closed"}, default_sensitivity="open"))
        self.assertTrue(can_see("member", passage("closed"), cfg))
        self.assertTrue(can_see("stranger", passage("open"), cfg))
        self.assertFalse(can_see("stranger", passage("closed"), cfg))


class RefusalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = config.load(RIVERBEND_CONFIG)
        cls.index = Index.build(load_corpus(RIVERBEND, cls.cfg["default_sensitivity"]))

    def test_fires_for_listed_roles_only(self):
        q = "What are the salary bands for mechanics?"
        self.assertIsNotNone(check_question("guest", q, self.cfg))
        self.assertIsNotNone(check_question("STAFF", q, self.cfg))
        self.assertIsNone(check_question("lead", q, self.cfg))
        self.assertIsNone(check_question("admin", q, self.cfg))

    def test_whole_word_match(self):
        self.assertIsNone(check_question("guest", "Do you sell salaryman figurines?", self.cfg))
        self.assertIsNotNone(check_question("guest", "salaries?", self.cfg))
        self.assertIsNone(check_question("guest", "What are shop hours?", self.cfg))

    def test_answer_refused_does_not_search(self):
        res = answer(self.index, self.cfg, "guest", "salary bands", 5)
        self.assertEqual(res, {"refused": True, "message": "Ask the owner directly.", "results": []})

    def test_answer_admin_sees_confidential(self):
        res = answer(self.index, self.cfg, "admin", "salary bands for mechanics", 5)
        self.assertFalse(res["refused"])
        self.assertEqual(res["results"][0]["doc_id"], "salary-bands.md")

    def test_answer_lead_not_refused_but_filtered(self):
        res = answer(self.index, self.cfg, "lead", "salary bands for mechanics", 10)
        self.assertFalse(res["refused"])
        self.assertNotIn("salary-bands.md", {r["doc_id"] for r in res["results"]})

    def test_answer_guest_sees_public_only(self):
        res = answer(self.index, self.cfg, "guest", "repair bike parts returns", 50)
        self.assertTrue(res["results"])
        self.assertEqual({r["doc_id"] for r in res["results"]} - {"returns-policy.md", "onboarding.md"}, set())


if __name__ == "__main__":
    unittest.main()
