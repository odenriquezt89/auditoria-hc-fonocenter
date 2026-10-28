"""
Configuración global del sistema de notificaciones.
Carga variables de entorno para SMTP, SendGrid, Twilio y Meta WhatsApp Cloud API.
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class AppConfig:
    # Modo de ejecución (True = simulación y log detallado sin enviar mensajes reales)
    DRY_RUN: bool = True

    # Configuración de Correo SMTP
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_USE_TLS: bool = True
    EMAIL_FROM_ADDRESS: str = "calidad@fonocenter.com"
    EMAIL_FROM_NAME: str = "Comité Calidad FONOCENTER IPS"

    # Configuración API SendGrid (Alternativa a SMTP)
    SENDGRID_API_KEY: Optional[str] = None

    # Configuración Twilio (WhatsApp API)
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_WHATSAPP_FROM: str = "whatsapp:+14155238886"  # Twilio Sandbox o Número oficial

    # Configuración Meta WhatsApp Cloud API (Alternativa oficial a Twilio)
    META_WA_PHONE_NUMBER_ID: Optional[str] = None
    META_WA_ACCESS_TOKEN: Optional[str] = None

    # Configuración de Plantillas y Rutas
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    TEMPLATES_DIR: str = os.path.join(BASE_DIR, "templates")
    DATA_DIR: str = os.path.join(BASE_DIR, "data")
    REPORTS_DIR: str = os.path.join(BASE_DIR, "reports")


def load_config() -> AppConfig:
    """Carga configuración desde variables de entorno del sistema."""
    # Intentar cargar .env si existe manualmente sin dependencias forzadas
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, val = line.split("=", 1)
                        key = key.strip()
                        val = val.strip().strip("'").strip('"')
                        if key not in os.environ:
                            os.environ[key] = val
        except Exception:
            pass

    dry_run_env = os.getenv("NOTIFICATIONS_DRY_RUN", "true").lower() in ("true", "1", "yes")

    config = AppConfig(
        DRY_RUN=dry_run_env,
        SMTP_HOST=os.getenv("SMTP_HOST", "smtp.gmail.com"),
        SMTP_PORT=int(os.getenv("SMTP_PORT", "587")),
        SMTP_USER=os.getenv("SMTP_USER", ""),
        SMTP_PASSWORD=os.getenv("SMTP_PASSWORD", ""),
        SMTP_USE_TLS=os.getenv("SMTP_USE_TLS", "true").lower() in ("true", "1", "yes"),
        EMAIL_FROM_ADDRESS=os.getenv("EMAIL_FROM_ADDRESS", "calidad@fonocenter.com"),
        EMAIL_FROM_NAME=os.getenv("EMAIL_FROM_NAME", "Comité Calidad FONOCENTER IPS"),
        SENDGRID_API_KEY=os.getenv("SENDGRID_API_KEY"),
        TWILIO_ACCOUNT_SID=os.getenv("TWILIO_ACCOUNT_SID"),
        TWILIO_AUTH_TOKEN=os.getenv("TWILIO_AUTH_TOKEN"),
        TWILIO_WHATSAPP_FROM=os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886"),
        META_WA_PHONE_NUMBER_ID=os.getenv("META_WA_PHONE_NUMBER_ID"),
        META_WA_ACCESS_TOKEN=os.getenv("META_WA_ACCESS_TOKEN"),
    )

    os.makedirs(config.REPORTS_DIR, exist_ok=True)
    return config
