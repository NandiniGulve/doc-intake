"""Replays canned model outputs (valid / ambiguous / malformed) through the real engine."""
import glob
import json
import os
import unittest
from core.schema import new_session, get_value
from tests.helpers import Fixed, turn

DIR = os.path.join(os.path.dirname(__file__), "fixtures")


class FixtureTests(unittest.TestCase):
    def test_all_fixtures(self):
        files = sorted(glob.glob(os.path.join(DIR, "*.json")))
        self.assertGreaterEqual(len(files), 8)
        for path in files:
            with self.subTest(fixture=os.path.basename(path)):
                with open(path) as f:
                    fx = json.load(f)
                start = new_session()
                r = turn(start, "anything", Fixed(fx["raw"]))
                ex = fx["expect"]
                for p, v in ex.get("values", {}).items():
                    self.assertEqual(get_value(r["session"]["values"], p), v, p)
                for p, st in ex.get("status", {}).items():
                    self.assertEqual(r["session"]["status"][p], st, p)
                if ex.get("state_unchanged"):
                    self.assertEqual(r["session"], start)
                if "errors" in ex:
                    self.assertEqual(bool(r["errors"]), ex["errors"])
                if "reply_contains" in ex:
                    self.assertIn(ex["reply_contains"], r["reply"])


if __name__ == "__main__":
    unittest.main()
