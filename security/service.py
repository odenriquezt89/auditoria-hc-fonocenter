"""
Servicio Principal de Gestión de Usuarios, Autenticación y Control de Accesos (RBAC).
Controla la lógica de negocio, reglas de seguridad y semilla inicial obligatoria.
"""

from datetime import datetime
import os
import sqlite3
import uuid
from typing import Optional, List, Dict, Any

from security.database import get_db_connection, init_db
from security.hasher import hash_password, verify_password
from security.models import (
    User,
    Permissions,
    UserWithPermissions,
    UserCreate,
    UserUpdate,
    LoginResponse
)


class SecurityException(Exception):
    """Excepción base para violaciones de reglas de seguridad y permisos."""
    pass


class UserService:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path
        # Inicializa esquema de tablas si no existen
        init_db(self.db_path)
        # Ejecuta la semilla inicial del Administrador Maestro
        self.seed_master_admin()

    def _resolve_acting_user(self, user_or_id: Any) -> Optional[UserWithPermissions]:
        """Resuelve un objeto UserWithPermissions a partir de instancia o UUID."""
        if user_or_id is None:
            return None
        if isinstance(user_or_id, UserWithPermissions):
            return user_or_id
        if isinstance(user_or_id, str):
            return self.get_user_by_id(user_or_id)
        return None

    def seed_master_admin(self) -> UserWithPermissions:
        """
        Garantiza la existencia del Administrador Maestro inicial:
        - Nombre: Dr. Daniel Enríquez
        - Username: daniel.enriquez (o configurable vía variable de entorno)
        - es_admin_principal: true
        - Permisos: Todos activados en true
        """
        master_name = os.getenv("MASTER_ADMIN_NAME", "Dr. Daniel Enríquez")
        master_username = os.getenv("MASTER_ADMIN_USERNAME", "daniel.enriquez").strip().lower()
        master_password = os.getenv("MASTER_ADMIN_PASSWORD", "AdminFonocenter2026*")
        master_email = os.getenv("MASTER_ADMIN_EMAIL", "odenriquezt@gmail.com").strip().lower()
        master_doc = os.getenv("MASTER_ADMIN_DOCUMENT", "1085270585")
        master_tarjeta = os.getenv("MASTER_ADMIN_TARJETA", "TP-1085270585-MD")

        with get_db_connection(self.db_path) as conn:
            # Verificar si ya existe por username o como admin principal
            cur = conn.execute(
                "SELECT id FROM users WHERE username = ? OR es_admin_principal = 1",
                (master_username,)
            )
            existing = cur.fetchone()

            if existing:
                # El admin principal ya existe; retornarlo
                user_id = existing["id"]
                return self._fetch_user_with_permissions(conn, user_id)

            # Crear el administrador maestro con todos los permisos
            user_id = str(uuid.uuid4())
            now_iso = datetime.now().isoformat()
            hashed_pw = hash_password(master_password)

            conn.execute(
                """
                INSERT INTO users (
                    id, nombre_completo, documento_identidad, tarjeta_profesional,
                    correo, username, password_hash, estado, es_admin_principal,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, 1, ?, ?)
                """,
                (
                    user_id,
                    master_name,
                    master_doc,
                    master_tarjeta,
                    master_email,
                    master_username,
                    hashed_pw,
                    now_iso,
                    now_iso,
                )
            )

            perm_id = str(uuid.uuid4())
            conn.execute(
                """
                INSERT INTO permissions (
                    id, user_id, can_delete_audit, can_review_audit,
                    can_send_whatsapp, can_create_users, can_view_analysis_only
                ) VALUES (?, ?, 1, 1, 1, 1, 0)
                """,
                (perm_id, user_id)
            )

            return self._fetch_user_with_permissions(conn, user_id)

    def create_user(
        self,
        data: UserCreate,
        acting_user: Optional[Any] = None,
        creator_user_id: Optional[str] = None
    ) -> UserWithPermissions:
        """
        Crea un nuevo usuario en el sistema con su respectiva matriz de permisos.
        Exclusivo para el Administrador Principal (es_admin_principal = True).
        """
        actor = self._resolve_acting_user(creator_user_id or acting_user)
        if actor and not actor.es_admin_principal:
            raise SecurityException("Acceso denegado: Únicamente el Administrador Principal puede registrar nuevos usuarios y asignar permisos.")

        clean_username = data.username.strip().lower()
        clean_email = data.correo.strip().lower()
        clean_doc = data.documento_identidad.strip()

        with get_db_connection(self.db_path) as conn:
            # Validar unicidad de username
            cur = conn.execute("SELECT id FROM users WHERE username = ?", (clean_username,))
            if cur.fetchone():
                raise SecurityException(f"El nombre de usuario '{clean_username}' ya está registrado.")

            # Validar unicidad de documento de identidad
            cur = conn.execute("SELECT id FROM users WHERE documento_identidad = ?", (clean_doc,))
            if cur.fetchone():
                raise SecurityException(f"El documento de identidad '{clean_doc}' ya se encuentra registrado.")

            # Validar unicidad de correo
            cur = conn.execute("SELECT id FROM users WHERE correo = ?", (clean_email,))
            if cur.fetchone():
                raise SecurityException(f"El correo electrónico '{clean_email}' ya se encuentra registrado.")

            user_id = str(uuid.uuid4())
            now_iso = datetime.now().isoformat()
            hashed_pw = hash_password(data.password)

            conn.execute(
                """
                INSERT INTO users (
                    id, nombre_completo, documento_identidad, tarjeta_profesional,
                    correo, username, password_hash, estado, es_admin_principal,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    data.nombre_completo.strip(),
                    clean_doc,
                    data.tarjeta_profesional.strip() if data.tarjeta_profesional else None,
                    clean_email,
                    clean_username,
                    hashed_pw,
                    1 if data.estado else 0,
                    1 if data.es_admin_principal else 0,
                    now_iso,
                    now_iso,
                )
            )

            perm_id = str(uuid.uuid4())
            conn.execute(
                """
                INSERT INTO permissions (
                    id, user_id, can_delete_audit, can_review_audit,
                    can_send_whatsapp, can_create_users, can_view_analysis_only
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    perm_id,
                    user_id,
                    1 if (data.es_admin_principal or data.can_delete_audit) else 0,
                    1 if (data.es_admin_principal or data.can_review_audit) else 0,
                    1 if (data.es_admin_principal or data.can_send_whatsapp) else 0,
                    1 if (data.es_admin_principal or data.can_create_users) else 0,
                    1 if data.can_view_analysis_only else 0,
                )
            )

            return self._fetch_user_with_permissions(conn, user_id)

    def authenticate(self, username: str, password: str) -> LoginResponse:
        """
        Autentica un usuario verificando credenciales y estado activo.
        """
        clean_username = username.strip().lower()

        with get_db_connection(self.db_path) as conn:
            cur = conn.execute(
                """
                SELECT u.*, p.id AS perm_id, p.can_delete_audit, p.can_review_audit,
                       p.can_send_whatsapp, p.can_create_users, p.can_view_analysis_only
                FROM users u
                LEFT JOIN permissions p ON p.user_id = u.id
                WHERE u.username = ?
                """,
                (clean_username,)
            )
            row = cur.fetchone()

            if not row:
                return LoginResponse(
                    success=False,
                    message="Usuario o contraseña incorrectos."
                )

            if not bool(row["estado"]):
                return LoginResponse(
                    success=False,
                    message="La cuenta de usuario se encuentra inactiva. Contacte al Administrador Principal."
                )

            if not verify_password(password, row["password_hash"]):
                return LoginResponse(
                    success=False,
                    message="Usuario o contraseña incorrectos."
                )

            user_obj = self._row_to_user_with_permissions(row)
            return LoginResponse(
                success=True,
                message=f"Autenticación exitosa. Bienvenido {user_obj.nombre_completo}.",
                user=user_obj
            )

    def get_user_by_id(self, user_id: str) -> Optional[UserWithPermissions]:
        with get_db_connection(self.db_path) as conn:
            return self._fetch_user_with_permissions(conn, user_id)

    def get_user_by_username(self, username: str) -> Optional[UserWithPermissions]:
        clean = username.strip().lower()
        with get_db_connection(self.db_path) as conn:
            cur = conn.execute("SELECT id FROM users WHERE username = ?", (clean,))
            row = cur.fetchone()
            if not row:
                return None
            return self._fetch_user_with_permissions(conn, row["id"])

    def has_permission(self, user_id: str, perm_name: str) -> bool:
        """Verifica si un usuario específico tiene un permiso habilitado."""
        user = self.get_user_by_id(user_id)
        if not user:
            return False
        return user.has_permission(perm_name)

    def list_users(self, include_inactive: bool = True) -> List[UserWithPermissions]:
        """Lista todos los usuarios ordenados por fecha de creación."""
        with get_db_connection(self.db_path) as conn:
            query = """
                SELECT u.*, p.id AS perm_id, p.can_delete_audit, p.can_review_audit,
                       p.can_send_whatsapp, p.can_create_users, p.can_view_analysis_only
                FROM users u
                LEFT JOIN permissions p ON p.user_id = u.id
            """
            if not include_inactive:
                query += " WHERE u.estado = 1"
            query += " ORDER BY u.es_admin_principal DESC, u.created_at ASC"

            cur = conn.execute(query)
            return [self._row_to_user_with_permissions(row) for row in cur.fetchall()]

    def update_user(
        self,
        user_id: str,
        data: UserUpdate,
        acting_user: Optional[Any] = None,
        operator_user_id: Optional[str] = None
    ) -> UserWithPermissions:
        """
        Actualiza los datos o permisos de un usuario existente.
        Exclusivo para el Administrador Principal (es_admin_principal = True).
        """
        actor = self._resolve_acting_user(operator_user_id or acting_user)
        if actor and not actor.es_admin_principal:
            raise SecurityException("Acceso denegado: Únicamente el Administrador Principal puede otorgar permisos o modificar usuarios.")

        with get_db_connection(self.db_path) as conn:
            cur = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            target = cur.fetchone()
            if not target:
                raise ValueError(f"Usuario con ID '{user_id}' no encontrado.")

            is_master = bool(target["es_admin_principal"])
            now_iso = datetime.now().isoformat()

            # Evitar desactivar al administrador principal
            if is_master and data.estado is False:
                raise SecurityException("No es posible desactivar al Administrador Principal del sistema.")

            if is_master and any(
                val is False for val in (
                    data.can_delete_audit,
                    data.can_review_audit,
                    data.can_send_whatsapp,
                    data.can_create_users
                )
            ):
                raise SecurityException("No es posible revocar permisos al Administrador Principal del sistema.")

            # Actualizar tabla users
            updates = []
            params = []

            if data.nombre_completo is not None:
                updates.append("nombre_completo = ?")
                params.append(data.nombre_completo.strip())

            if data.tarjeta_profesional is not None:
                updates.append("tarjeta_profesional = ?")
                params.append(data.tarjeta_profesional.strip() if data.tarjeta_profesional else None)

            if data.correo is not None:
                clean_email = data.correo.strip().lower()
                # Verificar unicidad
                cur_e = conn.execute("SELECT id FROM users WHERE correo = ? AND id != ?", (clean_email, user_id))
                if cur_e.fetchone():
                    raise SecurityException(f"El correo '{clean_email}' ya pertenece a otro usuario.")
                updates.append("correo = ?")
                params.append(clean_email)

            if data.password:
                hashed = hash_password(data.password)
                updates.append("password_hash = ?")
                params.append(hashed)

            if data.estado is not None and not is_master:
                updates.append("estado = ?")
                params.append(1 if data.estado else 0)

            if updates:
                updates.append("updated_at = ?")
                params.append(now_iso)
                params.append(user_id)
                conn.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = ?", tuple(params))

            # Actualizar tabla permissions
            if not is_master:
                perm_updates = []
                perm_params = []

                if data.can_delete_audit is not None:
                    perm_updates.append("can_delete_audit = ?")
                    perm_params.append(1 if data.can_delete_audit else 0)

                if data.can_review_audit is not None:
                    perm_updates.append("can_review_audit = ?")
                    perm_params.append(1 if data.can_review_audit else 0)

                if data.can_send_whatsapp is not None:
                    perm_updates.append("can_send_whatsapp = ?")
                    perm_params.append(1 if data.can_send_whatsapp else 0)

                if data.can_create_users is not None:
                    perm_updates.append("can_create_users = ?")
                    perm_params.append(1 if data.can_create_users else 0)

                if data.can_view_analysis_only is not None:
                    perm_updates.append("can_view_analysis_only = ?")
                    perm_params.append(1 if data.can_view_analysis_only else 0)

                if perm_updates:
                    perm_params.append(user_id)
                    conn.execute(f"UPDATE permissions SET {', '.join(perm_updates)} WHERE user_id = ?", tuple(perm_params))

            return self._fetch_user_with_permissions(conn, user_id)

    def delete_user(
        self,
        user_id: str,
        acting_user: Optional[Any] = None,
        operator_user_id: Optional[str] = None
    ) -> bool:
        """
        Elimina un usuario del sistema.
        Exclusivo para el Administrador Principal (es_admin_principal = True).
        Prohíbe la eliminación del Administrador Principal.
        """
        actor = self._resolve_acting_user(operator_user_id or acting_user)
        if actor and not actor.es_admin_principal:
            raise SecurityException("Acceso denegado: Únicamente el Administrador Principal puede eliminar usuarios del sistema.")

        with get_db_connection(self.db_path) as conn:
            cur = conn.execute("SELECT es_admin_principal FROM users WHERE id = ?", (user_id,))
            row = cur.fetchone()
            if not row:
                return False

            if bool(row["es_admin_principal"]):
                raise SecurityException("Operación Prohibida: El Administrador Principal no puede ser eliminado del sistema.")

            conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
            return True

    def _fetch_user_with_permissions(self, conn: sqlite3.Connection, user_id: str) -> Optional[UserWithPermissions]:
        cur = conn.execute(
            """
            SELECT u.*, p.id AS perm_id, p.can_delete_audit, p.can_review_audit,
                   p.can_send_whatsapp, p.can_create_users, p.can_view_analysis_only
            FROM users u
            LEFT JOIN permissions p ON p.user_id = u.id
            WHERE u.id = ?
            """,
            (user_id,)
        )
        row = cur.fetchone()
        if not row:
            return None
        return self._row_to_user_with_permissions(row)

    def _row_to_user_with_permissions(self, row: sqlite3.Row) -> UserWithPermissions:
        has_analysis_col = "can_view_analysis_only" in row.keys()
        perms = Permissions(
            id=row["perm_id"] or str(uuid.uuid4()),
            user_id=row["id"],
            can_delete_audit=bool(row["can_delete_audit"]),
            can_review_audit=bool(row["can_review_audit"]),
            can_send_whatsapp=bool(row["can_send_whatsapp"]),
            can_create_users=bool(row["can_create_users"]),
            can_view_analysis_only=bool(row["can_view_analysis_only"]) if has_analysis_col else False,
        )

        return UserWithPermissions(
            id=row["id"],
            nombre_completo=row["nombre_completo"],
            documento_identidad=row["documento_identidad"],
            tarjeta_profesional=row["tarjeta_profesional"],
            correo=row["correo"],
            username=row["username"],
            estado=bool(row["estado"]),
            es_admin_principal=bool(row["es_admin_principal"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            permissions=perms,
        )


_service_instance: Optional[UserService] = None


def get_user_service(db_path: Optional[str] = None) -> UserService:
    global _service_instance
    if _service_instance is None or db_path is not None:
        _service_instance = UserService(db_path)
    return _service_instance
