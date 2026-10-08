# Document Intake Assistant (practice project)
Conversational intake for a *fictional* Personal Wishes Document. Not legal advice.

## Run
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload          # mock model by default -> http://localhost:8000
```
Real model: `cp .env.example .env`, then `export LLM_PROVIDER=anthropic ANTHROPIC_API_KEY=...` (never commit keys).
If the provider is `anthropic` but the key is missing, the app **starts anyway on the mock** and shows a warning banner in the UI.

## Test
```bash
python -m unittest discover -s tests -t .          # core logic: stdlib only
pip install -r requirements-dev.txt && same command # also runs the API tests
```

## Architecture
| Layer | File | Job |
|---|---|---|
| UI | `static/index.html` | chat, live state with status colours, pending changes, draft preview |
| API | `main.py` | typed request/response models (pydantic) |
| App logic | `core/engine.py` | call LLM, validate, apply, choose next question |
| Schema | `core/schema.py` | fields, types, validation, status model |
| LLM | `llm/` | `extract(session, asking, message, history) -> raw JSON string` |
| Document | `core/document.py` | pure function: session -> text |

## API contract
| Method + path | Body | Returns |
|---|---|---|
| `POST /api/sessions` | - | `SessionView` |
| `GET /api/sessions/{id}` | - | `SessionView` (404 if unknown) |
| `POST /api/sessions/{id}/messages` | `{"message": str (1-2000 chars)}` | `SessionView` (422 if invalid) |

`SessionView`: `state` (nested, as in the brief; `null` = unknown), `status` per field
(`unknown | unconfirmed | confirmed`), `pending_changes`, `skipped`, `document`, `history`, `llm_mode`,
`config_warning`, `changes` (this turn), `errors` (rejected model output). Full schema at `/docs`.

## Model contract (what any LLM provider must return)
```json
{"updates": {"executor": {"name": "James"}},      // stated clearly -> confirmed
 "tentative": {},                                  // hedged ("probably...") -> unconfirmed
 "confirmations": {"executor.name": true},         // yes/no to a confirm / change question
 "correction": false,                              // explicit "actually..." change
 "ack": "Thanks."}
```
Everything is validated (types, unknown keys, lengths) before it touches state.

## Behaviour decisions
- **State, not chat history, is the source of truth.** The LLM only proposes updates.
- **Unknown vs unconfirmed vs none**: `null` unknown; `unconfirmed` = hedged, shown as `[UNCONFIRMED]` and queried back; `[]` = user said "none".
- **Next question is chosen in code**: pending change > unconfirmed value > next unknown field. Never re-asks captured data.
- **Contradictions**: within one message -> dropped and asked. Across turns -> kept as `pending`, user is asked "Did you mean to change X to Y?". Explicit corrections ("actually...") overwrite directly.
- **Vague answers**: 1st failure -> tailored clarifying question; 2nd -> field is skipped (listed, can be filled any time). No infinite loops.
- **Failures**: malformed JSON -> one retry; network/provider errors and bad shapes leave state untouched and return a polite reply.

## Replacing the mock with a real provider
`MockLLM` and `AnthropicLLM` implement one method, `extract(session=, asking=, message=, history=) -> str`.
`llm/factory.py` picks one from `LLM_PROVIDER`. To add another provider, write a class with that method that
returns JSON following the model contract above; the engine, validation and tests don't change.
Fixtures in `tests/fixtures/` (valid, ambiguous, malformed, invalid, contradictory) replay canned outputs through the
real engine, and the same fixtures are a good regression suite for any provider.
The mock is regex based and intentionally simple; a real model handles far more phrasing.

## Improve for production
Persistent storage + auth/session expiry; structured outputs / tool-calling instead of free-form JSON; eval suite on
real transcripts; prompt-injection handling; encryption/retention of personal data; streaming and async HTTP;
rate limiting; undo history; observability; legal review of the template; per-field confidence from the model.
