"""
archive.py - Maneja el formato de archivo .syc

Flags (1 byte):
  bit 0: tar sólido
  bit 1: datos encriptados
  bit 2: cabecera + datos encriptados (full-encrypted)
  bit 3: CRC32 presente en entradas
  bit 4: MD5 presente en entradas

Formato normal:
  [4 bytes]  Magic: b'SYC\x01'
  [1 byte]   Flags
  [2 bytes]  Longitud del método
  [N bytes]  Nombre del método
  [4 bytes]  Número de entradas
  Por cada entrada:
    [2 bytes]  Longitud del nombre
    [N bytes]  Nombre
    [8 bytes]  Tamaño original
    [8 bytes]  Tamaño comprimido (0 si tar)
    [4 bytes]  CRC32 (solo si FLAG_CRC32)
    [16 bytes] MD5  (solo si FLAG_MD5)
    [M bytes]  Datos comprimidos (ausente si tar o full-encrypted)

  Si FLAG_TAR:
    [8 bytes]  tar_original_size
    [8 bytes]  tar_compressed_size
    [M bytes]  bloque tar (encriptado si FLAG_ENC o FLAG_FULL_ENC)

  Si FLAG_ENC (sin tar): los datos de cada entrada están encriptados individualmente
  Si FLAG_FULL_ENC: todo desde "número de entradas" en adelante está encriptado
"""

import struct
import os
import hashlib
import zlib
from dataclasses import dataclass, field
from typing import List, Optional

MAGIC = b'SYC\x01'

FLAG_TAR       = 0x01
FLAG_ENC       = 0x02  # datos encriptados
FLAG_FULL_ENC  = 0x04  # cabecera + datos encriptados
FLAG_CRC32     = 0x08
FLAG_MD5       = 0x10
FLAG_COMMENT   = 0x20  # archive comment present


@dataclass
class FileEntry:
    name: str
    original_size: int
    compressed_size: int = 0
    data: bytes = field(default=b"", repr=False)
    crc32: Optional[int] = None    # int o None
    md5:   Optional[bytes] = None  # 16 bytes o None


def compute_crc32(data: bytes) -> int:
    return zlib.crc32(data) & 0xFFFFFFFF

def compute_md5(data: bytes) -> bytes:
    return hashlib.md5(data).digest()


class SycArchive:

    def __init__(self, method: str = "", tar_mode: bool = False,
                 enc_key: str = None, enc_alg: str = "AES256",
                 full_encrypted: bool = False):
        self.method          = method
        self.tar_mode        = tar_mode
        self.enc_key         = enc_key          # None = sin encriptación
        self.enc_alg         = enc_alg
        self.full_encrypted  = full_encrypted   # encriptar cabecera también
        self.comment: str = ""          # archive comment (optional)
        self.entries: List[FileEntry] = []
        self.tar_original_size:   int   = 0
        self.tar_compressed_size: int   = 0
        self.tar_data:            bytes = b""
        # Flags detectados al leer
        self._has_crc32 = False
        self._has_md5   = False

    def add_entry(self, name: str, original_size: int,
                  compressed_data: bytes = b"", compressed_size: int = 0,
                  crc32: int = None, md5: bytes = None):
        self.entries.append(FileEntry(
            name=name,
            original_size=original_size,
            compressed_size=len(compressed_data) if compressed_data else compressed_size,
            data=compressed_data,
            crc32=crc32,
            md5=md5,
        ))

    def set_tar_block(self, tar_original: bytes, tar_compressed: bytes):
        self.tar_original_size   = len(tar_original)
        self.tar_compressed_size = len(tar_compressed)
        self.tar_data            = tar_compressed

    # ── Flags ────────────────────────────────────────────────────────────────

    def _build_flags(self) -> int:
        flags = 0
        if self.tar_mode:       flags |= FLAG_TAR
        if self.full_encrypted: flags |= FLAG_FULL_ENC
        elif self.enc_key:      flags |= FLAG_ENC
        if any(e.crc32 is not None for e in self.entries): flags |= FLAG_CRC32
        if any(e.md5   is not None for e in self.entries): flags |= FLAG_MD5
        if self.comment: flags |= FLAG_COMMENT
        return flags

    # ── Serialización del índice ──────────────────────────────────────────────

    def _serialize_index(self, flags: int) -> bytes:
        """Serializa número de entradas + cada entrada (sin los datos del tar)"""
        import io
        buf = io.BytesIO()
        buf.write(struct.pack("<I", len(self.entries)))
        has_crc = bool(flags & FLAG_CRC32)
        has_md5 = bool(flags & FLAG_MD5)
        for entry in self.entries:
            name_b = entry.name.encode("utf-8")
            buf.write(struct.pack("<H", len(name_b)))
            buf.write(name_b)
            buf.write(struct.pack("<Q", entry.original_size))
            if self.tar_mode or (flags & FLAG_FULL_ENC):
                buf.write(struct.pack("<Q", 0))
            else:
                buf.write(struct.pack("<Q", entry.compressed_size))
            if has_crc:
                buf.write(struct.pack("<I", entry.crc32 or 0))
            if has_md5:
                buf.write(entry.md5 or b'\x00' * 16)
            # Datos de entrada (solo modo normal sin full_encrypted)
            if not self.tar_mode and not (flags & FLAG_FULL_ENC):
                buf.write(entry.data)
        return buf.getvalue()

    def _serialize_tar_block(self) -> bytes:
        return (struct.pack("<Q", self.tar_original_size) +
                struct.pack("<Q", self.tar_compressed_size) +
                self.tar_data)

    # ── Write ─────────────────────────────────────────────────────────────────

    def write(self, path: str):
        from crypto import encrypt
        flags = self._build_flags()

        with open(path, "wb") as f:
            f.write(MAGIC)
            f.write(struct.pack("<B", flags))
            method_b = self.method.encode("utf-8")
            f.write(struct.pack("<H", len(method_b)))
            f.write(method_b)

            # Write comment if present
            if flags & FLAG_COMMENT:
                comment_b = self.comment.encode("utf-8")
                f.write(struct.pack("<H", len(comment_b)))
                f.write(comment_b)

            if flags & FLAG_FULL_ENC:
                # Encriptar: índice + (bloque tar si aplica)
                index_bytes = self._serialize_index(flags)
                payload = index_bytes
                if self.tar_mode:
                    # Encriptar datos tar por separado dentro del payload
                    tar_data_enc = encrypt(self.tar_data, self.enc_key, self.enc_alg)
                    payload += (struct.pack("<Q", self.tar_original_size) +
                                struct.pack("<Q", len(tar_data_enc)) +
                                tar_data_enc)
                enc_payload = encrypt(payload, self.enc_key, self.enc_alg)
                # Guardar nombre del algoritmo (1 byte ya está en el blob)
                f.write(struct.pack("<Q", len(enc_payload)))
                f.write(enc_payload)

            else:
                # Índice en claro
                index_bytes = self._serialize_index(flags)
                f.write(index_bytes)

                if self.tar_mode:
                    tar_payload = self.tar_data
                    if flags & FLAG_ENC:
                        tar_payload = encrypt(tar_payload, self.enc_key, self.enc_alg)
                    f.write(struct.pack("<Q", self.tar_original_size))
                    f.write(struct.pack("<Q", len(tar_payload)))
                    f.write(tar_payload)

    # ── Read ──────────────────────────────────────────────────────────────────

    @classmethod
    def read(cls, path: str, password: str = None) -> "SycArchive":
        from crypto import decrypt, alg_name as _alg_name
        with open(path, "rb") as f:
            magic = f.read(4)
            if magic != MAGIC:
                raise ValueError(f"Archivo inválido: magic incorrecto ({magic!r})")

            flags      = struct.unpack("<B", f.read(1))[0]
            method_len = struct.unpack("<H", f.read(2))[0]
            method     = f.read(method_len).decode("utf-8")

            tar_mode      = bool(flags & FLAG_TAR)
            full_enc      = bool(flags & FLAG_FULL_ENC)
            enc           = bool(flags & FLAG_ENC)
            has_crc       = bool(flags & FLAG_CRC32)
            has_md5       = bool(flags & FLAG_MD5)
            has_comment   = bool(flags & FLAG_COMMENT)

            archive = cls(method=method, tar_mode=tar_mode)

            # Read comment if present
            if has_comment:
                comment_len = struct.unpack("<H", f.read(2))[0]
                archive.comment = f.read(comment_len).decode("utf-8")
            archive._has_crc32 = has_crc
            archive._has_md5   = has_md5

            if full_enc:
                if not password:
                    raise ValueError("Este archivo está encriptado. Usa -key PASSWORD")
                enc_len = struct.unpack("<Q", f.read(8))[0]
                enc_blob = f.read(enc_len)
                # Detectar algoritmo del blob
                archive.enc_alg = _alg_name(enc_blob)
                payload = decrypt(enc_blob, password)
                archive._parse_index(payload, flags, password, from_bytes=True)
            else:
                archive._parse_index_stream(f, flags, password)

        return archive

    def _parse_index(self, data: bytes, flags: int, password: str, from_bytes: bool = False):
        """Parsea el índice desde bytes (modo full_encrypted)"""
        import io
        from crypto import decrypt
        buf = io.BytesIO(data)
        has_crc = bool(flags & FLAG_CRC32)
        has_md5 = bool(flags & FLAG_MD5)
        tar_mode = bool(flags & FLAG_TAR)
        full_enc = bool(flags & FLAG_FULL_ENC)

        num_files = struct.unpack("<I", buf.read(4))[0]
        for _ in range(num_files):
            name_len = struct.unpack("<H", buf.read(2))[0]
            name     = buf.read(name_len).decode("utf-8")
            orig     = struct.unpack("<Q", buf.read(8))[0]
            comp     = struct.unpack("<Q", buf.read(8))[0]
            crc32    = struct.unpack("<I", buf.read(4))[0] if has_crc else None
            md5      = buf.read(16) if has_md5 else None
            data_b   = b"" if (tar_mode or full_enc) else buf.read(comp)
            self.entries.append(FileEntry(
                name=name, original_size=orig, compressed_size=comp,
                data=data_b, crc32=crc32, md5=md5
            ))

        if tar_mode:
            self.tar_original_size = struct.unpack("<Q", buf.read(8))[0]
            enc_tar_size           = struct.unpack("<Q", buf.read(8))[0]
            enc_tar                = buf.read(enc_tar_size)
            self.tar_data          = decrypt(enc_tar, password)
            self.tar_compressed_size = len(self.tar_data)

    def _parse_index_stream(self, f, flags: int, password: str):
        """Parsea el índice desde un stream de archivo (modo normal/enc)"""
        from crypto import decrypt
        has_crc  = bool(flags & FLAG_CRC32)
        has_md5  = bool(flags & FLAG_MD5)
        tar_mode = bool(flags & FLAG_TAR)
        enc      = bool(flags & FLAG_ENC)

        num_files = struct.unpack("<I", f.read(4))[0]
        for _ in range(num_files):
            name_len = struct.unpack("<H", f.read(2))[0]
            name     = f.read(name_len).decode("utf-8")
            orig     = struct.unpack("<Q", f.read(8))[0]
            comp     = struct.unpack("<Q", f.read(8))[0]
            crc32    = struct.unpack("<I", f.read(4))[0] if has_crc else None
            md5      = f.read(16) if has_md5 else None
            if tar_mode:
                data_b = b""
            else:
                raw = f.read(comp)
                data_b = decrypt(raw, password) if (enc and password) else raw
            self.entries.append(FileEntry(
                name=name, original_size=orig, compressed_size=comp,
                data=data_b, crc32=crc32, md5=md5
            ))

        if tar_mode:
            self.tar_original_size = struct.unpack("<Q", f.read(8))[0]
            comp_size              = struct.unpack("<Q", f.read(8))[0]
            raw_tar                = f.read(comp_size)
            self.tar_data          = decrypt(raw_tar, password) if (enc and password) else raw_tar
            self.tar_compressed_size = len(self.tar_data)

    # ── List ──────────────────────────────────────────────────────────────────

    def list_entries(self):
        result = []
        if self.tar_mode and self.tar_original_size > 0:
            total_orig = sum(e.original_size for e in self.entries)
            for e in self.entries:
                prop     = e.original_size / total_orig if total_orig > 0 else 0
                est_comp = int(self.tar_compressed_size * prop)
                ratio    = (1 - est_comp / e.original_size) * 100 if e.original_size > 0 else 0
                result.append((e.name, e.original_size, est_comp, ratio, e.crc32, e.md5))
        else:
            for e in self.entries:
                ratio = (1 - e.compressed_size / e.original_size) * 100 if e.original_size > 0 else 0
                result.append((e.name, e.original_size, e.compressed_size, ratio, e.crc32, e.md5))
        return result