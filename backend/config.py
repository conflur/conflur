from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"

    # Database — App DB (Neon.tech)
    # DATABASE_URL: rol owner (neondb_owner) — SOLO migraciones/admin (puede saltear RLS).
    DATABASE_URL: str
    # APP_DATABASE_URL: rol de app (conflur_app, NOBYPASSRLS) — runtime de la app.
    # El RLS solo protege si la app se conecta con un rol SIN bypassrls. Si está
    # vacío, cae a DATABASE_URL (solo aceptable en local sin datos reales).
    APP_DATABASE_URL: str = ""
    # Knowledge Module DB (shared platform — aprendizaje table, tenant_id='eia1')
    KM_DATABASE_URL: str = ""
    KM_TENANT_ID: str = "eia1"

    # Auth
    NEXTAUTH_SECRET: str
    NEXTAUTH_URL: str = "http://localhost:3000"

    # WebAuthn / Passkeys
    # RP_ID = dominio efectivo (sin esquema ni puerto). Dev: localhost · Prod: conflur.com
    WEBAUTHN_RP_ID: str = "localhost"
    WEBAUTHN_RP_NAME: str = "Conflur"
    # Origin exacto desde donde corre el frontend. Dev: http://localhost:3000 · Prod: https://conflur.com
    WEBAUTHN_ORIGIN: str = "http://localhost:3000"

    # Anthropic / LiteLLM — modelo configurable por agente (default Sonnet 4.6)
    ANTHROPIC_API_KEY: str
    NOTES_MODEL: str = "claude-sonnet-4-6"
    CEO_MODEL: str = "claude-sonnet-4-6"
    CONTENT_MODEL: str = "claude-sonnet-4-6"
    CS_MODEL: str = "claude-sonnet-4-6"
    FINANCE_MODEL: str = "claude-sonnet-4-6"

    # Billing
    STRIPE_SECRET_KEY: str
    STRIPE_WEBHOOK_SECRET: str
    MERCADOPAGO_ACCESS_TOKEN: str
    MERCADOPAGO_WEBHOOK_SECRET: str

    # Telegram
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""

    # Frontend (en backend/.env para tener un único archivo de config en local)
    NEXT_PUBLIC_API_URL: str = "http://localhost:8000"

    # CORS
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000"]

    class Config:
        env_file = ".env"


settings = Settings()
