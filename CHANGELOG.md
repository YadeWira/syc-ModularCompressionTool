# SYC Changelog

---

# v0.2.1

## Bug Fixes

| File | Location | Bug | Fix |
|---|---|---|---|
| `executor.py` | `_apply_step_file` (used by `compress_stream`) | zpaqfranz stores the filename it receives internally (`data_XXXXXXXX.tmp`). During decompression it extracts `data_XXXXXXXX.tmp` but the code searched for `data.tmp` — not found → `Tempfile decompress: 'data.tmp' not found` | Each step now uses its own subdirectory (`workdir/UID/`) with fixed names inside (`data.tmp`, `packed.zpaq`). zpaqfranz always sees and stores `data.tmp`. |

This bug caused **all tar-mode extractions** to fail when using zpaqfranz (or any tempfile compressor as the last step):

- Section 9: extract json tar, extract mixed tar
- Section 10: extract full-encrypted (tar mode)
- Section 12: extract multi-part tar
- Section 14: `--innosetup` extract (tar mode)
- Section 15: round-trip nato, round-trip Kodak

Block mode (`-block`) and dedup (`-dd`) were unaffected because they use a different extraction path.

**Test results after fix: 126 PASS, 0 FAIL, 1 SKIP** (from 115/11/1 before).

---

# v0.2.0

## New Features

### syc — CLI

- **`-block SIZE`** — splits solid tar into independent compressed blocks (e.g. `-block 512MB`). Each block is compressed and decompressed independently, enabling low-RAM operation on large archives. Works with or without `-tar`.
- **`-dd [CHUNK_SIZE]`** — chunk-level deduplication before compression. Default chunk: 4 MB. Example: `-dd 8MB -block 256MB` for RAM-efficient dedup of large datasets.
- **`compress_stream`** — tar solid mode no longer loads the tar into RAM. The tar file is written to disk and fed to the compressor pipeline via file paths, not `bytes`. Eliminates the double-RAM spike on large inputs.
- **Streaming SHA-256** in dedup analysis — files are hashed in 8 MB chunks instead of being fully loaded.
- **Streaming chunk reads** in `-dd` — `_dedup_files` reads directly in `chunk_size` blocks, never loads the full file.

### psycg — Archive Manager

- **Lazy tree loading** — `<<TreeviewOpen>>` event loads folder children on first expand.
- **Real-time search** — search box in the path bar filters the file list as you type.
- **Keyboard shortcuts**: `Ctrl+O` Open, `Ctrl+N` Create, `F5` Reload, `Delete` Close archive, `Backspace`/`Alt+←` Navigate up, `Ctrl+A` Select all.
- **F5 reload** — reloads the current archive from disk without reopening.
- **Drag & drop** — `.syc` files dropped onto the window open automatically (requires `tkinterdnd2`).
- **"Select all"** added to context menu.
- **App Identity** section in Settings — custom app name, icon (`.ico`/`.png`) with 24×24 preview, Reset button. Saved in `psycg.cfg`.
- **Default generated icon** — blue rounded square with "S" shown when no icon is configured.
- **Icon inherited by sycg** — configured icon passed via `--icon` when launching sycg for operations.
- **`_set_window_icon`** — uses `WM_SETICON` via ctypes for reliable icon assignment.

### Language system

- **All 5 languages fully translated**: EN, ES, FR, PT, RU — 91 keys each for `[psycg]` + 23 keys for `[sycg]`.
- **Both GUIs share a single `.syl` file**: `[psycg]` section for the archive manager, `[sycg]` section for the progress window.
- **sycg Lang parser fixed**: `[sycg]` keys now correctly mapped (`window_compressing` → `window.compressing`).

## Bug Fixes

| File | Location | Bug | Fix |
|---|---|---|---|
| `syc.py` | `cmd_add` dedup extract | `args.ow` always returned `"+"` | Changed to `args.overwrite` |
| `archive.py` | `_build_flags` | `FLAG_MULTIBLOCK` set even for single-blob dedup | Only set when `len(dedup_blobs) > 1` |
| `archive.py` | `_parse_index_stream` | `tar_compressed_size` used decrypted size | Now uses on-disk size |
| `chunk.py` | `peek_tar_mode` | `flag == FLAG_TAR` fails when other flags set | Changed to `bool(flag & FLAG_TAR)` |
| `chunk.py` | `read_tar_parts` | Same flag equality bug | Same fix |
| `psycg.py` | `PropertiesDialog` | X button not packed — invisible | Added `.pack(side="right")` |
| `psycg.py` | `SettingsDialog` | Duplicate X button | Removed duplicate |
| `psycg.py` | `AskPasswordDialog` / `ExtractDialog` | X buttons had no bind | Added bind |
| `psycg.py` | `_on_double_click` | Preview used basename → wrong file when duplicates exist | Now uses full archive path |
| `psycg.py` | `_on_double_click` | Temp dirs never deleted | Tracked in `_preview_dirs`, cleaned in `_on_close` |
| `sycg.py` | `Lang.__init__` | `[sycg]` keys stored as `sycg.window_compressing`, looked up as `window.compressing` | Parser strips section prefix, converts `_` → `.` |

## Removed

- `_build_tar_memory` — replaced by `compress_stream`
- Duplicate local imports inside functions — moved to module level

---

# v0.1.0

## New Features

- **`psycg`** — Full GUI archive manager (WinRAR/7-Zip style)
  - Hierarchical file tree with expand/collapse folders
  - Toolbar: Open, Create, Extract, Extract To, Test, Info, Close, Settings
  - Create Archive dialog: method, solid tar, CRC32, MD5, encrypt, split
  - Extract dialog with overwrite modes: always, skip, ask
  - Archive Properties dialog
  - Context menu: extract selected, extract to, copy name
  - Double-click file → extract to temp and open with default app

- **Language system (`psycg`)** — `.syl` files in `lang/` folder
  - Ships with EN, ES, FR, PT, RU
  - Live language switching via Settings dialog

- **Settings dialog** — persistent `psycg.cfg` (theme, language)

- **`-x PATTERN`** — Exclude files from compression
- **`-n PATTERN`** — Include only matching files
- **`-ow MODE`** — Overwrite control: `+` always, `-` skip, `p` prompt
- **`-y`** — Answer yes to all prompts
- **`e` command** — Extract flat (no folder structure)
- **`-m` is now required**

## Bug Fixes

- Fixed `psycg` column sizing
- Fixed packed size overflow on multi-part archives
- Fixed drag trembling (absolute `x_root` coordinates)
- Fixed `psycg` not opening archive after creation

---

# v0.0.3

## Bug Fixes

| Bug | Fix |
|---|---|
| Tar extraction on Windows: backslash in arcname | `_arcname()` now always uses forward slashes |
| AES256/ChaCha20 extract fails in normal mode | `write()` encrypts per-entry, stores encrypted size |
| `-f` exact match fails on sub-path entries | `_matches_filter()` also compares basename |
| Multi-part extract: `ModuleNotFoundError` (recovery module) | Removed unimplemented import |
| Test round-trip count mismatch | `test.bat` fixed to use `dir /b /s /a-d` |

---

# v0.0.2

## New Commands

- **`syc ls`** — PowerShell-style listing with optional folder filter
- **`syc m`** — list all methods from `syc.ini`
- **`--innosetup [FILE]`** — silent mode for installer integration

## GUI (sycg)

- `--title`, `--icon`, `--theme`, `--lang`, `--close`, `--nocancel`, `--nopause`, `--nobackground`
- Real-time progress bar, metrics display

## Compatibility

- Python 3.8.10 support
- Windows 7 / 8 / 10 / 11, x86 and x64

---

# v0.0.1

Initial release.