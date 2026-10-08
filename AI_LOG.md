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
2. Reviewing the Implementation Against the Assignment

After the initial implementation, I specifically reviewed whether the application covered all the requirements in the provided technical-test brief.

Prompt used:

"Does this project take into consideration everything mentioned?"

Issues identified during the review

The review identified several areas that needed improvement:

The executor information was not represented in the desired nested structure.
There was no clear distinction between unknown, unconfirmed, and confirmed information.
Existing information could potentially be overwritten without confirmation.
Some conversation paths could result in repeated questions.
API responses were not sufficiently typed.
Missing LLM configuration could result in an application failure instead of a graceful fallback.
Test fixtures for valid, ambiguous, and malformed LLM responses were missing.

These were treated as engineering gaps rather than assuming that the initial implementation was complete.

3. Correcting the Identified Gaps

Prompt used:

"Let me know all the gaps and what problems do they cause?"

The implementation was then revised to address the identified issues.

Main improvements

Structured executor information

Executor details were represented separately so that the executor's name and relationship could be managed consistently.

Field confirmation

Information was given explicit states such as:

Unknown
Unconfirmed
Confirmed

This prevents uncertain information from being treated as established fact.

Protection against accidental overwrites

When a user provides information that conflicts with previously confirmed information, the application can request confirmation before replacing the existing value.

Conversation flow

The application checks the current state before deciding what information is still required. This reduces unnecessary repetition and helps prevent question loops.

Typed API responses

The API contract was made explicit so that the frontend receives predictable structured data.

Graceful LLM configuration

If the real LLM configuration is unavailable, the application can continue using the deterministic mock provider rather than failing during startup.

Test fixtures

Fixtures were added for different LLM-output situations, including:

Valid structured output
Ambiguous output
Malformed output

This provides a way to test how the application behaves when the AI component does not behave perfectly.

4. Testing and Validation

I did not rely only on the generated implementation. I ran the automated test suite locally and also tested the application manually through the user interface.

The test cases included:

Providing multiple fields in a single response
Providing uncertain or hedged answers
Correcting previously entered information
Providing contradictory information
Repeatedly responding with "not sure"
Testing malformed model output
Checking the generated document

The automated test suite initially passed 31 tests.

After additional fixes and regression tests were added, the test suite reached 33 passing tests.

5. Issues Found During Testing
5.1 Incomplete Executor Information

During manual testing, I found an issue with partially confirmed executor information.

For example, after an executor name became uncertain, the relationship could remain stored. This could produce an inconsistent document containing a missing executor name while still displaying the relationship.

Fix

The state-update logic was changed so that:

A relationship is not retained independently when its executor name is no longer confirmed.
An unconfirmed relationship is reset when the corresponding executor name is removed.
The application does not generate a misleading half-complete executor entry.

Additional tests were added to prevent regression.

5.2 Incorrect Confirmation Wording

During testing, the application sometimes responded with wording such as "Thanks" even though a change was still waiting for confirmation.

This was misleading because the system had not actually accepted the new information yet.

Fix

The response logic was changed so that the application clearly communicates when information is:

Being requested
Awaiting confirmation
Confirmed and stored

This keeps the conversational response consistent with the actual structured state.

5.3 Python Indentation Error

While applying one of the fixes, an IndentationError was introduced into the Python code due to incorrect indentation during a copy/paste.

This caused several test modules to fail during import.

I used the Python traceback to locate the problematic section, corrected the indentation, and ran the test suite again.

After correcting the issue, the tests passed successfully.

This was a useful reminder that generated code must still be executed and validated rather than being accepted based only on visual inspection.

5.4 Environment Configuration

I also identified an issue with environment configuration.

The project used a .env file for configuration, but the application was not initially loading the values from the file.

Fix

Environment loading was added using python-dotenv, together with load_dotenv() during application startup.

This allows configuration such as the LLM provider and API key to be read from the environment without hard-coding secrets in the source code.

6. Reviewing AI-Generated Suggestions

During development, I did not assume that every AI-generated suggestion was correct.

One example was the initial AI-generated documentation. It described some implementation details that did not exactly match the final project structure. I compared the documentation against the actual code and revised it so that the documentation reflects the implemented system rather than the originally proposed design.

I also treated the real LLM integration as unverified until it could be tested against the actual provider. The deterministic mock provider was used for reliable local development and testing.

Another consideration was the mock LLM itself. Because it uses deterministic parsing rather than a full language model, it supports a limited range of natural-language variations. This is acceptable for local testing, but a production system would require a real LLM provider together with stronger validation and error handling.