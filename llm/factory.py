import os
from .mock import MockLLM


def get_llm():
    """Returns (llm, mode, warning). Missing config degrades to the mock instead of crashing."""
    if os.environ.get("LLM_PROVIDER", "mock") == "anthropic":
        try:
            from .anthropic_llm import AnthropicLLM
            return AnthropicLLM(), "anthropic", None
        except RuntimeError as e:
            return MockLLM(), "mock", f"{e}. Falling back to the built-in mock model."
    return MockLLM(), "mock", None
