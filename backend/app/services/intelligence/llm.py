from functools import lru_cache

from langchain_core.language_models.chat_models import BaseChatModel

from app.core.config import settings
from app.services.intelligence.errors import LLMConfigError


@lru_cache
def get_chat_model() -> BaseChatModel:
    """Provider-agnostic chat model. Temperature 0 for deterministic extraction."""
    if settings.llm_provider == "anthropic":
        if not settings.anthropic_api_key:
            raise LLMConfigError("ANTHROPIC_API_KEY is not configured.")
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=settings.llm_model,
            api_key=settings.anthropic_api_key,
            temperature=0,
            max_tokens=settings.llm_max_tokens,
            timeout=settings.llm_timeout_seconds,
        )

    if settings.llm_provider == "openai":
        if not settings.openai_api_key:
            raise LLMConfigError("OPENAI_API_KEY is not configured.")
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=settings.llm_model,
            api_key=settings.openai_api_key,
            temperature=0,
            max_tokens=settings.llm_max_tokens,
            timeout=settings.llm_timeout_seconds,
        )

    if settings.llm_provider == "gemini":
        if not settings.google_api_key:
            raise LLMConfigError("GOOGLE_API_KEY is not configured.")
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=settings.llm_model,
            google_api_key=settings.google_api_key,
            temperature=0,
            max_output_tokens=settings.llm_max_tokens,
            timeout=settings.llm_timeout_seconds,
        )

    raise LLMConfigError(f"Unsupported LLM provider: {settings.llm_provider}")
