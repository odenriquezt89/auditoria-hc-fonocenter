"""
Módulo de Notificaciones Multicanal para Auditoría Médica - FONOCENTER IPS
Soporta Email (SMTP / SendGrid API) y WhatsApp (Twilio / Meta Cloud API) con validaciones y generación de reportes.
"""

from .models import (
    DoctorRecord,
    AuditNotificationData,
    NotificationResult,
    ChannelType,
    DeliveryStatus
)
from .dispatcher import NotificationDispatcher
from .validators import validate_email, validate_and_format_phone
from .report_generator import generate_consolidation_report

__all__ = [
    "DoctorRecord",
    "AuditNotificationData",
    "NotificationResult",
    "ChannelType",
    "DeliveryStatus",
    "NotificationDispatcher",
    "validate_email",
    "validate_and_format_phone",
    "generate_consolidation_report",
]
