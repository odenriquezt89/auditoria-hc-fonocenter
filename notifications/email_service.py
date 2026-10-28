"""
Servicio de envío de correos electrónicos profesionales vía SMTP y SendGrid API.
Renderiza plantillas HTML responsivas usando Jinja2.
"""

import os
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional
from jinja2 import Environment, FileSystemLoader

import requests

from .config import AppConfig
from .models import AuditNotificationData, NotificationResult, ChannelType, DeliveryStatus
from .validators import validate_email

logger = logging.getLogger("Notifications.EmailService")


class EmailNotificationService:
    def __init__(self, config: AppConfig):
        self.config = config
        self.jinja_env = Environment(
            loader=FileSystemLoader(self.config.TEMPLATES_DIR),
            autoescape=True
        )

    def render_email_html(self, data: AuditNotificationData) -> str:
        """Renderiza la plantilla HTML de correo con las variables de la auditoría."""
        template = self.jinja_env.get_template("email_audit_notification.html")
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

    def render_email_plaintext(self, data: AuditNotificationData) -> str:
        """Genera una versión alternativa en texto plano del correo."""
        return (
            f"FONOCENTER IPS - Notificación de Auditoría Médica\n"
            f"Comité de Calidad y Auditoría Médica (Res. 1995/1999 & 3100/2019)\n\n"
            f"Estimado(a) Dr(a). {data.doctor_name},\n\n"
            f"Resultados de la Auditoría a la Historia Clínica: {data.hc_number}\n"
            f"Especialidad / Servicio: {data.specialty}\n"
            f"Fecha de Evaluación: {data.audit_date}\n"
            f"Calificación Obtenida: {data.score:.1f}% ({data.risk_level})\n\n"
            f"Criterio con Oportunidad de Mejora: {data.weak_criterion or 'N/A'}\n"
            f"Detalle del Hallazgo: {data.finding_detail}\n\n"
            f"Atentamente,\n"
            f"Comité de Calidad Asistencial - FONOCENTER IPS\n"
            f"Contacto: calidad@fonocenter.com"
        )

    def send_notification(self, data: AuditNotificationData) -> NotificationResult:
        """Valida y envía el correo electrónico o ejecuta la simulación dry-run."""
        is_valid_email, email_or_err = validate_email(data.email)
        
        if not is_valid_email:
            logger.warning(f"[EMAIL] Destinatario inválido para {data.doctor_name}: {email_or_err}")
            return NotificationResult(
                hc_number=data.hc_number,
                doctor_name=data.doctor_name,
                channel=ChannelType.EMAIL,
                status=DeliveryStatus.SKIPPED_INVALID_DATA,
                recipient=str(data.email),
                error_message=email_or_err
            )

        html_content = self.render_email_html(data)
        plain_text = self.render_email_plaintext(data)
        subject = f"FONOCENTER IPS: Resultado Auditoría Médica [{data.hc_number}] - {data.doctor_name}"

        # Modo Simulación (DRY-RUN)
        if self.config.DRY_RUN or not (self.config.SMTP_USER or self.config.SENDGRID_API_KEY):
            logger.info(f"[EMAIL DRY-RUN] Simulación de envío exitosa a {email_or_err} para HC {data.hc_number}")
            return NotificationResult(
                hc_number=data.hc_number,
                doctor_name=data.doctor_name,
                channel=ChannelType.EMAIL,
                status=DeliveryStatus.DRY_RUN_SUCCESS,
                recipient=email_or_err,
                message_id=f"sim-email-{data.hc_number}",
                rendered_preview=plain_text[:200] + "..."
            )

        # Enviar vía SendGrid API si está configurado
        if self.config.SENDGRID_API_KEY:
            return self._send_via_sendgrid(email_or_err, subject, html_content, plain_text, data)

        # Enviar vía SMTP
        return self._send_via_smtp(email_or_err, subject, html_content, plain_text, data)

    def _send_via_sendgrid(self, to_email: str, subject: str, html: str, plain: str, data: AuditNotificationData) -> NotificationResult:
        try:
            url = "https://api.sendgrid.com/v3/mail/send"
            headers = {
                "Authorization": f"Bearer {self.config.SENDGRID_API_KEY}",
                "Content-Type": "application/json"
            }
            payload = {
                "personalizations": [{"to": [{"email": to_email, "name": data.doctor_name}]}],
                "from": {"email": self.config.EMAIL_FROM_ADDRESS, "name": self.config.EMAIL_FROM_NAME},
                "subject": subject,
                "content": [
                    {"type": "text/plain", "value": plain},
                    {"type": "text/html", "value": html}
                ]
            }
            resp = requests.post(url, json=payload, headers=headers, timeout=10)
            if resp.status_code in (200, 202):
                msg_id = resp.headers.get("X-Message-Id", f"sg-{data.hc_number}")
                logger.info(f"[SENDGRID] Correo enviado exitosamente a {to_email}")
                return NotificationResult(
                    hc_number=data.hc_number,
                    doctor_name=data.doctor_name,
                    channel=ChannelType.EMAIL,
                    status=DeliveryStatus.SENT,
                    recipient=to_email,
                    message_id=msg_id
                )
            else:
                err_msg = f"Error SendGrid ({resp.status_code}): {resp.text}"
                logger.error(err_msg)
                return NotificationResult(
                    hc_number=data.hc_number,
                    doctor_name=data.doctor_name,
                    channel=ChannelType.EMAIL,
                    status=DeliveryStatus.FAILED,
                    recipient=to_email,
                    error_message=err_msg
                )
        except Exception as e:
            logger.exception(f"Excepción enviando correo SendGrid a {to_email}: {e}")
            return NotificationResult(
                hc_number=data.hc_number,
                doctor_name=data.doctor_name,
                channel=ChannelType.EMAIL,
                status=DeliveryStatus.FAILED,
                recipient=to_email,
                error_message=str(e)
            )

    def _send_via_smtp(self, to_email: str, subject: str, html: str, plain: str, data: AuditNotificationData) -> NotificationResult:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{self.config.EMAIL_FROM_NAME} <{self.config.EMAIL_FROM_ADDRESS}>"
            msg["To"] = to_email

            msg.attach(MIMEText(plain, "plain", "utf-8"))
            msg.attach(MIMEText(html, "html", "utf-8"))

            with smtplib.SMTP(self.config.SMTP_HOST, self.config.SMTP_PORT, timeout=15) as server:
                if self.config.SMTP_USE_TLS:
                    server.starttls()
                if self.config.SMTP_USER and self.config.SMTP_PASSWORD:
                    server.login(self.config.SMTP_USER, self.config.SMTP_PASSWORD)
                server.send_message(msg)

            logger.info(f"[SMTP] Correo enviado exitosamente a {to_email}")
            return NotificationResult(
                hc_number=data.hc_number,
                doctor_name=data.doctor_name,
                channel=ChannelType.EMAIL,
                status=DeliveryStatus.SENT,
                recipient=to_email,
                message_id=f"smtp-{data.hc_number}"
            )
        except Exception as e:
            logger.exception(f"Excepción enviando correo SMTP a {to_email}: {e}")
            return NotificationResult(
                hc_number=data.hc_number,
                doctor_name=data.doctor_name,
                channel=ChannelType.EMAIL,
                status=DeliveryStatus.FAILED,
                recipient=to_email,
                error_message=str(e)
            )
