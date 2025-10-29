from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = Field(default="dev", alias="APP_ENV")
    chunk_size: int = Field(default=500, alias="CHUNK_SIZE")

    database_url: str | None = Field(default=None, alias="DATABASE_URL")

    db_ssl: int | bool | str = Field(default=0, alias="DB_SSL")
    db_ssl_verify: int | bool | str = Field(default=1, alias="DB_SSL_VERIFY")
    db_ssl_ca: str | None = Field(default=None, alias="DB_SSL_CA")


settings = Settings()
