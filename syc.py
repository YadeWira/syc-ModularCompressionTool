"""
syc.py - CLI principal de SYC
"""

import argparse
import fnmatch
import hashlib
import io
import logging
import os
import shutil
import sys
import tarfile
import tempfile
import time

# Force UTF-8 on stdout/stderr for CJK and special filenames
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() not in ("utf-8", "utf8"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from ini_parser import SycIniParser
from method import MethodChain
from executor import Executor, ExecutionError
from archive import SycArchive, compute_crc32, compute_md5
from crypto import encrypt, decrypt, alg_name as crypto_alg_name
from chunk import (parse_chunk_size, split_normal, split_tar,
                   read_tar_parts, read_normal_parts,
                   is_multipart_pattern, glob_parts, peek_tar_mode)

# ─── Logging ─────────────────────────────────────────────────────────────────
# Logger va a stdout (mismo stream que monitor)
_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
logging.root.handlers = []
logging.root.addHandler(_handler)
logging.root.setLevel(logging.INFO)

logger      = logging.getLogger("syc")
step_logger = logging.getLogger("syc.executor")

# ─── Helpers ─────────────────────────────────────────────────────────────────

def _fmt_size(n: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"

def _out(msg: str):
    _log_write(f"[INFO] {msg}")
    if _progress.innosetup:
        return
    sys.stdout.write(f"[INFO] {msg}\n")
    sys.stdout.flush()

def _live(msg: str):
    if _progress.innosetup:
        return
    sys.stdout.write(f"\r[INFO] {msg:<78}")
    sys.stdout.flush()

def _live_commit(msg: str):
    _log_write(f"[INFO] {msg}")
    if _progress.innosetup:
        return
    sys.stdout.write(f"\r[INFO] {msg:<78}\n")
    sys.stdout.flush()

# ─── Log ─────────────────────────────────────────────────────────────────────

_log_file = None  # File object, set by _init_log()

def _init_log(archive_path: str, log_arg):
    """
    Inicializa el archivo de log.
    log_arg: True = auto (archive.log), str = ruta específica
    """
    global _log_file
    if log_arg is None or log_arg is False:
        return
    if log_arg is True or log_arg == "":
        log_path = archive_path + ".log"
    else:
        log_path = log_arg
    _log_file = open(log_path, "w", encoding="utf-8", buffering=1)
    _log_write(f"SYC log - {' '.join(sys.argv)}")
    _log_write(f"Start: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    _log_write("-" * 60)
    _out(f"Log: {log_path}")

def _log_write(msg: str):
    """Write a log line with timestamp"""
    if _log_file is None:
        return
    import datetime
    ts = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
    _log_file.write(f"[{ts}] {msg}\n")

def _close_log():
    global _log_file
    if _log_file:
        import datetime
        _log_write("-" * 60)
        _log_write(f"End: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        _log_file.close()
        _log_file = None


def _load_ini(cfg_paths):
    parser = SycIniParser()
    loaded = []
    for path in cfg_paths:
        if os.path.exists(path):
            parser.parse_file(path)
            loaded.append(path)
    if not loaded:
        _out("WARN: No .ini config file found")
    else:
        _out(f"Config loaded from: {', '.join(loaded)}")
    return parser

def _visual_width(s: str) -> int:
    """Calcula el ancho visual de un string contando CJK y otros wide chars como 2 columnas"""
    width = 0
    for c in s:
        cp = ord(c)
        # Rangos de caracteres "wide" (doble ancho en terminal)
        if (0x1100 <= cp <= 0x115F or  # Hangul Jamo
            0x2E80 <= cp <= 0x303E or  # CJK Radicals, Kangxi
            0x3040 <= cp <= 0x33FF or  # Japanese (Hiragana, Katakana, etc.)
            0x3400 <= cp <= 0x4DBF or  # CJK Unified Ext A
            0x4E00 <= cp <= 0x9FFF or  # CJK Unified Ideographs
            0xA000 <= cp <= 0xA4CF or  # Yi
            0xAC00 <= cp <= 0xD7AF or  # Hangul Syllables
            0xF900 <= cp <= 0xFAFF or  # CJK Compatibility Ideographs
            0xFE10 <= cp <= 0xFE1F or  # Vertical Forms
            0xFE30 <= cp <= 0xFE6F or  # CJK Compatibility Forms
            0xFF01 <= cp <= 0xFF60 or  # Fullwidth Forms
            0xFFE0 <= cp <= 0xFFE6 or  # Fullwidth Signs
            0x20000 <= cp <= 0x2FFFD or # CJK Ext B-F
            0x30000 <= cp <= 0x3FFFD):  # CJK Ext G+
            width += 2
        else:
            width += 1
    return width


def _fit_name(name: str, max_width: int) -> str:
    """Trunca el nombre para que su ancho visual no supere max_width"""
    if _visual_width(name) <= max_width:
        return name
    # Truncar por la izquierda mostrando el final (más informativo)
    result = ""
    prefix = "…"
    budget = max_width - _visual_width(prefix)
    # Tomar chars desde el final hasta llenar el budget
    chars = list(name)
    taken = []
    for c in reversed(chars):
        w = 2 if _visual_width(c) == 2 else 1
        if budget - w < 0:
            break
        taken.append(c)
        budget -= w
    return prefix + "".join(reversed(taken))


def _pad_name(name: str, width: int) -> str:
    """Igual que f'{name:<width}' pero respetando el ancho visual CJK"""
    vw = _visual_width(name)
    padding = max(0, width - vw)
    return name + " " * padding


# ─── Progreso global ─────────────────────────────────────────────────────────

class _Progress:
    """Contador de pasos para mostrar % global del proceso"""
    def __init__(self):
        self.total         = 0
        self.done          = 0
        self.innosetup     = False
        self.progress_file = None


    def setup(self, total: int):
        self.total = total
        self.done  = 0

    def step(self):
        """Avanza un paso y muestra el % actualizado"""
        if self.total == 0:
            return
        self.done += 1
        pct = (self.done / self.total) * 100
        if self.innosetup:
            line = f"{pct:.1f}\n"
            sys.stdout.write(line)
            sys.stdout.flush()
            if self.progress_file:
                try:
                    with open(self.progress_file, "w") as _pf:
                        _pf.write(line)
                except Exception:
                    pass
        else:
            sys.stdout.write(f"\r[INFO] {pct:.1f}%{' ' * 70}\n")
            sys.stdout.flush()

_progress = _Progress()


def _fmt_elapsed(seconds: float) -> str:
    """Formatea tiempo transcurrido: segundos si < 60s, minutos si >= 60s"""
    if seconds < 60:
        return f"{seconds:.2f} sec"
    return f"{seconds/60:.2f} min"


def _verbose_level(args) -> int:
    """0=normal, 1=-v, 2=-vv"""
    if getattr(args, "vv", False): return 2
    if getattr(args, "verbose", False): return 1
    return 0

def _collect_files(file_args):
    """
    Devuelve lista de (filepath, base) donde:
      base = directorio a usar como raiz para calcular arcnames
      - TESTC      -> base = padre de TESTC  (preserva TESTC/ en el arcname)
      - TESTC/*   -> base = TESTC           (elimina TESTC/ del arcname)
      - archivo.txt -> base = directorio del archivo
    """
    import glob
    results = []  # lista de (filepath, base)
    for arg in file_args:
        if '*' in arg or ('?' in arg and not arg.endswith('.syc')):
            # Wildcard: base es el directorio del patron
            base = os.path.abspath(os.path.dirname(arg))
            matches = glob.glob(arg, recursive=True)
            if not matches:
                _out(f"WARN: Not found: {arg}")
            for match in sorted(matches):
                if os.path.isdir(match):
                    for root, _, fnames in os.walk(match):
                        for fname in fnames:
                            results.append((os.path.join(root, fname), base))
                elif os.path.isfile(match):
                    results.append((match, base))
        elif os.path.isdir(arg):
            # Directorio sin wildcard: base es el PADRE del directorio
            # para que el directorio mismo quede en el arcname
            base = os.path.abspath(os.path.join(arg, '..'))
            for root, _, fnames in os.walk(arg):
                for fname in fnames:
                    results.append((os.path.join(root, fname), base))
        elif os.path.isfile(arg):
            base = os.path.abspath(os.path.dirname(arg))
            results.append((arg, base))
        else:
            _out(f"WARN: Not found: {arg}")
    return results

# ─── Tar helpers ─────────────────────────────────────────────────────────────

def _arcname(filepath: str, base: str) -> str:
    """Calcula el arcname relativo a base.
    Siempre usa forward slashes para compatibilidad con tarfile en Windows."""
    rel = os.path.relpath(os.path.abspath(filepath), base)
    return rel.replace("\\", "/")



def _build_tar_disk(file_pairs: list, tmpdir: str) -> str:
    """Empaqueta los files en un tar en disco. file_pairs = [(filepath, base), ...]"""
    tar_path = os.path.join(tmpdir, "syc_solid.tar")
    with tarfile.open(tar_path, mode="w") as tar:
        for filepath, base in file_pairs:
            tar.add(filepath, arcname=_arcname(filepath, base))
    return tar_path


def _extract_tar(tar_bytes: bytes, outdir: str):
    """Extrae un tar desde bytes al directorio de salida"""
    buf = io.BytesIO(tar_bytes)
    with tarfile.open(fileobj=buf, mode="r") as tar:
        # filter="data" only exists in Python 3.12+
        try:
            tar.extractall(path=outdir, filter="data")
        except TypeError:
            tar.extractall(path=outdir)


def _extract_tar_file(tar_path: str, outdir: str) -> int:
    """Extrae un tar desde un archivo en disco (sin cargarlo en RAM).
    Retorna el número de archivos extraídos."""
    os.makedirs(outdir, exist_ok=True)
    with tarfile.open(tar_path, mode="r") as tar:
        members = tar.getmembers()
        try:
            tar.extractall(path=outdir, filter="data")
        except TypeError:
            tar.extractall(path=outdir)
    return len([m for m in members if m.isfile()])

# ─── Help ────────────────────────────────────────────────────────────────────

def _print_help():
    import platform, struct
    # CPU cores/threads
    try:
        import psutil
        cores   = psutil.cpu_count(logical=False) or 1
        threads = psutil.cpu_count(logical=True)  or 1
        ram_gb  = psutil.virtual_memory().total / (1024**3)
        cpu_str = f"CPU: {cores}C/{threads}T"
        ram_str = f"RAM: {ram_gb:.1f} GB"
    except Exception:
        import os
        threads = os.cpu_count() or 1
        cpu_str = f"CPU: {threads}T"
        ram_str = ""
    arch = "x64" if struct.calcsize("P")*8 == 64 else "x86"
    header = f"SYC v0.2.0 {arch} | by Yade Bravo (YadeWira) | {cpu_str}"
    if ram_str: header += f" | {ram_str}"
    print(header)
    print("""SYC - Modular compression tool with external compressors
Usage: syc <command> [options]

Commands:
  a    Add / compress files
  x    Extract files (preserving folder structure)
  e    Extract files flat (no folder structure)
  l    List contents (compact)
  ls   List contents PowerShell-style, with optional folder filter
  t    Verify integrity
  m    List all compression methods from syc.ini

Compression options (a):
  -m METHOD          Compression method (alias from .ini or direct chain)
  -cfg FILE          Config file (default: syc.ini)
  -v                 Verbose: show file name and ratio
  -vv                Extra verbose: show compressor output in real time

Solid mode:
  -tar               Pack everything into tar before compressing (better ratio)
  -block SIZE        Split into independent blocks (e.g. 512MB, 1GB)
                     Works with or without -tar. Each block compressed separately.
  -dd [CHUNK_SIZE]   Deduplication: deduplicate content at chunk level before compressing
                     Default chunk size: 4MB. Example: -dd 8MB
                     Combine with -block for low-RAM compression of dedup'd data
  -tmpr              Tar temp file in RAM
  -tmpd [PATH]       Tar temp file on disk (default if -tmpr not specified)

Multi-part:
  -chunk SIZE        Split into parts (e.g. 4MB, 700KB, 1GB)
                     Requires '??' in archive name: "backup??.syc"

Hashes:
  --crc32            Calculate and store CRC32 per file
  --md5              Calculate and store MD5 per file
  --comment "TEXT"   Add a text comment to the archive

Encryption:
  -key PASSWORD      Encrypt with password (AES-256 by default)
  -ks ALGORITHM      AES256 (default) or CC20 (ChaCha20)
  --full-encrypted   Encrypt header too (hides file names)

Compression filters (a):
  -x PATTERN         Exclude files matching PATTERN (repeatable)
  -n PATTERN         Include only files matching PATTERN (repeatable)
                     Both support wildcards: -x "*.tmp" -x "*.log"

Extraction options (x / e):
  -o PATH            Output directory (default: current directory)
  -f  PATTERN        Extract matching files, flat output (no folder structure)
  -ff PATTERN        Extract matching files, preserving full path
                     Both support: exact name, wildcards (*), folder prefix (folder/)
                     Both are repeatable: -f file1.exe -f file2.exe
  -ow MODE           Overwrite existing files: + always (default), - skip, p prompt
  -y                 Answer yes to all prompts (same as -ow +)

InnoSetup:
  --innosetup        Silent mode: only output % to stdout
  --innosetup FILE   Same, also write % to FILE in real time

Log:
  --log              Save log to archive.syc.log (auto name)
  --log FILE         Save log to specific path

Examples:
  syc m
  syc m -cfg myconfig.ini
  syc ls backup.syc
  syc ls backup.syc compressors\
  syc a backup.syc folder -m xpszx
  syc a backup.syc folder -m xpszx -v
  syc a backup.syc folder -m xpszx -tar
  syc a backup.syc folder -m xpszx -block 512MB
  syc a backup.syc folder -m xpszx -dd
  syc a backup.syc folder -m xpszx -dd 8MB -block 256MB
  syc a backup.syc folder -m xpszx -tar -tmpd D:/tmp
  syc a backup.syc folder -m xpszx --comment "My backup"
  syc a backup.syc folder -m xpszx --md5 --crc32
  syc a backup.syc folder -m xpszx -key MyPass -ks CC20
  syc a backup.syc folder -m xpszx -key P --full-encrypted
  syc a "back??.syc" folder -m xpszx -chunk 700MB
  syc x backup.syc -o dest
  syc x backup.syc -o dest -key MyPass
  syc x backup.syc -o dest -f "file.exe"
  syc x backup.syc -o dest -ff "folder\file.exe"
  syc x backup.syc -o dest -f "*.exe" -f "*.dll"
  syc x "back??.syc" -o dest
  syc l backup.syc
  syc l backup.syc -key MyPass""")


# ─── Comandos ────────────────────────────────────────────────────────────────

def cmd_methods(args):
    """Lists all [Compression methods] from the .ini with resolved chains"""
    ini = _load_ini(getattr(args, "cfg", ["syc.ini"]))
    methods = ini.list_methods()
    if not methods:
        _out("No methods found in config.")
        return
    max_len = max(len(m) for m in methods)
    _out(f"Methods defined in config ({len(methods)} total):")
    _out("")
    for alias in methods:
        resolved = ini.resolve_method(alias)
        if resolved != alias:
            _out(f"  {alias:<{max_len}}  ->  {resolved}")
        else:
            _out(f"  {alias}")
    _out("")


# ─── Deduplication helpers ───────────────────────────────────────────────────

def _analyze_duplicates(files: list, out_fn) -> dict:
    """
    Fase 1: escanea todos los archivos y detecta duplicados exactos (file-level).
    Retorna un dict: sha256_hex → [arcname, ...] para cada grupo con >1 archivo.
    También imprime el reporte via out_fn.
    """
    import hashlib
    file_hashes: dict = {}  # sha256_hex → [(filepath, arcname)]

    out_fn(f"  Analyzing {len(files)} files...")
    _BUF = 8 * 1024 * 1024  # 8 MB read buffer
    for filepath, base in files:
        arcname = _arcname(filepath, base)
        h = hashlib.sha256()
        with open(filepath, "rb") as fh:
            while True:
                buf = fh.read(_BUF)
                if not buf:
                    break
                h.update(buf)
        digest = h.hexdigest()
        if digest not in file_hashes:
            file_hashes[digest] = []
        file_hashes[digest].append((filepath, arcname))

    # Grupos con duplicados
    dup_groups = {h: entries for h, entries in file_hashes.items() if len(entries) > 1}
    unique_files = sum(1 for entries in file_hashes.values() if len(entries) == 1)
    dup_files    = sum(len(e) - 1 for e in dup_groups.values())  # archivos extra (redundantes)
    dup_size     = 0

    if dup_groups:
        out_fn(f"  Found {len(dup_groups)} duplicate group(s)  ({dup_files} redundant file(s)):")
        for h, entries in dup_groups.items():
            names = [arc for _, arc in entries]
            sz = os.path.getsize(entries[0][0])
            saved = sz * (len(entries) - 1)
            dup_size += saved
            out_fn(f"    [{_fmt_size(sz)} x{len(entries)}]  {names[0]}")
            for name in names[1:]:
                out_fn(f"      = {name}")
        out_fn(f"  File-level dedup saves: {_fmt_size(dup_size)}")
    else:
        out_fn(f"  No exact duplicate files found  ({unique_files} unique)")

    return dup_groups


def _dedup_files(files: list, chunk_size: int):
    """
    Fase 2: deduplicación a nivel de chunks sobre todos los archivos.
    Retorna:
      dedup_index: [(arcname, orig_size, [chunk_ids])]
      unique_chunks: list[bytes]  — chunks únicos en orden de primera aparición
    """
    import hashlib
    chunk_map: dict = {}      # sha256 digest → chunk_id
    unique_chunks: list = []

    dedup_index = []
    for filepath, base in files:
        arcname   = _arcname(filepath, base)
        orig_size = os.path.getsize(filepath)
        chunk_ids = []
        with open(filepath, "rb") as fh:
            while True:
                chunk = fh.read(chunk_size)
                if not chunk:
                    break
                h = hashlib.sha256(chunk).digest()
                if h not in chunk_map:
                    chunk_map[h] = len(unique_chunks)
                    unique_chunks.append(chunk)
                chunk_ids.append(chunk_map[h])
        dedup_index.append((arcname, orig_size, chunk_ids))
    return dedup_index, unique_chunks


def cmd_add(args):
    _cmd_start = time.time()
    _inno = getattr(args, "innosetup", None)
    if _inno is not None:
        _progress.innosetup     = True
        _progress.progress_file = _inno if isinstance(_inno, str) else None
        logging.getLogger("syc.executor").setLevel(logging.WARNING)
        logging.getLogger("syc").setLevel(logging.WARNING)
    _init_log(args.archive, getattr(args, "log", None))
    ini = _load_ini(args.cfg)
    # Resolver workdir para files temporales del executor
    if args.tmpr:
        workdir = None  # RAM no aplica al executor, usar tempdir del sistema
    elif args.tmpd is not None:
        workdir = args.tmpd if args.tmpd else None
    else:
        workdir = None
    executor = Executor(ini.compressors, workdir=workdir,
                        passthrough=(_verbose_level(args) >= 2))

    method_name = args.method
    if method_name in ini.methods:
        chain_str = ini.resolve_method(method_name)
        _out(f"Method '{method_name}' -> {chain_str}")
    else:
        chain_str = method_name
        _out(f"Direct method: {chain_str}")

    chain = MethodChain.parse(chain_str)

    files = _collect_files(args.files)
    if not files:
        _out("ERROR: No files to compress")
        sys.exit(1)

    # Apply -x (exclude) and -n (include-only) filters
    excl = [p.replace("\\", "/") for p in (getattr(args, "x", None) or [])]
    incl = [p.replace("\\", "/") for p in (getattr(args, "n", None) or [])]
    if excl or incl:
        def _filt(pair):
            rel = _arcname(pair[0], pair[1]).replace("\\", "/")
            base = rel.split("/")[-1]
            if excl:
                for pat in excl:
                    if fnmatch.fnmatch(rel, pat) or fnmatch.fnmatch(base, pat):
                        return False
            if incl:
                for pat in incl:
                    if fnmatch.fnmatch(rel, pat) or fnmatch.fnmatch(base, pat):
                        return True
                return False
            return True
        before = len(files)
        files = [f for f in files if _filt(f)]
        _out(f"  Filter: {before} -> {len(files)} files")
    if not files:
        _out("ERROR: No files left after filtering")
        sys.exit(1)

    # -block sin -tar → solid implícito (mini-tar por bloque)
    if getattr(args, "block", None) and not args.tar and not getattr(args, "dd", None):
        args.tar = True
        _out(f"  Note: -block implies solid mode (-tar)")

    # ── Modo Deduplicación ───────────────────────────────────────────────────
    if getattr(args, "dd", None):
        from archive import FLAG_DEDUP
        _cmd_start_dd = time.time()
        dd_chunk_size = parse_chunk_size(args.dd)
        block_size    = parse_chunk_size(args.block) if getattr(args, "block", None) else 0

        if args.tar:
            _out("[WARN] -tar is ignored in -dd mode (chunk store is already solid)")

        total_orig = sum(os.path.getsize(f) for f, _ in files)
        _out(f"Dedup mode: {len(files)} files ({_fmt_size(total_orig)})  chunk={_fmt_size(dd_chunk_size)}")

        # Pre-estimar número de bloques para calcular steps totales
        # Usa tamaño total para estimar — el chunk store siempre es <= total_orig
        _pre_num_groups = max(1, int(total_orig / block_size)) if block_size > 0 else 1

        # Setup de progreso: 1(ini) + 1(fase1) + 1(fase2) + B*(N*2) + 1(write)
        _progress.setup(1 + 1 + 1 + _pre_num_groups * len(chain.steps) * 2 + 1)
        _progress.step()  # ini

        # ── Fase 1: análisis de duplicados a nivel de archivo ────────────────
        _out("")
        _out("  [Phase 1/2] File-level duplicate analysis:")
        dup_groups = _analyze_duplicates(files, _out)
        _progress.step()  # fase 1 completada

        # ── Fase 2: deduplicación a nivel de chunks ───────────────────────────
        _out("")
        _out("  [Phase 2/2] Chunk-level deduplication:")
        dedup_index, unique_chunks = _dedup_files(files, dd_chunk_size)
        _progress.step()  # fase 2 completada
        total_chunks  = len(unique_chunks)
        dedup_orig    = sum(len(c) for c in unique_chunks)
        saved         = total_orig - dedup_orig
        saved_pct     = (saved / total_orig * 100) if total_orig else 0
        _out(f"  {total_chunks} unique chunks  ({_fmt_size(dedup_orig)} deduplicated / "
             f"{_fmt_size(total_orig)} original  {saved_pct:.1f}% savings)")
        _out("")

        # Paso 2: agrupar chunks en bloques (o un solo blob)
        if block_size > 0:
            # Agrupar chunks hasta block_size bytes de datos originales
            chunk_groups = []
            cur_group    = []
            cur_sz       = 0
            for chunk in unique_chunks:
                if cur_group and cur_sz + len(chunk) > block_size:
                    chunk_groups.append(cur_group)
                    cur_group = []
                    cur_sz    = 0
                cur_group.append(chunk)
                cur_sz += len(chunk)
            if cur_group:
                chunk_groups.append(cur_group)
            _out(f"  Block mode: {len(chunk_groups)} block(s) of ~{_fmt_size(block_size)}")
        else:
            chunk_groups = [unique_chunks]  # un solo blob

        # Paso 3: comprimir cada grupo
        # (progreso ya configurado arriba con estimacion de bloques)
        executor.global_progress = _progress
        executor.show_progress   = (_verbose_level(args) < 2) and not _progress.innosetup
        executor.step_total      = len(chain.steps)
        step_logger.setLevel(logging.INFO)

        archive = SycArchive(method=method_name,
                             enc_key=args.key, enc_alg=args.ks,
                             full_encrypted=args.full_encrypted)
        archive.dedup_mode = True
        if getattr(args, "comment", None):
            archive.comment = args.comment

        # Poblar entries con chunk_ids
        for arcname, orig_size, chunk_ids in dedup_index:
            archive.add_entry(name=arcname, original_size=orig_size)
            archive.entries[-1].chunk_ids = chunk_ids
        _compress_start = time.time()
        total_comp = 0
        chunk_offset = 0  # offset global de chunk IDs en el store

        for bi, group in enumerate(chunk_groups, 1):
            group_orig = sum(len(c) for c in group)
            blob       = archive._serialize_chunk_blob(group)
            _out(f"  Block {bi}/{len(chunk_groups)}: {len(group)} chunks ({_fmt_size(group_orig)})")
            executor.step_done = 0
            try:
                comp_data = executor.compress(chain, blob)
            except ExecutionError as e:
                _out(f"ERROR block {bi}: {e}")
                sys.exit(1)
            ratio = (1 - len(comp_data) / group_orig) * 100 if group_orig else 0
            _out(f"    {_fmt_size(group_orig)} -> {_fmt_size(len(comp_data))} ({ratio:.1f}%)")
            archive.dedup_blobs.append((len(group), group_orig, comp_data))
            total_comp += len(comp_data)

        elapsed = time.time() - _compress_start
        s = int(elapsed)
        avg_speed = dedup_orig / elapsed if elapsed > 0 else 0
        _live_commit(
            f"  {_fmt_size(dedup_orig)} -> {_fmt_size(total_comp)} "
            f"({(1 - total_comp/dedup_orig)*100:.1f}% compression)  "
            f"{s//60:02d}:{s%60:02d}  avg {_fmt_size(avg_speed)}/s"
        )

        archive.write(args.archive)
        _progress.step()
        _out("")
        _out(f"Archive created: {args.archive}")
        _out(f"Total: {_fmt_size(total_orig)} -> {_fmt_size(total_comp)} "
             f"(dedup {saved_pct:.1f}% + compress {(1-total_comp/dedup_orig)*100:.1f}%)")
        _out(f"Elapsed time: {_fmt_elapsed(time.time()-_cmd_start)}")
        _close_log()
        return

    # ── Modo TAR sólido ──────────────────────────────────────────────────────
    if args.tar:
        # Setup progreso global: ini(1) + tar(1) + compresores(N*2 inicio+fin) + write/split(1)
        # ── Pre-group for block mode to know total steps ──────────────────────
        block_size = parse_chunk_size(args.block) if getattr(args, "block", None) else 0
        if block_size > 0:
            _pre_blocks = []
            _cur_grp = []; _cur_sz = 0
            for fp, base in files:
                fsz = os.path.getsize(fp)
                if _cur_grp and _cur_sz + fsz > block_size:
                    _pre_blocks.append(_cur_grp); _cur_grp = []; _cur_sz = 0
                _cur_grp.append((fp, base)); _cur_sz += fsz
            if _cur_grp: _pre_blocks.append(_cur_grp)
            num_blocks = len(_pre_blocks)
            # steps: 1(ini) + 1(agrupacion) + B*(1_tar + N*2_compress) + 1(write)
            _progress.setup(1 + 1 + num_blocks * (1 + len(chain.steps) * 2) + 1)
        else:
            _progress.setup(1 + 1 + len(chain.steps) * 2 + 1)

        _progress.step()  # paso 1: ini cargado

        archive = SycArchive(method=method_name, tar_mode=True,
                             enc_key=args.key, enc_alg=args.ks,
                             full_encrypted=args.full_encrypted)
        total_orig = sum(os.path.getsize(f) for f, _ in files)

        _out(f"Solid mode (-tar): packing {len(files)} files ({_fmt_size(total_orig)})...")

        # Registrar metadatos de cada archivo en el índice
        for filepath, base in files:
            name = _arcname(filepath, base)
            if args.crc32 or args.md5:
                with open(filepath, "rb") as _f:
                    _fdata = _f.read()
                crc32 = compute_crc32(_fdata) if args.crc32 else None
                md5   = compute_md5(_fdata)   if args.md5   else None
            else:
                crc32 = md5 = None
            archive.add_entry(name=name, original_size=os.path.getsize(filepath),
                              crc32=crc32, md5=md5)

        # Construir tar
        step_logger.setLevel(logging.WARNING)
        tmpdir_used = args.tmpd if args.tmpd else tempfile.gettempdir()
        os.makedirs(tmpdir_used, exist_ok=True)

        if block_size > 0:
            _out(f"  Block mode: {_fmt_size(block_size)} per block")
            blocks_files = _pre_blocks  # reuse pre-grouped

            _out(f"  {len(blocks_files)} block(s) to compress")
            _progress.step()  # paso: agrupacion tar

            total_comp = 0
            _compress_start = time.time()
            step_logger.setLevel(logging.INFO)
            executor.show_progress = (_verbose_level(args) < 2) and not _progress.innosetup
            executor.step_total    = len(chain.steps)
            executor.global_progress = _progress

            for bi, group in enumerate(blocks_files, 1):
                grp_orig = sum(os.path.getsize(f) for f, _ in group)
                _out(f"  Block {bi}/{len(blocks_files)}: {len(group)} files ({_fmt_size(grp_orig)})")

                # Tar del bloque a disco, comprimir sin cargar a RAM
                tar_path = os.path.join(tmpdir_used, f"syc_block_{bi}.tar")
                with tarfile.open(tar_path, "w") as tar:
                    for fp, base in group:
                        tar.add(fp, arcname=_arcname(fp, base))
                tar_size = os.path.getsize(tar_path)
                _progress.step()  # paso: tar del bloque listo

                executor.step_done = 0
                executor.expected_size = 0
                blk_workdir = os.path.join(tmpdir_used, f"blk{bi}_work")
                os.makedirs(blk_workdir, exist_ok=True)
                try:
                    comp_path = executor.compress_stream(chain, tar_path, blk_workdir)
                    with open(comp_path, "rb") as _cf:
                        compressed = _cf.read()
                    os.remove(comp_path)
                except ExecutionError as e:
                    sys.stdout.write("\n")
                    _out(f"ERROR block {bi}: {e}")
                    sys.exit(1)
                finally:
                    shutil.rmtree(blk_workdir, ignore_errors=True)
                try:
                    os.remove(tar_path)
                except OSError:
                    pass

                ratio = (1 - len(compressed) / tar_size) * 100 if tar_size else 0
                _out(f"    {_fmt_size(tar_size)} -> {_fmt_size(len(compressed))} ({ratio:.1f}%)")
                archive.add_block(tar_size, compressed)
                total_comp += len(compressed)

            elapsed_total = time.time() - _compress_start
            s = int(elapsed_total)
            avg_speed = total_orig / elapsed_total if elapsed_total > 0 else 0
            _live_commit(
                f"  {_fmt_size(total_orig)} -> {_fmt_size(total_comp)} "
                f"({(1 - total_comp/total_orig)*100:.1f}% reduction)  "
                f"{s//60:02d}:{s%60:02d}  avg {_fmt_size(avg_speed)}/s"
            )

        else:
            # ── Modo normal: un solo tar ──────────────────────────────────────

            _out(f"  Packing to disk: {tmpdir_used}")
            tar_path = _build_tar_disk(files, tmpdir_used)
            tar_size = os.path.getsize(tar_path)
            _out(f"  Tar ready: {_fmt_size(tar_size)}")
            _progress.step()

            expected_comp = 0
            if os.path.exists(args.archive):
                expected_comp = os.path.getsize(args.archive)

            _out(f"  Compressing tar ({_fmt_size(tar_size)})...")
            step_logger.setLevel(logging.INFO)
            executor.show_progress   = (_verbose_level(args) < 2) and not _progress.innosetup
            executor.expected_size   = expected_comp
            executor.step_total      = len(chain.steps)
            executor.step_done       = 0
            executor.global_progress = _progress

            _compress_start = time.time()
            # compress_stream: tar nunca se carga a RAM, solo rutas entre pasos
            tar_workdir = os.path.join(tmpdir_used, "tar_compress_work")
            os.makedirs(tar_workdir, exist_ok=True)
            try:
                comp_path = executor.compress_stream(chain, tar_path, tar_workdir)
                with open(comp_path, "rb") as _cf:
                    compressed = _cf.read()
                os.remove(comp_path)
            except ExecutionError as e:
                sys.stdout.write("\n")
                _out(f"ERROR: {e}")
                sys.exit(1)
            finally:
                shutil.rmtree(tar_workdir, ignore_errors=True)
            try:
                os.remove(tar_path)
            except OSError:
                pass

            comp_size = len(compressed)
            ratio = (1 - comp_size / tar_size) * 100 if tar_size else 0
            elapsed_total = time.time() - _compress_start
            s = int(elapsed_total)
            avg_speed = tar_size / elapsed_total if elapsed_total > 0 else 0
            _live_commit(
                f"  {_fmt_size(tar_size)} -> {_fmt_size(comp_size)} "
                f"({ratio:.1f}% reduction)  "
                f"{s // 60:02d}:{s % 60:02d}  avg {_fmt_size(avg_speed)}/s"
            )

            # Build tar bytes for set_tar_block (only needed for final write, unavoidable)
            archive.set_tar_block_sizes(tar_size, compressed)

        if getattr(args, "comment", None):
            archive.comment = args.comment

        total_comp_size = sum(len(c) for _, c in archive.blocks) if archive.blocks else len(compressed)
        total_ratio = (1 - total_comp_size / total_orig) * 100 if total_orig > 0 else 0

        if args.chunk and is_multipart_pattern(args.archive):
            chunk_size = parse_chunk_size(args.chunk)
            _out(f"  Splitting into parts of {args.chunk}...")
            paths = split_tar(archive, args.archive, chunk_size)
            _out("")
            for p in paths:
                _out(f"  Part: {p}  ({_fmt_size(os.path.getsize(p))})")
            _out("")
            _progress.step()  # paso final: escritura/division
            _out(f"Total: {_fmt_size(total_orig)} -> {_fmt_size(total_comp_size)} ({total_ratio:.1f}% reduction)  [{len(paths)} parts]")
        else:
            archive.write(args.archive)
            _progress.step()  # paso final: escritura
            _out("")
            _out(f"Archive created: {args.archive}")
            _out(f"Total: {_fmt_size(total_orig)} -> {_fmt_size(total_comp_size)} ({total_ratio:.1f}% reduction)")
        _out(f"Elapsed time: {_fmt_elapsed(time.time()-_cmd_start)}")
        _close_log()
        return

    # ── Modo normal (un archivo a la vez) ────────────────────────────────────
    archive = SycArchive(method=method_name, tar_mode=False,
                         enc_key=args.key, enc_alg=args.ks,
                         full_encrypted=args.full_encrypted)
    if getattr(args, "comment", None):
        archive.comment = args.comment
    total_files = len(files)
    total_orig  = 0
    total_comp  = 0

    for i, (filepath, base) in enumerate(files, 1):
        with open(filepath, "rb") as f:
            data = f.read()
        orig_size = len(data)

        if args.verbose:
            _out(f"  Compressing: {filepath} ({_fmt_size(orig_size)})")

        step_logger.setLevel(logging.INFO if (args.verbose or i == 1) else logging.WARNING)

        try:
            compressed = executor.compress(chain, data)
        except ExecutionError as e:
            sys.stdout.write("\n")
            _out(f"ERROR: {e}")
            sys.exit(1)

        comp_size = len(compressed)
        ratio = (1 - comp_size / orig_size) * 100 if orig_size > 0 else 0

        if _verbose_level(args) >= 1:
            _out(f"    {_fmt_size(orig_size)} -> {_fmt_size(comp_size)} ({ratio:.1f}% reduction)")

        total_orig += orig_size
        total_comp += comp_size
        name  = _arcname(filepath, base)
        crc32 = compute_crc32(data) if args.crc32 else None
        md5   = compute_md5(data)   if args.md5   else None
        archive.add_entry(name=name, original_size=orig_size,
                          compressed_data=compressed, crc32=crc32, md5=md5)

        pct = (i / total_files) * 100
        total_ratio = (1 - total_comp / total_orig) * 100
        progress_msg = f"  Total Progress - {pct:.1f}%  [{i}/{total_files}]  {_fmt_size(total_orig)} -> {_fmt_size(total_comp)} ({total_ratio:.1f}%)"
        if _verbose_level(args) >= 1:
            _out(progress_msg)
        else:
            _live(progress_msg)

    if _verbose_level(args) == 0:
        _live_commit(f"  Total Progress - 100.0%  [{total_files}/{total_files}]  {_fmt_size(total_orig)} -> {_fmt_size(total_comp)}")

    total_ratio = (1 - total_comp / total_orig) * 100 if total_orig > 0 else 0

    if args.chunk and is_multipart_pattern(args.archive):
        chunk_size = parse_chunk_size(args.chunk)
        _out(f"  Splitting into parts of {args.chunk}...")
        paths = split_normal(
            [(e.name, e.original_size, e.data, method_name) for e in archive.entries],
            args.archive, chunk_size
        )
        _out("")
        for p in paths:
            _out(f"  Part: {p}  ({_fmt_size(os.path.getsize(p))})")
        _out("")
        _out(f"Total: {_fmt_size(total_orig)} -> {_fmt_size(total_comp)} ({total_ratio:.1f}% reduction)  [{len(paths)} parts]")
    else:
        archive.write(args.archive)
        _out("")
        _out(f"Archive created: {args.archive}")
        _out(f"Total: {_fmt_size(total_orig)} -> {_fmt_size(total_comp)} ({total_ratio:.1f}% reduction)")
    _out(f"Elapsed time: {_fmt_elapsed(time.time()-_cmd_start)}")
    _close_log()


def cmd_extract(args):
    _cmd_start = time.time()
    _inno = getattr(args, "innosetup", None)
    if _inno is not None:
        _progress.innosetup     = True
        _progress.progress_file = _inno if isinstance(_inno, str) else None
        logging.getLogger("syc.executor").setLevel(logging.WARNING)
        logging.getLogger("syc").setLevel(logging.WARNING)


    _init_log(args.archive, getattr(args, "log", None))
    ini = _load_ini(args.cfg)

    # Detectar si es multi-parte
    password = args.key if hasattr(args, "key") else None
    if is_multipart_pattern(args.archive):
        parts = glob_parts(args.archive)
        if not parts:
            _out(f"ERROR: No parts found for: {args.archive}")
            sys.exit(1)
        tar_mode = peek_tar_mode(parts[0])
        if tar_mode:
            _out(f"Multi-part tar: {len(parts)} parts found")
            archive = read_tar_parts(args.archive, password=password)
        else:
            _out(f"Multi-part normal: {len(parts)} parts found")
            archives = read_normal_parts(args.archive, password=password)
            for arc in archives:
                _do_extract_normal(arc, ini, args)
            _close_log()
            return
    else:
        try:
            archive = SycArchive.read(args.archive, password=password)
        except ValueError as e:
            _out(f"ERROR: {e}")
            sys.exit(1)

    dedup_str = "  [dedup]" if archive.dedup_mode else ""
    _out(f"Archive method: {archive.method}{'  [tar mode]' if archive.tar_mode else ''}{dedup_str}")

    method_name = archive.method
    chain_str = ini.resolve_method(method_name) if method_name in ini.methods else method_name
    chain = MethodChain.parse(chain_str)
    if args.tmpr:
        workdir = None
    elif args.tmpd is not None:
        workdir = args.tmpd if args.tmpd else None
    else:
        workdir = None
    executor = Executor(ini.compressors, workdir=workdir,
                        passthrough=(_verbose_level(args) >= 2))
    outdir = args.output or "."

    # ── Extracción modo dedup ────────────────────────────────────────────────
    if archive.dedup_mode:
        _cmd_start = time.time()
        _progress.setup(len(archive.dedup_blobs) * len(chain.steps) * 2 + 1 + 1)
        executor.global_progress = _progress
        executor.show_progress   = (_verbose_level(args) < 2) and not _progress.innosetup
        executor.step_total      = len(chain.steps)
        step_logger.setLevel(logging.INFO)

        num_blobs = len(archive.dedup_blobs)
        _out(f"  Decompressing {num_blobs} block(s)...")
        all_chunks = []
        for bi, (n_chunks, orig_size, comp_data) in enumerate(archive.dedup_blobs, 1):
            _out(f"  Block {bi}/{num_blobs}: {n_chunks} chunks ({_fmt_size(len(comp_data))} compressed)")
            executor.step_done = 0
            try:
                blob = executor.decompress(chain, comp_data)
            except ExecutionError as e:
                _out(f"ERROR block {bi}: {e}")
                sys.exit(1)
            block_chunks = SycArchive._parse_chunk_blob(blob)
            all_chunks.extend(block_chunks)
            _out(f"    -> {n_chunks} chunks ({_fmt_size(sum(len(c) for c in block_chunks))})")

        _out(f"  Reconstructing {len(archive.entries)} files...")
        os.makedirs(outdir, exist_ok=True)
        overwrite_mode = getattr(args, "overwrite", "+")
        extracted = 0
        skipped   = 0
        for entry in archive.entries:
            out_path = os.path.join(outdir, entry.name.replace("/", os.sep))
            if os.path.exists(out_path):
                if overwrite_mode == "-":
                    skipped += 1
                    continue
                elif overwrite_mode == "p":
                    ans = input(f"  Overwrite {entry.name}? [y/N] ").strip().lower()
                    if ans != "y":
                        skipped += 1
                        continue
            os.makedirs(os.path.dirname(out_path), exist_ok=True) if os.path.dirname(out_path) else None
            with open(out_path, "wb") as fh:
                for cid in entry.chunk_ids:
                    fh.write(all_chunks[cid])
            extracted += 1
        _progress.step()
        _out(f"  Extracted {extracted} files ({skipped} skipped) to: {outdir}")
        _out(f"Elapsed time: {_fmt_elapsed(time.time()-_cmd_start)}")
        _close_log()
        return

    # ── Extracción modo tar ──────────────────────────────────────────────────
    if archive.tar_mode:
        if getattr(args, "f", None) or getattr(args, "ff", None):
            _out("ERROR: -f/-ff filter is not supported in tar mode.")
            _out("       Tar archives must be fully decompressed before filtering.")
            _out("       Extract without -f/-ff, then pick the files you need.")
            sys.exit(1)

        multiblock = bool(archive.blocks)

        if multiblock:
            num_blocks = len(archive.blocks)
            # steps: B*(N*2_decomp) + 1(extract)
            _progress.setup(num_blocks * len(chain.steps) * 2 + 1)
        else:
            _progress.setup(len(chain.steps) * 2 + 1)

        executor.global_progress = _progress
        executor.show_progress = (_verbose_level(args) < 2) and not _progress.innosetup
        executor.step_total = len(chain.steps)
        step_logger.setLevel(logging.INFO)

        if multiblock:
            _out(f"  Decompressing {num_blocks} blocks ({_fmt_size(archive.tar_compressed_size)})...")
            total_decomp = 0
            total_files  = 0
            # workdir persistente para el file-chain (se limpia al final)
            block_workdir = tempfile.mkdtemp(prefix="syc_blk_")
            try:
                for bi, (orig_size, comp_data) in enumerate(archive.blocks, 1):
                    _out(f"  Block {bi}/{num_blocks}: {_fmt_size(len(comp_data))} compressed")
                    executor.step_done = 0
                    # Escribir bloque comprimido a disco (no RAM)
                    packed_path = os.path.join(block_workdir, f"blk{bi}_packed.tmp")
                    with open(packed_path, "wb") as fh:
                        fh.write(comp_data)
                    del comp_data  # liberar inmediatamente
                    try:
                        tar_path = executor.decompress_stream(chain, packed_path, block_workdir)
                    except ExecutionError as e:
                        _out(f"ERROR block {bi}: {e}")
                        sys.exit(1)
                    fsize = os.path.getsize(tar_path)
                    total_decomp += fsize
                    _out(f"    -> {_fmt_size(fsize)}")
                    # Extraer tar directamente del archivo — sin cargarlo a RAM
                    nf = _extract_tar_file(tar_path, outdir)
                    total_files += nf
                    os.remove(tar_path)  # liberar espacio inmediatamente
            finally:
                shutil.rmtree(block_workdir, ignore_errors=True)
            _out(f"  Total decompressed: {_fmt_size(total_decomp)}")
            _progress.step()  # paso final
            _out(f"  Extracted {total_files} files to: {outdir}")
        else:
            _out(f"  Decompressing tar block ({_fmt_size(archive.tar_compressed_size)})...")
            executor.step_done = 0
            try:
                tar_bytes = executor.decompress(chain, archive.tar_data)
            except ExecutionError as e:
                _out(f"ERROR: {e}")
                sys.exit(1)
            _out(f"  Extracting {len(archive.entries)} files to: {outdir}")
            _extract_tar(tar_bytes, outdir)
            _progress.step()  # paso final: extraccion completada
            _out(f"  {_fmt_size(archive.tar_compressed_size)} -> {_fmt_size(len(tar_bytes))}")
        _out("")
        _out(f"Extraction complete in: {outdir}")
        _out(f"Elapsed time: {_fmt_elapsed(time.time()-_cmd_start)}")
        _close_log()
        return

    # ── Extracción modo normal ───────────────────────────────────────────────
    _do_extract_normal(archive, ini, args, _cmd_start)


def _matches_filter(name: str, filters: list) -> bool:
    """Check if a file name matches any of the -f filters.
    Supports exact match, wildcard (*), and folder prefix (ends with /)
    """
    import fnmatch
    if not filters:
        return True
    norm = name.replace("\\", "/")
    for f in filters:
        fn = f.replace("\\", "/")
        # Folder prefix: -f compressors/
        if fn.endswith("/"):
            if norm.startswith(fn) or norm + "/" == fn:
                return True
        # Wildcard
        elif "*" in fn or "?" in fn:
            if fnmatch.fnmatch(norm, fn) or fnmatch.fnmatch(norm.split("/")[-1], fn):
                return True
        # Exact match — try full path and basename
        else:
            basename = norm.split("/")[-1]
            if norm.lower() == fn.lower():
                return True
            # Also match against basename alone (e.g. -f "file.json" matches "folder/file.json")
            if "/" not in fn and basename.lower() == fn.lower():
                return True
    return False


def _do_extract_normal(archive, ini, args, cmd_start: float = None):
    method_name = archive.method
    chain_str = ini.resolve_method(method_name) if method_name in ini.methods else method_name
    chain = MethodChain.parse(chain_str)
    if args.tmpr:
        workdir = None
    elif args.tmpd is not None:
        workdir = args.tmpd if args.tmpd else None
    else:
        workdir = None
    executor = Executor(ini.compressors, workdir=workdir,
                        passthrough=(_verbose_level(args) >= 2))
    outdir = args.output or "."

    # Apply -f (flat) or -ff (full path) filters
    filters_flat = [f.replace("\\","/") for f in (getattr(args,"f",None) or [])]
    filters_full = [f.replace("\\","/") for f in (getattr(args,"ff",None) or [])]
    all_filters  = filters_flat + filters_full
    flat_mode    = bool(filters_flat) and not filters_full

    if all_filters:
        entries_to_extract = [e for e in archive.entries
                              if _matches_filter(e.name, all_filters)]
    else:
        entries_to_extract = list(archive.entries)

    if all_filters and not entries_to_extract:
        _out("ERROR: No files matched the specified filter(s).")
        sys.exit(1)

    if all_filters:
        tag = "flat" if flat_mode else "full path"
        _out("  Filter ({}): {}  ({}/{} files)".format(
            tag, ", ".join(all_filters), len(entries_to_extract), len(archive.entries)))

    total_files = len(entries_to_extract)
    for i, entry in enumerate(entries_to_extract, 1):
        if flat_mode:
            out_path = os.path.join(outdir, os.path.basename(entry.name))
        else:
            out_path = os.path.join(outdir, entry.name)
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

        vlevel = _verbose_level(args)
        if vlevel >= 1:
            _out(f"  Extracting: {entry.name} ({_fmt_size(entry.compressed_size)})")

        step_logger.setLevel(logging.INFO if (vlevel >= 1 or i == 1) else logging.WARNING)

        try:
            data = executor.decompress(chain, entry.data)
        except ExecutionError as e:
            sys.stdout.write("\n")
            _out(f"ERROR: {e}")
            sys.exit(1)

        # Overwrite check (-y forces always overwrite)
        ow = "+" if getattr(args, "yes", False) else getattr(args, "overwrite", "+")
        if os.path.exists(out_path) and ow != "+":
            if ow == "-":
                _out(f"  Skipping (exists): {entry.name}")
                continue
            elif ow == "p":
                ans = input(f"  Overwrite {out_path}? [y/N] ").strip().lower()
                if ans != "y":
                    _out(f"  Skipping: {entry.name}")
                    continue

        with open(out_path, "wb") as f:
            f.write(data)

        if _verbose_level(args) >= 1:
            _out(f"    -> {out_path} ({_fmt_size(len(data))})")

        pct = (i / total_files) * 100
        _live(f"  Total Progress - {pct:.1f}%  [{i}/{total_files}]")

    _live_commit(f"  Total Progress - 100.0%  [{total_files}/{total_files}]")
    _out("")
    _out(f"Extraction complete in: {outdir}")
    if cmd_start is not None:
        _out(f"Elapsed time: {_fmt_elapsed(time.time()-cmd_start)}")
    _close_log()


def cmd_list(args):
    _init_log(args.archive, getattr(args, "log", None))
    password = args.key if hasattr(args, "key") else None
    try:
        archive = SycArchive.read(args.archive, password=password)
    except ValueError as e:
        _out(f"ERROR: {e}")
        sys.exit(1)

    try:
        term_width = os.get_terminal_size().columns
    except OSError:
        term_width = 120
    term_width = max(80, term_width)

    mode_str = "dedup" if archive.dedup_mode else ("solid tar" if archive.tar_mode else "normal")
    enc_str  = ""
    if archive.full_encrypted: enc_str = "  [full-encrypted: " + (archive.enc_alg or "?") + "]"
    elif archive.enc_key: enc_str = "  [encrypted]"

    print(f"\nFile    : {args.archive}")
    print(f"Mode    : {mode_str}{enc_str}")
    print(f"Method  : {archive.method}")
    if archive.comment:
        print(f"Comment : {archive.comment}")
    print(f"Files   : {len(archive.entries)}")
    if archive.dedup_mode and archive.dedup_blobs:
        total_store_comp = sum(len(c) for _, _, c in archive.dedup_blobs)
        total_store_orig = sum(o for _, o, _ in archive.dedup_blobs)
        print(f"Store   : {_fmt_size(total_store_orig)} -> {_fmt_size(total_store_comp)}")
    elif archive.tar_mode and archive.tar_original_size:
        print(f"Block   : {_fmt_size(archive.tar_original_size)} -> {_fmt_size(archive.tar_compressed_size)}")
    print()

    has_crc = archive._has_crc32
    has_md5 = archive._has_md5

    # Columnas fijas: orig(10) comp(12) ratio(7) + separadores
    fixed = 1 + 10 + 1 + 12 + 1 + 7  # sep+orig sep+comp sep+ratio
    if has_crc: fixed += 1 + 10       # sep + CRC32 (8 hex chars + padding)
    if has_md5: fixed += 1 + 32       # sep + MD5 (32 hex)
    name_width = max(20, term_width - fixed)

    # Header — todo en una sola línea
    hdr  = _pad_name("Name", name_width)
    hdr += f" {'Original':>10} {'Compressed':>12} {'Ratio':>7}"
    if has_crc: hdr += f" {'CRC32':>10}"
    if has_md5: hdr += f" {'MD5':>32}"
    print(hdr)
    print("─" * term_width)

    total_orig = total_comp = 0
    for name, orig, comp, ratio, crc32, md5 in archive.list_entries():
        disp = _fit_name(name, name_width)
        row  = _pad_name(disp, name_width)
        row += f" {_fmt_size(orig):>10} {_fmt_size(comp):>12} {ratio:>6.1f}%"
        if has_crc: row += f" {crc32:>10X}" if crc32 is not None else f" {'-':>10}"
        if has_md5: row += f" {md5.hex()}"  if md5   else f" {'-':>32}"
        print(row)
        total_orig += orig
        total_comp += comp

    print("─" * term_width)
    total_ratio = (1 - total_comp / total_orig) * 100 if total_orig > 0 else 0
    footer  = _pad_name("TOTAL", name_width)
    footer += f" {_fmt_size(total_orig):>10} {_fmt_size(total_comp):>12} {total_ratio:>6.1f}%"
    print(footer)
    if archive.dedup_mode:
        print("  * Compressed size estimated proportionally from chunk store")
    elif archive.tar_mode:
        print("  * Compressed size estimated proportionally from tar block")
    print()


def cmd_ls(args):
    password = args.key if hasattr(args, "key") else None
    try:
        archive = SycArchive.read(args.archive, password=password)
    except ValueError as e:
        _out("ERROR: " + str(e))
        sys.exit(1)

    def _norm(p):
        return p.replace("\\", "/")

    folder = _norm(args.folder).rstrip("/") if (hasattr(args, "folder") and args.folder) else ""

    entries = archive.list_entries()
    all_paths = [_norm(e[0]) for e in entries]

    if folder:
        prefix = folder + "/"
        items = []
        for i, e in enumerate(entries):
            p = all_paths[i]
            if p.startswith(prefix):
                rel = p[len(prefix):]
                items.append((rel, e[1], e[2], e[3], e[4], e[5]))
        if not items:
            print("  No entries found matching: " + folder + "\\")
            return
        header = args.archive + "  [" + folder + "\\]"
    else:
        items = [(e[0], e[1], e[2], e[3], e[4], e[5]) for e in entries]
        header = args.archive

    subdirs = set()
    files = []
    for name, orig, comp, ratio, crc32, md5 in items:
        n = _norm(name)
        parts = n.split("/")
        if len(parts) > 1:
            subdirs.add(parts[0])
        else:
            files.append((name, orig))

    all_sizes = [orig for _, orig, *_ in items]
    max_len = max((len("{:,}".format(s)) for s in all_sizes), default=6)
    max_len = max(max_len, 6)

    mode_str = "solid tar" if archive.tar_mode else "normal"
    print("")
    print("    Archive: " + header + "  [" + archive.method + " | " + mode_str + "]")
    if archive.comment:
        print("    Comment: " + archive.comment)
    print("")
    print("{:<6}  {:>{}}  {}".format("Mode", "Length", max_len, "Name"))
    print("{:<6}  {:>{}}  {}".format("----", "------", max_len, "----"))

    total_orig = 0

    for d in sorted(subdirs):
        print("{:<6}  {:>{}}  {}\\".format("d----", "", max_len, d))

    for name, orig, comp, ratio, crc32, md5 in sorted(items, key=lambda x: x[0].lower()):
        n = _norm(name)
        if "/" not in n:
            size_str = "{:,}".format(orig)
            print("{:<6}  {:>{}}  {}".format("-a---", size_str, max_len, name))
            total_orig += orig

    print("")
    nf_direct = len([e for e in items if "/" not in _norm(e[0])])
    nf_total  = len(items)
    nd = len(subdirs)
    total_all = sum(e[1] for e in items)  # todos los archivos incluyendo subcarpetas
    parts = []
    if nd: parts.append("{} {}".format(nd, "directories" if nd != 1 else "directory"))
    parts.append("{} {}".format(nf_total, "files" if nf_total != 1 else "file"))
    parts.append(_fmt_size(total_all) + " original")
    if archive.tar_mode and archive.tar_compressed_size:
        parts.append(_fmt_size(archive.tar_compressed_size) + " compressed")
    print("    " + "    ".join(parts))
    print("")



def cmd_test(args):
    try:
        archive = SycArchive.read(args.archive)
        mode = "tar" if archive.tar_mode else "normal"
        print(f"OK: {args.archive} — {len(archive.entries)} file(s), method: {archive.method}, mode: {mode}")
    except Exception as e:
        _out(f"ERROR: Invalid archive: {e}")
        sys.exit(1)

# ─── CLI ─────────────────────────────────────────────────────────────────────

def main():
    # Mostrar help propio antes de que argparse haga nada
    if len(sys.argv) == 1 or sys.argv[1] in ("-h", "--help", "/?"):
        _print_help()
        sys.exit(0)

    parser = argparse.ArgumentParser(prog="syc", add_help=False)
    subparsers = parser.add_subparsers(dest="command")

    p_add = subparsers.add_parser("a", add_help=False)
    p_add.add_argument("archive")
    p_add.add_argument("files", nargs="+")
    p_add.add_argument("-m", "--method", default=None, metavar="METHOD",
                       help="Compression method (required)")
    p_add.add_argument("-cfg", nargs="+", default=["syc.ini"])
    p_add.add_argument("-v", "--verbose", action="store_true")
    p_add.add_argument("-vv", action="store_true")
    p_add.add_argument("-tar", action="store_true")
    p_add.add_argument("-tmpr", action="store_true")
    p_add.add_argument("-tmpd", nargs="?", const="", default=None, metavar="RUTA")
    p_add.add_argument("-chunk", default=None, metavar="TAMANO")
    p_add.add_argument("-dd", nargs="?", const="4MB", default=None, metavar="CHUNK_SIZE",
                       help="Deduplication: default 4MB chunks")
    p_add.add_argument("-block", default=None, metavar="SIZE",
                       help="Split tar into independent blocks (e.g. 512MB). Requires -tar.")

    p_add.add_argument("-key", default=None, metavar="PASSWORD")
    p_add.add_argument("-ks", default="AES256", choices=["AES256", "CC20"])
    p_add.add_argument("--full-encrypted", action="store_true")
    p_add.add_argument("--crc32", action="store_true")
    p_add.add_argument("--md5", action="store_true")
    p_add.add_argument("-x", action="append", default=None, metavar="PATTERN",
                       help="Exclude files matching PATTERN (repeatable)")
    p_add.add_argument("-n", action="append", default=None, metavar="PATTERN",
                       help="Include only files matching PATTERN (repeatable)")
    p_add.add_argument("--comment", default=None, metavar="TEXT",
                       help="Add a comment to the archive")
    p_add.add_argument("--innosetup", nargs="?", const=True, default=None, metavar="FILE",
                       help="InnoSetup mode: only show %%, silence all [INFO] output")
    p_add.add_argument("--log", nargs="?", const=True, default=None,
                       metavar="ARCHIVO",
                       help="Guardar log (sin ARCHIVO = nombre_archivo.log)")



    p_ext = subparsers.add_parser("x", add_help=False)
    p_ext.add_argument("archive")
    p_ext.add_argument("-o", "--output", default=".")
    p_ext.add_argument("-cfg", nargs="+", default=["syc.ini"])
    p_ext.add_argument("-v", "--verbose", action="store_true")
    p_ext.add_argument("-vv", action="store_true")
    p_ext.add_argument("-tmpr", action="store_true")
    p_ext.add_argument("-tmpd", nargs="?", const="", default=None, metavar="RUTA")
    p_ext.add_argument("-key", default=None, metavar="PASSWORD")
    p_ext.add_argument("--overwrite", "-ow", default="+", choices=["+","-","p"],
                       metavar="MODE",
                       help="Overwrite mode: + always (default), - skip existing, p prompt")
    p_ext.add_argument("-f", action="append", default=None, metavar="PATTERN",
                       help="Extract matching files, flat (no folder structure)")
    p_ext.add_argument("-ff", action="append", default=None, metavar="PATTERN",
                       help="Extract matching files, preserving full path")
    p_ext.add_argument("-y", "--yes", action="store_true",
                       help="Answer yes to all prompts (same as --overwrite=+)")
    p_ext.add_argument("--innosetup", nargs="?", const=True, default=None, metavar="FILE")
    p_ext.add_argument("--log", nargs="?", const=True, default=None, metavar="ARCHIVO")


    p_e = subparsers.add_parser("e", add_help=False)
    p_e.add_argument("archive")
    p_e.add_argument("-o", "--output", default=".")
    p_e.add_argument("-cfg", nargs="+", default=["syc.ini"])
    p_e.add_argument("-v", "--verbose", action="store_true")
    p_e.add_argument("-vv", action="store_true")
    p_e.add_argument("-tmpr", action="store_true")
    p_e.add_argument("-tmpd", nargs="?", const="", default=None, metavar="RUTA")
    p_e.add_argument("-key", default=None, metavar="PASSWORD")
    p_e.add_argument("-f", action="append", default=None, metavar="PATTERN")
    p_e.add_argument("--overwrite", "-ow", default="+", choices=["+","-","p"], metavar="MODE")
    p_e.add_argument("-y", "--yes", action="store_true")
    p_e.add_argument("--innosetup", nargs="?", const=True, default=None, metavar="FILE")
    p_e.add_argument("--log", nargs="?", const=True, default=None, metavar="ARCHIVO")

    p_ls = subparsers.add_parser("ls", add_help=False)
    p_ls.add_argument("archive")
    p_ls.add_argument("folder", nargs="?", default="")
    p_ls.add_argument("-key", default=None, metavar="PASSWORD")

    p_m = subparsers.add_parser("m", add_help=False)
    p_m.add_argument("-cfg", nargs="+", default=["syc.ini"])

    p_list = subparsers.add_parser("l", add_help=False)
    p_list.add_argument("archive")
    p_list.add_argument("-key", default=None, metavar="PASSWORD")
    p_list.add_argument("--log", nargs="?", const=True, default=None, metavar="ARCHIVO")

    p_test = subparsers.add_parser("t", add_help=False)
    p_test.add_argument("archive")

    # Si el comando no es reconocido, mostrar help
    if sys.argv[1] not in ("a", "x", "e", "l", "ls", "t", "m"):
        _print_help()
        sys.exit(1)

    # Si el subcomando pide help
    if len(sys.argv) > 2 and sys.argv[2] in ("-h", "--help"):
        _print_help()
        sys.exit(0)

    args = parser.parse_args()

    if args.command is None:
        _print_help()
        sys.exit(0)

    # Si -tar activo y no se especificó ni -tmpr ni -tmpd, usar -tmpd por defecto
    if hasattr(args, "tar") and args.tar and not args.tmpr and args.tmpd is None:
        args.tmpd = ""

    if args.command == "a":
        cmd_add(args)
    elif args.command == "x":
        cmd_extract(args)
    elif args.command == "e":
        # e = extract flat (no folder structure) — force -f "*" in flat mode
        if not getattr(args, "f", None):
            args.f = ["*"]
        args.ff = None  # ensure flat mode
        cmd_extract(args)
    elif args.command == "l":
        cmd_list(args)
    elif args.command == "t":
        cmd_test(args)
    elif args.command == "ls":
        cmd_ls(args)
    elif args.command == "m":
        cmd_methods(args)


if __name__ == "__main__":
    try:
        main()
    except FileNotFoundError as e:
        _out(f"ERROR: File not found: {e.filename}")
        sys.exit(1)
    except PermissionError as e:
        _out(f"ERROR: No permissions to access: {e.filename}")
        sys.exit(1)
    except KeyboardInterrupt:
        sys.stdout.write("\n")
        _out("Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        _out(f"ERROR: {type(e).__name__}: {e}")
        sys.exit(1)