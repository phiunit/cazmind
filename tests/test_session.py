import json
import os
import time
import unittest
from contextlib import redirect_stderr
from io import StringIO
from unittest import mock

from cazmind import session

SECRET = b"k" * 32
OTHER = b"o" * 32


def signed(payload, secret=SECRET):
    part = session._b64encode(json.dumps(payload).encode())
    return part + "." + session._b64encode(session._sign(secret, part))


class TokenTests(unittest.TestCase):
    def test_issue_verify(self):
        token = session.issue(SECRET, "  Pat@Example.com ", "staff", name="Pat")
        self.assertNotIn("=", token)
        payload = session.verify(SECRET, token)
        self.assertEqual(payload["sub"], "pat@example.com")
        self.assertEqual(payload["role"], "staff")
        self.assertEqual(payload["name"], "Pat")
        self.assertAlmostEqual(payload["exp"], time.time() + 12 * 3600, delta=5)

    def test_name_optional(self):
        payload = session.verify(SECRET, session.issue(SECRET, "a@example.com", "guest"))
        self.assertNotIn("name", payload)

    def test_str_secret_works(self):
        s = "s" * 32
        self.assertIsNotNone(session.verify(s, session.issue(s, "a@example.com", "guest")))

    def test_tampered_payload(self):
        token = session.issue(SECRET, "a@example.com", "guest")
        payload_part, sig = token.split(".")
        forged = session._b64encode(json.dumps(
            {"sub": "a@example.com", "role": "admin", "exp": int(time.time()) + 999}).encode())
        self.assertIsNone(session.verify(SECRET, forged + "." + sig))
        flipped = sig[:-1] + ("A" if sig[-1] != "A" else "B")
        self.assertIsNone(session.verify(SECRET, payload_part + "." + flipped))

    def test_wrong_secret(self):
        token = session.issue(SECRET, "a@example.com", "staff")
        self.assertIsNone(session.verify(OTHER, token))

    def test_expired(self):
        self.assertIsNone(session.verify(SECRET, session.issue(SECRET, "a@example.com", "staff", ttl=-1)))
        self.assertIsNone(session.verify(SECRET, session.issue(SECRET, "a@example.com", "staff", ttl=0)))

    def test_missing_or_bad_exp(self):
        self.assertIsNone(session.verify(SECRET, signed({"sub": "a@example.com", "role": "staff"})))
        self.assertIsNone(session.verify(SECRET, signed({"sub": "a", "role": "s", "exp": "9999999999"})))
        self.assertIsNone(session.verify(SECRET, signed({"sub": "a", "role": "s", "exp": True})))
        self.assertIsNotNone(session.verify(SECRET, signed({"sub": "a", "role": "s", "exp": int(time.time()) + 60})))

    def test_malformed(self):
        good = session.issue(SECRET, "a@example.com", "staff")
        bad_inputs = [None, 123, b"bytes", "", ".", "abc", "a.b.c", good + ".x",
                      "!!!.???", "é.é", good.replace(".", ".=", 1), signed([1, 2, 3]),
                      signed("string"), "e30." + good.split(".")[1]]
        for bad in bad_inputs:
            self.assertIsNone(session.verify(SECRET, bad), repr(bad))


class SecretTests(unittest.TestCase):
    def setUp(self):
        session._dev_secret = None
        self.env = mock.patch.dict(os.environ, {}, clear=False)
        self.env.start()
        os.environ.pop(session.ENV_SECRET, None)
        os.environ.pop(session.ENV_DEV, None)

    def tearDown(self):
        self.env.stop()
        session._dev_secret = None

    def test_nothing_set_raises(self):
        with self.assertRaises(RuntimeError):
            session.resolve_secret()

    def test_dev_mode_random_and_warns_once(self):
        os.environ[session.ENV_DEV] = "1"
        err = StringIO()
        with redirect_stderr(err):
            a = session.resolve_secret()
            b = session.resolve_secret()
        self.assertEqual(len(a), 32)
        self.assertEqual(a, b)  # stable within the process
        self.assertEqual(err.getvalue().count("warning"), 1)
        session._dev_secret = None
        with redirect_stderr(StringIO()):
            self.assertNotEqual(session.resolve_secret(), a)

    def test_dev_flag_must_be_exactly_1(self):
        os.environ[session.ENV_DEV] = "true"
        with self.assertRaises(RuntimeError):
            session.resolve_secret()

    def test_explicit_and_env(self):
        self.assertEqual(session.resolve_secret("x" * 32), b"x" * 32)
        os.environ[session.ENV_SECRET] = "y" * 40
        self.assertEqual(session.resolve_secret(), b"y" * 40)
        self.assertEqual(session.resolve_secret(b"z" * 32), b"z" * 32)

    def test_short_secrets_rejected(self):
        with self.assertRaises(ValueError):
            session.resolve_secret("short")
        with self.assertRaises(ValueError):
            session.resolve_secret("")
        os.environ[session.ENV_SECRET] = "x" * 31
        with self.assertRaises(ValueError):
            session.resolve_secret()
        os.environ[session.ENV_DEV] = "1"  # dev mode never rescues a bad secret
        with self.assertRaises(ValueError):
            session.resolve_secret()


if __name__ == "__main__":
    unittest.main()
