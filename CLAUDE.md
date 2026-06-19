# CLAUDE.md — EIA-1

## Norte global — leer primero, siempre

> **EMPRESAS-IA es el producto.** El producto es una plataforma para que cualquier persona, sin saber programar, pueda crear una empresa 100% agéntica describiéndola en lenguaje natural.
>
> **EIA-1 / Conflur NO es el producto final.** Es la segunda instancia que valida que el modelo es replicable. CRIZA fue la primera. Cada instancia que se construye prueba que el proceso funciona y afina el molde para la siguiente.
>
> Esto significa: cada decisión de diseño en EIA-1 debe poder documentarse como un paso replicable. Si algo no se puede replicar para otra instancia, hay que rediseñarlo.
>
> Fuente: `../docs/VISION-EMPRESAS-IA.md` · `../docs/EIA1_Foundation_Document.md`

---

## Qué es EIA-1 / Conflur

Segunda empresa agéntica de la plataforma EMPRESAS-IA (Capa 2). **Nombre del producto: Conflur** (conflur.com). Software B2C para profesionales de salud en práctica privada en LATAM. Portafolio de vertical stacks: tool (agenda + notas IA + billing + dashboard financiero) + contenido + curso, uno por especialidad.

**Primer vertical:** psicólogos. **Mercado:** LATAM, español. **Precio:** $15/mes.

> Esta instancia es completamente independiente de CRIZA y DPN.
> Lo que EIA-1 sabe, aprende y almacena NO se filtra a otras instancias.

---

## Protocolo de inicio de sesión

**Al iniciar cualquier sesión en EIA-1:**

1. Leer el bloque **Norte global** de este CLAUDE.md — el norte no es negociable y no cambia
2. Leer `agents.md` — contexto activo, pendientes, flags abiertos
3. Leer el cycle activo en Linear (proyecto EIA-1, equipo Sebabizz._dev)
4. Leer el último `docs/progress/YYYY-MM-DD.md`
5. Mostrar: qué está In Progress, qué está en Todo, si hay Bloqueados
6. Preguntar: "¿Arrancamos con X o preferís otra cosa?"

---

## Fuentes de verdad

| Fuente | Rol | Cuándo leer |
|---|---|---|
| `agents.md` | Contexto activo: estado, pendientes, flags | Siempre al iniciar |
| Linear | Estado operativo de tareas | Siempre al iniciar |
| `docs/architecture.md` | Decisiones técnicas tomadas | Si la tarea requiere contexto técnico |
| `docs/progress/YYYY-MM-DD.md` | Log de la sesión anterior | Si hay duda de qué quedó pendiente |
| **`../docs/NEW_INSTANCE_PROTOCOL.md`** | **Protocolo canónico de inicio de instancia — lectura, preguntas, checklist, errores frecuentes** | **Al iniciar una instancia nueva desde cero** |
| `../docs/VISION-EMPRESAS-IA.md` | Norte global del producto — qué es EMPRESAS-IA y para qué existe | **Siempre al iniciar** — es el norte |
| `../docs/EIA1_Foundation_Document.md` | Diseño fundacional completo: exploración, decisiones, agentes, GTM | Si la tarea afecta diseño o modelo de negocio |
| **`../docs/platform-boundary.md`** | **Qué es Capa 0-1 vs Capa 2 — dónde vive cada dato y módulo** | **Siempre que haya una decisión sobre dónde pertenece algo** |

---

## Principios que heredan del CLAUDE.md de plataforma

- **Plataforma primero:** EIA-1 es Capa 2. Lo genérico va en `platform/` o `knowledge_module/`.
- **Consultar antes de actuar:** ante duda, preguntar a Sebas antes de proceder.
- **Veracidad por dato:** establecido (con fuente) / asumido (con peso) / a-confirmar.
- **Design Gate antes de codear:** completar `docs/DESIGN_GATE.md` antes de arrancar cualquier módulo.
- **Objetivo primero sobre costo de tokens:** usar Sonnet 4.6 por defecto.
- **Decisión final siempre humana:** el sistema arma y propone; Sebas decide.

---

## Regla de capa — qué es plataforma y qué es Conflur

**Pregunta obligatoria antes de diseñar o construir cualquier pieza:**
> ¿Esto serviría igual para CRIZA, DPN o una futura instancia sin modificarlo?
> - Sí → va en `platform/` o `knowledge_module/` (Capa 0-1)
> - No → va en `eia1/` (Capa 2)

### Tabla de referencia rápida

| Componente | Dónde va | Por qué |
|---|---|---|
| Knowledge Module (infraestructura, código base) | `knowledge_module/` — plataforma | Cualquier instancia lo usa |
| Datos del KM de Conflur | `knowledge_module/` con `tenant_id="eia1"` | Infraestructura compartida, datos aislados |
| Playbook, Design Gate template | `docs/` — plataforma | Aplica a todos los proyectos |
| **El producto SaaS** (agenda, notas IA, billing, dashboard) | `eia1/` — Conflur | Específico de profesionales de salud |
| **Auth** (NextAuth + WebAuthn) | `eia1/` — Conflur | Decisión de Conflur; otra instancia puede elegir otra solución |
| **Modelos de datos** (patients, appointments, notes, payments) | `eia1/` — Conflur | Dominio de salud privada |
| **Skins verticales** (templates de notas por especialidad) | `eia1/` — Conflur | Específicos de cada profesión |
| **Billing** (Stripe + MercadoPago) | `eia1/` — Conflur | Decisión de Conflur |
| **Agentes de Conflur** (notas, CEO, CS, crecimiento, finanzas) | `eia1/agents/` — Conflur | Prompts y lógica del dominio de salud |
| **Telegram bot** (CEO-agente ↔ Sebas) | `eia1/` — Conflur | Canal de esta empresa |
| **Dashboard /admin** | `eia1/` — Conflur | Monitoreo de Conflur |
| **GTM** (comunidades, canales, contenido) | `eia1/` — Conflur | Estrategia específica de salud en LATAM |

### Casos grises

- **Docker:** el patrón es genérico (playbook). El `docker-compose.yml` concreto con los servicios de Conflur va en `eia1/`.
- **LiteLLM:** la idea de abstracción es de plataforma. La configuración específica (variables `.env`, modelos por agente) va en `eia1/`.
- **Seguridad Nivel 3 / RLS:** el patrón está en el playbook. La implementación en las tablas de Conflur va en `eia1/`.

---

## Durante el trabajo

- Al empezar una tarea → moverla a **In Progress** en Linear inmediatamente
- Al terminar → verificar Definition of Done ANTES de marcarla **Done**
- Al tomar una decisión técnica → registrar en `docs/architecture.md`
- Si surge un bloqueador → label **Bloqueado** + nota en Linear
- Si surge tarea nueva → crearla en Linear antes de arrancar

---

## Al cerrar cada sesión

1. Verificar que todo lo trabajado esté actualizado en Linear
2. Tareas a medias → dejarlas In Progress con nota del estado
3. Crear `docs/progress/YYYY-MM-DD.md` con resumen de la sesión
4. Sugerir cuál debería ser la próxima sesión

---

## Aislamiento de contexto

Abrir Claude Code **desde `EMPRESAS-IA/eia1/`** para trabajar en EIA-1.
Nunca desde `EMPRESAS-IA/criza/` ni mezclar contextos en una misma sesión.
