# Building from Source

[← Back to README](../README.md)

---

## Requirements

- Python 3.10+ (x64)
- Python 3.10+ (x86) — optional, for 32-bit build
- Internet connection (first run only, to download pip packages)

---

## Running from Source

No build required:

```powershell
python syc.py a backup.syc myfolder -m xpszx
python sycg.py a backup.syc myfolder -m xpszx
```

---

## Automated Build — build.bat

`build.bat` handles everything automatically:

1. Detects Python x64 and x86 installations
2. Installs required pip packages
3. Compiles `syc.exe` and `sycg.exe` for each architecture
4. Outputs all `.exe` files to `build\`

```powershell
.\build.bat
```

### Expected output

```
 SYC Builder - Yade Bravo (YadeWira)
 =====================================

 Detecting Python installations...
   [OK] Python x64 : C:\...\Python312\python.exe (3.12.10)
   [OK] Python x86 : C:\...\Python312-32\python.exe (3.12.10)

 Installing x64 dependencies...
   [OK] x64 ready.
 Installing x86 dependencies...
   [OK] x86 ready.

 Building x64...
 -------------------------------------
   Building syc_x64.exe ...
   [OK] syc_x64.exe - 8 MB
   Building sycg_x64.exe ...
   [OK] sycg_x64.exe - 12 MB

 Building x86...
 -------------------------------------
   Building syc_x86.exe ...
   [OK] syc_x86.exe - 7 MB
   Building sycg_x86.exe ...
   [OK] sycg_x86.exe - 10 MB

 Done! Output in: D:\...\build
```

---

## Python x86 Installation

Download the **32-bit installer** from [python.org](https://python.org/downloads):

- Select **Windows installer (32-bit)**
- Install to a path like `C:\Users\<user>\AppData\Local\Programs\Python\Python312-32\`

`build.bat` searches these locations automatically:

```
%USERPROFILE%\AppData\Local\Programs\Python\Python312-32\
%USERPROFILE%\AppData\Local\Programs\Python\Python311-32\
C:\Python312-32\
C:\Python311-32\
C:\Program Files (x86)\Python312\
```

---

## psutil on x86

`psutil` for x86 requires **Microsoft C++ Build Tools** to compile from source. `build.bat` handles this automatically by trying `--only-binary :all:` (prebuilt wheel). If no prebuilt wheel is available, it continues without psutil — CPU/RAM display in the help will be limited but everything else works normally.

---

## Manual Build

If you prefer to build manually:

```powershell
# x64
pip install pyinstaller psutil pillow cryptography
pyinstaller --onefile --name syc_x64  --icon NONE syc.py
pyinstaller --onefile --name sycg_x64 --icon NONE sycg.py

# x86 (from Python x86 environment)
C:\...\Python312-32\python.exe -m pip install pyinstaller psutil pillow cryptography
C:\...\Python312-32\python.exe -m PyInstaller --onefile --name syc_x86  --icon NONE syc.py
C:\...\Python312-32\python.exe -m PyInstaller --onefile --name sycg_x86 --icon NONE sycg.py
```

---

## Output Structure

After building, copy the required files alongside the executables:

```
release\
  syc.exe          ← rename syc_x64.exe or syc_x86.exe
  sycg.exe         ← rename sycg_x64.exe or sycg_x86.exe
  syc.ini
  EN.syl
  ES.syl
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

## GitHub Actions (Cloud Build)

See [build.yml](../build.yml) for an automated GitHub Actions workflow that builds both architectures on every push.

---

## See Also

- [Getting Started](getting-started.md)
- [Examples & Recipes](examples.md)
