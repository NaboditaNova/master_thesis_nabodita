from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # keep whatever you already had (app_env, chunk_size, etc.)
    app_env: str = Field(default="dev", alias="APP_ENV")
    chunk_size: int = Field(default=500, alias="CHUNK_SIZE")

    # IMPORTANT: make optional
    database_url: str | None = Field(default=None, alias="DATABASE_URL")

    # (optional) expose TLS flags if you want to print them in `env`:
    db_ssl: int | bool | str = Field(default=0, alias="DB_SSL")
    db_ssl_verify: int | bool | str = Field(default=1, alias="DB_SSL_VERIFY")
    db_ssl_ca: str | None = Field(default=None, alias="DB_SSL_CA")


# class Settings(BaseSettings):
#     app_env: str = "local"
#     database_url: str
#     chunk_size: int = 500

#     class Config:
#         env_file = ".env"
#         extra = "ignore"


settings = Settings()
