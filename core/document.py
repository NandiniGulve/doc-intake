from .schema import FIELDS, get_value

MISSING = "[NOT YET PROVIDED]"


def _mark(s, p, text):
    return text + (" [UNCONFIRMED]" if s["status"][p] == "unconfirmed" else "")


def _scalar(s, p):
    v = get_value(s["values"], p)
    return MISSING if v is None else _mark(s, p, str(v))


def _list(s, p, empty, sep="; "):
    v = get_value(s["values"], p)
    if v is None:
        return MISSING
    return _mark(s, p, sep.join(v)) if v else empty


def render(s: dict) -> str:
    v = s["values"]
    w = {True: "worldwide", False: "in the jurisdiction of residence only", None: MISSING}[v["covers_worldwide_assets"]]
    if v["covers_worldwide_assets"] is not None:
        w = _mark(s, "covers_worldwide_assets", w)
    kids = {True: f"I have children: {_list(s, 'children_names', 'None', ', ')}.",
            False: "I have no children.", None: f"Children: {MISSING}"}[v["has_children"]]
    done = sum(1 for p in FIELDS if s["status"][p] == "confirmed")
    return f"""*** FICTIONAL DOCUMENT - FOR PRACTICE ONLY - NOT LEGAL ADVICE ***

PERSONAL WISHES DOCUMENT (DRAFT)

1. Personal details
I, {_scalar(s, 'full_name')}, of {_scalar(s, 'home_address')}, set out my wishes below.

2. Scope
This document applies to my assets: {w}.

3. Family
{kids}

4. Executor
I appoint {_scalar(s, 'executor.name')} ({_scalar(s, 'executor.relationship')}) as my executor.

5. Specific gifts
{_list(s, 'specific_gifts', 'None specified')}

6. Additional wishes
{_list(s, 'additional_wishes', 'None specified')}

(Confirmed fields: {done}/{len(FIELDS)}. Items marked [UNCONFIRMED] still need your confirmation.)
*** This is a fictional draft and does not constitute legal advice. ***
"""
