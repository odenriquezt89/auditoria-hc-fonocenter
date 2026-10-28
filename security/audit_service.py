"""
Servicio de Persistencia Centralizada para Auditorías Clínicas y Ciclos de Auditoría.
Permite consolidar en SQLite todas las auditorías realizadas por cualquier usuario/auditor,
garantizando trazabilidad absoluta de quién realizó o reevaluó cada historia clínica.
"""

from datetime import datetime
import json
import sqlite3
import uuid
from typing import List, Dict, Any, Optional

from security.database import get_db_connection, init_db
from security.service import SecurityException
from security.models import UserWithPermissions


class AuditService:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path
        init_db(self.db_path)

    def list_audits(self, auditor_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Retorna todas las auditorías registradas en la base de datos centralizada.
        El perfil principal del Dr. Daniel Enríquez tiene acceso al 100% consolidado.
        """
        with get_db_connection(self.db_path) as conn:
            query = "SELECT * FROM audit_records"
            params = []
            if auditor_id:
                query += " WHERE auditor_id = ?"
                params.append(auditor_id)
            query += " ORDER BY audit_date DESC, created_at DESC"

            cur = conn.execute(query, tuple(params))
            rows = cur.fetchall()
            return [self._row_to_audit_dict(r) for r in rows]

    def get_audit_by_id(self, audit_id: str) -> Optional[Dict[str, Any]]:
        with get_db_connection(self.db_path) as conn:
            cur = conn.execute("SELECT * FROM audit_records WHERE id = ?", (audit_id,))
            row = cur.fetchone()
            if not row:
                return None
            return self._row_to_audit_dict(row)

    def save_audit(self, data: Dict[str, Any], auditor_user: Optional[UserWithPermissions] = None) -> Dict[str, Any]:
        """
        Registra una nueva auditoría en el repositorio central.
        Asocia de manera obligatoria los metadatos del auditor que efectúa la evaluación.
        """
        if auditor_user and not auditor_user.has_permission("can_review_audit"):
            raise SecurityException("Acceso denegado: Se requiere el permiso 'can_review_audit' para realizar auditorías.")

        audit_id = data.get("id") or ("AUD-" + uuid.uuid4().hex[:8].upper())
        now_iso = datetime.now().isoformat()
        evals_json = json.dumps(data.get("evaluations", {}), ensure_ascii=False)
        comments_json = json.dumps(data.get("comments", {}), ensure_ascii=False)

        auditor_id = auditor_user.id if auditor_user else data.get("auditorId")
        auditor_name = auditor_user.nombre_completo if auditor_user else (data.get("auditorName") or "No especificado")
        auditor_username = auditor_user.username if auditor_user else (data.get("auditorUsername") or "sistema")

        with get_db_connection(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO audit_records (
                    id, hc_number, audit_date, doctor_name, patient_id, patient_name,
                    service_type, score, risk_level, is_compliant, evaluations_json,
                    comments_json, audit_note, auditor_id, auditor_name, auditor_username,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    hc_number = excluded.hc_number,
                    audit_date = excluded.audit_date,
                    doctor_name = excluded.doctor_name,
                    patient_id = excluded.patient_id,
                    patient_name = excluded.patient_name,
                    service_type = excluded.service_type,
                    score = excluded.score,
                    risk_level = excluded.risk_level,
                    is_compliant = excluded.is_compliant,
                    evaluations_json = excluded.evaluations_json,
                    comments_json = excluded.comments_json,
                    audit_note = excluded.audit_note,
                    auditor_id = excluded.auditor_id,
                    auditor_name = excluded.auditor_name,
                    auditor_username = excluded.auditor_username,
                    updated_at = excluded.updated_at
                """,
                (
                    audit_id,
                    str(data.get("hcNumber", "")).strip(),
                    str(data.get("auditDate", "")).strip(),
                    str(data.get("doctorName", "")).strip(),
                    str(data.get("patientId", "")).strip(),
                    str(data.get("patientName", "")).strip(),
                    str(data.get("serviceType", "")).strip(),
                    float(data.get("score", 0.0)),
                    str(data.get("riskLevel", "CRITICO")),
                    1 if data.get("isCompliant", False) else 0,
                    evals_json,
                    comments_json,
                    data.get("auditNote"),
                    auditor_id,
                    auditor_name,
                    auditor_username,
                    now_iso,
                    now_iso,
                )
            )

            cur = conn.execute("SELECT * FROM audit_records WHERE id = ?", (audit_id,))
            return self._row_to_audit_dict(cur.fetchone())

    def delete_audit(self, audit_id: str, acting_user: Optional[UserWithPermissions] = None) -> bool:
        """
        Elimina una auditoría del repositorio central.
        Requiere de forma estricta el permiso 'can_delete_audit'.
        """
        if acting_user and not acting_user.has_permission("can_delete_audit"):
            raise SecurityException("Acceso denegado: Se requiere el permiso 'can_delete_audit' para eliminar auditorías.")

        with get_db_connection(self.db_path) as conn:
            cur = conn.execute("DELETE FROM audit_records WHERE id = ?", (audit_id,))
            return cur.rowcount > 0

    def list_cycles(self) -> List[Dict[str, Any]]:
        with get_db_connection(self.db_path) as conn:
            cur = conn.execute("SELECT * FROM audit_cycles ORDER BY start_date DESC, created_at DESC")
            rows = cur.fetchall()
            return [self._row_to_cycle_dict(r) for r in rows]

    def save_cycle(self, data: Dict[str, Any]) -> Dict[str, Any]:
        cycle_id = data.get("id") or ("CYC-" + uuid.uuid4().hex[:8].upper())
        now_iso = datetime.now().isoformat()
        summary_json = json.dumps(data.get("summary", {}), ensure_ascii=False)

        with get_db_connection(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO audit_cycles (
                    id, name, start_date, end_date, total_audits, global_score,
                    notes, summary_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    start_date = excluded.start_date,
                    end_date = excluded.end_date,
                    total_audits = excluded.total_audits,
                    global_score = excluded.global_score,
                    notes = excluded.notes,
                    summary_json = excluded.summary_json
                """,
                (
                    cycle_id,
                    str(data.get("name", "")).strip(),
                    str(data.get("startDate", "")).strip(),
                    str(data.get("endDate", "")).strip(),
                    int(data.get("totalAudits", 0)),
                    float(data.get("globalScore", 0.0)),
                    data.get("notes"),
                    summary_json,
                    now_iso,
                )
            )

            cur = conn.execute("SELECT * FROM audit_cycles WHERE id = ?", (cycle_id,))
            return self._row_to_cycle_dict(cur.fetchone())

    def _row_to_audit_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        try:
            evals = json.loads(row["evaluations_json"]) if row["evaluations_json"] else {}
        except Exception:
            evals = {}
        try:
            comments = json.loads(row["comments_json"]) if row["comments_json"] else {}
        except Exception:
            comments = {}

        return {
            "id": row["id"],
            "hcNumber": row["hc_number"],
            "auditDate": row["audit_date"],
            "doctorName": row["doctor_name"],
            "patientId": row["patient_id"],
            "patientName": row["patient_name"],
            "serviceType": row["service_type"],
            "score": float(row["score"]),
            "riskLevel": row["risk_level"],
            "isCompliant": bool(row["is_compliant"]),
            "evaluations": evals,
            "comments": comments,
            "auditNote": row["audit_note"],
            "auditorId": row["auditor_id"],
            "auditorName": row["auditor_name"],
            "auditorUsername": row["auditor_username"],
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"]
        }

    def _row_to_cycle_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        try:
            summary = json.loads(row["summary_json"]) if row["summary_json"] else {}
        except Exception:
            summary = {}

        return {
            "id": row["id"],
            "name": row["name"],
            "startDate": row["start_date"],
            "endDate": row["end_date"],
            "totalAudits": int(row["total_audits"]),
            "globalScore": float(row["global_score"]),
            "notes": row["notes"],
            "summary": summary,
            "createdAt": row["created_at"]
        }
