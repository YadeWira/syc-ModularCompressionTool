"""
crypto.py - Encriptación para SYC

Algoritmos soportados:
  AES256  -> AES-256-GCM  (autenticado, hardware acelerado)
  CC20    -> ChaCha20-Poly1305 (autenticado, rápido en ARM)

Ambos son AEAD (Authenticated Encryption with Associated Data):
  - Encriptan los datos
  - Generan un tag de autenticación (detecta tampering)
  - Usan un nonce aleatorio por operación

Formato del bloque encriptado:
  [1 byte]   algoritmo: 0x01=AES256, 0x02=CC20
  [16 bytes] salt (para derivar clave desde password)
  [12 bytes] nonce
  [N bytes]  ciphertext + tag (16 bytes al final, incluido en ciphertext)
"""

import os
import struct
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM, ChaCha20Poly1305

ALG_AES256 = 0x01
ALG_CC20   = 0x02

ALG_NAMES = {
    "AES256": ALG_AES256,
    "CC20":   ALG_CC20,
}
ALG_IDS = {v: k for k, v in ALG_NAMES.items()}

ITERATIONS = 100_000  # PBKDF2 iterations


def _derive_key(password: str, salt: bytes, alg: int) -> bytes:
    """Deriva una clave de 32 bytes desde el password usando PBKDF2-HMAC-SHA256"""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=ITERATIONS,
    )
    return kdf.derive(password.encode("utf-8"))


def encrypt(data: bytes, password: str, alg_name: str = "AES256") -> bytes:
    """
    Encripta datos con el algoritmo especificado.
    Devuelve el bloque encriptado con header incluido.
    """
    alg = ALG_NAMES.get(alg_name.upper())
    if alg is None:
        raise ValueError(f"Algoritmo desconocido: {alg_name!r}. Usa AES256 o CC20")

    salt  = os.urandom(16)
    nonce = os.urandom(12)
    key   = _derive_key(password, salt, alg)

    if alg == ALG_AES256:
        cipher = AESGCM(key)
    else:
        cipher = ChaCha20Poly1305(key)

    ciphertext = cipher.encrypt(nonce, data, None)

    return struct.pack("<B", alg) + salt + nonce + ciphertext


def decrypt(blob: bytes, password: str) -> bytes:
    """
    Desencripta un bloque producido por encrypt().
    Lanza InvalidTag si la contraseña es incorrecta o los datos fueron alterados.
    """
    if len(blob) < 1 + 16 + 12:
        raise ValueError("Bloque encriptado demasiado corto")

    alg   = struct.unpack("<B", blob[0:1])[0]
    salt  = blob[1:17]
    nonce = blob[17:29]
    ciphertext = blob[29:]

    key = _derive_key(password, salt, alg)

    if alg == ALG_AES256:
        cipher = AESGCM(key)
    elif alg == ALG_CC20:
        cipher = ChaCha20Poly1305(key)
    else:
        raise ValueError(f"Algoritmo desconocido en archivo: 0x{alg:02x}")

    try:
        return cipher.decrypt(nonce, ciphertext, None)
    except Exception:
        raise ValueError("Contraseña incorrecta o archivo corrupto")


def alg_name(blob: bytes) -> str:
    """Devuelve el nombre del algoritmo usado en un bloque encriptado"""
    if not blob:
        return ""
    alg = struct.unpack("<B", blob[0:1])[0]
    return ALG_IDS.get(alg, f"0x{alg:02x}")
