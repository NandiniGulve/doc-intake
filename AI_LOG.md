# AI log - YOU must rewrite this with your own experience
The entries below are what happened when an AI assistant helped scaffold this project. Keep only what is true
for you, and add your own prompts, mistakes and fixes. Candid beats polished.

## Entries from the scaffold (verify, edit or delete)
1. Prompt: "Design a small app that interviews a user and keeps structured state." Result: state as source of
   truth, LLM only extracts.
2. Bug found by a test: the mock treated any long message as an address, so "Actually my name is X" also
   overwrote the address. Fixed by only using "bare answer" rules when nothing else matched.
3. Output I questioned: "I'm ..." was parsed as a name ("I'm not sure" became a name). Restricted to when the
   name question was just asked.
4. Self-review against the brief found gaps (flat executor, no "unconfirmed" state, silent cross-turn overwrites,
   possible question loops, untyped responses, crash on missing key, no fixtures). All fixed in round two.
5. Limitation: FastAPI could not be run in the build sandbox (no network), so the API tests are skipped there.

## Your entries
- Prompt:
- What the AI produced:
- What I questioned / corrected:
