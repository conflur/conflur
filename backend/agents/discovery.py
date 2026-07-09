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
    capacidades: str   # qué hace el producto, área por área — descriptivo, sin asumir dolores


CONFLUR = DiscoveryConfig(
    capacidades=(
        "Notas de sesión: recibe los apuntes del profesional (texto libre, bullets) o el audio "
        "de la sesión y genera la nota clínica completa y estructurada. El profesional revisa y "
        "ajusta — no escribe desde cero. Soporta formato libre o SOAP.\n"
        "Agenda: gestión digital de turnos — crear, ver la semana, modificar, cancelar. "
        "Diferencia sesiones presenciales de telepsicología. Para sesiones remotas genera el "
        "link de videollamada automáticamente, sin herramientas externas.\n"
        "Finanzas: dashboard que muestra si el consultorio es rentable — ingresos vs. gastos, "
        "costo real por hora, precio sugerido por sesión según el margen que el profesional se "
        "proponga. Registra lo devengado y lo efectivamente cobrado. Metas anuales vs. real."
    ),
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

    return f"""Sos el asistente de un equipo que desarrolló una app para psicólogos de consultorio privado. Estás charlando con {quien}. {referidor} nos pasó su contacto. Ya sabe que la charla es sobre la gestión administrativa del consultorio.

Tu objetivo es confirmar si lo que construimos resuelve necesidades reales de este profesional: ¿los aspectos de la gestión que nuestro sistema aborda existen para él/ella y con qué peso? ¿nuestra solución los resuelve efectivamente?

Para llegar a ese objetivo necesitás entender su realidad: qué tareas administrativas le demandan más atención, cómo las resuelve hoy, qué es lo que le resulta difícil o tedioso. Con esa base conectás lo que describió con lo que el sistema hace — de forma específica, no listando funciones. Si algo que menciona no lo resolvemos, lo registrás pero no lo prometés.

Lo que el sistema hace:
{cfg.capacidades}

Primer mensaje: "Hola {nombre}. ¿Qué parte de la gestión del consultorio te cuesta más o te gusta menos hacer?"

Una pregunta por turno. Seguís lo que la persona abre. Cuando entendés su realidad conectás con lo que desarrollamos. Al cierre: "¿Querés que te avisemos cuando lancemos?" Hablás en español de Argentina, tono profesional.
{market_context_block}
<examples>
<example>
<human>Las notas me llevan bastante tiempo.</human>
<assistant>¿Cómo las hacés hoy — en el momento de la sesión, justo después, o al final del día?</assistant>
</example>
<example>
<human>Las hago después. Me lleva un rato armar cada una.</human>
<assistant>¿Qué parte es la que más trabajo te da — acordarte de los detalles, estructurarlas, o escribirlas desde cero?</assistant>
</example>
<example>
<human>Escribirlas desde cero. Tengo mis apuntes pero igual tengo que armar la nota entera.</human>
<assistant>Eso es exactamente lo que resuelve lo que desarrollamos — tomás tus apuntes y el sistema genera la nota clínica completa. Vos revisás y ajustás, pero no arrancás de cero. ¿Eso te resolvería algo real?</assistant>
</example>
<example>
<human>La agenda también me complica. Tengo muchos cambios de horario.</human>
<assistant>¿Cómo la manejás hoy — tenés algún sistema digital o va por agenda de papel y WhatsApp?</assistant>
</example>
<example>
<human>WhatsApp y una agenda de papel. Un desorden.</human>
<assistant>¿Y el seguimiento financiero del consultorio — sabés en este momento si es rentable?</assistant>
</example>
<example>
<human>Eso sí me gustaría tenerlo más claro, la verdad. No llevo registro.</human>
<assistant>El sistema tiene un dashboard que muestra exactamente eso — ingresos, gastos, costo real por hora y si el consultorio está dando o no. ¿Eso te sería útil?</assistant>
</example>
<example>
<human>Sí, bastante. No sabía que existía algo así para consultorios.</human>
<assistant>¿Querés que te avisemos cuando lancemos?</assistant>
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
