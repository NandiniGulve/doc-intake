# What I would improve for production

**Reliability**
- Use the provider's structured output / tool-calling instead of asking for free-form JSON.
- Build an evaluation set from real conversations to catch regressions when prompts or models change.
- Add timeouts, backoff and a circuit breaker around LLM calls, and use async HTTP.

**Data and security**
- Replace the in-memory sessions with a database, plus authentication and session expiry.
- Encrypt personal data, set retention and deletion rules, and keep PII out of logs.
- Add prompt-injection defences, input limits and rate limiting.

**Product**
- Add undo/history for edits, per-field confidence from the model, and streaming responses.
- Support different jurisdictions, and have a lawyer review the document template.
- Improve accessibility of the UI.

**Operations**
- Add logging, metrics and tracing, and track model cost and latency.
- Set up CI that runs the tests, and Docker for reproducible setup.