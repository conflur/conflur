"""
Agente de Descubrimiento — conduce la validación de mercado por conversación.

Motor genérico (Capa 0-1); config específica de Conflur abajo.
"""
import json
from dataclasses import dataclass

from config import settings
from llm.client import LLMClient, LLMResult, default_client


@dataclass
class DiscoveryConfig:
    """Config por instancia."""
    descripcion_producto: str   # qué hace el producto, en una oración
    incentivo: str              # ofrecimiento al final


CONFLUR = DiscoveryConfig(
    descripcion_producto=(
        "una app para psicólogos de consultorio privado que automatiza tres cosas: "
        "las notas de sesión con IA, la agenda, y un dashboard que muestra si el consultorio es rentable"
    ),
    incentivo="acceso anticipado y meses gratis cuando lancemos",
)


def build_system_prompt(
    nombre: str,
    referidor: str,
    genero: str | None = None,
    cfg: DiscoveryConfig = CONFLUR,
) -> str:
    if genero == "M":
        quien = f"un psicólogo llamado {nombre}"
    elif genero == "F":
        quien = f"una psicóloga llamada {nombre}"
    else:
        quien = f"un/a psicólogo/a llamado/a {nombre}"

    return f"""Estás charlando por chat con {quien}, de práctica privada en Argentina. {referidor} nos pasó su contacto.

Tu objetivo es entender cómo es la realidad del consultorio por dentro: qué parte de la gestión les pesa más, cómo lo resuelven hoy, y qué les parecería una solución. No vendés nada en esta charla.

Hay cuatro cosas concretas que querés descubrir, en el orden que surja naturalmente:
1. ¿Qué parte de gestionar el consultorio le resulta más pesada? (notas de sesión, agenda, finanzas u otra)
2. ¿Cómo lo resuelve hoy? ¿Qué funciona y qué no?
3. Al mostrarle la solución, ¿qué le parece? ¿Qué parte le interesa más? Sobre las notas en particular: preguntale si preferiría que la app convierta sus apuntes escritos en notas clínicas completas, o que grabe y transcriba el audio de la sesión directamente.
4. ¿Pagaría por algo así? ¿Cuánto le parece razonable?

Cuando llegue el momento de presentar la solución, describila así: {cfg.descripcion_producto}.
Al final, si hubo interés, ofrecele {cfg.incentivo} y preguntale si querés que le avisemos.

Cómo llevás la conversación:
- Primer mensaje: solo el saludo. "Hola {nombre}, ¿cómo estás? Te escribo porque {referidor} me pasó tu contacto."
- Segundo mensaje: te presentás y hacés el disclosure en una sola oración simple, sin hacerlo un gran momento. Algo así: "Trabajo en Conflur, una app para psicólogos de consultorio. Antes de lanzar queremos entender cómo es la realidad de cerca — esta charla la lleva un asistente con IA. ¿Tenés unos minutos para contarme cómo manejás el lado administrativo del consultorio?"
- Después: una pregunta corta por mensaje. Si algo te resulta interesante, profundizás un poco antes de pasar al siguiente tema.
- Si la persona dice que no quiere charlar con una IA, lo respetás y terminás la conversación. No le ofrezcas pasarla a nadie.

Hablás en español de Argentina: directo, simple, sin palabras raras. Una sola idea por mensaje."""


def discovery_reply(
    history: list[dict],
    *,
    nombre: str,
    referidor: str,
    genero: str | None = None,
    cfg: DiscoveryConfig = CONFLUR,
    client: LLMClient | None = None,
    model: str | None = None,
) -> LLMResult:
    """Dado el historial (turnos user/assistant), produce el próximo mensaje del agente.

    `history` vacío → produce el mensaje de apertura.
    """
    client = client or default_client
    _trigger = {"role": "user", "content": "(Arrancá vos: escribí solo el primer mensaje de apertura.)"}
    # Anthropic exige que el primer mensaje sea 'user'. Si el historial empieza con 'assistant'
    # (mensaje de apertura guardado en la sesión), inyectamos el mismo disparador inicial.
    if not history:
        convo = [_trigger]
    elif history[0]["role"] == "assistant":
        convo = [_trigger, *history]
    else:
        convo = history
    messages = [{"role": "system", "content": build_system_prompt(nombre, referidor, genero, cfg)}, *convo]
    return client.complete(
        messages,
        model=model or settings.DISCOVERY_MODEL,
        max_tokens=300,
        temperature=0.6,
    )


# --- Síntesis (transcript → hallazgos estructurados) ---

_SINTESIS_PROMPT = """Sos un analista. A partir de la transcripción de una charla de descubrimiento
con un/a psicólogo/a, extraé un JSON (en español, valores concisos) con EXACTAMENTE estos campos:
- rol: "solo" | "consultorio_con_equipo" | "desconocido"
- dolores: lista de tags cortos (ej. "las notas se acumulan", "no lleva la cuenta de la plata")
- notas_preferencia: "texto" | "audio" | "indiferente" | null (qué formato prefiere para las notas de sesión — null si no se habló del tema)
- separacion_consultorio_personal: cómo maneja sueldo/caja (texto corto o null)
- reaccion_concepto: qué le resonó / qué pidió (texto corto o null)
- interes: true | false (si quiere que le avisen del lanzamiento)
- contacto: mail/teléfono si lo dejó, o null
- resumen: 1-2 oraciones
Respondé SOLO con el JSON, sin markdown ni texto adicional."""


def _transcript_text(history: list[dict]) -> str:
    etiqueta = {"assistant": "ASISTENTE", "user": "PERSONA"}
    return "\n".join(f"{etiqueta.get(t['role'], t['role']).upper()}: {t['content']}" for t in history)


def synthesize_discovery(
    history: list[dict], *, client: LLMClient | None = None, model: str | None = None,
) -> dict:
    """Extrae hallazgos estructurados de la transcripción."""
    client = client or default_client
    res = client.complete(
        [
            {"role": "system", "content": _SINTESIS_PROMPT},
            {"role": "user", "content": _transcript_text(history)},
        ],
        model=model or settings.DISCOVERY_MODEL,
        max_tokens=600,
        temperature=0.0,
    )
    txt = res.text.strip()
    if txt.startswith("```"):
        txt = txt.strip("`").removeprefix("json").strip()
    return json.loads(txt)
