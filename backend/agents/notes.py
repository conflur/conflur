"""
Agente de notas clínicas — core differentiator.

Convierte los apuntes/bullets del profesional en una nota de evolución clínica
profesional. Principios aplicados:
- Privacidad (P4): el contenido clínico no se loguea; al prompt va solo lo que el
  profesional ingresa + contexto mínimo. Sin datos identificatorios innecesarios.
- Tono (P5): profesional, respetuoso, clínico; no inventa datos (P7) — si falta
  información, no la rellena.
- Modelo configurable por agente (NOTES_MODEL); uso de tokens devuelto para tracking.
"""
from config import settings
from llm.client import LLMClient, LLMResult, default_client

# Reglas comunes a todos los formatos.
_REGLAS_COMUNES = """Usá SOLO la información provista. No inventes síntomas, diagnósticos, fechas ni datos que no estén en los apuntes (si algo no está, no lo incluyas). Redacción profesional y concisa; no agregues encabezados administrativos ni datos personales del paciente. Es un borrador que el profesional revisa y edita antes de guardar."""

SYSTEM_PROMPT = f"""Sos un asistente que redacta notas de evolución clínica para profesionales de salud mental (psicólogos), en español rioplatense, en tono profesional y clínico.

Reglas:
- Redactá una nota de evolución de sesión a partir de los apuntes que te da el profesional.
- {_REGLAS_COMUNES}
- Estructura sugerida: estado/observación, contenido trabajado en la sesión, evolución respecto a objetivos, e indicaciones/plan si surgen de los apuntes."""

# Formato SOAP: estándar clínico estructurado (Subjetivo / Objetivo / Análisis / Plan).
SOAP_SYSTEM_PROMPT = f"""Sos un asistente que redacta notas de evolución clínica en formato SOAP para profesionales de salud mental (psicólogos), en español rioplatense, en tono profesional y clínico.

Estructurá la nota EXACTAMENTE en estas cuatro secciones, cada una con su encabezado markdown:

## Subjetivo (S)
Lo que reporta el paciente desde su experiencia (motivo, síntomas, emociones, vivencias).

## Objetivo (O)
Observaciones clínicas del profesional y resultados de escalas/instrumentos aplicados, si los hubiera.

## Análisis (A)
Integración clínica: evolución respecto a los objetivos, progreso y formulación, en base a lo registrado.

## Plan (P)
Intervenciones para la próxima sesión, tareas o indicaciones, si surgen de los apuntes.

Reglas:
- {_REGLAS_COMUNES}
- Mantené las cuatro secciones SIEMPRE. Si una sección no tiene contenido en los apuntes, escribí "Sin datos registrados en esta sesión." debajo del encabezado, sin inventar."""

FORMATS = ("libre", "soap")


def generate_clinical_note(
    bullets: str,
    *,
    template_type: str = "psychology_session",
    note_format: str = "libre",
    client: LLMClient | None = None,
    model: str | None = None,
    patient_first_name: str | None = None,
) -> LLMResult:
    """Genera el borrador de nota a partir de los bullets del profesional.

    `note_format`: "libre" (nota de evolución corrida) | "soap" (estructurada en
    Subjetivo/Objetivo/Análisis/Plan).
    """
    client = client or default_client
    model = model or settings.NOTES_MODEL

    system_prompt = SOAP_SYSTEM_PROMPT if note_format == "soap" else SYSTEM_PROMPT
    instruccion = "Redactá la nota de evolución en formato SOAP." if note_format == "soap" else "Redactá la nota de evolución clínica."

    contexto = f"Nombre del paciente (solo para redacción, no lo incluyas como dato): {patient_first_name}\n\n" if patient_first_name else ""
    user_prompt = (
        f"{contexto}Apuntes de la sesión (tipo: {template_type}):\n{bullets}\n\n"
        f"{instruccion}"
    )

    return client.complete(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        model=model,
        max_tokens=1024,
        temperature=0.3,
    )
