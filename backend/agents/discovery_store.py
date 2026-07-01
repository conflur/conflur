"""
Persistencia y consolidación de hallazgos del Agente de Descubrimiento (Fase 2b).

Guarda cada charla (hallazgos JSONB + transcript) en la DB de la instancia (tenant-scoped, RLS) y
consolida across charlas → hallazgos agregados que alimentan `docs/capa-profesional.md`. Datos de
instancia, aislados; ingestables a la KM semántica compartida más adelante.
"""
import uuid
from collections import Counter

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import DiscoveryFinding


async def save_finding(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    findings: dict,
    *,
    transcript: str | None = None,
    referidor: str | None = None,
) -> DiscoveryFinding:
    """Persiste los hallazgos de una charla (materializa rol/interes/contacto para consolidar)."""
    row = DiscoveryFinding(
        tenant_id=tenant_id,
        findings=findings,
        transcript=transcript,
        referidor=referidor,
        rol=findings.get("rol"),
        interes=findings.get("interes"),
        contacto=findings.get("contacto"),
    )
    session.add(row)
    await session.commit()
    return row


async def consolidate_findings(session: AsyncSession) -> dict:
    """Agrega los hallazgos del consultorio/instancia (RLS ya filtra por tenant)."""
    rows = list(await session.scalars(select(DiscoveryFinding)))
    return aggregate_findings(rows)


def aggregate_findings(rows) -> dict:
    """Lógica pura de consolidación (rows: objetos con .rol/.interes/.contacto/.findings)."""
    total = len(rows)

    por_rol: Counter = Counter()
    dolores: Counter = Counter()
    turno_cita: Counter = Counter()
    paciente_consultante: Counter = Counter()
    nombre_seccion: Counter = Counter()
    interesados = 0
    contactos: list[str] = []

    for r in rows:
        f = r.findings or {}
        if r.rol:
            por_rol[r.rol] += 1
        for d in (f.get("dolores") or []):
            dolores[str(d).strip().lower()] += 1
        terms = f.get("terminos") or {}
        if terms.get("turno_o_cita"):
            turno_cita[str(terms["turno_o_cita"]).strip().lower()] += 1
        if terms.get("paciente_o_consultante"):
            paciente_consultante[str(terms["paciente_o_consultante"]).strip().lower()] += 1
        if terms.get("nombre_seccion_finanzas"):
            nombre_seccion[str(terms["nombre_seccion_finanzas"]).strip().lower()] += 1
        if r.interes:
            interesados += 1
        if r.contacto:
            contactos.append(r.contacto)

    return {
        "total_charlas": total,
        "por_rol": dict(por_rol),
        "dolores_frecuentes": dolores.most_common(10),
        "terminos": {
            "turno_vs_cita": dict(turno_cita),
            "paciente_vs_consultante": dict(paciente_consultante),
            "nombre_seccion_finanzas": dict(nombre_seccion),
        },
        "interesados": interesados,
        "pct_interes": round(interesados / total * 100, 1) if total else None,
        "contactos": contactos,
    }
