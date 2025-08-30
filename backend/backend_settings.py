from pydantic_settings import BaseSettings
from pydantic import Field
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

class Settings(BaseSettings):
    APP_NAME: str = "Vinfreak Admin"
    ADMIN_USER: str = "admin"
    ADMIN_PASS: str = "admin"  # change later
    # Default to a SQLite database in the backend directory. In
    # production set the DATABASE_URL environment variable to point to a
    # database on a persistent volume or an external service.
    DATABASE_URL: str = f"sqlite:///{BASE_DIR / 'cars.db'}"
    ADMIN_DATABASE_URL: str = f"sqlite:///{BASE_DIR / 'admin.db'}"
    UPLOAD_DIR: str = (BASE_DIR / "uploads").as_posix()
    SECRET_KEY: str = "change-me"

settings = Settings()
