# FONOCENTER IPS - Sistema de Auditoría Médica de Historias Clínicas & RBAC

Sistema institucional integral para la evaluación, auditoría concurrente en red local, seguimiento del ciclo PHVA y notificación multicanal de Historias Clínicas, alineado con las directrices de la **Resolución 1995 de 1999** y la **Resolución 3100 de 2019** del Ministerio de Salud y Protección Social de Colombia.

---

## 🌟 Características Principales

1. **Trabajo Multiusuario Concurrente en Red Local (LAN / Wi-Fi)**:
   - Backend centralizado en **FastAPI** (`server.py`) con base de datos SQLite en modo WAL (`data/auditoria_seguridad.db`).
   - Múltiples auditores pueden conectarse simultáneamente desde diferentes computadores, portátiles o tabletas conectadas a la red de la clínica.
   - Script de inicio con doble clic: `INICIAR_SERVIDOR_RED_LOCAL.bat`.

2. **Control de Acceso Basado en Roles (RBAC Estricto)**:
   - Autenticación segura mediante contraseñas hasheadas con **bcrypt** (costo 12).
   - Administrador Maestro: **Dr. Daniel Enríquez** (`daniel.enriquez`).
   - **Reglas de Seguridad Estrictas**: Únicamente el Administrador Principal puede crear usuarios, otorgar o revocar permisos, o eliminar usuarios del sistema. Los auditores estándar no tienen privilegios de administración.
   - Matriz de permisos operativos:
     - `can_delete_audit`: Permiso para eliminar registros de auditoría (crítico).
     - `can_review_audit`: Permiso para auditar y evaluar historias clínicas.
     - `can_send_whatsapp`: Permiso para enviar notificaciones clínicas vía WhatsApp.
     - `can_create_users`: Reservado exclusivamente para el Administrador Principal.

3. **Cierre de Ciclos y Comparación Periódica**:
   - Módulo en la pestaña **Registros** para cerrar periodos o ciclos de auditoría (ej: "Auditoría Enero 2026", "Auditoría Trimestre I").
   - Comparación y trazabilidad histórica del cumplimiento técnico y calidad del registro médico.

4. **Visibilidad Total y Trazabilidad Institucional**:
   - Cada auditoría almacena la huella digital del auditor (`auditorId`, `auditorName`, `auditorUsername`).
   - El perfil maestro consolida y supervisa el 100% de las auditorías generadas en la institución.

5. **Notificaciones Multicanal Automatizadas**:
   - Notificación de hallazgos a médicos evaluados mediante **Correo Electrónico** (SMTP/SendGrid) y **WhatsApp** (Twilio/Meta Cloud API).

---

## 📁 Estructura del Repositorio

```text
AUDITORIA HC FONOCENTER/
├── index.html                        # Interfaz Web de Auditoría Médica (SPA)
├── server.py                         # API FastAPI y Servidor Web Concurrente
├── INICIAR_SERVIDOR_RED_LOCAL.bat    # Lanzador por lotes con detección de IP
├── requirements.txt                  # Dependencias del servidor y seguridad
├── .env.example                      # Plantilla de variables de entorno
├── .gitignore                        # Reglas de exclusión para Git
├── data/                             # Base de datos SQLite y datos de referencia
│   └── medicos_auditoria_bd.csv      # Directorio institucional de médicos
├── security/                         # Módulo RBAC y Lógica de Seguridad
│   ├── database.py                   # Conexión SQLite con WAL y PRAGMAs
│   ├── models.py                     # Esquemas Pydantic y DTOs
│   ├── hasher.py                     # Cifrado seguro de contraseñas con bcrypt
│   ├── service.py                    # Reglas de negocio RBAC y Semilla Maestra
│   └── audit_service.py              # Servicio centralizado de auditorías y ciclos
├── tests/                            # Pruebas unitarias automatizadas
│   ├── test_security.py              # Suite de pruebas de seguridad y RBAC
│   ├── test_audit_service.py         # Suite de pruebas del servicio de auditoría
│   └── test_server_endpoints.py      # Pruebas de integración de endpoints
├── notifications/                    # Motor de despacho multicanal
├── templates/                        # Plantillas HTML y texto para alertas
└── reports/                          # Informes ejecutivos y bitácoras
```

---

## 🚀 Puesta en Marcha Rápida

### 1. Requisitos Previos
- Python 3.10 o superior.
- Navegador Web moderno (Google Chrome, Microsoft Edge, Mozilla Firefox).

### 2. Instalación de Dependencias
```bash
pip install -r requirements.txt
```

### 3. Iniciar el Servidor de Red Local
Haga doble clic en el archivo:
```text
INICIAR_SERVIDOR_RED_LOCAL.bat
```
O ejecute manualmente desde la consola:
```bash
python server.py
```

El servidor detectará automáticamente la dirección IP local de su equipo y mostrará:
- **Acceso Local:** `http://localhost:8000`
- **Acceso en Red Local (otros equipos):** `http://<IP-DE-SU-EQUIPO>:8000`

---

## 🧪 Ejecución de Pruebas Automatizadas

Para validar la integridad del sistema, reglas de seguridad y RBAC:
```bash
python -m unittest discover -s tests -p "test_*.py"
```

---

## 🔒 Buenas Prácticas de Seguridad
- El archivo de base de datos `auditoria_seguridad.db` se almacena localmente y está excluido de control de versiones para proteger la confidencialidad de datos clínicos según la Ley Estatutaria 1581 de 2012 (Habeas Data).
- Copie `.env.example` a `.env` para configurar credenciales institucionales seguras.

---

## 👥 Autores y Créditos
- **Líder Institucional & Administrador Maestro**: Dr. Daniel Enríquez
- **Institución**: FONOCENTER IPS
