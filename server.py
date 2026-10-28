"""
Servidor Local de Red y API Centralizada para Auditoría Clínica - FONOCENTER IPS.
Permite el trabajo simultáneo en línea de múltiples usuarios y auditores en red local (LAN/Wi-Fi).
Consolida todas las auditorías en tiempo real en la base de datos central SQLite y sirve la aplicación web.
"""

from datetime import datetime
import json
import os
import socket
import sys
from typing import Optional, List, Dict, Any

import uvicorn
from fastapi import FastAPI, HTTPException, Request, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Asegurar importación de módulos locales
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from security.service import UserService, SecurityException
from security.audit_service import AuditService
from security.models import UserCreate, UserUpdate, LoginRequest


app = FastAPI(
    title="FONOCENTER IPS - Sistema de Auditoría Médica y RBAC",
    description="API Centralizada para Trabajo en Línea Multiusuario y Control de Accesos",
    version="2.0.0"
)

# Permitir CORS total para conexiones dentro de la red local
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

user_service = UserService()
audit_service = AuditService()


def get_local_ip() -> str:
    """Detecta la dirección IP de la máquina en la red local (LAN / Wi-Fi)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # No requiere conexión a internet real, solo resuelve la interfaz primaria
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        try:
            ip = socket.gethostbyname(socket.gethostname())
        except Exception:
            ip = "127.0.0.1"
    finally:
        s.close()
    return ip


# ----------------------------------------------------
# 1. ESTADO DEL SERVIDOR Y RED LOCAL
# ----------------------------------------------------
@app.get("/api/server-info")
def get_server_info():
    local_ip = get_local_ip()
    users = user_service.list_users(include_inactive=True)
    audits = audit_service.list_audits()
    cycles = audit_service.list_cycles()

    return {
        "status": "online",
        "institutional_name": "FONOCENTER IPS",
        "hostname": socket.gethostname(),
        "local_ip": local_ip,
        "port": 8000,
        "local_url": f"http://localhost:8000",
        "lan_url": f"http://{local_ip}:8000",
        "stats": {
            "total_users": len(users),
            "total_audits": len(audits),
            "total_cycles": len(cycles)
        },
        "timestamp": datetime.now().isoformat()
    }


# ----------------------------------------------------
# 2. AUTENTICACIÓN Y SESIÓN
# ----------------------------------------------------
@app.post("/api/auth/login")
def login(creds: LoginRequest):
    auth_res = user_service.authenticate(creds.username, creds.password)
    if not auth_res.success or not auth_res.user:
        raise HTTPException(status_code=401, detail=auth_res.message)

    return {
        "success": True,
        "message": auth_res.message,
        "user": auth_res.user.to_dict()
    }


# ----------------------------------------------------
# 3. GESTIÓN DE USUARIOS Y CONTROL DE ACCESO (RBAC)
# ----------------------------------------------------
@app.get("/api/users")
def list_users():
    users = user_service.list_users(include_inactive=True)
    return [u.to_dict() for u in users]


@app.post("/api/users")
def create_user(user_data: UserCreate, request: Request):
    acting_user_id = request.headers.get("x-user-id")
    if not acting_user_id:
        raise HTTPException(status_code=403, detail="Acceso denegado: Se requiere autenticación como Administrador Principal.")
    actor = user_service.get_user_by_id(acting_user_id)
    if not actor or not actor.es_admin_principal:
        raise HTTPException(status_code=403, detail="Acceso denegado: Únicamente el Administrador Principal puede agregar otros usuarios y asignar permisos.")
    try:
        new_user = user_service.create_user(user_data, creator_user_id=acting_user_id)
        return new_user.to_dict()
    except SecurityException as se:
        raise HTTPException(status_code=403, detail=str(se))
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))


@app.put("/api/users/{user_id}")
def update_user(user_id: str, update_data: UserUpdate, request: Request):
    acting_user_id = request.headers.get("x-user-id")
    if not acting_user_id:
        raise HTTPException(status_code=403, detail="Acceso denegado: Se requiere autenticación como Administrador Principal.")
    actor = user_service.get_user_by_id(acting_user_id)
    if not actor or not actor.es_admin_principal:
        raise HTTPException(status_code=403, detail="Acceso denegado: Únicamente el Administrador Principal puede otorgar permisos o modificar otros usuarios.")
    try:
        updated = user_service.update_user(user_id, update_data, operator_user_id=acting_user_id)
        return updated.to_dict()
    except SecurityException as se:
        raise HTTPException(status_code=403, detail=str(se))
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))


@app.delete("/api/users/{user_id}")
def delete_user(user_id: str, request: Request):
    acting_user_id = request.headers.get("x-user-id")
    if not acting_user_id:
        raise HTTPException(status_code=403, detail="Acceso denegado: Se requiere autenticación como Administrador Principal.")
    actor = user_service.get_user_by_id(acting_user_id)
    if not actor or not actor.es_admin_principal:
        raise HTTPException(status_code=403, detail="Acceso denegado: Únicamente el Administrador Principal puede eliminar usuarios del sistema.")
    try:
        success = user_service.delete_user(user_id, operator_user_id=acting_user_id)
        return {"success": success}
    except SecurityException as se:
        raise HTTPException(status_code=403, detail=str(se))


# ----------------------------------------------------
# 4. AUDITORÍAS CENTRALIZADAS (VISIBILIDAD TOTAL)
# ----------------------------------------------------
@app.get("/api/audits")
def get_all_audits(auditor_id: Optional[str] = None):
    """
    Retorna el consolidado de todas las auditorías registradas en la institución.
    El perfil principal del Dr. Daniel Enríquez ve el 100% de las auditorías sin importar quién las realizó.
    """
    return audit_service.list_audits(auditor_id=auditor_id)


@app.post("/api/audits")
def save_audit(audit_data: Dict[str, Any], request: Request):
    acting_user_id = request.headers.get("x-user-id")
    auditor_user = user_service.get_user_by_id(acting_user_id) if acting_user_id else None

    try:
        saved = audit_service.save_audit(audit_data, auditor_user=auditor_user)
        return saved
    except SecurityException as se:
        raise HTTPException(status_code=403, detail=str(se))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api/audits/{audit_id}")
def delete_audit(audit_id: str, request: Request):
    acting_user_id = request.headers.get("x-user-id")
    acting_user = user_service.get_user_by_id(acting_user_id) if acting_user_id else None

    try:
        deleted = audit_service.delete_audit(audit_id, acting_user=acting_user)
        return {"success": deleted}
    except SecurityException as se:
        raise HTTPException(status_code=403, detail=str(se))


# ----------------------------------------------------
# 5. CICLOS DE AUDITORÍA CENTRALIZADOS
# ----------------------------------------------------
@app.get("/api/cycles")
def get_cycles():
    return audit_service.list_cycles()


@app.post("/api/cycles")
def save_cycle(cycle_data: Dict[str, Any]):
    return audit_service.save_cycle(cycle_data)


# ----------------------------------------------------
# 6. ENTREGA DE LA APLICACIÓN WEB (HTML / ASSETS)
# ----------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def serve_index():
    index_file = os.path.join(BASE_DIR, "index.html")
    if os.path.exists(index_file):
        with open(index_file, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h3>index.html no encontrado</h3>", status_code=404)


def main():
    local_ip = get_local_ip()
    port = 8000

    print("\n" + "=" * 78)
    print("  FONOCENTER IPS - SERVIDOR DE AUDITORÍA CLÍNICA MULTIUSUARIO EN LÍNEA")
    print("=" * 78)
    print(f"  • Acceso Local (esta máquina):             http://localhost:{port}")
    print(f"  • Acceso Red Local LAN (otros equipos):    http://{local_ip}:{port}")
    print(f"  • Documentación API Interactiva (Swagger): http://localhost:{port}/docs")
    print(f"  • Administrador Maestro Inicial:           daniel.enriquez")
    print("=" * 78)
    print("  -> Presione Ctrl+C en cualquier momento para detener el servidor.")
    print("=" * 78 + "\n")

    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")


if __name__ == "__main__":
    main()
