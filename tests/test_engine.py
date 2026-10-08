import unittest
from core.schema import new_session, validate_updates, get_value
from core.engine import process_turn, parse_model_output, LLMError, FALLBACK, next_action
from core.document import render
from tests.helpers import turn, session_with, Fixed


class Tests(unittest.TestCase):
    def test_validation_rejects_bad_types_and_unknown_fields(self):
        clean, errs = validate_updates({"has_children": "yes", "foo": 1, "full_name": " Jane ", "executor": {"name": "Jo"}})
        self.assertEqual(clean, {"full_name": "Jane", "executor.name": "Jo"})
        self.assertEqual(len(errs), 2)

    def test_state_matches_brief_shape(self):
        v = new_session()["values"]
        self.assertEqual(v["executor"], {"name": None, "relationship": None})

    def test_multiple_fields_in_one_message(self):
        r = turn(new_session(), "My name is Jane Smith and I live at 1 High St, London.")
        v = r["session"]["values"]
        self.assertEqual((v["full_name"], v["home_address"]), ("Jane Smith", "1 High St, London"))

    def test_does_not_reask_captured_fields(self):
        r = turn(new_session(), "My name is Jane Smith")
        self.assertEqual(r["asking"], {"kind": "ask", "path": "home_address"})
        self.assertNotIn("full name", r["reply"])

    def test_executor_with_relationship(self):
        v = turn(new_session(), "My executor is my brother James Smith")["session"]["values"]
        self.assertEqual(v["executor"], {"name": "James Smith", "relationship": "brother"})

    # --- corrections and cross-turn contradictions
    def test_explicit_correction_overwrites_and_is_reported(self):
        s = session_with(full_name="Jane Smith")
        r = turn(s, "Actually my name is Jane Smythe")
        self.assertEqual(r["session"]["values"]["full_name"], "Jane Smythe")
        self.assertEqual(r["changes"][0]["old"], "Jane Smith")

    def test_unflagged_contradiction_asks_before_overwriting(self):
        s = session_with(full_name="Jane Smith")
        r = turn(s, "My name is Jane Smythe")
        self.assertEqual(r["session"]["values"]["full_name"], "Jane Smith")  # unchanged
        self.assertEqual(r["session"]["pending"], {"full_name": "Jane Smythe"})
        self.assertIn("Did you mean to change it to Jane Smythe", r["reply"])
        r2 = turn(r["session"], "yes")
        self.assertEqual(r2["session"]["values"]["full_name"], "Jane Smythe")
        self.assertEqual(r2["session"]["pending"], {})

    def test_pending_change_rejected(self):
        s = session_with(full_name="Jane Smith")
        s = turn(s, "My name is Jane Smythe")["session"]
        r = turn(s, "no")
        self.assertEqual(r["session"]["values"]["full_name"], "Jane Smith")
        self.assertEqual(r["session"]["pending"], {})

    # --- unconfirmed values
    def test_hedged_answer_is_unconfirmed_then_confirmed(self):
        r = turn(new_session(), "I think my executor is probably my brother James")
        s = r["session"]
        self.assertEqual(s["status"]["executor.name"], "unconfirmed")
        self.assertIn("is that right", r["reply"])
        self.assertIn("[UNCONFIRMED]", render(s))
        s = turn(s, "yes")["session"]
        self.assertEqual(s["status"]["executor.name"], "confirmed")

    def test_hedged_answer_rejected_resets_to_unknown(self):
        s = turn(new_session(), "my executor is probably James")["session"]
        r = turn(s, "no")
        self.assertIsNone(r["session"]["values"]["executor"]["name"])
        self.assertEqual(r["session"]["status"]["executor.name"], "unknown")

    # --- vague answers: clarify, then move on (no infinite loop)
    def test_vague_answer_gets_tailored_clarification_then_skips(self):
        s = session_with(full_name="J", home_address="X Street 1")
        r = turn(s, "not sure, maybe")
        self.assertIn("anywhere in the world", r["reply"])  # tailored follow-up, not the same question
        r = turn(r["session"], "dunno")
        self.assertIn("covers_worldwide_assets", r["session"]["skipped"])
        self.assertNotEqual(r["asking"]["path"], "covers_worldwide_assets")
        self.assertIsNone(r["session"]["values"]["covers_worldwide_assets"])

    def test_skipped_field_can_be_filled_later(self):
        s = session_with(full_name="J", home_address="X Street 1")
        s["skipped"] = ["covers_worldwide_assets"]
        r = turn(s, "It should cover everything worldwide")
        self.assertIs(r["session"]["values"]["covers_worldwide_assets"], True)
        self.assertEqual(r["session"]["skipped"], [])

    # --- children logic
    def test_no_children_skips_names_and_clears_them(self):
        s = session_with(has_children=True, children_names=["A"])
        r = turn(s, "Actually I have no children")
        self.assertEqual(r["session"]["values"]["children_names"], [])
        self.assertNotEqual((r["asking"] or {}).get("path"), "children_names")

    def test_changing_mind_to_children_asks_for_names(self):
        s = session_with(has_children=False, children_names=[])
        r = turn(s, "Actually my children are Tom and Ann")
        v = r["session"]["values"]
        self.assertIs(v["has_children"], True)
        self.assertEqual(v["children_names"], ["Tom", "Ann"])

    # --- model failures
    def test_malformed_output_keeps_state(self):
        s = session_with(full_name="Jane Smith")
        r = turn(s, "!malformed")
        self.assertEqual(r["session"], s)
        self.assertEqual(r["reply"], FALLBACK)

    def test_llm_exception_handled(self):
        class Boom:
            def extract(self, **kw): raise ConnectionError("down")
        r = turn(new_session(), "hi", Boom())
        self.assertEqual(r["reply"], FALLBACK)
        self.assertIn("unavailable", r["errors"][0])

    def test_retry_recovers_from_one_bad_response(self):
        class Flaky:
            n = 0
            def extract(self, **kw):
                Flaky.n += 1
                return "garbage" if Flaky.n == 1 else '{"updates": {"full_name": "Jane Smith"}}'
        r = turn(new_session(), "x", Flaky())
        self.assertEqual(r["session"]["values"]["full_name"], "Jane Smith")

    def test_invalid_confirmation_ignored(self):
        r = turn(new_session(), "x", Fixed('{"confirmations": {"full_name": true}}'))
        self.assertTrue(r["errors"])
        self.assertEqual(r["session"]["status"]["full_name"], "unknown")

    def test_parse_handles_fences_and_rejects_garbage(self):
        self.assertEqual(parse_model_output('```json\n{"updates": {}}\n```'), {"updates": {}})
        with self.assertRaises(LLMError):
            parse_model_output("[1,2]")

    # --- document
    def test_document_marks_unknowns_and_disclaimer(self):
        doc = render(new_session())
        self.assertIn("NOT LEGAL ADVICE", doc)
        self.assertIn("[NOT YET PROVIDED]", doc)

    def test_preview_matches_state_after_each_turn(self):
        s = turn(new_session(), "My name is Jane Smith")["session"]
        self.assertIn("Jane Smith", render(s))
        s = turn(s, "Actually my name is Jane Smythe")["session"]
        self.assertIn("Jane Smythe", render(s))
        self.assertNotIn("Jane Smith,", render(s))

    def test_full_conversation_completes(self):
        s = new_session()
        for m in ["Jane Smith", "1 High Street, London", "yes", "no", "My brother James", "none", "none"]:
            s = turn(s, m)["session"]
        self.assertIsNone(next_action(s))
        self.assertEqual(s["values"]["executor"]["relationship"], "brother")
        self.assertEqual(s["values"]["specific_gifts"], [])


if __name__ == "__main__":
    unittest.main()
