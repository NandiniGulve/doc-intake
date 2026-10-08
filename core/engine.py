"""Application logic. The LLM only *extracts*; this module validates, applies and decides what to ask.

Model contract (JSON):
  {"updates": {...explicit values...}, "tentative": {...hedged values...},
   "confirmations": {"path": true|false}, "correction": bool, "ack": "text"}
"""
import copy
import json
import re
from .schema import (FIELDS, ORDER, label, get_value, set_value, applicable,
                     validate_updates, validate_confirmations)

FALLBACK = "Sorry, I had trouble processing that. Could you rephrase it?"
MAX_ATTEMPTS = 2  # failed tries on one question before we move on


class LLMError(Exception):
    pass


def parse_model_output(raw) -> dict:
    text = re.sub(r"^```(?:json)?|```$", "", (raw or "").strip() if isinstance(raw, str) else "", flags=re.M).strip()
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError) as e:
        raise LLMError(f"malformed JSON: {e}")
    if not isinstance(data, dict):
        raise LLMError("response must be a JSON object")
    return data


def fmt(v) -> str:
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, list):
        return ", ".join(v) or "none"
    return str(v)


def next_action(s: dict):
    if s["pending"]:
        return {"kind": "resolve_pending", "path": next(iter(s["pending"]))}
    for p in ORDER:
        if applicable(s["values"], p) and s["status"][p] == "unconfirmed":
            return {"kind": "confirm", "path": p}
    for p in ORDER:
        if applicable(s["values"], p) and s["status"][p] == "unknown" and p not in s["skipped"]:
            return {"kind": "ask", "path": p}
    return None


def prompt(s: dict, a) -> str:
    if a is None:
        if s["skipped"]:
            return ("That's everything except: " + ", ".join(label(p) for p in s["skipped"]) +
                    ". Tell me any of those whenever you like, or review the draft.")
        return "That's everything! Review the draft on the right, or tell me anything to correct."
    p, v = a["path"], s["values"]
    if a["kind"] == "resolve_pending":
        return (f"Earlier you told me your {label(p)} was {fmt(get_value(v, p))}. "
                f"Did you mean to change it to {fmt(s['pending'][p])}? (yes/no)")
    if a["kind"] == "confirm":
        return f"Just to check: your {label(p)} is {fmt(get_value(v, p))}, is that right? (yes/no)"
    return FIELDS[p][2] if s["attempts"].get(p) else FIELDS[p][1]


def _set(s, path, val, status, changes):
    old = get_value(s["values"], path)
    set_value(s["values"], path, val)
    s["status"][path] = status
    s["attempts"].pop(path, None)
    if path in s["skipped"]:
        s["skipped"].remove(path)
    if old != val:
        changes.append({"field": path, "old": old, "new": val})


def _call_llm(s, asked, message, history, llm):
    last = None
    for _ in range(2):  # one retry on malformed output
        try:
            return parse_model_output(llm.extract(session=s, asking=asked, message=message, history=history)), None
        except LLMError as e:
            last = str(e)
        except Exception as e:  # network / config errors: don't retry
            return None, f"llm unavailable: {e}"
    return None, last


def process_turn(session: dict, history: list, message: str, llm) -> dict:
    s = copy.deepcopy(session)
    asked = next_action(s)
    data, err = _call_llm(s, asked, message, history, llm)
    if data is None:
        return {"session": session, "changes": [], "errors": [err], "reply": FALLBACK, "asking": asked}

    updates, e1 = validate_updates(data.get("updates", {}))
    tentative, e2 = validate_updates(data.get("tentative", {}))
    conf, e3 = validate_confirmations(data.get("confirmations", {}), s)
    errors = e1 + e2 + e3
    correction = data.get("correction") is True
    changes, notes, progress = [], [], False

    # contradictory data inside one message -> drop and ask
    if updates.get("has_children") is False and updates.get("children_names"):
        del updates["has_children"], updates["children_names"]
        notes.append("You said both that you have no children and named some - which is right?")
    elif updates.get("children_names") and "has_children" not in updates:
        updates["has_children"] = True

    for p, ok in conf.items():  # 1. confirmations / rejections
        progress = True
        if p in s["pending"]:
            v = s["pending"].pop(p)
            if ok:
                _set(s, p, v, "confirmed", changes)
        elif ok:
            s["status"][p] = "confirmed"
        else:
            _set(s, p, None, "unknown", changes)

    for p, v in updates.items():  # 2. explicit values
        progress = True
        cur = get_value(s["values"], p)
        if s["status"][p] == "confirmed" and cur != v and not correction:
            s["pending"][p] = v  # cross-turn contradiction: ask before overwriting
        else:
            s["pending"].pop(p, None)
            _set(s, p, v, "confirmed", changes)

    for p, v in tentative.items():  # 3. hedged values stay unconfirmed
        if s["status"][p] in ("unknown", "unconfirmed"):
            progress = True
            _set(s, p, v, "unconfirmed", changes)

    vals = s["values"]  # 4. keep children consistent
    if vals["has_children"] is False and vals["children_names"] != []:
        _set(s, "children_names", [], "confirmed", changes)
    elif vals["has_children"] is True and vals["children_names"] == []:
        _set(s, "children_names", None, "unknown", [])

    if asked and not progress:  # 5. vague answers: clarify, then move on
        p, n = asked["path"], s["attempts"].get(asked["path"], 0) + 1
        s["attempts"][p] = n
        if n >= MAX_ATTEMPTS:
            s["attempts"].pop(p)
            if asked["kind"] == "resolve_pending":
                s["pending"].pop(p, None)
                notes.append(f"OK, I'll keep your earlier {label(p)}.")
            else:
                if asked["kind"] == "confirm":
                    _set(s, p, None, "unknown", [])
                s["skipped"].append(p)
                notes.append(f"I'll leave {label(p)} as not provided for now.")
    elif not progress and not notes:
        notes.append("I didn't catch anything new.")

    if vals["executor"]["name"] is None and s["status"]["executor.relationship"] == "unconfirmed":
        _set(s, "executor.relationship", None, "unknown", [])  # no half-filled executor

    ack = data.get("ack") if isinstance(data.get("ack"), str) else ""
    nxt = next_action(s)
    captured = bool(changes) or any(conf.values())  # a pending change is not "captured"
    parts = ([ack[:200]] if captured and ack else []) + notes
    if asked and not progress and not notes and nxt:
        parts.insert(0, "I didn't catch a clear answer.")
    parts.append(prompt(s, nxt))
    return {"session": s, "changes": changes, "errors": errors, "reply": " ".join(parts), "asking": nxt}
