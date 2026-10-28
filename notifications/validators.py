"""
Validadores de formato para correos electrónicos, números telefónicos y datos clínicos.
"""

import re
from typing import Tuple, List
from .models import AuditNotificationData

# Regex estándar para validación sintáctica de correo
EMAIL_REGEX = re.compile(
    r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
)

# Regex para teléfonos celulares en Colombia (10 dígitos empezando en 3)
COLOMBIA_PHONE_REGEX = re.compile(r"^(?:(?:\+57|57)?\s*)?(3\d{9})$")


def validate_email(email: str) -> Tuple[bool, str]:
    """
    Valida sintácticamente una dirección de correo electrónico.
    Retorna (es_valido, mensaje_o_email_normalizado).
    """
    if not email or not isinstance(email, str):
        return False, "Dirección de correo vacía o no especificada."
    
    clean_email = email.strip()
    if not EMAIL_REGEX.match(clean_email):
        return False, f"Formato de correo inválido o incompleto: '{clean_email}'."
    
    return True, clean_email.lower()


def validate_and_format_phone(phone: str, default_country_code: str = "+57") -> Tuple[bool, str, str]:
    """
    Valida y formatea un número telefónico a estándar internacional E.164 (+57XXXXXXXXXX).
    Retorna (es_valido, numero_formateado_e164, mensaje_error).
    """
    if not phone or not isinstance(phone, str):
        return False, "", "Número de teléfono vacío o no especificado."
    
    # Remover espacios, guiones y paréntesis
    clean_digits = re.sub(r"[^\d+]", "", str(phone).strip())
    
    # Manejo de números colombianos
    match = COLOMBIA_PHONE_REGEX.match(clean_digits)
    if match:
        national_number = match.group(1)
        e164_number = f"+57{national_number}"
        return True, e164_number, ""
    
    # Si ya tiene prefijo internacional genérico válido (entre 10 y 15 dígitos)
    if clean_digits.startswith("+") and len(clean_digits) >= 11:
        return True, clean_digits, ""
    
    # Si son 10 dígitos sin el '+'
    if len(clean_digits) == 10:
        return True, f"{default_country_code}{clean_digits}", ""
        
    return False, "", f"Número de teléfono '{phone}' no cumple el formato celular colombiano (10 dígitos)."


def validate_audit_record(data: AuditNotificationData) -> Tuple[bool, List[str]]:
    """
    Valida la integridad de los datos de auditoría médica.
    """
    errors = []
    
    if not data.hc_number or not data.hc_number.strip():
        errors.append("ID de Historia Clínica no especificado.")
        
    if not data.doctor_name or not data.doctor_name.strip():
        errors.append("Nombre del profesional no especificado.")
        
    if data.score < 0.0 or data.score > 100.0:
        errors.append(f"Calificación de auditoría ({data.score}) fuera del rango permitido [0.0 - 100.0].")
        
    return len(errors) == 0, errors
