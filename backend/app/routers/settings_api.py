from fastapi import APIRouter
from pydantic import BaseModel

from app.config import settings

router = APIRouter(prefix="/api/settings", tags=["settings"])


class SettingsSchema(BaseModel):
    ollama_url: str
    openai_api_key: str
    openai_base_url: str
    n8n_url: str
    email_host: str
    email_port: str
    email_user: str
    email_use_ssl: bool
    max_upload_mb: int


@router.get("/", response_model=SettingsSchema)
def get_settings():
    # Never send the secret back to the browser. The UI shows a password field
    # and sends back an empty string when the user does not change it.
    return SettingsSchema(
        ollama_url=settings.ollama_url,
        openai_api_key="",
        openai_base_url=settings.openai_base_url,
        n8n_url=settings.n8n_url,
        email_host=settings.email_host,
        email_port=settings.email_port,
        email_user=settings.email_user,
        email_use_ssl=settings.email_use_ssl,
        max_upload_mb=settings.max_upload_mb,
    )


@router.post("/", response_model=SettingsSchema)
def update_settings(settings_in: SettingsSchema):
    settings.ollama_url = settings_in.ollama_url
    # An empty key means "leave the stored key alone" rather than "clear it".
    if settings_in.openai_api_key:
        settings.openai_api_key = settings_in.openai_api_key
    settings.openai_base_url = settings_in.openai_base_url
    settings.n8n_url = settings_in.n8n_url
    settings.email_host = settings_in.email_host
    settings.email_port = settings_in.email_port
    settings.email_user = settings_in.email_user
    settings.email_use_ssl = settings_in.email_use_ssl
    settings.max_upload_mb = settings_in.max_upload_mb

    return SettingsSchema(
        ollama_url=settings.ollama_url,
        openai_api_key="",
        openai_base_url=settings.openai_base_url,
        n8n_url=settings.n8n_url,
        email_host=settings.email_host,
        email_port=settings.email_port,
        email_user=settings.email_user,
        email_use_ssl=settings.email_use_ssl,
        max_upload_mb=settings.max_upload_mb,
    )


@router.get("/test/n8n")
def test_n8n():
    """Server-side reachability probe.

    A browser `no-cors` request always resolves, so the check has to happen here
    where the response status is actually observable.
    """
    import requests

    base = (settings.n8n_url or "").rstrip("/")
    if not base:
        return {"ok": False, "error": "No n8n URL configured"}
    try:
        resp = requests.get(f"{base}/healthz", timeout=5)
        return {"ok": resp.status_code < 500, "status_code": resp.status_code}
    except Exception as exc:
        return {"ok": False, "error": type(exc).__name__}
