import copy
from core.schema import new_session, set_value
from core.engine import process_turn
from llm.mock import MockLLM


def session_with(**paths):
    """Build a session with confirmed values, e.g. session_with(full_name="Jane")."""
    s = new_session()
    for p, v in paths.items():
        p = p.replace("__", ".")
        set_value(s["values"], p, v)
        s["status"][p] = "confirmed"
    return s


def turn(session, msg, llm=None):
    return process_turn(session, [], msg, llm or MockLLM())


class Fixed:
    """Fixture LLM: always returns a canned raw model output."""
    def __init__(self, raw): self.raw = raw
    def extract(self, **kw): return self.raw
