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

Infra lista (SEB-161 a 164): repo `empresas-ia/conflur`, backend en Railway (`conflur-production.up.railway.app`), frontend en Vercel, DB Neon con schema aplicado.

**SEB-166 (Auth) — ✅ DONE, verificado en prod (`https://conflur.vercel.app`).**
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
- Suite total: **31 tests** verdes.

> El ficha_schema de psicología es un **dato editable** (`specialties.ficha_schema`), no código → se ajusta tras validar con un profesional real sin tocar código.

**Diseño v2 consolidado** en `docs/architecture.md` (D15–D20) y Linear reestructurado (SEB-175→182): verticales por esquema, omnicanal de dos lados, dominio financiero (carga por compra + costo-hora + precio inteligente + devengado/percibido), facturación ARCA, fichas + seguridad + export durable, agentes core→premium.

**Próximo sugerido:** SEB-176 (ficha clínica por esquema — guardar/validar valores de la ficha del paciente, usa el schema de SEB-175) o SEB-167 (agenda). Luego SEB-165→169 (LiteLLM→notas IA, core). Pasada de UI al final.

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

---

## Dónde están las cosas

```
EMPRESAS-IA/
├── docs/EIA1_Foundation_Document.md  ← documento fundacional del diseño
├── knowledge_module/                  ← KM compartido (tenant_id="eia1")
└── eia1/                              ← este repo
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
