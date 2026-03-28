# Examples & Recipes

[← Back to README](../README.md)

---

## Basic Compression

```powershell
# Fast: zstd level 22
syc a backup.syc myfolder -m z22

# Better ratio: xprecomp + srep + zstd
syc a backup.syc myfolder -m xpszx

# Best ratio (slow): xprecomp + srep + zpaqfranz
syc a backup.syc myfolder -m xpszf1 -tar
```

---

## Solid Mode (-tar)

Packs all files into a single tar block before compressing. Much better ratio for folders with many small files.

```powershell
# Solid mode
syc a backup.syc myfolder -m xpszf1 -tar

# Solid, temp in RAM (faster if enough RAM)
syc a backup.syc myfolder -m xpszf1 -tar -tmpr

# Solid, temp in specific folder
syc a backup.syc myfolder -m xpszf1 -tar -tmpd D:\temp
```

---

## Block Mode (-block)

Splits the solid tar into independent compressed blocks. Each block is decompressed independently — ideal for large archives or when RAM is limited.

```powershell
# 512 MB blocks (good balance of ratio and RAM)
syc a backup.syc myfolder -m xpszf1 -block 512MB

# 256 MB blocks (lower RAM peak on 32-bit)
syc a backup.syc myfolder -m xpszf1 -block 256MB

# Extract (transparent — blocks decompressed automatically)
syc x backup.syc -o dest
```

> `-block` implies `-tar` automatically.

---

## Deduplication (-dd)

Performs chunk-level deduplication across all input files before compressing. Files that share identical chunks (even in different files) are stored only once.

```powershell
# Default chunk size (4 MB)
syc a backup.syc myfolder -m xpszf1 -dd

# Custom chunk size
syc a backup.syc myfolder -m xpszf1 -dd 8MB

# Dedup + block mode (best for large, partially-redundant datasets)
syc a backup.syc myfolder -m xpszf1 -dd 4MB -block 256MB
```

---

## Multi-Part Archives

```powershell
# Split into 700 MB parts (DVD-friendly)
syc a "backup??.syc" myfolder -m xpszx -chunk 700MB

# Split into 4 GB parts (FAT32 limit)
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

# Hide file names too
syc a backup.syc myfolder -m xpszx -key MyPassword --full-encrypted

# Extract encrypted
syc x backup.syc -o dest -key MyPassword
```

---

## Filtering Files

```powershell
# Exclude temp files and logs
syc a backup.syc myfolder -m xpszx -x "*.tmp" -x "*.log"

# Include only executables
syc a backup.syc myfolder -m xpszx -n "*.exe" -n "*.dll"
```

---

## Partial Extraction

```powershell
# Extract single file flat (no folders)
syc x backup.syc -o dest -f "readme.txt"

# Extract preserving full path
syc x backup.syc -o dest -ff "compressors\srep.exe"

# Wildcard
syc x backup.syc -o dest -f "compressors\*.exe"

# Multiple filters
syc x backup.syc -o dest -f "srep.exe" -f "zstd.exe"
```

---

## Hashing and Logging

```powershell
# Store checksums
syc a backup.syc myfolder -m xpszx --crc32 --md5

# Log (auto name: backup.syc.log)
syc a backup.syc myfolder -m xpszx --log

# Log to specific path
syc a backup.syc myfolder -m xpszx --log D:\logs\backup.log
```

---

## GUI Progress Window (sycg)

```powershell
# Basic
sycg a backup.syc myfolder -m xpszf1 -tar

# Spanish, white theme, custom title
sycg x data.syc -o dest --lang ES --theme white --title "Extracting files..."

# Custom icon
sycg a backup.syc myfolder -m xpszx --icon myapp.ico

# InnoSetup (no buttons, auto-close)
sycg x data.syc -o dest --nocancel --nopause --nobackground --close
```

---

## Archive Manager (psycg)

```powershell
# Open empty manager
psycg

# Open specific archive
psycg backup.syc

# Spanish, light theme
psycg --lang ES --theme white
```

---

## InnoSetup Integration

```iss
[Files]
Source: "syc.exe";    DestDir: "{tmp}"; Flags: deleteafterinstall
Source: "sycg.exe";   DestDir: "{tmp}"; Flags: deleteafterinstall
Source: "syc.ini";    DestDir: "{tmp}"; Flags: deleteafterinstall
Source: "lang\ES.syl"; DestDir: "{tmp}\lang\"; Flags: deleteafterinstall

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
         ' --lang "' + ExpandConstant('{tmp}\lang\ES.syl') + '"' +
         ' --title "Installing MyApp"',
         ExpandConstant('{tmp}'),
         SW_SHOW, ewWaitUntilTerminated, ResultCode);
  end;
end;
```

---

## List Archive Contents

```powershell
# Compact table
syc l backup.syc

# PowerShell style
syc ls backup.syc

# Filter by folder
syc ls backup.syc compressors\

# Encrypted
syc l backup.syc -key MyPassword
```

---

## Combining Everything

```powershell
# Maximum compression, encrypted, hashed, logged
syc a secure.syc myfolder -m xpszf1 -tar -block 512MB ^
    -key StrongPass --full-encrypted --md5 --crc32 --log

# Extract
syc x secure.syc -o recovered -key StrongPass
```

---

## See Also

- [CLI Reference — syc](syc-cli.md)
- [GUI Reference — sycg](sycg-gui.md)
- [Archive Manager — psycg](psycg-gui.md)
- [syc.ini Configuration](syc-ini.md)
