# CLI Reference — syc

[← Back to README](../README.md)

---

## Commands

```
syc <command> [options]
```

| Command | Description |
|---|---|
| `a` | Add / compress files into a `.syc` archive |
| `x` | Extract files from a `.syc` archive |
| `l` | List contents of an archive |
| `t` | Verify archive integrity |

---

## Command: `a` — Add / Compress

```powershell
syc a <archive.syc> <files...> [options]
```

### Core options

| Flag | Description |
|---|---|
| `-m METHOD` | Compression method — alias from `syc.ini` or direct chain (e.g. `xpszx`) |
| `-cfg FILE` | Config file path (default: `syc.ini` in current directory) |
| `-v` | Verbose: show each file name and compression ratio |
| `-vv` | Extra verbose: show live compressor output |

### Solid mode

| Flag | Description |
|---|---|
| `-tar` | Pack all files into a tar block before compressing (better ratio) |
| `-tmpr` | Store tar temporary file in RAM |
| `-tmpd [PATH]` | Store tar temporary file on disk. If PATH is omitted, uses system temp |

### Multi-part

| Flag | Description |
|---|---|
| `-chunk SIZE` | Split output into parts of SIZE (e.g. `4MB`, `700KB`, `1GB`) |

> Requires `??` in the archive name: `syc a "backup??.syc" folder -m xpszx -chunk 700MB`
> Output: `backup01.syc`, `backup02.syc`, ...

### Hashing

| Flag | Description |
|---|---|
| `--crc32` | Calculate and store CRC32 checksum per file |
| `--md5` | Calculate and store MD5 checksum per file |

### Encryption

| Flag | Description |
|---|---|
| `-key PASSWORD` | Encrypt archive with a password (AES-256 by default) |
| `-ks ALGORITHM` | Encryption algorithm: `AES256` (default) or `CC20` (ChaCha20-Poly1305) |
| `--full-encrypted` | Also encrypt the archive header (hides file names) |

### Logging

| Flag | Description |
|---|---|
| `--log` | Save log to `archive.syc.log` (auto name) |
| `--log FILE` | Save log to a specific path |

---

## Command: `x` — Extract

```powershell
syc x <archive.syc> [options]
```

| Flag | Description |
|---|---|
| `-o PATH` | Output directory (default: current directory) |
| `-cfg FILE` | Config file path |
| `-v` | Verbose output |
| `-vv` | Extra verbose |
| `-key PASSWORD` | Password for encrypted archives |
| `-tmpr` | Extract temp file in RAM |
| `-tmpd [PATH]` | Extract temp file on disk |
| `--log [FILE]` | Save extraction log |

### Multi-part extraction

```powershell
syc x "backup??.syc" -o destination
```

SYC automatically finds and reassembles all parts matching the pattern.

---

## Command: `l` — List

```powershell
syc l <archive.syc> [-key PASSWORD]
```

Lists all files with their original size, compressed size, and ratio.
For encrypted archives, provide `-key` to decrypt the header.

---

## Command: `t` — Test / Verify

```powershell
syc t <archive.syc>
```

Verifies the archive can be read correctly. Checks CRC32/MD5 hashes if present.

---

## Method Chains

Methods are defined in `syc.ini` as aliases. You can also use direct chains:

```powershell
# Using an alias
syc a out.syc folder -m xpszf1

# Direct chain (same thing)
syc a out.syc folder -m "xprecomp+srep:-m5f:-a0+zpaqfranz:-ssd:-t0:-m1"
```

Chain syntax: `compressor1:opt1:opt2+compressor2:opt1+compressor3`

Options use `:` as separator instead of spaces. Prefix `-` options with `-`:
- `srep:-m5f:-a0` → runs `srep -m5f -a0`
- `zpaqfranz:-ssd:-t0:-m1` → runs `zpaqfranz ... -ssd -t0 -m1`

---

## Progress Output

When compressing or extracting, SYC shows real-time progress:

```
[INFO] Config loaded from: syc.ini
[INFO] Method 'xpszf1' -> xprecomp+srep:-m5f:-a0+zpaqfranz:-ssd:-t0:-m1
[INFO] 11.1%
[INFO] Solid mode (-tar): packing 157 files (359.8 MB)...
[INFO] 22.2%
[INFO] [+] xprecomp (mixed)
[INFO]   00:11  360.0 MB escrito  32.5 MB/s
[INFO] 33.3%
...
[INFO] Total: 359.8 MB -> 142.5 MB (60.4% reduction)
[INFO] Elapsed time: 22.40 sec
```

---

## See Also

- [syc.ini Configuration](syc-ini.md)
- [Examples & Recipes](examples.md)
- [GUI Reference — sycg](sycg-gui.md)
