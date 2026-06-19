# architecture.md — Decisiones de EIA-1

> Registro de todas las decisiones técnicas y de diseño tomadas.
> Si hay conflicto: este archivo gana para decisiones técnicas. Linear gana para estado de tareas.

---

## Identidad

- **Nombre del producto:** Conflur (confluir + fluir — ambos pilares del producto y servicio)
- **Dominio:** conflur.com (registrado en Cloudflare — 2026-06-19)
- **Problema que resuelve:** los profesionales de salud en práctica privada en LATAM gestionan su práctica con papel, Excel y WhatsApp. EIA-1 les da una herramienta digital simple con IA que les ahorra tiempo y les ayuda a tomar decisiones financieras.
- **Usuario final:** profesionales de salud en práctica privada en LATAM (psicólogos, kinesiólogos, fonoaudiólogos, terapistas ocupacionales, nutricionistas, psicopedagogos)
- **Milestone próximo:** M0 — MVP psicólogos (freemium, 20-30 usuarios en 3 semanas)

---

## Modelo de negocio

- **Tipo:** B2C SaaS + educación
- **Precio:** freemium → $15/mes USD
- **Revenue streams:** suscripción mensual + cursos one-time ($97–297) + afiliados largo plazo
- **Go-to-market:** community-driven (grupos Facebook/WhatsApp de profesionales LATAM)
- **Mercado:** LATAM en español (Argentina, México, Colombia como foco inicial)

---

## Arquitectura del producto

### Plataforma core (compartida entre verticales)
- Agenda (vista semanal, turnos)
- Perfil de paciente/cliente
- Notas con generación IA (bullets → nota completa)
- Registro de cobros + PDF de recibo
- Dashboard financiero de decisión

### Skin vertical (configurable por especialidad)
- Templates de notas específicos por profesión
- Terminología propia de la especialidad
- Flujos propios (ej: HEP para kinesiólogos, planes alimentarios para nutricionistas)

**Decisión D1 [2026-06-17]:** arquitectura plataforma core + skin vertical. No N productos distintos.  
**Razón:** el 80% del código es compartido. Nuevo vertical = configurar, no reescribir. Permite portafolio sin explosión de deuda técnica.

---

## Stack

- **Frontend:** Next.js + TypeScript
- **Backend:** Python + FastAPI
- **Base de datos:** PostgreSQL (Neon.tech)
- **Auth:** NextAuth + PostgreSQL propio (ver §Auth)
- **IA:** Anthropic API via LiteLLM — modelo configurable por `.env`, default `claude-sonnet-4-6`
- **Billing:** Stripe + MercadoPago (ambos desde M0)
- **Hosting frontend:** Vercel
- **Hosting backend:** Railway
- **Contenedores:** Docker desde el inicio (Dockerfile por servicio + docker-compose.yml)

---

## Ambientes

- **Local:** desarrollo en Docker
- **Staging:** se configura antes del primer usuario real — base de datos independiente
- **Producción:** Vercel (frontend) + Railway (backend) + Neon.tech (DB)

---

## Seguridad

**Nivel aplicable: 1 + 2 + 3** (hay usuarios con login y datos clínicos sensibles de terceros)

- Multi-tenancy: `tenant_id` en todas las tablas relevantes (= `tenants.id`, el consultorio)
- RLS en PostgreSQL como última línea de defensa — aísla **entre consultorios**
- Aislamiento **dentro del consultorio** (visibilidad clínica): capa de autorización de la app vía `patient_access` (ver §Tenancy)
- KM de EIA-1: `tenant_id = "eia1"` — completamente aislado de CRIZA
- Política de retención: pendiente de definir antes del primer usuario real

**Decisión D2 [2026-06-17]:** aplicar Seguridad Nivel 3 desde el inicio. Los datos clínicos de pacientes son sensibles. No es negociable postergar multi-tenancy.

**Decisión D14 [2026-06-19]:** la app se conecta con un rol dedicado **`conflur_app` sin `BYPASSRLS`** (`APP_DATABASE_URL`); el rol owner (`neondb_owner`, `DATABASE_URL`) queda **solo para migraciones/admin**.
**Razón:** se detectó que `neondb_owner` tiene `rolbypassrls = true` — saltea TODO el RLS aunque las tablas tengan `FORCE ROW LEVEL SECURITY`. Si la app corriera con ese rol, el RLS sería decorativo y el aislamiento entre consultorios no existiría. El test `tests/test_tenancy_rls.py` prueba el aislamiento conectándose con el rol sin bypass. **En Railway, `APP_DATABASE_URL` debe apuntar a `conflur_app`.**

---

## Tenancy — modelo de primera clase

El tenant (consultorio) es una **entidad de primera clase**, no `= user_id`. Esto se diseñó completo desde el inicio para no rehacer el modelo cuando llegue un consultorio multi-profesional o una instancia tipo organización.

```
tenant (consultorio)
  ├── memberships (usuarios con rol dentro del consultorio)
  │     ├── owner        → gestiona miembros, billing, agenda
  │     ├── professional → SUS pacientes y SUS notas (vía patient_access)
  │     └── assistant    → secretaría: agenda + cobros + contacto; NUNCA la nota clínica
  └── recursos (patients, appointments, clinical_notes, payments, subscriptions) → tenant_id
```

- **`users`** = identidad global (login, passkeys). Sin rol propio; el rol vive en `memberships` y es relativo al consultorio. `users.is_platform_admin` es el único rol global (Sebas / soporte).
- **`tenants`** = consultorio. `type` = `individual` (un profesional = consultorio de un miembro) | `practice` (varios).
- **`memberships`** = liga user ↔ tenant + rol + estado.
- **Suscripción** = del consultorio (`subscriptions.tenant_id`), no del usuario — el consultorio paga y el freemium gate se mide por consultorio.

### Dos capas de aislamiento

| Capa | Qué aísla | Mecanismo |
|---|---|---|
| Entre consultorios | que el consultorio A nunca vea datos del B | **RLS** sobre `tenant_id` |
| Dentro del consultorio | quién ve qué paciente/nota | **Autorización** por rol + `patient_access` (capa de app) |

El RLS por `tenant_id` no alcanza dentro del consultorio: los miembros comparten `tenant_id`. La nota clínica la protege `patient_access`.

### Visibilidad clínica (`patient_access`)

- Una nota clínica la ve **quien tiene un `patient_access` activo** sobre el paciente (no vencido, no revocado). La secretaría/admin NUNCA.
- `access_type='primary'` → un profesional principal por paciente.
- `access_type='shared'` → **interconsulta**: el principal comparte el paciente con otro profesional de forma explícita, registrada (`granted_by_user_id`), revocable (`revoked_at`) y opcionalmente temporal (`expires_at`). Durante la ventana ambos ven las notas del paciente y cada uno suma la suya.
- Todo grant/revoke es auditable.

**Decisión D12 [2026-06-19]:** tenant de primera clase (`tenants` + `memberships` + roles owner/professional/assistant), no `tenant_id = user_id`. Suscripción a nivel consultorio.
**Razón:** un consultorio real tiene varios profesionales + secretaría. Diseñar completo ahora (aunque M0 active solo el camino del profesional individual) evita rehacer el modelo de tenancy — el retrabajo que la regla de capa prohíbe. Mismo modelo sirve a una instancia tipo organización (LegalCo) sin tocar el schema.

**Decisión D13 [2026-06-19]:** visibilidad clínica por `patient_access` (dos capas: RLS entre consultorios + autorización dentro). Interconsulta = compartir explícito, revocable, temporal y auditado.
**Razón:** dato clínico sagrado (principio 4). El RLS por tenant no protege entre profesionales del mismo consultorio; la nota se protege en la capa de autorización. La interconsulta es un patrón clínico real que necesita contexto compartido acotado.

---

## KM (Knowledge Module)

- Usa la infraestructura compartida de `../knowledge_module/`
- `tenant_id = "eia1"` — todos los datos de EIA-1 están aislados
- Lo que EIA-1 aprende (lecciones, patrones, feedback) no se filtra a CRIZA ni a otras instancias

---

## Colaboración y Docker

- **Modo:** solo (Sebas) ahora — puede sumar colaboradores
- **Docker:** desde el inicio. Dockerfile por servicio + docker-compose.yml para ambiente local
- **Instrucciones:** README con `docker-compose up` para levantar el ambiente completo

---

## Testing

- **Nivel M0:** unittests en funciones críticas del backend
- **Regla base irrompible:** siempre tests para auth, datos de pacientes y billing — sin excepción
- **Herramientas:** pytest (backend) · Jest (frontend)
- **Evolución:** integration tests en endpoints principales cuando el MVP esté estable

---

## Observabilidad

- Logging básico desde el inicio: timestamp + endpoint + status code en cada request
- Errores: stack trace completo
- Nivel de log configurable por variable de entorno (`LOG_LEVEL`)
- Backups de DB: automáticos en Neon.tech (verificar plan antes del primer usuario real)

---

## Linear

- **Proyecto:** EIA-1 (a crear)
- **Equipo:** Sebabizz._dev
- **Labels:** `bug` · `feature` · `infra` · `docs` · `testing` · `Bloqueado` · `En revisión`
- **Milestone M0:** Setup + MVP psicólogos

---

## Agentes del sistema

- **CEO-agente:** orquesta el portafolio, revisa KPIs semanales, ajusta instrucciones de otros agentes
- **Agente de Contenido/Crecimiento:** genera y distribuye contenido en canales (FB grupos, Instagram), monitorea señales de captación
- **Agente CS:** onboarding, activación de freemium, seguimiento de conversión a pago
- **Agente de Notas:** genera notas clínicas a partir de input del profesional
- **Agente Financiero:** trackea costos, emite alertas, genera reportes de rentabilidad

**Comunicación entre agentes:** via KM (lectura/escritura en base de datos), no por chat directo.
**Modelo base:** `claude-sonnet-4-6` · configurable por agente via `.env` (`CEO_MODEL`, `NOTES_MODEL`, etc.)

---

## Verticales — decisiones de priorización

**Decisión D3 [2026-06-17]:** primer vertical = psicólogos.  
**Razón:** profesión más grande del listado en LATAM, demanda post-COVID en máximos, la mayoría trabaja independiente, tool relativamente simple en MVP, comunidades online enormes.

**Decisión D4 [2026-06-17]:** go-to-market community-driven antes de cualquier inversión en ads.  
**Razón:** grupos de Facebook/WhatsApp de profesionales de salud en LATAM tienen decenas de miles de miembros activos. Canal de costo cero con alta concentración del target.

### Estrategia de canales

Cada canal tiene un rol distinto — no son intercambiables:

| Canal | Rol | Prioridad |
|---|---|---|
| **Facebook grupos** | Comunidad y conversación — captación principal. Grupos de psicólogos en AR/MX/CO tienen decenas de miles de miembros activos. | Alta — arrancar aquí |
| **Instagram** | Contenido y alcance — posts/Reels para visibilidad. Broadcasting, no comunidad. Complementa FB. | Media — arrancar en paralelo |
| **WhatsApp grupos** | Alta conversión cuando se tiene acceso. Más privado, requiere ganarse la confianza primero. | Media — se activa después de establecer presencia en FB |
| **Telegram** | Penetración baja en LATAM para este segmento. No prioritario en el MVP. | Baja — evaluar en Mes 3+ |
| **LinkedIn** | Demasiado corporativo para psicólogos en práctica privada. | Descartado |

---

## Principios de los agentes de Conflur

Estos principios rigen el diseño, los prompts y la evaluación de todos los agentes de EIA-1. Son no negociables y se incluyen en el system prompt base de cada agente.

**Decisión D5 [2026-06-18]:** 9 principios operativos para todos los agentes de Conflur.

| # | Principio | Definición operativa |
|---|---|---|
| 1 | **Objetivo primero** | Razonar desde la decisión que hay que tomar, no desde los datos disponibles. |
| 2 | **Experiencia que abraza el dolor** | El profesional abre la app con mala predisposición — no le gustan las finanzas, le cuesta lo tecnológico, le resulta tedioso registrar. Cada pantalla, cada mensaje, cada interacción tiene que desarmar esa resistencia. La app no puede ser una carga más. Tiene que sentirse como alivio. |
| 3 | **Rentabilidad total** | Trackear y optimizar TODOS los costos: tokens, infraestructura, medios de pago (comisiones), publicidad, impuestos, licencias, tools. Ningún costo es invisible. El objetivo siempre gana sobre el costo, pero el costo siempre se mide. |
| 4 | **Privacidad como diseño** | Datos de pacientes sagrados. Nunca en prompts, nunca en logs, nunca entre tenants. |
| 5 | **Tono: respeto + calidez** | Son profesionales altamente capacitados que al usar esta app demuestran valentía. Nunca subestimarlos. Nunca infantilizarlos. El tono reconoce su esfuerzo y profesionalismo, y los acompaña con calidez genuina en algo que les genera incomodidad. |
| 6 | **Acción sobre análisis** | Ante duda razonable, actuar y aprender. No sobre-analizar. |
| 7 | **Veracidad por dato** | Establecido / asumido / a-confirmar. Nunca inventar números. |
| 8 | **Aprendizaje como ventaja** | Todo el sistema aprende de cada experiencia. Usar la analogía: ¿qué situación pasada se parece a esta? ¿Qué funcionó? ¿Cómo lo aplico de forma eficiente y rentable? El aprendizaje es el activo que se acumula. |
| 9 | **Feedback como mejora continua** | Cada agente tiene KPIs y mecanismos de feedback. Ver §Sistema de feedback. |

---

## Sistema de metas, KPIs y feedback

### Por qué este sistema existe

Objective-first (principio 1) requiere saber qué se quiere lograr antes de actuar. Para que los agentes puedan razonar desde el objetivo, necesitan metas claras. Las metas generan KPIs. Los KPIs alimentan el feedback. El feedback cierra el loop y mejora las metas siguientes.

```
Metas empresa (CEO-agente)
        ↓ cascadea
Metas por agente
        ↓ se miden con
KPIs por agente
        ↓ alimentan
Feedback (cuantitativo + proxies cualitativos + calibración humana)
        ↓ informa
Ajuste de instrucciones / estrategia / metas
        ↓ reinicia el ciclo
```

### Metas de empresa (Conflur)

| Horizonte | Meta |
|---|---|
| 3 semanas | 20-30 usuarios freemium activos |
| 4 meses | 300 usuarios de pago |
| 8 meses | 500+ usuarios de pago |

Métricas de salud permanentes: MRR · churn mensual · CAC · costo por usuario activo.

### Metas por agente (derivadas de las de empresa)

| Agente | Meta derivada |
|---|---|
| Contenido/Crecimiento | Leads calificados/semana suficientes para alimentar la meta de freemium del período |
| CS | % de freemium que activan en 7 días · % que convierten a pago en 30 días |
| Notas | % de notas aceptadas sin edición significativa > umbral (a definir con datos reales del M1) |
| Finanzas | Costo por usuario activo < umbral (tokens + infra + comisiones de pago) |
| CEO | MRR on-track mensual · churn < umbral · CAC dentro de payback razonable |

Las metas de los agentes no son fijas: el CEO-agente las recalibra si el contexto cambia (ej: si conversión freemium→pago es más alta de lo esperado, puede bajar la meta de adquisición y subir la de retención).

---

## Sistema de feedback agéntico

El feedback en Conflur opera en tres capas. La clave: no forzar número donde hay calidad.

### Capa 1 — KPIs cuantitativos (automáticos)

| Agente | KPI principal |
|---|---|
| Agente de notas | % de notas aceptadas sin edición significativa |
| Agente CS | % de activación en 7 días · churn mensual |
| Agente de contenido | Conversión post → signup · DMs y menciones entrantes |
| Agente financiero | % de alertas que el usuario califica como útiles |
| CEO-agente | MRR · churn · costo por cliente adquirido |

### Capa 2 — Proxies cualitativos (automáticos con interpretación)

Para el agente de contenido y comunidad, donde el vínculo con el usuario importa tanto o más que el volumen:

- Comentarios que generan conversación de terceros (no solo likes)
- Etiquetas espontáneas — un profesional que etiqueta a un colega en un post es una señal fuerte de confianza
- Mensajes directos entrantes tras un post
- Saves y compartidos
- Calidad de comentarios: longitud, preguntas de seguimiento

Estos proxies son rastreables y entran al KM. El CEO-agente los interpreta semanalmente.

### Capa 3 — Revisión de calibración humana (mensual)

Para lo que no tiene proxy confiable — tono, autenticidad, "¿cómo se siente esto?" — Sebas revisa una muestra de outputs del agente de contenido y comunidad con una escala de 3 puntos:

- **1 — Perdió el tono:** formulado, frío, o equivocado en el registro
- **2 — Ok:** cumple, sin destacar
- **3 — Nació para esto:** genuino, cálido, mueve a la acción

Esa calificación entra al KM como input para el CEO-agente. No automatizar lo que no se puede automatizar — el ojo humano es parte del sistema.

### Capa 3 — Calibración humana (Sebas)

Frecuencia adaptativa — más intensa al inicio, se estabiliza con el tiempo:

| Fase | Período | Frecuencia |
|---|---|---|
| Puesta a punto | Primeras 4-6 semanas | Cada 2-3 días |
| Estabilización | Meses 2-3 | Semanal |
| Crucero | Mes 4 en adelante | Mensual |

Escala de calificación (1-3): **1 — Perdió el tono** · **2 — Ok** · **3 — Nació para esto**

Esa calificación entra al KM como input para el CEO-agente. No automatizar lo que no se puede automatizar — el ojo humano es parte del sistema, especialmente en la fase de puesta a punto.

### Ciclo de mejora (up-down / down-up)

- **Down-up:** cada agente registra en el KM dificultades o patrones nuevos al terminar un run
- **Up-down:** el CEO-agente revisa KPIs + calibración de Sebas y actualiza instrucciones de cada agente
- Los system prompts de los agentes son versionados en el KM — para poder medir si el cambio mejoró el KPI

**Decisión D6 [2026-06-18]:** sistema de feedback de 3 capas. System prompts versionados en el KM. CEO-agente con ciclo semanal cuantitativo. Calibración humana con frecuencia adaptativa (cada 2-3 días al inicio → semanal → mensual).

---

## Auth

- **Solución:** NextAuth (sesión/JWT) + verificación de credenciales en FastAPI + PostgreSQL propio (control total de datos — dato clínico sensible)
- **Métodos de login:**
  - Email + contraseña (siempre disponible, fallback obligatorio)
  - Biometría / Passkeys (WebAuthn) — se ofrece al usuario después del primer login para registrar su dispositivo
- **Dónde vive la lógica:** FastAPI es dueño de la verificación (password + WebAuthn). NextAuth usa un Credentials provider que llama a los endpoints `/auth/*` del backend + estrategia JWT. El JWT lleva `user_id` (+ tenant activo + rol en ese tenant); FastAPI lo valida en cada request y setea el contexto de seguridad (`app.tenant_id`, `app.user_id`) para RLS.
- **Librerías:** `py_webauthn` (backend, verificación) + `@simplewebauthn/browser` (frontend, ceremonia WebAuthn en el navegador)
- **Sesiones:** 30 días de duración máxima · expiración por inactividad a los 14 días
- **Tabla adicional:** `user_passkeys` — almacena credenciales WebAuthn por dispositivo

**Decisión D7 [2026-06-18]:** Passkeys/WebAuthn en M0, no M1.
**Razón:** implementación de 1-2 días con librerías estándar. UX diferenciador desde el inicio — el profesional entra con la huella entre sesión y sesión, sin tipear contraseña en el celular.

**Decisión D11 [2026-06-19]:** el auth es un **estándar de plataforma**, decidido una vez por EMPRESAS-IA — no una elección de cada instancia. El cliente (no-técnico) nunca elige stack. La verificación de auth vive en el **backend** (FastAPI), no en el frontend.
**Razón:** (a) replicabilidad — "el backend es dueño del auth y del binding al tenant" es agnóstico al frontend, que es la capa que más varía entre instancias; (b) una sola fuente de verdad para dato sensible (mismo servicio que tiene modelos + RLS verifica credenciales y setea el tenant); (c) cumple la testing rule (auth en pytest). El patrón replicable de Capa 0-1 es `token validado → tenant_id → set_tenant(RLS)`; la elección concreta (NextAuth + passkeys) es Capa 2 de Conflur, implementación de referencia de ese patrón.

---

## Canal de comunicación humano ↔ CEO-agente

**Telegram** — bot privado (solo el chat ID de Sebas puede interactuar).

- **M0:** notificaciones proactivas (nuevo usuario, pago recibido, fallo de billing, error crítico) + comandos básicos de consulta ("usuarios activos", "MRR del mes")
- **M1:** CEO-agente conversacional completo — diálogo con contexto, reportes semanales automáticos, gates de aprobación via Telegram

**Librería:** `python-telegram-bot` · **Issue:** SEB-173

**Decisión D8 [2026-06-18]:** Telegram como canal principal de comunicación Sebas ↔ CEO-agente. El humano no abre un dashboard — el CEO-agente viene a él.

---

## Tesorería

Separado de los medios de pago (cómo paga el cliente) — esto es cómo llega el dinero a Sebas.

- **MercadoPago:** liquida directamente en pesos en AR. Sin intermediario.
- **Stripe:** liquida en USD. Flujo: Stripe → Wallbit → Santander AR (Sebas).
  - Wallbit tiene convenio con Santander AR para recibir remesas del exterior de forma simple.
  - Configuración 100% en el dashboard de Stripe y Wallbit — sin impacto en el código.

**Decisión D9 [2026-06-19]:** Wallbit como capa de tesorería para liquidaciones de Stripe en AR.
**Decisión D10 [2026-06-19]:** planes mensual ($15/mes) y anual ($144/año = $12/mes, 20% descuento) desde M0. Toggle mensual/anual visible en el upgrade flow desde el primer día. Stripe maneja el cobro recurrente y dunning automáticamente. MercadoPago implementa suscripciones equivalentes para usuarios LATAM.
**Razón:** convenio Wallbit-Santander simplifica la recepción de USD sin abrir cuenta bancaria en el exterior.

---

## Decisiones pendientes (bloquean inicio de construcción)

| # | Decisión | Opciones | Bloqueante para |
|---|---|---|---|
| P1 | ~~Nombre del producto~~ | ✅ **Conflur** | — |
| P2 | Stack técnico frontend | Next.js / otro | arrancar desarrollo |
| P3 | Stack técnico backend | FastAPI / otro | arrancar desarrollo |
| P4 | Billing LATAM | Stripe + MercadoPago (ambos) | MVP |
| P5 | Dominio y hosting | conflu.io — Cloudflare Registrar | deploy |

---

*Documento iniciado: 2026-06-17*  
*Actualizar en cada sesión cuando se toman decisiones técnicas nuevas.*
