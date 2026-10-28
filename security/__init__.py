"""
Módulo de Seguridad, Autenticación y Control de Acceso Basado en Permisos (RBAC).
Sistema de Auditoría Médica de Historias Clínicas - FONOCENTER IPS.
"""

from security.models import (
    Permissions,
    User,
    UserWithPermissions,
    UserCreate,
    UserUpdate,
    LoginRequest,
    LoginResponse
)
from security.hasher import hash_password, verify_password
from security.database import init_db, get_db_connection, get_default_db_path
from security.service import UserService, SecurityException, get_user_service

__all__ = [
    "Permissions",
    "User",
    "UserWithPermissions",
    "UserCreate",
    "UserUpdate",
    "LoginRequest",
    "LoginResponse",
    "hash_password",
    "verify_password",
    "init_db",
    "get_db_connection",
    "get_default_db_path",
    "UserService",
    "SecurityException",
    "get_user_service"
]
