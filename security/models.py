"""
Modelos de Datos y Esquemas para Usuario, Autenticación y Matriz de Permisos (RBAC).
Utiliza Pydantic v2 para validación estricta de esquemas y formatos.
"""

from datetime import datetime
import re
import uuid
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict


EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


class Permissions(BaseModel):
    """
    Matriz de permisos operativos explícitos para el sistema de auditoría médica.
    """
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: Optional[str] = Field(default=None)
    can_delete_audit: bool = Field(
        default=False,
        description="Permiso para eliminar auditorías realizadas (operación crítica de alto riesgo)."
    )
    can_review_audit: bool = Field(
        default=True,
        description="Permiso para auditar, diligenciar y reevaluar historias clínicas."
    )
    can_send_whatsapp: bool = Field(
        default=False,
        description="Permiso para disparar notificaciones e informes de auditoría vía WhatsApp API."
    )
    can_create_users: bool = Field(
        default=False,
        description="Permiso para registrar, editar y administrar usuarios y permisos en el sistema."
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "can_delete_audit": self.can_delete_audit,
            "can_review_audit": self.can_review_audit,
            "can_send_whatsapp": self.can_send_whatsapp,
            "can_create_users": self.can_create_users,
        }


class User(BaseModel):
    """
    Entidad de Usuario del sistema de auditoría médica.
    """
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    nombre_completo: str = Field(..., min_length=3, max_length=150)
    documento_identidad: str = Field(..., min_length=4, max_length=30)
    tarjeta_profesional: Optional[str] = Field(default=None, max_length=50)
    correo: str = Field(..., max_length=120)
    username: str = Field(..., min_length=3, max_length=50)
    password_hash: str
    estado: bool = Field(default=True, description="True para activo, False para inactivo")
    es_admin_principal: bool = Field(default=False, description="True si es el administrador maestro")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())

    @field_validator("correo")
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        clean = v.strip().lower()
        if not EMAIL_REGEX.match(clean):
            raise ValueError(f"Formato de correo electrónico inválido: {v}")
        return clean

    @field_validator("username")
    @classmethod
    def validate_username_format(cls, v: str) -> str:
        clean = v.strip().lower()
        if not re.match(r"^[a-z0-9._-]+$", clean):
            raise ValueError("El username solo puede contener letras, números, puntos, guiones o subguiones")
        return clean


class UserWithPermissions(BaseModel):
    """
    Representación consolidada de un usuario junto a su matriz de permisos.
    """
    model_config = ConfigDict(from_attributes=True)

    id: str
    nombre_completo: str
    documento_identidad: str
    tarjeta_profesional: Optional[str] = None
    correo: str
    username: str
    estado: bool
    es_admin_principal: bool
    created_at: str
    updated_at: str
    permissions: Permissions

    @property
    def permisos(self) -> Permissions:
        """Alias en español para permissions."""
        return self.permissions

    def has_permission(self, perm_name: str) -> bool:
        """Verifica si el usuario cuenta con un permiso específico o es admin principal."""
        if not self.estado:
            return False
        if self.es_admin_principal:
            return True
        return getattr(self.permissions, perm_name, False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "nombre_completo": self.nombre_completo,
            "documento_identidad": self.documento_identidad,
            "tarjeta_profesional": self.tarjeta_profesional,
            "correo": self.correo,
            "username": self.username,
            "estado": self.estado,
            "es_admin_principal": self.es_admin_principal,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "permissions": self.permissions.to_dict(),
        }


class UserCreate(BaseModel):
    """
    DTO para la creación de un nuevo usuario en el sistema.
    """
    nombre_completo: str = Field(..., min_length=3, max_length=150)
    documento_identidad: str = Field(..., min_length=4, max_length=30)
    tarjeta_profesional: Optional[str] = Field(default=None, max_length=50)
    correo: str = Field(..., max_length=120)
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, description="Contraseña en texto plano a ser hasheada")
    estado: bool = Field(default=True)
    es_admin_principal: bool = Field(default=False)

    # Permisos iniciales
    can_delete_audit: bool = Field(default=False)
    can_review_audit: bool = Field(default=True)
    can_send_whatsapp: bool = Field(default=False)
    can_create_users: bool = Field(default=False)

    @field_validator("correo")
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        clean = v.strip().lower()
        if not EMAIL_REGEX.match(clean):
            raise ValueError(f"Formato de correo electrónico inválido: {v}")
        return clean

    @field_validator("username")
    @classmethod
    def validate_username_format(cls, v: str) -> str:
        clean = v.strip().lower()
        if not re.match(r"^[a-z0-9._-]+$", clean):
            raise ValueError("El username solo puede contener letras, números, puntos, guiones o subguiones")
        return clean


class UserUpdate(BaseModel):
    """
    DTO para la actualización de un usuario existente.
    """
    nombre_completo: Optional[str] = None
    tarjeta_profesional: Optional[str] = None
    correo: Optional[str] = None
    password: Optional[str] = None
    estado: Optional[bool] = None

    # Actualización de permisos
    can_delete_audit: Optional[bool] = None
    can_review_audit: Optional[bool] = None
    can_send_whatsapp: Optional[bool] = None
    can_create_users: Optional[bool] = None


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    success: bool
    message: str
    user: Optional[UserWithPermissions] = None
