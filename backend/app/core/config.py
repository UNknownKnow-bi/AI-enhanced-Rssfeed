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

    # DeepSeek AI Labeling
    DEEPSEEK_API_KEY: str = "sk-35ab39b6ccb14251a3173a414221da29"
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-chat"
    AI_BATCH_SIZE: int = 3  # Number of articles to process per API call
    AI_MAX_RETRIES: int = 2  # Maximum retry attempts on API failure
    AI_RETRY_INTERVAL_MINUTES: int = 15  # Interval for retrying error articles
    AI_RETRY_BATCH_DELAY_SECONDS: int = 10  # Delay between batches when retrying

    # AI Summary Configuration
    AI_SUMMARY_BATCH_SIZE: int = 3  # Number of articles to summarize per batch
    AI_SUMMARY_TIMEOUT_SECONDS: int = 30  # Timeout for summary API requests
    AI_SUMMARY_MAX_CONCURRENT: int = 4  # Maximum concurrent summary requests
    AI_SUMMARY_INTERVAL_MINUTES: int = 15  # Interval for processing pending summaries
    AI_SUMMARY_RETRY_INTERVAL_MINUTES: int = 15  # Interval for retrying failed summaries
    # Delay between labeling batches (seconds)
    AI_LABEL_BATCH_DELAY_SECONDS: int = 3

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
