@echo off
setlocal enabledelayedexpansion
title SYC Builder v0.1.0

echo.
echo  SYC Builder v0.1.0 - Yade Bravo (YadeWira)
echo  =====================================
echo.

set "SRCDIR=%~dp0"
set "OUTDIR=%SRCDIR%build"
if not exist "%OUTDIR%" mkdir "%OUTDIR%"

set "PY64="
set "PY32="

for %%P in (
    "%USERPROFILE%\AppData\Local\Programs\Python\Python38\python.exe"
    "C:\Python38\python.exe"
    "C:\Program Files\Python38\python.exe"
    "%USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe"
    "%USERPROFILE%\AppData\Local\Programs\Python\Python311\python.exe"
    "%USERPROFILE%\AppData\Local\Programs\Python\Python310\python.exe"
    "C:\Python312\python.exe"
    "C:\Python311\python.exe"
    "C:\Program Files\Python312\python.exe"
    "C:\Program Files\Python311\python.exe"
) do (
    if exist %%P (
        if "!PY64!"=="" (
            %%P -c "import struct,sys; sys.exit(0 if struct.calcsize('P')*8==64 else 1)" >nul 2>&1
            if !errorlevel!==0 set "PY64=%%~P"
        )
    )
)

for %%P in (
    "%USERPROFILE%\AppData\Local\Programs\Python\Python312-32\python.exe"
    "%USERPROFILE%\AppData\Local\Programs\Python\Python311-32\python.exe"
    "%USERPROFILE%\AppData\Local\Programs\Python\Python310-32\python.exe"
    "C:\Python312-32\python.exe"
    "C:\Python311-32\python.exe"
    "C:\Program Files (x86)\Python312\python.exe"
    "C:\Program Files (x86)\Python311\python.exe"
    "%USERPROFILE%\AppData\Local\Programs\Python\Python38-32\python.exe"
    "C:\Python38-32\python.exe"
    "C:\Program Files (x86)\Python38\python.exe"
) do (
    if exist %%P (
        if "!PY32!"=="" (
            %%P -c "import struct,sys; sys.exit(0 if struct.calcsize('P')*8==32 else 1)" >nul 2>&1
            if !errorlevel!==0 set "PY32=%%~P"
        )
    )
)

if "!PY64!"=="" (
    python -c "import struct,sys; sys.exit(0 if struct.calcsize('P')*8==64 else 1)" >nul 2>&1
    if !errorlevel!==0 (
        for /f "delims=" %%i in ('where python 2^>nul') do (
            if "!PY64!"=="" set "PY64=%%i"
        )
    )
)

echo  Detecting Python installations...
echo.

if "!PY64!"=="" (
    echo   [--] Python x64 : NOT FOUND
) else (
    for /f "tokens=2 delims= " %%v in ('"!PY64!" --version 2^>^&1') do set "VER64=%%v"
    echo   [OK] Python x64 : !PY64! (!VER64!)
)

if "!PY32!"=="" (
    echo   [--] Python x86 : NOT FOUND
) else (
    for /f "tokens=2 delims= " %%v in ('"!PY32!" --version 2^>^&1') do set "VER32=%%v"
    echo   [OK] Python x86 : !PY32! (!VER32!)
)

echo.

if "!PY64!"=="" if "!PY32!"=="" (
    echo [ERROR] No Python installation found. Aborting.
    goto :end
)

:: Dependencias base (siempre disponibles)
set "DEPS_BASE=pyinstaller pillow cryptography reedsolo"
:: psutil: puede fallar en x86 sin Visual C++ Build Tools
:: Se intenta instalar, si falla se continua sin ella (hay fallback en syc.py)
set "DEPS_OPTIONAL=psutil"

if not "!PY64!"=="" (
    echo  Installing x64 dependencies...
    "!PY64!" -m pip install %DEPS_BASE% %DEPS_OPTIONAL% -q --disable-pip-version-check
    if !errorlevel! neq 0 (
        echo   [WARN] psutil failed, installing without it...
        "!PY64!" -m pip install %DEPS_BASE% -q --disable-pip-version-check
    )
    echo   [OK] x64 ready.
)

if not "!PY32!"=="" (
    echo  Installing x86 dependencies...
    "!PY32!" -m pip install %DEPS_BASE% -q --disable-pip-version-check
    :: psutil x86 requiere Visual C++ Build Tools - intentar solo si ya esta instalado
    "!PY32!" -c "import psutil" >nul 2>&1
    if !errorlevel! neq 0 (
        echo   [INFO] Trying psutil x86 with prebuilt wheel...
        "!PY32!" -m pip install psutil --only-binary :all: -q --disable-pip-version-check >nul 2>&1
        if !errorlevel! neq 0 (
            echo   [INFO] psutil not available for x86 - CPU/RAM info will be limited.
        ) else (
            echo   [OK] psutil x86 installed.
        )
    ) else (
        echo   [OK] psutil x86 already available.
    )
    echo   [OK] x86 ready.
)

echo.

if not "!PY64!"=="" (
    echo  Building x64...
    echo  -------------------------------------
    call :compile "!PY64!" x64 syc       syc.py
    call :compile "!PY64!" x64 sycg      sycg.py
    call :compile "!PY64!" x64 psycg     psycg.py  --noconsole
    echo.
)

if not "!PY32!"=="" (
    echo  Building x86...
    echo  -------------------------------------
    call :compile "!PY32!" x86 syc       syc.py
    call :compile "!PY32!" x86 sycg      sycg.py
    call :compile "!PY32!" x86 psycg     psycg.py  --noconsole
    echo.
)

echo  Done! Output in: %OUTDIR%
echo  -------------------------------------
dir "%OUTDIR%\*.exe" 2>nul | findstr /i ".exe"
echo.

:: ── Copy support files to build\ ─────────────────────────────────────────────
echo  Copying support files...
copy /y "%SRCDIR%syc.ini"  "%OUTDIR%\" >nul 2>&1
copy /y "%SRCDIR%EN.syl"   "%OUTDIR%\" >nul 2>&1
copy /y "%SRCDIR%ES.syl"   "%OUTDIR%\" >nul 2>&1
copy /y "%SRCDIR%FR.syl"   "%OUTDIR%\" >nul 2>&1
copy /y "%SRCDIR%PT.syl"   "%OUTDIR%\" >nul 2>&1
copy /y "%SRCDIR%RU.syl"   "%OUTDIR%\" >nul 2>&1
if exist "%SRCDIR%icon.ico" copy /y "%SRCDIR%icon.ico" "%OUTDIR%\" >nul 2>&1

:: Copy lang\ folder if it exists
if exist "%SRCDIR%lang\" (
    if not exist "%OUTDIR%\lang\" mkdir "%OUTDIR%\lang\"
    xcopy /y /q "%SRCDIR%lang\*.syl" "%OUTDIR%\lang\" >nul 2>&1
    echo   [OK] lang\ folder copied
)

echo   [OK] Support files copied
echo.
goto :end

:compile
set "_PY=%~1"
set "_ARCH=%~2"
set "_NAME=%~3"
set "_SCRIPT=%~4"
set "_EXTRA=%~5"
set "_OUT=%_NAME%_%_ARCH%"
set "_WORK=%OUTDIR%\work_%_ARCH%_%_NAME%"

echo   Building %_OUT%.exe ...

"%_PY%" -m PyInstaller ^
    --onefile ^
    --name "%_OUT%" ^
    --icon NONE ^
    --distpath "%OUTDIR%" ^
    --workpath "%_WORK%" ^
    --specpath "%_WORK%" ^
    --noconfirm ^
    --log-level WARN ^
    %_EXTRA% ^
    "%SRCDIR%%_SCRIPT%" >nul 2>&1

if exist "%OUTDIR%\%_OUT%.exe" (
    for %%S in ("%OUTDIR%\%_OUT%.exe") do set "_SZ=%%~zS"
    set /a "_MB=!_SZ! / 1048576"
    echo   [OK] %_OUT%.exe - !_MB! MB
    if exist "%_WORK%" rd /s /q "%_WORK%" >nul 2>&1
) else (
    echo   [FAIL] %_OUT%.exe - check build log
)
goto :eof

:end
echo.
pause
endlocal