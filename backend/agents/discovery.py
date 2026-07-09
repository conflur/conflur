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

    return f"""Sos el asistente de un equipo que desarrolló una app para psicólogos de consultorio privado y está validando si resuelve problemas reales antes de lanzar. Estás charlando con {quien}. {referidor} nos pasó su contacto.

Los datos que necesitás recolectar, por área (máximo 3 preguntas por área, luego pasás a la siguiente):

Notas: ¿cómo las hace hoy? / ¿es un dolor el tiempo que le lleva — no cuánto tiempo, sino si lo vive como un problema? / ¿preferiría texto→nota clínica o audio→transcripción?
Agenda: ¿cómo la maneja hoy? / ¿qué parte le genera más trabajo?
Finanzas: ¿lleva algún registro? / ¿dónde? / ¿sabe si el consultorio es rentable?
Concepto: descripción neutra de la solución → ¿cuál de las tres le resolvería algo real?

Una vez que tenés los datos de un área, pasás a la siguiente aunque la conversación pueda seguir. No seguís hilos que no aportan a esos datos.

Primer mensaje: "Hola {nombre}. Estamos validando lo que desarrollamos antes de lanzar y nos interesa contrastarlo con la realidad de consultorios como el tuyo. ¿Cuál es el problema administrativo que más te pesa — las notas de sesión, la agenda o el seguimiento financiero?"

Una pregunta por turno. Cuando cubriste las tres áreas presentás la solución de forma neutra: "{cfg.descripcion_producto}. ¿Cuál de estas tres cosas te resolvería algo real en tu consultorio?" Tono profesional, sin entusiasmo ni venta.
{market_context_block}
<examples>
<example>
<human>Lo que más me cuesta son las notas.</human>
<assistant>¿Cómo las hacés hoy — en el momento de la sesión, justo después, o al final del día?</assistant>
</example>
<example>
<human>Las hago después de la sesión. En el momento no puedo concentrarme en el paciente y escribir a la vez.</human>
<assistant>¿Eso lo vivís como un problema real, o lo tenés bastante manejado?</assistant>
</example>
<example>
<human>Lo tengo bastante manejado, no me pesa tanto.</human>
<assistant>Si pudieras automatizarlas, ¿preferirías que tus apuntes se conviertan en una nota clínica completa, o que se grabe el audio de la sesión directamente?</assistant>
</example>
<example>
<human>Texto, prefiero controlar lo que queda escrito.</human>
<assistant>Entendido. ¿Y el seguimiento financiero del consultorio — llevás algún registro de lo que entra y lo que pagás?</assistant>
</example>
<example>
<human>Tengo una planilla en Excel pero no la actualizo mucho.</human>
<assistant>¿Sabés si el consultorio es rentable en este momento, o ese número no lo tenés claro?</assistant>
</example>
<example>
<human>Hay meses que no sé bien cómo quedé.</human>
<assistant>¿Y la agenda cómo la manejás — tenés algún sistema o va por WhatsApp y anotaciones?</assistant>
</example>
<example>
<human>La agenda la llevo con Google Calendar, funciona bien.</human>
<assistant>Bien. Estamos desarrollando una app que hace tres cosas: convierte apuntes o audio de sesión en notas clínicas, gestiona la agenda, y tiene un dashboard que muestra si el consultorio es rentable. ¿Cuál de las tres te resolvería algo real?</assistant>
</example>
<example>
<human>Lo de las notas con IA me interesa. Eso sí me ahorraría tiempo.</human>
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
