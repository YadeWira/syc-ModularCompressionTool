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
    "dark":  dict(
        BG="#1C1C1C", BG2="#252525", BG3="#2E2E2E", BG4="#333333",
        FG="#D8D8D8", DIM="#666666",
        GREEN="#5DC85D", BLUE="#4B9EE8", YELLOW="#DDB84A", RED="#D95F5F",
        TB="#111111",  TB_FG="#888888",
        SEL="#1E3A5F", SEL_FG="#D8D8D8",
        BORDER="#3A3A3A",
    ),
    "white": dict(
        BG="#F5F5F5", BG2="#E8E8E8", BG3="#DCDCDC", BG4="#D0D0D0",
        FG="#1A1A1A", DIM="#888888",
        GREEN="#2E7D32", BLUE="#1565C0", YELLOW="#F57F17", RED="#C62828",
        TB="#D0D0D0",  TB_FG="#444444",
        SEL="#C8DDEE", SEL_FG="#1A1A1A",
        BORDER="#BBBBBB",
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
    _DEFAULTS = {"theme": "auto", "lang": "EN"}

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
    FLAG_COMMENT  = 0x20

    with open(path, "rb") as f:
        magic = f.read(4)
        if magic != MAGIC:
            raise ValueError("Not a valid .syc file")
        flags      = struct.unpack("<B", f.read(1))[0]
        method_len = struct.unpack("<H", f.read(2))[0]
        method     = f.read(method_len).decode("utf-8")

        tar_mode  = bool(flags & FLAG_TAR)
        full_enc  = bool(flags & FLAG_FULL_ENC)
        enc       = bool(flags & FLAG_ENC)
        has_crc   = bool(flags & FLAG_CRC32)
        has_md5   = bool(flags & FLAG_MD5)
        has_comment = bool(flags & FLAG_COMMENT)

        comment = ""
        if has_comment:
            clen    = struct.unpack("<H", f.read(2))[0]
            comment = f.read(clen).decode("utf-8")

        entries = []
        if full_enc:
            # Can't read index without password
            return dict(method=method, tar_mode=tar_mode, comment=comment,
                        entries=[], encrypted=True, full_enc=True)

        num = struct.unpack("<I", f.read(4))[0]
        for _ in range(num):
            nlen = struct.unpack("<H", f.read(2))[0]
            name = f.read(nlen).decode("utf-8")
            orig = struct.unpack("<Q", f.read(8))[0]
            comp = struct.unpack("<Q", f.read(8))[0]
            crc  = struct.unpack("<I", f.read(4))[0] if has_crc else None
            md5  = f.read(16)                         if has_md5 else None
            if not tar_mode and not full_enc:
                # Skip compressed data
                skip = comp
                if enc and password:
                    skip = comp  # encrypted size stored
                f.seek(skip, 1)
            entries.append(dict(name=name, orig=orig, comp=comp, crc=crc))

        tar_orig = tar_comp = 0
        if tar_mode:
            tar_orig = struct.unpack("<Q", f.read(8))[0]
            tar_comp = struct.unpack("<Q", f.read(8))[0]
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
                tar_orig=tar_orig, tar_comp=tar_comp, file_size=file_size)


# ── Custom Title Bar (matches sycg.py) ────────────────────────────────────────
class TitleBar:
    def __init__(self, root, title, T, on_close, on_minimize):
        self.root = root
        self._drag_x = self._drag_y = 0

        bar = tk.Frame(root, bg=T["TB"], height=30)
        bar.pack(fill="x")
        bar.pack_propagate(False)

        tk.Label(bar, text="SYC", bg=T["TB"], fg=T["TB_FG"],
                 font=FS, anchor="w").pack(side="left", padx=(10, 2), pady=5)

        self.lbl = tk.Label(bar, text=title, bg=T["TB"], fg=T["TB_FG"],
                            font=FS, anchor="w")
        self.lbl.pack(side="left", pady=5)

        def mk_btn(txt, cmd, hover):
            b = tk.Label(bar, text=txt, bg=T["TB"], fg=T["TB_FG"],
                         font=("Consolas", 10), width=3, cursor="hand2")
            b.pack(side="right")
            b.bind("<Enter>",   lambda e: b.config(bg=hover, fg="white"))
            b.bind("<Leave>",   lambda e: b.config(bg=T["TB"], fg=T["TB_FG"]))
            b.bind("<Button-1>", lambda e: cmd())
            return b

        mk_btn("✕", on_close,    "#C0392B")
        mk_btn("□", root.wm_attributes if False else lambda: root.wm_state(
               "zoomed" if root.wm_state() == "normal" else "normal"), "#444444")
        mk_btn("—", on_minimize, "#333333")

        for w in (bar, self.lbl):
            w.bind("<ButtonPress-1>",  self._drag_start)
            w.bind("<B1-Motion>",      self._drag_move)

    def set_title(self, t): self.lbl.config(text=t)

    def _drag_start(self, e):
        self._drag_x = e.x_root - self.root.winfo_x()
        self._drag_y = e.y_root - self.root.winfo_y()

    def _drag_move(self, e):
        x = e.x_root - self._drag_x
        y = e.y_root - self._drag_y
        self.root.geometry(f"+{x}+{y}")


# ── Styled Widgets ─────────────────────────────────────────────────────────────
def mk_btn(parent, text, cmd, T, fg=None, width=None):
    kw = dict(bg=T["BG3"], fg=fg or T["FG"], font=FS, relief="flat", bd=0,
              padx=12, pady=5, cursor="hand2",
              activebackground=T["BG4"], activeforeground=fg or T["FG"],
              command=cmd)
    if width: kw["width"] = width
    b = tk.Button(parent, text=text, **kw)
    return b


def mk_sep(parent, T, vertical=False):
    if vertical:
        tk.Frame(parent, bg=T["BORDER"], width=1).pack(side="left", fill="y",
                                                        padx=4, pady=4)
    else:
        tk.Frame(parent, bg=T["BORDER"], height=1).pack(fill="x")


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
        tk.Label(tb, text="✕", bg=T["TB"], fg=T["TB_FG"], font=F, cursor="hand2",
                 width=3).pack(side="right")

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
    def __init__(self, parent, T, ini_path, methods):
        self.result = None
        d = tk.Toplevel(parent)
        d.overrideredirect(True)
        d.configure(bg=T["BG"])
        pw = parent.winfo_rootx() + parent.winfo_width()  // 2 - 240
        ph = parent.winfo_rooty() + parent.winfo_height() // 2 - 160
        d.geometry(f"480x370+{pw}+{ph}")

        tb = tk.Frame(d, bg=T["TB"], height=26); tb.pack(fill="x"); tb.pack_propagate(False)
        tk.Label(tb, text=_lang.t("dlg.create_title"), bg=T["TB"], fg=T["FG"],
                 font=FB, anchor="w").pack(side="left", padx=8, pady=4)
        tk.Label(tb, text="✕", bg=T["TB"], fg=T["TB_FG"], font=F, cursor="hand2",
                 width=3).pack(side="right")

        body = tk.Frame(d, bg=T["BG"]); body.pack(fill="both", expand=True, padx=16, pady=12)

        def row(label, widget_fn, pady=4):
            tk.Label(body, text=label, bg=T["BG"], fg=T["DIM"],
                     font=FS, anchor="w").pack(fill="x", pady=(pady, 0))
            return widget_fn()

        # Archive path
        v_arc = tk.StringVar()
        def arc_w():
            fr = tk.Frame(body, bg=T["BG"]); fr.pack(fill="x", pady=(2, 4))
            e = tk.Entry(fr, textvariable=v_arc, bg=T["BG3"], fg=T["FG"],
                         font=F, relief="flat", bd=0, insertbackground=T["FG"])
            e.pack(side="left", fill="x", expand=True, ipady=4, padx=(0, 4))
            def browse():
                p = filedialog.asksaveasfilename(defaultextension=".syc",
                    filetypes=[("SYC Archive", "*.syc")])
                if p: v_arc.set(p)
            mk_btn(fr, "...", browse, T).pack(side="right")
        row(_lang.t("dlg.arc_path"), arc_w)

        # Method
        v_method = tk.StringVar(value=methods[0] if methods else "xpszf1")
        def meth_w():
            cb = ttk.Combobox(body, textvariable=v_method, values=methods,
                              state="readonly", font=F)
            style = ttk.Style(); style.theme_use("default")
            style.configure("TCombobox", fieldbackground=T["BG3"],
                            background=T["BG3"], foreground=T["FG"],
                            arrowcolor=T["FG"])
            cb.pack(fill="x", pady=(2, 4), ipady=3)
        row(_lang.t("dlg.method"), meth_w)

        # Options row
        opt_fr = tk.Frame(body, bg=T["BG"]); opt_fr.pack(fill="x", pady=(4, 0))
        v_tar    = tk.BooleanVar(value=True)
        v_crc    = tk.BooleanVar()
        v_md5    = tk.BooleanVar()
        v_key    = tk.BooleanVar()
        kw_cb = dict(bg=T["BG"], fg=T["FG"], font=FS, activebackground=T["BG"],
                     activeforeground=T["GREEN"], selectcolor=T["BG3"],
                     relief="flat", bd=0)
        tk.Checkbutton(opt_fr, text=_lang.t("dlg.solid"), variable=v_tar, **kw_cb).pack(side="left")
        tk.Checkbutton(opt_fr, text="CRC32", variable=v_crc, **kw_cb).pack(side="left", padx=(12, 0))
        tk.Checkbutton(opt_fr, text="MD5",   variable=v_md5, **kw_cb).pack(side="left", padx=(8, 0))
        tk.Checkbutton(opt_fr, text=_lang.t("dlg.encrypt"), variable=v_key, **kw_cb).pack(side="left", padx=(8, 0))

        # Chunk / split row
        chunk_fr = tk.Frame(body, bg=T["BG"]); chunk_fr.pack(fill="x", pady=(6, 0))
        v_chunk_en = tk.BooleanVar()
        v_chunk    = tk.StringVar(value="700MB")
        kw_cb2 = dict(bg=T["BG"], fg=T["FG"], font=FS, activebackground=T["BG"],
                      activeforeground=T["GREEN"], selectcolor=T["BG3"],
                      relief="flat", bd=0)
        tk.Checkbutton(chunk_fr, text=_lang.t("dlg.split"),
                       variable=v_chunk_en, **kw_cb2).pack(side="left")
        chunk_entry = tk.Entry(chunk_fr, textvariable=v_chunk,
                               bg=T["BG3"], fg=T["FG"], font=F,
                               relief="flat", bd=0, insertbackground=T["FG"],
                               width=8, state="disabled")
        chunk_entry.pack(side="left", padx=(6, 0), ipady=3)
        tk.Label(chunk_fr, text=_lang.t("dlg.split_hint"),
                 bg=T["BG"], fg=T["DIM"], font=FS).pack(side="left", padx=(4, 0))
        def toggle_chunk(*_):
            chunk_entry.config(state="normal" if v_chunk_en.get() else "disabled")
        v_chunk_en.trace_add("write", toggle_chunk)

        # Chunk requires ?? in archive name — auto-add if missing
        def validate_chunk_name(arc, method_chunk):
            if method_chunk and "??" not in arc:
                base, ext = os.path.splitext(arc)
                return base + "??" + ext
            return arc

        # Password
        v_pass = tk.StringVar()
        def pass_w():
            e = tk.Entry(body, textvariable=v_pass, show="•",
                         bg=T["BG3"], fg=T["FG"], font=F,
                         relief="flat", bd=0, insertbackground=T["FG"],
                         state="disabled")
            e.pack(fill="x", pady=(2, 4), ipady=4)
            def toggle(*_):
                e.config(state="normal" if v_key.get() else "disabled")
            v_key.trace_add("write", toggle)
            return e
        row(_lang.t("dlg.pass_label"), pass_w)

        # Buttons
        bf = tk.Frame(body, bg=T["BG"]); bf.pack(fill="x", side="bottom", pady=(8, 0))
        def ok():
            if not v_arc.get():
                messagebox.showerror("Error", "Please specify an archive path", parent=d)
                return
            chunk = v_chunk.get().strip() if v_chunk_en.get() else None
            arc   = validate_chunk_name(v_arc.get(), chunk)
            self.result = dict(
                archive=arc, method=v_method.get(),
                tar=v_tar.get(), crc32=v_crc.get(),
                md5=v_md5.get(), password=v_pass.get() if v_key.get() else None,
                chunk=chunk,
            )
            d.destroy()
        mk_btn(bf, _lang.t("dlg.create"), ok,        T, fg=T["GREEN"]).pack(side="right")
        mk_btn(bf, _lang.t("dlg.cancel"), d.destroy, T).pack(side="right", padx=(0, 6))

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
        tk.Label(tb, text="✕", bg=T["TB"], fg=T["TB_FG"], font=F, cursor="hand2",
                 width=3).pack(side="right")

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
    def __init__(self, parent, T, current_theme, current_lang, on_apply):
        self.result = None
        d = tk.Toplevel(parent)
        d.overrideredirect(True)
        d.configure(bg=T["BG"])
        pw = parent.winfo_rootx() + parent.winfo_width()  // 2 - 220
        ph = parent.winfo_rooty() + parent.winfo_height() // 2 - 140
        d.geometry(f"440x280+{pw}+{ph}")

        # Title bar
        tb = tk.Frame(d, bg=T["TB"], height=26); tb.pack(fill="x"); tb.pack_propagate(False)
        tk.Label(tb, text="⚙  " + _lang.t("settings.title"), bg=T["TB"], fg=T["FG"],
                 font=FB, anchor="w").pack(side="left", padx=8, pady=4)
        tk.Label(tb, text="✕", bg=T["TB"], fg=T["TB_FG"], font=F, cursor="hand2",
                 width=3).pack(side="right").bind if False else None
        x_lbl = tk.Label(tb, text="✕", bg=T["TB"], fg=T["TB_FG"], font=F,
                         cursor="hand2", width=3)
        x_lbl.pack(side="right")
        x_lbl.bind("<Button-1>", lambda e: d.destroy())

        body = tk.Frame(d, bg=T["BG"]); body.pack(fill="both", expand=True, padx=20, pady=16)

        def section_label(text):
            tk.Label(body, text=text, bg=T["BG"], fg=T["DIM"],
                     font=FS, anchor="w").pack(fill="x", pady=(8, 2))

        def separator():
            tk.Frame(body, bg=T["BORDER"], height=1).pack(fill="x", pady=4)

        # ── Theme ──────────────────────────────────────────────────────────────
        section_label(_lang.t("settings.theme"))
        v_theme = tk.StringVar(value=current_theme)
        tf = tk.Frame(body, bg=T["BG"]); tf.pack(fill="x")
        kw_r = dict(bg=T["BG"], fg=T["FG"], font=F, activebackground=T["BG"],
                    selectcolor=T["BG3"], relief="flat", bd=0)
        for val, lbl_key in [("dark","settings.theme_dark"),
                              ("white","settings.theme_white"),
                              ("auto","settings.theme_auto")]:
            tk.Radiobutton(tf, text=_lang.t(lbl_key), variable=v_theme,
                           value=val, **kw_r).pack(side="left", padx=(0, 16))

        separator()

        # ── Language ───────────────────────────────────────────────────────────
        section_label(_lang.t("settings.language"))

        # Discover available .syl files in lang/ or same dir
        available = [("EN", "English")]
        seen = {"EN"}
        for base in [_lang_dir(), _here()]:
            if os.path.isdir(base):
                for fname in sorted(os.listdir(base)):
                    if fname.upper().endswith(".SYL"):
                        code = os.path.splitext(fname)[0].upper()
                        if code not in seen:
                            seen.add(code)
                            display = LANGS.get(code, code)
                            available.append((code, display))

        v_lang = tk.StringVar(value=current_lang)
        lf = tk.Frame(body, bg=T["BG"]); lf.pack(fill="x", pady=(0, 4))

        lang_codes   = [c for c, _ in available]
        lang_labels  = [f"{c} — {n}" for c, n in available]

        # Set current selection
        cur_idx = lang_codes.index(current_lang) if current_lang in lang_codes else 0
        v_lang_display = tk.StringVar(value=lang_labels[cur_idx])

        style = ttk.Style(); style.theme_use("default")
        style.configure("TCombobox", fieldbackground=T["BG3"],
                        background=T["BG3"], foreground=T["FG"],
                        arrowcolor=T["FG"])
        lang_cb = ttk.Combobox(lf, textvariable=v_lang_display,
                               values=lang_labels, state="readonly", font=F)
        lang_cb.pack(fill="x", ipady=3)

        def on_lang_select(e):
            idx = lang_labels.index(v_lang_display.get())
            v_lang.set(lang_codes[idx])
        lang_cb.bind("<<ComboboxSelected>>", on_lang_select)

        tk.Label(body, text=_lang.t("settings.lang_note"),
                 bg=T["BG"], fg=T["DIM"], font=FS, anchor="w").pack(fill="x")

        separator()

        # ── Buttons ────────────────────────────────────────────────────────────
        bf = tk.Frame(body, bg=T["BG"]); bf.pack(fill="x", side="bottom", pady=(4, 0))

        def apply():
            chosen_theme = v_theme.get()
            chosen_lang  = v_lang.get()
            _cfg.set("theme", chosen_theme)
            _cfg.set("lang",  chosen_lang)
            _cfg.save()
            d.destroy()
            on_apply(chosen_theme, chosen_lang)

        mk_btn(bf, _lang.t("dlg.ok"),     apply,     T, fg=T["GREEN"]).pack(side="right")
        mk_btn(bf, _lang.t("dlg.cancel"), d.destroy, T).pack(side="right", padx=(0, 6))
        d.bind("<Return>", lambda e: apply())
        d.bind("<Escape>", lambda e: d.destroy())
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
            T, self._on_close, self.root.iconify)

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
        self.tree.bind("<Button-3>", self._show_ctx)
        self.tree.bind("<Double-1>", self._on_double_click)
        self.tree.bind("<Return>",   self._on_double_click)

        # Drag-and-drop hint
        self.root.drop_target_register = lambda *a: None  # no-op if dnd not available
        try:
            self.root.dnd_bind = lambda *a: None
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
        tk.Label(sb, textvariable=self.var_count,  bg=T["BG2"], fg=T["DIM"],
                 font=FS, anchor="e").pack(side="right", padx=8)

    # ── Treeview styling ──────────────────────────────────────────────────────

    def _setup_treeview_style(self):
        T = self.T
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview",
                        background=T["BG"],
                        foreground=T["FG"],
                        fieldbackground=T["BG"],
                        font=FS,
                        rowheight=22,
                        borderwidth=0,
                        indent=16,
                        relief="flat")
        style.configure("Treeview.Heading",
                        background=T["BG2"],
                        foreground=T["DIM"],
                        font=FS,
                        relief="flat",
                        borderwidth=0)
        style.map("Treeview",
                  background=[("selected", T["SEL"])],
                  foreground=[("selected", T["SEL_FG"])])
        style.map("Treeview.Heading",
                  background=[("active", T["BG3"])])
        for sb in ("Vertical.TScrollbar", "Horizontal.TScrollbar"):
            style.configure(sb,
                            background=T["BG3"], troughcolor=T["BG"],
                            arrowcolor=T["DIM"], borderwidth=0,
                            relief="flat", width=10)
            style.map(sb,
                      background=[("active", T["BG4"]),
                                  ("pressed", T["BLUE"])])

        # Combobox theme
        style.configure("TCombobox",
                        fieldbackground=T["BG3"], background=T["BG3"],
                        foreground=T["FG"], arrowcolor=T["FG"],
                        borderwidth=0, relief="flat",
                        selectbackground=T["SEL"],
                        selectforeground=T["SEL_FG"])
        style.map("TCombobox",
                  fieldbackground=[("readonly", T["BG3"])],
                  background=[("active", T["BG4"])],
                  foreground=[("disabled", T["DIM"])])

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
        """Build hierarchical tree showing children of focus_path."""
        self.tree.delete(*self.tree.get_children())
        T = self.T
        method  = data.get("method", "")
        entries = data.get("entries", [])

        # Normalize all paths
        norm = [{**e, "name": e["name"].replace("\\", "/").strip("/")}
                for e in entries]

        self._build_subtree("", focus_path, norm, method, data)

        self.tree.tag_configure("folder",    foreground=T["BLUE"])
        self.tree.tag_configure("file",      foreground=T["FG"])
        self.tree.tag_configure("encrypted", foreground=T["YELLOW"])

    def _build_subtree(self, parent_iid, root_path, entries, method, data):
        """
        Insert folders and files under parent_iid.
        root_path: the folder prefix we are currently showing (e.g. "EL" or "")
        """
        T = self.T

        # Collect direct children of root_path
        folders = {}   # folder_name -> set of entries inside
        files   = []   # entries directly in root_path

        prefix = (root_path + "/") if root_path else ""

        for e in entries:
            name = e["name"]
            if root_path and not name.startswith(prefix):
                continue
            rel = name[len(prefix):]  # relative to current root
            if "/" in rel:
                # It's in a subfolder
                folder = rel.split("/")[0]
                folders.setdefault(folder, []).append(e)
            else:
                files.append(e)

        # Insert folders first (sorted)
        for folder in sorted(folders.keys()):
            full_path = (prefix + folder) if prefix else folder
            iid = f"d:{full_path}"
            # Folder stats: sum of children
            children = folders[folder]
            f_orig = sum(c.get("orig", 0) for c in children)
            f_comp = sum(c.get("comp", 0) for c in children)
            f_ratio_val = (1 - f_comp/f_orig)*100 if f_orig > 0 else None
            if f_ratio_val is None or f_ratio_val < -999 or f_ratio_val > 100:
                f_ratio = "—"
            else:
                f_ratio = f"{f_ratio_val:.1f}%"
            self.tree.insert(
                parent_iid, "end",
                iid=iid,
                text=folder + "/",
                values=(_fmt_size(f_orig) if f_orig else "—",
                        _fmt_size(f_comp) if f_comp else "—",
                        f_ratio, ""),
                open=False,
                tags=("folder",),
            )
            # Recursively insert children (collapsed by default)
            self._build_subtree(iid, full_path, entries, method, data)

        # Insert files (sorted)
        for e in sorted(files, key=lambda x: x["name"].split("/")[-1]):
            name  = e["name"]
            fname = name.split("/")[-1]
            orig  = e.get("orig", 0)
            comp  = e.get("comp", 0)
            ratio_val = (1 - comp/orig)*100 if orig > 0 else None
            if ratio_val is None or ratio_val < -999 or ratio_val > 100:
                ratio = "—"
            else:
                ratio = f"{ratio_val:.1f}%"
            tag   = "encrypted" if data.get("encrypted") else "file"
            self.tree.insert(
                parent_iid, "end",
                iid=f"f:{name}",
                text=fname,
                values=(_fmt_size(orig) if orig else "—",
                        _fmt_size(comp) if comp else "—",
                        ratio, method),
                tags=(tag,),
            )

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

    def _cmd_create(self):
        if not self._methods:
            messagebox.showwarning("No methods", "No compression methods found in syc.ini",
                                   parent=self.root)
            return

        # Ask for source files/folders first
        sources = filedialog.askdirectory(title="Select folder to compress",
                                          parent=self.root)
        if not sources:
            return

        dlg = CompressDialog(self.root, self.T, self._ini_path, self._methods)
        if not dlg.result:
            return

        r = dlg.result
        cmd = ["a", r["archive"], sources, "-m", r["method"],
               "-cfg", self._ini_path]
        if r["tar"]:      cmd.append("-tar")
        if r["crc32"]:    cmd.append("--crc32")
        if r["md5"]:      cmd.append("--md5")
        if r["chunk"]:    cmd += ["-chunk", r["chunk"]]
        if r["password"]: cmd += ["-key", r["password"]]

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
        info = dict(
            path    = self.archive_path,
            size    = os.path.getsize(self.archive_path),
            method  = d.get("method", "—"),
            mode    = "solid tar" if d.get("tar_mode") else "normal",
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
        def on_apply(new_theme, new_lang):
            # Apply language immediately
            global _lang
            _lang = SylParser()
            self._lang_code = new_lang
            if new_lang != "EN":
                path = _syl_path(new_lang)
                if path:
                    _lang.load(path)
            self._apply_lang()

            # Theme change requires restart — show note
            resolved = detect_theme() if new_theme == "auto" else new_theme
            if resolved != self.theme:
                self._status(_lang.t("settings.restart_note"))
            else:
                self._status(_lang.t("nav.ready"))

        SettingsDialog(self.root, self.T, _cfg.get("theme", "auto"),
                       self._lang_code, on_apply)

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
        # Title bar
        self.titlebar.set_title(_lang.t("title"))
        # Path bar and status
        self._update_pathbar()
        self._status(_lang.t("nav.ready"))

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
        cmd = ["x", self.archive_path, "-o", tmp,
               "-cfg", self._ini_path, "-ff", name.split("/")[-1]]
        if self.password:
            cmd += ["-key", self.password]
        self._status(f"Opening {os.path.basename(name)}…")
        def worker():
            result = _run_syc(cmd)
            if result.returncode == 0:
                # Find extracted file
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

    def _on_close(self):
        self.root.destroy()


# ── Entry Point ────────────────────────────────────────────────────────────────
def main():
    import argparse
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("file",    nargs="?", default=None)
    ap.add_argument("--theme", default=None,
                    help="Theme override: dark, white, auto")
    ap.add_argument("--lang",  default=None,
                    help="Language code (EN/ES/FR/PT/RU) or path to .syl file")
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