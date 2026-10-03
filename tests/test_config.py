import json
import os
import tempfile
import unittest

from cazmind import config

from helpers import RIVERBEND_CONFIG


def write(tmp, data):
    path = os.path.join(tmp, "cazmind.json")
    with open(path, "w", encoding="utf-8") as f:
        f.write(data if isinstance(data, str) else json.dumps(data))
    return path


class ConfigTests(unittest.TestCase):
    def test_defaults_when_missing(self):
        self.assertEqual(config.load(), config.defaults())
        self.assertEqual(config.load("/nonexistent/cazmind.json"), config.defaults())

    def test_example_config(self):
        cfg = config.load(RIVERBEND_CONFIG)
        self.assertEqual(cfg["org_name"], "Riverbend Bike Co")
        self.assertEqual(cfg["roles"]["guest"], "public")
        self.assertEqual(len(cfg["refusals"]), 1)

    def test_override_and_normalize(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = config.load(write(tmp, {
                "levels": ["Open", "Team", "Board"],
                "roles": {"Member": "team", "director": "BOARD"},
                "default_sensitivity": "Team",
                "max_chars": 800,
            }))
        self.assertEqual(cfg["levels"], ["open", "team", "board"])
        self.assertEqual(cfg["roles"], {"member": "team", "director": "board"})
        self.assertEqual(cfg["default_sensitivity"], "team")
        self.assertEqual(cfg["max_chars"], 800)

    def test_role_level_must_exist(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "role 'staff'"):
                config.load(write(tmp, {"roles": {"staff": "secret"}}))

    def test_default_sensitivity_must_exist(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "default_sensitivity"):
                config.load(write(tmp, {"default_sensitivity": "private"}))

    def test_changing_levels_revalidates_default_roles(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                config.load(write(tmp, {"levels": ["a", "b"]}))

    def test_bad_shapes(self):
        with tempfile.TemporaryDirectory() as tmp:
            for bad in ['[1, 2]', {"levels": []}, {"max_chars": 0},
                        {"refusals": {}}, {"roles": ["guest"]}, "{not json"]:
                with self.assertRaises(ValueError, msg=repr(bad)):
                    config.load(write(tmp, bad))


if __name__ == "__main__":
    unittest.main()
