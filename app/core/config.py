import os
from typing import List
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_SECRET_KEY = "change-this-in-production-use-a-secure-random-key-at-least-32-chars"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_ENV: str = "development"  # development | staging | production
    SECRET_KEY: str = DEFAULT_SECRET_KEY
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    DATABASE_URL: str = "postgresql://topline:topline_secret@127.0.0.1:5432/topline_dev"
    TEST_DATABASE_URL: str = "postgresql://topline:topline_secret@127.0.0.1:5432/topline_test"

    PLATFORM_ACCESS_FEE_MINOR: int = 100000  # KSh 1,000 in minor units (cents)
    PLATFORM_ACCESS_CURRENCY: str = "KES"

    DOCUMENT_STORAGE_DIR: str = os.path.join(BASE_DIR, "storage", "documents")
    MAX_UPLOAD_SIZE_BYTES: int = 5 * 1024 * 1024  # 5 MB
    ALLOWED_DOCUMENT_MIME_TYPES: List[str] = [
        "application/pdf",
        "image/jpeg",
        "image/png",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ]

    # M-Pesa Daraja
    MPESA_ENVIRONMENT: str = "sandbox"  # mock | sandbox | production
    MPESA_CONSUMER_KEY: str = "placeholder_consumer_key"
    MPESA_CONSUMER_SECRET: str = "placeholder_consumer_secret"
    MPESA_SHORTCODE: str = "174379"
    MPESA_PASSKEY: str = "placeholder_passkey"
    MPESA_CALLBACK_URL: str = "http://127.0.0.1:8000/api/v1/payments/mpesa/callback"
    # Shared secret appended to the callback URL (?token=...). Required in production.
    MPESA_CALLBACK_TOKEN: str = ""

    # OTP Provider: mock (returns code in API response, dev only) / none / <real provider>
    OTP_PROVIDER: str = "mock"
    OTP_EXPIRY_MINUTES: int = 10

    @field_validator("DATABASE_URL", "TEST_DATABASE_URL", mode="before")
    @classmethod
    def _normalize_db_url(cls, v):
        """Fly/Heroku-style postgres:// and bare postgresql:// -> psycopg v3 driver."""
        if isinstance(v, str):
            for prefix in ("postgres://", "postgresql://"):
                if v.startswith(prefix):
                    return "postgresql+psycopg://" + v[len(prefix):]
        return v

    @model_validator(mode="after")
    def _check_production_settings(self):
        if self.APP_ENV == "production":
            problems = []
            if self.SECRET_KEY == DEFAULT_SECRET_KEY or len(self.SECRET_KEY) < 32:
                problems.append("SECRET_KEY must be a random string of at least 32 characters")
            if not self.MPESA_CALLBACK_TOKEN or len(self.MPESA_CALLBACK_TOKEN) < 24:
                problems.append("MPESA_CALLBACK_TOKEN must be set (at least 24 characters)")
            if self.OTP_PROVIDER == "mock":
                problems.append("OTP_PROVIDER=mock would expose OTP codes; use 'none' or a real provider")
            if problems:
                raise ValueError("Unsafe production configuration: " + "; ".join(problems))
        return self

    @property
    def IS_PRODUCTION(self) -> bool:
        return self.APP_ENV == "production"


settings = Settings()
