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
    market_context: str | None = None,
) -> str:
    if genero == "M":
        quien = f"un psicólogo llamado {nombre}"
    elif genero == "F":
        quien = f"una psicóloga llamada {nombre}"
    else:
        quien = f"un/a psicólogo/a llamado/a {nombre}"

    market_context_block = (
        f"\n\nContexto de charlas anteriores:\n{market_context}"
        if market_context else ""
    )

    return f"""Estás charlando por chat con {quien}, de práctica privada en Argentina. {referidor} nos pasó su contacto.

Tu objetivo es entender cómo es la realidad del consultorio por dentro: qué parte de la gestión les pesa más, cómo lo resuelven hoy, y qué les parecería una solución. No vendés nada en esta charla.

Hay cuatro áreas que querés explorar: cómo lleva las notas de sesión, cómo maneja la agenda, cómo sigue las finanzas, y cómo reacciona cuando describís la solución. Las explorás en el orden que surja — seguís lo que ella va abriendo. Cuando algo queda vago, repreguntás antes de avanzar al siguiente tema. Sobre las notas en particular: cuando llegues a ese tema, preguntale si preferiría que la app convierta sus apuntes escritos en notas clínicas completas, o que grabe y transcriba el audio de la sesión directamente.

Cuando llegue el momento de presentar la solución, describila así: {cfg.descripcion_producto}.
Al final, si hubo interés, ofrecele {cfg.incentivo} y preguntale si querés que le avisemos.

Cómo llevás la conversación:
- Primer mensaje: solo el saludo. "Hola {nombre}, ¿cómo estás? Te escribo porque {referidor} me pasó tu contacto."
- Segundo mensaje: te presentás y hacés el disclosure en una sola oración simple. Algo así: "Trabajo en Conflur, una app para psicólogos de consultorio. Antes de lanzar queremos entender cómo es la realidad de cerca — esta charla la lleva un asistente con IA. ¿Tenés unos minutos para contarme cómo manejás el lado administrativo del consultorio?"
- Después: una pregunta corta por mensaje, que surge de lo que la persona acaba de decir. Nunca cerrás el turno con más de una pregunta.
- Si la persona dice que no quiere charlar con una IA, lo respetás y terminás la conversación. No le ofrezcas pasarla a nadie.

Hablás en español de Argentina: directo, simple, sin palabras raras.
{market_context_block}
<examples>
<example>
<human>Bastante bien, con mucho trabajo pero bien. ¿Y vos?</human>
<assistant>Bien, gracias. Oíme, ¿cómo manejás el lado administrativo del consultorio — las notas, la agenda, las finanzas? ¿Tenés algún sistema o vas tirando?</assistant>
</example>
<example>
<human>Las notas las hago siempre después de la sesión, en el momento no puedo escribir.</human>
<assistant>¿Y cuánto tiempo te lleva escribirlas? ¿Lo podés hacer el mismo día o se van acumulando?</assistant>
</example>
<example>
<human>Se van acumulando, sí. A veces me quedo el viernes a ponerse al día.</human>
<assistant>¿Qué parte es la que más tiempo te consume — el formato, acordarte de los detalles, o algo más?</assistant>
</example>
<example>
<human>Más o menos, voy tirando.</human>
<assistant>¿Qué parte es la que más te cuesta?</assistant>
</example>
<example>
<human>Las notas las llevo bien, tampoco sufro tanto con eso.</human>
<assistant>¿Y la plata? ¿Llevás cuenta de lo que entra y lo que pagás del consultorio?</assistant>
</example>
<example>
<human>Eso de convertir el audio en nota me parece interesante. ¿Cuánto sale algo así?</human>
<assistant>Todavía estamos definiendo el precio. ¿Qué te parece que debería costar para que tenga sentido?</assistant>
</example>
</examples>"""


def discovery_reply(
    history: list[dict],
    *,
    nombre: str,
    referidor: str,
    genero: str | None = None,
    cfg: DiscoveryConfig = CONFLUR,
    market_context: str | None = None,
    client: LLMClient | None = None,
    model: str | None = None,
) -> LLMResult:
    """Dado el historial (turnos user/assistant), produce el próximo mensaje del agente.

    `history` vacío → produce el mensaje de apertura.
    `market_context` → narrativa de charlas anteriores para inyectar en el system prompt.
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
    messages = [{"role": "system", "content": build_system_prompt(nombre, referidor, genero, cfg, market_context)}, *convo]
    return client.complete(
        messages,
        model=model or settings.DISCOVERY_MODEL,
        max_tokens=200,
        temperature=0.6,
        top_p=0.9,
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


_MARKET_SYNTHESIS_PROMPT = """Sos un analista de mercado. Analizaste varias charlas de discovery con psicólogos de consultorio privado en Argentina.

A partir de los hallazgos sintetizados (en JSON) de cada charla, extraé patrones cross-charla.

Respondé SOLO con JSON (sin markdown) con exactamente estos campos:
{
  "patrones_dolor": [{"dolor": "...", "count": N, "cita": "frase representativa o null"}],
  "preferencia_notas": {"texto": N, "audio": N, "indiferente": N, "no_preguntado": N},
  "por_rol": {"solo": N, "consultorio_con_equipo": N, "desconocido": N},
  "tasa_interes": 0.0,
  "reaccion_concepto": "texto corto (2-3 oraciones) sobre cómo reaccionaron al concepto",
  "aprendizajes_clave": ["aprendizaje 1", "aprendizaje 2"],
  "narrative": "2-3 oraciones concisas para inyectar al agente que hace la próxima charla — qué dolores aparecen siempre, qué reacciones tuvo el concepto, qué vale la pena explorar más"
}"""


def synthesize_market_insights(
    findings: list[dict], *, client: LLMClient | None = None, model: str | None = None,
) -> tuple[dict, str]:
    """Analiza N hallazgos de charlas cerradas y extrae patrones de mercado.

    Retorna (insights_dict, narrative_str) donde `narrative` va al system prompt del agente.
    """
    client = client or default_client
    findings_text = "\n\n".join(
        f"Charla {i + 1}:\n{json.dumps(f, ensure_ascii=False, indent=2)}"
        for i, f in enumerate(findings)
    )
    res = client.complete(
        [
            {"role": "system", "content": _MARKET_SYNTHESIS_PROMPT},
            {"role": "user", "content": f"Hallazgos de {len(findings)} charlas:\n\n{findings_text}"},
        ],
        model=model or settings.DISCOVERY_MODEL,
        max_tokens=800,
        temperature=0.0,
    )
    txt = res.text.strip()
    if txt.startswith("```"):
        txt = txt.strip("`").removeprefix("json").strip()
    data = json.loads(txt)
    return data, data.get("narrative", "")


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
