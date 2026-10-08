# Document Intake Assistant (practice project)

A small web app that interviews a user and drafts a *fictional* Personal Wishes Document.
**Fictional practice project. Not legal advice.**

Extra files: `AI_LOG.md` (how AI was used) and `PRODUCTION_NOTES.md` (what I would improve for production).

## Setup and run

Requires Python 3.9+.

```bash
python -m venv .venv
# Mac/Linux:  source .venv/bin/activate
# Windows:    .venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
uvicorn main:app --reload
```
Open http://localhost:8000. By default the app uses a built-in mock model, so no API key is needed.

### Using a real model (optional)
1. Copy `.env.example` to `.env` (this file is git-ignored, never commit it).
2. Set `LLM_PROVIDER=anthropic` and `ANTHROPIC_API_KEY=your-key` in `.env`, then restart.
3. If the provider is `anthropic` but the key is missing, the app still starts on the mock and shows a warning banner in the UI.

Note: the real-provider path has only been tested against a mocked HTTP call, not the live API.

## Tests
```bash
python -m unittest discover -s tests -t .
```
Keep `LLM_PROVIDER=mock` in `.env` when running tests (the API tests import the app).
`tests/test_api.py` needs `httpx` (in `requirements-dev.txt`) and is skipped if it isn't installed.

## Architecture
| Layer | File | Job |
|---|---|---|
| UI | `static/index.html` | chat, live state with status colours, pending changes, draft preview |
| API | `main.py` | typed request/response models (pydantic) |
| Application logic | `core/engine.py` | call the LLM, validate, apply, choose the next question |
| Schema | `core/schema.py` | fields, types, validation, status model |
| LLM interaction | `llm/` | `extract(session, asking, message, history) -> raw JSON string` |
| Document generation | `core/document.py` | pure function: session -> text |

## API contract
| Method + path | Body | Returns |
|---|---|---|
| `POST /api/sessions` | none | `SessionView` |
| `GET /api/sessions/{id}` | none | `SessionView` (404 if unknown) |
| `POST /api/sessions/{id}/messages` | `{"message": str (1-2000 chars)}` | `SessionView` (422 if invalid) |

`SessionView` contains: `state` (nested as in the brief, `null` = unknown), `status` per field
(`unknown | unconfirmed | confirmed`), `pending_changes`, `skipped`, `document`, `history`, `llm_mode`,
`config_warning`, `changes` (this turn) and `errors` (rejected model output). Full schema at `/docs`.

## Model contract (what any LLM provider must return)
```json
{"updates": {"executor": {"name": "James"}},
 "tentative": {},
 "confirmations": {"executor.name": true},
 "correction": false,
 "ack": "Thanks."}
```
- `updates`: values stated clearly (stored as confirmed).
- `tentative`: hedged values ("probably...") (stored as unconfirmed and queried back).
- `confirmations`: yes/no to a confirm or change question.
- `correction`: true only for an explicit "actually..." change.

Everything is validated (types, unknown keys, lengths) before it touches state.

## Behaviour decisions
- **State, not chat history, is the source of truth.** The LLM only proposes updates.
- **Unknown vs unconfirmed vs none:** `null` = unknown; `unconfirmed` = hedged, shown as `[UNCONFIRMED]`; `[]` = user said "none".
- **The next question is chosen in code:** pending change, then unconfirmed value, then next unknown field. Captured data is never re-asked.
- **Contradictions:** within one message they are dropped and the user is asked. Across turns the new value is held as `pending` and the user is asked "Did you mean to change X to Y?". Explicit corrections ("actually...") overwrite directly.
- **Vague answers:** the first failure gets a tailored clarifying question, the second skips the field (it is listed and can be filled in later). No infinite loops.
- **Failures:** malformed JSON gets one retry; network/provider errors and bad shapes leave state untouched and return a polite reply.

## Replacing the mock with a real provider
`MockLLM` and `AnthropicLLM` implement one method: `extract(session=, asking=, message=, history=) -> str`.
`llm/factory.py` picks one from `LLM_PROVIDER`. To add another provider, write a class with that method that
returns JSON following the model contract above; the engine, validation and tests don't change.
Fixtures in `tests/fixtures/` (valid, ambiguous, malformed, invalid, contradictory) replay canned model outputs
through the real engine and make a regression suite for any provider.
The mock is regex based and intentionally simple; a real model handles far more phrasing.

## Production
See `PRODUCTION_NOTES.md`.