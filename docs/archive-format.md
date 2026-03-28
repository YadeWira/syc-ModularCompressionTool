# Archive Format — .syc

[← Back to README](../README.md)

---

## Overview

A `.syc` file is a binary archive with a fixed header, a file index, and compressed data blocks. Supports four modes:

| Mode | Flag | Description |
|---|---|---|
| **Normal** | — | Each file compressed individually |
| **Solid** | `FLAG_TAR` | All files in one tar block, then compressed |
| **Multiblock** | `FLAG_TAR + FLAG_MULTIBLOCK` | Solid tar split into independent compressed blocks |
| **Dedup** | `FLAG_DEDUP` | Chunk-level deduplication, then compressed |

---

## Magic & Header

```
Offset  Size  Description
──────  ────  ───────────────────────────────────────────────────
0       4     Magic: SYC\x01  (53 59 43 01)
4       1     Flags byte (see below)
5       2     Method name length (uint16 LE)
7       N     Method name (UTF-8)
7+N     2     Comment length (uint16 LE)  ← only if FLAG_COMMENT
9+N     C     Comment text (UTF-8)        ← only if FLAG_COMMENT
...     ...   Index or encrypted payload
```

### Flags byte

| Bit | Value | Name | Description |
|---|---|---|---|
| 0 | `0x01` | `FLAG_TAR` | Solid mode (tar block) |
| 1 | `0x02` | `FLAG_ENC` | Data encrypted |
| 2 | `0x04` | `FLAG_FULL_ENC` | Header + data encrypted |
| 3 | `0x08` | `FLAG_CRC32` | CRC32 per file |
| 4 | `0x10` | `FLAG_MD5` | MD5 per file |
| 5 | `0x20` | `FLAG_COMMENT` | Archive comment present |
| 6 | `0x40` | `FLAG_MULTIBLOCK` | Tar split into ≥2 independent blocks |
| 7 | `0x80` | `FLAG_DEDUP` | Deduplication mode |

> `FLAG_MULTIBLOCK` is only set when there are 2 or more blocks. A single-block solid archive uses `FLAG_TAR` alone.

---

## Normal Mode Layout

```
[Magic][Flags][Method][Comment?]
[NumFiles : uint32]
  [NameLen : uint16][Name : UTF-8]
  [OrigSize : uint64]
  [CompSize : uint64]
  [CRC32 : uint32]    ← only if FLAG_CRC32
  [MD5 : 16 bytes]    ← only if FLAG_MD5
  [CompressedData : CompSize bytes]
  ...
```

Each file's data is compressed independently through the full method chain.

---

## Solid Mode Layout (FLAG_TAR, single block)

```
[Magic][Flags][Method][Comment?]
[NumFiles]
  [Name][OrigSize][0 : uint64][CRC32?][MD5?]   ← CompSize = 0 (no data here)
  ...
[TarOriginalSize  : uint64]
[TarCompressedSize : uint64]
[CompressedTarBlock]
```

---

## Multiblock Solid Layout (FLAG_TAR + FLAG_MULTIBLOCK)

Used when `-block SIZE` is specified. Each block is a separate tar compressed independently.

```
[Magic][Flags][Method][Comment?]
[NumFiles]
  [Name][OrigSize][0][CRC32?][MD5?]
  ...
[NumBlocks : uint32]
  [BlockOrigSize : uint64]
  [BlockCompSize : uint64]
  [CompressedBlock : BlockCompSize bytes]
  [BlockOrigSize : uint64]
  [BlockCompSize : uint64]
  [CompressedBlock : BlockCompSize bytes]
  ...
```

Each block is decompressed independently during extraction — no need to decompress the whole archive to access any block.

---

## Deduplication Mode Layout (FLAG_DEDUP)

Used when `-dd` is specified. The index stores chunk ID lists per file, and the chunk store holds unique chunks (compressed).

```
[Magic][Flags][Method][Comment?]
[NumFiles : uint32]
  [NameLen : uint16][Name : UTF-8]
  [OrigSize : uint64]
  [NumChunkIds : uint32]
  [ChunkId : uint32] × NumChunkIds
  ...

; Chunk store (single blob, FLAG_MULTIBLOCK not set):
[NumChunks : uint32]
[StoreOrigSize : uint64]
[StoreCompSize : uint64]
[CompressedChunkBlob : StoreCompSize bytes]

; Or multi-block store (FLAG_DEDUP + FLAG_MULTIBLOCK):
[NumBlocks : uint32]
  [NumChunks : uint32]
  [BlockOrigSize : uint64]
  [BlockCompSize : uint64]
  [CompressedBlob : BlockCompSize bytes]
  ...
```

**Chunk blob format** (after decompression):
```
For each chunk:
  [ChunkSize : uint32]
  [ChunkData : ChunkSize bytes]
```

---

## Encrypted Mode (FLAG_ENC)

In normal mode: each entry's compressed data is individually encrypted. The index stores the encrypted size.

In solid/multiblock mode: each tar block is individually encrypted.

---

## Full Encrypted Mode (FLAG_FULL_ENC)

```
[Magic][Flags][Method][Comment?]
[EncryptedPayloadSize : uint64]
[EncryptedPayload]     ← entire index + data encrypted as one blob
```

File names are completely hidden.

---

## Encryption Blob Format

Each encrypted blob (whether per-entry, per-block, or the full payload) starts with:

```
1 byte    Algorithm: 0x01 = AES-256-GCM,  0x02 = ChaCha20-Poly1305
16 bytes  Salt (random, for PBKDF2)
12 bytes  Nonce (random)
N bytes   Ciphertext + 16-byte authentication tag
```

Key derivation: **PBKDF2-HMAC-SHA256**, 100,000 iterations, 32-byte key.

---

## Multi-Part Archives

### Part 1

```
[Magic SYC\x01][Flags][Method]
[NumFiles][File index...]
[NumParts : uint32]
[TotalOrigSize : uint64]
[TotalCompSize : uint64]
[Fragment data]
```

### Parts 2..N

```
[Magic SYCp]   (53 59 43 70)
[PartNumber : uint32]  (1-based)
[TotalParts : uint32]
[Fragment data]
```

---

## See Also

- [CLI Reference — syc](syc-cli.md)
- [syc.ini Configuration](syc-ini.md)
