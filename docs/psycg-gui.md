# Archive Manager — psycg

[← Back to README](../README.md)

---

## Overview

`psycg` is a full GUI archive manager in the style of WinRAR or 7-Zip. It lets you open, browse, create, and extract `.syc` archives without using the command line.

---

## Usage

```powershell
# Open manager (empty)
psycg

# Open manager with a specific archive
psycg backup.syc

# With theme and language
psycg backup.syc --theme white --lang ES
```

---

## CLI Flags

| Flag | Description |
|---|---|
| `file` | Optional `.syc` archive to open on startup |
| `--theme dark\|white\|auto` | UI theme. `auto` reads Windows dark/light mode from registry |
| `--lang CODE\|FILE` | Language code (`EN`, `ES`, `FR`, `PT`, `RU`) or path to a `.syl` file |

---

## Toolbar

| Button | Shortcut | Description |
|---|---|---|
| 📂 Open | `Ctrl+O` | Open a `.syc` archive |
| 📦 Create | `Ctrl+N` | Create a new archive |
| 📤 Extract | — | Extract selected files to archive folder |
| 📋 Extract To | — | Extract selected files with destination dialog |
| ✓ Test | — | Verify archive integrity |
| ℹ Info | — | Show archive properties |
| ✕ Close | `Delete` | Close current archive |
| ⚙ Settings | — | Open Settings dialog |

---

## Keyboard Shortcuts

| Key | Action |
|---|---|
| `Ctrl+O` | Open archive |
| `Ctrl+N` | Create archive |
| `F5` | Reload archive from disk |
| `Delete` | Close archive |
| `Backspace` / `Alt+←` | Navigate up one folder level |
| `Ctrl+A` | Select all visible items |

---

## Navigation

- **Double-click folder** — navigate into it (tree shows children)
- **↑ Up button** — go up one level
- **Path bar** — shows current archive path and folder path
- **Search box** — filter the file list in real time (right side of path bar)

---

## File Tree

The tree shows folders and files hierarchically. Folders are lazy-loaded — children are only fetched when you expand them, so large archives with thousands of entries open instantly.

**Columns:**
- **Name** — file or folder name
- **Original** — uncompressed size
- **Packed** — compressed size (estimated proportionally for solid/dedup archives)
- **Ratio** — compression ratio
- **Method** — compression method used

---

## Context Menu

Right-click on any item:

| Item | Description |
|---|---|
| Extract selected | Extract to archive folder |
| Extract selected to… | Extract with destination dialog |
| Copy name | Copy the full archive path to clipboard |
| Select all | Select all visible items |

---

## Create Archive Dialog

Accessible via 📦 Create or `Ctrl+N`. Lets you pick:

- **Archive path** — destination `.syc` file
- **Method** — from methods defined in `syc.ini`
- **Solid** (`-tar`) — pack all files into one tar before compressing
- **CRC32 / MD5** — store checksums per file
- **Split** (`-chunk`) — split into fixed-size parts
- **Block mode** (`-block`) — split solid tar into independent blocks
- **Dedup** (`-dd`) — chunk-level deduplication
- **Encryption** — AES-256 or ChaCha20, optional "hide filenames"
- **Password** — encryption password

---

## Extract Dialog

- **Destination folder** — where to extract files
- **Overwrite** — Always / Skip / Ask

---

## Archive Properties (Info)

Shows:
- File path, archive size on disk
- Compression method and mode (normal / solid tar / multiblock / dedup)
- Number of files, total original size, total compressed size, ratio
- Comment (if any)
- Encryption status

---

## Settings

### Theme

| Value | Description |
|---|---|
| Dark | Dark background (default) |
| Light | Light background |
| Auto | Reads Windows setting from registry |

> Theme changes require a restart.

### Language

Discovers all `.syl` files in the `lang/` folder. Switch live — no restart needed.

### App Identity

| Field | Description |
|---|---|
| App name | Replaces "SYC Archive Manager" in the title bar and taskbar |
| Icon | Custom icon (`.ico` or `.png`). Shown in title bar, taskbar, and alt-tab. |
| Reset | Clears name and icon back to defaults |

Settings are saved to `psycg.cfg` next to the executable and applied on the next launch.

**Icon notes:**
- Windows context menus only support `.ico` — `.png` works in the title bar but not in the system tray or context menus
- When psycg launches sycg (for compress/extract operations), the configured icon is passed via `--icon` so both windows show the same icon

---

## Drag & Drop

If `tkinterdnd2` is installed (`pip install tkinterdnd2`), you can drag `.syc` files onto the window to open them. If `tkinterdnd2` is not installed, drag & drop is silently disabled.

---

## Configuration File — psycg.cfg

Stored next to the executable. Keys:

```ini
theme     = auto         ; dark / white / auto
lang      = EN           ; language code
app_name  =              ; custom app name (empty = default)
app_icon  =              ; path to .ico or .png (empty = generated icon)
```

---

## See Also

- [CLI Reference — syc](syc-cli.md)
- [GUI Reference — sycg](sycg-gui.md)
- [Language Files (.syl)](language-files.md)
- [Examples & Recipes](examples.md)
