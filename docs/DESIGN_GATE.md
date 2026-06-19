# Design Gate — MVP psicólogos (M0)

**Versión:** 1.0  
**Fecha:** 2026-06-18  
**Módulo:** MVP psicólogos — primer vertical de Conflur  
**Capa:** 2 (instancia EIA-1)  
**Estado:** 🟡 LISTO CON DEUDA — ver §5 para decisiones abiertas menores

---

## 1. Identidad

| Pregunta | Respuesta |
|---|---|
| ¿Qué es? | MVP del primer vertical de Conflur: herramienta de gestión para psicólogos en práctica privada en LATAM |
| ¿Qué problema resuelve? | El psicólogo gestiona su práctica con papel, Excel y WhatsApp. Conflur le da agenda + notas clínicas con IA + registro de cobros + dashboard financiero en un solo lugar |
| ¿Quién lo usa? | Psicólogos en práctica privada independiente en LATAM (Argentina, México, Colombia como foco inicial) |
| ¿De qué depende? | PostgreSQL/Neon · Anthropic API via LiteLLM · NextAuth · Stripe + MercadoPago |
| ¿Qué depende de él? | Nada aún — es el primer vertical. Futuros verticales heredarán la plataforma core |
| ¿Milestone más próximo? | M0 — 20-30 usuarios freemium activos en 3 semanas desde el primer deploy |

---

## 2. Trazabilidad diseño → implementación

### Entidades / tablas

| Entidad | Doc de diseño | En código (archivo) | Scope M0 | Estado |
|---|---|---|---|---|
| `users` | architecture.md §Auth | `backend/models/user.py` + migración | ✅ incluido | 🔵 pendiente — a crear |
| `user_passkeys` | architecture.md §Auth | `backend/models/passkey.py` + migración | ✅ incluido | 🔵 pendiente — a crear |
| `patients` | architecture.md §Plataforma core | `backend/models/patient.py` + migración | ✅ incluido | 🔵 pendiente — a crear |
| `appointments` | architecture.md §Plataforma core | `backend/models/appointment.py` + migración | ✅ incluido | 🔵 pendiente — a crear |
| `clinical_notes` | architecture.md §Plataforma core | `backend/models/note.py` + migración | ✅ incluido | 🔵 pendiente — a crear |
| `payments` | architecture.md §Plataforma core | `backend/models/payment.py` + migración | ✅ incluido | 🔵 pendiente — a crear |
| `subscriptions` | architecture.md §Billing | `backend/models/subscription.py` + migración | ✅ incluido | 🔵 pendiente — a crear |
| `note_feedback` | architecture.md §Sistema de feedback | `backend/models/note_feedback.py` + migración | ✅ incluido | 🔵 pendiente — a crear |

**Nota de multi-tenancy:** todas las tablas con datos de profesional o paciente tienen `tenant_id` (= `user_id` del profesional). RLS habilitado en `patients`, `appointments`, `clinical_notes`, `payments`.

### Contratos / interfaces

| Contrato | Entre quiénes | Doc de diseño | En código | Scope M0 | Estado |
|---|---|---|---|---|---|
| REST API auth | Frontend ↔ Backend | architecture.md §Auth | `backend/api/auth.py` | ✅ incluido | 🔵 pendiente |
| REST API passkeys | Frontend ↔ Backend | architecture.md §Auth | `backend/api/passkeys.py` | ✅ incluido | 🔵 pendiente |
| REST API agenda | Frontend ↔ Backend | architecture.md §Plataforma core | `backend/api/appointments.py` | ✅ incluido | 🔵 pendiente |
| REST API pacientes | Frontend ↔ Backend | architecture.md §Plataforma core | `backend/api/patients.py` | ✅ incluido | 🔵 pendiente |
| REST API notas | Frontend ↔ Backend | architecture.md §Plataforma core | `backend/api/notes.py` | ✅ incluido | 🔵 pendiente |
| REST API cobros | Frontend ↔ Backend | architecture.md §Plataforma core | `backend/api/payments.py` | ✅ incluido | 🔵 pendiente |
| REST API dashboard | Frontend ↔ Backend | architecture.md §Plataforma core | `backend/api/dashboard.py` | ✅ incluido | 🔵 pendiente |
| LiteLLM → Anthropic | Agente notas ↔ API IA | architecture.md §Stack | `backend/agents/notes_agent.py` | ✅ incluido | 🔵 pendiente |
| Stripe webhooks | Stripe → Backend | architecture.md §Billing | `backend/api/webhooks/stripe.py` | ✅ incluido | 🔵 pendiente |
| MercadoPago webhooks | MercadoPago → Backend | architecture.md §Billing | `backend/api/webhooks/mercadopago.py` | ✅ incluido | 🔵 pendiente |

### KM write — agente de notas

EIA-1 usa dos bases de datos. Ver `../docs/platform-boundary.md` para el detalle completo.

| Tipo de output | Qué contiene | Dónde va | Cómo | Estado |
|---|---|---|---|---|
| **Nota generada** | Texto completo de la nota clínica | `clinical_notes.content` [App DB] | `POST /api/notes/generate` | 🔵 pendiente |
| **Feedback del profesional** | Calificación (1-3) + ediciones del profesional | `note_feedback` [App DB] | `POST /api/notes/{id}/feedback` | 🔵 pendiente |
| **Aprendizaje destilado** | Patrones extraídos del feedback (qué tipos de nota se aceptan, qué se edita) | `aprendizaje` [KM, `tenant_id='eia1'`] | `aprendizaje.py` — proceso de extracción | 🔵 pendiente — M1 |

**Razón de la separación:** `note_feedback` es dato operativo crudo (registro por nota, por profesional). El KM almacena conocimiento destilado (patrones, analogías). El proceso de extracción convierte feedback crudo en aprendizaje estructurado.

---

## 3. Checklist del playbook

### Seguridad Nivel 1

- [x] Credenciales en `.env`, nunca en código — `.env.example` ya existe
- [x] `.env` en `.gitignore` — ya configurado
- [x] `.env.example` completo — ya existe
- [ ] Sin credenciales en historial de git — verificar antes del primer commit real

### Seguridad Nivel 3 — aplica ✅

Conflur almacena datos clínicos de pacientes (terceros que depositan info confidencial).

- [ ] `tenant_id` en todas las tablas relevantes — **desde el inicio, no negociable**
- [ ] RLS en PostgreSQL — habilitado en `patients`, `appointments`, `clinical_notes`, `payments`
- [ ] Audit logs de acceso — **postergado a M1** (decisión: datos clínicos pero no NDAs; mínimo viable primero)
- [ ] Política de retención documentada — si el profesional se da de baja: exportar datos + eliminar en 30 días. Documentar en ToS antes del primer usuario real.

### Estructura de archivos

- [x] `README.md` existe
- [x] `docs/architecture.md` existe
- [x] `docs/progress/` configurado
- [x] `.env.example` existe
- [x] `.gitignore` existe

### Testing

- [ ] Tests para auth (login, passkeys, expiración de sesión)
- [ ] Tests para billing (pago exitoso, fallo, cancelación, webhook)
- [ ] Tests para aislamiento de tenants (un profesional no puede ver datos de otro)
- [ ] Tests para generación de notas (mock de LiteLLM para no consumir tokens en tests)
- [ ] Markers `unit` / `integration` configurados en pytest

### Observabilidad

Va a producción con usuarios reales → aplica:

- [ ] Logging de requests: timestamp + endpoint + status code + `tenant_id`
- [ ] Logging de errores con stack trace completo
- [ ] `LOG_LEVEL` configurable por `.env`
- [ ] **Nunca loguear contenido de notas clínicas ni datos de pacientes**

### Backups y resiliencia

- **DB:** Neon.tech — backups automáticos incluidos (verificar plan antes del primer usuario real)
- **Si Neon cae:** la app queda inoperativa (sin caché local) — aceptable para MVP
- **Recuperación:** restaurar desde backup de Neon; datos de pacientes no se reconstruyen manualmente

---

## 4. Scope explícito M0

Lo que NO entra en M0 y por qué:

| Feature | Versión objetivo | Razón del postergue |
|---|---|---|
| Audit logs de acceso | M1 | Mínimo viable primero; no hay requerimiento regulatorio inmediato |
| Agentes CEO / Crecimiento / CS / Finanzas | M1 | El MVP es el producto; los agentes operativos vienen después de tener usuarios |
| Recordatorios automáticos (SMS/WhatsApp) | M1 | Requiere integración adicional (Twilio/WhatsApp API); no crítico para el MVP |
| Sincronización con Google Calendar | M1 | Útil pero no bloqueante para los primeros usuarios |
| Módulo de cursos/educación | M2 | Segundo revenue stream — después de validar el tool |
| Contenido y comunidad (agente de crecimiento) | M1 | GTM es manual al inicio; Sebas opera las comunidades |
| Verticales adicionales (kinesiólogos, etc.) | M2+ | Validar psicólogos primero |
| App mobile nativa | M2+ | PWA en M0; native app cuando haya tracción |
| Aprendizaje acumulado del agente de notas | M1 | El feedback se recolecta en M0; el loop de mejora se activa en M1 |
| Política de retención completa / ToS | Antes del primer usuario real | Debe existir antes de tener datos reales de pacientes |

---

## 5. Decisiones requeridas antes de arrancar

| # | Pregunta | Opciones | Decisión tomada | Fecha |
|---|---|---|---|---|
| D1 | ¿Qué está incluido en el plan freemium vs pago? | A: N pacientes gratis (ej: 5) · B: N notas/mes gratis · C: tiempo limitado (14 días trial) | **A: hasta 5 pacientes activos en freemium** — más de 5 requiere plan pago | 2026-06-18 |
| D2 | ¿Cómo ingresa el profesional el contenido de la sesión para generar la nota? | A: bullets de texto · B: grabación de audio · C: ambos | **A: bullets de texto en M0** — audio es M1 (mayor complejidad técnica y de privacidad) | 2026-06-18 |
| D3 | ¿En qué moneda se almacenan los cobros? | A: moneda local del profesional · B: USD siempre · C: moneda local + equivalente USD | **A: moneda local** — el profesional trabaja en pesos/soles/etc.; la conversión a USD es un reporte, no el dato base | 2026-06-18 |
| D4 | ¿Qué información lleva el PDF de recibo? | A: mínimo (nombre, fecha, monto) · B: completo (datos fiscales, concepto) | **A: mínimo para M0** — los requerimientos fiscales varían por país; empezar simple y extender por mercado | 2026-06-18 |

> Todas las decisiones de §5 están resueltas. El gate puede avanzar.

---

## 6. Estado del gate

| Estado | Condición |
|---|---|
| 🔴 BLOQUEADO | Hay decisiones abiertas en §5 o GAPs sin resolver en §2 |
| 🟡 LISTO CON DEUDA | Decisiones cerradas; hay items 🔵 documentados como deuda intencional |
| ✅ LISTO | Todo resuelto — desarrollo puede arrancar |

**Estado actual: 🟡 LISTO CON DEUDA**

Deuda intencional documentada:
- Audit logs → M1 (decisión explícita)
- Loop de aprendizaje del agente de notas → M1 (feedback se recolecta en M0)
- Todos los items 🔵 en §2 son código pendiente de escribir, no decisiones pendientes

**El desarrollo puede arrancar.**

---

*Actualizar este archivo antes de cada sesión que agregue entidades nuevas al MVP.*  
*Si surge una entidad nueva en el diseño, agregarla a §2 ANTES de codearla.*
