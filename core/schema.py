"""Explicit schema. Values are nested like the brief's example; per-field status lives beside them.
status: unknown (no value) | unconfirmed (hedged / tentative) | confirmed.
None = unknown, [] = user explicitly said 'none'."""
FIELDS = {  # path: (type, question, clarifying question used after a failed attempt)
    "full_name": ("str", "What is your full name?", "Could you give me your full name, first and last?"),
    "home_address": ("str", "What is your home address?", "Please give the street, town and postcode of your home."),
    "covers_worldwide_assets": ("bool", "Should this document cover your assets worldwide? (yes/no)",
                                "Do you want it to cover assets anywhere in the world (yes), or only those in your home country (no)?"),
    "has_children": ("bool", "Do you have any children?", "Just yes or no - do you have any children?"),
    "children_names": ("str_list", "What are your children's names?", "Please list your children's first names, separated by commas."),
    "executor.name": ("str", "Who would you like to appoint as your executor?", "Please give the name of the person you'd like as executor."),
    "executor.relationship": ("str", "How is your executor related to you?", "For example brother, friend or solicitor - how are they related to you?"),
    "specific_gifts": ("str_list", "Are there any specific gifts you want to leave? (or say 'none')", "List any gifts you want to leave, or say 'none'."),
    "additional_wishes": ("str_list", "Any additional wishes? (or say 'none')", "List any other wishes, or say 'none'."),
}
ORDER = list(FIELDS)
MAX_LEN = 500


def label(path: str) -> str:
    return path.replace("_", " ").replace(".", " ")


def get_value(values: dict, path: str):
    for p in path.split("."):
        values = values[p]
    return values


def set_value(values: dict, path: str, val):
    *parents, last = path.split(".")
    for p in parents:
        values = values[p]
    values[last] = val


def new_session() -> dict:
    values = {"executor": {}}
    for p in FIELDS:
        set_value(values, p, None)
    return {"values": values, "status": {p: "unknown" for p in FIELDS}, "pending": {}, "attempts": {}, "skipped": []}


def applicable(values: dict, path: str) -> bool:
    if path == "children_names":
        return values["has_children"] is True
    if path == "executor.relationship":  # pointless to ask without a name
        return values["executor"]["name"] is not None
    return True


def flatten(updates) -> tuple[dict, list[str]]:
    """Accept nested ({"executor": {"name": ..}}) or dotted keys -> flat path dict."""
    if not isinstance(updates, dict):
        return {}, ["expected an object"]
    flat, errors = {}, []
    for k, v in updates.items():
        if k == "executor":
            if isinstance(v, dict):
                flat.update({f"executor.{k2}": v2 for k2, v2 in v.items()})
            else:
                errors.append("executor must be an object")
        else:
            flat[k] = v
    return flat, errors


def _clean_str(v):
    if isinstance(v, str) and v.strip() and len(v) <= MAX_LEN:
        return v.strip()
    raise ValueError("expected non-empty string (<=500 chars)")


def validate(flat: dict) -> tuple[dict, list[str]]:
    """Strictly validate model output. Returns (clean, errors)."""
    clean, errors = {}, []
    for key, val in flat.items():
        if key not in FIELDS:
            errors.append(f"unknown field: {key}")
            continue
        kind = FIELDS[key][0]
        try:
            if kind == "str":
                clean[key] = _clean_str(val)
            elif kind == "bool":
                if not isinstance(val, bool):  # reject "yes", 1, etc.
                    raise ValueError("expected true/false")
                clean[key] = val
            else:
                if not isinstance(val, list):
                    raise ValueError("expected list")
                clean[key] = [_clean_str(x) for x in val]
        except ValueError as e:
            errors.append(f"{key}: {e}")
    return clean, errors


def validate_updates(updates) -> tuple[dict, list[str]]:
    flat, e1 = flatten(updates)
    clean, e2 = validate(flat)
    return clean, e1 + e2


def validate_confirmations(conf, session) -> tuple[dict, list[str]]:
    if not isinstance(conf, dict):
        return {}, ["confirmations must be an object"]
    ok, errors = {}, []
    for p, v in conf.items():
        if not isinstance(v, bool):
            errors.append(f"confirmation {p}: expected true/false")
        elif p not in session["pending"] and session["status"].get(p) != "unconfirmed":
            errors.append(f"confirmation {p}: nothing awaiting confirmation")
        else:
            ok[p] = v
    return ok, errors
