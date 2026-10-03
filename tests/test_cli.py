import json
import os
import subprocess
import sys
import tempfile
import unittest

from helpers import ENGINE, RIVERBEND, RIVERBEND_CONFIG


def run(*args):
    return subprocess.run([sys.executable, "-m", "cazmind", *args], cwd=ENGINE,
                          capture_output=True, text=True, timeout=60)


class CliTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.index = os.path.join(cls.tmp.name, "rb.json")
        proc = run("index", RIVERBEND, "-o", cls.index, "--config", RIVERBEND_CONFIG)
        cls.index_proc = proc

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def ask(self, question, *extra):
        return run("ask", question, "--index", self.index, "--config", RIVERBEND_CONFIG, *extra)

    def test_index(self):
        self.assertEqual(self.index_proc.returncode, 0, self.index_proc.stderr)
        self.assertIn("from 7 documents", self.index_proc.stdout)
        self.assertTrue(os.path.exists(self.index))

    def test_ask_text(self):
        proc = self.ask("repair turnaround times", "--role", "staff", "-k", "2")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue(proc.stdout.startswith("1. Repair Intake SOP > Turnaround times"), proc.stdout)

    def test_guest_refused(self):
        proc = self.ask("what are the salary bands?", "--role", "guest")
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout.strip(), "Ask the owner directly.")

    def test_admin_json(self):
        proc = self.ask("salary bands for mechanics", "--role", "admin", "--json")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(proc.stdout)
        self.assertFalse(data["refused"])
        self.assertEqual(data["results"][0]["doc_id"], "salary-bands.md")

    def test_no_results(self):
        proc = self.ask("zzzqqq", "--role", "admin")
        self.assertEqual(proc.stdout.strip(), "No results.")

    def test_usage_errors_exit_2(self):
        self.assertEqual(run().returncode, 2)
        self.assertEqual(run("ask").returncode, 2)
        self.assertEqual(self.ask("bike", "-k", "0").returncode, 2)
        self.assertEqual(run("ask", "bike", "--index", os.path.join(self.tmp.name, "nope.json")).returncode, 2)
        self.assertEqual(run("index", os.path.join(self.tmp.name, "no-dir"), "-o",
                             os.path.join(self.tmp.name, "x.json")).returncode, 2)
        self.assertEqual(self.ask("bike", "--config", os.path.join(self.tmp.name, "missing.json")).returncode, 2)


if __name__ == "__main__":
    unittest.main()
