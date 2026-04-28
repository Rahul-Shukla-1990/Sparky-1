from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Maritime OSINT Agent"
    app_env: str = "local"
    database_url: str = "sqlite:///./data/maritime_osint.db"
    secret_key: str = "change-this-local-secret"
    scheduler_enabled: bool = True
    collection_interval_minutes: int = 30
    telegram_polling_enabled: bool = False
    telegram_polling_interval_minutes: int = 1
    telegram_bot_token: str = ""
    telegram_allowed_chat_ids: str = ""
    telegram_allowed_user_ids: str = ""
    aoi_mode: str = "broad_ior"
    export_dir: str = "./data/exports"
    brief_dir: str = "./data/briefs"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()


def csv_to_set(value: str) -> set[str]:
    if not value:
        return set()
    return {item.strip() for item in value.split(",") if item.strip()}
