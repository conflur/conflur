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

SYSTEM_PROMPT = """Sos un asistente que redacta notas de evolución clínica para profesionales de salud mental (psicólogos), en español rioplatense, en tono profesional y clínico.

Reglas:
- Redactá una nota de evolución de sesión a partir de los apuntes que te da el profesional.
- Usá SOLO la información provista. No inventes síntomas, diagnósticos, fechas ni datos que no estén en los apuntes (si algo no está, no lo incluyas).
- Estructura sugerida: estado/observación, contenido trabajado en la sesión, evolución respecto a objetivos, e indicaciones/plan si surgen de los apuntes.
- Redacción profesional y concisa; no agregues encabezados administrativos ni datos personales del paciente.
- Es un borrador que el profesional revisa y edita antes de guardar."""


def generate_clinical_note(
    bullets: str,
    *,
    template_type: str = "psychology_session",
    client: LLMClient | None = None,
    model: str | None = None,
    patient_first_name: str | None = None,
) -> LLMResult:
    """Genera el borrador de nota a partir de los bullets del profesional."""
    client = client or default_client
    model = model or settings.NOTES_MODEL

    contexto = f"Nombre del paciente (solo para redacción, no lo incluyas como dato): {patient_first_name}\n\n" if patient_first_name else ""
    user_prompt = (
        f"{contexto}Apuntes de la sesión (tipo: {template_type}):\n{bullets}\n\n"
        "Redactá la nota de evolución clínica."
    )

    return client.complete(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        model=model,
        max_tokens=1024,
        temperature=0.3,
    )
