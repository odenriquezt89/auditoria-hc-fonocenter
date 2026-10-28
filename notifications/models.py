"""
Modelos de datos con validaciones y tipado fuerte (type hints).
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any


class ChannelType(str, Enum):
    EMAIL = "EMAIL"
    WHATSAPP = "WHATSAPP"
    BOTH = "BOTH"


class DeliveryStatus(str, Enum):
    SENT = "ENVIADO"
    FAILED = "FALLIDO"
    SKIPPED_INVALID_DATA = "OMITIDO_DATOS_INVALIDOS"
    DRY_RUN_SUCCESS = "SIMULADO_EXITOSO"


@dataclass
class DoctorRecord:
    """Información base del médico en la institución."""
    name: str
    phone: str
    email: str
    specialty: str = "Medicina General"


@dataclass
class AuditNotificationData:
    """Datos de una auditoría clínica listos para notificar."""
    hc_number: str
    doctor_name: str
    specialty: str
    phone: str
    email: str
    score: float
    risk_level: str
    finding_detail: str
    weak_criterion: Optional[str] = None
    audit_date: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))

    @property
    def is_conforme(self) -> bool:
        return self.score >= 90.0

    @property
    def is_moderado(self) -> bool:
        return 70.0 <= self.score < 90.0

    @property
    def is_critico(self) -> bool:
        return self.score < 70.0


@dataclass
class NotificationResult:
    """Resultado de la ejecución de una notificación individual."""
    hc_number: str
    doctor_name: str
    channel: ChannelType
    status: DeliveryStatus
    recipient: str
    timestamp: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    message_id: Optional[str] = None
    error_message: Optional[str] = None
    rendered_preview: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ID_Historia_Clinica": self.hc_number,
            "Medico": self.doctor_name,
            "Canal": self.channel.value,
            "Estado": self.status.value,
            "Destinatario": self.recipient,
            "Fecha_Hora": self.timestamp,
            "ID_Mensaje": self.message_id or "N/A",
            "Detalle_Error": self.error_message or "Ninguno",
        }
