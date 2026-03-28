# Building from Source

[← Back to README](../README.md)

---

## Requirements

- Python **3.8** x64 (primary — ensures Win7 compatibility)
- Python **3.8** x86 — optional, for 32-bit build
- Internet connection (first run only, to download pip packages)

> **Win7 compatibility note:** Python 3.9+ dropped Windows 7 support. Use Python 3.8.x for all builds if you need Win7 compatibility.

---

## Running from Source

No build required:

```powershell
python syc.py a backup.syc myfolder -m xpszx
python sycg.py a backup.syc myfolder -m xpszx
python psycg.py
```

---

## Automated Build — build.bat

`build.bat` handles everything automatically:

1. Searches for Python 3.8 first (Win7 compatible), then newer versions
2. Installs required pip packages
3. Compiles `syc.exe`, `sycg.exe`, and `psycg.exe` for each architecture
4. Outputs all `.exe` files to `build\`

```powershell
.\build.bat
```

### Expected output

```
 SYC Builder - Yade Bravo (YadeWira)
 =====================================

 Detecting Python installations...
   [OK] Python x64 : C:\...\Python38\python.exe (3.8.20)
   [OK] Python x86 : C:\...\Python38-32\python.exe (3.8.20)

 Building x64...
 -------------------------------------
   Building syc_x64.exe ...     [OK] 8 MB
   Building sycg_x64.exe ...    [OK] 12 MB
   Building psycg_x64.exe ...   [OK] 14 MB

 Building x86...
 -------------------------------------
   Building syc_x86.exe ...     [OK] 7 MB
   Building sycg_x86.exe ...    [OK] 10 MB
   Building psycg_x86.exe ...   [OK] 12 MB

 Done! Output in: D:\...\build
```

---

## Python x86 Installation

Download the **32-bit installer** from [python.org](https://python.org/downloads):

- Select **Windows installer (32-bit)** for Python 3.8.x
- Install to a path like `C:\Users\<user>\AppData\Local\Programs\Python\Python38-32\`

`build.bat` searches these locations automatically:

```
%USERPROFILE%\AppData\Local\Programs\Python\Python38-32\
%USERPROFILE%\AppData\Local\Programs\Python\Python38\
C:\Python38-32\
C:\Python38\
C:\Program Files (x86)\Python38\
```

---

## psutil on x86

`psutil` for x86 requires Microsoft C++ Build Tools to compile from source. `build.bat` tries `--only-binary :all:` first (prebuilt wheel). If no wheel is available, it continues without psutil — CPU/RAM display in the help will be limited but everything else works normally.

---

## Manual Build

```powershell
# x64
pip install pyinstaller psutil pillow cryptography
pyinstaller --onefile --name syc_x64   --icon NONE syc.py
pyinstaller --onefile --name sycg_x64  --icon NONE sycg.py
pyinstaller --onefile --name psycg_x64 --icon NONE psycg.py

# x86 (from Python x86 environment)
C:\...\Python38-32\python.exe -m pip install pyinstaller psutil pillow cryptography
C:\...\Python38-32\python.exe -m PyInstaller --onefile --name syc_x86   --icon NONE syc.py
C:\...\Python38-32\python.exe -m PyInstaller --onefile --name sycg_x86  --icon NONE sycg.py
C:\...\Python38-32\python.exe -m PyInstaller --onefile --name psycg_x86 --icon NONE psycg.py
```

---

## Output Structure

```
release\
  syc.exe          ← rename syc_x64.exe or syc_x86.exe
  sycg.exe
  psycg.exe
  syc.ini
  psycg.cfg        ← auto-created on first run
  lang\
    EN.syl
    ES.syl
    FR.syl
    PT.syl
    RU.syl
  compressors\
    zstd.exe
    srep.exe
    zpaqfranz.exe
    lz4.exe
    ...
  xtool\
    xtool.exe
    *.dll
```

---

## See Also

- [Getting Started](getting-started.md)
- [Examples & Recipes](examples.md)
