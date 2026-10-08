"""API tests; skipped automatically unless fastapi + httpx are installed (pip install -r requirements-dev.txt)."""
import unittest
try:
    from fastapi.testclient import TestClient
    import main
    HAVE = True
except Exception:  # pragma: no cover
    HAVE = False


@unittest.skipUnless(HAVE, "fastapi/httpx not installed")
class ApiTests(unittest.TestCase):
    def setUp(self):
        self.c = TestClient(main.app)
        self.sid = self.c.post("/api/sessions").json()["session_id"]

    def test_contract_shape(self):
        d = self.c.get(f"/api/sessions/{self.sid}").json()
        for k in ("state", "status", "pending_changes", "skipped", "document", "history", "llm_mode"):
            self.assertIn(k, d)
        self.assertIn("name", d["state"]["executor"])

    def test_message_updates_state_and_document(self):
        d = self.c.post(f"/api/sessions/{self.sid}/messages", json={"message": "My name is Jane Smith"}).json()
        self.assertEqual(d["state"]["full_name"], "Jane Smith")
        self.assertIn("Jane Smith", d["document"])
        self.assertEqual(d["history"][-1]["role"], "assistant")

    def test_validation_and_404(self):
        self.assertEqual(self.c.post(f"/api/sessions/{self.sid}/messages", json={"message": ""}).status_code, 422)
        self.assertEqual(self.c.get("/api/sessions/nope").status_code, 404)

    def test_malformed_model_output_is_graceful(self):
        d = self.c.post(f"/api/sessions/{self.sid}/messages", json={"message": "!malformed"}).json()
        self.assertTrue(d["errors"])


if __name__ == "__main__":
    unittest.main()
