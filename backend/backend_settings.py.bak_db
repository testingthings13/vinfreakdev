from pydantic_settings import BaseSettings
from pydantic import Field
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

class Settings(BaseSettings):
    APP_NAME: str = "Vinfreak Admin"
    ADMIN_USER: str = "admin"
    ADMIN_PASS: str = "admin"  # change later
    DATABASE_URL: str = f"sqlite:////home/kali/Desktop/vinfreak/backend/cars.db"
    UPLOAD_DIR: str = (BASE_DIR / "uploads").as_posix()
    SECRET_KEY: str = "change-me"

settings = Settings()
