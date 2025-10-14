from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str

    # Application
    DEBUG: bool = False
    SECRET_KEY: str

    # RSS Scraping
    SCRAPE_INTERVAL_MINUTES: int = 15
    SOURCE_FETCH_GAP_SECONDS: int = 120

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
