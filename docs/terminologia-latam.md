# Terminología — práctica psicológica privada en LATAM

> **Estado: BORRADOR para validar.** Fundamentado en fuentes reales (colegios de psicólogos,
> normativa y software del rubro en AR/MX/CO — ver §Fuentes). Sebas lo valida y lo cruza con su
> propia investigación. Una vez validado, es la **fuente canónica** de los textos de la app (UI copy)
> y la **base de la capacitación**.
>
> **Alcance:** primer vertical = psicólogos; primer mercado = Argentina; idioma = español LATAM.
> Criterio: elegir un término primario por concepto + registrar las variantes regionales, para que
> los textos sean **swappables por región** (encaja con el modelo de skins verticales).

---

## Cómo leer este glosario

- **Término app (recomendado):** el que conviene usar en la UI hoy.
- **Variantes regionales:** lo que se usa en cada país; útil para capacitación y para una futura
  localización por mercado.
- **Notas:** matices legales o de uso que importan.

---

## 1. Núcleo clínico

| Concepto | Término app (recomendado) | Variantes regionales | Notas |
|---|---|---|---|
| Persona que se atiende | **Paciente** | `consultante` (AR, tradición psicoanalítica) · `cliente` (enfoques humanistas) | "Paciente" es el más universal y el que usan los colegios y el software del rubro. "Consultante" es válido y preferido por parte del campo psi argentino → candidato a **opción configurable por profesional** (ver §Decisiones). |
| Registro clínico completo (legal) | **Historia clínica** | `expediente clínico` (MX, NOM-004-SSA3-2012) · `historia clínica` (AR Ley 26.529, CO Res. 1995) | Es el artefacto **legalmente obligatorio**. En MX se llama *expediente clínico*. Es el "todo": datos + ficha + evolución. |
| Datos estructurados de admisión | **Ficha** (o *ficha clínica*) | `ficha de admisión` · `anamnesis` · `historia` | En la app, la "ficha" es el formulario estructurado por esquema. Es **parte** de la historia clínica, no su sinónimo. |
| Nota de cada sesión | **Nota de evolución** (o *evolución*) | `nota de sesión` · `evolución` · `seguimiento` | "Evolución" es el término formal dentro de la HC para el registro del progreso sesión a sesión. La app hoy dice "nota" → considerar "nota de evolución". |
| Encuentro terapéutico | **Sesión** | universal (45–60 min típico) | Pan-LATAM. Sin conflicto. |
| Primera atención | **Primera consulta** (o *entrevista de admisión*) | `consulta inicial` (MX) · `consulta de admisión` (AR) | Las siguientes en MX se llaman *consultas subsecuentes*; en general, *sesiones de seguimiento*. |

## 2. Agenda

| Concepto | Término app (recomendado) | Variantes regionales | Notas |
|---|---|---|---|
| Cita agendada | **Turno** *(decisión pendiente, ver §Decisiones)* | `turno` (AR) · `cita` (MX, CO, PE, CL informal "hora") | **El más divergente.** "Turno" es fuertemente argentino; "cita" es el más pan-LATAM. La app usa "turno" hoy. |
| Estado: agendado | **Agendado** | `programado` · `pendiente` | |
| Estado: realizado | **Realizado** | `atendido` · `completado` | |
| Estado: no asistió | **No asistió** | `ausente` · `inasistencia` | |
| Estado: cancelado | **Cancelado** | — | |
| Lugar de atención | **Consultorio** | pan-LATAM | Sin conflicto. |

## 3. Finanzas y administración

| Concepto | Término app (recomendado) | Variantes regionales | Notas |
|---|---|---|---|
| Lo que cobra el profesional | **Honorarios** | `honorarios` (AR/MX) · `aranceles` (AR, formal/colegios) · `tarifa` (CO) | "Honorarios" es pan-LATAM. En AR los colegios publican **HMS** (Honorarios Mínimos Sugeridos). |
| Valor de referencia del colegio | **Honorario sugerido** | `HMS` (AR) · `arancel mínimo` | Dato AR; útil para el módulo de precio sugerido. |
| Cobertura de salud del paciente | **Cobertura** (genérico) | `obra social` / `prepaga` (AR) · `EPS` / `medicina prepagada` (CO) · `seguro` / `aseguradora` (MX) | Muy divergente. Usar el genérico "cobertura" en la UI y el término local como dato/etiqueta. |
| Matrícula del profesional | **Matrícula** | `matrícula profesional` (AR) · `cédula profesional` (MX) · `tarjeta profesional` (CO) | En MX la *cédula profesional* es **obligatoria en cada nota clínica**. |
| Facturación al paciente | **Comprobante / Factura** | `factura` · `recibo` · ARCA/AFIP (AR), CFDI (MX), DIAN (CO) | Ya cubierto por SEB-180 (capa país-agnóstica). |

## 4. Normativa por país (para capacitación y compliance)

| País | Historia clínica | Datos personales |
|---|---|---|
| Argentina | Ley 26.529 (HC, retención 10 años) | Ley 25.326 |
| México | NOM-004-SSA3-2012 (expediente clínico) | LFPDPPP |
| Colombia | Resolución 1995 de 1999 | Ley 1581 de 2012 |

---

## Mapeo a los textos actuales de la app

| Pantalla / string actual | ¿Coincide con el recomendado? | Acción sugerida |
|---|---|---|
| "Pacientes" | ✅ | Mantener |
| "Turno" / "Nuevo turno" (Agenda) | ⚠️ AR-específico | Decidir turno vs cita (§Decisiones) |
| "Ficha" (tab del paciente) | ✅ como dato estructurado | Aclarar que es parte de la HC, no la HC |
| "Notas" / "Notas IA" | ⚠️ | Evaluar "Nota de evolución" |
| "Honorario por sesión" | ✅ | Mantener |
| "Finanzas / Gastos / Ingresos / Cobros" | ✅ neutro | Mantener |

---

## Decisiones que requieren tu criterio

1. **`turno` vs `cita`** (lo más divergente). Si el mercado a 12 meses es AR → "turno" es lo natural.
   Si se apunta a LATAM amplio pronto → "cita" es más neutral y evita retrabajo de copy. *Recomendación:
   "turno" ahora (mercado AR), con los textos centralizados para swap por región después.*
2. **`paciente` vs `consultante`** → candidato a **preferencia configurable por profesional** (un toggle
   que cambia el label en toda la UI), dado que dentro del campo psi argentino conviven ambos.
3. **`ficha` vs `historia clínica`** → mantener "ficha" para el formulario estructurado, pero usar
   **"historia clínica"** como el concepto-paraguas en textos legales/export (SEB-177/185).
4. **`nota` vs `nota de evolución`** → "evolución" es más preciso clínicamente; evaluar para la UI de notas.

---

## Fuentes

- Colegios de Psicólogos de Argentina — Honorarios Mínimos Sugeridos (HMS): [colpsilar.com.ar](https://colpsilar.com.ar/honorarios-minimos-orientativos/), [cppc.org.ar](https://cppc.org.ar/resolucion-de-junta-de-gobierno-no-017-23-actualizacion-de-aranceles-minimos/)
- México — Expediente clínico en psicología (NOM-004-SSA3-2012): [psicoedu.org](https://psicoedu.org/expediente-clinico-en-psicologia/), [irene.plus](https://irene.plus/blog/noticias-2/como-desarrollar-un-expediente-clinico-en-psicologia-segun-la-norma-oficial-mexicana-6)
- Colombia — tarifas y atención psicológica: [medicosdoc.com](https://medicosdoc.com/blog-detalle/cuanto-cuesta-una-consulta-con-un-psicologo-en-bogota/724)
- Software del rubro en LATAM (referencia de terminología de producto): AgendaPro, Medilink, Psicobit, Medesk.
