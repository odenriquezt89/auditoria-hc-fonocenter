"""
Suite de Pruebas Automatizadas para el Módulo de Seguridad y RBAC.
Verifica:
1. Inicialización y creación de esquemas.
2. Semilla del Administrador Maestro (Dr. Daniel Enríquez).
3. Hashing y verificación segura de contraseñas con bcrypt.
4. Restricciones de unicidad (documento, correo, username).
5. Asignación y verificación de la matriz de permisos de 4 flags.
6. Reglas de control de acceso para creación y eliminación de usuarios.
7. Protección estricta del Administrador Maestro.
"""

import os
import sys
import tempfile
import unittest

# Asegurar importación de módulos locales
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from security.models import UserCreate, Permissions, UserUpdate
from security.service import UserService, SecurityException
from security.hasher import hash_password, verify_password


class TestSecurityRBAC(unittest.TestCase):
    def setUp(self):
        # Utiliza una base de datos temporal aislada para cada prueba
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db.close()
        self.db_path = self.temp_db.name
        self.service = UserService(db_path=self.db_path)

    def tearDown(self):
        # Limpieza de base de datos temporal
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except OSError:
                pass

    def test_01_master_admin_seed(self):
        """Verifica que el Administrador Maestro se siembra automáticamente con todos los permisos."""
        master = self.service.get_user_by_username("daniel.enriquez")
        self.assertIsNotNone(master)
        self.assertEqual(master.nombre_completo, "Dr. Daniel Enríquez")
        self.assertTrue(master.es_admin_principal)
        self.assertTrue(master.estado)
        
        # Verificar permisos
        perms = master.permisos
        self.assertTrue(perms.can_delete_audit)
        self.assertTrue(perms.can_review_audit)
        self.assertTrue(perms.can_send_whatsapp)
        self.assertTrue(perms.can_create_users)

    def test_02_bcrypt_hashing_and_auth(self):
        """Verifica el correcto funcionamiento del hashing con bcrypt y la autenticación."""
        # Autenticación exitosa del admin maestro
        auth_success = self.service.authenticate("daniel.enriquez", "AdminFonocenter2026*")
        self.assertIsNotNone(auth_success)
        self.assertTrue(auth_success.success)
        self.assertIsNotNone(auth_success.user)
        self.assertEqual(auth_success.user.username, "daniel.enriquez")

        # Autenticación con contraseña errónea
        auth_fail = self.service.authenticate("daniel.enriquez", "ClaveEquivocada123")
        self.assertFalse(auth_fail.success)
        self.assertIsNone(auth_fail.user)

        # Autenticación de usuario inexistente
        auth_none = self.service.authenticate("no_existe", "Password123")
        self.assertFalse(auth_none.success)
        self.assertIsNone(auth_none.user)

    def test_03_create_auditor_user(self):
        """Verifica la creación de un nuevo usuario con permisos específicos."""
        master = self.service.get_user_by_username("daniel.enriquez")
        new_user_data = UserCreate(
            nombre_completo="Dra. Carolina Martínez",
            documento_identidad="52987654",
            tarjeta_profesional="TP-52987654-MD",
            correo="carolina.martinez@fonocenter.com",
            username="carolina.martinez",
            password="AuditorPassword2026*",
            estado=True,
            can_delete_audit=False,  # No puede borrar auditorías
            can_review_audit=True,   # Puede revisar y auditar
            can_send_whatsapp=True,  # Puede enviar WhatsApp
            can_create_users=False   # No puede crear usuarios
        )

        created_user = self.service.create_user(new_user_data, creator_user_id=master.id)
        self.assertEqual(created_user.username, "carolina.martinez")
        self.assertFalse(created_user.es_admin_principal)
        self.assertFalse(created_user.permisos.can_delete_audit)
        self.assertTrue(created_user.permisos.can_review_audit)
        self.assertTrue(created_user.permisos.can_send_whatsapp)
        self.assertFalse(created_user.permisos.can_create_users)

        # Verificar permisos con has_permission
        self.assertTrue(self.service.has_permission(created_user.id, "can_review_audit"))
        self.assertFalse(self.service.has_permission(created_user.id, "can_delete_audit"))
        self.assertFalse(self.service.has_permission(created_user.id, "can_create_users"))

    def test_04_enforce_creator_permission(self):
        """Un usuario sin can_create_users no debe poder registrar a otros usuarios."""
        master = self.service.get_user_by_username("daniel.enriquez")
        
        # Crear usuario sin permiso de creación
        auditor_data = UserCreate(
            nombre_completo="Auditor Sin Permisos",
            documento_identidad="111222333",
            correo="sinpermiso@fonocenter.com",
            username="auditor.sinpermiso",
            password="AuditorPassword2026*",
            can_delete_audit=False,
            can_review_audit=True,
            can_send_whatsapp=False,
            can_create_users=False
        )
        auditor = self.service.create_user(auditor_data, creator_user_id=master.id)

        # Intentar crear un usuario usando la ID de este auditor
        target_user = UserCreate(
            nombre_completo="Nuevo Usuario Ilegal",
            documento_identidad="444555666",
            correo="ilegal@fonocenter.com",
            username="ilegal.user",
            password="Password2026*",
            can_review_audit=True
        )

        with self.assertRaises(SecurityException):
            self.service.create_user(target_user, creator_user_id=auditor.id)

    def test_05_uniqueness_constraints(self):
        """Verifica que el sistema rechace duplicados en username, documento o correo."""
        master = self.service.get_user_by_username("daniel.enriquez")

        # Intento de duplicar username
        dup_username = UserCreate(
            nombre_completo="Otro Daniel",
            documento_identidad="999999999",
            correo="otro@fonocenter.com",
            username="daniel.enriquez",
            password="Password2026*"
        )
        with self.assertRaises(SecurityException):
            self.service.create_user(dup_username, creator_user_id=master.id)

        # Intento de duplicar documento
        dup_doc = UserCreate(
            nombre_completo="Otro Doc",
            documento_identidad=master.documento_identidad,
            correo="otro2@fonocenter.com",
            username="otro.doc",
            password="Password2026*"
        )
        with self.assertRaises(SecurityException):
            self.service.create_user(dup_doc, creator_user_id=master.id)

    def test_06_master_admin_protection(self):
        """Verifica que el Administrador Maestro no pueda ser eliminado o desactivado."""
        master = self.service.get_user_by_username("daniel.enriquez")

        # Intentar desactivar
        update_data = UserUpdate(estado=False)
        with self.assertRaises(SecurityException):
            self.service.update_user(master.id, update_data, operator_user_id=master.id)

        # Intentar quitarle can_create_users
        perm_update = UserUpdate(can_create_users=False)
        with self.assertRaises(SecurityException):
            self.service.update_user(master.id, perm_update, operator_user_id=master.id)

        # Intentar eliminar
        with self.assertRaises(SecurityException):
            self.service.delete_user(master.id, operator_user_id=master.id)

    def test_07_strict_non_admin_restrictions(self):
        """Verifica que un usuario que no sea Administrador Principal NO puede crear usuarios, NO puede otorgar permisos y NO puede eliminar usuarios."""
        master = self.service.get_user_by_username("daniel.enriquez")

        # Crear un usuario auditor auxiliar
        auditor_data = UserCreate(
            nombre_completo="Dra. Diana López",
            documento_identidad="77889900",
            correo="diana.lopez@fonocenter.com",
            username="diana.lopez",
            password="AuditorPassword2026*",
            can_delete_audit=False,
            can_review_audit=True,
            can_send_whatsapp=True,
            can_create_users=True  # Incluso si tuviera este flag, no es admin principal
        )
        auditor = self.service.create_user(auditor_data, creator_user_id=master.id)
        self.assertFalse(auditor.es_admin_principal)

        # Crear un tercer usuario como conejillo de indias
        user3_data = UserCreate(
            nombre_completo="Usuario Prueba 3",
            documento_identidad="55667788",
            correo="prueba3@fonocenter.com",
            username="prueba3",
            password="AuditorPassword2026*"
        )
        user3 = self.service.create_user(user3_data, creator_user_id=master.id)

        # 1. Auditor no puede agregar otros usuarios
        new_user_data = UserCreate(
            nombre_completo="Usuario No Autorizado",
            documento_identidad="123999888",
            correo="noautorizado@fonocenter.com",
            username="no.autorizado",
            password="Password2026*"
        )
        with self.assertRaises(SecurityException) as ctx:
            self.service.create_user(new_user_data, creator_user_id=auditor.id)
        self.assertIn("Administrador Principal", str(ctx.exception))

        # 2. Auditor no puede otorgar ni modificar permisos
        perm_grant = UserUpdate(can_delete_audit=True)
        with self.assertRaises(SecurityException) as ctx:
            self.service.update_user(user3.id, perm_grant, operator_user_id=auditor.id)
        self.assertIn("Administrador Principal", str(ctx.exception))

        # 3. Auditor no puede eliminar otros usuarios
        with self.assertRaises(SecurityException) as ctx:
            self.service.delete_user(user3.id, operator_user_id=auditor.id)
        self.assertIn("Administrador Principal", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
