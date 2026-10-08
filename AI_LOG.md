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
- What I questioned / corrected: When i said "not sure" to the confirmation question, it dropped "James" entirely but kept "brother", so the draft says "I appoint [NOT YET PROVIDED] (brother [UNCONFIRMED])". A cleaner rule is to leave the value unconfirmed and move on, or to drop both name and relationship together.
# AI Log

## 1. Initial project design

### Prompt I used

> I have an engineering technical test to build a Document Intake Assistant. It needs a conversational interface, structured state, an LLM interaction layer, validation, corrections to previously supplied information, and generation of a fictional Personal Wishes Document. Suggest a simple full-stack architecture that is easy to test and explain.

### AI response / approach

The AI suggested separating the application into:

* Frontend/UI
* Backend/API
* LLM interaction layer
* Structured state
* Document generation
* Automated tests

I followed this approach because it matched the requirements of the technical test and made the responsibilities of each part clear.

---

## 2. Designing the structured state

### Prompt I used

> Design a Pydantic schema for the Personal Wishes Document information. It should contain full name, home address, worldwide assets, children, executor name and relationship, specific gifts, and additional wishes. Unknown values should be represented explicitly.

### Result

The resulting structure was based around a `WishesState` model:

```json
{
  "full_name": null,
  "home_address": null,
  "covers_worldwide_assets": null,
  "has_children": null,
  "children": [],
  "executor": {
    "name": null,
    "relationship": null
  },
  "specific_gifts": [],
  "additional_wishes": null
}
```

One important decision was to use `null` for information that had not yet been confirmed rather than allowing the application to guess.

---

## 3. Preventing the LLM from directly changing application state

### Prompt I used

> How should I design the LLM interaction so that the LLM does not directly modify the application's structured state? I want the model to propose updates which are validated before they are applied.

### What I learned

The AI suggested using a separate model for the LLM response, such as an `LLMResult`, containing:

* A response message
* Proposed field updates
* A clarification flag

The application then validates this response and applies only the accepted fields to `WishesState`.

The final flow became:

```text
User message
    ↓
LLM
    ↓
LLMResult
    ↓
Pydantic validation
    ↓
Validated update
    ↓
WishesState
```

This was important because the assignment explicitly says that model output should be validated before it is applied to structured state.

---

## 4. Handling corrections

### Prompt I used

> How can I allow the user to correct information they previously supplied without rebuilding the whole conversation state?

### Example

I tested a conversation such as:

```text
User: My executor is James.

User: Actually, my executor is Sarah.
```

The implementation treats the second message as a new validated update and changes only the executor name.

The important design principle was:

```text
LLM output = proposed update
Structured state = source of truth
```

This also makes the behavior easier to test.

---

## 5. Handling multiple fields in one message

### Prompt I used

> The user may provide several pieces of information in a single message, for example "My name is Jane Smith and I live at 10 High Street." How should the application handle this?

### Result

I added extraction logic that can identify multiple fields from one message and return them together.

For example:

```text
User:
My name is Jane Smith and my address is 10 High Street.
```

can produce updates for:

```text
full_name
home_address
```

instead of asking the user for each field again.

This was useful because the assignment specifically expects the application to handle answers containing several fields in a reasonable order.

---

## 6. Testing the implementation

### Prompt I used

> Create a small pytest test suite for the most important behavior of the application. Include structured state updates, document generation, multiple-field extraction, and corrections.

### What I tested

I added tests for:

* API health
* Structured state updates
* Preserving fields that were not changed
* Multiple-field extraction
* Children extraction
* Corrections
* Required document disclaimer
* Missing information

I used tests to catch implementation problems rather than relying only on manually checking the UI.

---

## 7. Bug caught during testing — indentation error

During development, I encountered an indentation error in the Python code.

The code looked structurally correct at first glance, but Python reported an error when the test/application was executed.

Instead of assuming that the generated code was correct, I ran the tests and used the error message to locate the problem.

I corrected the indentation and ran the tests again.

This was a useful example of why AI-generated code still needs to be executed and reviewed. The AI can produce code that looks reasonable but contains a simple syntax or indentation mistake.

The final lesson was:

> Never assume generated code is correct just because it looks correct. Run the application and tests.

---

## 8. Mock LLM decision

### Prompt I used

> I may not have access to a paid LLM API while developing the assignment. How can I design the application so that it still demonstrates the LLM architecture?

### Result

I implemented a deterministic `MockLLM` behind the same interface as the real provider.

The architecture is:

```text
LLM Adapter
   ├── MockLLM
   └── OpenAIAdapter
```

The default configuration uses the mock provider, so the application can be run without an API key.

A real provider can be enabled through environment configuration.

This also makes testing easier because the mock provider produces predictable results.

---

## 9. AI output that I questioned

One approach suggested by AI was effectively to let the model's response become application state directly.

I did not use that approach.

I considered it unsafe because an LLM response can be malformed, incomplete, or contain information that was not actually supplied by the user.

I changed the design so that:

```text
LLM
 ↓
Structured response
 ↓
Validation
 ↓
State update
```

rather than:

```text
LLM
 ↓
Directly modify state
```

This was one of the main engineering decisions I made while using AI assistance.

---

## 10. Error handling

### Prompt I used

> What should happen if the LLM returns malformed output or the provider fails?

### Result

The backend was designed so that model output must match the expected Pydantic structure before it is applied.

If the provider fails, the backend returns a controlled error instead of silently changing the structured state.

For a production application, I would additionally add:

* Provider timeouts
* Retries
* Rate limiting
* Logging/observability
* Better provider-specific error handling
* Persistent state

---

## 11. What I would improve

The current project is intentionally small for the technical test.

If I continued developing it, I would improve:

1. More robust ambiguity and contradiction detection.
2. Stronger provider-native structured output.
3. Persistent storage such as PostgreSQL.
4. Authentication and authorization.
5. Audit history for state changes.
6. Better frontend and end-to-end tests.
7. More comprehensive LLM evaluation fixtures.
8. Timeouts and retries around external LLM calls.
9. Secure storage of sensitive personal information.
10. A proper secrets manager for production.
11. Document versioning and explicit final confirmation.
12. Additional observability and monitoring.

---

## 12. Overall reflection

AI was useful for generating initial implementation ideas, suggesting test cases, debugging, and improving the project structure.

However, I did not treat AI output as automatically correct. I verified the generated code by running the application and tests, reviewed the resulting behavior, and changed the design where necessary.

The most important lesson from using AI for this project was that the LLM should be treated as an unreliable external component. The application itself should maintain the source of truth, validate model output, handle errors, and make state changes explicitly.
