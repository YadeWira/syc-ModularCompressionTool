# Examples & Recipes

[← Back to README](../README.md)

---

## Basic Compression

```powershell
# Fast compression with zstd level 22
syc a backup.syc myfolder -m z22

# Better ratio: xprecomp + srep + zstd
syc a backup.syc myfolder -m xpszx

# Best ratio (slow): xprecomp + srep + zpaqfranz m1
syc a backup.syc myfolder -m xpszf1 -tar
```

---

## Solid Mode (-tar)

Solid mode packs all files into a single tar block before compressing. This improves ratio significantly for folders with many small files.

```powershell
# Solid mode, temp on disk (default)
syc a backup.syc myfolder -m xpszf1 -tar

# Solid mode, temp in RAM (faster if you have enough RAM)
syc a backup.syc myfolder -m xpszf1 -tar -tmpr

# Solid mode, temp in specific directory
syc a backup.syc myfolder -m xpszf1 -tar -tmpd D:\temp
```

---

## Multi-Part Archives

```powershell
# Split into 700MB parts (DVD-friendly)
syc a "backup??.syc" myfolder -m xpszx -chunk 700MB

# Split into 4GB parts (FAT32 limit)
syc a "backup??.syc" myfolder -m xpszx -chunk 4000MB

# With solid mode
syc a "backup??.syc" myfolder -m xpszf1 -tar -chunk 700MB

# Extract multi-part
syc x "backup??.syc" -o destination
```

---

## Encryption

```powershell
# AES-256-GCM (default)
syc a backup.syc myfolder -m xpszx -key MyPassword

# ChaCha20-Poly1305 (faster on ARM)
syc a backup.syc myfolder -m xpszx -key MyPassword -ks CC20

# Encrypt everything including file names
syc a backup.syc myfolder -m xpszx -key MyPassword --full-encrypted

# Extract encrypted
syc x backup.syc -o dest -key MyPassword
```

---

## Hashing

```powershell
# Store CRC32 and MD5 per file
syc a backup.syc myfolder -m xpszx --crc32 --md5

# Verify (checks hashes during extraction)
syc t backup.syc
```

---

## Logging

```powershell
# Auto log name (backup.syc.log)
syc a backup.syc myfolder -m xpszx --log

# Custom log path
syc a backup.syc myfolder -m xpszx --log D:\logs\mybackup.log

# Log + verbose
syc a backup.syc myfolder -m xpszx -v --log
```

---

## GUI Usage

```powershell
# Basic GUI
sycg a backup.syc myfolder -m xpszf1 -tar

# Spanish UI
sycg a backup.syc myfolder -m xpszf1 -tar --lang ES.syl

# White theme with custom title and icon
sycg x data.syc -o dest --theme white --icon myapp.ico --title "Extracting files..."

# For InnoSetup (no buttons, auto-close)
sycg x data.syc -o dest --nocancel --nopause --nobackground --close --lang ES.syl
```

---

## InnoSetup Integration

Full example for an installer that extracts a `.syc` file with a progress window:

```iss
[Files]
Source: "syc.exe";           DestDir: "{tmp}"; Flags: deleteafterinstall
Source: "sycg.exe";          DestDir: "{tmp}"; Flags: deleteafterinstall
Source: "syc.ini";           DestDir: "{tmp}"; Flags: deleteafterinstall
Source: "ES.syl";            DestDir: "{tmp}"; Flags: deleteafterinstall
Source: "compressors\*";     DestDir: "{tmp}\compressors\"; Flags: deleteafterinstall recursesubdirs
Source: "xtool\*";           DestDir: "{tmp}\xtool\"; Flags: deleteafterinstall recursesubdirs
; data.syc is OUTSIDE the installer, next to setup.exe

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
var ResultCode: Integer;
begin
  if CurStep = ssPostInstall then
  begin
    Exec(ExpandConstant('{tmp}\sycg.exe'),
         'x "' + ExpandConstant('{src}\data.syc') + '"' +
         ' -o "' + ExpandConstant('{app}') + '"' +
         ' --nocancel --nopause --nobackground --close' +
         ' --lang "' + ExpandConstant('{tmp}\ES.syl') + '"' +
         ' --title "Installing MyApp"',
         ExpandConstant('{tmp}'),
         SW_SHOW, ewWaitUntilTerminated, ResultCode);
  end;
end;
```

Distribution layout:
```
release\
  MyApp Setup.exe   ← the installer
  data.syc          ← the compressed game/app data (outside installer)
```

---

## Listing Archive Contents

```powershell
# List all files
syc l backup.syc

# List encrypted archive
syc l backup.syc -key MyPassword
```

---

## Combining Everything

```powershell
# Maximum compression, encrypted, hashed, logged
syc a secure.syc myfolder -m xpszfx -tar -key StrongPass --full-encrypted --md5 --crc32 --log

# Extract it
syc x secure.syc -o recovered -key StrongPass
```

---

## See Also

- [CLI Reference — syc](syc-cli.md)
- [GUI Reference — sycg](sycg-gui.md)
- [syc.ini Configuration](syc-ini.md)
