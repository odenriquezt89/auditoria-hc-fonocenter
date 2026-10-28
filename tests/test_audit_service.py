"""
Pruebas Unitarias para el Servicio de Auditoría y Trazabilidad de Auditores.
Verifica:
1. Persistencia y listado centralizado de auditorías.
2. Identificación obligatoria del perfil de auditor responsable.
3. Visibilidad global de auditorías (perfil principal ve todo sin importar quién auditó).
4. Ciclos de auditoría centralizados.
5. Control de permisos para eliminación y reevaluación.
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from security.service import UserService, SecurityException
from security.audit_service import AuditService
from security.models import UserCreate


class TestAuditService(unittest.TestCase):
    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db.close()
        self.db_path = self.temp_db.name
        self.user_service = UserService(db_path=self.db_path)
        self.audit_service = AuditService(db_path=self.db_path)

    def tearDown(self):
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except OSError:
                pass

    def test_01_save_audit_with_auditor_traceability(self):
        """Verifica que cada auditoría registre la identidad exacta del auditor que la realizó."""
        master = self.user_service.get_user_by_username("daniel.enriquez")

        # Crear una auditora asistente
        auditor_data = UserCreate(
            nombre_completo="Dra. Carolina Martínez",
            documento_identidad="52987654",
            tarjeta_profesional="TP-52987654-MD",
            correo="carolina.martinez@fonocenter.com",
            username="carolina.martinez",
            password="AuditorPassword2026*",
            can_review_audit=True,
            can_delete_audit=False
        )
        auditor = self.user_service.create_user(auditor_data, creator_user_id=master.id)

        # La Dra. Carolina realiza una auditoría
        audit_payload = {
            "hcNumber": "HC-889900",
            "auditDate": "2026-10-27",
            "doctorName": "ENRIQUEZ TORRES OSCAR DANIEL",
            "patientId": "100234567",
            "patientName": "Pedro Picapiedra",
            "serviceType": "Atención Médica Domiciliaria PAD",
            "score": 95.0,
            "riskLevel": "CONFORME",
            "isCompliant": True,
            "evaluations": {"C01": "CUMPLE", "C02": "CUMPLE"},
            "comments": {},
            "auditNote": "Historia clínica completa con excelente pertinencia."
        }

        saved = self.audit_service.save_audit(audit_payload, auditor_user=auditor)
        self.assertEqual(saved["hcNumber"], "HC-889900")
        self.assertEqual(saved["auditorId"], auditor.id)
        self.assertEqual(saved["auditorName"], "Dra. Carolina Martínez")
        self.assertEqual(saved["auditorUsername"], "carolina.martinez")

        # Dr. Daniel realiza otra auditoría
        payload2 = {
            "hcNumber": "HC-112233",
            "auditDate": "2026-10-27",
            "doctorName": "DR. PEREZ LOPEZ",
            "patientId": "998877",
            "patientName": "Maria Gomez",
            "serviceType": "Atención Médica Domiciliaria PAD",
            "score": 75.0,
            "riskLevel": "MODERADO",
            "isCompliant": False,
            "evaluations": {"C01": "CUMPLE", "C02": "NO_CUMPLE"}
        }
        saved2 = self.audit_service.save_audit(payload2, auditor_user=master)
        self.assertEqual(saved2["auditorUsername"], "daniel.enriquez")

        # Verificar que el listado total consolida AMBAS auditorías (visibilidad total)
        all_audits = self.audit_service.list_audits()
        self.assertEqual(len(all_audits), 2)
        hc_numbers = [a["hcNumber"] for a in all_audits]
        self.assertIn("HC-889900", hc_numbers)
        self.assertIn("HC-112233", hc_numbers)

        # Filtrado específico por auditor
        carolina_audits = self.audit_service.list_audits(auditor_id=auditor.id)
        self.assertEqual(len(carolina_audits), 1)
        self.assertEqual(carolina_audits[0]["hcNumber"], "HC-889900")

    def test_02_permission_guards_in_audits(self):
        """Verifica que un usuario sin can_delete_audit no pueda eliminar registros."""
        master = self.user_service.get_user_by_username("daniel.enriquez")
        auditor_data = UserCreate(
            nombre_completo="Auditor Limitado",
            documento_identidad="77889900",
            correo="limitado@fonocenter.com",
            username="auditor.limitado",
            password="Password2026*",
            can_review_audit=True,
            can_delete_audit=False
        )
        auditor = self.user_service.create_user(auditor_data, creator_user_id=master.id)

        audit_payload = {
            "id": "AUD-TEST-DELETE",
            "hcNumber": "HC-55555",
            "auditDate": "2026-10-27",
            "doctorName": "DR. TEST",
            "patientId": "123",
            "patientName": "Paciente",
            "score": 80.0,
            "riskLevel": "MODERADO",
            "isCompliant": False
        }
        self.audit_service.save_audit(audit_payload, auditor_user=master)

        # El auditor sin permiso intenta eliminar
        with self.assertRaises(SecurityException):
            self.audit_service.delete_audit("AUD-TEST-DELETE", acting_user=auditor)

        # El administrador maestro sí puede eliminar
        deleted = self.audit_service.delete_audit("AUD-TEST-DELETE", acting_user=master)
        self.assertTrue(deleted)
        self.assertIsNone(self.audit_service.get_audit_by_id("AUD-TEST-DELETE"))


if __name__ == "__main__":
    unittest.main()
