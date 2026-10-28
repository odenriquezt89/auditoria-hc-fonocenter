"""
Herramienta CLI de Gestión de Seguridad y Usuarios RBAC.
Permite inicializar la base de datos, sembrar el administrador maestro,
crear usuarios, listar usuarios y verificar credenciales desde la terminal.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from security.service import UserService, SecurityException
from security.models import UserCreate


def main():
    parser = argparse.ArgumentParser(
        description="Gestión de Seguridad y Usuarios RBAC - FONOCENTER IPS"
    )
    subparsers = parser.add_subparsers(dest="command", help="Comandos disponibles")

    # init-db
    subparsers.add_parser("init-db", help="Inicializa la base de datos y la semilla del administrador maestro.")

    # list-users
    subparsers.add_parser("list-users", help="Lista todos los usuarios registrados y su estado/permisos.")

    # create-user
    create_parser = subparsers.add_parser("create-user", help="Crea un nuevo usuario en el sistema.")
    create_parser.add_argument("--nombre", required=True, help="Nombre completo del usuario")
    create_parser.add_argument("--doc", required=True, help="Documento de identidad (cédula)")
    create_parser.add_argument("--email", required=True, help="Correo electrónico")
    create_parser.add_argument("--username", required=True, help="Nombre de usuario único")
    create_parser.add_argument("--password", required=True, help="Contraseña segura")
    create_parser.add_argument("--tarjeta", default=None, help="Tarjeta profesional médica")
    create_parser.add_argument("--creator", default=None, help="ID del usuario creador (debe tener can_create_users)")
    create_parser.add_argument("--can-delete", action="store_true", help="Permiso para eliminar auditorías")
    create_parser.add_argument("--can-review", action="store_true", help="Permiso para auditar y revisar HC")
    create_parser.add_argument("--can-whatsapp", action="store_true", help="Permiso para enviar notificaciones WhatsApp")
    create_parser.add_argument("--can-create-users", action="store_true", help="Permiso para registrar nuevos usuarios")

    # verify-login
    login_parser = subparsers.add_parser("verify-login", help="Verifica las credenciales de un usuario.")
    login_parser.add_argument("--username", required=True, help="Nombre de usuario o correo")
    login_parser.add_argument("--password", required=True, help="Contraseña a verificar")

    args = parser.parse_args()

    service = UserService()

    if args.command == "init-db":
        master = service.seed_master_admin()
        print(f"[OK] Base de datos lista. Administrador Maestro verificado:")
        print(f"     ID: {master.id}")
        print(f"     Nombre: {master.nombre_completo}")
        print(f"     Username: {master.username}")
        print(f"     Documento: {master.documento_identidad}")
        print(f"     Admin Principal: {master.es_admin_principal}")
        print(f"     Permisos: {master.permisos.to_dict()}")

    elif args.command == "list-users":
        users = service.list_users(include_inactive=True)
        print(f"\n{'='*95}")
        print(f"{'ID':<38} | {'USERNAME':<16} | {'NOMBRE':<25} | {'ESTADO':<8} | {'ADMIN':<5}")
        print(f"{'='*95}")
        for u in users:
            status = "ACTIVO" if u.estado else "INACTIVO"
            admin = "SI" if u.es_admin_principal else "NO"
            print(f"{u.id:<38} | {u.username:<16} | {u.nombre_completo[:24]:<25} | {status:<8} | {admin:<5}")
            p = u.permisos
            print(f"   -> Permisos: Delete={p.can_delete_audit} | Review={p.can_review_audit} | WhatsApp={p.can_send_whatsapp} | CreateUsers={p.can_create_users}")
        print(f"{'='*95}\nTotal usuarios: {len(users)}\n")

    elif args.command == "create-user":
        try:
            user_data = UserCreate(
                nombre_completo=args.nombre,
                documento_identidad=args.doc,
                tarjeta_profesional=args.tarjeta,
                correo=args.email,
                username=args.username,
                password=args.password,
                estado=True,
                can_delete_audit=args.can_delete,
                can_review_audit=args.can_review,
                can_send_whatsapp=args.can_whatsapp,
                can_create_users=args.can_create_users
            )
            created = service.create_user(user_data, creator_user_id=args.creator)
            print(f"[OK] Usuario creado exitosamente:")
            print(f"     ID: {created.id}")
            print(f"     Username: {created.username}")
            print(f"     Nombre: {created.nombre_completo}")
        except SecurityException as se:
            print(f"[ERROR DE SEGURIDAD] {se}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"[ERROR] {e}", file=sys.stderr)
            sys.exit(1)

    elif args.command == "verify-login":
        auth_res = service.authenticate(args.username, args.password)
        if auth_res:
            u = auth_res.user
            print(f"[EXITO] Autenticación válida.")
            print(f"     Usuario: {u.nombre_completo} ({u.username})")
            print(f"     Admin Principal: {u.es_admin_principal}")
            print(f"     Permisos: {u.permisos.model_dump()}")
        else:
            print(f"[FALLO] Credenciales inválidas o usuario inactivo.", file=sys.stderr)
            sys.exit(1)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
