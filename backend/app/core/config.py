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

    # Feed Cache
    FEED_CACHE_TTL_SECONDS: int = 180  # 3 minutes
    FEED_CACHE_MAX_SIZE: int = 999  # Maximum number of feeds to cache

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
