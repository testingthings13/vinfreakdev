from pydantic_settings import BaseSettings
from pydantic import Field
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

class Settings(BaseSettings):
    APP_NAME: str = "Vinfreak Admin"
    ADMIN_USER: str = "admin"
    ADMIN_PASS: str = "admin"  # change later
    # Default to a SQLite database in the backend directory; override via
    # the DATABASE_URL environment variable for other databases.
    DATABASE_URL: str = f"sqlite:///{BASE_DIR / 'cars.db'}"
    UPLOAD_DIR: str = (BASE_DIR / "uploads").as_posix()
    SECRET_KEY: str = "change-me"

settings = Settings()
