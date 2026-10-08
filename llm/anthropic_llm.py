"""Real provider via plain HTTPS (no SDK needed). Same interface as MockLLM.extract."""
import json
import os
import urllib.request
from core.schema import FIELDS

SYSTEM = f"""You extract structured data from a user's messages for a fictional Personal Wishes Document.
Return ONLY a JSON object (no prose, no markdown):
{{"updates": {{}}, "tentative": {{}}, "confirmations": {{}}, "correction": false, "ack": "short friendly acknowledgement"}}
- Field paths and types: {json.dumps({k: v[0] for k, v in FIELDS.items()})}. Nest executor as {{"executor": {{"name": "..", "relationship": ".."}}}}.
  str_list = list of strings; an empty list means the user explicitly said 'none'.
- updates: values the user stated clearly in their LATEST message. tentative: values they hedged ("probably", "I think").
- confirmations: {{"path": true/false}} when the user answers yes/no to the question in `question_just_asked`.
- correction: true only if the user is explicitly changing something said earlier ("actually...", "change it to...").
- Never guess or invent. If an answer is ambiguous or off-topic, return empty objects."""


class AnthropicLLM:
    def __init__(self, api_key=None, model=None):
        self.key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.model = model or os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5-5")
        if not self.key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set")

    def extract(self, *, session, asking, message, history):
        user = json.dumps({"current_values": session["values"], "status": session["status"],
                           "pending_changes": session["pending"], "question_just_asked": asking,
                           "user_message": message})
        body = json.dumps({"model": self.model, "max_tokens": 600, "system": SYSTEM,
                           "messages": [{"role": "user", "content": user}]}).encode()
        req = urllib.request.Request("https://api.anthropic.com/v1/messages", body, {
            "x-api-key": self.key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)["content"][0]["text"]
