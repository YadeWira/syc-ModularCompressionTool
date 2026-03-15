# GUI Reference — sycg

[← Back to README](../README.md)

---

## Overview

`sycg` is a GUI wrapper for `syc`. It launches `syc.exe` as a background process and displays a progress window with real-time metrics.

`sycg.exe` must be in the same directory as `syc.exe`.

---

## Usage

```powershell
sycg <syc-command> <archive> [syc-options] [sycg-options]
```

All standard `syc` flags work normally. The sycg-exclusive flags listed below are intercepted and never passed to `syc`.

---

## sycg-exclusive Flags

### `--title "Text"`

Sets a custom window title instead of the default `SYC — Compressing archive.syc`.

```powershell
sycg x data.syc -o dest --title "Installing My App v1.0"
```

---

### `--icon file.ico`

Sets a custom icon in the title bar.

- `.ico` files require **Pillow** (`pip install pillow`)
- `.png` files work without any extra dependency

```powershell
sycg x data.syc -o dest --icon myapp.ico
```

---

### `--theme dark|white|auto`

Sets the UI color theme.

| Value | Description |
|---|---|
| `dark` | Dark background, light text |
| `white` | Light background, dark text |
| `auto` | Reads Windows dark/light mode from registry (default) |

```powershell
sycg x data.syc -o dest --theme white
```

---

### `--lang file.syl`

Loads a language file for the UI. Default is English (built-in).

```powershell
sycg x data.syc -o dest --lang ES.syl
```

See [Language Files (.syl)](language-files.md) for the format.

---

### `--close`

Automatically closes the window 3 seconds after successful completion.
The button shows a countdown: `Close (3s)` → `Close (2s)` → `Close (1s)`.

```powershell
sycg x data.syc -o dest --close
```

---

### `--nocancel`

Disables the Cancel button and the title bar close button (`✕`) while the operation is running.

---

### `--nopause`

Disables the Pause button.

---

### `--nobackground`

Disables the Background button.

---

## InnoSetup Integration

For use inside an InnoSetup `[Run]` section:

```iss
[Run]
Filename: "{tmp}\sycg.exe";
Parameters: "x ""{tmp}\data.syc"" -o ""{app}"" --nocancel --nopause --nobackground --close --lang ""{tmp}\ES.syl"" --title ""Installing {#MyAppName}""";
Flags: waituntilterminated;
```

`sycg.exe` compiled with console support blocks until completion, so `waituntilterminated` works correctly.

---

## Window Layout

```
┌─────────────────────────────────────────────┐
│ [icon] SYC — Compressing archive.syc    — ✕ │  ← Custom title bar (draggable)
├─────────────────────────────────────────────┤
│ Compressing — 66%                  0:00:14  │  ← Operation + % + elapsed
├─────────────────────────────────────────────┤
│ Processed:  126.9 MB   Compressed: 142.5 MB │
│ Bytes:      359.8 MB   Elapsed:    0:00:14  │  ← Metrics grid
│ Ratio:      60.4%      Speed:      43.2 MB/s│
│                                             │
│ [+] zpaqfranz:-ssd:-t0:-m1 (tempfile)       │  ← Current step
│ ████████████████████░░░░░░░░░░░░░░          │  ← Progress bar
│ 66%                                         │
├─────────────────────────────────────────────┤
│ Background    Pause               Cancel    │  ← Buttons
└─────────────────────────────────────────────┘
```

On completion, a status bar appears above the buttons:

```
  ✓  Completed in 0:00:25   359.8 MB → 142.5 MB  (60.4%)
```

---

## See Also

- [CLI Reference — syc](syc-cli.md)
- [Language Files (.syl)](language-files.md)
- [Examples & Recipes](examples.md)
