# Getting Started

[← Back to README](../README.md)

---

## Requirements

- Windows 10 / 11 (x86 or x64)
- External compressors (see below)
- Python 3.10+ if running from source

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
  sycg.exe         — GUI wrapper
  syc.ini          — compressor configuration
  EN.syl           — English language file
  ES.syl           — Spanish language file
  compressors/
    zstd.exe
    srep.exe
    zpaqfranz.exe
    lz4.exe
    lolz.exe
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
```

## First Extraction

```powershell
syc x output.syc -o destination
```

## Using the GUI

```powershell
sycg a output.syc myfolder -m xpszx -tar
sycg x output.syc -o destination
```

---

## Verifying it Works

```powershell
syc
# Expected: SYC v0.0.1 x64 | by Yade Bravo (YadeWira) | CPU: ...
```

---

## Next Steps

- [CLI Reference](syc-cli.md) — all commands and flags
- [syc.ini Configuration](syc-ini.md) — define your own methods
- [Examples](examples.md) — common patterns
