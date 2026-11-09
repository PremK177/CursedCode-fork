"""
LLM client adapter.

Supports OpenRouter (default) or xAI Grok. Switch providers via LLM_PROVIDER env var.
Logs every prompt and response to server/logs/llm_audit.jsonl per Debug Dojo rules.
"""
from datetime import datetime, timezone
import json
import os
import time
import httpx
from app.core.config import get_settings
from app.core.exceptions import LLMUnavailableError
from app.core.logging import get_logger

logger = get_logger(__name__)

OPENROUTER_BASE = "https://openrouter.ai/api/v1"
XAI_BASE = "https://api.x.ai/v1"

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "logs")
AUDIT_LOG_PATH = os.path.join(LOG_DIR, "llm_audit.jsonl")


def log_llm_audit(
    messages: list[dict],
    response_text: str,
    model: str,
    provider: str,
    status: str,
    latency_ms: int = 0,
) -> None:
    """Append prompt and response audit entry to server/logs/llm_audit.jsonl."""
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "provider": provider,
            "model": model,
            "status": status,
            "latency_ms": latency_ms,
            "messages": messages,
            "response": response_text,
        }
        with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as exc:
        logger.warning("Could not write LLM audit log: %s", exc)


async def chat_completion(messages: list[dict], max_tokens: int = 512) -> str:
    """Send a chat completion request, audit-log prompt & response, and return assistant text."""
    settings = get_settings()

    if settings.llm_provider == "openrouter":
        url = f"{OPENROUTER_BASE}/chat/completions"
        api_key = settings.openrouter_api_key
        model = settings.openrouter_model
    else:
        url = f"{XAI_BASE}/chat/completions"
        api_key = settings.xai_api_key
        model = settings.xai_model

    if not api_key:
        log_llm_audit(
            messages=messages,
            response_text="[LLM API key not configured; deterministic fallback used]",
            model=model,
            provider=settings.llm_provider,
            status="skipped_no_api_key",
            latency_ms=0,
        )
        raise LLMUnavailableError("LLM API key is not configured.")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {"model": model, "messages": messages, "max_tokens": max_tokens}

    start_time = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            log_llm_audit(
                messages=messages,
                response_text=content,
                model=model,
                provider=settings.llm_provider,
                status="ok",
                latency_ms=latency_ms,
            )
            return content
    except httpx.TimeoutException as exc:
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        log_llm_audit(
            messages=messages,
            response_text=f"[Timeout: {exc}]",
            model=model,
            provider=settings.llm_provider,
            status="timeout",
            latency_ms=latency_ms,
        )
        logger.error("LLM request timed out: %s", exc)
        raise LLMUnavailableError("LLM request timed out.")
    except Exception as exc:
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        log_llm_audit(
            messages=messages,
            response_text=f"[Error: {exc}]",
            model=model,
            provider=settings.llm_provider,
            status="error",
            latency_ms=latency_ms,
        )
        logger.error("LLM request failed: %s", exc)
        raise LLMUnavailableError("LLM provider returned an error.")
