import uuid
from typing import Any, Literal, Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from core.schema import new_session
from core.engine import process_turn, prompt, next_action
from core.document import render
from llm.factory import get_llm

app = FastAPI(title="Document Intake Assistant")
llm, LLM_MODE, CONFIG_WARNING = get_llm()
SESSIONS: dict[str, dict] = {}  # in-memory; swap for a DB in production


# ---- API contract -------------------------------------------------------
class MessageIn(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


class Executor(BaseModel):
    name: Optional[str] = None
    relationship: Optional[str] = None


class Values(BaseModel):
    full_name: Optional[str] = None
    home_address: Optional[str] = None
    covers_worldwide_assets: Optional[bool] = None
    has_children: Optional[bool] = None
    children_names: Optional[list[str]] = None
    executor: Executor = Field(default_factory=Executor)
    specific_gifts: Optional[list[str]] = None
    additional_wishes: Optional[list[str]] = None


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class Change(BaseModel):
    field: str
    old: Any = None
    new: Any = None


class SessionView(BaseModel):
    session_id: str
    state: Values                                # structured data (null = unknown)
    status: dict[str, Literal["unknown", "unconfirmed", "confirmed"]]
    pending_changes: dict[str, Any]              # new values awaiting the user's OK
    skipped: list[str]                           # questions we gave up on for now
    document: str
    history: list[ChatMessage]
    llm_mode: Literal["mock", "anthropic"]
    config_warning: Optional[str] = None
    changes: list[Change] = []                   # what this turn changed
    errors: list[str] = []                       # validation problems with model output


def view(sid: str, changes=None, errors=None) -> SessionView:
    r = SESSIONS[sid]
    s = r["session"]
    return SessionView(session_id=sid, state=s["values"], status=s["status"], pending_changes=s["pending"],
                       skipped=s["skipped"], document=render(s), history=r["history"], llm_mode=LLM_MODE,
                       config_warning=CONFIG_WARNING, changes=changes or [], errors=errors or [])


def _get(sid: str) -> dict:
    if sid not in SESSIONS:
        raise HTTPException(404, "session not found")
    return SESSIONS[sid]


# ---- routes -------------------------------------------------------------
@app.post("/api/sessions", response_model=SessionView)
def create():
    sid = uuid.uuid4().hex
    s = new_session()
    intro = "Hi! This is a fictional practice document, not legal advice. " + prompt(s, next_action(s))
    SESSIONS[sid] = {"session": s, "history": [{"role": "assistant", "content": intro}]}
    return view(sid)


@app.get("/api/sessions/{sid}", response_model=SessionView)
def get(sid: str):
    _get(sid)
    return view(sid)


@app.post("/api/sessions/{sid}/messages", response_model=SessionView)
def send(sid: str, body: MessageIn):
    rec = _get(sid)
    r = process_turn(rec["session"], rec["history"], body.message, llm)
    rec["session"] = r["session"]
    rec["history"] += [{"role": "user", "content": body.message}, {"role": "assistant", "content": r["reply"]}]
    return view(sid, r["changes"], r["errors"])


app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def index():
    return FileResponse("static/index.html")
