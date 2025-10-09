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

class EmailSettings(BaseSettings):
    # เปิด/ปิดการส่งเมลจริง
    EMAIL_ENABLED: bool = True

    # smtp | console
    EMAIL_BACKEND: str = "smtp"

    # Tencent Exmail:
    # - SSL:   host=smtp.exmail.qq.com, port=465, EMAIL_USE_SSL=true, EMAIL_USE_TLS=false
    # - STARTTLS: host=smtp.exmail.qq.com, port=587, EMAIL_USE_TLS=true, EMAIL_USE_SSL=false
    EMAIL_HOST: str = "smtp.exmail.qq.com"
    EMAIL_PORT: int = 465

    EMAIL_USERNAME: str = "pongsakorn.hr@zkteco.com"   # อีเมลเต็ม เช่น hr@yourcompany.com
    EMAIL_PASSWORD: str = "Keng_1995"   # รหัสผ่านหรือ授权码(หากเปิดใช้งาน)
    EMAIL_FROM: str = "pongsakorn.hr@zkteco.com"       # ควรตรงกับ EMAIL_USERNAME สำหรับ Exmail
    EMAIL_FROM_NAME: str = "HRM System"

    EMAIL_USE_TLS: bool = False
    EMAIL_USE_SSL: bool = True  # Exmail แนะนำ 465/SSL

email_settings = EmailSettings()