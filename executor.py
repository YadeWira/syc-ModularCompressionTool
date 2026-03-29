"""
executor.py - Ejecuta compresores externos manejando todos los modos del .ini

Modos detectados automáticamente:
  - stdio puro:   <stdin> y <stdout>, sin $$arcdatafile$$
  - mixto:        <stdin> como entrada + $$arcpackedfile$$ como salida (ej: xprecomp)
  - tempfile puro: $$arcdatafile$$ y $$arcpackedfile$$, sin stdio

Notas Windows:
  - Las rutas con backslash se pasan como string a shell=True para evitar
    que shlex las rompa
  - Las rutas relativas del .ini se resuelven contra el CWD del proceso
"""

import os
import sys
import subprocess
import tempfile
import logging
import threading
import time


class ProgressMonitor:
    """
    Hilo que actualiza una línea de progreso mientras corre un compresor.
    Muestra: tiempo transcurrido + tamaño del archivo de salida (si existe).
    """

    def __init__(self, label: str, watch_file: str = None, expected_size: int = 0):
        self.label        = label         # Ej: "Comprimiendo tar (360.1 MB)"
        self.watch_file   = watch_file    # Ruta del archivo de salida a monitorear
        self.expected_size = expected_size # Tamaño esperado para calcular %
        self._stop        = threading.Event()
        self._thread      = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self._start = time.time()
        self._thread.start()
        time.sleep(0.05)  # dar tiempo al hilo para escribir la primera linea

    def stop(self):
        self._stop.set()
        self._thread.join(timeout=2)
        try:
            from syc import _progress as _gp
            if _gp.innosetup:
                return
        except Exception:
            pass
        sys.stdout.write("\n")
        sys.stdout.flush()

    def _fmt_time(self, seconds: float) -> str:
        s = int(seconds)
        return f"{s // 60:02d}:{s % 60:02d}"

    def _fmt_size(self, n: int) -> str:
        for unit in ["B", "KB", "MB", "GB"]:
            if n < 1024:
                return f"{n:.1f} {unit}"
            n /= 1024
        return f"{n:.1f} TB"

    def _run(self):
        # Verificar innosetup al inicio del hilo
        try:
            from syc import _progress as _gp
            if _gp.innosetup:
                return  # no escribir nada en modo innosetup
        except Exception:
            pass

        last_written = 0
        last_time    = time.time()
        first_tick   = True

        while not self._stop.is_set():
            now     = time.time()
            elapsed = now - self._start
            et      = self._fmt_time(elapsed)

            # Si label vacio: solo mostrar tiempo/progreso indentado
            if self.label:
                parts = [f"[INFO]   {self.label}", et]
            else:
                parts = [et]

            if self.watch_file:
                try:
                    written = os.path.getsize(self.watch_file)
                    if written > 0:
                        if self.expected_size > 0:
                            pct = min(99.9, written / self.expected_size * 100)
                            parts.append(
                                f"{self._fmt_size(written)} / {self._fmt_size(self.expected_size)}"
                                f" ({pct:.1f}%)"
                            )
                        else:
                            parts.append(f"{self._fmt_size(written)} written")

                        dt = now - last_time
                        if dt > 0.1 and written > last_written:
                            speed = (written - last_written) / dt
                            parts.append(f"{self._fmt_size(speed)}/s")

                        last_written = written
                        last_time    = now
                except OSError:
                    pass

            line = "  ".join(parts)
            try:
                from syc import _progress as _gp
                _innosetup = _gp.innosetup
            except Exception:
                _innosetup = False
            if not _innosetup:
                if self.label:
                    sys.stdout.write(f"\r[INFO] {line:<103}")
                else:
                    sys.stdout.write(f"\r[INFO]   {line:<101}")
                sys.stdout.flush()
            if first_tick:
                first_tick = False
                self._stop.wait(1.0)
            else:
                self._stop.wait(1.0)

def _log_compressor(line: str):
    """Escribe la salida de un compresor al log si está activo"""
    try:
        from syc import _log_write
        _log_write(f"  [compressor] {line.rstrip()}")
    except Exception:
        pass

from method import MethodStep, MethodChain, build_cmd
from ini_parser import CompressorDef
from typing import Dict


logger = logging.getLogger("syc.executor")

IS_WINDOWS = sys.platform == "win32"


class ExecutionError(Exception):
    pass


# ─── Detección de modo ────────────────────────────────────────────────────────

def _has_stdin(t: str) -> bool:
    return "<stdin>" in t

def _has_stdout(t: str) -> bool:
    return "<stdout>" in t

def _has_datafile(t: str) -> bool:
    return "$$arcdatafile$$" in t

def _has_packedfile(t: str) -> bool:
    return "$$arcpackedfile$$" in t

def _detect_mode(template: str) -> str:
    """
    Retorna el modo de ejecución:
      'stdio'   -> entrada y salida por pipes
      'mixed'   -> entrada por stdin, salida a archivo temporal
      'tempfile'-> entrada y salida por archivos temporales
    """
    stdin  = _has_stdin(template)
    stdout = _has_stdout(template)
    dpf    = _has_packedfile(template)
    ddf    = _has_datafile(template)

    if stdin and not dpf and not ddf:
        return "stdio"
    if stdin and dpf and not ddf:
        return "mixed"
    # Descompresión: archivo de entrada ($$arcpackedfile$$) + stdout como salida
    if dpf and stdout and not stdin and not ddf:
        return "reverse_mixed"
    return "tempfile"


# ─── Ejecución ───────────────────────────────────────────────────────────────

def _run_cmd(cmd: str, input_data: bytes = None, capture_stdout: bool = True,
             passthrough: bool = False, cwd: str = None) -> bytes:
    """
    Ejecuta un comando como string.
    passthrough=True (-vv): stderr and stdout (when not captured) go to console.
    passthrough=False: stderr and stdout are silently captured.
    stdout de datos siempre se captura si capture_stdout=True.
    """
    logger.debug(f"CMD: {cmd}")
    if passthrough:
        result = subprocess.run(
            cmd,
            input=input_data,
            stdout=subprocess.PIPE if capture_stdout else None,
            stderr=None,
            shell=IS_WINDOWS,
            cwd=cwd,
        )
    else:
        result = subprocess.run(
            cmd,
            input=input_data,
            stdout=subprocess.PIPE if capture_stdout else subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            shell=IS_WINDOWS,
            cwd=cwd,
        )
    if result.returncode != 0:
        raise ExecutionError(
            f"Compressor failed (exit {result.returncode}):\n"
            f"  CMD: {cmd}"
        )
    return result.stdout if capture_stdout else b""


def _run_stdio(cmd: str, input_data: bytes, passthrough: bool = False) -> bytes:
    """Entrada por stdin, salida por stdout"""
    clean = cmd.replace("<stdin>", "").replace("<stdout>", "").strip()
    return _run_cmd(clean, input_data=input_data, capture_stdout=True, passthrough=passthrough)


def _run_mixed(cmd: str, input_data: bytes, packedfile: str,
               passthrough: bool = False, monitor: "ProgressMonitor" = None) -> bytes:
    """Modo mixto: entrada por stdin, salida a archivo temporal."""
    clean = cmd.replace("<stdin>", "").replace("<stdout>", "").strip()
    if monitor:
        monitor.watch_file = packedfile
        monitor.start()
    try:
        _run_cmd(clean, input_data=input_data, capture_stdout=False, passthrough=passthrough)
    finally:
        if monitor:
            monitor.stop()

    if not os.path.exists(packedfile):
        raise ExecutionError(f"Mixed mode: compressor did not generate: {packedfile}")
    with open(packedfile, "rb") as f:
        return f.read()


def _run_reverse_mixed(cmd: str, input_data: bytes, packedfile: str,
                       passthrough: bool = False,
                       monitor: "ProgressMonitor" = None) -> bytes:
    """Modo reverse_mixed: escribe input a $$arcpackedfile$$, captura stdout como salida.
    Usado por xprecomp decode (lee archivo, escribe a stdout con -)."""
    # Guardar datos en packedfile temporal
    with open(packedfile, "wb") as f:
        f.write(input_data)

    clean = cmd.replace("<stdout>", "").replace("<stdin>", "").strip()
    # Reemplazar - al final si quedó como argumento de salida
    # xtool decode -t75p packed.tmp -   <- el '-' final es stdout

    if monitor:
        monitor.watch_file = packedfile
        monitor.start()
    try:
        result = _run_cmd(clean, input_data=None, capture_stdout=True,
                          passthrough=passthrough)
    finally:
        if monitor:
            monitor.stop()
    return result


def _run_tempfile(cmd: str, input_data: bytes, datafile: str, packedfile: str,
                  passthrough: bool = False, monitor: "ProgressMonitor" = None,
                  compress: bool = True) -> bytes:
    """Entrada y salida por archivos temporales.
    compress=True:  input->datafile,  ejecuta, lee packedfile
    compress=False: input->packedfile, ejecuta, lee datafile  (ej: zpaqfranz x)
    """
    tmpdir = os.path.dirname(datafile)

    if compress:
        # Comprimir: escribir datos de entrada al datafile
        with open(datafile, "wb") as f:
            f.write(input_data)
    else:
        # Descomprimir: escribir datos de entrada al packedfile (ej: packed.zpaq)
        with open(packedfile, "wb") as f:
            f.write(input_data)

    # Para compresores que extraen al CWD (ej: zpaqfranz sin $$arcdatafile$$),
    # resolver la ruta del ejecutable a absoluta y usar cwd=tmpdir
    use_cwd = (not compress
               and "$$arcdatafile$$" not in cmd
               and datafile not in cmd)

    run_cmd = cmd
    run_cwd = None
    if use_cwd:
        # Convertir el ejecutable a ruta absoluta para que cwd no lo rompa
        # El ejecutable es el primer token del comando
        import shlex as _shlex
        tokens = cmd.split()
        exe = tokens[0]
        abs_exe = os.path.abspath(exe)
        if os.path.exists(abs_exe):
            run_cmd = abs_exe + cmd[len(exe):]
        run_cwd = tmpdir

    if monitor:
        monitor.watch_file = packedfile if compress else datafile
        monitor.start()
    try:
        _run_cmd(run_cmd, input_data=None, capture_stdout=False,
                 passthrough=passthrough, cwd=run_cwd)
    finally:
        if monitor:
            monitor.stop()

    if compress:
        if not os.path.exists(packedfile):
            raise ExecutionError(f"Tempfile compress: not generated: {packedfile}")
        with open(packedfile, "rb") as f:
            return f.read()
    else:
        # Buscar el archivo de salida — algunos compresores (zpaqfranz)
        # extraen a subdirectorios en vez del CWD directamente
        target_name = os.path.basename(datafile)
        if os.path.exists(datafile):
            # Caso ideal: está en el lugar esperado
            with open(datafile, "rb") as f:
                return f.read()
        # Buscar recursivamente en tmpdir
        for root, dirs, files in os.walk(tmpdir):
            for fname in files:
                if fname == target_name:
                    found = os.path.join(root, fname)
                    with open(found, "rb") as f:
                        return f.read()
        raise ExecutionError(
            f"Tempfile decompress: '{target_name}' not found in {tmpdir}"
        )

# ─── Executor ────────────────────────────────────────────────────────────────

class Executor:
    """
    Ejecuta una cadena de compresores (MethodChain) sobre datos en memoria.
    Detecta automáticamente el modo (stdio / mixto / tempfile) por compresor.
    """

    def __init__(self, compressors: Dict[str, CompressorDef], workdir: str = None,
                 passthrough: bool = False, show_progress: bool = False,
                 expected_size: int = 0):
        self.compressors   = compressors
        self.workdir       = workdir or tempfile.gettempdir()
        self.passthrough   = passthrough
        self.show_progress = show_progress
        self.expected_size = expected_size
        self.step_total      = 0    # total de pasos en la cadena
        self.step_done       = 0    # pasos completados
        self.global_progress = None # referencia a _Progress de syc.py

    def compress(self, chain: MethodChain, data: bytes) -> bytes:
        current = data
        for step in chain.steps:
            current = self._apply_step(step, current, compress=True)
        return current

    def decompress(self, chain: MethodChain, data: bytes) -> bytes:
        current = data
        for step in chain.reversed_steps():
            current = self._apply_step(step, current, compress=False)
        return current

    def compress_stream(self, chain: MethodChain,
                        input_path: str, workdir: str) -> str:
        """Comprime una cadena sin cargar datos a RAM.
        Lee y escribe sólo rutas de archivo entre pasos.
        Retorna la ruta del archivo final comprimido.
        El caller es responsable de limpiar workdir."""
        current_path = input_path
        for step in chain.steps:
            current_path = self._apply_step_file(step, current_path,
                                                  compress=True, workdir=workdir)
        return current_path

    def decompress_stream(self, chain: MethodChain,
                          input_path: str, workdir: str) -> str:
        """Descomprime una cadena sin cargar datos a RAM.
        Lee y escribe sólo rutas de archivo entre pasos.
        Retorna la ruta del archivo final descomprimido.
        El caller es responsable de limpiar workdir."""
        current_path = input_path
        for step in chain.reversed_steps():
            current_path = self._apply_step_file(step, current_path,
                                                  compress=False, workdir=workdir)
        return current_path

    def _apply_step(self, step: MethodStep, data: bytes, compress: bool) -> bytes:
        comp_def = self.compressors.get(step.compressor)
        if comp_def is None:
            raise ExecutionError(f"Compressor '{step.compressor}' not defined in .ini")

        template = comp_def.packcmd if compress else comp_def.unpackcmd
        if template is None:
            raise ExecutionError(
                f"Compressor '{step.compressor}' has no "
                f"{'packcmd' if compress else 'unpackcmd'} definido"
            )

        mode  = _detect_mode(template)
        arrow = "[+]" if compress else "[-]"
        use_monitor = self.show_progress and not self.passthrough and mode != "stdio"

        # stdio: log normal + ejecutar
        if mode == "stdio":
            _inno = getattr(self.global_progress, "innosetup", False)
            if not _inno:
                logger.info(f"{arrow} {step.raw} ({mode})")
            # Reportar inicio del paso (despues del log)
            if self.global_progress is not None:
                self.global_progress.step()
            cmd = build_cmd(template, step, datafile="", packedfile="",
                           extra_options=comp_def.default or "")
            result = _run_stdio(cmd, data, passthrough=self.passthrough)
            # Reportar fin del paso (siempre, independiente de show_progress)
            if self.global_progress is not None:
                self.global_progress.step()
            return result

        # tempfile / mixed: log primero, luego progreso
        _inno = getattr(self.global_progress, "innosetup", False)
        if not use_monitor:
            if not _inno:
                logger.info(f"{arrow} {step.raw} ({mode})")
        else:
            if not _inno:
                sys.stdout.write(f"[INFO] {arrow} {step.raw} ({mode})\n")
                sys.stdout.flush()

        # Reportar inicio del paso (despues del log)
        if self.global_progress is not None:
            self.global_progress.step()

        with tempfile.TemporaryDirectory(dir=self.workdir) as tmpdir:
            datafile   = os.path.join(tmpdir, "data.tmp")
            packedfile = os.path.join(tmpdir, "packed.tmp")

            if comp_def.packedfile:
                packedfile = os.path.join(tmpdir, os.path.basename(
                    comp_def.packedfile.replace("$$arcpackedfile$$", "packed")))
            if comp_def.datafile:
                datafile = os.path.join(tmpdir, os.path.basename(
                    comp_def.datafile.replace("$$arcdatafile$$", "data")))

            cmd = build_cmd(template, step, datafile, packedfile,
                           extra_options=comp_def.default or "")

            monitor = None
            if use_monitor:
                monitor = ProgressMonitor(
                    label="",  # solo tiempo y progreso, sin repetir nombre
                    watch_file=None,
                    expected_size=self.expected_size,
                )

            if mode == "mixed":
                result = _run_mixed(cmd, data, packedfile,
                                    passthrough=self.passthrough, monitor=monitor)
            elif mode == "reverse_mixed":
                result = _run_reverse_mixed(cmd, data, packedfile,
                                            passthrough=self.passthrough, monitor=monitor)
            else:
                result = _run_tempfile(cmd, data, datafile, packedfile,
                                       passthrough=self.passthrough, monitor=monitor,
                                       compress=compress)

            # Actualizar progreso global (siempre, independiente del monitor)
            if self.global_progress is not None:
                self.global_progress.step()

            return result

    def _apply_step_file(self, step: MethodStep, input_path: str,
                         compress: bool, workdir: str) -> str:
        """Como _apply_step pero entrada/salida son rutas de archivo.
        Nunca carga el contenido completo en RAM.
        Retorna la ruta del archivo de salida."""
        comp_def = self.compressors.get(step.compressor)
        if comp_def is None:
            raise ExecutionError(f"Compressor '{step.compressor}' not defined in .ini")

        template = comp_def.packcmd if compress else comp_def.unpackcmd
        if template is None:
            raise ExecutionError(
                f"Compressor '{step.compressor}' has no "
                f"{'packcmd' if compress else 'unpackcmd'} definido"
            )

        mode  = _detect_mode(template)
        arrow = "[+]" if compress else "[-]"
        use_monitor = self.show_progress and not self.passthrough and mode != "stdio"

        # Logging + progress (mismo patrón que _apply_step)
        _inno = getattr(self.global_progress, "innosetup", False)
        if use_monitor:
            if not _inno:
                sys.stdout.write(f"[INFO] {arrow} {step.raw} ({mode})\n")
                sys.stdout.flush()
        else:
            if not _inno:
                logger.info(f"{arrow} {step.raw} ({mode})")
        if self.global_progress is not None:
            self.global_progress.step()

        # Construir nombres de archivo de trabajo en el workdir del caller
        import uuid as _uuid
        uid = _uuid.uuid4().hex[:8]

        # Determinar extensiones esperadas por el compresor
        def _ext(tpl_key, default):
            val = getattr(comp_def, tpl_key, None)
            if val:
                base = val.replace("$$arcpackedfile$$", "").replace("$$arcdatafile$$", "")
                if base.startswith("."):
                    return base
            return default

        packed_ext = _ext("packedfile", ".tmp")
        data_ext   = _ext("datafile",   ".tmp")

        # Use a per-step subdirectory with FIXED filenames (data.tmp / packed.ext)
        # This is critical for compressors like zpaqfranz that store the filename
        # internally — decompression must find exactly "data.tmp", not "data_UID.tmp"
        step_dir = os.path.join(workdir, uid)
        os.makedirs(step_dir, exist_ok=True)
        datafile   = os.path.join(step_dir, f"data{data_ext}")
        packedfile = os.path.join(step_dir, f"packed{packed_ext}")

        # Reusar el archivo de entrada del paso anterior directamente
        # según el modo de cada compresor
        if mode in ("tempfile",):
            if not compress:
                # input_path = comprimido → usar como packedfile
                # no copiar: renombrar (mismo disco, O(1))
                if input_path != packedfile:
                    os.replace(input_path, packedfile)
            else:
                if input_path != datafile:
                    os.replace(input_path, datafile)
        elif mode in ("mixed", "reverse_mixed"):
            if input_path != packedfile:
                os.replace(input_path, packedfile)

        cmd = build_cmd(template, step, datafile, packedfile,
                        extra_options=comp_def.default or "")

        monitor = None
        if use_monitor:
            monitor = ProgressMonitor(
                label="",
                watch_file=None,
                expected_size=self.expected_size,
            )

        # ── Ejecución ──
        if mode == "stdio":
            # stdio: leer del archivo de entrada, capturar stdout → escribir a archivo
            with open(input_path, "rb") as fh:
                in_data = fh.read()
            try:
                os.remove(input_path)
            except OSError:
                pass
            clean = cmd.replace("<stdin>", "").replace("<stdout>", "").strip()
            out_data = _run_cmd(clean, input_data=in_data,
                                capture_stdout=True, passthrough=self.passthrough)
            with open(datafile, "wb") as fh:
                fh.write(out_data)
            out_path = datafile

        elif mode == "mixed":
            # entrada stdin (leer archivo), salida → packedfile
            with open(packedfile, "rb") as fh:
                in_data = fh.read()
            try:
                os.remove(packedfile)
            except OSError:
                pass
            clean = cmd.replace("<stdin>", "").replace("<stdout>", "").strip()
            out_data = _run_cmd(clean, input_data=in_data,
                                capture_stdout=False, passthrough=self.passthrough)
            # resultado queda en el packedfile generado por el proceso
            # rebuscar igual que _run_mixed
            if not os.path.exists(packedfile):
                raise ExecutionError(f"Mixed file-mode: compressor did not generate {packedfile}")
            out_path = packedfile

        elif mode == "reverse_mixed":
            # entrada → packedfile (ya movido), salida stdout → datafile
            clean = cmd.replace("<stdin>", "").replace("<stdout>", "").strip()
            # Ajustar $$arcpackedfile$$ en cmd para apuntar al archivo ya en su lugar
            from method import build_cmd as _bc
            cmd2 = _bc(template, step, datafile, packedfile,
                       extra_options=comp_def.default or "")
            cmd2 = cmd2.replace("<stdout>", "").replace("<stdin>", "").strip()
            if monitor:
                monitor.watch_file = packedfile
                monitor.start()
            try:
                result = _run_cmd(cmd2, input_data=None,
                                  capture_stdout=True, passthrough=self.passthrough)
            finally:
                if monitor:
                    monitor.stop()
            try:
                os.remove(packedfile)
            except OSError:
                pass
            with open(datafile, "wb") as fh:
                fh.write(result)
            out_path = datafile

        else:  # tempfile
            use_cwd = (not compress
                       and "$$arcdatafile$$" not in template
                       and datafile not in cmd)
            run_cwd = None
            run_cmd = cmd
            if use_cwd:
                tokens = cmd.split()
                exe = tokens[0]
                abs_exe = os.path.abspath(exe)
                if os.path.exists(abs_exe):
                    run_cmd = abs_exe + cmd[len(exe):]
                run_cwd = step_dir  # use step_dir so zpaqfranz extracts here

            if monitor:
                monitor.watch_file = packedfile if compress else datafile
                monitor.start()
            try:
                _run_cmd(run_cmd, input_data=None,
                         capture_stdout=False, passthrough=self.passthrough,
                         cwd=run_cwd)
            finally:
                if monitor:
                    monitor.stop()

            # Limpiar el archivo de entrada (ya no necesario)
            in_to_del = datafile if compress else packedfile
            try:
                if os.path.exists(in_to_del):
                    os.remove(in_to_del)
            except OSError:
                pass

            out_path_candidate = packedfile if compress else datafile
            if os.path.exists(out_path_candidate):
                out_path = out_path_candidate
            else:
                # Fallback search — some compressors extract to a subdir of step_dir
                target_name = os.path.basename(out_path_candidate)
                found = None
                for root, dirs, files in os.walk(step_dir):
                    for fname in files:
                        if fname == target_name:
                            found = os.path.join(root, fname)
                            break
                    if found:
                        break
                # If still not found, pick any file that is not the packed input
                if not found:
                    packed_name = os.path.basename(packedfile)
                    for root, dirs, files in os.walk(step_dir):
                        for fname in files:
                            if fname != packed_name:
                                found = os.path.join(root, fname)
                                break
                        if found:
                            break
                if not found:
                    raise ExecutionError(
                        f"File-chain: '{target_name}' not found in {step_dir}")
                # Move to expected path for next step
                if found != out_path_candidate:
                    try:
                        os.replace(found, out_path_candidate)
                        found = out_path_candidate
                    except OSError:
                        pass
                out_path = found

        if self.global_progress is not None:
            self.global_progress.step()

        return out_path