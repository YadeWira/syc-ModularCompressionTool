"""
psycg.py - SYC Archive Manager
GUI completa al estilo WinRAR/7-Zip para archivos .syc
Misma paleta y estilo que sycg.py
"""
import sys, os, subprocess, threading, tempfile, shutil, struct
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

# ── Palette (matches sycg.py exactly) ─────────────────────────────────────────
THEMES = {
    "dark": dict(
        BG="#1C1C1C", BG2="#252525", BG3="#2E2E2E", BG4="#333333", BG5="#3A3A3A",
        FG="#D8D8D8", DIM="#666666",
        GREEN="#5DC85D", BLUE="#4B9EE8", YELLOW="#DDB84A", RED="#D95F5F",
        BLUE_DIM="#1E3A5F",
        TB="#111111", TB_FG="#888888",
        SEL="#1E3A5F", SEL_FG="#D8D8D8",
        BORDER="#3A3A3A", BORDER_LIGHT="#444444",
        SHADOW="#111111", HIGHLIGHT="#383838",
    ),
    "white": dict(
        BG="#F5F5F5", BG2="#E8E8E8", BG3="#DCDCDC", BG4="#D0D0D0", BG5="#C4C4C4",
        FG="#1A1A1A", DIM="#888888",
        GREEN="#2E7D32", BLUE="#1565C0", YELLOW="#F57F17", RED="#C62828",
        BLUE_DIM="#C8DDEE",
        TB="#D0D0D0", TB_FG="#444444",
        SEL="#C8DDEE", SEL_FG="#1A1A1A",
        BORDER="#BBBBBB", BORDER_LIGHT="#CACACA",
        SHADOW="#AAAAAA", HIGHLIGHT="#F0F0F0",
    ),
}

# ── Language support (.syl files) ────────────────────────────────────────────
LANGS = {
    "EN": "English",
    "ES": "Español",
    "FR": "Français",
    "PT": "Português",
    "RU": "Русский",
}

class SylParser:
    """Parse .syl language files (same format as sycg.py)"""
    _DEFAULTS = {
        "toolbar.open":       "Open",
        "toolbar.create":     "Create",
        "toolbar.extract":    "Extract",
        "toolbar.extract_to": "Extract To",
        "toolbar.test":       "Test",
        "toolbar.info":       "Info",
        "toolbar.close":      "Close",
        "nav.no_archive":     "No archive open",
        "nav.files":          "{n} files",
        "nav.ready":          "Ready",
        "nav.opened":         "Opened: {name}",
        "nav.done":           "Done ✓",
        "nav.error":          "Error",
        "nav.loading":        "Loading…",
        "nav.up":             "↑ Up",
        "col.name":           "Name",
        "col.original":       "Original",
        "col.packed":         "Packed",
        "col.ratio":          "Ratio",
        "col.method":         "Method",
        "dlg.open_title":     "Open SYC Archive",
        "dlg.create_title":   "Create Archive",
        "dlg.extract_title":  "Extract To",
        "dlg.props_title":    "Archive Properties",
        "dlg.password":       "Password required",
        "dlg.arc_path":       "Archive path:",
        "dlg.method":         "Method:",
        "dlg.dest":           "Destination folder:",
        "dlg.overwrite":      "Overwrite:",
        "dlg.ow_always":      "Always",
        "dlg.ow_skip":        "Skip",
        "dlg.ow_ask":         "Ask",
        "dlg.ok":             "OK",
        "dlg.cancel":         "Cancel",
        "dlg.create":         "Create",
        "dlg.extract":        "Extract",
        "dlg.close":          "Close",
        "dlg.browse":         "...",
        "dlg.solid":          "Solid (-tar)",
        "dlg.split":          "Split (-chunk)",
        "dlg.split_hint":     "e.g. 700MB, 4GB, 500KB",
        "dlg.encrypt":        "Encrypt",
        "dlg.pass_label":     "Password (if encrypted):",
        "prop.path":          "Path:",
        "prop.size":          "Size:",
        "prop.method":        "Method:",
        "prop.mode":          "Mode:",
        "prop.files":         "Files:",
        "prop.original":      "Original:",
        "prop.packed":        "Packed:",
        "prop.ratio":         "Ratio:",
        "prop.comment":       "Comment:",
        "prop.encrypted":     "Encrypted:",
        "prop.yes":           "Yes",
        "prop.solid_tar":     "solid tar",
        "prop.normal":        "normal",
        "ctx.extract_sel":    "Extract selected",
        "ctx.extract_to":     "Extract selected to…",
        "ctx.copy_name":      "Copy name",
        "ctx.select_all":     "Select all",
        "op.compressing":     "Compressing…",
        "op.extracting":      "Extracting…",
        "op.testing":         "Testing integrity…",
        "op.failed":          "Operation failed",
        "err.no_methods":     "No compression methods found in syc.ini",
        "err.invalid":        "Not a valid .syc file",
        "title":              "SYC Archive Manager",
        "settings.title":       "Settings",
        "settings.theme":       "Theme",
        "settings.theme_dark":  "Dark",
        "settings.theme_white": "Light",
        "settings.theme_auto":  "Auto (system)",
        "settings.language":    "Language",
        "settings.lang_note":   "Place .syl files in the lang/ folder to add more languages.",
        "settings.restart_note":"Restart to apply theme changes.",
        # New in v0.1.1
        "dlg.block":          "Block mode (-block)",
        "dlg.block_hint":     "e.g. 256MB, 512MB, 1GB",
        "dlg.dedup":          "Dedup (-dd)",
        "dlg.dedup_hint":     "chunk size, e.g. 1MB, 4MB",
        "prop.dedup":         "dedup",
        "prop.multiblock":    "multiblock tar",
        "dlg.full_enc":       "Hide filenames",
        # App identity
        "settings.app_title":    "App Identity",
        "settings.app_name":     "App name:",
        "settings.app_name_hint":"Leave blank to use default",
        "settings.app_icon":     "Icon (.ico / .png):",
        "settings.app_icon_hint":"Leave blank to use default",
        "settings.app_reset":    "Reset",

    }

    def __init__(self):
        self._d = dict(self._DEFAULTS)

    def load(self, path):
        if not path or not os.path.exists(path):
            return
        section = ""
        try:
            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith(";"):
                        continue
                    if line.startswith("[") and line.endswith("]"):
                        section = line[1:-1].lower()
                        continue
                    if "=" in line:
                        k, _, v = line.partition("=")
                        k = k.strip()
                        v = v.strip()
                        # psycg section: key "toolbar_open" maps to "toolbar.open"
                        if section == "psycg":
                            # "toolbar_open" -> "toolbar.open"
                            # "settings_title" -> "settings.title"
                            dot_key = k.replace("_", ".", 1)
                            self._d[dot_key] = v
                        else:
                            self._d[f"{section}.{k}"] = v
        except Exception:
            pass

    def t(self, key, **kw):
        val = self._d.get(key, self._DEFAULTS.get(key, key))
        for k, v in kw.items():
            val = val.replace("{" + k + "}", str(v))
        return val

_lang = SylParser()  # global lang instance

# ── Config (psycg.cfg) ────────────────────────────────────────────────────────
def _here():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def _lang_dir():
    """Returns path to lang/ folder, falls back to _here()"""
    p = os.path.join(_here(), "lang")
    return p if os.path.isdir(p) else _here()


def _syl_path(code):
    """Returns full path to a .syl file by code (e.g. 'ES')"""
    for base in [_lang_dir(), _here()]:
        p = os.path.join(base, code.upper() + ".syl")
        if os.path.exists(p):
            return p
    return None



class Config:
    """Read/write psycg.cfg next to the executable"""
    _DEFAULTS = {"theme": "auto", "lang": "EN", "app_name": "", "app_icon": ""}

    def __init__(self):
        self._path = os.path.join(_here(), "psycg.cfg")
        self._d    = dict(self._DEFAULTS)
        self._load()

    def _load(self):
        if not os.path.exists(self._path):
            return
        try:
            with open(self._path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith(";") or line.startswith("#"):
                        continue
                    if "=" in line:
                        k, _, v = line.partition("=")
                        self._d[k.strip()] = v.strip()
        except Exception:
            pass

    def save(self):
        try:
            with open(self._path, "w", encoding="utf-8") as f:
                f.write("; psycg.cfg - SYC Archive Manager configuration\n")
                f.write("; This file is auto-generated. You can edit it manually.\n\n")
                for k, v in self._d.items():
                    f.write(f"{k} = {v}\n")
        except Exception:
            pass

    def get(self, key, default=None):
        return self._d.get(key, default if default is not None
                           else self._DEFAULTS.get(key, ""))

    def set(self, key, value):
        self._d[key] = str(value)

_cfg = Config()

F  = ("Consolas", 9)
FB = ("Consolas", 9, "bold")
FS = ("Consolas", 8)
FL = ("Consolas", 10)

def detect_theme():
    try:
        import winreg
        k = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                           r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
        val, _ = winreg.QueryValueEx(k, "AppsUseLightTheme")
        return "white" if val == 1 else "dark"
    except Exception:
        return "dark"


def _syc_exe():
    here = _here()
    for name in ["syc.exe", "syc_x64.exe", "syc_x86.exe"]:
        p = os.path.join(here, name)
        if os.path.exists(p):
            return p
    return None  # fall back to python syc.py


def _run_syc(args, **kwargs):
    exe = _syc_exe()
    here = _here()
    if exe:
        cmd = [exe] + args
    else:
        cmd = [sys.executable, os.path.join(here, "syc.py")] + args
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    return subprocess.run(cmd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace",
                          creationflags=flags, env=env, **kwargs)


def _fmt_size(n):
    if n < 0:               return "—"
    if n < 1024:            return f"{n} B"
    if n < 1024**2:         return f"{n/1024:.1f} KB"
    if n < 1024**3:         return f"{n/1024**2:.1f} MB"
    if n < 1024**4:         return f"{n/1024**3:.2f} GB"
    return                         f"{n/1024**4:.2f} TB"


# ── Read archive metadata without syc.exe ─────────────────────────────────────
def _read_archive(path, password=None):
    """Returns dict with keys: method, tar_mode, comment, entries[]"""
    MAGIC = b"SYC\x01"
    FLAG_TAR      = 0x01
    FLAG_ENC      = 0x02
    FLAG_FULL_ENC = 0x04
    FLAG_CRC32    = 0x08
    FLAG_MD5      = 0x10
    FLAG_COMMENT    = 0x20
    FLAG_MULTIBLOCK = 0x40
    FLAG_DEDUP      = 0x80

    with open(path, "rb") as f:
        magic = f.read(4)
        if magic != MAGIC:
            raise ValueError("Not a valid .syc file")
        flags      = struct.unpack("<B", f.read(1))[0]
        method_len = struct.unpack("<H", f.read(2))[0]
        method     = f.read(method_len).decode("utf-8")

        tar_mode    = bool(flags & FLAG_TAR)
        full_enc    = bool(flags & FLAG_FULL_ENC)
        enc         = bool(flags & FLAG_ENC)
        has_crc     = bool(flags & FLAG_CRC32)
        has_md5     = bool(flags & FLAG_MD5)
        has_comment = bool(flags & FLAG_COMMENT)
        multiblock  = bool(flags & FLAG_MULTIBLOCK)
        dedup_mode  = bool(flags & FLAG_DEDUP)

        comment = ""
        if has_comment:
            clen    = struct.unpack("<H", f.read(2))[0]
            comment = f.read(clen).decode("utf-8")

        entries = []
        if full_enc:
            # Can't read index without password
            return dict(method=method, tar_mode=tar_mode, comment=comment,
                        entries=[], encrypted=True, full_enc=True,
                        dedup_mode=dedup_mode, multiblock=multiblock)

        num = struct.unpack("<I", f.read(4))[0]
        for _ in range(num):
            nlen = struct.unpack("<H", f.read(2))[0]
            name = f.read(nlen).decode("utf-8")
            orig = struct.unpack("<Q", f.read(8))[0]
            if dedup_mode:
                # Dedup format: num_chunk_ids (4) + chunk_ids (N*4)
                # We don't need the ids, just skip them
                num_cids = struct.unpack("<I", f.read(4))[0]
                f.seek(num_cids * 4, 1)
                entries.append(dict(name=name, orig=orig, comp=0, crc=None))
            else:
                comp = struct.unpack("<Q", f.read(8))[0]
                crc  = struct.unpack("<I", f.read(4))[0] if has_crc else None
                md5  = f.read(16)                         if has_md5 else None
                if not tar_mode and not full_enc:
                    skip = comp
                    f.seek(skip, 1)
                entries.append(dict(name=name, orig=orig, comp=comp, crc=crc))

        tar_orig = tar_comp = 0
        if tar_mode:
            if multiblock:
                # Read num_blocks and sum their sizes
                num_blocks = struct.unpack("<I", f.read(4))[0]
                for _ in range(num_blocks):
                    bo = struct.unpack("<Q", f.read(8))[0]
                    bc = struct.unpack("<Q", f.read(8))[0]
                    tar_orig += bo
                    tar_comp += bc
                    f.seek(bc, 1)  # skip block data
            else:
                tar_orig = struct.unpack("<Q", f.read(8))[0]
                tar_comp = struct.unpack("<Q", f.read(8))[0]
            # Distribute proportionally
            total_orig = sum(e["orig"] for e in entries) or 1
            for e in entries:
                e["comp"] = int(tar_comp * (e["orig"] / total_orig))
        elif dedup_mode:
            # Read dedup index: entries already read, now read store blobs
            num_entries = len(entries)
            # Re-read entries: dedup format has chunk_ids, not orig/comp
            # We already read them as name+orig+comp but comp=num_chunk_ids in dedup
            # Just read the store to get total compressed size
            is_block = multiblock
            total_store_comp = 0
            total_store_orig = 0
            if is_block:
                nb = struct.unpack("<I", f.read(4))[0]
                for _ in range(nb):
                    n_chunks = struct.unpack("<I", f.read(4))[0]
                    bo = struct.unpack("<Q", f.read(8))[0]
                    bc = struct.unpack("<Q", f.read(8))[0]
                    total_store_orig += bo
                    total_store_comp += bc
                    f.seek(bc, 1)
            else:
                n_chunks = struct.unpack("<I", f.read(4))[0]
                bo = struct.unpack("<Q", f.read(8))[0]
                bc = struct.unpack("<Q", f.read(8))[0]
                total_store_orig = bo
                total_store_comp = bc
            tar_orig = total_store_orig
            tar_comp = total_store_comp
            # Distribute proportionally
            total_orig = sum(e["orig"] for e in entries) or 1
            for e in entries:
                e["comp"] = int(tar_comp * (e["orig"] / total_orig))

    file_size = os.path.getsize(path)
    # Sanity-check comp sizes — if they overflow or exceed file size, cap them
    if tar_comp > file_size * 10:
        tar_comp = file_size
    for e in entries:
        if e["comp"] > file_size * 10:
            e["comp"] = 0
    return dict(method=method, tar_mode=tar_mode, comment=comment,
                entries=entries, encrypted=enc or full_enc, full_enc=full_enc,
                tar_orig=tar_orig, tar_comp=tar_comp, file_size=file_size,
                dedup_mode=dedup_mode, multiblock=multiblock)


def _make_default_icon_photo(size=16):
    """Generic blue-S icon. Works with or without PIL."""
    try:
        from PIL import Image, ImageDraw, ImageFont, ImageTk
        img  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle([0, 0, size-1, size-1],
                                radius=size//6, fill=(75, 158, 232, 255))
        font_size = max(7, size - 5)
        try:
            fnt = ImageFont.truetype("arial.ttf", font_size)
        except Exception:
            fnt = ImageFont.load_default()
        bb = draw.textbbox((0, 0), "S", font=fnt)
        draw.text(((size-(bb[2]-bb[0]))//2 - bb[0],
                   (size-(bb[3]-bb[1]))//2 - bb[1] - 1),
                  "S", fill=(255, 255, 255, 255), font=fnt)
        return ImageTk.PhotoImage(img)
    except Exception:
        ph = tk.PhotoImage(width=size, height=size)
        ph.put("#4B9EE8", to=(0, 0, size, size))
        return ph


# ── Custom Title Bar (matches sycg.py) ────────────────────────────────────────
class TitleBar:
    def __init__(self, root, title, T, on_close, on_minimize):
        self.root = root
        self._drag_x = self._drag_y = 0
        self._T = T  # kept for set_icon reset

        bar = tk.Frame(root, bg=T["TB"], height=30)
        bar.pack(fill="x")
        bar.pack_propagate(False)

        # App logo mark — default generated icon, replaced by custom if set
        self._icon_photo = None
        self._icon_lbl = tk.Label(bar, bg=T["TB"], anchor="w", text="")
        self._icon_lbl.pack(side="left", padx=(10, 4), pady=5)
        root.after(1, self._init_default_icon)

        self.lbl = tk.Label(bar, text=title, bg=T["TB"], fg=T["TB_FG"],
                            font=FS, anchor="w")
        self.lbl.pack(side="left", pady=5)

        def mk_btn(txt, cmd, hover_bg, hover_fg="white"):
            b = tk.Label(bar, text=txt, bg=T["TB"], fg=T["TB_FG"],
                         font=("Consolas", 10), width=4, cursor="hand2")
            b.pack(side="right")
            b.bind("<Enter>",    lambda e: b.config(bg=hover_bg, fg=hover_fg))
            b.bind("<Leave>",    lambda e: b.config(bg=T["TB"], fg=T["TB_FG"]))
            b.bind("<Button-1>", lambda e: cmd())
            return b

        mk_btn("✕", on_close,    "#C0392B")
        mk_btn("□", lambda: root.wm_state(
               "zoomed" if root.wm_state() == "normal" else "normal"),
               T["BG4"], T["FG"])
        mk_btn("—", on_minimize, T["BG4"], T["FG"])

        for w in (bar, self.lbl):
            w.bind("<ButtonPress-1>",  self._drag_start)
            w.bind("<B1-Motion>",      self._drag_move)

    def set_title(self, t): self.lbl.config(text=t)

    def _init_default_icon(self):
        # Only apply default if _apply_app_identity hasn't already set a custom icon
        if self._icon_photo is None:
            self._icon_photo = _make_default_icon_photo(16)
            self._icon_lbl.config(image=self._icon_photo, text="")

    def set_icon(self, photo_16):
        """Replace the ▣ mark with a real 16×16 PhotoImage."""
        if photo_16 is None:
            self._icon_photo = _make_default_icon_photo(16)
            self._icon_lbl.config(image=self._icon_photo, text="")
        else:
            self._icon_photo = photo_16  # prevent GC
            self._icon_lbl.config(image=photo_16, text="")

    def _drag_start(self, e):
        self._drag_x = e.x_root - self.root.winfo_x()
        self._drag_y = e.y_root - self.root.winfo_y()

    def _drag_move(self, e):
        x = e.x_root - self._drag_x
        y = e.y_root - self._drag_y
        self.root.geometry(f"+{x}+{y}")


# ── Styled Widgets ─────────────────────────────────────────────────────────────
def mk_btn(parent, text, cmd, T, fg=None, width=None):
    """Button with a subtle top-highlight border for depth."""
    # Wrap in a frame that gives a 1px top highlight
    container = tk.Frame(parent, bg=T["HIGHLIGHT"], padx=0, pady=0)
    inner     = tk.Frame(container, bg=T["BG3"])
    inner.pack(fill="both", expand=True, padx=(0, 0), pady=(1, 0))
    kw = dict(bg=T["BG3"], fg=fg or T["FG"], font=FS, relief="flat", bd=0,
              padx=12, pady=4, cursor="hand2",
              activebackground=T["BG4"], activeforeground=fg or T["FG"],
              command=cmd)
    if width: kw["width"] = width
    b = tk.Button(inner, text=text, **kw)
    b.pack(fill="both")
    # Hover darkens the bottom border
    def _enter(e):
        container.config(bg=T["BLUE_DIM"] if fg == T.get("GREEN") else T["BORDER_LIGHT"])
        inner.config(bg=T["BG4"]); b.config(bg=T["BG4"])
    def _leave(e):
        container.config(bg=T["HIGHLIGHT"])
        inner.config(bg=T["BG3"]); b.config(bg=T["BG3"])
    for w in (b, inner):
        w.bind("<Enter>", _enter); w.bind("<Leave>", _leave)
    return container


def mk_sep(parent, T, vertical=False):
    """Two-tone separator: shadow line + highlight line for depth effect."""
    if vertical:
        f = tk.Frame(parent, bg=T["BORDER"], width=1)
        f.pack(side="left", fill="y", padx=(4, 0), pady=3)
        tk.Frame(parent, bg=T["HIGHLIGHT"], width=1).pack(side="left", fill="y",
                                                           padx=(0, 4), pady=3)
    else:
        tk.Frame(parent, bg=T["SHADOW"],    height=1).pack(fill="x")
        tk.Frame(parent, bg=T["HIGHLIGHT"], height=1).pack(fill="x")


# ── Dialogs ────────────────────────────────────────────────────────────────────
class AskPasswordDialog:
    def __init__(self, parent, T):
        self.result = None
        d = tk.Toplevel(parent)
        d.overrideredirect(True)
        d.configure(bg=T["BG"])
        d.resizable(False, False)
        pw = parent.winfo_rootx() + parent.winfo_width()  // 2 - 180
        ph = parent.winfo_rooty() + parent.winfo_height() // 2 - 60
        d.geometry(f"360x120+{pw}+{ph}")

        # title bar
        tb = tk.Frame(d, bg=T["TB"], height=26); tb.pack(fill="x"); tb.pack_propagate(False)
        tk.Label(tb, text=_lang.t("dlg.password"), bg=T["TB"], fg=T["TB_FG"],
                 font=FS, anchor="w").pack(side="left", padx=8, pady=4)
        _apx = tk.Label(tb, text="✕", bg=T["TB"], fg=T["TB_FG"], font=F, cursor="hand2", width=3)
        _apx.pack(side="right")
        _apx.bind("<Button-1>", lambda e: d.destroy())

        body = tk.Frame(d, bg=T["BG"]); body.pack(fill="both", expand=True, padx=14, pady=10)
        tk.Label(body, text=_lang.t("dlg.pass_label"), bg=T["BG"], fg=T["DIM"], font=FS).pack(anchor="w")
        var = tk.StringVar()
        e = tk.Entry(body, textvariable=var, show="•", bg=T["BG3"], fg=T["FG"],
                     font=F, relief="flat", bd=0, insertbackground=T["FG"])
        e.pack(fill="x", pady=(2, 8))
        e.focus_set()

        bf = tk.Frame(body, bg=T["BG"]); bf.pack(fill="x")
        def ok():
            self.result = var.get()
            d.destroy()
        def cancel():
            d.destroy()
        mk_btn(bf, _lang.t("dlg.ok"),     ok,     T, fg=T["GREEN"]).pack(side="right")
        mk_btn(bf, _lang.t("dlg.cancel"), cancel, T).pack(side="right", padx=(0, 6))
        e.bind("<Return>", lambda e: ok())
        d.bind("<Escape>", lambda e: cancel())
        d.grab_set()
        parent.wait_window(d)


class CompressDialog:
    """Dialog to create a new .syc archive"""
    def __init__(self, parent, T, ini_path, methods, default_arc=""):
        self.result = None
        d = tk.Toplevel(parent)
        d.overrideredirect(True)
        d.configure(bg=T["BG"])

        tb = tk.Frame(d, bg=T["TB"], height=26); tb.pack(fill="x"); tb.pack_propagate(False)
        tk.Label(tb, text=_lang.t("dlg.create_title"), bg=T["TB"], fg=T["FG"],
                 font=FB, anchor="w").pack(side="left", padx=8, pady=4)
        x_lbl = tk.Label(tb, text="✕", bg=T["TB"], fg=T["TB_FG"], font=F, cursor="hand2", width=3)
        x_lbl.pack(side="right")
        x_lbl.bind("<Button-1>", lambda e: d.destroy())

        body = tk.Frame(d, bg=T["BG"]); body.pack(fill="both", expand=True, padx=16, pady=10)

        kw_cb = dict(bg=T["BG"], fg=T["FG"], font=FS, activebackground=T["BG"],
                     activeforeground=T["GREEN"], selectcolor=T["BG3"], relief="flat", bd=0)

        def lbl(text, pady_top=6):
            tk.Label(body, text=text, bg=T["BG"], fg=T["DIM"],
                     font=FS, anchor="w").pack(fill="x", pady=(pady_top, 0))

        def entry_row(var, hint=None, show=None, disabled=False):
            kw = dict(textvariable=var, bg=T["BG3"], fg=T["FG"], font=F,
                      relief="flat", bd=0, insertbackground=T["FG"])
            if show: kw["show"] = show
            e = tk.Entry(body, **kw)
            e.pack(fill="x", pady=(2, 0), ipady=4)
            if disabled: e.config(state="disabled")
            return e

        # ── Archive path ──────────────────────────────────────────────────────
        lbl(_lang.t("dlg.arc_path"), pady_top=0)
        v_arc = tk.StringVar(value=default_arc)
        arc_fr = tk.Frame(body, bg=T["BG"]); arc_fr.pack(fill="x", pady=(2, 0))
        tk.Entry(arc_fr, textvariable=v_arc, bg=T["BG3"], fg=T["FG"], font=F,
                 relief="flat", bd=0, insertbackground=T["FG"]).pack(
                 side="left", fill="x", expand=True, ipady=4, padx=(0, 4))
        def browse():
            p = filedialog.asksaveasfilename(defaultextension=".syc",
                filetypes=[("SYC Archive", "*.syc")])
            if p: v_arc.set(p)
        mk_btn(arc_fr, "...", browse, T).pack(side="right")

        # ── Method ────────────────────────────────────────────────────────────
        lbl(_lang.t("dlg.method"))
        v_method = tk.StringVar(value=methods[0] if methods else "xpszf1")
        cb = ttk.Combobox(body, textvariable=v_method, values=methods, state="readonly", font=F)
        cb.pack(fill="x", pady=(2, 0), ipady=3)

        # ── Options row (solid / crc / md5) ───────────────────────────────────
        opt_fr = tk.Frame(body, bg=T["BG"]); opt_fr.pack(fill="x", pady=(6, 0))
        v_tar = tk.BooleanVar(value=True)
        v_crc = tk.BooleanVar()
        v_md5 = tk.BooleanVar()
        tk.Checkbutton(opt_fr, text=_lang.t("dlg.solid"), variable=v_tar, **kw_cb).pack(side="left")
        tk.Checkbutton(opt_fr, text="CRC32", variable=v_crc, **kw_cb).pack(side="left", padx=(12, 0))
        tk.Checkbutton(opt_fr, text="MD5",   variable=v_md5, **kw_cb).pack(side="left", padx=(8, 0))

        # ── Chunk / Block / Dedup rows ─────────────────────────────────────────
        def option_row(lang_key, default_val, hint_key):
            fr = tk.Frame(body, bg=T["BG"]); fr.pack(fill="x", pady=(3, 0))
            v_en  = tk.BooleanVar()
            v_val = tk.StringVar(value=default_val)
            tk.Checkbutton(fr, text=_lang.t(lang_key), variable=v_en,
                           **kw_cb).pack(side="left")
            ent = tk.Entry(fr, textvariable=v_val, bg=T["BG3"], fg=T["FG"], font=F,
                           relief="flat", bd=0, insertbackground=T["FG"],
                           width=8, state="disabled")
            ent.pack(side="left", padx=(6, 0), ipady=3)
            tk.Label(fr, text=_lang.t(hint_key), bg=T["BG"], fg=T["DIM"],
                     font=FS).pack(side="left", padx=(4, 0))
            v_en.trace_add("write", lambda *_: ent.config(
                state="normal" if v_en.get() else "disabled"))
            return v_en, v_val

        v_chunk_en, v_chunk = option_row("dlg.split", "700MB", "dlg.split_hint")
        v_block_en, v_block = option_row("dlg.block", "512MB", "dlg.block_hint")
        v_dedup_en, v_dedup = option_row("dlg.dedup", "1MB",   "dlg.dedup_hint")

        # ── Encryption ────────────────────────────────────────────────────────
        tk.Frame(body, bg=T["BORDER"], height=1).pack(fill="x", pady=(8, 0))
        enc_fr = tk.Frame(body, bg=T["BG"]); enc_fr.pack(fill="x", pady=(4, 0))
        v_key = tk.BooleanVar()
        tk.Checkbutton(enc_fr, text=_lang.t("dlg.encrypt"), variable=v_key,
                       **kw_cb).pack(side="left")

        # Algorithm: AES256 / CC20
        v_alg = tk.StringVar(value="AES256")
        kw_r = dict(bg=T["BG"], fg=T["FG"], font=FS, activebackground=T["BG"],
                    selectcolor=T["BG3"], relief="flat", bd=0, state="disabled")
        rb_aes = tk.Radiobutton(enc_fr, text="AES-256", variable=v_alg,
                                value="AES256", **kw_r)
        rb_cc  = tk.Radiobutton(enc_fr, text="ChaCha20", variable=v_alg,
                                value="CC20", **kw_r)
        rb_aes.pack(side="left", padx=(16, 0))
        rb_cc.pack(side="left",  padx=(8, 0))

        # Full-encrypted checkbox
        v_full_enc = tk.BooleanVar()
        rb_full = tk.Checkbutton(enc_fr, text=_lang.t("dlg.full_enc"), variable=v_full_enc,
                                 state="disabled", **kw_cb)
        rb_full.pack(side="left", padx=(12, 0))

        def toggle_enc(*_):
            st = "normal" if v_key.get() else "disabled"
            rb_aes.config(state=st)
            rb_cc.config(state=st)
            rb_full.config(state=st)
            pass_entry.config(state=st)
            if not v_key.get():
                v_full_enc.set(False)
        v_key.trace_add("write", toggle_enc)

        # Password field
        lbl(_lang.t("dlg.pass_label"))
        v_pass = tk.StringVar()
        pass_entry = tk.Entry(body, textvariable=v_pass, show="•",
                              bg=T["BG3"], fg=T["FG"], font=F,
                              relief="flat", bd=0, insertbackground=T["FG"],
                              state="disabled")
        pass_entry.pack(fill="x", pady=(2, 0), ipady=4)

        # ── Buttons ────────────────────────────────────────────────────────────
        def validate_chunk_name(arc, use_chunk):
            if use_chunk and "??" not in arc:
                base, ext = os.path.splitext(arc)
                return base + "??" + ext
            return arc

        bf = tk.Frame(body, bg=T["BG"]); bf.pack(fill="x", pady=(10, 0))
        def ok():
            if not v_arc.get():
                messagebox.showerror("Error", "Please specify an archive path", parent=d)
                return
            chunk = v_chunk.get().strip() if v_chunk_en.get() else None
            arc   = validate_chunk_name(v_arc.get(), chunk)
            self.result = dict(
                archive=arc, method=v_method.get(),
                tar=v_tar.get(), crc32=v_crc.get(), md5=v_md5.get(),
                password=v_pass.get() if v_key.get() else None,
                alg=v_alg.get() if v_key.get() else None,
                full_enc=v_full_enc.get(),
                chunk=chunk,
                block=v_block.get().strip() if v_block_en.get() else None,
                dedup=v_dedup.get().strip() if v_dedup_en.get() else None,
            )
            d.destroy()
        mk_btn(bf, _lang.t("dlg.create"), ok,        T, fg=T["GREEN"]).pack(side="right")
        mk_btn(bf, _lang.t("dlg.cancel"), d.destroy, T).pack(side="right", padx=(0, 6))

        # Auto-fit height to content
        d.update_idletasks()
        h = d.winfo_reqheight()
        pw2 = parent.winfo_rootx() + parent.winfo_width()  // 2 - 240
        ph2 = parent.winfo_rooty() + parent.winfo_height() // 2 - h // 2
        d.geometry(f"480x{h}+{pw2}+{ph2}")

        d.grab_set()
        parent.wait_window(d)


class ExtractDialog:
    """Dialog to extract archive"""
    def __init__(self, parent, T, default_dest=""):
        self.result = None
        d = tk.Toplevel(parent)
        d.overrideredirect(True)
        d.configure(bg=T["BG"])
        pw = parent.winfo_rootx() + parent.winfo_width()  // 2 - 220
        ph = parent.winfo_rooty() + parent.winfo_height() // 2 - 80
        d.geometry(f"440x160+{pw}+{ph}")

        tb = tk.Frame(d, bg=T["TB"], height=26); tb.pack(fill="x"); tb.pack_propagate(False)
        tk.Label(tb, text=_lang.t("dlg.extract_title"), bg=T["TB"], fg=T["FG"],
                 font=FB, anchor="w").pack(side="left", padx=8, pady=4)
        _ex = tk.Label(tb, text="✕", bg=T["TB"], fg=T["TB_FG"], font=F, cursor="hand2", width=3)
        _ex.pack(side="right")
        _ex.bind("<Button-1>", lambda e: d.destroy())

        body = tk.Frame(d, bg=T["BG"]); body.pack(fill="both", expand=True, padx=16, pady=12)

        tk.Label(body, text=_lang.t("dlg.dest"), bg=T["BG"], fg=T["DIM"], font=FS).pack(anchor="w")
        v_dest = tk.StringVar(value=default_dest)
        fr = tk.Frame(body, bg=T["BG"]); fr.pack(fill="x", pady=(2, 8))
        e = tk.Entry(fr, textvariable=v_dest, bg=T["BG3"], fg=T["FG"],
                     font=F, relief="flat", bd=0, insertbackground=T["FG"])
        e.pack(side="left", fill="x", expand=True, ipady=4, padx=(0, 4))
        def browse():
            p = filedialog.askdirectory()
            if p: v_dest.set(p)
        mk_btn(fr, "...", browse, T).pack(side="right")

        v_ow = tk.StringVar(value="+")
        ow_fr = tk.Frame(body, bg=T["BG"]); ow_fr.pack(fill="x", pady=(0, 8))
        kw_r = dict(bg=T["BG"], fg=T["FG"], font=FS, activebackground=T["BG"],
                    selectcolor=T["BG3"], relief="flat", bd=0)
        tk.Label(ow_fr, text=_lang.t("dlg.overwrite"), bg=T["BG"], fg=T["DIM"], font=FS).pack(side="left", padx=(0, 8))
        for val, lbl in [("+", _lang.t("dlg.ow_always")), ("-", _lang.t("dlg.ow_skip")), ("p", _lang.t("dlg.ow_ask"))]:
            tk.Radiobutton(ow_fr, text=lbl, variable=v_ow, value=val, **kw_r).pack(side="left", padx=4)

        bf = tk.Frame(body, bg=T["BG"]); bf.pack(fill="x")
        def ok():
            self.result = dict(dest=v_dest.get(), overwrite=v_ow.get())
            d.destroy()
        mk_btn(bf, _lang.t("dlg.extract"), ok,        T, fg=T["GREEN"]).pack(side="right")
        mk_btn(bf, _lang.t("dlg.cancel"),  d.destroy, T).pack(side="right", padx=(0, 6))
        e.bind("<Return>", lambda e: ok())

        d.grab_set()
        parent.wait_window(d)


class PropertiesDialog:
    """Archive properties dialog"""
    def __init__(self, parent, T, info):
        d = tk.Toplevel(parent)
        d.overrideredirect(True)
        d.configure(bg=T["BG"])
        pw = parent.winfo_rootx() + parent.winfo_width()  // 2 - 180
        ph = parent.winfo_rooty() + parent.winfo_height() // 2 - 140
        d.geometry(f"360x280+{pw}+{ph}")

        tb = tk.Frame(d, bg=T["TB"], height=26); tb.pack(fill="x"); tb.pack_propagate(False)
        tk.Label(tb, text=_lang.t("dlg.props_title"), bg=T["TB"], fg=T["FG"],
                 font=FB, anchor="w").pack(side="left", padx=8, pady=4)
        tk.Label(tb, text="✕", bg=T["TB"], fg=T["TB_FG"], font=F, cursor="hand2",
                 width=3).bind("<Button-1>", lambda e: d.destroy())

        body = tk.Frame(d, bg=T["BG"]); body.pack(fill="both", expand=True, padx=16, pady=12)

        def row(label, value, fg=None):
            fr = tk.Frame(body, bg=T["BG"]); fr.pack(fill="x", pady=2)
            tk.Label(fr, text=label, bg=T["BG"], fg=T["DIM"], font=FS,
                     width=16, anchor="w").pack(side="left")
            tk.Label(fr, text=value, bg=T["BG"], fg=fg or T["FG"], font=F,
                     anchor="w").pack(side="left")

        row(_lang.t("prop.path"),     info.get("path", "-"))
        row(_lang.t("prop.size"),     _fmt_size(info.get("size", 0)))
        row(_lang.t("prop.method"),   info.get("method", "-"),   T["BLUE"])
        row(_lang.t("prop.mode"),     info.get("mode", "-"))
        row(_lang.t("prop.files"),    str(info.get("files", 0)))
        row(_lang.t("prop.original"), _fmt_size(info.get("orig", 0)))
        row(_lang.t("prop.packed"),   _fmt_size(info.get("comp", 0)))
        if info.get("orig", 0):
            ratio = (1 - info.get("comp", 0) / info["orig"]) * 100
            row(_lang.t("prop.ratio"), f"{ratio:.1f}%", T["GREEN"])
        if info.get("comment"):
            tk.Frame(body, bg=T["BORDER"], height=1).pack(fill="x", pady=6)
            tk.Label(body, text="Comment:", bg=T["BG"], fg=T["DIM"], font=FS, anchor="w").pack(fill="x")
            tk.Label(body, text=info["comment"], bg=T["BG3"], fg=T["FG"], font=FS,
                     anchor="w", padx=8, pady=4, wraplength=300).pack(fill="x")
        if info.get("encrypted"):
            row(_lang.t("prop.encrypted"), _lang.t("prop.yes"), T["YELLOW"])

        mk_btn(body, _lang.t("dlg.close"), d.destroy, T).pack(side="bottom", pady=(8, 0))
        d.grab_set()
        parent.wait_window(d)


# ── Settings Dialog ───────────────────────────────────────────────────────────
class SettingsDialog:
    def __init__(self, parent, T, current_theme, current_lang, on_apply,
                 current_app_name="", current_app_icon=""):
        self.result = None
        d = tk.Toplevel(parent)
        d.overrideredirect(True)
        d.configure(bg=T["BG"])
        pw = parent.winfo_rootx() + parent.winfo_width()  // 2 - 230
        ph = parent.winfo_rooty() + parent.winfo_height() // 2 - 200

        # Title bar
        tb = tk.Frame(d, bg=T["TB"], height=26); tb.pack(fill="x"); tb.pack_propagate(False)
        tk.Label(tb, text="⚙  " + _lang.t("settings.title"), bg=T["TB"], fg=T["FG"],
                 font=FB, anchor="w").pack(side="left", padx=8, pady=4)
        x_lbl = tk.Label(tb, text="✕", bg=T["TB"], fg=T["TB_FG"], font=F,
                         cursor="hand2", width=3)
        x_lbl.pack(side="right")
        x_lbl.bind("<Button-1>", lambda e: d.destroy())

        body = tk.Frame(d, bg=T["BG"]); body.pack(fill="both", expand=True, padx=20, pady=12)

        def section_label(text):
            tk.Label(body, text=text, bg=T["BG"], fg=T["DIM"],
                     font=FS, anchor="w").pack(fill="x", pady=(6, 2))

        def separator():
            tk.Frame(body, bg=T["BORDER"], height=1).pack(fill="x", pady=(4, 2))

        # ── Theme ──────────────────────────────────────────────────────────────
        section_label(_lang.t("settings.theme"))
        v_theme = tk.StringVar(value=current_theme)
        tf = tk.Frame(body, bg=T["BG"]); tf.pack(fill="x")
        kw_r = dict(bg=T["BG"], fg=T["FG"], font=F, activebackground=T["BG"],
                    selectcolor=T["BG3"], relief="flat", bd=0)
        for val, lbl_key in [("dark",  "settings.theme_dark"),
                              ("white", "settings.theme_white"),
                              ("auto",  "settings.theme_auto")]:
            tk.Radiobutton(tf, text=_lang.t(lbl_key), variable=v_theme,
                           value=val, **kw_r).pack(side="left", padx=(0, 16))

        separator()

        # ── Language ───────────────────────────────────────────────────────────
        section_label(_lang.t("settings.language"))

        available = [("EN", "English")]
        seen = {"EN"}
        for base in [_lang_dir(), _here()]:
            if os.path.isdir(base):
                for fname in sorted(os.listdir(base)):
                    if fname.upper().endswith(".SYL"):
                        code = os.path.splitext(fname)[0].upper()
                        if code not in seen:
                            seen.add(code)
                            available.append((code, LANGS.get(code, code)))

        v_lang      = tk.StringVar(value=current_lang)
        lang_codes  = [c for c, _ in available]
        lang_labels = [f"{c} — {n}" for c, n in available]
        cur_idx = lang_codes.index(current_lang) if current_lang in lang_codes else 0
        v_lang_display = tk.StringVar(value=lang_labels[cur_idx])

        style = ttk.Style(); style.theme_use("default")
        style.configure("TCombobox", fieldbackground=T["BG3"],
                        background=T["BG3"], foreground=T["FG"], arrowcolor=T["FG"])
        lang_cb = ttk.Combobox(body, textvariable=v_lang_display,
                               values=lang_labels, state="readonly", font=F)
        lang_cb.pack(fill="x", pady=(2, 0), ipady=3)

        def on_lang_select(e):
            v_lang.set(lang_codes[lang_labels.index(v_lang_display.get())])
        lang_cb.bind("<<ComboboxSelected>>", on_lang_select)

        tk.Label(body, text=_lang.t("settings.lang_note"),
                 bg=T["BG"], fg=T["DIM"], font=FS, anchor="w").pack(fill="x")

        separator()

        # ── App Identity ───────────────────────────────────────────────────────
        section_label(_lang.t("settings.app_title"))

        def _field_row(label_key, hint_key, var, browse_cmd=None):
            fr_lbl = tk.Frame(body, bg=T["BG"]); fr_lbl.pack(fill="x", pady=(2, 0))
            tk.Label(fr_lbl, text=_lang.t(label_key), bg=T["BG"], fg=T["DIM"],
                     font=FS, width=20, anchor="w").pack(side="left")
            tk.Label(fr_lbl, text=_lang.t(hint_key), bg=T["BG"], fg=T["BORDER"],
                     font=("Consolas", 7), anchor="w").pack(side="left", padx=(4,0))
            fr_inp = tk.Frame(body, bg=T["BG"]); fr_inp.pack(fill="x", pady=(2, 0))
            e = tk.Entry(fr_inp, textvariable=var, bg=T["BG3"], fg=T["FG"],
                         font=F, relief="flat", bd=0, insertbackground=T["FG"])
            e.pack(side="left", fill="x", expand=True, ipady=3,
                   padx=(0, 4) if browse_cmd else 0)
            if browse_cmd:
                mk_btn(fr_inp, "...", browse_cmd, T).pack(side="right")
            return e

        v_app_name = tk.StringVar(value=current_app_name)
        _field_row("settings.app_name", "settings.app_name_hint", v_app_name)

        v_app_icon = tk.StringVar(value=current_app_icon)
        def browse_icon():
            p = filedialog.askopenfilename(
                title="Select icon",
                filetypes=[("Icon files", "*.ico *.png"), ("All files", "*.*")],
                parent=d)
            if p:
                v_app_icon.set(p)
        icon_entry = _field_row("settings.app_icon", "settings.app_icon_hint",
                                v_app_icon, browse_icon)

        # Icon preview label
        icon_preview_fr = tk.Frame(body, bg=T["BG"]); icon_preview_fr.pack(fill="x", pady=(4,0))
        icon_preview_lbl = tk.Label(icon_preview_fr, text="", bg=T["BG"],
                                    fg=T["DIM"], font=FS, anchor="w")
        icon_preview_lbl.pack(side="left")
        self._icon_photo_tmp = None  # prevent GC

        def update_icon_preview(*_):
            path = v_app_icon.get().strip()
            if not path or not os.path.exists(path):
                icon_preview_lbl.config(text="", image="")
                return
            try:
                from PIL import Image, ImageTk
                img = Image.open(path).resize((24, 24))
                ph  = ImageTk.PhotoImage(img)
                self._icon_photo_tmp = ph
                icon_preview_lbl.config(image=ph, text="")
            except Exception:
                try:
                    ph = tk.PhotoImage(file=path)
                    ph_small = ph.subsample(max(1, ph.width()//24))
                    self._icon_photo_tmp = ph_small
                    icon_preview_lbl.config(image=ph_small, text="")
                except Exception:
                    icon_preview_lbl.config(text="(preview unavailable)", image="")

        v_app_icon.trace_add("write", lambda *_: icon_preview_lbl.after(200, update_icon_preview))
        update_icon_preview()

        # Reset button
        def reset_identity():
            v_app_name.set("")
            v_app_icon.set("")
        mk_btn(icon_preview_fr, _lang.t("settings.app_reset"), reset_identity,
               T, fg=T["RED"]).pack(side="right")

        separator()

        # ── Buttons ────────────────────────────────────────────────────────────
        bf = tk.Frame(body, bg=T["BG"]); bf.pack(fill="x", pady=(4, 0))

        def apply():
            _cfg.set("theme",    v_theme.get())
            _cfg.set("lang",     v_lang.get())
            _cfg.set("app_name", v_app_name.get().strip())
            _cfg.set("app_icon", v_app_icon.get().strip())
            _cfg.save()
            d.destroy()
            on_apply(v_theme.get(), v_lang.get(),
                     v_app_name.get().strip(), v_app_icon.get().strip())

        mk_btn(bf, _lang.t("dlg.ok"),     apply,     T, fg=T["GREEN"]).pack(side="right")
        mk_btn(bf, _lang.t("dlg.cancel"), d.destroy, T).pack(side="right", padx=(0, 6))
        d.bind("<Return>", lambda e: apply())
        d.bind("<Escape>", lambda e: d.destroy())

        # Auto-fit height
        d.update_idletasks()
        h = d.winfo_reqheight()
        d.geometry(f"460x{h}+{pw}+{ph}")

        d.grab_set()
        parent.wait_window(d)




# ── Main Window ────────────────────────────────────────────────────────────────
class PSycG:
    W, H = 860, 540

    def __init__(self, open_file=None, theme="auto", lang=None):
        # Load config first
        cfg_theme = _cfg.get("theme", "auto")
        cfg_lang  = _cfg.get("lang",  "EN")

        # CLI args override config
        if theme == "auto": theme = cfg_theme
        if lang is None:    lang  = cfg_lang if cfg_lang != "EN" else None

        self.theme = detect_theme() if theme == "auto" else theme
        self.T = THEMES.get(self.theme, THEMES["dark"])
        T = self.T

        self.archive_path = None
        self.archive_data = None
        self.password     = None
        self._ini_path    = os.path.join(_here(), "syc.ini")
        self._methods     = self._load_methods()
        self._nav_path    = ""
        self._lang_code   = "EN"

        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.configure(bg=T["BG"])
        sx, sy = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        self.root.geometry(f"{self.W}x{self.H}+{(sx-self.W)//2}+{(sy-self.H)//2}")
        self.root.minsize(600, 400)

        # Force taskbar entry + apply rounded corners on Windows
        if sys.platform == "win32":
            self.root.update_idletasks()
            try:
                import ctypes
                GWL_EXSTYLE      = -20
                WS_EX_APPWINDOW  = 0x00040000
                WS_EX_TOOLWINDOW = 0x00000080
                hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
                style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
                style = (style & ~WS_EX_TOOLWINDOW) | WS_EX_APPWINDOW
                ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
                self._hwnd = hwnd
                self.root.withdraw()
                self.root.after(10, self.root.deiconify)
            except Exception:
                self._hwnd = None

        # Load language (EN = no file needed, defaults used)
        if lang and lang != "EN":
            # Accept code or path
            if not lang.endswith(".syl"):
                lang_path = _syl_path(lang)
            else:
                lang_path = lang if os.path.exists(lang) else _syl_path(
                    os.path.splitext(os.path.basename(lang))[0])
            if lang_path:
                _lang.load(lang_path)
                self._lang_code = os.path.splitext(
                    os.path.basename(lang_path))[0].upper()

        self._build_ui()
        self._setup_treeview_style()

        self.root.bind("<Configure>", self._on_resize)

        # Apply saved app identity (name + icon)
        self._apply_app_identity(
            _cfg.get("app_name", ""),
            _cfg.get("app_icon", "")
        )

        # Keyboard shortcuts
        self.root.bind("<Control-o>",  lambda e: self._cmd_open())
        self.root.bind("<Control-O>",  lambda e: self._cmd_open())
        self.root.bind("<Control-n>",  lambda e: self._cmd_create())
        self.root.bind("<Control-N>",  lambda e: self._cmd_create())
        self.root.bind("<F5>",         lambda e: self._reload_archive())
        self.root.bind("<Delete>",     lambda e: self._cmd_close_arc())
        self.root.bind("<BackSpace>",  lambda e: self._nav_up())
        self.root.bind("<Alt-Left>",   lambda e: self._nav_up())
        self.root.bind("<Control-a>",  lambda e: self._select_all())
        self.root.bind("<Control-A>",  lambda e: self._select_all())

        if open_file:
            self.root.after(100, lambda: self._open_archive(open_file))

        self.root.mainloop()

    def _try_autodetect_lang(self):
        pass  # Replaced by config-based loading

    def _load_methods(self):
        """Only reads entries under [Compression methods] section"""
        methods = []
        if not os.path.exists(self._ini_path):
            return ["xpszf1"]
        try:
            in_methods = False
            with open(self._ini_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith(";"):
                        continue
                    if line.startswith("["):
                        in_methods = line.lower().startswith("[compression methods]")
                        continue
                    if in_methods and "=" in line:
                        name = line.split("=")[0].strip()
                        if name:
                            methods.append(name)
        except Exception:
            pass
        return methods or ["xpszf1"]

    # ── UI Construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        T = self.T

        # Title bar
        self.titlebar = TitleBar(
            self.root, _lang.t("title"),
            T, self._on_close, self._minimize)

        mk_sep(self.root, T)

        # Toolbar
        self._build_toolbar()
        mk_sep(self.root, T)

        # Path bar
        self._build_pathbar()
        mk_sep(self.root, T)

        # Main area (file list)
        main = tk.Frame(self.root, bg=T["BG"])
        main.pack(fill="both", expand=True)
        self._build_filelist(main)

        mk_sep(self.root, T)
        # Status bar
        self._build_statusbar()

    def _build_toolbar(self):
        T = self.T
        tb = tk.Frame(self.root, bg=T["BG2"], height=42)
        tb.pack(fill="x")
        tb.pack_propagate(False)

        kw = dict(bg=T["BG2"], relief="flat")

        # Track sub-labels for live language updates
        self._toolbar_labels = {}  # key -> Label widget

        def tool_btn(parent, text, lang_key, cmd, fg=None):
            fr = tk.Frame(parent, bg=T["BG2"], cursor="hand2")
            fr.pack(side="left")
            icon_lbl = tk.Label(fr, text=text, bg=T["BG2"],
                                fg=fg or T["FG"], font=("Consolas", 14))
            icon_lbl.pack(padx=(10, 10), pady=(3, 0))
            sub_lbl  = tk.Label(fr, text=_lang.t(lang_key), bg=T["BG2"],
                                fg=T["DIM"], font=("Consolas", 7))
            sub_lbl.pack(pady=(0, 3))
            self._toolbar_labels[lang_key] = sub_lbl
            for w in (fr, icon_lbl, sub_lbl):
                w.bind("<Button-1>",  lambda e: cmd())
                w.bind("<Enter>",     lambda e: fr.config(bg=T["BG3"]) or
                                     [c.config(bg=T["BG3"]) for c in fr.winfo_children()])
                w.bind("<Leave>",     lambda e: fr.config(bg=T["BG2"]) or
                                     [c.config(bg=T["BG2"]) for c in fr.winfo_children()])
            return fr

        tool_btn(tb, "📂", "toolbar.open",       self._cmd_open)
        tk.Frame(tb, bg=T["BORDER"], width=1).pack(side="left", fill="y", pady=6)
        tool_btn(tb, "📦", "toolbar.create",     self._cmd_create)
        tool_btn(tb, "📤", "toolbar.extract",    self._cmd_extract_sel)
        tool_btn(tb, "📋", "toolbar.extract_to", self._cmd_extract_to)
        tk.Frame(tb, bg=T["BORDER"], width=1).pack(side="left", fill="y", pady=6)
        tool_btn(tb, "✓",  "toolbar.test",       self._cmd_test,      T["GREEN"])
        tool_btn(tb, "ℹ",  "toolbar.info",       self._cmd_info,      T["BLUE"])
        tk.Frame(tb, bg=T["BORDER"], width=1).pack(side="left", fill="y", pady=6)
        tool_btn(tb, "✕",  "toolbar.close",      self._cmd_close_arc, T["RED"])

        # Settings gear button (right side of toolbar)
        tk.Frame(tb, bg=T["BORDER"], width=1).pack(side="right", fill="y", pady=6)
        gear_fr = tk.Frame(tb, bg=T["BG2"], cursor="hand2")
        gear_fr.pack(side="right")
        gear_icon = tk.Label(gear_fr, text="⚙", bg=T["BG2"],
                             fg=T["DIM"], font=("Consolas", 14))
        gear_icon.pack(padx=(10, 10), pady=(3, 0))
        gear_sub = tk.Label(gear_fr, text=_lang.t("settings.title"),
                            bg=T["BG2"], fg=T["DIM"], font=("Consolas", 7))
        gear_sub.pack(pady=(0, 3))
        self._toolbar_labels["settings.title"] = gear_sub
        for w in (gear_fr, gear_icon, gear_sub):
            w.bind("<Button-1>", lambda e: self._cmd_settings())
            w.bind("<Enter>",    lambda e: [x.config(bg=T["BG3"]) for x in gear_fr.winfo_children() + [gear_fr]])
            w.bind("<Leave>",    lambda e: [x.config(bg=T["BG2"]) for x in gear_fr.winfo_children() + [gear_fr]])

    def _build_pathbar(self):
        T = self.T
        pb = tk.Frame(self.root, bg=T["BG2"], height=28)
        pb.pack(fill="x")
        pb.pack_propagate(False)

        # Up button
        self.btn_up = tk.Label(pb, text=_lang.t("nav.up"),
                               bg=T["BG2"], fg=T["DIM"], font=FS,
                               cursor="hand2", padx=8)
        self.btn_up.pack(side="left", pady=4)
        self.btn_up.bind("<Button-1>", lambda e: self._nav_up())
        self.btn_up.bind("<Enter>", lambda e: self.btn_up.config(fg=T["BLUE"]))
        self.btn_up.bind("<Leave>", lambda e: self.btn_up.config(fg=T["DIM"]))

        tk.Frame(pb, bg=T["BORDER"], width=1).pack(side="left", fill="y", pady=4)

        self.var_path = tk.StringVar(value=_lang.t("nav.no_archive"))
        tk.Label(pb, textvariable=self.var_path, bg=T["BG2"], fg=T["FG"],
                 font=FS, anchor="w", padx=8).pack(side="left", pady=4)

        # Search box (right side)
        tk.Frame(pb, bg=T["BORDER"], width=1).pack(side="right", fill="y", pady=4)
        self._var_search = tk.StringVar()
        self._var_search.trace_add("write", lambda *_: self._on_search())
        _se = tk.Entry(pb, textvariable=self._var_search, bg=T["BG3"], fg=T["FG"],
                       font=FS, relief="flat", bd=0, insertbackground=T["FG"],
                       width=18)
        _se.pack(side="right", pady=5, ipady=2, padx=(0, 4))
        tk.Label(pb, text="🔍", bg=T["BG2"], fg=T["DIM"], font=FS).pack(
                 side="right", pady=4)

    def _build_filelist(self, parent):
        T = self.T

        # Frame with scrollbars
        fr = tk.Frame(parent, bg=T["BG"])
        fr.pack(fill="both", expand=True)

        # "tree headings" shows the expand arrow + columns
        cols = ("size", "packed", "ratio", "method")
        self.tree = ttk.Treeview(fr, columns=cols, show="tree headings",
                                 selectmode="extended")

        # Tree column (name) — set via tree column #0
        self.tree.heading("#0", text=_lang.t("col.name"), anchor="w",
                          command=lambda: self._sort_col("#0"))
        self.tree.column("#0", width=340, anchor="w", minwidth=120, stretch=True)

        # Fixed-width right columns (don't stretch)
        self._fixed_cols = [
            ("size",   _lang.t("col.original"), 100, "e"),
            ("packed", _lang.t("col.packed"),   100, "e"),
            ("ratio",  _lang.t("col.ratio"),     80, "e"),
            ("method", _lang.t("col.method"),   160, "e"),
        ]
        for col, text, width, anchor in self._fixed_cols:
            self.tree.heading(col, text=text, anchor=anchor,
                              command=lambda c=col: self._sort_col(c))
            self.tree.column(col, width=width, anchor=anchor,
                             minwidth=40, stretch=False)

        # Scrollbars
        vsb = ttk.Scrollbar(fr, orient="vertical",   command=self.tree.yview)
        hsb = ttk.Scrollbar(fr, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        fr.grid_rowconfigure(0, weight=1)
        fr.grid_columnconfigure(0, weight=1)

        # Context menu
        self.ctx = tk.Menu(self.root, tearoff=0, bg=T["BG2"], fg=T["FG"],
                           activebackground=T["SEL"], activeforeground=T["SEL_FG"],
                           font=FS, relief="flat", bd=1)
        self.ctx.add_command(label=_lang.t("ctx.extract_sel"), command=self._cmd_extract_sel)
        self.ctx.add_command(label=_lang.t("ctx.extract_to"),  command=self._cmd_extract_to)
        self.ctx.add_separator()
        self.ctx.add_command(label=_lang.t("ctx.copy_name"),   command=self._ctx_copy_name)
        self.ctx.add_command(label=_lang.t("ctx.select_all"),  command=self._select_all)
        self.tree.bind("<Button-3>", self._show_ctx)
        self.tree.bind("<Double-1>", self._on_double_click)
        self.tree.bind("<Return>",   self._on_double_click)

        # Lazy load: open event triggers child population
        self.tree.bind("<<TreeviewOpen>>", self._on_tree_open)

        # Drag-and-drop: try tkinterdnd2, fall back silently
        try:
            self.root.drop_target_register("DND_Files")
            self.root.dnd_bind("<<Drop>>", self._on_dnd_drop)
        except Exception:
            pass

    def _build_statusbar(self):
        T = self.T
        sb = tk.Frame(self.root, bg=T["BG2"], height=24)
        sb.pack(fill="x", side="bottom")
        sb.pack_propagate(False)

        self.var_status = tk.StringVar(value=_lang.t("nav.ready"))
        self.var_count  = tk.StringVar(value="")

        tk.Label(sb, textvariable=self.var_status, bg=T["BG2"], fg=T["DIM"],
                 font=FS, anchor="w").pack(side="left", padx=8)
        # Keyboard hint (far right, very dim)
        tk.Label(sb, text="Ctrl+O  Ctrl+N  F5  Del",
                 bg=T["BG2"], fg=T["BORDER"], font=("Consolas", 7),
                 anchor="e").pack(side="right", padx=(0, 8))
        tk.Label(sb, textvariable=self.var_count,  bg=T["BG2"], fg=T["DIM"],
                 font=FS, anchor="e").pack(side="right", padx=8)

    # ── Treeview styling ──────────────────────────────────────────────────────

    def _setup_treeview_style(self):
        T = self.T
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview",
                        background=T["BG3"],
                        foreground=T["FG"],
                        fieldbackground=T["BG3"],
                        font=FS,
                        rowheight=23,
                        borderwidth=0,
                        indent=18,
                        relief="flat")
        style.configure("Treeview.Heading",
                        background=T["BG2"],
                        foreground=T["DIM"],
                        font=("Consolas", 8, "bold"),
                        relief="flat",
                        borderwidth=0,
                        padding=(4, 4))
        style.map("Treeview",
                  background=[("selected", T["SEL"])],
                  foreground=[("selected", T["SEL_FG"])])
        style.map("Treeview.Heading",
                  background=[("active", T["BG4"]),
                               ("pressed", T["BG5"])])
        for sb in ("Vertical.TScrollbar", "Horizontal.TScrollbar"):
            style.configure(sb,
                            background=T["BG4"], troughcolor=T["BG3"],
                            arrowcolor=T["DIM"], borderwidth=0,
                            relief="flat", width=8, arrowsize=8)
            style.map(sb,
                      background=[("active", T["BG5"]),
                                  ("pressed", T["BLUE"])])

        # Combobox theme
        style.configure("TCombobox",
                        fieldbackground=T["BG3"], background=T["BG4"],
                        foreground=T["FG"], arrowcolor=T["DIM"],
                        borderwidth=0, relief="flat",
                        selectbackground=T["SEL"],
                        selectforeground=T["SEL_FG"],
                        padding=(4, 2))
        style.map("TCombobox",
                  fieldbackground=[("readonly", T["BG3"])],
                  background=[("active", T["BG5"])],
                  foreground=[("disabled", T["DIM"])],
                  arrowcolor=[("disabled", T["DIM"]), ("active", T["FG"])])

    # ── Archive Operations ────────────────────────────────────────────────────

    def _open_archive(self, path=None):
        if path is None:
            path = filedialog.askopenfilename(
                title="Open SYC Archive",
                filetypes=[("SYC Archives", "*.syc"), ("All files", "*.*")])
        if not path:
            return
        path = os.path.normpath(path)
        if not os.path.exists(path):
            messagebox.showerror("Error", f"File not found:\n{path}", parent=self.root)
            return

        self._status("Loading…")
        try:
            data = _read_archive(path, self.password)
        except ValueError as e:
            messagebox.showerror("Invalid Archive", str(e), parent=self.root)
            self._status("Error loading archive")
            return
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self.root)
            self._status("Error")
            return

        if data.get("full_enc") and not self.password:
            dlg = AskPasswordDialog(self.root, self.T)
            if not dlg.result:
                return
            self.password = dlg.result
            try:
                data = _read_archive(path, self.password)
            except Exception as e:
                messagebox.showerror("Error", str(e), parent=self.root)
                return

        self.archive_path = path
        self.archive_data = data
        self._populate_tree(data, "")

        name = os.path.basename(path)
        self.titlebar.set_title(f"SYC Archive Manager — {name}")
        self._nav_path = ""
        self._update_pathbar()
        n = len(data["entries"])
        self._status(_lang.t("nav.opened", name=name))
        self.var_count.set(f"{n} file{'s' if n != 1 else ''}  |  "
                           f"{_fmt_size(os.path.getsize(path))}")

    def _populate_tree(self, data, focus_path=""):
        """Build hierarchical tree - TOP LEVEL ONLY, lazy-load subdirs on expand."""
        self.tree.delete(*self.tree.get_children())
        T = self.T
        self.tree.tag_configure("folder",    foreground=T["BLUE"])
        self.tree.tag_configure("file",      foreground=T["FG"])
        self.tree.tag_configure("encrypted", foreground=T["YELLOW"])

        entries = data.get("entries", [])
        norm = [{**e, "name": e["name"].replace("\\", "/").strip("/")}
                for e in entries]
        # Cache normalized entries for lazy loading
        self._tree_entries = norm
        self._tree_method  = data.get("method", "")
        self._tree_data    = data

        self._build_subtree("", focus_path, norm, data.get("method", ""), data,
                            lazy=True)

    def _build_subtree(self, parent_iid, root_path, entries, method, data,
                       lazy=False):
        """
        Insert direct children of root_path into the tree.
        If lazy=True, folders get a dummy child so they show the expand arrow;
        actual children are loaded by _on_tree_open when the user expands.
        """
        T = self.T
        prefix = (root_path + "/") if root_path else ""

        folders = {}
        files   = []
        for e in entries:
            name = e["name"]
            if root_path and not name.startswith(prefix):
                continue
            rel = name[len(prefix):]
            if "/" in rel:
                folder = rel.split("/")[0]
                folders.setdefault(folder, []).append(e)
            else:
                files.append(e)

        for folder in sorted(folders.keys()):
            full_path = (prefix + folder) if prefix else folder
            iid = f"d:{full_path}"
            children = folders[folder]
            f_orig = sum(ch.get("orig", 0) for ch in children)
            f_comp = sum(ch.get("comp", 0) for ch in children)
            f_ratio_val = (1 - f_comp / f_orig) * 100 if f_orig > 0 else None
            f_ratio = ("—" if f_ratio_val is None or not (-999 < f_ratio_val <= 100)
                       else f"{f_ratio_val:.1f}%")
            nf = sum(1 for ch in children if "/" not in ch["name"][len(prefix + folder + "/"):])
            total_n = len(children)
            self.tree.insert(
                parent_iid, "end", iid=iid,
                text=f"{folder}/",
                values=(_fmt_size(f_orig) if f_orig else "—",
                        _fmt_size(f_comp) if f_comp else "—",
                        f_ratio, ""),
                open=False, tags=("folder",),
            )
            if lazy:
                # Placeholder child so the arrow appears — real content loaded on expand
                self.tree.insert(iid, "end", iid=f"_ph:{full_path}",
                                 text="", values=("", "", "", ""))
            else:
                self._build_subtree(iid, full_path, entries, method, data, lazy=False)

        enc = data.get("encrypted", False)
        for e in sorted(files, key=lambda x: x["name"].split("/")[-1].lower()):
            name  = e["name"]
            fname = name.split("/")[-1]
            orig  = e.get("orig", 0)
            comp  = e.get("comp", 0)
            ratio_val = (1 - comp / orig) * 100 if orig > 0 else None
            ratio = ("—" if ratio_val is None or not (-999 < ratio_val <= 100)
                     else f"{ratio_val:.1f}%")
            self.tree.insert(
                parent_iid, "end", iid=f"f:{name}",
                text=fname,
                values=(_fmt_size(orig) if orig else "—",
                        _fmt_size(comp) if comp else "—",
                        ratio, method),
                tags=("encrypted" if enc else "file",),
            )

    def _on_tree_open(self, event):
        """Lazy-load children when a folder is expanded."""
        iid = self.tree.focus()
        if not iid.startswith("d:"):
            return
        # Check if the first child is a placeholder
        children = self.tree.get_children(iid)
        if not children:
            return
        first = children[0]
        if not first.startswith("_ph:"):
            return  # already loaded
        # Remove placeholder and build real children
        self.tree.delete(first)
        folder_path = iid[2:]  # strip "d:"
        self._build_subtree(iid, folder_path,
                            self._tree_entries, self._tree_method,
                            self._tree_data, lazy=True)

    def _on_dnd_drop(self, event):
        """Handle files dropped onto the window."""
        raw = event.data.strip()
        # tkinterdnd2 wraps paths in {} if they contain spaces
        import re as _re
        paths = _re.findall(r'\{([^}]+)\}|([^\s]+)', raw)
        paths = [a or b for a, b in paths]
        for path in paths:
            path = path.strip()
            if path.lower().endswith(".syc") and os.path.exists(path):
                self._open_archive(path)
                break

    def _sort_col(self, col):
        # Only sort top-level items (don't reorder inside folders)
        if col == "#0":
            items = [(self.tree.item(k, "text"), k) for k in self.tree.get_children("")]
        else:
            items = [(self.tree.set(k, col), k) for k in self.tree.get_children("")]
        col_key = col.replace("#", "_")
        reverse = getattr(self, f"_sort_{col_key}_rev", False)
        try:
            items.sort(key=lambda x: x[0].lower(), reverse=reverse)
        except Exception:
            pass
        for i, (_, k) in enumerate(items):
            self.tree.move(k, "", i)
        setattr(self, f"_sort_{col_key}_rev", not reverse)

    # ── Commands ──────────────────────────────────────────────────────────────

    def _cmd_open(self):
        self._open_archive()


    def _open_first_part(self, archive_pattern):
        """After compression, open the first real file (resolves ?? wildcard)"""
        import glob as _glob
        if "??" in archive_pattern:
            # Replace ?? with glob pattern and find first part
            pattern = archive_pattern.replace("??", "*")
            matches = sorted(_glob.glob(pattern))
            if matches:
                self._open_archive(matches[0])
            else:
                self._status(_lang.t("nav.error"))
        else:
            self._open_archive(archive_pattern)

    def _pick_sources(self):
        """Custom file browser: navigate folders, select files AND folders mixed."""
        T = self.T
        selected = []       # full paths in order added
        result_box = [None]

        d = tk.Toplevel(self.root)
        d.overrideredirect(True)
        d.configure(bg=T["BG"])
        W, H = 660, 460
        pw = self.root.winfo_rootx() + self.root.winfo_width()  // 2 - W // 2
        ph = self.root.winfo_rooty() + self.root.winfo_height() // 2 - H // 2
        d.geometry(f"{W}x{H}+{pw}+{ph}")
        d.resizable(True, True)

        # ── Title bar ─────────────────────────────────────────────────────────
        tb = tk.Frame(d, bg=T["TB"], height=26); tb.pack(fill="x"); tb.pack_propagate(False)
        tk.Label(tb, text="Select files and folders", bg=T["TB"], fg=T["FG"],
                 font=FB, anchor="w").pack(side="left", padx=8, pady=4)
        x = tk.Label(tb, text="✕", bg=T["TB"], fg=T["TB_FG"], font=F, cursor="hand2", width=3)
        x.pack(side="right")
        x.bind("<Button-1>", lambda e: d.destroy())

        # ── Path bar (editable) ───────────────────────────────────────────────
        pb = tk.Frame(d, bg=T["BG2"], height=30); pb.pack(fill="x"); pb.pack_propagate(False)

        # Drive/root quick-jump buttons on Windows
        drives_fr = tk.Frame(pb, bg=T["BG2"]); drives_fr.pack(side="left", padx=(6,0))
        if sys.platform == "win32":
            import string
            for drv in [f"{l}:\\" for l in string.ascii_uppercase
                        if os.path.exists(f"{l}:\\")]:
                lbl = drv[:2]
                b = tk.Label(drives_fr, text=lbl, bg=T["BG3"], fg=T["DIM"],
                             font=FS, padx=5, pady=1, cursor="hand2", relief="flat")
                b.pack(side="left", padx=(0,2), pady=4)
                b.bind("<Button-1>", lambda e, p=drv: refresh(p))
                b.bind("<Enter>", lambda e, w=b: w.config(fg=T["BLUE"]))
                b.bind("<Leave>", lambda e, w=b: w.config(fg=T["DIM"]))

        var_path = tk.StringVar()
        path_entry = tk.Entry(pb, textvariable=var_path, bg=T["BG3"], fg=T["FG"],
                              font=FS, relief="flat", bd=0, insertbackground=T["FG"])
        path_entry.pack(side="left", fill="x", expand=True, ipady=3, padx=(6,4), pady=4)
        def go_to_typed(event=None):
            p = var_path.get().strip()
            if os.path.isdir(p):
                refresh(p)
        path_entry.bind("<Return>", go_to_typed)

        # ── Main area ─────────────────────────────────────────────────────────
        main = tk.Frame(d, bg=T["BG"]); main.pack(fill="both", expand=True, padx=6, pady=(4,0))

        # Left: browser
        left = tk.Frame(main, bg=T["BG"]); left.pack(side="left", fill="both", expand=True)
        tk.Label(left, text="Browse  (double-click to enter, ↵ to add)",
                 bg=T["BG"], fg=T["DIM"], font=FS).pack(anchor="w", padx=2)

        bf = tk.Frame(left, bg=T["BG"]); bf.pack(fill="both", expand=True)
        vsb1 = ttk.Scrollbar(bf, orient="vertical")
        browse_lb = tk.Listbox(bf, bg=T["BG3"], fg=T["FG"], font=FS,
                               selectmode="extended", relief="flat", bd=0,
                               selectbackground=T["SEL"], selectforeground=T["SEL_FG"],
                               activestyle="none", yscrollcommand=vsb1.set)
        vsb1.config(command=browse_lb.yview)
        browse_lb.pack(side="left", fill="both", expand=True)
        vsb1.pack(side="right", fill="y")

        tk.Frame(main, bg=T["BORDER"], width=1).pack(side="left", fill="y", padx=5)

        # Right: selected
        right = tk.Frame(main, bg=T["BG"], width=190); right.pack(side="left", fill="y")
        right.pack_propagate(False)
        tk.Label(right, text="Selected", bg=T["BG"], fg=T["DIM"], font=FS).pack(anchor="w", padx=2)

        rf = tk.Frame(right, bg=T["BG"]); rf.pack(fill="both", expand=True)
        vsb2 = ttk.Scrollbar(rf, orient="vertical")
        sel_lb = tk.Listbox(rf, bg=T["BG2"], fg=T["FG"], font=FS,
                            selectmode="extended", relief="flat", bd=0,
                            selectbackground=T["SEL"], selectforeground=T["SEL_FG"],
                            activestyle="none", yscrollcommand=vsb2.set)
        vsb2.config(command=sel_lb.yview)
        sel_lb.pack(side="left", fill="both", expand=True)
        vsb2.pack(side="right", fill="y")

        # ── Bottom bar ────────────────────────────────────────────────────────
        tk.Frame(d, bg=T["BORDER"], height=1).pack(fill="x")
        bot = tk.Frame(d, bg=T["BG2"], height=38); bot.pack(fill="x"); bot.pack_propagate(False)

        # ── State ─────────────────────────────────────────────────────────────
        _cwd = [os.path.expanduser("~")]

        def refresh(path):
            path = os.path.normpath(path)
            _cwd[0] = path
            var_path.set(path)
            browse_lb.delete(0, "end")
            # ".." entry (unless at root)
            parent = os.path.dirname(path)
            if parent != path:
                browse_lb.insert("end", "📁 ..")
                browse_lb.itemconfig(0, fg=T["DIM"])
            try:
                items = sorted(os.listdir(path),
                               key=lambda x: (not os.path.isdir(os.path.join(path, x)),
                                              x.lower()))
                for item in items:
                    full = os.path.join(path, item)
                    icon = "📁 " if os.path.isdir(full) else "📄 "
                    browse_lb.insert("end", icon + item)
            except PermissionError:
                browse_lb.insert("end", "  (permission denied)")

        def _entry_path(idx):
            """Return full path for a listbox index."""
            raw = browse_lb.get(idx)[2:]   # strip icon prefix: emoji(1) + space(1) = 2 chars
            if raw == "..":
                return os.path.dirname(_cwd[0])
            return os.path.normpath(os.path.join(_cwd[0], raw))

        def on_double(event):
            sel = browse_lb.curselection()
            if not sel:
                return
            full = _entry_path(sel[0])
            if os.path.isdir(full):
                refresh(full)

        def add_selected(event=None):
            sels = browse_lb.curselection()
            for i in sels:
                raw = browse_lb.get(i)[2:]
                if raw == "..":
                    continue
                full = _entry_path(i)
                if full not in selected:
                    selected.append(full)
                    sel_lb.insert("end", os.path.basename(full))

        def remove_selected(event=None):
            idxs = list(sel_lb.curselection())[::-1]
            for i in idxs:
                sel_lb.delete(i)
                del selected[i]

        browse_lb.bind("<Double-1>", on_double)
        browse_lb.bind("<Return>",   add_selected)

        def confirm():
            if selected:
                result_box[0] = list(selected)
            d.destroy()

        mk_btn(bot, "→ Add",   add_selected,    T, fg=T["BLUE"]).pack(side="left", padx=(8,0), pady=5)
        mk_btn(bot, "✕ Remove",remove_selected, T, fg=T["RED"]).pack(side="left", padx=(4,0), pady=5)
        mk_btn(bot, _lang.t("dlg.cancel"), d.destroy, T).pack(side="right", padx=(0,8), pady=5)
        mk_btn(bot, "Add to archive", confirm, T, fg=T["GREEN"]).pack(side="right", padx=(0,4), pady=5)

        refresh(_cwd[0])
        d.bind("<Escape>", lambda e: d.destroy())
        d.grab_set()
        self.root.wait_window(d)
        return result_box[0]

    def _cmd_create(self):
        if not self._methods:
            messagebox.showwarning("No methods", "No compression methods found in syc.ini",
                                   parent=self.root)
            return

        # Ask for source: folder OR files
        # Show a small picker dialog to choose between folder and files
        sources = self._pick_sources()
        if not sources:
            return

        # Build default archive path from first source
        first = sources[0] if isinstance(sources, list) else sources
        if os.path.isdir(first):
            name = os.path.basename(os.path.normpath(first))
            default_arc = os.path.join(os.path.dirname(first), name + ".syc")
        else:
            name = os.path.splitext(os.path.basename(first))[0]
            default_arc = os.path.join(os.path.dirname(first), name + ".syc")

        dlg = CompressDialog(self.root, self.T, self._ini_path, self._methods,
                             default_arc=default_arc)
        if not dlg.result:
            return

        r = dlg.result
        src_list = sources if isinstance(sources, list) else [sources]
        cmd = ["a", r["archive"]] + src_list + ["-m", r["method"],
               "-cfg", self._ini_path]
        if r["tar"]:      cmd.append("-tar")
        if r["crc32"]:    cmd.append("--crc32")
        if r["md5"]:      cmd.append("--md5")
        if r["chunk"]:    cmd += ["-chunk", r["chunk"]]
        if r["block"]:    cmd += ["-block", r["block"]]
        if r["dedup"]:    cmd += ["-dd",    r["dedup"]]
        if r["password"]:
            cmd += ["-key", r["password"]]
            if r.get("alg") and r["alg"] != "AES256":
                cmd += ["-ks", r["alg"]]
            if r.get("full_enc"):
                cmd.append("--full-encrypted")

        self._run_operation(cmd, _lang.t("op.compressing"),
                            on_done=lambda: self._open_first_part(r["archive"]))

    def _cmd_extract_sel(self):
        if not self.archive_path:
            return
        dest = os.path.dirname(self.archive_path)
        self._do_extract(dest, "+")

    def _cmd_extract_to(self):
        if not self.archive_path:
            return
        default = os.path.dirname(self.archive_path)
        dlg = ExtractDialog(self.root, self.T, default)
        if not dlg.result:
            return
        self._do_extract(dlg.result["dest"], dlg.result["overwrite"])

    def _do_extract(self, dest, overwrite):
        if not self.archive_path:
            return
        sel = self.tree.selection()
        cmd = ["x", self.archive_path, "-o", dest,
               "-cfg", self._ini_path,
               "-ow", overwrite]
        if self.password:
            cmd += ["-key", self.password]
        # Add -ff filters for selected files (skip folder rows)
        if sel:
            for iid in sel:
                if iid.startswith("f:"):
                    name = iid[2:]   # full path stored in iid
                    cmd += ["-ff", name]
                elif iid.startswith("d:"):
                    folder = iid[2:] + "/"
                    cmd += ["-ff", folder]
        self._run_operation(cmd, _lang.t("op.extracting"),
                            on_done=lambda: self._status(f"Extracted to: {dest}"))

    def _cmd_test(self):
        if not self.archive_path:
            return
        cmd = ["t", self.archive_path]
        if self.password:
            cmd += ["-key", self.password]
        self._run_operation(cmd, _lang.t("op.testing"),
                            on_done=lambda: self._status("Test passed ✓"))

    def _cmd_info(self):
        if not self.archive_path or not self.archive_data:
            return
        d = self.archive_data
        entries = d.get("entries", [])
        total_orig = sum(e.get("orig", 0) for e in entries)
        total_comp = sum(e.get("comp", 0) for e in entries)
        if d.get("tar_comp"):
            total_comp = d["tar_comp"]
        if d.get("dedup_mode"):
            mode_str = _lang.t("prop.dedup")
        elif d.get("tar_mode") and d.get("multiblock"):
            mode_str = _lang.t("prop.multiblock")
        elif d.get("tar_mode"):
            mode_str = _lang.t("prop.solid_tar")
        else:
            mode_str = _lang.t("prop.normal")
        info = dict(
            path    = self.archive_path,
            size    = os.path.getsize(self.archive_path),
            method  = d.get("method", "—"),
            mode    = mode_str,
            files   = len(entries),
            orig    = total_orig,
            comp    = total_comp or os.path.getsize(self.archive_path),
            comment = d.get("comment", ""),
            encrypted = d.get("encrypted", False),
        )
        PropertiesDialog(self.root, self.T, info)

    def _cmd_close_arc(self):
        self.archive_path = None
        self.archive_data = None
        self.password     = None
        self.tree.delete(*self.tree.get_children())
        self.titlebar.set_title("SYC Archive Manager")
        self._nav_path = ""
        self.var_path.set(_lang.t("nav.no_archive"))
        self.var_status.set(_lang.t("nav.ready"))
        self.var_count.set("")

    # ── Background runner ─────────────────────────────────────────────────────

    def _run_operation(self, syc_args, label, on_done=None):
        """
        Run syc command showing a sycg progress window.
        Falls back to background thread if sycg not found.
        """
        self._status(label)
        self.var_count.set("⏳")

        sycg     = self._find_sycg()
        sycg_py  = self._find_sycg_py()

        # Build the command to launch sycg
        sycg_cmd_prefix = None
        if sycg:
            sycg_cmd_prefix = [sycg]
        elif sycg_py:
            sycg_cmd_prefix = [sys.executable, sycg_py]

        if sycg_cmd_prefix:
            # Map syc commands to sycg commands (sycg uses 'b' for extract)
            sycg_args = list(syc_args)
            if sycg_args and sycg_args[0] == "x":
                sycg_args[0] = "b"

            extra = ["--title", label.rstrip("…"), "--close", "--nobackground"]
            # Inherit current language
            if self._lang_code != "EN":
                lang_path = _syl_path(self._lang_code)
                if lang_path:
                    extra += ["--lang", lang_path]
            # Inherit icon from psycg settings
            _icon_path = _cfg.get("app_icon", "").strip()
            if not _icon_path:
                _icon_path = os.path.join(_here(), "icon.ico")
            if _icon_path and os.path.exists(_icon_path):
                extra += ["--icon", _icon_path]
            cmd = sycg_cmd_prefix + sycg_args + extra
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"
            env["PYTHONUTF8"] = "1"

            def worker():
                flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                proc = subprocess.Popen(cmd, env=env)
                proc.wait()
                ok = proc.returncode == 0
                if ok:
                    self.root.after(0, lambda: self._status(_lang.t("nav.done")))
                    if on_done:
                        self.root.after(200, on_done)
                else:
                    self.root.after(0, lambda: self._status(_lang.t("op.failed")))
                self.root.after(0, lambda: self.var_count.set(""))

            threading.Thread(target=worker, daemon=True).start()

        elif True:  # no sycg found
            # Fallback: run syc silently in background
            def worker():
                result = _run_syc(syc_args)
                ok = result.returncode == 0
                if not ok:
                    err = (result.stderr or result.stdout or "Unknown error").strip()
                    self.root.after(0, lambda: messagebox.showerror(
                        "Error", err[:400], parent=self.root))
                    self.root.after(0, lambda: self._status(_lang.t("nav.error")))
                else:
                    self.root.after(0, lambda: self._status(_lang.t("nav.done")))
                    if on_done:
                        self.root.after(100, on_done)
                self.root.after(0, lambda: self.var_count.set(""))

            threading.Thread(target=worker, daemon=True).start()

    def _find_sycg(self):
        """Find sycg executable or sycg.py next to psycg"""
        here = _here()
        for name in ["sycg.exe", "sycg_x64.exe", "sycg_x86.exe"]:
            p = os.path.join(here, name)
            if os.path.exists(p):
                return p
        return None  # no sycg found

    def _find_sycg_py(self):
        """Find sycg.py for dev mode"""
        p = os.path.join(_here(), "sycg.py")
        return p if os.path.exists(p) else None

    # ── Misc helpers ──────────────────────────────────────────────────────────

    def _show_ctx(self, event):
        iid = self.tree.identify_row(event.y)
        if iid:
            if iid not in self.tree.selection():
                self.tree.selection_set(iid)
            self.ctx.post(event.x_root, event.y_root)

    def _ctx_copy_name(self):
        sel = self.tree.selection()
        if sel:
            iid = sel[0]
            if iid.startswith("d:"):
                name = iid[2:]
            elif iid.startswith("f:"):
                name = iid[2:]
            else:
                name = self.tree.item(iid, "text")
            self.root.clipboard_clear()
            self.root.clipboard_append(name)

    def _nav_enter(self, folder_path):
        """Navigate into a folder — repopulate tree from that path"""
        if not self.archive_data:
            return
        self._nav_path = folder_path
        self._populate_tree(self.archive_data, folder_path)
        self._update_pathbar()

    def _nav_up(self):
        """Navigate up one level"""
        if not self._nav_path:
            return
        parent = "/".join(self._nav_path.split("/")[:-1])
        self._nav_path = parent
        if self.archive_data:
            self._populate_tree(self.archive_data, parent)
        self._update_pathbar()

    def _update_pathbar(self):
        arc = self.archive_path or ""
        if self._nav_path:
            self.var_path.set(f"{arc}  ▸  {self._nav_path}/")
            self.btn_up.config(fg=self.T["BLUE"])
        else:
            self.var_path.set(arc or _lang.t("nav.no_archive"))
            self.btn_up.config(fg=self.T["DIM"])

    def _cmd_settings(self):
        def on_apply(new_theme, new_lang, new_name="", new_icon=""):
            # Apply language immediately
            global _lang
            _lang = SylParser()
            self._lang_code = new_lang
            if new_lang != "EN":
                path = _syl_path(new_lang)
                if path:
                    _lang.load(path)
            self._apply_lang()

            # Apply app identity immediately
            self._apply_app_identity(new_name, new_icon)

            # Theme change requires restart — show note
            resolved = detect_theme() if new_theme == "auto" else new_theme
            if resolved != self.theme:
                self._status(_lang.t("settings.restart_note"))
            else:
                self._status(_lang.t("nav.ready"))

        SettingsDialog(self.root, self.T, _cfg.get("theme", "auto"),
                       self._lang_code, on_apply,
                       current_app_name=_cfg.get("app_name", ""),
                       current_app_icon=_cfg.get("app_icon", ""))

    def _reload_archive(self):
        """F5: reload currently open archive from disk."""
        if self.archive_path and os.path.exists(self.archive_path):
            self._open_archive(self.archive_path)

    def _select_all(self):
        """Ctrl+A: select all visible tree items."""
        for iid in self.tree.get_children(""):
            self.tree.selection_add(iid)

    def _on_search(self):
        """Filter tree to show only entries matching the search string."""
        query = self._var_search.get().strip().lower()
        if not self.archive_data:
            return
        if not query:
            # Restore full tree
            self._populate_tree(self.archive_data, self._nav_path)
            return
        # Build flat list of matching entries
        entries = self._tree_entries if hasattr(self, "__tree_entries") else                   getattr(self, "_tree_entries", [])
        if not entries:
            return
        matched = [e for e in entries
                   if query in e["name"].lower() or
                   query in e["name"].split("/")[-1].lower()]
        # Temporarily show flat results
        self.tree.delete(*self.tree.get_children())
        method = self._tree_method if hasattr(self, "_tree_method") else ""
        enc    = self.archive_data.get("encrypted", False)
        for e in sorted(matched, key=lambda x: x["name"].lower()):
            name  = e["name"]
            orig  = e.get("orig", 0)
            comp  = e.get("comp", 0)
            ratio_val = (1 - comp / orig) * 100 if orig > 0 else None
            ratio = ("—" if ratio_val is None or not (-999 < ratio_val <= 100)
                     else f"{ratio_val:.1f}%")
            self.tree.insert(
                "", "end", iid=f"f:{name}",
                text=name,  # show full path in search results
                values=(_fmt_size(orig) if orig else "—",
                        _fmt_size(comp) if comp else "—",
                        ratio, method),
                tags=("encrypted" if enc else "file",),
            )

    def _on_lang_change(self, event=None):
        # Legacy handler kept for compatibility
        pass

    def _apply_lang(self):
        """Update all live UI text after a language change"""
        # Toolbar button labels
        for key, lbl in self._toolbar_labels.items():
            lbl.config(text=_lang.t(key))
        # Nav up button
        self.btn_up.config(text=_lang.t("nav.up"))
        # Treeview column headers
        self.tree.heading("#0",     text=_lang.t("col.name"))
        self.tree.heading("size",   text=_lang.t("col.original"))
        self.tree.heading("packed", text=_lang.t("col.packed"))
        self.tree.heading("ratio",  text=_lang.t("col.ratio"))
        self.tree.heading("method", text=_lang.t("col.method"))
        # Context menu
        self.ctx.entryconfig(0, label=_lang.t("ctx.extract_sel"))
        self.ctx.entryconfig(1, label=_lang.t("ctx.extract_to"))
        self.ctx.entryconfig(3, label=_lang.t("ctx.copy_name"))
        self.ctx.entryconfig(4, label=_lang.t("ctx.select_all"))
        # Title bar
        self.titlebar.set_title(_lang.t("title"))
        # Path bar and status
        self._update_pathbar()
        self._status(_lang.t("nav.ready"))
        # Clear search on language change
        if hasattr(self, "_var_search"):
            self._var_search.set("")

    def _on_double_click(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        iid = sel[0]
        if iid.startswith("d:"):
            # Double-click folder: navigate into it
            folder_path = iid[2:]
            self._nav_enter(folder_path)
            return
        # File: extract to temp and open
        name = iid[2:] if iid.startswith("f:") else self.tree.item(iid, "text")
        if not self.archive_path:
            return
        tmp = tempfile.mkdtemp(prefix="syc_preview_")
        if not hasattr(self, "_preview_dirs"):
            self._preview_dirs = []
        self._preview_dirs.append(tmp)
        cmd = ["x", self.archive_path, "-o", tmp,
               "-cfg", self._ini_path, "-ff", name]
        if self.password:
            cmd += ["-key", self.password]
        self._status(f"Opening {os.path.basename(name)}…")
        def worker():
            result = _run_syc(cmd)
            if result.returncode == 0:
                for root_d, _, files in os.walk(tmp):
                    for f in files:
                        fpath = os.path.join(root_d, f)
                        self.root.after(0, lambda p=fpath: self._open_file(p))
                        return
            else:
                self.root.after(0, lambda: self._status("Could not extract for preview"))
        threading.Thread(target=worker, daemon=True).start()

    def _open_file(self, path):
        try:
            if sys.platform == "win32":
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as e:
            messagebox.showwarning("Open", f"Could not open file:\n{e}", parent=self.root)

    def _on_resize(self, event):
        if event.widget is not self.root:
            return
        # Recalculate #0 column width = total - fixed columns
        try:
            total = self.tree.winfo_width()
            if total < 10:
                return
            fixed = sum(w for _, _, w, _ in self._fixed_cols) + 20  # +scrollbar
            name_w = max(120, total - fixed)
            self.tree.column("#0", width=name_w)
        except Exception:
            pass


    def _status(self, msg):
        self.var_status.set(msg)

    def _apply_app_identity(self, name: str, icon: str):
        """Apply custom app name and/or icon. Empty string = use default."""
        # ── Name ──────────────────────────────────────────────────────────────
        display_name = name.strip() if name.strip() else _lang.t("title")

        if not self.archive_path:
            self.titlebar.set_title(display_name)

        # Update taskbar title via both HWNDs (wrapper + client)
        if sys.platform == "win32":
            try:
                import ctypes
                for hwnd in (self.root.winfo_id(),
                             ctypes.windll.user32.GetParent(self.root.winfo_id())):
                    if hwnd:
                        ctypes.windll.user32.SetWindowTextW(hwnd, display_name)
            except Exception:
                pass

        # ── Icon ──────────────────────────────────────────────────────────────
        icon_path = icon.strip() if icon else ""
        if not icon_path:
            icon_path = os.path.join(_here(), "icon.ico")
        if not os.path.exists(icon_path):
            # No icon — revert titlebar to default ▣ mark
            self.titlebar.set_icon(None)
            return

        self._set_window_icon(icon_path)

    def _set_window_icon(self, path: str):
        """Set the taskbar/alt-tab icon for an overrideredirect tkinter window.

        Strategy:
          1. LoadImageW loads the .ico natively (no PIL needed, no size warnings).
          2. WM_SETICON is sent to BOTH the client HWND (winfo_id) AND the
             wrapper HWND (self._hwnd, which carries WS_EX_APPWINDOW for taskbar).
          3. SetClassLongPtrW updates the window-class icon so new toplevel
             windows inherit it too.
          4. PIL iconphoto fallback for non-.ico files.
        """
        import warnings, ctypes
        path_w = os.path.normpath(path)   # backslashes required by Win32 API

        if sys.platform != "win32":
            # Non-Windows: PIL fallback only
            self._set_icon_pil(path_w)
            return

        user32  = ctypes.windll.user32
        # Use c_size_t for all HWND/HANDLE values — pointer-sized on 32 and 64 bit
        user32.LoadImageW.restype  = ctypes.c_size_t
        user32.LoadImageW.argtypes = [ctypes.c_size_t, ctypes.c_wchar_p,
                                       ctypes.c_uint, ctypes.c_int,
                                       ctypes.c_int,  ctypes.c_uint]
        user32.SendMessageW.restype  = ctypes.c_size_t
        user32.SendMessageW.argtypes = [ctypes.c_size_t, ctypes.c_uint,
                                         ctypes.c_size_t, ctypes.c_size_t]
        user32.SetClassLongPtrW.restype  = ctypes.c_size_t
        user32.SetClassLongPtrW.argtypes = [ctypes.c_size_t, ctypes.c_int,
                                             ctypes.c_size_t]

        IMAGE_ICON      = 1
        LR_LOADFROMFILE = 0x0010
        LR_DEFAULTSIZE  = 0x0040
        WM_SETICON      = 0x0080
        ICON_SMALL      = 0
        ICON_BIG        = 1
        GCLP_HICON      = -14
        GCLP_HICONSM    = -34

        # Load one icon at default size (Windows picks 32x32 normally)
        hicon = user32.LoadImageW(0, path_w, IMAGE_ICON, 0, 0,
                                   LR_LOADFROMFILE | LR_DEFAULTSIZE)

        if not hicon:
            # .ico load failed — try PIL fallback
            self._set_icon_pil(path_w)
            return

        # The client HWND (the tk widget itself)
        hwnd_client  = self.root.winfo_id()
        # The wrapper HWND that was given WS_EX_APPWINDOW for taskbar visibility
        hwnd_wrapper = getattr(self, "_hwnd", 0) or 0

        for hwnd in filter(None, set([hwnd_client, hwnd_wrapper])):
            user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG,   hicon)
            user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, hicon)

        # Update window class icon so the taskbar entry inherits it
        try:
            user32.SetClassLongPtrW(hwnd_client, GCLP_HICON,   hicon)
            user32.SetClassLongPtrW(hwnd_client, GCLP_HICONSM, hicon)
        except Exception:
            pass

        # Show the icon in the custom title bar (16×16 PIL thumbnail)
        self._load_titlebar_icon(path_w)

    def _load_titlebar_icon(self, path_w: str):
        """Load a 16×16 PhotoImage and push it to the TitleBar widget."""
        try:
            import warnings
            from PIL import Image, ImageTk
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                img16 = Image.open(path_w).convert("RGBA").resize(
                    (16, 16), Image.LANCZOS)
            ph = ImageTk.PhotoImage(img16)
            self._titlebar_icon_photo = ph   # keep reference
            self.titlebar.set_icon(ph)
        except Exception:
            self.titlebar.set_icon(None)  # revert to ▣

    def _set_icon_pil(self, path_w: str):
        """PNG/any-format icon via PIL.
        Converts the image to a real Win32 HICON so SetClassLongPtrW works,
        giving a proper taskbar icon — not just an iconphoto placeholder."""
        import warnings, ctypes, io as _io
        try:
            from PIL import Image, ImageTk
        except ImportError:
            # No PIL — nothing we can do for PNG on Windows
            return

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            base = Image.open(path_w).convert("RGBA")

        if sys.platform == "win32":
            # ── Build HICON from raw BGRA bitmap via Win32 CreateIconFromResourceEx ──
            try:
                # Resize to 32x32 for the main icon
                img32 = base.resize((32, 32), Image.LANCZOS)
                # Convert RGBA → BGRA (Win32 expects BGRA)
                r, g, b, a = img32.split()
                bgra = Image.merge("RGBA", (b, g, r, a))
                raw  = bgra.tobytes()

                gdi32 = ctypes.windll.gdi32
                user32 = ctypes.windll.user32

                # CreateBitmap then convert to HICON via CreateIconIndirect
                BITMAPINFOHEADER = ctypes.c_byte * 40
                class ICONINFO(ctypes.Structure):
                    _fields_ = [("fIcon",    ctypes.c_bool),
                                 ("xHotspot", ctypes.c_uint),
                                 ("yHotspot", ctypes.c_uint),
                                 ("hbmMask",  ctypes.c_size_t),
                                 ("hbmColor", ctypes.c_size_t)]

                # Color bitmap (32-bit BGRA)
                hbm_color = gdi32.CreateBitmap(32, 32, 1, 32, raw)
                # Mask bitmap (all opaque — alpha handled by BGRA)
                mask_data = (ctypes.c_byte * (32 * 4))(0)
                hbm_mask  = gdi32.CreateBitmap(32, 4, 1, 1, mask_data)

                ii = ICONINFO(fIcon=True, xHotspot=0, yHotspot=0,
                              hbmMask=hbm_mask, hbmColor=hbm_color)
                user32.CreateIconIndirect.restype  = ctypes.c_size_t
                user32.CreateIconIndirect.argtypes = [ctypes.POINTER(ICONINFO)]
                hicon = user32.CreateIconIndirect(ctypes.byref(ii))

                gdi32.DeleteObject(hbm_color)
                gdi32.DeleteObject(hbm_mask)

                if hicon:
                    WM_SETICON = 0x0080
                    GCLP_HICON, GCLP_HICONSM = -14, -34
                    user32.SetClassLongPtrW.restype  = ctypes.c_size_t
                    user32.SetClassLongPtrW.argtypes = [ctypes.c_size_t,
                                                        ctypes.c_int, ctypes.c_size_t]
                    user32.SendMessageW.restype  = ctypes.c_size_t
                    user32.SendMessageW.argtypes = [ctypes.c_size_t, ctypes.c_uint,
                                                     ctypes.c_size_t, ctypes.c_size_t]
                    hwnd_client  = self.root.winfo_id()
                    hwnd_wrapper = getattr(self, "_hwnd", 0) or 0
                    for hwnd in filter(None, {hwnd_client, hwnd_wrapper}):
                        user32.SendMessageW(hwnd, WM_SETICON, 1, hicon)
                        user32.SendMessageW(hwnd, WM_SETICON, 0, hicon)
                    user32.SetClassLongPtrW(hwnd_client, GCLP_HICON,   hicon)
                    user32.SetClassLongPtrW(hwnd_client, GCLP_HICONSM, hicon)
                    return
            except Exception:
                pass  # fall through to iconphoto

        # ── Non-Windows or bitmap path failed: use iconphoto ──────────────────
        self._app_icon_photos = [
            ImageTk.PhotoImage(base.resize((sz, sz), Image.LANCZOS))
            for sz in (16, 32, 48)
        ]
        self.root.iconphoto(True, *self._app_icon_photos)
        # Also update titlebar
        self._load_titlebar_icon(path_w)

    def _minimize(self):
        """Minimize using ctypes on Windows (overrideredirect blocks iconify)"""
        if sys.platform == "win32":
            try:
                import ctypes
                hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
                ctypes.windll.user32.ShowWindow(hwnd, 6)  # SW_MINIMIZE = 6
            except Exception:
                pass
        else:
            self.root.iconify()

    def _on_close(self):
        # Clean up preview temp directories
        for d in getattr(self, "_preview_dirs", []):
            try:
                shutil.rmtree(d, ignore_errors=True)
            except Exception:
                pass
        self.root.destroy()


# ── Entry Point ────────────────────────────────────────────────────────────────
def main():
    import argparse
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("file",       nargs="?", default=None)
    ap.add_argument("--theme",    default=None)
    ap.add_argument("--lang",     default=None)
    args, _ = ap.parse_known_args()

    # Normalize lang arg: "ES" -> resolved path, or pass as-is if it's a file
    lang = args.lang
    if lang:
        if lang.endswith(".syl") and os.path.exists(lang):
            pass  # full path given
        else:
            code = lang.upper().replace(".SYL", "")
            lang = code  # pass code, __init__ resolves via _syl_path

    PSycG(open_file=args.file,
          theme=args.theme or "auto",
          lang=lang)

if __name__ == "__main__":
    main()