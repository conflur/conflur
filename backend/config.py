from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"

    # Database — App DB (Neon.tech)
    DATABASE_URL: str
    # Knowledge Module DB (shared platform — aprendizaje table, tenant_id='eia1')
    KM_DATABASE_URL: str = ""
    KM_TENANT_ID: str = "eia1"

    # Auth
    NEXTAUTH_SECRET: str
    NEXTAUTH_URL: str = "http://localhost:3000"

    # Anthropic / LiteLLM
    ANTHROPIC_API_KEY: str
    NOTES_MODEL: str = "claude-sonnet-4-6"
    CEO_MODEL: str = "claude-sonnet-4-6"

    # Billing
    STRIPE_SECRET_KEY: str
    STRIPE_WEBHOOK_SECRET: str
    MERCADOPAGO_ACCESS_TOKEN: str
    MERCADOPAGO_WEBHOOK_SECRET: str

    # Telegram
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""

    # CORS
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000"]

    class Config:
        env_file = ".env"


settings = Settings()
