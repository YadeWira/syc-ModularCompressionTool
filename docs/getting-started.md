# Getting Started

[← Back to README](../README.md)

---

## Requirements

- **Windows 7 / 8 / 10 / 11** (x86 or x64)
- External compressors (see below)
- Python **3.8+** if running from source (3.8 recommended for Win7 compatibility)

### pip packages (source only)

```powershell
pip install cryptography pillow psutil pyinstaller
```

---

## Directory Structure

Place all files in the same folder:

```
myapp/
  syc.exe          — main compressor CLI
  sycg.exe         — GUI progress window
  psycg.exe        — archive manager
  syc.ini          — compressor configuration
  lang/
    EN.syl         — English language file
    ES.syl         — Spanish language file
    FR.syl         — French
    PT.syl         — Portuguese
    RU.syl         — Russian
  compressors/
    zstd.exe
    srep.exe
    zpaqfranz.exe
    lz4.exe
    ...
  xtool/
    xtool.exe
    *.dll
```

---

## First Compression

```powershell
# Basic compression with zstd level 22
syc a output.syc myfolder -m z22

# Better ratio: xprecomp + srep + zstd
syc a output.syc myfolder -m xpszx

# Best ratio: xprecomp + srep + zpaqfranz (slow)
syc a output.syc myfolder -m xpszf1 -tar

# Large archives with low RAM (block mode)
syc a output.syc myfolder -m xpszf1 -tar -block 512MB
```

## First Extraction

```powershell
syc x output.syc -o destination
```

## Using the GUI Progress Window

```powershell
sycg a output.syc myfolder -m xpszx -tar
sycg x output.syc -o destination
```

## Using the Archive Manager

```powershell
# Open manager (empty)
psycg

# Open manager with a specific archive
psycg backup.syc
```

---

## Verifying it Works

```powershell
syc
# Expected: SYC v0.2.0 x64 | by Yade Bravo (YadeWira) | CPU: ...
```

---

## Next Steps

- [CLI Reference](syc-cli.md) — all commands and flags
- [Archive Manager](psycg-gui.md) — using the GUI manager
- [syc.ini Configuration](syc-ini.md) — define your own methods
- [Examples](examples.md) — common patterns
