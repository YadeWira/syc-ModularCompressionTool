# SYC v0.0.3 — Changelog (fixes only)

## Bug Fixes

| Bug | Description | Fix |
|-----|-------------|-----|
| **Tar extraction on Windows (critical)** | `_arcname()` used `os.path.relpath()` which returns backslashes on Windows. `tarfile` stored paths like `folder\file.png` and only extracted the last file correctly — 25 files in → 1 file out | `_arcname()` now calls `.replace("\\", "/")` to always use forward slashes |
| **AES256 / ChaCha20 extract fails** | In normal (non-tar) mode, `write()` called `_serialize_index()` which stored plain compressed data, but `_parse_index_stream()` tried to `decrypt()` it — causing decryption failure on every read | `write()` now encrypts each entry's data individually when `FLAG_ENC` is set, and stores the encrypted size |
| **`list encrypted` exit 1** | Same root cause as above — `l` command failed reading encrypted normal archives | Fixed by the encryption write fix above |
| **`-f` exact match fails** | `-f "nato_simple.json"` failed to match entries stored as `nato/nato_simple.json` — only full path comparison was done | `_matches_filter()` now also compares against the basename when the filter contains no `/` |
| **`-ff` exact match fails** | Same root cause as `-f` exact match | Same fix |
| **Multiple `-f` fails** | Same root cause as `-f` exact match | Same fix |
| **Multi-part normal extract crashes** | `from recovery import find_rr_files, check_and_recover` imported a module that was never implemented, causing `ModuleNotFoundError` on every multi-part extraction | Removed the recovery import block entirely (feature planned for future release) |
| **Multi-part tar extract also affected** | Same `recovery` import also present in tar multi-part path | Removed |
| **Round-trip count mismatch in test** | `test.bat` used `dir /b` (non-recursive) for input count but `dir /b /s` (recursive) for output count — directories were counted as files | Fixed both to use `dir /b /s /a-d` (excludes directories) |

---

# SYC v0.0.2 — Changelog

## New Commands

- **`syc ls`** — PowerShell-style directory listing with optional folder filter
  ```
  syc ls archive.syc
  syc ls archive.syc compressors\
  ```
- **`syc m`** — list all compression methods from `syc.ini` with resolved chains
- **`--innosetup`** / **`--innosetup FILE`** — silent mode for installer integration, outputs only `%` to stdout. Optionally writes `%` to a temp file in real time for polling from InnoSetup Pascal code.

---

## Extraction

- **`-f PATTERN`** — extract matching files with flat output (no folder structure)
- **`-ff PATTERN`** — extract matching files preserving full path
- Both support exact names, wildcards (`*.exe`), folder prefix (`compressors\`), and multiple filters (`-f a.exe -f b.exe`)
- `-f` / `-ff` not supported in tar mode (warning issued)

---

## Archives

- **`--comment "TEXT"`** — embed a text comment in the archive, visible in `l` and `ls`
- Stored with `FLAG_COMMENT = 0x20` in the binary header — fully backwards compatible (old archives read fine)

---

## GUI (sycg)

- Custom title bar with draggable window (`overrideredirect`) — no native Windows title bar
- **`--title "Text"`** — custom window title
- **`--icon file.ico`** — custom icon in title bar (`.ico` requires Pillow, `.png` native)
- **`--theme dark/white/auto`** — UI theme; `auto` detects Windows dark/light mode from registry
- **`--lang file.syl`** — language file system; ships with `EN.syl` and `ES.syl`
- **`--close`** — auto-close with 3s countdown after completion
- **`--nocancel`**, **`--nopause`**, **`--nobackground`** — disable individual buttons
- Real-time progress bar with smooth animation between steps
- Metrics display: processed, compressed, bytes, elapsed, ratio, speed

---

## Compatibility

- **Python 3.8.10** support:
  - Fixed type hints (`list[x]` → `List[x]`, `dict[x,y]` → `Dict[x,y]`)
  - Fixed `tarfile.extractall(filter="data")` — `filter` argument only exists in Python 3.12+, now falls back gracefully
- **Windows 7 / 8 / 10 / 11** — x86 and x64
- `build.bat` auto-detects Python 3.8 x86/x64, handles `psutil` prebuilt wheel for x86 (no Visual C++ Build Tools required)

---

## CLI

- All `[INFO]` output messages translated to English
- `default` field in `syc.ini` now correctly applied when method chain has no explicit options for a compressor (was parsed but silently ignored in v0.0.1)

---

## Bug Fixes

| Bug | Description | Fix |
|-----|-------------|-----|
| **`default` field ignored** | `syc.ini` `default = ...` was parsed but never passed to the executor — `{options}` stayed empty | Passed `comp_def.default` as `extra_options` to `build_cmd()` |
| **`tarfile.extractall` crash on Python 3.8** | `filter="data"` argument only exists in Python 3.12+, caused `TypeError` on extraction | `try/except TypeError` fallback to `extractall()` without filter |
| **Type hint crash on Python 3.8** | `list[str]`, `dict[str, X]` inline generics not supported before Python 3.9 | Replaced with `List[str]`, `Dict[str, X]` from `typing` module |
| **`--innosetup` monitor output leaked** | `ProgressMonitor` thread wrote `[INFO]   00:xx` lines even in silent mode | Check `_progress.innosetup` at thread start and in write loop |
| **`--innosetup` stdio steps not counted** | Stdio compressors (srep, xprecomp) skipped `global_progress.step()` when `show_progress=False` | Removed `show_progress` condition from stdio end-step reporting |
| **`_extract_tar` indentation bug** | `try/except` block inside `_extract_tar` was double-indented, causing silent extraction failure | Fixed indentation |
| **`_Progress` missing attributes** | `innosetup` and `progress_file` added to `setup()` instead of `__init__()`, causing `AttributeError` when `_out()` ran before `setup()` | Moved both fields to `__init__()` |
| **`sycg` Total Progress regex (Spanish)** | Parser looked for `Progreso Total` but `syc.py` was translated to emit `Total Progress` | Updated regex to match English output |
| **`sycg` `os` shadowing in `main()`** | `import os` inside an `except` block in `main()` made Python treat `os` as a local variable throughout `main()`, causing `UnboundLocalError` | Renamed to `import os as _os` |
| **`sycg` `sys.executable` vs `__file__`** | When compiled with PyInstaller, `__file__` pointed to the `_MEI` temp dir instead of the real exe dir | Used `sys.executable` when `sys.frozen` is set |
| **`UnicodeEncodeError` on CJK filenames** | Windows default `cp1252` encoding caused crash on Chinese/Japanese file names | Force `PYTHONIOENCODING=utf-8` + `PYTHONUTF8=1` in subprocess env |
| **zpaqfranz extraction failed without `-nopath`** | Without `-nopath`, zpaqfranz stored full temp paths inside the archive, causing extraction to fail | Added `-nopath` as required flag in `syc.ini` documentation and default config |
| **`sycg` `CREATE_NO_WINDOW` missing** | `syc.exe` subprocess opened a visible console window when launched from sycg | Added `subprocess.CREATE_NO_WINDOW` flag on Windows |

---

## Known Limitations (planned for future releases)

- **Self-extracting archives (SFX)** — planned for v0.0.3
- **`solid` field** in compressor definitions — parsed but not enforced
- **`syc.groups`** — per-file-type compressor selection not implemented
- **Multi-volume spanning with recovery records** — not implemented
- **Archive timestamps** — file modification dates not stored in `.syc`
- **InnoSetup native Pascal integration** — no official `.iss` include, manual `Exec()` only