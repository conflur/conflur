# La capa que ve el profesional — propuesta v0

> **Estado: hipótesis v0 para validar con profesionales reales (3-5 psicólogos) antes de fijar.**
> Pensada para cambiar. Surge del repaso "qué ve el profesional" (2026-06-27).

---

## El reencuadre (la base)

No vendemos **"un sistema de gestión"** → vendemos **resolver el dolor de gestionar el consultorio**:
*"dedicate a tus pacientes, del resto nos ocupamos nosotros"*. Dos palancas:

- **La herramienta** → le **saca de encima** el trabajo administrativo (lo hace por él).
- **La formación** → le **saca la ignorancia/ansiedad** de no saber llevar un consultorio (le enseña, y le enseña a leer sus datos para decidir).

Juntas: *"no solo te ordeno el consultorio — te enseño a tener un consultorio próspero y tranquilo."*

## Principios de la capa

1. **Organizada por el día y las preguntas del profesional**, no por nuestras tablas.
2. **La vista correcta por rol** (la base ya lo soporta: `owner` / `professional` / `assistant`).
3. **"Registramos e iluminamos; ellos deciden."** La herramienta **captura** y **traduce datos en respuestas**; la **decisión —y la responsabilidad— es del profesional**. Se dice explícito en la UI (*"vos decidís"*) y en los ToS (blindaje legal + principio; alineado al ADN de EMPRESAS-IA: *el sistema arma, el humano elige*).
4. **Lenguaje de consultorio**, jerga contable/clínica abajo.
5. **Suficiente**: el núcleo validado por el mercado, nada de más.
6. **Flexible**: es v0; se ajusta tras validar.

---

## La navegación (núcleo suficiente)

| Sección | Qué resuelve | Lenguaje |
|---|---|---|
| **Hoy** (inicio) | "¿qué tengo que hacer hoy?" | nuevo |
| **Agenda** | turnos, confirmaciones, recordatorios | "Turno" (AR) / "Cita" (regional) |
| **Pacientes** | ficha + **notas de evolución** (IA / SOAP) | "Paciente", "Ficha", "Nota" |
| **Mis números** *(hoy "Finanzas")* | "¿el consultorio es rentable? ¿cobro bien? ¿la caja alcanza?" | sin jerga |
| **Aprender** *(liviano al inicio)* | formación: cómo usar + cómo leer los datos | — |
| **Mi cuenta** | datos, equipo, prestaciones | — |

> "Finanzas" → **"Mis números"** (o "Mi consultorio") es hipótesis a validar — que no asuste.

## La pantalla "Hoy" (el corazón) — por rol

- **Profesional / solo:** *tus turnos de hoy* (con quién, presencial/telepsicología + link), **notas pendientes de escribir**, 1 señal ("3 turnos hoy · 1 nota pendiente"). Acceso: nuevo turno / paciente.
- **Secretaría:** agenda del día de **todos** los profesionales, **confirmaciones pendientes**, cobros del día. **Sin acceso clínico.**
- **Dueño:** el pulso — turnos del día + **una** señal financiera simple (mes en verde/amarillo/rojo).

---

## "Mis números" reencuadrado (finanzas sin contaduría)

### Principio clave: el consultorio NO es el bolsillo personal
Lo que enseñamos: **separar las finanzas del consultorio de las personales.** El modelo ya lo soporta — el **sueldo del profesional es un costo del consultorio**, así la rentabilidad ya es *después* de pagarse. El lenguaje hace explícito el límite:

> *"Tu consultorio y tu bolsillo son cosas distintas. Acá ves el **consultorio**; tu sueldo sale de acá."*
> Tip de onboarding: **"Pagate un sueldo, no metas la mano en la caja."**

### Las 3 preguntas grandes (no tablas)
1. **¿El consultorio es rentable?** — gana/pierde **después** de tu sueldo. Una cifra + color.
2. **¿Estás cobrando bien?** — precio sugerido vs lo que cobrás.
3. **¿La caja del consultorio alcanza?** — se sostiene, puede pagar lo que debe + tu sueldo.

Abajo, colapsado: *"Ver el detalle"* (Estado de Resultado, devengado/percibido, matriz, etc.) para quien quiera. Siempre presente: *"Esto es para que decidas vos — Conflur te muestra, no decide."*

> **Ajuste por el vertical:** los psicólogos cobran **por sesión** → NO se prioriza cobranzas/deudas/planes de cuotas-paciente. El foco es **rentabilidad y precio**. (Las cuotas de SEB-179 quedan para otros verticales / lado proveedor.)

---

## La formación, en capas (tejida, no un curso colgado)

Enseña dos cosas: **usar la herramienta** y **leer los datos para decidir** (lo que no hacemos por ellos).

| # | Capa | Dónde | Modelo | Cuándo |
|---|---|---|---|---|
| 1 | Micro-tips en contexto | in-app | gratis | con el MVP |
| 2 | Curso/contenido base | **YouTube** | gratis — top-of-funnel, **capta** | temprano |
| 3 | Cursos desarrollados | **Udemy / Hotmart / Skool** | membresía paga | post-MVP |
| 4 | Masterclass + sesiones grupales/individuales | — | pago (más caro) | **último — implica presencia de Sebas, analizar antes** |

> Las capas 1-2 (gratis) son también **canal de adquisición**: el contenido atrae profesionales → la herramienta convierte → 3-4 monetizan. Encaja con "tool + contenido + curso".

### Capacitación organizada en el KM (trazable al sistema)
Cada pieza de formación = **entidad en el KM** con metadata:
- **capa** (tip / YouTube / curso pago / masterclass)
- **qué cubre** (feature/pantalla del sistema)
- **versión del sistema** que refleja
- plataforma (in-app, YouTube, Hotmart…) + estado

→ Al cambiar una feature, se consulta el KM por el material que la cubre y sale la **lista exacta de capacitación a actualizar.** Lo vigila el **agente de mantenimiento de plataforma** (hoy un hueco identificado del roster — ver mapa de agentes pendiente).

---

## Qué queda AFUERA del MVP (suficiente, no de más)
Deliberadamente fuera de la capa profesional ahora: portal del paciente, tests psicométricos (PHQ-9/GAD-7), cobranzas/planes de cuotas complejos, inventario, reportes contables avanzados. Anotados como capas futuras u otros verticales.

## Cómo la hacemos flexible (va a cambiar)
- **Copy/labels centralizado** → cambiar "Finanzas→Mis números" o "Turno→Cita" (regional) sin tocar lógica (resuelve también el swap regional del glosario).
- **"Hoy" modular por widgets** → se agregan/quitan por rol y vertical.
- **Config por especialidad** (skin) → el mismo molde sirve a kinesiólogos, etc.
- **Plan de validación:** v0 → probar con 3-5 psicólogos reales antes de fijar.

---

## Issues relacionados
- SEB-194 — vista anual del Estado de Resultado.
- SEB-195 — UX Finanzas simple para no-financieros.
- SEB-185 — ToS: dejar explícito "Conflur informa, no decide".
- (pendiente) Mapa de fases de agentes + roster completo (incluye agente de mantenimiento que mantiene la formación en sync).

## Fuentes (investigación de mercado/terminología)
Software del rubro y necesidades validadas: [Medilink](https://www.softwaremedilink.com/psicologia), [PsicoGestión](https://psicogestion.app/), [Medesk](https://www.medesk.net/es/solutiones/psicologia-y-psiquiatria/), [Docfav](https://pro.docfav.com/software-para-psicologos), [Freud](https://www.heyfreud.com/en/blog/elegir-software-gestion-psicologos). Terminología: ver `docs/terminologia-latam.md`.
