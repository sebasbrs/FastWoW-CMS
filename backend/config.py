from os import getenv
from pathlib import Path

from dotenv import load_dotenv


# Load .env from backend/ if present (development convenience)
BASE_DIR = Path(__file__).resolve().parent
env_path = BASE_DIR / ".env"
if env_path.exists():
    load_dotenv(env_path)


def _env_or(key: str, default: str) -> str:
    return getenv(key, default)


# Database configuration for multiple AzerothCore schemas
# Uses environment variables, with sensible defaults for local dev
DB_CONFIG = {
    "cms": {
        "host": _env_or("DB_CMS_HOST", "127.0.0.1"),
        "port": int(_env_or("DB_CMS_PORT", "3306")),
        "user": _env_or("DB_CMS_USER", "root"),
        "password": _env_or("DB_CMS_PASSWORD", ""),
        "db": _env_or("DB_CMS_NAME", "cms"),
    },
    "auth": {
        "host": _env_or("DB_AUTH_HOST", "127.0.0.1"),
        "port": int(_env_or("DB_AUTH_PORT", "3306")),
        "user": _env_or("DB_AUTH_USER", "root"),
        "password": _env_or("DB_AUTH_PASSWORD", ""),
        "db": _env_or("DB_AUTH_NAME", "auth"),
    },
    "characters": {
        "host": _env_or("DB_CHAR_HOST", "127.0.0.1"),
        "port": int(_env_or("DB_CHAR_PORT", "3306")),
        "user": _env_or("DB_CHAR_USER", "root"),
        "password": _env_or("DB_CHAR_PASSWORD", ""),
        "db": _env_or("DB_CHAR_NAME", "characters"),
    },
    "world": {
        "host": _env_or("DB_WORLD_HOST", "127.0.0.1"),
        "port": int(_env_or("DB_WORLD_PORT", "3306")),
        "user": _env_or("DB_WORLD_USER", "root"),
        "password": _env_or("DB_WORLD_PASSWORD", ""),
        "db": _env_or("DB_WORLD_NAME", "world"),
    },
}


DEFAULT_POOL_ARGS = {
    "minsize": int(_env_or("DB_POOL_MINSIZE", "1")),
    "maxsize": int(_env_or("DB_POOL_MAXSIZE", "10")),
    # You can add more aiomysql.create_pool kwargs here if needed
}


# JWT settings
JWT_SECRET = _env_or("JWT_SECRET", "change-me-to-a-strong-secret")
JWT_ALGORITHM = _env_or("JWT_ALGORITHM", "HS256")
# token lifetime in seconds
JWT_EXP_SECONDS = int(_env_or("JWT_EXP_SECONDS", "3600"))

# SMTP / Email settings for password recovery
SMTP_HOST = _env_or("SMTP_HOST", "localhost")
SMTP_PORT = int(_env_or("SMTP_PORT", "25"))
SMTP_USER = _env_or("SMTP_USER", "")
SMTP_PASSWORD = _env_or("SMTP_PASSWORD", "")
SMTP_STARTTLS = _env_or("SMTP_STARTTLS", "1") == "1"
EMAIL_FROM = _env_or("EMAIL_FROM", "no-reply@example.com")
PASSWORD_RESET_TOKEN_EXP_MIN = int(_env_or("PASSWORD_RESET_TOKEN_EXP_MIN", "30"))
EMAIL_VERIFICATION_TOKEN_EXP_MIN = int(_env_or("EMAIL_VERIFICATION_TOKEN_EXP_MIN", "1440"))  # 24h por defecto
