from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    mongodb_url: str
    db_name: str = "data-warehouse"
    nasdaq_api_key: str = ""
    anthropic_api_key: str = ""

    class Config:
        env_file = ".env"

settings = Settings()