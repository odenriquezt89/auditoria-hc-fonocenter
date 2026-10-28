"""
Gestión de Base de Datos SQLite para Usuarios, Credenciales y Permisos (RBAC).
Garantiza integridad referencial, índices únicos y persistencia atómica.
"""

import os
import sqlite3
from contextlib import contextmanager
from typing import Generator


def get_default_db_path() -> str:
    """Obtiene la ruta de la base de datos desde entorno o valor por defecto."""
    env_path = os.getenv("SECURITY_DB_PATH")
    if env_path:
        return env_path

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, "data")
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, "auditoria_seguridad.db")


@contextmanager
def get_db_connection(db_path: str = None) -> Generator[sqlite3.Connection, None, None]:
    """
    Context manager para conexiones a la base de datos SQLite con
    soporte de llaves foráneas y diccionarios de filas.
    """
    path = db_path or get_default_db_path()
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)

    conn = sqlite3.connect(path, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")

    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path: str = None) -> None:
    """
    Crea las tablas 'users' y 'permissions' con sus respectivas restricciones
    e índices únicos si aún no existen.
    """
    schema_sql = """
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        nombre_completo TEXT NOT NULL,
        documento_identidad TEXT UNIQUE NOT NULL,
        tarjeta_profesional TEXT,
        correo TEXT UNIQUE NOT NULL,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        estado INTEGER NOT NULL DEFAULT 1,
        es_admin_principal INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS permissions (
        id TEXT PRIMARY KEY,
        user_id TEXT UNIQUE NOT NULL,
        can_delete_audit INTEGER NOT NULL DEFAULT 0,
        can_review_audit INTEGER NOT NULL DEFAULT 1,
        can_send_whatsapp INTEGER NOT NULL DEFAULT 0,
        can_create_users INTEGER NOT NULL DEFAULT 0,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS audit_records (
        id TEXT PRIMARY KEY,
        hc_number TEXT NOT NULL,
        audit_date TEXT NOT NULL,
        doctor_name TEXT NOT NULL,
        patient_id TEXT,
        patient_name TEXT,
        service_type TEXT,
        score REAL NOT NULL,
        risk_level TEXT NOT NULL,
        is_compliant INTEGER NOT NULL,
        evaluations_json TEXT NOT NULL,
        comments_json TEXT,
        audit_note TEXT,
        auditor_id TEXT,
        auditor_name TEXT,
        auditor_username TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS audit_cycles (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        start_date TEXT NOT NULL,
        end_date TEXT NOT NULL,
        total_audits INTEGER NOT NULL DEFAULT 0,
        global_score REAL NOT NULL DEFAULT 0.0,
        notes TEXT,
        summary_json TEXT,
        created_at TEXT NOT NULL
    );

    CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
    CREATE INDEX IF NOT EXISTS idx_users_documento ON users(documento_identidad);
    CREATE INDEX IF NOT EXISTS idx_users_correo ON users(correo);
    CREATE INDEX IF NOT EXISTS idx_permissions_user_id ON permissions(user_id);
    CREATE INDEX IF NOT EXISTS idx_audits_hc_number ON audit_records(hc_number);
    CREATE INDEX IF NOT EXISTS idx_audits_doctor ON audit_records(doctor_name);
    CREATE INDEX IF NOT EXISTS idx_audits_auditor ON audit_records(auditor_id);
    CREATE INDEX IF NOT EXISTS idx_audits_date ON audit_records(audit_date);
    """

    with get_db_connection(db_path) as conn:
        conn.executescript(schema_sql)
