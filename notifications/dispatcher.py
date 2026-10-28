"""
Despachador multicanal que orquesta el envío de notificaciones y consolida los resultados.
"""

import os
import logging
from typing import List, Optional
import pandas as pd

from .config import AppConfig
from .models import AuditNotificationData, NotificationResult, ChannelType
from .email_service import EmailNotificationService
from .whatsapp_service import WhatsAppNotificationService
from .validators import validate_audit_record

logger = logging.getLogger("Notifications.Dispatcher")


class NotificationDispatcher:
    def __init__(self, config: Optional[AppConfig] = None):
        self.config = config or AppConfig()
        self.email_service = EmailNotificationService(self.config)
        self.whatsapp_service = WhatsAppNotificationService(self.config)

    def load_records_from_file(self, filepath: str) -> List[AuditNotificationData]:
        """Carga y mapea registros de auditoría desde CSV o Excel."""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"No se encontró el archivo de datos: {filepath}")

        if filepath.endswith(".csv"):
            df = pd.read_csv(filepath, encoding="utf-8")
        elif filepath.endswith((".xlsx", ".xls")):
            df = pd.read_excel(filepath)
        else:
            raise ValueError(f"Formato no soportado: {filepath}. Use .csv o .xlsx")

        records = []
        for _, row in df.iterrows():
            # Manejo flexible de nombres de columnas
            hc_number = str(row.get("ID_HISTORIA_CLINICA") or row.get("Numero_HC") or row.get("id") or "HC-SIN-ID")
            doctor_name = str(row.get("NOMBRE_COMPLETO") or row.get("Medico_Evaluado") or row.get("doctorName") or "Médico No Identificado").strip()
            specialty = str(row.get("ESPECIALIDAD") or row.get("Servicio") or row.get("serviceType") or "Medicina General")
            phone = str(row.get("TELEFONO") or row.get("phone") or "")
            email = str(row.get("CORREO_ELECTRONICO") or row.get("email") or "")
            
            # Puntuación
            score_raw = row.get("CALIFICACION_GENERAL") or row.get("Calificacion_Ponderada") or row.get("score") or 0.0
            try:
                if isinstance(score_raw, str):
                    score_clean = float(score_raw.replace("%", "").strip())
                else:
                    score_clean = float(score_raw)
            except Exception:
                score_clean = 0.0

            risk_level = str(row.get("NIVEL_RIESGO") or row.get("riskLevel") or ("CONFORME" if score_clean >= 90 else "MODERADO" if score_clean >= 70 else "CRITICO"))
            finding_detail = str(row.get("HALLAZGO_PRIORITARIO") or row.get("Detalle_Hallazgo") or "Cumplimiento general evaluado satisfactoriamente.")
            weak_criterion = str(row.get("CRITERIO_DEBIL") or row.get("Criterio_Oportunidad") or "")

            records.append(AuditNotificationData(
                hc_number=hc_number,
                doctor_name=doctor_name,
                specialty=specialty,
                phone=phone,
                email=email,
                score=score_clean,
                risk_level=risk_level,
                finding_detail=finding_detail,
                weak_criterion=weak_criterion if weak_criterion and weak_criterion != "nan" else None
            ))

        logger.info(f"Cargados {len(records)} registros de auditoría desde {filepath}")
        return records

    def dispatch_single(self, data: AuditNotificationData, channel: ChannelType = ChannelType.BOTH) -> List[NotificationResult]:
        """Envía las notificaciones para un registro de auditoría individual."""
        results = []
        is_valid, errs = validate_audit_record(data)
        if not is_valid:
            logger.error(f"Registro inválido para {data.doctor_name}: {', '.join(errs)}")

        # Enviar Correo
        if channel in (ChannelType.EMAIL, ChannelType.BOTH):
            email_res = self.email_service.send_notification(data)
            results.append(email_res)

        # Enviar WhatsApp
        if channel in (ChannelType.WHATSAPP, ChannelType.BOTH):
            wa_res = self.whatsapp_service.send_notification(data)
            results.append(wa_res)

        return results

    def dispatch_batch(self, records: List[AuditNotificationData], channel: ChannelType = ChannelType.BOTH) -> List[NotificationResult]:
        """Procesa un lote completo de auditorías generando la traza de resultados."""
        all_results = []
        for idx, rec in enumerate(records, start=1):
            logger.info(f"[{idx}/{len(records)}] Procesando auditoría {rec.hc_number} - {rec.doctor_name}...")
            res_list = self.dispatch_single(rec, channel)
            all_results.extend(res_list)
        return all_results
