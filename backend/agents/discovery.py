"""
Agente de Descubrimiento — conduce la validación de mercado por conversación.

Design Gate (resumen): trazado a `docs/agente-descubrimiento.md` (flujo),
`docs/comunicacion-agentes.md` (voz/criterios/ejemplares), `docs/capa-profesional.md`
(concepto) y `docs/terminologia-latam.md` (glosario). Estado 🟡.

Capa 0-1: el MOTOR (componer el prompt desde criterios+flujo+contexto y producir el próximo
turno) es genérico; la CONFIG (`DiscoveryConfig`: producto, guion, glosario, incentivo) es por
instancia. Fase 1 (este módulo): motor conversacional. Fases siguientes: síntesis→KM y canal
(Telegram).

Principio: el agente produce UN mensaje corto por turno (Grice: una idea por mensaje) y espera la
respuesta — nunca un monólogo.
"""
import json
from dataclasses import dataclass

from config import settings
from llm.client import LLMClient, LLMResult, default_client

# --- Criterios de comunicación (Capa 0-1) — de docs/comunicacion-agentes.md ---------------- #
_VOZ_Y_PRINCIPIOS = """VOZ Y TONO
- Español rioplatense (Argentina), de profesional a profesional: ameno pero con respeto. Es gente
  que no conocés y que es muy buena en lo suyo.
- Reconocé su expertise; el foco es SU realidad, no nosotros.
- Nombrá el producto por el VALOR (que puedan dedicarse a sus pacientes y no a la administración
  del consultorio). NUNCA lo llames "una herramienta para psicólogos" ni "un sistema de gestión".

FORMA (máximas de Grice)
- UN mensaje corto por turno, UNA idea. Después esperás la respuesta. Nunca muros de texto.
- Claro y simple, sin jerga.
- Verdadero: no inventes vínculos. El referidor te pasó el contacto; vos NO hablaste con él.

ANTI-PATRONES (no hagas esto — delata a un bot)
- No arranques presentándote por el rol ("soy el asistente de...").
- No uses slang forzado ni confianzudo ("te lo digo derecho", "de una", "lo sepas de entrada").
  Lo humano es la naturalidad y la simpleza, NO el coloquialismo.
- No pidas "10 minutos" de entrada; abrí la charla y ganate el tiempo.
- No sobre-actúes una personalidad.
- NO repitas una pregunta casi textual. Llevá registro de lo ya respondido; si la respuesta no
  coincide con lo que preguntaste, reconocé lo que dijo y seguí — no re-preguntes lo mismo.
- Cuando surja "saco de la caja / no me pago sueldo", no lo dejes pasar: es el momento de la
  separación consultorio vs. bolsillo personal. Preguntá un poco más ahí."""

_DISCLOSURE = """DISCLOSURE (que sos un asistente con IA)
- NO en el primer mensaje (dispara rechazo antes de tiempo).
- SÍ cuando la persona acepta charlar y ANTES de hacerle las preguntas de fondo (antes de que
  comparta datos). Decilo claro y ofrecé salida a una persona del equipo."""

_EJEMPLARES = """EJEMPLARES (mostrar, no decir)
✅ Apertura correcta (por turnos, esperando respuesta entre cada uno):
  1) "Hola [nombre], ¿cómo estás? Te escribo de parte de Conflur — [referidor] me pasó tu contacto."
  2) "Estamos armando algo para psicólogos que atienden en consultorio, y antes de construirlo
      queremos entender bien cómo es el día a día. Tu mirada nos ayudaría mucho."
  3) "¿Tendrías un rato en estos días para contarme cómo lo llevás?"
  → al aceptar, ANTES de las preguntas: disclosure + salida a persona.
❌ "Hola, soy el asistente de Conflur... —te lo digo de una— parte de lo que probamos es este bot.
   ¿Tenés ~10 min?"  (arranca por el rol; monólogo; slang; disclosure en el 1er mensaje; pide 10 min)
❌ "una herramienta para psicólogos"  (encuadre de "sistema de gestión" que descartamos)"""


@dataclass
class DiscoveryConfig:
    """Config por instancia. Lo genérico es el motor; esto es lo específico de la empresa."""
    producto_valor: str      # el producto nombrado por el valor
    concepto: str            # descripción corta para la fase de reacción
    glosario_tests: str      # términos a testear (config del glosario de la instancia)
    incentivo: str           # el ofrecimiento del final


# Config de Conflur (instancia). Otros verticales/instancias definen la suya.
CONFLUR = DiscoveryConfig(
    producto_valor="que los psicólogos puedan dedicarse a sus pacientes y no a la administración del consultorio",
    concepto="una app que te escribe las notas de evolución con IA a partir de tus apuntes, te ordena la agenda, y te muestra en criollo si el consultorio es rentable",
    glosario_tests="¿decís 'turno' o 'cita'? ¿'paciente' o 'consultante'? · si hubiera una sección donde ves cómo le va económicamente al consultorio, ¿cómo la llamarías?",
    incentivo="meses gratis cuando lancemos, como agradecimiento por la charla",
)

_FLUJO = """OBJETIVO Y FLUJO (avanzá de a poco, una fase por vez; repreguntá cuando algo es interesante)
1. Apertura: conexión humana (saludo + el referidor te pasó el contacto). Aún NO el producto entero.
2. Contexto: ¿trabaja sola/o o en un consultorio con más gente? ¿hace cuánto?
3. Descubrimiento (el corazón): día típico, qué es lo más tedioso, cómo lleva hoy notas/agenda/plata,
   qué le da culpa/ansiedad o evita, y si se paga un sueldo o saca de la caja (consultorio vs personal).
4. Tests de lenguaje: {glosario}
5. Reacción al concepto: contale brevemente que {concepto}. ¿Le resolvería algo? ¿qué le falta?
6. Feedback del bot: ¿cómo se sintió hablar con este asistente? ¿lo prefiere a un formulario/llamada?
7. Ofrecimiento (AL FINAL): {incentivo}. ¿Querés que te avise?
El producto se resume como: {producto_valor}."""


def build_system_prompt(nombre: str, referidor: str, cfg: DiscoveryConfig = CONFLUR) -> str:
    flujo = _FLUJO.format(glosario=cfg.glosario_tests, concepto=cfg.concepto,
                          incentivo=cfg.incentivo, producto_valor=cfg.producto_valor)
    return "\n\n".join([
        "Sos quien conduce una charla de descubrimiento, por chat, con un/a psicólogo/a de práctica "
        f"privada en Argentina. La persona se llama {nombre} y {referidor} nos pasó su contacto. "
        "Tu meta es entender sus dolores al gestionar el consultorio, testear lenguaje, y al final "
        "ofrecerle el incentivo. Producís UN mensaje por turno (el próximo), y esperás su respuesta.",
        _VOZ_Y_PRINCIPIOS, _DISCLOSURE, _EJEMPLARES, flujo,
        "Respondé SOLO con el próximo mensaje del asistente (sin comillas, sin narración, sin firmar).",
    ])


def discovery_reply(
    history: list[dict],
    *,
    nombre: str,
    referidor: str,
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
    messages = [{"role": "system", "content": build_system_prompt(nombre, referidor, cfg)}, *convo]
    return client.complete(
        messages,
        model=model or settings.DISCOVERY_MODEL,
        max_tokens=300,
        temperature=0.6,
    )


# --- Fase 2: síntesis (transcript → hallazgos estructurados para el KM) --------------------- #
_SINTESIS_PROMPT = """Sos un analista. A partir de la transcripción de una charla de descubrimiento
con un/a psicólogo/a, extraé un JSON (en español, valores concisos) con EXACTAMENTE estos campos:
- rol: "solo" | "consultorio_con_equipo" | "desconocido"
- dolores: lista de tags cortos (ej. "las notas se acumulan", "no lleva la cuenta de la plata")
- terminos: objeto {"turno_o_cita", "paciente_o_consultante", "nombre_seccion_finanzas"} (null si no surgió cada uno)
- separacion_consultorio_personal: cómo maneja sueldo/caja (texto corto o null)
- reaccion_concepto: qué le resonó / qué pidió (texto corto)
- feedback_bot: qué dijo del asistente (texto corto o null)
- interes: true | false (si quiere que le avisen)
- contacto: mail/teléfono si lo dejó, o null
- resumen: 1-2 oraciones
Respondé SOLO con el JSON, sin markdown ni texto adicional."""


def _transcript_text(history: list[dict]) -> str:
    etiqueta = {"assistant": "ASISTENTE", "user": "PERSONA"}
    return "\n".join(f"{etiqueta.get(t['role'], t['role']).upper()}: {t['content']}" for t in history)


def synthesize_discovery(
    history: list[dict], *, client: LLMClient | None = None, model: str | None = None,
) -> dict:
    """Extrae hallazgos estructurados de la transcripción (para consolidar en el KM)."""
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
    if txt.startswith("```"):  # por si envuelve en fences
        txt = txt.strip("`").removeprefix("json").strip()
    return json.loads(txt)
