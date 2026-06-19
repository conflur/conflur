# Conflur

Herramienta de gestión para profesionales de salud en práctica privada en LATAM.
Agenda · Notas clínicas con IA · Cobros · Dashboard financiero.

**Vertical activo:** psicólogos · **Precio:** freemium → $15/mes

---

## Levantar el ambiente local

### Prerequisitos

- Docker + Docker Compose
- Cuenta en [Neon.tech](https://neon.tech) (base de datos)
- API key de [Anthropic](https://console.anthropic.com)

### Setup

```bash
# 1. Clonar el repo
git clone <repo-url>
cd eia1

# 2. Configurar variables de entorno
cp .env.example .env
# Editar .env con los valores reales

# 3. Levantar todo
docker compose up
```

El ambiente queda disponible en:
- **Frontend:** http://localhost:3000
- **Backend:** http://localhost:8000
- **API docs:** http://localhost:8000/docs

### Comandos útiles

```bash
# Solo backend
docker compose up backend

# Tests del backend
docker compose run --rm backend pytest -m unit

# Rebuild después de cambios en dependencias
docker compose build
```

---

## Estructura

```
eia1/
├── frontend/          # Next.js + TypeScript → Vercel
│   └── src/
│       ├── app/       # App Router (páginas)
│       ├── components/
│       └── lib/
├── backend/           # Python + FastAPI → Railway
│   ├── api/           # Endpoints REST
│   │   └── webhooks/  # Stripe + MercadoPago
│   ├── models/        # SQLAlchemy models
│   ├── agents/        # Agentes IA (notas, CEO, etc.)
│   ├── utils/
│   ├── tests/
│   ├── main.py
│   └── config.py
├── .env.example       # Variables requeridas
└── .gitignore
```

---

## Documentación

- [`agents.md`](agents.md) — contexto activo (leer al inicio de cada sesión)
- [`docs/architecture.md`](docs/architecture.md) — decisiones técnicas
- [`docs/DESIGN_GATE.md`](docs/DESIGN_GATE.md) — gate del MVP psicólogos
- [`docs/progress/`](docs/progress/) — logs de sesión
- [`../docs/EIA1_Foundation_Document.md`](../docs/EIA1_Foundation_Document.md) — diseño fundacional

## Parte de

[EMPRESAS-IA](../) — plataforma para empresas 100% agénticas
