"""
chunk.py - Manejo de archivos multi-parte (.syc con chunks)

Nomenclatura: data??.syc -> data01.syc, data02.syc, ...
El '??' en el nombre se reemplaza por el número de parte con ceros a la izquierda.

Formato de cada parte:
  Modo normal: cada parte es un .syc válido con su propio subconjunto de archivos.
  Modo tar:    la primera parte lleva el header completo + índice + fragmento de datos.
               Las partes 2..N llevan solo el fragmento de datos con un mini-header.

Mini-header para partes tar 2..N:
  [4 bytes]  Magic: b'SYCp'   (p = part)
  [4 bytes]  Número de parte (uint32 LE, base 1)
  [4 bytes]  Total de partes (uint32 LE)
  [M bytes]  Fragmento de datos
"""

import os
import re
import glob
import struct
from typing import List


MAGIC_PART = b'SYCp'


def _parse_chunk_size(s: str) -> int:
    """Convierte '4MB', '700KB', '1GB' a bytes"""
    s = s.strip().upper()
    m = re.match(r'^(\d+(?:\.\d+)?)\s*(KB|MB|GB|B)?$', s)
    if not m:
        raise ValueError(f"Invalid chunk size: {s!r}. Use e.g. 4MB, 700KB, 1GB")
    n = float(m.group(1))
    unit = m.group(2) or 'B'
    multipliers = {'B': 1, 'KB': 1024, 'MB': 1024**2, 'GB': 1024**3}
    return int(n * multipliers[unit])


def _resolve_pattern(pattern: str, part: int, total: int) -> str:
    """
    Reemplaza '??' por el número de parte con ceros.
    La cantidad de '?' define el ancho del número.
    data??.syc, part=1, total=9  -> data01.syc
    data???.syc, part=1, total=99 -> data001.syc
    """
    q_match = re.search(r'\?+', pattern)
    if not q_match:
        # Sin wildcard — agregar número antes de la extensión
        base, ext = os.path.splitext(pattern)
        width = len(str(total))
        return f"{base}{str(part).zfill(width)}{ext}"
    width = len(q_match.group())
    return pattern[:q_match.start()] + str(part).zfill(width) + pattern[q_match.end():]


def _glob_parts(pattern: str) -> List[str]:
    """Busca todos los archivos que coincidan con el patrón ?? y los ordena"""
    q_match = re.search(r'\?+', pattern)
    if not q_match:
        return sorted(glob.glob(pattern))
    glob_pattern = pattern[:q_match.start()] + '*' + pattern[q_match.end():]
    # Filtrar solo los que tengan exactamente dígitos donde van los '?'
    width = len(q_match.group())
    regex = re.escape(pattern[:q_match.start()]) + r'(\d{' + str(width) + r'})' + re.escape(pattern[q_match.end():])
    matches = []
    for f in glob.glob(glob_pattern):
        if re.fullmatch(regex, os.path.basename(f)) or re.fullmatch(regex, f):
            matches.append(f)
    return sorted(matches)


def split_normal(archives_data: List[tuple], pattern: str, chunk_size: int) -> List[str]:
    """
    Divide archivos comprimidos en chunks de tamaño máximo.
    archives_data: lista de (nombre, orig_size, compressed_bytes)
    Devuelve lista de rutas creadas.
    """
    from archive import SycArchive

    parts = []
    current_entries = []
    current_size = 0

    def _flush(part_num, entries, total_hint):
        path = _resolve_pattern(pattern, part_num, total_hint)
        arc = SycArchive.__new__(SycArchive)
        arc.method = entries[0][3]  # method guardado en tupla
        arc.tar_mode = False
        arc.entries = []
        arc.tar_original_size = 0
        arc.tar_compressed_size = 0
        arc.tar_data = b""
        for name, orig_size, comp_data, _ in entries:
            arc.add_entry(name=name, original_size=orig_size, compressed_data=comp_data)
        arc.write(path)
        return path

    # Primera pasada: agrupar en chunks
    chunks = []
    cur = []
    cur_size = 0
    for item in archives_data:
        name, orig_size, comp_data, method = item
        item_size = len(comp_data)
        if cur and cur_size + item_size > chunk_size:
            chunks.append(cur)
            cur = []
            cur_size = 0
        cur.append(item)
        cur_size += item_size
    if cur:
        chunks.append(cur)

    total = len(chunks)
    paths = []
    for i, chunk in enumerate(chunks, 1):
        path = _resolve_pattern(pattern, i, total)
        arc = SycArchive(method=chunk[0][3], tar_mode=False)
        for name, orig_size, comp_data, _ in chunk:
            arc.add_entry(name=name, original_size=orig_size, compressed_data=comp_data)
        arc.write(path)
        paths.append(path)
    return paths


def split_tar(archive, pattern: str, chunk_size: int) -> List[str]:
    """
    Divide el bloque tar comprimido en partes.
    La parte 1 lleva el header completo + índice + primer fragmento.
    Las partes 2..N llevan mini-header + fragmento.
    """
    from archive import SycArchive

    data = archive.tar_data
    total_size = len(data)

    # Calcular cuánto espacio queda en la parte 1 para datos
    # (el header con índice puede ser grande, lo calculamos primero)
    import io, struct as st
    buf = io.BytesIO()
    # Simular escritura del header para medir su tamaño
    from archive import FLAG_TAR
    method_bytes = archive.method.encode("utf-8")
    header_size = (
        4 +  # MAGIC
        1 +  # flags
        2 + len(method_bytes) +  # method
        4 +  # num_files
        sum(2 + len(e.name.encode()) + 8 + 8 for e in archive.entries) +  # entries
        8 + 8  # tar_original_size + tar_compressed_size
    )

    # Tamaño de datos en parte 1
    part1_data_size = max(0, chunk_size - header_size)
    if part1_data_size <= 0:
        part1_data_size = chunk_size  # si el header ya es más grande, igual dividimos

    # Dividir datos en fragmentos
    fragments = []
    fragments.append(data[:part1_data_size])
    remaining = data[part1_data_size:]
    while remaining:
        # Partes 2..N: mini-header (12 bytes) + datos
        frag_size = chunk_size - 12
        fragments.append(remaining[:frag_size])
        remaining = remaining[frag_size:]

    total_parts = len(fragments)
    paths = []

    for i, frag in enumerate(fragments, 1):
        path = _resolve_pattern(pattern, i, total_parts)
        if i == 1:
            # Parte 1: .syc completo con índice, tar_compressed_size = total
            arc = SycArchive(method=archive.method, tar_mode=True)
            arc.entries = archive.entries
            arc.tar_original_size   = archive.tar_original_size
            arc.tar_compressed_size = archive.tar_compressed_size  # tamaño total real
            arc.tar_data = frag
            # Override write para guardar solo el fragmento (no el bloque completo)
            _write_tar_part1(arc, path, frag, archive.tar_compressed_size, archive.tar_original_size, total_parts)
        else:
            # Partes 2..N: mini-header + fragmento
            with open(path, "wb") as f:
                f.write(MAGIC_PART)
                f.write(struct.pack("<I", i))
                f.write(struct.pack("<I", total_parts))
                f.write(frag)
        paths.append(path)

    return paths


def _write_tar_part1(archive, path: str, frag: bytes,
                     total_comp_size: int, total_orig_size: int, total_parts: int):
    """Escribe la parte 1 del tar con header completo pero solo el fragmento de datos"""
    from archive import FLAG_TAR, MAGIC
    with open(path, "wb") as f:
        f.write(MAGIC)
        f.write(struct.pack("<B", FLAG_TAR))
        method_bytes = archive.method.encode("utf-8")
        f.write(struct.pack("<H", len(method_bytes)))
        f.write(method_bytes)
        f.write(struct.pack("<I", len(archive.entries)))
        for entry in archive.entries:
            name_bytes = entry.name.encode("utf-8")
            f.write(struct.pack("<H", len(name_bytes)))
            f.write(name_bytes)
            f.write(struct.pack("<Q", entry.original_size))
            f.write(struct.pack("<Q", 0))
        # total_parts marker + tamaños reales + fragmento
        f.write(struct.pack("<I", total_parts))   # cuántas partes hay en total
        f.write(struct.pack("<Q", total_orig_size))
        f.write(struct.pack("<Q", total_comp_size))
        f.write(frag)


def read_tar_parts(pattern: str, password: str = None):
    """
    Lee y ensambla todas las partes de un archivo tar multi-parte.
    Devuelve un SycArchive con tar_data completo.
    """
    from archive import SycArchive, MAGIC, FLAG_TAR

    parts = _glob_parts(pattern)
    if not parts:
        raise FileNotFoundError(f"No parts found for: {pattern}")

    # Leer parte 1
    with open(parts[0], "rb") as f:
        magic = f.read(4)
        if magic != MAGIC:
            raise ValueError("Part 1 invalid: bad magic")
        flag = struct.unpack("<B", f.read(1))[0]
        if not (flag & FLAG_TAR):
            raise ValueError("Part 1 is not tar mode")
        method_len = struct.unpack("<H", f.read(2))[0]
        method = f.read(method_len).decode("utf-8")
        num_files = struct.unpack("<I", f.read(4))[0]

        archive = SycArchive(method=method, tar_mode=True)
        from archive import FileEntry
        for _ in range(num_files):
            name_len = struct.unpack("<H", f.read(2))[0]
            name = f.read(name_len).decode("utf-8")
            orig_size = struct.unpack("<Q", f.read(8))[0]
            f.read(8)  # compressed_size placeholder (0)
            archive.entries.append(FileEntry(name=name, original_size=orig_size))

        total_parts = struct.unpack("<I", f.read(4))[0]
        archive.tar_original_size   = struct.unpack("<Q", f.read(8))[0]
        archive.tar_compressed_size = struct.unpack("<Q", f.read(8))[0]
        frag1 = f.read()

    if len(parts) != total_parts:
        raise ValueError(f"Expected {total_parts} parts, found {len(parts)}")

    # Leer partes 2..N
    fragments = [frag1]
    for part_path in parts[1:]:
        with open(part_path, "rb") as f:
            magic = f.read(4)
            if magic != MAGIC_PART:
                raise ValueError(f"Invalid part: {part_path}")
            part_num   = struct.unpack("<I", f.read(4))[0]
            total_p    = struct.unpack("<I", f.read(4))[0]
            fragments.append(f.read())

    # Write assembled tar to a temp file to avoid double-copy in RAM.
    # The caller (cmd_extract) uses decompress_stream which reads from file,
    # so we store the path instead of bytes when possible.
    import tempfile as _tf
    tmp = _tf.NamedTemporaryFile(delete=False, suffix=".tar", prefix="syc_assemble_")
    try:
        for frag in fragments:
            tmp.write(frag)
        tmp.flush()
        tmp.seek(0)
        archive.tar_data = tmp.read()  # still needed for compatibility
    finally:
        tmp.close()
        try:
            os.remove(tmp.name)
        except OSError:
            pass
    return archive


def read_normal_parts(pattern: str, password: str = None) -> list:
    """
    Lee todas las partes de un archivo normal multi-parte.
    Devuelve lista de SycArchive (uno por parte).
    """
    from archive import SycArchive
    parts = _glob_parts(pattern)
    if not parts:
        raise FileNotFoundError(f"No parts found for: {pattern}")
    return [SycArchive.read(p, password=password) for p in parts]


def parse_chunk_size(s: str) -> int:
    return _parse_chunk_size(s)

def glob_parts(pattern: str) -> List[str]:
    return _glob_parts(pattern)

def is_multipart_pattern(s: str) -> bool:
    return '?' in s


def peek_tar_mode(path: str) -> bool:
    """
    Lee solo el flag del header sin cargar los datos.
    Seguro para usar con partes de archivos multi-parte.
    """
    from archive import MAGIC, FLAG_TAR
    with open(path, "rb") as f:
        magic = f.read(4)
        if magic != MAGIC:
            return False
        flag = struct.unpack("<B", f.read(1))[0]
        return bool(flag & FLAG_TAR)