# agents.md — EIA-1
> Contexto activo para Claude. Máximo ~200 líneas.
> Detalle técnico → `docs/architecture.md`. Fundacional → `../docs/EIA1_Foundation_Document.md`.

---

## ⚠️ Norte — leer esto primero

**EMPRESAS-IA es el producto.** Una plataforma para que cualquier persona, sin saber programar, cree una empresa 100% agéntica en lenguaje natural.

**EIA-1 / Conflur NO es el producto final.** Es la segunda instancia que demuestra que el proceso es replicable. Cada decisión de diseño acá debe poder documentarse como un paso replicable para la siguiente instancia.

Si algo no se puede replicar → rediseñar, no parchear.

---

## Qué es EIA-1 / Conflur

Empresa agéntica (Capa 2 de EMPRESAS-IA) de software B2C para profesionales de salud en práctica privada en LATAM. Vende herramienta + contenido + educación. Modelo: portafolio de vertical stacks, uno por especialidad, gestionado por CEO-agente.

**Nombre del producto:** Conflur (confluir + fluir)  
**Dominio:** conflur.com (registrado en Cloudflare — 2026-06-19)  
**Primer vertical:** psicólogos.  
**Mercado:** LATAM en español.  
**Precio:** freemium → $15/mes.

---

## Estado actual

⚠️ **FASE: CONSTRUCCIÓN — M0**

Infra lista (SEB-161 a 164): repo `conflur/conflur` (org propia, org-por-instancia; el viejo `empresas-ia/conflur` quedó archivado), backend en Railway (`conflur-production.up.railway.app`), frontend en Vercel, DB Neon con schema aplicado.

**Prod (2026-06-26):** frontend `https://conflur-three.vercel.app` (Vercel, cuenta sebabizzi@gmail, proyecto `conflur`) · backend `https://conflur-backend-production.up.railway.app` (Railway, proyecto `conflur`). Stack verificado end-to-end (register→login→dashboard→API). Deploy por CLI/API (ver `docs/progress/2026-06-26.md`). Falta: decomisar deploys viejos en cuentas empresas-ia.

**SEB-166 (Auth) — ✅ DONE, verificado en prod.**
- Fundación de tenancy: `tenants` + `memberships` + roles + `patient_access` + RLS en 8 tablas. Ver `docs/architecture.md` §Tenancy y D11–D14.
- Backend (`backend/auth/`): `/auth/register|login|me` (password, bcrypt+JWT) y `/auth/passkey/*` (WebAuthn con `py_webauthn`). Dependency valida Bearer → `set_tenant` → RLS. 20 tests pasan.
- Frontend (`frontend/src`): NextAuth v4 (Credentials password + passkey), `/login`, `/register`, `/dashboard` protegido, middleware, `@simplewebauthn/browser`.
- El backend deriva CORS + WebAuthn RP_ID/origin de una sola var `FRONTEND_URL`.
- Wiring de prod aplicado: Vercel (`NEXTAUTH_SECRET`, `NEXTAUTH_URL`), Railway (`FRONTEND_URL`, `APP_DATABASE_URL` rol sin bypassrls, `NEXTAUTH_SECRET` real).
- Flujo probado en navegador: register→dashboard, login password, activar passkey, login con passkey. Todo OK.

**Backend avanzado (sin UI todavía):**
- **SEB-168 Pacientes** — CRUD + interconsulta (RLS + patient_access). 3 tests.
- **SEB-175 Verticales** — `Specialty` (catálogo + ficha_schema JSONB) + `SessionType` (prestación, RLS) + `Tenant.specialty_code`; esquema de ficha psicológica + `validate_ficha`; migración 0002 aplicada; endpoints `/specialties` y `/session-types`. 5 tests.
- **SEB-176 Ficha clínica** — `ClinicalFile` (values JSONB validados contra el ficha_schema) + `GET/PUT /patients/{id}/ficha` con **autorización clínica estricta** (solo patient_access; la secretaría ve el perfil, no la ficha). Migración 0003. 3 tests.
- **SEB-165 LiteLLM** (✅ Done) — `llm/client.py`: LLMClient backend inyectable, modelo por `.env`, tokens. 2 tests.
- **SEB-169 Notas IA** — agente `agents/notes.py` (bullets→nota) + `patients/notes.py` (generate/guardar/listar/feedback) con acceso clínico. Migración 0004 (appointment_id opcional). 5 tests.
- **SEB-167 Agenda** — `appointments/`: CRUD de turnos (crear/listar por rango/PATCH/cancelar) con autorización por rol (owner/assistant todos; professional los suyos), RLS. 3 tests. (Google Calendar + recordatorios WhatsApp = follow-up.)
- **Fix sistémico**: PATCH/PUT serializaban mal por `updated_at` onupdate + RLS por tx → patrón **flush→refresh→commit** en patients/ficha/session_types/appointments.
- **SEB-170 ✅ Finanzas — motor de costos + ingresos/cobros** — `Expense`/`RecurringExpense`/`MonthlySetting` + `costo-hora` (migr 0005); `IncomeRecord`/`CollectionRecord` devengado/percibido (migr 0006, dropea `Payment` legacy). `/finanzas/*`, acceso operativo. Sin inventario (D24).
- **SEB-171 (p1) dashboard financiero** — `GET /finanzas/dashboard`: ER + Flujo de Caja + Matriz Salud Financiera 2x2 + KPIs + alertas (cálculo puro).
- **SEB-178 ✅ precio inteligente** — `GET /finanzas/precio-sugerido`. session_types +target_margin +variable_cost (migr 0007).
- **SEB-171 ✅ completo** — dashboard (ER+FC+matriz+KPIs) + **metas anuales** (`AnnualGoal`, migr 0008, `/finanzas/metas`, integradas al dashboard vs real).
- **SEB-179 ✅ completo** — **planes de cuotas** (`PaymentPlan`/`PaymentInstallment`, migr 0009: cuotas con vencimiento, cierre auto al pagar la última, dirección paciente/proveedor) · **excedentes** (`SurplusRecord`, migr 0010: 4 fuentes + registro de acción + resumen) · **presupuesto** (`AnnualBudget`, migr 0011: proyección con inflación compuesta vs real reusando `costo_hora`). `/finanzas/planes-cuotas`, `/finanzas/excedentes`, `/finanzas/presupuesto`. +12 tests.
- **Agente de Descubrimiento — canal web (2026-07-02) ✅ completo:**
  `DiscoverySession` (migr 0014, sin RLS — UUID token = control de acceso) + router `discovery/`
  (crear sesión auth + `GET /sessions/{token}`, `POST /sessions/{token}/message`,
  `POST /sessions/{token}/close`, `GET /findings`, `POST /insights/refresh`) +
  frontend `/discovery/[token]` (chat sin login: burbujas, input, "Terminar conversación") +
  `/cuenta/discovery` (crear link con nombre+referidor+género, lista charlas, hallazgos
  consolidados, card "Lo que aprendimos"). Migración aplicada. 7 tests integration verdes.
  Estado: **Fase 1 ✅ · 2a ✅ · 2b ✅ · 3 web ✅ · 3b Telegram pendiente.**
  **Mejoras de calidad conversacional (2026-07-06):**
  - Few-shot examples (6 diálogos) en el system prompt — reemplaza instrucciones puras;
    áreas sin numeración para evitar orden scripted; max_tokens 200, top_p 0.9
  - LLMClient: soporte `top_p` en `complete()`
  **Capa de aprendizaje (2026-07-06) — `DiscoveryMarketInsight` (migr 0016):**
  - `synthesize_market_insights()` — analiza N findings y extrae patrones cross-session
  - Auto-refresh fire-and-forget al cerrar sesión (umbral ≥3 charlas)
  - Inyección de `market_context` en el system prompt: charlas ≥4 arrancan con el
    conocimiento acumulado de las anteriores
  - Frontend: card narrativa "Lo que aprendimos" en tab Hallazgos
- **Setup staging (2026-07-02) — en curso, no cerrado:** se decidió armar ambiente staging antes
  de deployar Fase 3 a prod. `main` = staging, `production` = prod (rama git nueva creada apuntando
  al commit prod pre-Fase 3). Neon branch `staging` creado. Railway prod reconectado a GitHub con
  auto-deploy en `production`. Railway staging `conflur-backend-staging` creado con env vars
  cargadas pero **build failed hasta setear Root Directory=backend en UI** (Railway CLI no cubre
  eso). Falta también: cambiar Vercel prod a branch `production` y crear proyecto Vercel staging.
  **`main` NO está pusheado** — se pushea recién cuando staging levante. Detalles + próximos pasos
  exactos en `docs/progress/2026-07-02.md` §🔜 PRÓXIMA SESIÓN. Checklist canónico en
  `docs/deploy-staging.md`. Ambientes en `docs/architecture.md` §Ambientes (D-STAGING).
- Suite total: **77 tests** verdes (`77 passed, 16 warnings in 1401.43s`).
- **Falta del dominio financiero:** SEB-180 ARCA.
- **UI (2026-06-25):** ✅ **Agenda** (`/agenda`, vista semanal: crear/estado/cancelar) + ✅ **Finanzas** (`/finanzas`: dashboard ER+FC+matriz+KPIs+metas vs real, movimientos gastos/ingresos/cobros, configuración mes+metas). Nav suma Agenda y Finanzas. Build de prod limpio. Pacientes/ficha/notas ya tenían UI → **MVP navegable de punta a punta**.
- **Telepsicología (2026-06-25):** turnos suman `modality` (presencial|telepsicologia) + `meeting_url` (migr 0012). Al crear un turno remoto se **autogenera el link** de videollamada. Proveedor **abstraído/swappable** (`appointments/meeting.py`, default **Jitsi** sin credenciales, configurable por `MEETING_PROVIDER`; Google Meet vía Calendar = follow-up). UI: selector de modalidad + link "Unirse a la videollamada". Tests en test_appointments.
- **Notas SOAP (2026-06-25):** el agente de notas soporta `note_format` (libre|soap). SOAP estructura en Subjetivo/Objetivo/Análisis/Plan vía prompt dedicado (`agents/notes.py`), sin cambio de schema (se persiste en `template_type`). UI NotasTab: selector Libre/SOAP + badge SOAP en el historial. Test unitario del prompt.
- **Nota git:** repo en `conflur/conflur`; se commitea/pushea como `sebasbizzi` (Owner). Ya no hace falta `gh auth switch`. (Se migró por espejo, no por Transfer, por el hold anti-fraude de GitHub sobre la org nueva.)

> El ficha_schema de psicología es un **dato editable** (`specialties.ficha_schema`), no código → se ajusta tras validar con un profesional real sin tocar código.

> ⚠️ **Notas IA en vivo requieren `ANTHROPIC_API_KEY`** (vacía en `.env` y Railway). Tests usan LLM fake. Crear cuenta Anthropic bajo empresas.ia.dev y setear la key (local + Railway) para ver la generación real.

**Diseño v2 consolidado** en `docs/architecture.md` (D15–D20) y Linear reestructurado (SEB-175→182): verticales por esquema, omnicanal de dos lados, dominio financiero (carga por compra + costo-hora + precio inteligente + devengado/percibido), facturación ARCA, fichas + seguridad + export durable, agentes core→premium.

**Próximo sugerido (2026-07-06):** hacer charlas reales de discovery en staging para probar la mejora conversacional (few-shot + learning layer). Con ≥3 charlas cerradas se activa el primer insight de aprendizaje. Una vez validado → promover a prod → Fase 3b (Telegram).

---

## Stack activo

- **Frontend:** Next.js + TypeScript → Vercel
- **Backend:** Python + FastAPI → Railway
- **DB:** PostgreSQL (Neon.tech)
- **Auth:** NextAuth + PostgreSQL propio + WebAuthn/Passkeys (huella digital)
- **IA:** LiteLLM → Anthropic API (Sonnet 4.6 por defecto, configurable por `.env`)
- **Billing:** Stripe + MercadoPago
- **Contenedores:** Docker (Dockerfile por servicio + docker-compose.yml)

---

## Linear

- **Proyecto:** EIA-1 (a crear)
- **Equipo:** Sebabizz._dev
- **Cycle activo:** ninguno aún
- **Milestone actual:** M0 — Setup + primer vertical MVP

---

## Verticales

| Vertical | Estado | Prioridad |
|---|---|---|
| Psicólogos | 🔴 diseño pendiente | 1 — arrancar aquí |
| Kinesiólogos | ⬜ no iniciado | 2 |
| Fonoaudiólogos | ⬜ no iniciado | 3 |
| Terapistas Ocupacionales | ⬜ no iniciado | 4 |
| Nutricionistas | ⬜ no iniciado | 5 |
| Psicopedagogos | ⬜ no iniciado | 6 |

---

## Pendientes / flags abiertos

- [x] **Nombre del producto** — ✅ Conflur
- [x] **Stack técnico** — ✅ resuelto (ver `docs/architecture.md`)
- [x] **Billing LATAM** — ✅ Stripe + MercadoPago ambos desde M0
- [x] **Sesión de configuración inicial** — ✅ playbook bloques 1–10 completados
- [x] **Proyecto Linear EIA-1** — ✅ creado (SEB-160 a SEB-172), milestone M0 activo
- [x] **Design Gate del MVP psicólogos** — ✅ estado 🟡 LISTO CON DEUDA (`docs/DESIGN_GATE.md`)
- [x] **Registrar conflur.com en Cloudflare** — ✅ comprado 2026-06-19
- [ ] **Crear cycle M0 en Linear** — acción de Sebas (los cycles los crea el usuario manualmente)
- [ ] **Construir el MVP** — desarrollo puede arrancar (Design Gate 🟡)
- [ ] **Migrar proyecto Neon `conflur`** de cuenta personal `sebabizzi` a `empresas.ia.dev` — infra debe vivir bajo la cuenta técnica de la plataforma
- [ ] **🔴 CRÍTICO — agregar `APP_DATABASE_URL` en Railway** apuntando al rol `conflur_app` (sin bypassrls). Sin esto, en producción la app usa `neondb_owner` que **saltea el RLS** → el aislamiento entre consultorios no existe. Valor en `backend/.env` local. Ver `docs/architecture.md` D14 y memoria `reference_neon_rls_bypass`.
- [ ] **Auditoría de cumplimiento de plataforma (2026-07-05)** — corrida de lectura, sin cambios de código en esta instancia. 12 hallazgos propios (E1-E12), los 2 primeros críticos y sin confirmar todavía: **E1 (SEB-254)** — el ítem de arriba (rol de Railway) sigue sin confirmarse resuelto; **E2 (SEB-255)** — notas clínicas en texto plano, confirmar que no haya pacientes reales cargados ya. El resto (E3-E12): sin headers de seguridad en el backend, expiración de sesión por inactividad no implementada, Stripe/MercadoPago sin webhooks, sin logging de requests/errores, Design Gate con tenancy pre-rediseño, `APP_ENV=development` en prod (loguea SQL completo), agente de notas sin KM (deuda M1 documentada), Discovery sin rate limiting, nitpicks de `.env.example` y de tests. Detalle completo: `../docs/AUDITORIA_CUMPLIMIENTO_2026-07-05.md`. Pendiente: revisar cada uno con Sebas y decidir método de resolución (panel en `../plataforma/control_panel/`).

---

## Dónde están las cosas

```
EMPRESAS-IA/
├── docs/EIA1_Foundation_Document.md  ← documento fundacional del diseño
└── eia1/                              ← este repo (DB propia, aislada)
    ├── agents.md                      ← este archivo
    ├── CLAUDE.md                      ← contexto de sesión para Claude
    ├── docs/
    │   ├── architecture.md            ← decisiones técnicas
    │   ├── DESIGN_GATE_TEMPLATE.md    ← copiar para cada módulo nuevo
    │   └── progress/                  ← logs de sesión
    └── (código — pendiente)
```

---

## REGLAS OPERATIVAS — no modificar, no borrar

> Esta sección se lee en cada sesión y permanece fija durante toda la vida del proyecto.

### Definition of Done

Una tarea de código está Done cuando:

- [ ] El código funciona según lo especificado
- [ ] Tiene tests para funciones críticas (auth, datos sensibles, lógica central)
- [ ] No hay credenciales expuestas en el código
- [ ] `agents.md` refleja cambios si corresponde
- [ ] La sesión está documentada en `docs/progress/YYYY-MM-DD.md`
- [ ] Si es módulo nuevo: el Design Gate existe y está en ✅

Verificar esta lista ANTES de mover un issue a Done en Linear.

### SDLC — fases activas

No avanzar a la siguiente fase sin confirmar que la anterior está resuelta:

Planificación → Requerimientos → Diseño → Desarrollo → Testing → Deployment → Mantenimiento

### Seguridad mínima siempre activa

- Nunca hardcodear credenciales. Siempre variables de entorno.
- `.env` siempre en `.gitignore` antes del primer commit.
- Cada endpoint verifica que el usuario tiene permiso sobre ESE recurso específico.
- Antes de cada commit: verificar que no hay credenciales expuestas.
- EIA-1 maneja datos clínicos de pacientes → aplicar Seguridad Nivel 3 (multi-tenancy + RLS).

### Linear — workflow

- Al iniciar tarea → In Progress
- Al completar tarea → verificar DoD → Done → avisar al usuario y esperar instrucción
- Issues no completados al cerrar cycle → vuelven a backlog, no se arrastran solos

### Protocolo de inicio de sesión

1. Leer el bloque **⚠️ Norte** de este `agents.md` — el norte no cambia nunca
2. Leer el resto de este `agents.md`
3. Leer el cycle activo en Linear (proyecto EIA-1)
4. Leer el último `docs/progress/YYYY-MM-DD.md`
5. Mostrar: qué está In Progress, qué está en Todo, si hay Bloqueados
6. Preguntar: "¿Arrancamos con X o preferís otra cosa?"
