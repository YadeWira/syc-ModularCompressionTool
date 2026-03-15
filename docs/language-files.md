# Language Files — .syl

[← Back to README](../README.md)

---

## Overview

`.syl` (SYC Language) files localize the `sycg` GUI. The format is a simple INI file with sections and key-value pairs.

The default language is English (built-in). To use a different language:

```powershell
sycg x data.syc -o dest --lang ES.syl
sycg x data.syc -o dest --lang C:\langs\FR.syl
```

If the path is relative, SYC looks for it in the same directory as `sycg.exe`.

---

## File Format

```ini
; SYC Language File - English
; Lines starting with ; are comments

[section]
key = value
```

- Sections are `[name]`
- Keys are case-insensitive
- Values are plain strings
- Template variables use `{name}` syntax

---

## Complete Key Reference

### `[window]`

| Key | Default (EN) | Description |
|---|---|---|
| `compressing` | `Compressing` | Operation label for `a` command |
| `extracting` | `Extracting` | Operation label for `x` command |
| `listing` | `Listing` | Operation label for `l` command |
| `verifying` | `Verifying` | Operation label for `t` command |
| `completed` | `Completed` | Shown when operation finishes |
| `elapsed` | `elapsed` | Suffix for elapsed time display |

### `[metrics]`

| Key | Default (EN) | Description |
|---|---|---|
| `processed` | `Processed:` | Label for processed bytes |
| `compressed` | `Compressed:` | Label for compressed bytes |
| `bytes` | `Bytes:` | Label for total input bytes |
| `elapsed` | `Elapsed:` | Label for elapsed time |
| `ratio` | `Ratio:` | Label for compression ratio |
| `speed` | `Speed:` | Label for compression speed |

### `[buttons]`

| Key | Default (EN) | Description |
|---|---|---|
| `background` | `Background` | Send to background button |
| `pause` | `Pause` | Pause button |
| `resume` | `Resume` | Resume button (after pause) |
| `cancel` | `Cancel` | Cancel button |
| `close` | `Close` | Close button (after completion) |
| `close_in` | `Close ({n}s)` | Countdown close button. `{n}` = seconds remaining |

### `[status]`

| Key | Default (EN) | Description |
|---|---|---|
| `initializing` | `Initializing...` | Status while starting |
| `done` | `✓  Completed in {time}` | Completion message. `{time}` = elapsed time |
| `error` | `✗  {msg}` | Error message. `{msg}` = error text |

### `[confirm]`

| Key | Default (EN) | Description |
|---|---|---|
| `cancel_title` | `Cancel` | Cancel confirmation dialog title |
| `cancel_msg` | `Cancel the operation?` | Cancel confirmation dialog message |

---

## Bundled Language Files

### EN.syl — English (default)

```ini
; SYC Language File - English

[window]
compressing    = Compressing
extracting     = Extracting
listing        = Listing
verifying      = Verifying
completed      = Completed
elapsed        = elapsed

[metrics]
processed      = Processed:
compressed     = Compressed:
bytes          = Bytes:
elapsed        = Elapsed:
ratio          = Ratio:
speed          = Speed:

[buttons]
background     = Background
pause          = Pause
resume         = Resume
cancel         = Cancel
close          = Close
close_in       = Close ({n}s)

[status]
initializing   = Initializing...
done           = ✓  Completed in {time}
error          = ✗  {msg}

[confirm]
cancel_title   = Cancel
cancel_msg     = Cancel the operation?
```

### ES.syl — Spanish

```ini
; SYC Language File - Español

[window]
compressing    = Comprimiendo
extracting     = Extrayendo
completed      = Completado

[buttons]
background     = Segundo plano
pause          = Pausar
resume         = Reanudar
cancel         = Cancelar
close          = Cerrar
close_in       = Cerrar ({n}s)

[confirm]
cancel_title   = Cancelar
cancel_msg     = ¿Cancelar la operación?
```

---

## Creating a New Language

1. Copy `EN.syl` and rename it (e.g. `FR.syl`)
2. Translate the values — do not change the keys
3. You only need to include keys you want to override. Missing keys fall back to English

```ini
; FR.syl - French
[buttons]
pause   = Pause
resume  = Reprendre
cancel  = Annuler
close   = Fermer
```

---

## See Also

- [GUI Reference — sycg](sycg-gui.md)
- [Examples & Recipes](examples.md)
