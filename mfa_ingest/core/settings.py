from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_env: str = "local"
    database_url: str
    chunk_size: int = 500

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
