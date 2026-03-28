# SYC — Modular Compression Tool

> **S**tream **Y**our **C**ompression — a modular, pipeline-based archiver with external compressor support.

**By Yade Bravo (YadeWira)** · v0.2.0

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
- **Block mode** (`-block SIZE`) — split solid tar into independent compressed blocks for low-RAM operation
- **Deduplication** (`-dd`) — chunk-level dedup before compression, combinable with `-block`
- **Multi-part archives** (`-chunk SIZE`) — split output into fixed-size parts
- **Encryption** — AES-256-GCM or ChaCha20-Poly1305 with PBKDF2 key derivation
- **Hashing** — optional CRC32 and MD5 per file
- **Archive comments** — embed a text comment with `--comment`
- **Real-time progress** — per-step percentage, MB/s speed, and elapsed time
- **Low RAM usage** — compress_stream pipeline never loads the tar into memory
- **GUI wrapper** (`sycg`) — progress window with theme and language support
- **Archive manager** (`psycg`) — full WinRAR/7-Zip style manager with tree view, lazy loading, search
- **Partial extraction** — extract specific files with `-f` (flat) or `-ff` (full path)
- **InnoSetup ready** — integrate with installers via `sycg` and `--innosetup` flags
- **Cross-architecture** — builds for x86 and x64 via `build.bat`
- **Windows 7+** compatible — Python 3.8, no modern API dependencies

---

## Quick Start

```powershell
# Compress a folder
syc a backup.syc myfolder -m xpszx -tar

# Extract
syc x backup.syc -o dest

# With GUI progress window
sycg a backup.syc myfolder -m xpszx -tar

# Open archive manager
psycg
psycg backup.syc
```

---

## Documentation

| Document | Description |
|---|---|
| [Getting Started](docs/getting-started.md) | Installation, requirements, first steps |
| [CLI Reference — syc](docs/syc-cli.md) | All commands and flags for `syc.exe` |
| [GUI Reference — sycg](docs/sycg-gui.md) | Progress window flags for `sycg.exe` |
| [Archive Manager — psycg](docs/psycg-gui.md) | Full archive manager reference |
| [syc.ini Configuration](docs/syc-ini.md) | Defining compressors and method chains |
| [Archive Format (.syc)](docs/archive-format.md) | Binary format specification |
| [Building from Source](docs/building.md) | Using `build.bat` for x86/x64 |
| [Language Files (.syl)](docs/language-files.md) | Localizing both GUIs |
| [Examples & Recipes](docs/examples.md) | Common use cases and patterns |

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for the full version history.
