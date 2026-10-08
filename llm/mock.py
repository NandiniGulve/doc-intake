"""Deterministic stand-in for a real model (regex based, so deliberately simple).
Same interface and output contract as AnthropicLLM."""
import json
import re

REL = r"(brother|sister|mother|father|son|daughter|husband|wife|partner|friend|cousin|uncle|aunt|nephew|niece|solicitor|lawyer)"
NAME = r"([A-Z][\w'\-]+(?:\s+[A-Z][\w'\-]+)*)"
SPLIT = r",|\band\b"
HEDGE = r"\b(probably|i think|maybe|might|perhaps|not certain)\b"
YES = r"\W*(yes|yeah|yep|correct|that'?s right|right)\b"
NO = r"\W*(no|nope|wrong|incorrect)\b"


class MockLLM:
    def extract(self, *, session, asking, message, history):
        if message.startswith("!malformed"):  # hooks to simulate misbehaving models
            return "Sure! here you go {not json"
        if message.startswith("!badtype"):
            return json.dumps({"updates": {"has_children": "yes", "favourite_colour": "red"}})
        m = message.strip()
        low = m.lower()
        kind, ap = (asking["kind"], asking["path"]) if asking else (None, None)
        ask = ap if kind == "ask" else None
        u, c = {}, {}

        if kind in ("confirm", "resolve_pending"):
            if re.match(YES, low):
                c[ap] = True
                return self._out(u, {}, c, False)
            if re.match(NO, low):
                c[ap] = False
                if x := re.search(r"(?:it'?s|it is|actually)\s+([^.]+)", m, re.I):
                    u[ap] = x.group(1).strip()
                return self._out(u, {}, c, bool(u))

        pat = r"my name is" if ask != "full_name" else r"my name is|i am|i'm"
        if x := re.search(rf"(?:{pat})\s+([^,.;]+?)(?:\s+and\b|[,.;]|$)", m, re.I):
            u["full_name"] = x.group(1).strip()
        if x := re.search(r"(?:i live (?:at|in)|my address is|address is)\s+(.+?)(?:\.\s|\.$|$)", m, re.I):
            u["home_address"] = x.group(1).strip()

        if ask == "covers_worldwide_assets" or "worldwide" in low:
            if re.search(r"not sure|maybe|don't know|unsure", low):
                pass  # ambiguous -> nothing extracted
            elif re.search(r"\b(no|only|just|not)\b", low):
                u["covers_worldwide_assets"] = False
            elif re.search(r"\b(yes|yeah|yep|all|worldwide|everything)\b", low):
                u["covers_worldwide_assets"] = True

        if re.search(r"\b(no|don'?t have (?:any )?)\s*(children|kids)\b", low) or (
                ask == "has_children" and re.fullmatch(r"\W*(no|nope|none)\W*", low)):
            u["has_children"] = False
        elif x := re.search(r"(?:children|kids)(?: are| named|:)\s+(.+)", m, re.I):
            u["children_names"] = [n.strip() for n in re.split(SPLIT, x.group(1).rstrip(".")) if n.strip()]
        elif ask == "has_children" and re.fullmatch(r"\W*(yes|yeah|yep)\W*", low):
            u["has_children"] = True

        x = re.search(rf"(?:executor is|appoint|executor will be|executor to be)\s+(?:(?:probably|maybe|perhaps)\s+)?(?:my\s+)?(?:{REL}\s+)?{NAME}", m)
        if x:
            if x.group(1):
                u["executor.relationship"] = x.group(1).lower()
            u["executor.name"] = x.group(2)
        elif ask == "executor.name" and not u:
            x = re.fullmatch(rf"(?:my\s+)?(?:{REL}\s+)?{NAME}\W*", m, re.I)
            if x:
                if x.group(1):
                    u["executor.relationship"] = x.group(1).lower()
                u["executor.name"] = x.group(2).strip()
        elif x := re.search(rf"\b{REL}\b", low):
            if ask == "executor.relationship" or "executor" in low:
                u["executor.relationship"] = x.group(1)

        if not u and m:  # bare answers to the question just asked
            if ask == "full_name" and re.fullmatch(NAME, m):
                u["full_name"] = m
            elif ask == "home_address" and len(m) > 8:
                u["home_address"] = m
            elif ask == "children_names":
                u["children_names"] = [n.strip() for n in re.split(SPLIT, m.rstrip(".")) if n.strip()]
            elif ask in ("specific_gifts", "additional_wishes"):
                u[ask] = [] if re.fullmatch(r"\W*(none|no|nothing|nope)\W*", low) else [
                    s.strip() for s in re.split(r";|\n", m) if s.strip()]

        if re.search(r"not sure|unsure|don't know", low):
            u = {}
        t = {}
        if u and re.search(HEDGE, low):  # hedged -> tentative, not confirmed
            t, u = u, {}
        corr = bool(re.search(r"\b(actually|correction|change|instead|sorry|i meant)\b", low))
        return self._out(u, t, c, corr)

    @staticmethod
    def _out(u, t, c, corr):
        return json.dumps({"updates": u, "tentative": t, "confirmations": c, "correction": corr,
                           "ack": "Thanks." if (u or t or c) else ""})
