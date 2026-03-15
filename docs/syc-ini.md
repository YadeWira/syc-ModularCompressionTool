# syc.ini Configuration

[← Back to README](../README.md)

---

## Overview

`syc.ini` uses the same format as FreeArc's `arc.ini`. It has two types of sections:

- `[Compression methods]` — aliases that map a short name to a full compressor chain
- `[External compressor:name]` — definition of each external compressor

---

## Compression Methods

```ini
[Compression methods]

; Simple alias
z22 = zstd:--ultra:-22

; Chain of compressors
xpszx = xprecomp+srep:-m5f:-a0+zstd:--ultra:-22

; Chain with zpaqfranz
xpszf1 = xprecomp+srep:-m5f:-a0+zpaqfranz:-ssd:-t0:-m1
```

### Chain syntax

```
compressor1:opt1:opt2+compressor2:opt1+compressor3
```

- Compressors separated by `+`
- Options separated by `:` instead of spaces
- Prefix flags with `-`: `srep:-m5f:-a0` → runs `srep -m5f -a0`

---

## External Compressor Definition

```ini
[External compressor:name]
header     = 0
packcmd    = path\to\compressor.exe {options} <stdin> <stdout>
unpackcmd  = path\to\compressor.exe -d <stdin> <stdout>
packedfile = $$arcpackedfile$$.ext   ; optional, for file-based compressors
datafile   = $$arcdatafile$$.ext     ; optional
```

### Fields

| Field | Description |
|---|---|
| `header` | Header bytes to skip (usually `0`) |
| `default` | Default options for `{options}` when none specified in the method chain |
| `packcmd` | Command to compress |
| `unpackcmd` | Command to decompress |
| `packedfile` | Custom packed file name (for compressors that write to a file) |
| `datafile` | Custom data file name |

### Placeholders

| Placeholder | Replaced with |
|---|---|
| `{options}` | Options from the method chain (space-separated) |
| `{compressor}` | The compressor name |
| `<stdin>` | Marks stdin as input |
| `<stdout>` | Marks stdout as output |
| `$$arcdatafile$$.ext` | Input data temp file path |
| `$$arcpackedfile$$.ext` | Output packed temp file path |

---

## The `default` Field

The `default` field defines the options substituted into `{options}` when the method chain does not specify any options for that compressor.

```ini
[External compressor:xprecomp]
header    = 0
default   = -c256mb -t100p -d3 -dd
packcmd   = xtool\xtool.exe precomp {options} - $$arcpackedfile$$.tmp <stdin>
unpackcmd = xtool\xtool.exe decode - - <stdin> <stdout>
```

**When `default` is used** — no options in the chain:
```ini
xpszx = xprecomp+srep+zstd
; xprecomp has no options → {options} = "-c256mb -t100p -d3 -dd"
```

**When `default` is ignored** — explicit options take priority:
```ini
xpszx_fast = xprecomp:-c128mb:-t50p+srep+zstd
; explicit options → {options} = "-c128mb -t50p", default ignored
```

Summary of `{options}` resolution:

| Situation | Result |
|---|---|
| Explicit options in chain (`xprecomp:-c128mb`) | Uses explicit options |
| No options + `default` defined | Uses `default` value |
| No options + no `default` | Empty string |


---

## Execution Modes

SYC auto-detects the mode from the command template:

| Mode | Condition | Example |
|---|---|---|
| `stdio` | Has `<stdin>` and/or `<stdout>`, no `$$` vars | zstd, lz4, xprecomp decode |
| `mixed` | Has `<stdin>` + `$$arcpackedfile$$` | xprecomp pack |
| `tempfile` | Has `$$arcdatafile$$` + `$$arcpackedfile$$` | srep, zpaqfranz |

---

## Built-in Compressors (example syc.ini)

### stdio compressors (pipe-based)

```ini
[External compressor:zstd]
header    = 0
packcmd   = compressors\zstd.exe {options} <stdin> <stdout>
unpackcmd = compressors\zstd.exe -d <stdin> <stdout>

[External compressor:lz4]
header    = 0
packcmd   = compressors\lz4.exe {options} <stdin> <stdout>
unpackcmd = compressors\lz4.exe -d <stdin> <stdout>
```

### Mixed mode (stdin → file)

```ini
[External compressor:xprecomp]
header    = 0
packcmd   = xtool\xtool.exe precomp -mzlib+preflate+png+brunsli -c256mb -t100p -d3 -dd - $$arcpackedfile$$.tmp <stdin>
unpackcmd = xtool\xtool.exe decode -t75p - - <stdin> <stdout>
```

### Tempfile compressors (file → file)

```ini
[External compressor:srep]
header    = 0
packcmd   = compressors\srep.exe {options} $$arcdatafile$$.tmp $$arcpackedfile$$.tmp
unpackcmd = compressors\srep.exe -d - - <stdin> <stdout>
```

### zpaqfranz (special case)

zpaqfranz stores files without their full path (`-nopath`) and extracts to the working directory:

```ini
[External compressor:zpaqfranz]
header     = 0
packcmd    = compressors\zpaqfranz.exe a $$arcpackedfile$$.zpaq $$arcdatafile$$.tmp {options} -nopath
unpackcmd  = compressors\zpaqfranz.exe x $$arcpackedfile$$.zpaq -t0 -space -noeta
packedfile = $$arcpackedfile$$.zpaq
```

> **Important:** `-nopath` is required. Without it, zpaqfranz stores the full temp path inside the archive and extraction fails.

---

## Recommended Methods

| Alias | Chain | Speed | Ratio |
|---|---|---|---|
| `z22` | zstd lvl 22 | ★★★★★ | ★★★ |
| `sz22` | srep + zstd | ★★★★ | ★★★★ |
| `xpszx` | xprecomp + srep + zstd | ★★★ | ★★★★ |
| `xpszf1` | xprecomp + srep + zpaqfranz m1 | ★★ | ★★★★★ |
| `xpszfx` | xprecomp + srep + zpaqfranz m5 | ★ | ★★★★★★ |

---

## See Also

- [CLI Reference — syc](syc-cli.md)
- [Archive Format (.syc)](archive-format.md)
- [Examples & Recipes](examples.md)
