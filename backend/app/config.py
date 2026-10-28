import os
import secrets as _secrets
import sys

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _generate_secret_key() -> str:
    """Generate a random secret key if none is configured."""
    return _secrets.token_hex(32)


def _default_data_dir() -> str:
    """Return the user data directory, preferring a packaged app location."""
    # Allow override via environment variable (set by Electron wrapper or launcher).
    env_dir = os.environ.get("JOB_HUNTER_DATA_DIR")
    if env_dir:
        return env_dir

    # Detect packaged app (PyInstaller / Electron child process).
    if getattr(sys, "frozen", False):
        # PyInstaller _MEIPASS-based executable.
        if hasattr(sys, "_MEIPASS"):
            base = os.path.dirname(sys.executable)
        else:
            base = os.path.dirname(os.path.abspath(sys.executable))
    else:
        base = os.path.dirname(os.path.abspath(__file__))

    # On macOS package: ~/Library/Application Support/NS
    # On Windows package: %APPDATA%/NS
    # Fallback: ./data (relative to backend dir) for dev
    if sys.platform == "darwin":
        support = os.path.expanduser("~/Library/Application Support/NS")
        if os.path.isdir(support) or os.environ.get("NS_PACKAGED"):
            return support
    elif sys.platform == "win32":
        appdata = os.environ.get("APPDATA", "")
        if appdata:
            return os.path.join(appdata, "NS")

    # Development / fallback
    return os.path.join(base, "data")


def _default_upload_dir(data_dir: str) -> str:
    return os.path.join(data_dir, "uploads")


_data_dir = _default_data_dir()
_upload_dir = _default_upload_dir(_data_dir)


class Settings(BaseSettings):
    database_url: str = Field(default="sqlite:///" + os.path.join(_data_dir, "job_hunter.db"))
    secret_key: str = Field(default_factory=_generate_secret_key)
    app_env: str = Field(default="production" if os.environ.get("NS_PACKAGED") else "development")
    cors_origins: str = Field(default="http://localhost:5173,http://127.0.0.1:5173,http://localhost:5173")
    upload_dir: str = Field(default=_upload_dir)
    max_upload_mb: int = Field(default=10)
    ollama_url: str = Field(default="http://localhost:11434")
    openai_api_key: str = Field(default="")
    openai_base_url: str = Field(default="https://api.openai.com/v1")
    n8n_url: str = Field(default="http://localhost:5678")
    n8n_user: str = Field(default="")
    n8n_password: str = Field(default="")
    email_host: str = Field(default="")
    email_port: str = Field(default="")
    email_user: str = Field(default="")
    email_password: str = Field(default="")
    email_use_ssl: bool = Field(default=True)
    webhook_secret: str = Field(default="")

    adzuna_app_id: str = Field(default="")
    adzuna_app_key: str = Field(default="")
    remotive_api_key: str = Field(default="")
    jsearch_api_key: str = Field(default="")
    usajobs_api_key: str = Field(default="")
    user_agent: str = Field(default="NS/1.0 (contact@example.com)")
    data_dir: str = Field(default=_data_dir)

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()

# Create runtime directories.
os.makedirs(settings.data_dir, exist_ok=True)
os.makedirs(settings.upload_dir, exist_ok=True)
