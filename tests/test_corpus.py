import os
import tempfile
import unittest

from cazmind.corpus import chunk, load_corpus, parse_document, parse_frontmatter, parse_tags


class FrontmatterTests(unittest.TestCase):
    def test_parses_fields(self):
        meta, body = parse_frontmatter(
            "---\ntitle: Hello\nsensitivity: Restricted\nsource: \"https://example.com/x\"\n---\nBody"
        )
        self.assertEqual(meta["title"], "Hello")
        self.assertEqual(meta["sensitivity"], "Restricted")
        self.assertEqual(meta["source"], "https://example.com/x")
        self.assertEqual(body, "Body")

    def test_missing_frontmatter(self):
        meta, body = parse_frontmatter("# Title\n\nText")
        self.assertEqual(meta, {})
        self.assertEqual(body, "# Title\n\nText")

    def test_unclosed_frontmatter_is_body(self):
        meta, body = parse_frontmatter("---\ntitle: x\nno close")
        self.assertEqual(meta, {})

    def test_tags_forms(self):
        self.assertEqual(parse_tags("a, b ,c"), ["a", "b", "c"])
        self.assertEqual(parse_tags("[a, 'b']"), ["a", "b"])
        self.assertEqual(parse_tags(""), [])

    def test_defaults_without_frontmatter(self):
        ps = parse_document("# My Doc\n\nHello there.", "dir/my-doc.md", "internal")
        self.assertEqual(len(ps), 1)
        p = ps[0]
        self.assertEqual(p["title"], "My Doc")
        self.assertEqual(p["sensitivity"], "internal")
        self.assertEqual(p["doc_id"], "dir/my-doc.md")
        self.assertEqual(p["source"], "")
        self.assertEqual(p["tags"], [])

    def test_title_falls_back_to_stem(self):
        ps = parse_document("Just text.", "notes/plain-file.md")
        self.assertEqual(ps[0]["title"], "plain-file")

    def test_frontmatter_title_and_sensitivity_win(self):
        text = "---\ntitle: FM Title\nsensitivity: CONFIDENTIAL\ntags: [x, y]\n---\n# H1\n\nBody"
        p = parse_document(text, "a.md")[0]
        self.assertEqual(p["title"], "FM Title")
        self.assertEqual(p["sensitivity"], "confidential")
        self.assertEqual(p["tags"], ["x", "y"])


class SplitTests(unittest.TestCase):
    def test_heading_split(self):
        text = "Intro line.\n# Top\nTop text.\n## Sub\nSub text.\n### Deeper\nDeep text.\n#### Not split\nStill deep.\n## Empty\n\n"
        ps = parse_document(text, "a.md")
        self.assertEqual([p["heading"] for p in ps], ["", "Top", "Sub", "Deeper"])
        self.assertIn("#### Not split", ps[3]["text"])
        self.assertEqual(ps[0]["text"], "Intro line.")

    def test_code_fence_hash_is_not_heading(self):
        text = "## Setup\n```\n# a shell comment\n```\nAfter."
        ps = parse_document(text, "a.md")
        self.assertEqual(len(ps), 1)
        self.assertIn("# a shell comment", ps[0]["text"])

    def test_long_section_chunks_on_paragraphs(self):
        paras = [("word " * 40).strip() for _ in range(10)]  # ~199 chars each
        text = "## Long\n" + "\n\n".join(paras)
        ps = parse_document(text, "a.md", max_chars=500)
        self.assertGreater(len(ps), 1)
        for p in ps:
            self.assertLessEqual(len(p["text"]), 500)
            self.assertEqual(p["heading"], "Long")
        joined = " ".join(" ".join(p["text"].split()) for p in ps)
        self.assertEqual(joined, " ".join(" ".join(paras).split()))

    def test_oversized_paragraph_stands_alone(self):
        big = "x" * 900
        chunks = chunk("small\n\n" + big + "\n\nsmall again", 500)
        self.assertEqual(chunks, ["small", big, "small again"])


class LoadCorpusTests(unittest.TestCase):
    def test_walk_skips_dot_and_underscore(self):
        with tempfile.TemporaryDirectory() as root:
            os.makedirs(os.path.join(root, "sub"))
            os.makedirs(os.path.join(root, "_drafts"))
            os.makedirs(os.path.join(root, ".hidden"))
            files = {
                "a.md": "# A\n\nalpha",
                "sub/b.md": "# B\n\nbeta",
                "_skip.md": "# S\n\nskip",
                ".skip.md": "# S\n\nskip",
                "_drafts/c.md": "# C\n\nskip",
                ".hidden/d.md": "# D\n\nskip",
                "notes.txt": "skip",
                "empty.md": "---\ntitle: E\n---\n\n   \n",
            }
            for name, body in files.items():
                with open(os.path.join(root, name), "w", encoding="utf-8") as f:
                    f.write(body)
            ps = load_corpus(root)
            self.assertEqual(sorted({p["doc_id"] for p in ps}), ["a.md", "sub/b.md"])

    def test_missing_root_raises(self):
        with self.assertRaises(NotADirectoryError):
            load_corpus("/nonexistent/cazmind/corpus")


if __name__ == "__main__":
    unittest.main()
