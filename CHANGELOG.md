# SYC Changelog

---

# v0.2.0

## New Features

### syc — CLI

- **`-block SIZE`** — splits solid tar into independent compressed blocks (e.g. `-block 512MB`). Each block is compressed and decompressed independently, enabling low-RAM operation on large archives. Works with or without `-tar`.
- **`-dd [CHUNK_SIZE]`** — chunk-level deduplication before compression. Default chunk: 4 MB. Example: `-dd 8MB -block 256MB` for RAM-efficient dedup of large datasets.
- **`compress_stream`** — tar solid mode no longer loads the tar into RAM. The tar file is written to disk and fed to the compressor pipeline via file paths, not `bytes`. Eliminates the double-RAM spike that caused crashes on 32-bit builds with large inputs.
- **Streaming SHA-256** in dedup analysis — files are hashed in 8 MB chunks instead of being fully loaded. A 4 GB file no longer causes a crash.
- **Streaming chunk reads** in `-dd` — `_dedup_files` reads directly in `chunk_size` blocks, never loads the full file.

### psycg — Archive Manager

- **Lazy tree loading** — `<<TreeviewOpen>>` event loads folder children on first expand. Previously all nodes were inserted at open time; large archives with thousands of entries no longer freeze the UI.
- **Real-time search** — search box in the path bar filters the file list as you type.
- **Keyboard shortcuts**: `Ctrl+O` Open, `Ctrl+N` Create, `F5` Reload, `Delete` Close archive, `Backspace`/`Alt+←` Navigate up, `Ctrl+A` Select all.
- **F5 reload** (`_reload_archive`) — reloads the current archive from disk without reopening the dialog.
- **Select all** (`_select_all`) — selects all visible tree items.
- **Drag & drop** — files dropped onto the window open if they are `.syc` archives (requires `tkinterdnd2`; fails silently if absent).
- **"Select all"** added to context menu.
- **Status bar keyboard hint** — shows `Ctrl+O  Ctrl+N  F5  Del` at the far right in a very dim color.
- **App Identity** section in Settings:
  - Custom app name (shown in title bar and taskbar)
  - Custom icon (`.ico` / `.png`) with 24×24 preview
  - Reset button
  - Saved in `psycg.cfg` as `app_name` / `app_icon`
  - Applied at startup and live when OK is clicked
- **Default generated icon** — a blue rounded square with "S" is shown in the title bar when no custom icon is configured. Generated programmatically via PIL (or plain `PhotoImage` fallback).
- **Icon inherited by sycg** — when psycg launches sycg for an operation, the configured icon path is passed via `--icon`.
- **`_set_window_icon`** — uses `WM_SETICON` via ctypes for reliable icon assignment on `overrideredirect` windows; falls back to PIL `iconphoto` then `wm_iconbitmap`.

### Language system

- **All 5 languages fully translated**: EN, ES, FR, PT, RU — 91 keys each for psycg + 23 keys for sycg.
- **Both GUI apps share a single `.syl` file**: `[psycg]` section for the archive manager, `[sycg]` section for the progress window.
- **sycg Lang parser fixed**: `[sycg]` section keys are now correctly mapped (`window_compressing` → `window.compressing`) — passing `--lang ES.syl` to sycg now actually applies the translation.
- **`settings.restart_note`** key added for theme-change notification.

## Bug Fixes

| File | Location | Bug | Fix |
|---|---|---|---|
| `syc.py` | `cmd_add` dedup extract | `args.ow` always returned `"+"` | Changed to `args.overwrite` |
| `archive.py` | `_build_flags` | `FLAG_MULTIBLOCK` activated even for single-blob dedup | Only set when `len(dedup_blobs) > 1` |
| `archive.py` | `_parse_index`, `_parse_index_stream` | `tar_compressed_size` assigned decrypted size | Now uses on-disk size (`comp_size` / `enc_tar_size`) |
| `chunk.py` | `peek_tar_mode` | `flag == FLAG_TAR` fails when other flags are set (e.g. `FLAG_COMMENT`) | Changed to `bool(flag & FLAG_TAR)` |
| `chunk.py` | `read_tar_parts` | Same flag equality bug in part-1 validation | Same fix |
| `psycg.py` | `PropertiesDialog` | X button created but never `.pack()`ed — invisible | Added `.pack(side="right")` |
| `psycg.py` | `SettingsDialog` | Duplicate X button (one without bind) | Removed the duplicate |
| `psycg.py` | `AskPasswordDialog` | X button had no `.bind("<Button-1>")` | Added bind |
| `psycg.py` | `ExtractDialog` | X button had no bind | Added bind |
| `psycg.py` | `_on_double_click` preview | Used `-ff basename` — wrong file extracted when duplicate names exist | Now uses full archive path |
| `psycg.py` | `_on_double_click` preview | Temp dirs created but never deleted | Tracked in `_preview_dirs`, cleaned in `_on_close` |
| `psycg.py` | `_build_subtree` | `_visual_width(c) == 2` wrong — should compare `_visual_width` of single char | Fixed ratio condition |
| `sycg.py` | `Lang.__init__` | `[sycg]` section keys stored as `sycg.window_compressing` but looked up as `window.compressing` | Parser now strips section prefix and converts `_` → `.` for `[sycg]` section |

## Removed

- `_build_tar_memory` — no longer used (compress_stream path uses disk for all tar operations)
- Duplicate local imports (`import time as _time`, `import hashlib as _hashlib`, etc.) inside functions — all moved to module-level

---

# v0.1.0

## New Features

- **`psycg`** — Full GUI archive manager (WinRAR/7-Zip style)
  - Hierarchical file tree with expand/collapse folders
  - Navigate into folders with double-click, ↑ Up button
  - Toolbar: Open, Create, Extract, Extract To, Test, Info, Close, Settings
  - Create Archive dialog: method, solid tar, CRC32, MD5, encrypt, split (-chunk)
  - Extract dialog with overwrite modes: always, skip, ask
  - Archive Properties dialog
  - Context menu: extract selected, extract to, copy name
  - Double-click file → extract to temp and open with default app
  - Resize-aware: Name column stretches, fixed columns stay right-aligned

- **Language system (`psycg`)** — `.syl` files in `lang/` folder
  - Ships with EN, ES, FR, PT, RU
  - Live language switching via Settings dialog
  - Inherits current language when launching `sycg`

- **Settings dialog** — persistent `psycg.cfg`
  - Theme: Dark / Light / Auto
  - Language selector (auto-discovers `.syl` files in `lang/`)

- **`-x PATTERN`** — Exclude files from compression (repeatable)
- **`-n PATTERN`** — Include only matching files (repeatable)
- **`-ow MODE`** — Overwrite control on extract: `+` always, `-` skip, `p` prompt
- **`-y`** — Answer yes to all prompts
- **`e` command** — Extract flat (no folder structure)
- **`-m` is now required** — no silent fallback to undefined default method

## Bug Fixes

- Fixed `psycg` column "RatioMethod" (Ratio too narrow, Method left-aligned)
- Fixed packed size overflow on multi-part archives in `psycg`
- Fixed drag trembling (use absolute `x_root` coordinates)
- Fixed `psycg` `??.syc` not opening after creation (resolves glob to first part)
- Fixed `_here()` not defined when `Config()` initialized at module load

---

# v0.0.3

## Bug Fixes

| Bug | Fix |
|---|---|
| Tar extraction on Windows: backslash in arcname → only last file extracted | `_arcname()` now always uses forward slashes |
| AES256/ChaCha20 extract fails in normal mode | `write()` now encrypts per-entry; stores encrypted size |
| `l` command fails on encrypted normal archives | Same fix |
| `-f` exact match fails on sub-path entries | `_matches_filter()` also compares against basename |
| Multi-part normal extract: `ModuleNotFoundError` (recovery module) | Removed unimplemented import |
| Test round-trip count mismatch | `test.bat` fixed to use `dir /b /s /a-d` |

---

# v0.0.2

## New Commands

- **`syc ls`** — PowerShell-style listing with optional folder filter
- **`syc m`** — list all methods from `syc.ini` with resolved chains
- **`--innosetup [FILE]`** — silent mode for installer integration

## Extraction

- **`-f PATTERN`** — flat extraction (no folder structure)
- **`-ff PATTERN`** — extraction preserving full path
- Both support wildcards, exact names, folder prefixes, and multiple filters

## Archives

- **`--comment "TEXT"`** — embed a text comment (`FLAG_COMMENT = 0x20`)

## GUI (sycg)

- Custom title bar, draggable window
- `--title`, `--icon`, `--theme`, `--lang`, `--close`, `--nocancel`, `--nopause`, `--nobackground`
- Real-time progress bar, metrics display

## Compatibility

- Python 3.8.10 support (type hints, `tarfile.extractall` filter fallback)
- Windows 7 / 8 / 10 / 11, x86 and x64

---

# v0.0.1

Initial release.
