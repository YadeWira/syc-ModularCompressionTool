# Archive Format — .syc

[← Back to README](../README.md)

---

## Overview

A `.syc` file is a binary archive with a fixed header, a file index, and compressed data blocks. The format supports two modes:

- **Normal mode** — each file compressed individually
- **Solid mode** (`-tar`) — all files packed into a tar block, then the whole block is compressed

---

## Magic & Header

```
Offset  Size  Description
──────  ────  ───────────────────────────────────────
0       4     Magic: SYC\x01  (53 59 43 01)
4       1     Flags (see below)
5       2     Method name length (uint16 LE)
7       N     Method name (UTF-8)
7+N     2     Comment length (uint16 LE) — only if FLAG_COMMENT
9+N     C     Comment text (UTF-8)       — only if FLAG_COMMENT
...     ...   Index or encrypted payload
```

### Flags byte

| Bit | Value | Name | Description |
|---|---|---|---|
| 0 | `0x01` | `FLAG_TAR` | Solid mode (tar block) |
| 1 | `0x02` | `FLAG_ENC` | Data encrypted per entry |
| 2 | `0x04` | `FLAG_FULL_ENC` | Header + data encrypted (full) |
| 3 | `0x08` | `FLAG_CRC32` | CRC32 per file |
| 4 | `0x10` | `FLAG_MD5` | MD5 per file |
| 5 | `0x20` | `FLAG_COMMENT` | Archive comment present |

---

## File Index

Immediately after the header (or encrypted, if `FLAG_FULL_ENC`):

```
4 bytes   Number of files (uint32 LE)

For each file:
  2 bytes   Name length (uint16 LE)
  N bytes   File name (UTF-8)
  8 bytes   Original size (uint64 LE)
  8 bytes   Compressed size (uint64 LE) — 0 in solid mode
  4 bytes   CRC32 (uint32 LE) — only if FLAG_CRC32
  16 bytes  MD5  (bytes)      — only if FLAG_MD5
  M bytes   Compressed data   — only in normal mode, absent in solid/full-enc
```

---

## Normal Mode Layout

```
[Magic][Flags][Method]
[NumFiles]
  [Name][OrigSize][CompSize][CRC32?][MD5?][CompressedData]
  [Name][OrigSize][CompSize][CRC32?][MD5?][CompressedData]
  ...
```

Each file's data is compressed independently with the full method chain.

---

## Solid Mode Layout (FLAG_TAR)

```
[Magic][Flags][Method]
[NumFiles]
  [Name][OrigSize][0][CRC32?][MD5?]   ← no data here
  ...
[TarOriginalSize  8 bytes]
[TarCompressedSize 8 bytes]
[CompressedTarBlock]                  ← all files in one tar, then compressed
```

---

## Encrypted Mode (FLAG_ENC)

In normal (non-tar) mode, each file's compressed data is encrypted individually. The index stores the **encrypted size** (not the original compressed size). Header and file names are in plaintext.

```
[Magic][Flags][Method][Comment?]
[NumFiles]
  [Name][OrigSize][EncryptedSize][CRC32?][MD5?][EncryptedData]
  [Name][OrigSize][EncryptedSize][CRC32?][MD5?][EncryptedData]
  ...
```

In solid (tar) mode with `FLAG_ENC`, the tar block is encrypted as a single blob.

## Full Encrypted Mode (FLAG_FULL_ENC)

```
[Magic][Flags][Method]
[EncryptedPayloadSize  8 bytes]
[EncryptedPayload]     ← contains the entire index + tar block
```

The payload is a single encrypted blob. File names are hidden.

---

## Encryption Format

Each encrypted blob has its own header:

```
1 byte    Algorithm: 0x01=AES-256-GCM, 0x02=ChaCha20-Poly1305
16 bytes  Salt (random, for PBKDF2)
12 bytes  Nonce (random)
N bytes   Ciphertext + 16-byte authentication tag
```

Key derivation: PBKDF2-HMAC-SHA256, 100,000 iterations, 32-byte key.

---

## Multi-Part Archives

### Part 1 (full header + first data fragment)

```
[Magic SYC\x01][Flags][Method]
[NumFiles][File index...]
[4 bytes]  Total number of parts (uint32 LE)
[8 bytes]  Total original size
[8 bytes]  Total compressed size
[Fragment data]
```

### Parts 2..N (data fragments only)

```
[Magic SYCp]      (53 59 43 70)
[4 bytes]  Part number (uint32 LE, 1-based)
[4 bytes]  Total parts (uint32 LE)
[Fragment data]
```

---

## See Also

- [CLI Reference — syc](syc-cli.md)
- [syc.ini Configuration](syc-ini.md)