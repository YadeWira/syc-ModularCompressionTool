# CLI Reference — syc

[← Back to README](../README.md)

---

## Commands

| Command | Description |
|---|---|
| `a` | Add / compress files into a `.syc` archive |
| `x` | Extract preserving folder structure |
| `e` | Extract flat (no folder structure) |
| `l` | List contents (compact table) |
| `ls` | List contents PowerShell-style, with optional folder filter |
| `t` | Verify archive integrity |
| `m` | List all compression methods from syc.ini |

---

## Command: `a` — Add / Compress

```powershell
syc a <archive.syc> <files...> [options]
```

### Core

| Flag | Description |
|---|---|
| `-m METHOD` | Compression method — alias from `syc.ini` or direct chain. **Required.** |
| `-cfg FILE` | Config file (default: `syc.ini` in current directory) |
| `-v` | Verbose: show each file name and ratio |
| `-vv` | Extra verbose: show live compressor output |

### Solid mode

| Flag | Description |
|---|---|
| `-tar` | Pack all files into a tar block before compressing |
| `-block SIZE` | Split tar into independent blocks (e.g. `256MB`, `512MB`, `1GB`). Implies `-tar`. Each block compressed and decompressed independently — low RAM usage. |
| `-tmpr` | Store tar temp in RAM (faster if you have enough RAM) |
| `-tmpd [PATH]` | Store tar temp on disk. If PATH omitted, uses system temp. |

### Deduplication

| Flag | Description |
|---|---|
| `-dd [CHUNK_SIZE]` | Chunk-level dedup before compressing. Default chunk: `4MB`. Example: `-dd 8MB`. Combine with `-block` for low-RAM dedup of large datasets. |

### Multi-part

| Flag | Description |
|---|---|
| `-chunk SIZE` | Split output into parts (e.g. `4MB`, `700KB`, `1GB`). Requires `??` in archive name. |

### Filters

| Flag | Description |
|---|---|
| `-x PATTERN` | Exclude files matching PATTERN. Repeatable. Supports wildcards: `-x "*.tmp"` |
| `-n PATTERN` | Include only files matching PATTERN. Repeatable. |

### Hashing

| Flag | Description |
|---|---|
| `--crc32` | Store CRC32 per file |
| `--md5` | Store MD5 per file |

### Encryption

| Flag | Description |
|---|---|
| `-key PASSWORD` | Encrypt with password (AES-256 by default) |
| `-ks ALGORITHM` | `AES256` (default) or `CC20` (ChaCha20-Poly1305) |
| `--full-encrypted` | Encrypt header too — hides file names |

### Other

| Flag | Description |
|---|---|
| `--comment "TEXT"` | Embed a text comment |
| `--innosetup [FILE]` | Silent mode: only output `%` to stdout |
| `--log [FILE]` | Save log. Auto name: `archive.syc.log` |

---

## Command: `x` — Extract

```powershell
syc x <archive.syc> [options]
```

| Flag | Description |
|---|---|
| `-o PATH` | Output directory (default: current directory) |
| `-f PATTERN` | Extract matching files, **flat** (no folder structure). Repeatable. |
| `-ff PATTERN` | Extract matching files, **preserving full path**. Repeatable. |
| `-ow MODE` | Overwrite: `+` always (default), `-` skip, `p` prompt |
| `-y` | Yes to all prompts (same as `-ow +`) |
| `-cfg FILE` | Config file path |
| `-key PASSWORD` | Password for encrypted archives |
| `-tmpr` / `-tmpd` | Temp file location |
| `--log [FILE]` | Save extraction log |

> `-f` and `-ff` are not supported in tar mode. Extract without them first.

### Multi-part extraction

```powershell
syc x "backup??.syc" -o destination
```

---

## Command: `e` — Extract Flat

Like `x` but always extracts without folder structure (equivalent to `x -f "*"`).

---

## Command: `l` — List

```powershell
syc l <archive.syc> [-key PASSWORD]
```

Shows file name, original size, compressed size, ratio, CRC32 and MD5 (if stored).

---

## Command: `ls` — List (PowerShell style)

```powershell
syc ls <archive.syc> [folder\] [-key PASSWORD]
```

```
    Archive: backup.syc  [xpszf1 | solid tar]
    Comment: Game data v1.2

Mode       Length  Name
----       ------  ----
d----              compressors\
-a---       1,245  readme.txt

    1 directory    18 files    14.5 MB original    6.8 MB compressed
```

---

## Command: `t` — Test / Verify

```powershell
syc t <archive.syc>
```

Verifies the archive header and checks CRC32/MD5 hashes if present.

---

## Command: `m` — List Methods

```powershell
syc m [-cfg FILE]
```

```
[INFO] Methods defined in config (5 total):

  z22     ->  zstd:--ultra:-22
  xpszx   ->  xprecomp+srep:-m5f:-a0+zstd:--ultra:-22
  xpszf1  ->  xprecomp+srep:-m5f:-a0+zpaqfranz:-ssd:-t0:-m1
```

---

## Method Chains

```powershell
# Using an alias
syc a out.syc folder -m xpszf1

# Direct chain (same thing)
syc a out.syc folder -m "xprecomp+srep:-m5f:-a0+zpaqfranz:-ssd:-t0:-m1"
```

Chain syntax: `compressor1:opt1:opt2+compressor2:opt1`  
Options use `:` as separator: `srep:-m5f:-a0` → runs `srep -m5f -a0`

---

## See Also

- [syc.ini Configuration](syc-ini.md)
- [Examples & Recipes](examples.md)
- [GUI Reference — sycg](sycg-gui.md)
- [Archive Manager — psycg](psycg-gui.md)
