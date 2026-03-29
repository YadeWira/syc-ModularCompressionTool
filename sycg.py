"""
sycg.py - GUI wrapper para SYC (estilo 7-Zip)
"""

import sys, os, subprocess, threading, time, re
import tkinter as tk
from tkinter import ttk, messagebox

# Cuando se compila con PyInstaller, __file__ apunta al directorio temporal _MEI
# sys.executable apunta al .exe real — usarlo para encontrar syc.exe
if getattr(sys, "frozen", False):
    _HERE = os.path.dirname(sys.executable)
else:
    _HERE = os.path.dirname(os.path.abspath(__file__))

# ─── Language loader ─────────────────────────────────────────────────────────

class Lang:
    """Loads a .syl language file and provides string lookups."""
    _DEFAULTS = {
        "window.compressing": "Compressing",  "window.extracting": "Extracting",
        "window.listing":     "Listing",      "window.verifying":  "Verifying",
        "window.completed":   "Completed",    "window.elapsed":    "elapsed",
        "metrics.processed":  "Processed:",   "metrics.compressed":"Compressed:",
        "metrics.bytes":      "Bytes:",       "metrics.elapsed":   "Elapsed:",
        "metrics.ratio":      "Ratio:",       "metrics.speed":     "Speed:",
        "buttons.background": "Background",   "buttons.pause":     "Pause",
        "buttons.resume":     "Resume",       "buttons.cancel":    "Cancel",
        "buttons.close":      "Close",        "buttons.close_in":  "Close ({n}s)",
        "status.initializing":"Initializing...","status.done":     "✓  Completed in {time}",
        "status.error":       "✗  {msg}",
        "confirm.cancel_title":"Cancel",      "confirm.cancel_msg":"Cancel the operation?",
    }

    def __init__(self, path: str = None):
        self._strings = dict(self._DEFAULTS)
        if path and os.path.exists(path):
            section = ""
            with open(path, encoding="utf-8", errors="replace") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith(";"):
                        continue
                    if line.startswith("[") and line.endswith("]"):
                        section = line[1:-1].lower()
                        continue
                    if "=" in line:
                        k, _, v = line.partition("=")
                        k = k.strip().lower()
                        v = v.strip()
                        if section == "sycg":
                            # "window_compressing" → "window.compressing"
                            # matches the keys sycg looks up directly
                            self._strings[k.replace("_", ".", 1)] = v
                        else:
                            self._strings[f"{section}.{k}"] = v

    def t(self, key: str, **kwargs) -> str:
        s = self._strings.get(key, key)
        for k, v in kwargs.items():
            s = s.replace("{" + k + "}", str(v))
        return s

_lang = Lang()  # default English, replaced by --lang


# Buscar syc en este orden:
# 1. syc.exe          (produccion, mismo directorio)
# 2. syc_x64.exe      (build, mismo directorio)
# 3. syc_x86.exe      (build, mismo directorio)
# 4. syc.py           (desarrollo)
import struct as _struct
_ARCH = "x64" if _struct.calcsize("P")*8 == 64 else "x86"

def _find_syc():
    # Solo buscar syc.exe o syc.py — sin variantes de arquitectura
    syc_exe = os.path.join(_HERE, "syc.exe")
    syc_py  = os.path.join(_HERE, "syc.py")
    if os.path.exists(syc_exe):
        return [syc_exe]
    if os.path.exists(syc_py):
        return [sys.executable, syc_py]
    return None

SYC_CMD = _find_syc()
if not SYC_CMD:
    import tkinter as _tk
    from tkinter import messagebox as _mb
    _r = _tk.Tk(); _r.withdraw()
    _path = os.path.join(_HERE, "syc.exe")
    _mb.showerror("SYCG", f"syc.exe not found.\n\nExpected location:\n{_path}")
    _r.destroy()
    sys.exit(1)

def fmt_size(n):
    for u in ["B","KB","MB","GB","TB"]:
        if n < 1024: return f"{n:.2f} {u}"
        n /= 1024
    return f"{n:.2f} PB"

def fmt_time(s):
    s=int(s); h,r=divmod(s,3600); m,s=divmod(r,60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"0:{m:02d}:{s:02d}"

class P:
    def __init__(self):
        self.pct=0.0; self.step=""; self.speed=0.0; self.written=0.0
        self.total=0.0; self.comp=0.0; self.ratio=0.0; self.status=""
        self.done=False; self.error=""
    def feed(self,line):
        line=line.strip()
        if not line: return
        m=re.match(r'^\[INFO\]\s+(\d+(?:\.\d+)?)%\s*$',line)
        if m: self.pct=float(m.group(1)); return
        m=re.match(r'^\[INFO\]\s+(\[[\+\-]\])\s+(.+?)\s+\((\w+)\)',line)
        if m: self.step=f"{m.group(1)} {m.group(2)} ({m.group(3)})"; self.status=self.step; return
        m=re.match(r'^\[INFO\]\s+\d+:\d+\s+([\d.]+)\s+\w+\s+escrito\s+([\d.]+)',line)
        if m: self.written=float(m.group(1)); self.speed=float(m.group(2)); return
        m=re.match(r'^\[INFO\]\s+\d+:\d+\s+([\d.]+)\s+\w+\s*/\s*([\d.]+)\s+\w+\s*\(([\d.]+)%\)\s+([\d.]+)',line)
        if m: self.written=float(m.group(1)); self.total=float(m.group(2)); self.ratio=float(m.group(3)); self.speed=float(m.group(4)); return
        m=re.match(r'^\[INFO\]\s+([\d.]+)\s+\w+\s*->\s*([\d.]+)\s+\w+\s*\(([\d.]+)%',line)
        if m: self.total=float(m.group(1)); self.comp=float(m.group(2)); self.ratio=float(m.group(3)); return
        m=re.match(r'^\[INFO\]\s+Total:\s+([\d.]+)\s+\w+\s*->\s*([\d.]+)\s+\w+\s*\(([\d.]+)%',line)
        if m: self.total=float(m.group(1)); self.comp=float(m.group(2)); self.ratio=float(m.group(3)); return
        m=re.match(r'^\[INFO\]\s+Modo s.lido.*?empaquetando\s+(\d+)\s+archivos\s+\(([\d.]+)',line)
        if m: self.status=f"Empaquetando {m.group(1)} archivos ({m.group(2)} MB)..."; return
        # Total Progress normal mode: [INFO]   Total Progress - 45.2%  [45/100]
        m=re.match(r'^\[INFO\]\s+Total Progress\s*-\s*([\d.]+)%',line)
        if m: self.pct=float(m.group(1)); return
        # Archivo actual modo normal: [INFO]   Comprimiendo: ruta (size)
        m=re.match(r'^\[INFO\]\s+(?:Comprimiendo|Extrayendo):\s+(.+?)\s+\(',line)
        if m: self.step=m.group(1); return
        if "Archivo creado:" in line or "Extracción completada" in line:
            self.done=True; self.pct=100.0; self.status=line.replace("[INFO]","").strip(); return
        if "ERROR:" in line: self.error=line.replace("[INFO]","").strip()

class SycWindow:
    # Dark theme defaults (overridden by _apply_theme)
    BG="#1C1C1C"; BG2="#252525"; BG3="#2E2E2E"; BG4="#333333"; BG5="#3A3A3A"
    FG="#D8D8D8"; DIM="#666666"
    GREEN="#5DC85D"; BLUE="#4B9EE8"; YELLOW="#DDB84A"; RED="#D95F5F"
    BLUE_DIM="#1E3A5F"; HIGHLIGHT="#383838"; SHADOW="#111111"
    BORDER="#3A3A3A"; BORDER_LIGHT="#444444"
    F=("Consolas",9); FB=("Consolas",9,"bold"); FS=("Consolas",8)

    _THEMES = {
        "dark":  dict(BG="#1C1C1C",BG2="#252525",BG3="#2E2E2E",BG4="#333333",BG5="#3A3A3A",
                      FG="#D8D8D8",DIM="#666666",
                      GREEN="#5DC85D",BLUE="#4B9EE8",YELLOW="#DDB84A",RED="#D95F5F",
                      BLUE_DIM="#1E3A5F",
                      TB="#111111",TB_FG="#888888",
                      BORDER="#3A3A3A",BORDER_LIGHT="#444444",
                      SHADOW="#111111",HIGHLIGHT="#383838"),
        "white": dict(BG="#F5F5F5",BG2="#E8E8E8",BG3="#DCDCDC",BG4="#D0D0D0",BG5="#C4C4C4",
                      FG="#1A1A1A",DIM="#888888",
                      GREEN="#2E7D32",BLUE="#1565C0",YELLOW="#F57F17",RED="#C62828",
                      BLUE_DIM="#C8DDEE",
                      TB="#D0D0D0",TB_FG="#444444",
                      BORDER="#BBBBBB",BORDER_LIGHT="#CACACA",
                      SHADOW="#AAAAAA",HIGHLIGHT="#F0F0F0"),
    }

    def _apply_theme(self, theme: str):
        if theme == "auto":
            try:
                import winreg
                k = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
                val, _ = winreg.QueryValueEx(k, "AppsUseLightTheme")
                winreg.CloseKey(k)
                theme = "white" if val == 1 else "dark"
            except Exception:
                theme = "dark"
        t = self._THEMES.get(theme, self._THEMES["dark"])
        for k, v in t.items():
            setattr(self, k, v)
        self._tb_bg = t.get("TB",  "#111111")
        self._tb_fg = t.get("TB_FG", "#888888")

    def __init__(self, title, op, args, auto_close=False,
                 no_cancel=False, no_pause=False, no_background=False,
                 icon=None, theme="dark"):
        self.op=op; self.args=args; self.p=P()
        self.proc=None; self.paused=False; self.cancelled=False
        self.t0=time.time(); self._shown=False; self.auto_close=auto_close
        self.no_cancel=no_cancel; self.no_pause=no_pause; self.no_background=no_background
        self.icon_path=icon; self.theme=theme
        self._apply_theme(theme)

        r=self.root=tk.Tk()
        r.overrideredirect(True)
        r.configure(bg=self.BG)
        r.configure(highlightbackground=self.BORDER)
        W,H=500,278
        sx,sy=r.winfo_screenwidth(),r.winfo_screenheight()
        r.geometry(f"{W}x{H}+{(sx-W)//2}+{(sy-H)//2}")
        r.configure(highlightbackground=self.BORDER, highlightthickness=1)
        self._drag_x=0; self._drag_y=0; self._title_text=title
        # Rounded corners
        # Icono de ventana (taskbar)
        if self.icon_path and os.path.exists(self.icon_path):
            try:
                ext = self.icon_path.lower().split(".")[-1]
                if ext == "ico":
                    r.iconbitmap(self.icon_path)
                elif ext == "png":
                    _img = tk.PhotoImage(file=self.icon_path)
                    r.iconphoto(True, _img)
                    r._icon_ref = _img
            except Exception: pass

        self._ui(); self._launch()
        r.after(150, self._tick); r.mainloop()

    def _ui(self):
        # ── Barra de título personalizada ─────────────────────────────────
        tb=tk.Frame(self.root,bg=self._tb_bg,height=30)
        tb.pack(fill="x"); tb.pack_propagate(False)

        # Icono personalizado o texto SYC
        ico_img = None
        if self.icon_path and os.path.exists(self.icon_path):
            ext = self.icon_path.lower().split(".")[-1]
            try:
                if ext == "png":
                    raw = tk.PhotoImage(file=self.icon_path)
                    # Escalar a 16x16 aprox
                    w,h = raw.width(), raw.height()
                    sub = max(1, min(w,h)//16)
                    ico_img = raw.subsample(sub, sub)
                elif ext in ("ico","gif","bmp"):
                    # Intentar PIL si está disponible
                    import warnings
                    from PIL import Image, ImageTk
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        img = Image.open(self.icon_path).resize((16,16), Image.LANCZOS)
                    ico_img = ImageTk.PhotoImage(img)
            except Exception:
                pass

        if ico_img:
            lbl_ico=tk.Label(tb,image=ico_img,bg=self._tb_bg)
            lbl_ico.pack(side="left",padx=(6,2),pady=4)
            lbl_ico.image=ico_img  # keep reference
        else:
            tk.Label(tb,text="SYC",bg=self._tb_bg,fg=self._tb_fg,
                     font=("Consolas",8),anchor="w").pack(side="left",padx=(10,4),pady=5)

        self.lbl_title=tk.Label(tb,text=self._title_text,bg=self._tb_bg,
                                fg=self._tb_fg,font=("Consolas",8),anchor="w")
        self.lbl_title.pack(side="left",pady=5)

        # Botones de ventana
        def mk_btn(parent, txt, cmd, hover_bg):
            b=tk.Label(parent,text=txt,bg=self._tb_bg,fg=self._tb_fg,
                       font=("Consolas",10),width=3,cursor="hand2")
            b.pack(side="right")
            b.bind("<Enter>",  lambda e: b.config(bg=hover_bg, fg="white"))
            b.bind("<Leave>",  lambda e: b.config(bg=self._tb_bg, fg=self._tb_fg))
            b.bind("<Button-1>", lambda e: cmd())
            return b

        mk_btn(tb, "✕", self._close,    "#C0392B")
        mk_btn(tb, "—", self.root.iconify, "#333333")

        # Arrastre de ventana
        for w in (tb, self.lbl_title):
            w.bind("<ButtonPress-1>",   self._drag_start)
            w.bind("<B1-Motion>",       self._drag_move)

        # ── Header operación ───────────────────────────────────────────────
        hdr=tk.Frame(self.root,bg=self.BG2,height=32); hdr.pack(fill="x"); hdr.pack_propagate(False)
        self.lbl_op=tk.Label(hdr,text=self.op,bg=self.BG2,fg=self.FG,font=self.FB,anchor="w")
        self.lbl_op.pack(side="left",padx=12,pady=5)
        self.lbl_ht=tk.Label(hdr,text="0:00:00",bg=self.BG2,fg=self.DIM,font=self.FS,anchor="e")
        self.lbl_ht.pack(side="right",padx=12,pady=5)

        # Separador
        tk.Frame(self.root,bg=self.BG3,height=1).pack(fill="x")

        # Métricas
        g=tk.Frame(self.root,bg=self.BG); g.pack(fill="x",padx=14,pady=(10,6))
        def lbl(p,r,c,t,v,fg=None):
            tk.Label(p,text=t,bg=self.BG,fg=self.DIM,font=self.FS,anchor="w",width=13).grid(row=r,column=c*2,sticky="w",pady=2)
            tk.Label(p,textvariable=v,bg=self.BG,fg=fg or self.FG,font=self.F,anchor="w",width=15).grid(row=r,column=c*2+1,sticky="w",padx=(2,18),pady=2)

        self.vp=tk.StringVar(value="—"); self.vc=tk.StringVar(value="—")
        self.vb=tk.StringVar(value="—"); self.vt=tk.StringVar(value="—")
        self.vr=tk.StringVar(value="—"); self.vs=tk.StringVar(value="—")

        lbl(g,0,0,_lang.t("metrics.processed"),self.vp); lbl(g,0,1,_lang.t("metrics.compressed"),self.vc)
        lbl(g,1,0,_lang.t("metrics.bytes"),self.vb);     lbl(g,1,1,_lang.t("metrics.elapsed"),self.vt)
        lbl(g,2,0,_lang.t("metrics.ratio"),self.vr,fg=self.GREEN); lbl(g,2,1,_lang.t("metrics.speed"),self.vs,fg=self.BLUE)

        # Paso actual
        sf=tk.Frame(self.root,bg=self.BG); sf.pack(fill="x",padx=14,pady=(0,4))
        self.vstep=tk.StringVar(value="")
        tk.Label(sf,textvariable=self.vstep,bg=self.BG,fg=self.DIM,font=self.FS,anchor="w").pack(fill="x")

        # Barra
        pf=tk.Frame(self.root,bg=self.BG); pf.pack(fill="x",padx=14)
        style=ttk.Style(); style.theme_use("default")
        style.configure("S.Horizontal.TProgressbar",
            troughcolor=self.BG3,background=self.GREEN,
            bordercolor=self.BG2,lightcolor=self.GREEN,darkcolor=self.GREEN,thickness=12)
        self.bar=ttk.Progressbar(pf,style="S.Horizontal.TProgressbar",
            orient="horizontal",mode="determinate",maximum=100)
        self.bar.pack(fill="x")

        pr=tk.Frame(self.root,bg=self.BG); pr.pack(fill="x",padx=14)
        self.vpct=tk.StringVar(value="0%")
        tk.Label(pr,textvariable=self.vpct,bg=self.BG,fg=self.DIM,font=self.FS,anchor="w").pack(side="left")

        # Panel completado (oculto)
        self.done_f=tk.Frame(self.root,bg=self.BG2)
        self.vdone=tk.StringVar(value="")
        self.lbl_done=tk.Label(self.done_f,textvariable=self.vdone,
            bg=self.BG2,fg=self.GREEN,font=self.FB,anchor="w",padx=14,pady=6)
        self.lbl_done.pack(fill="x")

        # Botones
        bf=tk.Frame(self.root,bg=self.BG); bf.pack(fill="x",side="bottom",padx=14,pady=8)
        bs=dict(bg=self.BG3,fg=self.FG,font=self.FS,relief="flat",bd=0,
                padx=14,pady=5,cursor="hand2",activebackground="#3A3A3A",activeforeground=self.FG)
        self.btn_bg=tk.Button(bf,text=_lang.t("buttons.background"),command=self._bg,**bs)
        self.btn_bg.pack(side="left")
        if self.no_background:
            self.btn_bg.config(state="disabled",cursor="arrow",fg=self.DIM)
        self.btn_p=tk.Button(bf,text=_lang.t("buttons.pause"),command=self._pause,**bs)
        self.btn_p.pack(side="left",padx=(6,0))
        if self.no_pause:
            self.btn_p.config(state="disabled",cursor="arrow",fg=self.DIM)
        self.btn_c=tk.Button(bf,text=_lang.t("buttons.cancel"),command=self._cancel,
            bg=self.BG3,fg=self.RED,font=self.FS,relief="flat",bd=0,padx=14,pady=5,
            cursor="hand2",activebackground="#3A3A3A",activeforeground=self.RED)
        self.btn_c.pack(side="right")
        if self.no_cancel:
            self.btn_c.config(state="disabled",cursor="arrow",fg=self.DIM)
            self.root.protocol("WM_DELETE_WINDOW", lambda: None)

    def _launch(self):
        # Agregar -v automaticamente para que SYC reporte archivos y progreso
        args = list(self.args)
        if "-v" not in args and "-vv" not in args:
            args.append("-v")
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"]       = "1"
        # CREATE_NO_WINDOW evita que syc.exe abra una consola visible en Windows
        _flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        self.proc=subprocess.Popen(SYC_CMD+args,
            stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
            text=True,encoding="utf-8",errors="replace",bufsize=1,
            env=env, creationflags=_flags)
        threading.Thread(target=self._read,daemon=True).start()

    def _read(self):
        for line in self.proc.stdout: self.p.feed(line)
        self.proc.wait()
        if not self.cancelled: self.p.done=True; self.p.pct=100.0

    def _tick(self):
        p=self.p; el=time.time()-self.t0
        self.lbl_ht.config(text=fmt_time(el))
        self.lbl_op.config(text=f"{self.op}  —  {p.pct:.0f}%")
        self.vt.set(fmt_time(el))
        if p.written>0: self.vp.set(fmt_size(p.written*1048576))
        if p.total>0:   self.vb.set(fmt_size(p.total*1048576))
        if p.comp>0:    self.vc.set(fmt_size(p.comp*1048576))
        if p.ratio>0:   self.vr.set(f"{p.ratio:.2f}%")
        if p.speed>0:   self.vs.set(f"{p.speed:.2f} MB/s")
        st=p.step or p.status
        if st and len(st)>68: st="…"+st[-67:]
        self.vstep.set(st)
        self.bar["value"]=p.pct
        self.vpct.set(f"{p.pct:.0f}%")

        if p.error and not self.cancelled:
            self.btn_p.config(state="disabled"); self.btn_c.config(state="disabled")
            self.vdone.set(_lang.t("status.error",msg=p.error))
            self.lbl_done.config(fg=self.RED)
            self.done_f.pack(fill="x",pady=(4,0)); return

        if p.done and not self.cancelled and not self._shown:
            self._shown=True
            self.bar["value"]=100; self.vpct.set("100%")
            t=fmt_size(p.total*1048576) if p.total>0 else "—"
            c=fmt_size(p.comp*1048576)  if p.comp>0  else "—"
            r=f"  ({p.ratio:.1f}%)" if p.ratio>0 else ""
            arrow=" → " if p.comp>0 else ""
            self.vdone.set(_lang.t("status.done",time=fmt_time(el)) + (f"   {t}{arrow}{c}{r}" if p.total>0 else ""))
            self.lbl_op.config(text=f'{_lang.t("window.completed")}  —  {fmt_time(el)}',fg=self.GREEN)
            self.btn_p.config(state="disabled")
            self.btn_c.config(state="disabled")
            # Cerrar siempre disponible al terminar
            self.btn_bg.config(text=_lang.t("buttons.close"), command=self.root.destroy,
                               state="normal", cursor="hand2", fg=self.FG)
            self.done_f.pack(fill="x",pady=(4,0))
            if self.auto_close:
                self._countdown(3)
            return

        self.root.after(150,self._tick)

    def _drag_start(self,e):
        self._drag_x=e.x_root-self.root.winfo_x()
        self._drag_y=e.y_root-self.root.winfo_y()
    def _drag_move(self,e):
        self.root.geometry(f"+{e.x_root-self._drag_x}+{e.y_root-self._drag_y}")
    def _countdown(self, n):
        if n <= 0:
            self.root.destroy()
            return
        self.btn_bg.config(text=_lang.t("buttons.close_in",n=n))
        self.root.after(1000, lambda: self._countdown(n-1))
    def _bg(self): self.root.iconify()
    def _pause(self):
        if not self.proc: return
        try:
            import signal
            sig=signal.SIGSTOP if hasattr(signal,"SIGSTOP") else 0
            rsig=signal.SIGCONT if hasattr(signal,"SIGCONT") else 0
            if not self.paused: os.kill(self.proc.pid,sig); self.paused=True; self.btn_p.config(text=_lang.t("buttons.resume"),fg=self.YELLOW); self.lbl_op.config(fg=self.YELLOW)
            else: os.kill(self.proc.pid,rsig); self.paused=False; self.btn_p.config(text=_lang.t("buttons.pause"),fg=self.FG); self.lbl_op.config(fg=self.FG)
        except Exception: pass
    def _cancel(self):
        if messagebox.askyesno(_lang.t("confirm.cancel_title"),_lang.t("confirm.cancel_msg"),parent=self.root):
            self.cancelled=True
            if self.proc:
                try: self.proc.terminate()
                except: pass
            self.root.destroy()
    def _close(self):
        if self.p.done: self.root.destroy()
        else: self._cancel()

def main():
    if len(sys.argv)<2:
        import struct
        try:
            import psutil
            cores   = psutil.cpu_count(logical=False) or 1
            threads = psutil.cpu_count(logical=True)  or 1
            ram_gb  = psutil.virtual_memory().total / (1024**3)
            cpu_str = f"CPU: {cores}C/{threads}T"
            ram_str = f"RAM: {ram_gb:.1f} GB"
        except Exception:
            import os as _os; threads = _os.cpu_count() or 1
            cpu_str = f"CPU: {threads}T"; ram_str = ""
        arch = "x64" if struct.calcsize("P")*8 == 64 else "x86"
        hdr = f"SYC v0.2.1 {arch} | by Yade Bravo (YadeWira) | {cpu_str}"
        if ram_str: hdr += f" | {ram_str}"
        print(hdr)
        print("""SYCG - GUI wrapper for SYC
Usage: sycg <command> archive [syc options] [sycg options]

Commands:
  a   Compress    b   Extract    l   List    t   Verify

SYC options (passed through):
  -m METHOD  -tar  -chunk SIZE  -key PASS  -v  -vv  --log  etc.

SYCG exclusive options:
  --title "Text"       Custom window title
  --icon  file.ico     Custom icon for title bar (.ico requires Pillow, .png native)
  --theme dark|white|auto   UI theme (auto detects Windows dark/light mode)
  --lang  file.syl     Language file (default: English built-in)
  --close              Auto-close window 3s after completion
  --nocancel           Disable Cancel button
  --nopause            Disable Pause button
  --nobackground       Disable Background button

Examples:
  sycg a backup.syc folder -m xpszx -tar
  sycg x backup.syc -o dest --lang ES.syl --theme white
  sycg x data.syc -o dest --nocancel --nopause --nobackground --close
  sycg a out.syc folder -m xpszx --icon icon.ico --title "My App Installer" """)
        sys.exit(1)
    argv=sys.argv[1:]
    global _lang
    # Flags exclusivos de sycg (no se pasan a SYC)
    _sycg_flags = {"--close","--nocancel","--nopause","--nobackground"}

    # --icon path
    icon_path = None
    if "--icon" in argv:
        idx = argv.index("--icon")
        if idx + 1 < len(argv):
            icon_path = argv[idx + 1]
            if not os.path.isabs(icon_path):
                icon_path = os.path.join(_HERE, icon_path)
            _sycg_flags = _sycg_flags | {"--icon", argv[idx + 1]}

    # --theme dark/white/auto
    theme = "auto"
    if "--theme" in argv:
        idx = argv.index("--theme")
        if idx + 1 < len(argv):
            theme = argv[idx + 1].lower()
            _sycg_flags = _sycg_flags | {"--theme", argv[idx + 1]}

    # --lang ES.syl / EN.syl
    if "--lang" in argv:
        idx = argv.index("--lang")
        if idx + 1 < len(argv):
            lang_file = argv[idx + 1]
            # Buscar junto al ejecutable si no es ruta absoluta
            if not os.path.isabs(lang_file):
                lang_file = os.path.join(_HERE, lang_file)
            _lang = Lang(lang_file)
            _sycg_flags = _sycg_flags | {"--lang", argv[idx + 1]}
    auto_close    = "--close"        in argv
    no_cancel     = "--nocancel"     in argv
    no_pause      = "--nopause"      in argv
    no_background = "--nobackground" in argv

    # --title "Mi titulo personalizado"
    custom_title = None
    if "--title" in argv:
        idx = argv.index("--title")
        if idx + 1 < len(argv):
            custom_title = argv[idx + 1]
            _sycg_flags = _sycg_flags | {"--title", custom_title}

    args=[a for a in argv if a not in _sycg_flags]
    cmd=args[0] if args else "?"; arc=args[1] if len(args)>1 else "archivo"
    ops={"a":_lang.t("window.compressing"),"x":_lang.t("window.extracting"),"l":_lang.t("window.listing"),"t":_lang.t("window.verifying")}
    title = custom_title if custom_title else f"SYC — {ops.get(cmd,cmd)} {os.path.basename(arc)}"
    SycWindow(title, ops.get(cmd,cmd), args,
              auto_close=auto_close, no_cancel=no_cancel,
              no_pause=no_pause, no_background=no_background,
              icon=icon_path, theme=theme)

if __name__=="__main__": main()