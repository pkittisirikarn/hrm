# config/settings.py
from pydantic_settings import BaseSettings, SettingsConfigDict
import os

class Settings(BaseSettings):
    """
    Class สำหรับเก็บการตั้งค่าของโปรเจกต์
    ข้อมูลจะถูกอ่านจาก Environment Variables หรือไฟล์ .env
    """
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # การตั้งค่าฐานข้อมูล
    DATABASE_URL: str = "sqlite:///./sql_app.db"

    # JWT Secret Key (สำหรับ Authentication)
    SECRET_KEY: str = "your-super-secret-key-please-change-this-to-a-strong-random-string"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Email Settings (สำหรับ Meeting Module)
    MAIL_USERNAME: str = os.getenv("MAIL_USERNAME", "your_email@example.com")
    MAIL_PASSWORD: str = os.getenv("MAIL_PASSWORD", "your_email_app_password")
    MAIL_FROM: str = os.getenv("MAIL_FROM", "your_email@example.com")
    MAIL_PORT: int = int(os.getenv("MAIL_PORT", 587))
    MAIL_SERVER: str = os.getenv("MAIL_SERVER", "smtp.example.com")
    MAIL_TLS: bool = os.getenv("MAIL_TLS", "True").lower() == "true"
    MAIL_SSL: bool = os.getenv("MAIL_SSL", "False").lower() == "true"
    USE_CREDENTIALS: bool = os.getenv("USE_CREDENTIALS", "True").lower() == "true"
    VALIDATE_CERTS: bool = os.getenv("VALIDATE_CERTS", "True").lower() == "true"


settings = Settings()
