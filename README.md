# SYC — Modular Compression Tool

> **S**tream **Y**our **C**ompression — a modular, pipeline-based archiver with external compressor support.

**By Yade Bravo (YadeWira)**

---

## What is SYC?

SYC is a command-line compression tool that orchestrates external compressors (zstd, srep, xprecomp, zpaqfranz, lz4, and more) in a pipeline, producing `.syc` archives. It follows the same `.ini` configuration format as FreeArc, making it easy to define and chain compressors.

SYC does not compress by itself — it coordinates external tools and manages the archive format, encryption, hashing, and multi-part splitting.

```
Input → xprecomp → srep → zpaqfranz → output.syc
```

---

## Features

- **Pipeline compression** — chain any number of external compressors
- **Solid mode** (`-tar`) — pack everything into a tar block before compressing for better ratios
- **Multi-part archives** — split output into fixed-size chunks
- **Encryption** — AES-256-GCM or ChaCha20-Poly1305 with PBKDF2 key derivation
- **Hashing** — optional CRC32 and MD5 per file
- **Archive comments** — embed a text comment with `--comment`
- **Real-time progress** — per-step percentage, MB/s speed, and elapsed time
- **GUI wrapper** (`sycg`) — tkinter-based progress window with theme and language support
- **Partial extraction** — extract specific files with `-f` (flat) or `-ff` (full path)
- **InnoSetup ready** — integrate with installers via `sycg` and `--innosetup` flags
- **Cross-architecture** — builds for x86 and x64 via `build.bat`

---

## Quick Start

```powershell
# Compress a folder
syc a backup.syc myfolder -m xpszx -tar

# Extract
syc x backup.syc -o dest

# With GUI
sycg a backup.syc myfolder -m xpszx -tar
```

---

## Documentation

| Document | Description |
|---|---|
| [Getting Started](docs/getting-started.md) | Installation, requirements, first steps |
| [CLI Reference — syc](docs/syc-cli.md) | All commands and flags for `syc.exe` |
| [GUI Reference — sycg](docs/sycg-gui.md) | All flags exclusive to `sycg.exe` |
| [syc.ini Configuration](docs/syc-ini.md) | Defining compressors and method chains |
| [Archive Format (.syc)](docs/archive-format.md) | Binary format specification |
| [Building from Source](docs/building.md) | Using `build.bat` for x86/x64 |
| [Language Files (.syl)](docs/language-files.md) | Localizing the GUI |
| [Examples & Recipes](docs/examples.md) | Common use cases and patterns |

## Changelog

### v0.0.2
- Added `--comment` flag to embed text comments in archives
- Added `syc ls` command — PowerShell-style directory listing with folder filter
- Added `syc m` command — list all compression methods from syc.ini
- Added `-f` / `-ff` flags for partial extraction (flat / full path)
- Added `--innosetup` flag for silent mode in installers
- Fixed Python 3.8 compatibility (type hints, `tarfile.extractall`)
- All CLI messages translated to English
- GUI (`sycg`): custom title bar, dark/white/auto themes, language files (.syl)
- GUI (`sycg`): `--icon`, `--theme`, `--lang`, `--close`, `--nocancel`, `--nopause`, `--nobackground`
- Windows 7 / 8 / 10 / 11 support (x86 and x64)

### v0.0.1
- Initial release

---

## Project Structure

```
syc/
  syc.py          — CLI main entry point
  sycg.py         — GUI wrapper (tkinter)
  archive.py      — .syc format read/write
  executor.py     — external compressor runner
  method.py       — method chain parser
  ini_parser.py   — syc.ini parser
  chunk.py        — multi-part archive support
  crypto.py       — AES-256 / ChaCha20 encryption
  syc.ini         — compressor definitions
  EN.syl          — English language file (sycg default)
  ES.syl          — Spanish language file
  build.bat       — automated build script
  docs/           — documentation
```

---

## Compatibility

| OS | x64 | x86 |
|---|---|---|
| Windows 11 | ✓ | ✓ |
| Windows 10 | ✓ | ✓ |
| Windows 8 / 8.1 | ✓ | ✓ |
| Windows 7 | ✓ | ✓ |

Compiled binaries target **Python 3.8.10 – 3.8.20**, ensuring maximum compatibility across all supported Windows versions.

---

## Requirements

- Python **3.8.10 – 3.8.20** (for running from source or building)
- External compressors placed in `compressors\` and `xtool\`
- `cryptography` pip package (for encryption features)
- `Pillow` pip package (for `.ico` icons in sycg)
- `psutil` pip package (optional, for CPU/RAM info)

---

## Known Limitations & Not Yet Implemented

These features exist in FreeArc or are planned but not yet implemented in SYC:

### `solid` field in compressor definitions

FreeArc supports a `solid` flag per compressor to indicate it works in solid mode only:

```ini
[External compressor:prepng]
header   = 0
solid    = 0
packcmd  = precomp -d0 -cn -f -o$$arcpackedfile$$.tmp $$arcdatafile$$.tmp
unpackcmd = precomp -o$$arcdatafile$$.tmp -r $$arcpackedfile$$.tmp
```

SYC parses this field but does not enforce it. The compressor will be used regardless of solid/non-solid mode.

### `syc.groups` — compressor groups

FreeArc supports a `.groups` file that defines sets of compressors and selection rules per file type (e.g. use PNG precompressor only for `.png` files). SYC reads `syc.ini` only and has no per-file-type compressor selection.

### InnoSetup integration — no native Pascal code

There is no official SYC Pascal unit or include file for InnoSetup. Integration is done manually via `Exec()` / `[Run]` calling `sycg.exe`, with progress polling via a temp file or by relying on `sycg`'s built-in progress window. A proper `[Code]`-level integration with native progress bar control is not yet available.

### Other FreeArc features not implemented

- `mem` field (memory limit per compressor)
- `dict` field (dictionary size hint)
- Multi-volume spanning with recovery records
- Archive comments
- Self-extracting archives (SFX) — planned for future release

---

## License

SYC is created by Yade Bravo (YadeWira).
