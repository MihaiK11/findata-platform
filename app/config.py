from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    mongodb_url: str
    db_name: str = "data-warehouse"
    nasdaq_api_key: str = ""
    anthropic_api_key: str = ""
    findata_api_url: str = "http://127.0.0.1:8000"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()