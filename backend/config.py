from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./court_watch.db"
    raw_data_dir: str = "./data/raw"
    log_dir: str = "./data/logs"
    log_level: str = "info"
    timezone: str = "America/Los_Angeles"
    target_date_mode: str = "today"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def raw_data_path(self) -> Path:
        return Path(self.raw_data_dir)

    @property
    def log_path(self) -> Path:
        return Path(self.log_dir)


settings = Settings()
