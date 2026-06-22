"""
Esquemas de ficha clínica por especialidad + validador.

El esquema define los campos clínicos EXTENDIDOS (más allá de los demográficos
que ya viven en Patient: nombre, contacto, etc.). Los valores de la ficha de un
paciente se guardan como JSONB validado contra este esquema (ver SEB-176).

Tipos de campo soportados:
  text · textarea · date · number · boolean · select (con options) · multiselect

Estructura del esquema:
  { "version": int, "sections": [ {"key","label","fields":[ {"key","label","type",...} ]} ] }
"""

# Esquema base de la ficha del psicólogo. Basado en investigación de historia
# clínica psicológica + Ley 26.529. 'riesgo_suicida' es campo de primera clase.
PSICOLOGIA_FICHA_SCHEMA = {
    "version": 1,
    "sections": [
        {
            "key": "identificacion",
            "label": "Identificación",
            "fields": [
                {"key": "obra_social", "label": "Obra social / prepaga", "type": "text"},
                {"key": "nro_afiliado", "label": "N° de afiliado", "type": "text"},
                {"key": "ocupacion", "label": "Ocupación", "type": "text"},
                {"key": "nivel_educativo", "label": "Nivel educativo", "type": "text"},
                {"key": "estado_civil", "label": "Estado civil", "type": "text"},
            ],
        },
        {
            "key": "motivo_consulta",
            "label": "Motivo de consulta",
            "fields": [
                {"key": "descripcion", "label": "Descripción (textual)", "type": "textarea", "required": True},
                {"key": "inicio_sintomas", "label": "Inicio de síntomas", "type": "date"},
                {"key": "desencadenantes", "label": "Desencadenantes", "type": "textarea"},
                {"key": "derivacion", "label": "Derivación", "type": "text"},
            ],
        },
        {
            "key": "anamnesis",
            "label": "Anamnesis",
            "fields": [
                {"key": "historia_desarrollo", "label": "Historia del desarrollo", "type": "textarea"},
                {"key": "antecedentes_personales", "label": "Antecedentes personales (médicos/psi)", "type": "textarea"},
                {"key": "medicacion_actual", "label": "Medicación actual", "type": "textarea"},
                {"key": "tratamientos_previos", "label": "Tratamientos previos", "type": "textarea"},
                {"key": "consumo_sustancias", "label": "Consumo de sustancias", "type": "textarea"},
                {"key": "antecedentes_familiares", "label": "Antecedentes familiares (salud mental)", "type": "textarea"},
            ],
        },
        {
            "key": "riesgo",
            "label": "Evaluación de riesgo",
            "fields": [
                {
                    "key": "riesgo_suicida",
                    "label": "Riesgo suicida",
                    "type": "select",
                    "options": ["sin_riesgo", "bajo", "moderado", "alto"],
                    "required": True,
                },
                {"key": "riesgo_notas", "label": "Notas de riesgo", "type": "textarea"},
            ],
        },
        {
            "key": "perfil_social",
            "label": "Perfil social y vincular",
            "fields": [
                {"key": "vinculos_actuales", "label": "Vínculos actuales", "type": "textarea"},
                {"key": "red_apoyo", "label": "Red de apoyo", "type": "textarea"},
                {"key": "situacion_laboral", "label": "Situación laboral", "type": "text"},
                {"key": "estresores", "label": "Estresores psicosociales", "type": "textarea"},
            ],
        },
        {
            "key": "evaluacion",
            "label": "Evaluación inicial",
            "fields": [
                {"key": "estado_mental", "label": "Estado mental / observaciones", "type": "textarea"},
                {"key": "tests_aplicados", "label": "Tests aplicados", "type": "textarea"},
            ],
        },
        {
            "key": "diagnostico",
            "label": "Diagnóstico y plan",
            "fields": [
                {"key": "impresion_diagnostica", "label": "Impresión diagnóstica (DSM-5/CIE)", "type": "text"},
                {"key": "es_presuntivo", "label": "Presuntivo", "type": "boolean"},
                {"key": "tipo_terapia", "label": "Tipo de terapia", "type": "text"},
                {"key": "frecuencia", "label": "Frecuencia", "type": "text"},
                {"key": "objetivos", "label": "Objetivos terapéuticos", "type": "textarea"},
            ],
        },
    ],
}


# Registro de esquemas semilla por especialidad (lo usa la migración de seed).
SEED_SPECIALTIES = {
    "psicologia": {"name": "Psicología", "ficha_schema": PSICOLOGIA_FICHA_SCHEMA},
}

_SCALAR_VALIDATORS = {
    "text": lambda v: isinstance(v, str),
    "textarea": lambda v: isinstance(v, str),
    "date": lambda v: isinstance(v, str),  # ISO date string
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
}


def validate_ficha(values: dict, schema: dict) -> list[str]:
    """
    Valida los valores de una ficha contra el esquema. Devuelve lista de errores
    (vacía = válido). No exige que estén todos los campos, salvo los `required`.
    """
    errors: list[str] = []
    if not isinstance(values, dict):
        return ["La ficha debe ser un objeto"]

    field_defs: dict[str, dict] = {}
    for section in schema.get("sections", []):
        for f in section.get("fields", []):
            field_defs[f["key"]] = f

    # Campos requeridos presentes y no vacíos
    for key, f in field_defs.items():
        if f.get("required") and (key not in values or values[key] in (None, "")):
            errors.append(f"Campo requerido faltante: {key}")

    # Validación de cada valor provisto
    for key, value in values.items():
        if key not in field_defs:
            errors.append(f"Campo desconocido: {key}")
            continue
        if value is None:
            continue
        f = field_defs[key]
        ftype = f["type"]
        if ftype in ("select",):
            if value not in f.get("options", []):
                errors.append(f"Valor inválido para {key}: {value}")
        elif ftype == "multiselect":
            opts = f.get("options", [])
            if not isinstance(value, list) or any(v not in opts for v in value):
                errors.append(f"Valor inválido para {key}")
        else:
            validator = _SCALAR_VALIDATORS.get(ftype)
            if validator and not validator(value):
                errors.append(f"Tipo inválido para {key} (esperado {ftype})")

    return errors
