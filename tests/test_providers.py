import io
import json
import os
import unittest
from unittest.mock import patch, MagicMock
from llm.factory import get_llm
from llm.anthropic_llm import AnthropicLLM
from llm.mock import MockLLM
from core.schema import new_session
from tests.helpers import turn


class ProviderTests(unittest.TestCase):
    def test_missing_key_falls_back_to_mock_with_warning(self):
        with patch.dict(os.environ, {"LLM_PROVIDER": "anthropic"}, clear=True):
            llm, mode, warn = get_llm()
        self.assertIsInstance(llm, MockLLM)
        self.assertEqual(mode, "mock")
        self.assertIn("ANTHROPIC_API_KEY", warn)

    def test_default_is_mock_without_warning(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(get_llm()[1:], ("mock", None))

    def test_anthropic_request_and_response_contract(self):
        body = {"content": [{"type": "text", "text": '{"updates": {"full_name": "Jane Smith"}}'}]}
        resp = MagicMock()
        resp.read.return_value = json.dumps(body).encode()
        resp.__enter__.return_value = resp
        with patch("urllib.request.urlopen", return_value=resp) as uo:
            llm = AnthropicLLM(api_key="test-key", model="m")
            r = turn(new_session(), "I'm Jane Smith", llm)
        req = uo.call_args[0][0]
        self.assertEqual(req.get_header("X-api-key"), "test-key")
        sent = json.loads(req.data)
        self.assertEqual(sent["model"], "m")
        self.assertIn("full_name", sent["system"])
        self.assertEqual(r["session"]["values"]["full_name"], "Jane Smith")

    def test_provider_http_error_is_graceful(self):
        with patch("urllib.request.urlopen", side_effect=OSError("boom")):
            r = turn(new_session(), "hi", AnthropicLLM(api_key="k"))
        self.assertIn("trouble", r["reply"])


if __name__ == "__main__":
    unittest.main()
