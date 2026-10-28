"""
Módulo de Hashing Seguro de Contraseñas.
Implementa bcrypt con sal aleatoria como motor criptográfico primario
según los estándares de seguridad de la información en salud.
"""

import hashlib
import os

try:
    import bcrypt
    _HAS_BCRYPT = True
except ImportError:
    _HAS_BCRYPT = False


def hash_password(password: str) -> str:
    """
    Genera un hash seguro con sal para una contraseña en texto plano.
    Utiliza bcrypt por defecto.
    """
    if not password:
        raise ValueError("La contraseña no puede estar vacía")

    if _HAS_BCRYPT:
        # Generar sal y derivar hash bcrypt (12 rondas de complejidad por defecto)
        salt = bcrypt.gensalt(rounds=12)
        hashed_bytes = bcrypt.hashpw(password.encode("utf-8"), salt)
        return hashed_bytes.decode("utf-8")
    else:
        # Fallback de alta seguridad con PBKDF2-HMAC-SHA256 (600.000 iteraciones)
        salt = os.urandom(16)
        kdf = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 600000)
        return f"pbkdf2:sha256:600000${salt.hex()}${kdf.hex()}"


def verify_password(plain_password: str, password_hash: str) -> bool:
    """
    Verifica si una contraseña en texto plano coincide con el hash almacenado.
    Soporta hashes bcrypt y fallback PBKDF2.
    """
    if not plain_password or not password_hash:
        return False

    try:
        if password_hash.startswith("$2b$") or password_hash.startswith("$2a$") or password_hash.startswith("$2y$"):
            if not _HAS_BCRYPT:
                return False
            return bcrypt.checkpw(plain_password.encode("utf-8"), password_hash.encode("utf-8"))
        elif password_hash.startswith("pbkdf2:sha256:"):
            parts = password_hash.split("$")
            if len(parts) != 3:
                return False
            iterations = int(parts[0].split(":")[2])
            salt = bytes.fromhex(parts[1])
            expected_kdf = bytes.fromhex(parts[2])
            actual_kdf = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt, iterations)
            import hmac
            return hmac.compare_digest(actual_kdf, expected_kdf)
        return False
    except Exception:
        return False
