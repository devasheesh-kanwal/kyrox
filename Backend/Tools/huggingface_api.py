import os
import logging
from pathlib import Path
from dotenv import load_dotenv
try:
    from huggingface_hub import InferenceClient
except ImportError:
    InferenceClient = None

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)
load_dotenv()

logger = logging.getLogger(__name__)

# Configurable LLM used for chat / text generation.
HF_CHAT_MODEL = os.getenv("HF_CHAT_MODEL", "mistralai/Mistral-7B-Instruct-v0.3")

_client: InferenceClient | None = None


class HuggingFaceAPIError(Exception):
    """Raised when a Hugging Face inference request fails."""


def get_hf_client() -> InferenceClient:
    """Return a reusable InferenceClient authenticated with HF_TOKEN."""
    global _client

    token = os.getenv("HF_TOKEN") or os.getenv("HUGGING_FACE_KEY")
    if not token:
        raise RuntimeError("HF_TOKEN (or HUGGING_FACE_KEY) environment variable is not set in .env")

    if _client is None:
        _client = InferenceClient(model=HF_CHAT_MODEL, token=token)

    return _client


def generate_chat_response(system_prompt: str, user_message: str) -> str:
    """
    Send a system prompt and user message to the configured Hugging Face chat model.
    Returns only the assistant's generated text.
    """
    if not isinstance(system_prompt, str) or not system_prompt.strip():
        raise ValueError("system_prompt must be a non-empty string")
    if not isinstance(user_message, str) or not user_message.strip():
        raise ValueError("user_message must be a non-empty string")

    messages = [
        {"role": "system", "content": system_prompt.strip()},
        {"role": "user", "content": user_message.strip()},
    ]

    try:
        client = get_hf_client()
        completion = client.chat_completion(
            messages=messages,
            model=HF_CHAT_MODEL,
            max_tokens=512,
            temperature=0.2,
        )
    except RuntimeError:
        raise
    except Exception as exc:
        logger.error("Hugging Face chat completion failed: %s", type(exc).__name__)
        raise HuggingFaceAPIError("Unable to generate a response from Hugging Face") from exc

    text = _extract_assistant_text(completion)
    if not text:
        raise HuggingFaceAPIError("Hugging Face returned an empty response")
    return text


def _extract_assistant_text(completion) -> str:
    try:
        choices = getattr(completion, "choices", None)
        if choices:
            message = getattr(choices[0], "message", None)
            content = getattr(message, "content", None) if message is not None else None
            if isinstance(content, str) and content.strip():
                return content.strip()
            if isinstance(choices[0], dict):
                nested = choices[0].get("message") or {}
                content = nested.get("content") if isinstance(nested, dict) else None
                if isinstance(content, str) and content.strip():
                    return content.strip()

        if isinstance(completion, dict):
            choices = completion.get("choices") or []
            if choices:
                nested = choices[0].get("message") or {}
                content = nested.get("content") if isinstance(nested, dict) else None
                if isinstance(content, str) and content.strip():
                    return content.strip()

        generated = getattr(completion, "generated_text", None)
        if isinstance(generated, str) and generated.strip():
            return generated.strip()
    except (AttributeError, IndexError, TypeError, KeyError):
        logger.warning("Unexpected Hugging Face completion payload shape")

    return ""


