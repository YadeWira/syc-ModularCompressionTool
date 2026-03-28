# Language Files — .syl

[← Back to README](../README.md)

---

## Overview

`.syl` (SYC Language) files localize both `sycg` (progress window) and `psycg` (archive manager). A single `.syl` file serves both tools via separate sections.

The default language is English (built-in). To use a different language:

```powershell
# sycg: pass on command line
sycg x data.syc -o dest --lang ES.syl
sycg x data.syc -o dest --lang ES       # code only, resolved from lang/ folder

# psycg: select in Settings dialog or pass on command line
psycg --lang ES
```

---

## File Format

```ini
; SYC Language File - English
; Lines starting with ; are comments

[sycg]
window_compressing = Compressing
buttons_cancel     = Cancel

[psycg]
toolbar_open       = Open
dlg_ok             = OK
```

- Sections: `[sycg]` for the progress window, `[psycg]` for the archive manager
- Keys use `_` as separator (e.g. `window_compressing`)
- Values are plain strings
- Template variables use `{name}` syntax (e.g. `{n}`, `{time}`, `{name}`)
- Missing keys fall back to English defaults

---

## [sycg] Section Keys

### `window`

| Key | Default (EN) | Description |
|---|---|---|
| `window_compressing` | `Compressing` | Operation label for `a` |
| `window_extracting` | `Extracting` | Operation label for `x` |
| `window_listing` | `Listing` | Operation label for `l` |
| `window_verifying` | `Verifying` | Operation label for `t` |
| `window_completed` | `Completed` | Shown on completion |
| `window_elapsed` | `elapsed` | Suffix for elapsed time |

### `metrics`

| Key | Default (EN) |
|---|---|
| `metrics_processed` | `Processed:` |
| `metrics_compressed` | `Compressed:` |
| `metrics_bytes` | `Bytes:` |
| `metrics_elapsed` | `Elapsed:` |
| `metrics_ratio` | `Ratio:` |
| `metrics_speed` | `Speed:` |

### `buttons`

| Key | Default (EN) |
|---|---|
| `buttons_background` | `Background` |
| `buttons_pause` | `Pause` |
| `buttons_resume` | `Resume` |
| `buttons_cancel` | `Cancel` |
| `buttons_close` | `Close` |
| `buttons_close_in` | `Close ({n}s)` |

### `status`

| Key | Default (EN) |
|---|---|
| `status_initializing` | `Initializing...` |
| `status_done` | `✓  Completed in {time}` |
| `status_error` | `✗  {msg}` |

### `confirm`

| Key | Default (EN) |
|---|---|
| `confirm_cancel_title` | `Cancel` |
| `confirm_cancel_msg` | `Cancel the operation?` |

---

## [psycg] Section Keys (selected)

Full list — 91 keys total. Below are the most commonly translated ones:

| Key | Default (EN) |
|---|---|
| `toolbar_open` | `Open` |
| `toolbar_create` | `Create` |
| `toolbar_extract` | `Extract` |
| `toolbar_extract_to` | `Extract To` |
| `toolbar_test` | `Test` |
| `toolbar_info` | `Info` |
| `toolbar_close` | `Close` |
| `nav_no_archive` | `No archive open` |
| `nav_ready` | `Ready` |
| `nav_up` | `↑ Up` |
| `col_name` | `Name` |
| `col_original` | `Original` |
| `col_packed` | `Packed` |
| `col_ratio` | `Ratio` |
| `col_method` | `Method` |
| `dlg_ok` | `OK` |
| `dlg_cancel` | `Cancel` |
| `dlg_create` | `Create` |
| `dlg_extract` | `Extract` |
| `dlg_close` | `Close` |
| `dlg_password` | `Password required` |
| `dlg_solid` | `Solid (-tar)` |
| `dlg_encrypt` | `Encrypt` |
| `dlg_block` | `Block mode (-block)` |
| `dlg_dedup` | `Dedup (-dd)` |
| `op_compressing` | `Compressing…` |
| `op_extracting` | `Extracting…` |
| `op_testing` | `Testing integrity…` |
| `title` | `SYC Archive Manager` |
| `settings_title` | `Settings` |
| `settings_theme` | `Theme` |
| `settings_language` | `Language` |
| `settings_app_title` | `App Identity` |
| `settings_app_name` | `App name:` |
| `settings_app_icon` | `Icon (.ico / .png):` |
| `settings_app_reset` | `Reset` |

---

## Bundled Languages

| Code | Language | Keys |
|---|---|---|
| `EN` | English (default) | 91 psycg + 23 sycg |
| `ES` | Español | 91 + 23 |
| `FR` | Français | 91 + 23 |
| `PT` | Português | 91 + 23 |
| `RU` | Русский | 91 + 23 |

---

## Creating a New Language

1. Copy `EN.syl` and rename it (e.g. `DE.syl`)
2. Translate values — do not change the keys
3. Place in the `lang/` folder next to the executables
4. psycg will auto-discover it in the Settings language list

You only need to translate keys you want to override — missing keys fall back to English.

---

## Adding a New Language to LANGS

If you want the language name to appear properly (not just the code) in the Settings dropdown, add it to the `LANGS` dict in `psycg.py`:

```python
LANGS = {
    "EN": "English",
    "ES": "Español",
    "FR": "Français",
    "PT": "Português",
    "RU": "Русский",
    "DE": "Deutsch",   # ← add your language
}
```

---

## See Also

- [GUI Reference — sycg](sycg-gui.md)
- [Archive Manager — psycg](psycg-gui.md)
- [Examples & Recipes](examples.md)
