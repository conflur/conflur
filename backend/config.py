from urllib.parse import urlparse

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

    # Frontend — ÚNICA variable a setear por entorno en el backend. De acá se
    # derivan CORS, WebAuthn origin y RP_ID. Dev: http://localhost:3000 ·
    # Prod: dominio del frontend en Vercel.
    FRONTEND_URL: str = "http://localhost:3000"

    WEBAUTHN_RP_NAME: str = "Conflur"

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

    # Telepsicología — proveedor de videollamada (abstraído, swappable).
    # Default Jitsi Meet: sala única e inadivinable, cifrada, sin credenciales.
    MEETING_PROVIDER: str = "jitsi"
    MEETING_JITSI_BASE: str = "https://meet.jit.si"

    # Frontend (en backend/.env para tener un único archivo de config en local)
    NEXT_PUBLIC_API_URL: str = "http://localhost:8000"

    # --- Derivados de FRONTEND_URL (no se setean por env) ------------------- #
    @property
    def allowed_origins(self) -> list[str]:
        """Origins permitidos para CORS: el frontend + localhost para dev."""
        return list(dict.fromkeys([self.FRONTEND_URL, "http://localhost:3000"]))

    @property
    def webauthn_origin(self) -> str:
        """Origin exacto esperado en la ceremonia WebAuthn."""
        return self.FRONTEND_URL

    @property
    def webauthn_rp_id(self) -> str:
        """RP ID = hostname del frontend (sin esquema ni puerto)."""
        return urlparse(self.FRONTEND_URL).hostname or "localhost"

    class Config:
        env_file = ".env"


settings = Settings()
