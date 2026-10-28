"""
Servicio de envío de notificaciones WhatsApp vía Twilio API y Meta WhatsApp Cloud API.
Renderiza plantillas con formato clínico optimizado.
"""

import os
import logging
from typing import Optional
from jinja2 import Environment, FileSystemLoader

import requests

from .config import AppConfig
from .models import AuditNotificationData, NotificationResult, ChannelType, DeliveryStatus
from .validators import validate_and_format_phone

logger = logging.getLogger("Notifications.WhatsAppService")


class WhatsAppNotificationService:
    def __init__(self, config: AppConfig):
        self.config = config
        self.jinja_env = Environment(
            loader=FileSystemLoader(self.config.TEMPLATES_DIR),
            autoescape=False
        )

    def render_message(self, data: AuditNotificationData) -> str:
        """Renderiza el mensaje de texto estructurado para WhatsApp."""
        template = self.jinja_env.get_template("whatsapp_message_template.txt")
        return template.render(
            doctor_name=data.doctor_name,
            hc_number=data.hc_number,
            specialty=data.specialty,
            score=data.score,
            risk_level=data.risk_level,
            weak_criterion=data.weak_criterion,
            finding_detail=data.finding_detail,
            audit_date=data.audit_date
        )

    def send_notification(self, data: AuditNotificationData) -> NotificationResult:
        """Valida el número y envía el mensaje de WhatsApp o ejecuta simulación."""
        is_valid_phone, formatted_phone, phone_err = validate_and_format_phone(data.phone)
        
        if not is_valid_phone:
            logger.warning(f"[WHATSAPP] Teléfono inválido para {data.doctor_name}: {phone_err}")
            return NotificationResult(
                hc_number=data.hc_number,
                doctor_name=data.doctor_name,
                channel=ChannelType.WHATSAPP,
                status=DeliveryStatus.SKIPPED_INVALID_DATA,
                recipient=str(data.phone),
                error_message=phone_err
            )

        message_body = self.render_message(data)

        # Modo Simulación (DRY-RUN)
        if self.config.DRY_RUN or not (self.config.TWILIO_ACCOUNT_SID or self.config.META_WA_ACCESS_TOKEN):
            logger.info(f"[WHATSAPP DRY-RUN] Simulación de envío exitosa a {formatted_phone} para HC {data.hc_number}")
            return NotificationResult(
                hc_number=data.hc_number,
                doctor_name=data.doctor_name,
                channel=ChannelType.WHATSAPP,
                status=DeliveryStatus.DRY_RUN_SUCCESS,
                recipient=formatted_phone,
                message_id=f"sim-wa-{data.hc_number}",
                rendered_preview=message_body[:200] + "..."
            )

        # Enviar vía Twilio si está configurado
        if self.config.TWILIO_ACCOUNT_SID and self.config.TWILIO_AUTH_TOKEN:
            return self._send_via_twilio(formatted_phone, message_body, data)

        # Enviar vía Meta WhatsApp Cloud API si está configurado
        if self.config.META_WA_ACCESS_TOKEN and self.config.META_WA_PHONE_NUMBER_ID:
            return self._send_via_meta_cloud(formatted_phone, message_body, data)

        return NotificationResult(
            hc_number=data.hc_number,
            doctor_name=data.doctor_name,
            channel=ChannelType.WHATSAPP,
            status=DeliveryStatus.FAILED,
            recipient=formatted_phone,
            error_message="No se encontraron credenciales válidas de Twilio o Meta Cloud API."
        )

    def _send_via_twilio(self, to_phone: str, body: str, data: AuditNotificationData) -> NotificationResult:
        try:
            url = f"https://api.twilio.com/2010-04-01/Accounts/{self.config.TWILIO_ACCOUNT_SID}/Messages.json"
            from_wa = self.config.TWILIO_WHATSAPP_FROM
            if not from_wa.startswith("whatsapp:"):
                from_wa = f"whatsapp:{from_wa}"
            
            payload = {
                "From": from_wa,
                "To": f"whatsapp:{to_phone}",
                "Body": body
            }
            resp = requests.post(
                url, 
                data=payload, 
                auth=(self.config.TWILIO_ACCOUNT_SID, self.config.TWILIO_AUTH_TOKEN),
                timeout=12
            )
            
            if resp.status_code in (200, 201):
                res_data = resp.json()
                sid = res_data.get("sid", f"tw-{data.hc_number}")
                logger.info(f"[TWILIO] WhatsApp enviado a {to_phone} (SID: {sid})")
                return NotificationResult(
                    hc_number=data.hc_number,
                    doctor_name=data.doctor_name,
                    channel=ChannelType.WHATSAPP,
                    status=DeliveryStatus.SENT,
                    recipient=to_phone,
                    message_id=sid
                )
            else:
                err_msg = f"Error Twilio ({resp.status_code}): {resp.text}"
                logger.error(err_msg)
                return NotificationResult(
                    hc_number=data.hc_number,
                    doctor_name=data.doctor_name,
                    channel=ChannelType.WHATSAPP,
                    status=DeliveryStatus.FAILED,
                    recipient=to_phone,
                    error_message=err_msg
                )
        except Exception as e:
            logger.exception(f"Excepción enviando WhatsApp Twilio a {to_phone}: {e}")
            return NotificationResult(
                hc_number=data.hc_number,
                doctor_name=data.doctor_name,
                channel=ChannelType.WHATSAPP,
                status=DeliveryStatus.FAILED,
                recipient=to_phone,
                error_message=str(e)
            )

    def _send_via_meta_cloud(self, to_phone: str, body: str, data: AuditNotificationData) -> NotificationResult:
        try:
            # Eliminar el '+' para la API de Meta
            clean_recipient = to_phone.replace("+", "")
            url = f"https://graph.facebook.com/v18.0/{self.config.META_WA_PHONE_NUMBER_ID}/messages"
            headers = {
                "Authorization": f"Bearer {self.config.META_WA_ACCESS_TOKEN}",
                "Content-Type": "application/json"
            }
            payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": clean_recipient,
                "type": "text",
                "text": {"preview_url": False, "body": body}
            }
            resp = requests.post(url, json=payload, headers=headers, timeout=12)
            if resp.status_code == 200:
                res_data = resp.json()
                msg_id = res_data.get("messages", [{}])[0].get("id", f"meta-{data.hc_number}")
                logger.info(f"[META CLOUD] WhatsApp enviado a {to_phone} (ID: {msg_id})")
                return NotificationResult(
                    hc_number=data.hc_number,
                    doctor_name=data.doctor_name,
                    channel=ChannelType.WHATSAPP,
                    status=DeliveryStatus.SENT,
                    recipient=to_phone,
                    message_id=msg_id
                )
            else:
                err_msg = f"Error Meta Cloud ({resp.status_code}): {resp.text}"
                logger.error(err_msg)
                return NotificationResult(
                    hc_number=data.hc_number,
                    doctor_name=data.doctor_name,
                    channel=ChannelType.WHATSAPP,
                    status=DeliveryStatus.FAILED,
                    recipient=to_phone,
                    error_message=err_msg
                )
        except Exception as e:
            logger.exception(f"Excepción enviando WhatsApp Meta Cloud a {to_phone}: {e}")
            return NotificationResult(
                hc_number=data.hc_number,
                doctor_name=data.doctor_name,
                channel=ChannelType.WHATSAPP,
                status=DeliveryStatus.FAILED,
                recipient=to_phone,
                error_message=str(e)
            )
