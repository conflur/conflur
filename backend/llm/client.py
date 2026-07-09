"""
Cliente LLM (LiteLLM) — abstracción única para todos los agentes.

Principios del proyecto:
- Modelo configurable por agente vía `.env` (NOTES_MODEL, CEO_MODEL, ...); default Sonnet 4.6.
- Se persiste el uso de tokens para optimizar con datos reales (no limitar a priori).
- El backend (LiteLLM) es inyectable → los tests corren sin litellm ni API key.

El swap de modelo NO requiere cambios de código: se cambia la variable de entorno.
"""
from dataclasses import dataclass
from typing import Callable

from config import settings


@dataclass
class LLMResult:
    text: str
    model: str
    input_tokens: int
    output_tokens: int

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


# Firma del backend: (messages, model, max_tokens, temperature, top_p=None) -> LLMResult
CompletionFn = Callable[..., LLMResult]


def _litellm_backend(
    messages: list[dict],
    model: str,
    max_tokens: int,
    temperature: float,
    top_p: float | None = None,
) -> LLMResult:
    """Backend real. Importa litellm de forma perezosa (solo se necesita en runtime)."""
    import litellm

    # Anthropic no acepta temperature y top_p simultáneamente.
    if top_p is not None:
        extra = {"top_p": top_p}
    else:
        extra = {"temperature": temperature}
    resp = litellm.completion(
        model=f"anthropic/{model}",
        messages=messages,
        max_tokens=max_tokens,
        api_key=settings.ANTHROPIC_API_KEY,
        **extra,
    )
    text = resp.choices[0].message.content or ""
    usage = resp.usage
    return LLMResult(
        text=text,
        model=model,
        input_tokens=getattr(usage, "prompt_tokens", 0),
        output_tokens=getattr(usage, "completion_tokens", 0),
    )


class LLMClient:
    """Cliente reusable por los agentes. `backend` inyectable para tests."""

    def __init__(self, backend: CompletionFn | None = None):
        self._backend = backend or _litellm_backend

    def complete(
        self,
        messages: list[dict],
        *,
        model: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.3,
        top_p: float | None = None,
    ) -> LLMResult:
        model = model or settings.NOTES_MODEL
        return self._backend(messages, model, max_tokens, temperature, top_p)


# Instancia por defecto (backend litellm). Los agentes la importan; los tests
# construyen LLMClient(backend=fake).
default_client = LLMClient()


def get_llm_client() -> LLMClient:
    """Dependency de FastAPI. Los tests la overridean con un backend fake."""
    return default_client
