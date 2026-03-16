@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1
title SYC Test Suite v0.0.2

set "SRCDIR=%~dp0"
set "PY=python.exe"
set "SYC=%SRCDIR%syc.py"
set "INI=%SRCDIR%syc.ini"
set "TEST=%SRCDIR%test-files-main"
set "OUT=%SRCDIR%test-output"
set "ARC=%SRCDIR%test-archives"
set "LOG=%SRCDIR%test_results.log"

:: Relaunch capturing output to log while showing on screen
if not defined SYC_RUNNING (
    set SYC_RUNNING=1
    powershell -Command "& cmd /c \"\"%~f0\"\" 2>&1 | Tee-Object -FilePath \"%LOG%\""
    goto :eof
)

set "PASS=0"
set "FAIL=0"
set "SKIP=0"

if not exist "%TEST%" ( echo [ERROR] test-files-main not found & pause & goto :eof )

if exist "%OUT%" rd /s /q "%OUT%" >nul 2>&1
if exist "%ARC%" rd /s /q "%ARC%" >nul 2>&1
mkdir "%OUT%" & mkdir "%ARC%"

echo.
echo  SYC Test Suite
echo  ==================================
echo  SYC:  %SYC%
echo  Data: %TEST%

goto :tests

:ok
echo   [PASS] %~1
set /a PASS+=1
goto :eof

:fail
echo   [FAIL] %~1  (%~2)
set /a FAIL+=1
goto :eof

:skip
echo   [SKIP] %~1
set /a SKIP+=1
goto :eof

:sec
echo.
echo  -- %~1
echo  -----------------------------------------------
goto :eof

:chk
if %1==0 ( call :ok "%~2" ) else ( call :fail "%~2" "exit %1" )
goto :eof

:exists
if exist "%~2" ( call :ok "%~1" ) else ( call :fail "%~1" "not found: %~2" )
goto :eof

:has_files
set "_C=0"
for /f %%i in ('dir /b /s /a-d "%~2\*" 2^>nul ^| find /c /v ""') do set "_C=%%i"
if !_C! GTR 0 ( call :ok "%~1 (!_C! files)" ) else ( call :fail "%~1" "empty" )
goto :eof

:tests
:: =============================================================================
call :sec "1. HELP / INFO"

call :skip "help (manual check)"

%PY% "%SYC%" m -cfg "%INI%"
call :chk %errorlevel% "syc m - list methods"

:: =============================================================================
call :sec "2. COMPRESS - NORMAL MODE"

%PY% "%SYC%" a "%ARC%\json_normal.syc" "%TEST%\nato" -m xpszf1 -cfg "%INI%"
call :chk %errorlevel% "compress json normal"
call :exists "json_normal.syc created" "%ARC%\json_normal.syc"

%PY% "%SYC%" a "%ARC%\png_normal.syc" "%TEST%\Kodak-Photo-CD\png_24-bit" -m xpszf1 -cfg "%INI%"
call :chk %errorlevel% "compress png normal"

%PY% "%SYC%" a "%ARC%\json_v.syc" "%TEST%\nato" -m xpszf1 -v -cfg "%INI%"
call :chk %errorlevel% "compress -v verbose"

%PY% "%SYC%" a "%ARC%\json_comment.syc" "%TEST%\nato" -m xpszf1 --comment "Test b0.0.3" -cfg "%INI%"
call :chk %errorlevel% "compress --comment"

%PY% "%SYC%" a "%ARC%\json_hash.syc" "%TEST%\nato" -m xpszf1 --crc32 --md5 -cfg "%INI%"
call :chk %errorlevel% "compress --crc32 --md5"

:: =============================================================================
call :sec "3. COMPRESS - TAR MODE"

%PY% "%SYC%" a "%ARC%\json_tar.syc" "%TEST%\nato" -m xpszf1 -tar -cfg "%INI%"
call :chk %errorlevel% "compress json tar"
call :exists "json_tar.syc created" "%ARC%\json_tar.syc"

%PY% "%SYC%" a "%ARC%\png_tar.syc" "%TEST%\Kodak-Photo-CD\png_24-bit" -m xpszf1 -tar -cfg "%INI%"
call :chk %errorlevel% "compress png tar"

%PY% "%SYC%" a "%ARC%\tar_comment.syc" "%TEST%\nato" -m xpszf1 -tar --comment "TAR test" -cfg "%INI%"
call :chk %errorlevel% "compress tar --comment"

%PY% "%SYC%" a "%ARC%\tar_tmpd.syc" "%TEST%\nato" -m xpszf1 -tar -tmpd "%TEMP%" -cfg "%INI%"
call :chk %errorlevel% "compress tar -tmpd"

%PY% "%SYC%" a "%ARC%\mixed_tar.syc" "%TEST%\Kodak-Photo-CD" -m xpszf1 -tar -cfg "%INI%"
call :chk %errorlevel% "compress mixed tar"

:: =============================================================================
call :sec "4. COMPRESS - ENCRYPTION"

%PY% "%SYC%" a "%ARC%\enc_aes.syc" "%TEST%\nato" -m xpszf1 -key TestPass123 -cfg "%INI%"
call :chk %errorlevel% "compress AES256"

%PY% "%SYC%" a "%ARC%\enc_cc20.syc" "%TEST%\nato" -m xpszf1 -key TestPass123 -ks CC20 -cfg "%INI%"
call :chk %errorlevel% "compress ChaCha20"

%PY% "%SYC%" a "%ARC%\enc_full.syc" "%TEST%\nato" -m xpszf1 -tar -key TestPass123 --full-encrypted -cfg "%INI%"
call :chk %errorlevel% "compress full-encrypted"

:: =============================================================================
call :sec "5. COMPRESS - MULTI-PART"

%PY% "%SYC%" a "%ARC%\chunk??.syc" "%TEST%\nato" -m xpszf1 -chunk 50KB -cfg "%INI%"
call :chk %errorlevel% "compress multi-part normal"

%PY% "%SYC%" a "%ARC%\tarchunk??.syc" "%TEST%\nato" -m xpszf1 -tar -chunk 50KB -cfg "%INI%"
call :chk %errorlevel% "compress multi-part tar"

:: =============================================================================
call :sec "6. LIST - l command"

%PY% "%SYC%" l "%ARC%\json_normal.syc"
call :chk %errorlevel% "list normal"

%PY% "%SYC%" l "%ARC%\json_tar.syc"
call :chk %errorlevel% "list tar"

%PY% "%SYC%" l "%ARC%\json_comment.syc"
call :chk %errorlevel% "list with comment"

%PY% "%SYC%" l "%ARC%\json_hash.syc"
call :chk %errorlevel% "list with hashes"

%PY% "%SYC%" l "%ARC%\enc_aes.syc" -key TestPass123
call :chk %errorlevel% "list encrypted"

%PY% "%SYC%" l "%ARC%\enc_full.syc" -key TestPass123
call :chk %errorlevel% "list full-encrypted"

:: =============================================================================
call :sec "7. LIST - ls command"

%PY% "%SYC%" ls "%ARC%\png_normal.syc"
call :chk %errorlevel% "ls normal"

%PY% "%SYC%" ls "%ARC%\mixed_tar.syc"
call :chk %errorlevel% "ls tar"

%PY% "%SYC%" ls "%ARC%\tar_comment.syc"
call :chk %errorlevel% "ls with comment"

%PY% "%SYC%" ls "%ARC%\mixed_tar.syc" "png_24-bit\"
call :chk %errorlevel% "ls folder filter"

:: =============================================================================
call :sec "8. EXTRACT - normal mode"

mkdir "%OUT%\json_normal"
%PY% "%SYC%" x "%ARC%\json_normal.syc" -o "%OUT%\json_normal" -cfg "%INI%"
call :chk %errorlevel% "extract json normal"
call :has_files "json normal files" "%OUT%\json_normal"

mkdir "%OUT%\png_normal"
%PY% "%SYC%" x "%ARC%\png_normal.syc" -o "%OUT%\png_normal" -cfg "%INI%"
call :chk %errorlevel% "extract png normal"
call :has_files "png normal files" "%OUT%\png_normal"

:: =============================================================================
call :sec "9. EXTRACT - tar mode"

mkdir "%OUT%\json_tar"
%PY% "%SYC%" x "%ARC%\json_tar.syc" -o "%OUT%\json_tar" -cfg "%INI%"
call :chk %errorlevel% "extract json tar"
call :has_files "json tar files" "%OUT%\json_tar"

mkdir "%OUT%\mixed_tar"
%PY% "%SYC%" x "%ARC%\mixed_tar.syc" -o "%OUT%\mixed_tar" -cfg "%INI%"
call :chk %errorlevel% "extract mixed tar"
call :has_files "mixed tar files" "%OUT%\mixed_tar"

:: =============================================================================
call :sec "10. EXTRACT - encrypted"

mkdir "%OUT%\enc_aes"
%PY% "%SYC%" x "%ARC%\enc_aes.syc" -o "%OUT%\enc_aes" -key TestPass123 -cfg "%INI%"
call :chk %errorlevel% "extract AES256"
call :has_files "aes files" "%OUT%\enc_aes"

mkdir "%OUT%\enc_cc20"
%PY% "%SYC%" x "%ARC%\enc_cc20.syc" -o "%OUT%\enc_cc20" -key TestPass123 -cfg "%INI%"
call :chk %errorlevel% "extract ChaCha20"
call :has_files "cc20 files" "%OUT%\enc_cc20"

mkdir "%OUT%\enc_full"
%PY% "%SYC%" x "%ARC%\enc_full.syc" -o "%OUT%\enc_full" -key TestPass123 -cfg "%INI%"
call :chk %errorlevel% "extract full-encrypted"
call :has_files "full-enc files" "%OUT%\enc_full"

%PY% "%SYC%" x "%ARC%\enc_aes.syc" -o "%OUT%\wrong" -key WrongPass -cfg "%INI%" >nul 2>&1
if !errorlevel! neq 0 ( call :ok "wrong password rejected" ) else ( call :fail "wrong password rejected" "should fail" )

:: =============================================================================
call :sec "11. EXTRACT - partial (-f and -ff)"

mkdir "%OUT%\pf"
%PY% "%SYC%" x "%ARC%\json_normal.syc" -o "%OUT%\pf" -f "nato_simple.json" -cfg "%INI%"
call :chk %errorlevel% "extract -f exact"
call :exists "-f flat file" "%OUT%\pf\nato_simple.json"

mkdir "%OUT%\pff"
%PY% "%SYC%" x "%ARC%\json_normal.syc" -o "%OUT%\pff" -ff "nato_simple.json" -cfg "%INI%"
call :chk %errorlevel% "extract -ff exact"

mkdir "%OUT%\pwild"
%PY% "%SYC%" x "%ARC%\json_normal.syc" -o "%OUT%\pwild" -f "*.json" -cfg "%INI%"
call :chk %errorlevel% "extract -f wildcard"
call :has_files "wildcard files" "%OUT%\pwild"

mkdir "%OUT%\pmulti"
%PY% "%SYC%" x "%ARC%\json_normal.syc" -o "%OUT%\pmulti" -f "nato_simple.json" -f "nato_nested_dict.json" -cfg "%INI%"
call :chk %errorlevel% "extract multiple -f"

mkdir "%OUT%\tar_f"
%PY% "%SYC%" x "%ARC%\json_tar.syc" -o "%OUT%\tar_f" -f "nato_simple.json" -cfg "%INI%"
call :chk %errorlevel% "-f on tar (warns + extracts all)"

:: =============================================================================
call :sec "12. EXTRACT - multi-part"

mkdir "%OUT%\chunk_out"
%PY% "%SYC%" x "%ARC%\chunk??.syc" -o "%OUT%\chunk_out" -cfg "%INI%"
call :chk %errorlevel% "extract multi-part normal"
call :has_files "multipart files" "%OUT%\chunk_out"

mkdir "%OUT%\tarchunk_out"
%PY% "%SYC%" x "%ARC%\tarchunk??.syc" -o "%OUT%\tarchunk_out" -cfg "%INI%"
call :chk %errorlevel% "extract multi-part tar"
call :has_files "tar multipart files" "%OUT%\tarchunk_out"

:: =============================================================================
call :sec "13. VERIFY - t command"

%PY% "%SYC%" t "%ARC%\json_normal.syc"
call :chk %errorlevel% "verify normal"

%PY% "%SYC%" t "%ARC%\json_tar.syc"
call :chk %errorlevel% "verify tar"

%PY% "%SYC%" t "%ARC%\json_hash.syc"
call :chk %errorlevel% "verify hash"

:: =============================================================================
call :sec "14. INNOSETUP MODE"

mkdir "%OUT%\inno"
%PY% "%SYC%" a "%ARC%\inno_test.syc" "%TEST%\nato" -m xpszf1 -tar --innosetup -cfg "%INI%"
call :chk %errorlevel% "--innosetup compress"

%PY% "%SYC%" x "%ARC%\inno_test.syc" -o "%OUT%\inno" --innosetup -cfg "%INI%"
call :chk %errorlevel% "--innosetup extract"

:: =============================================================================
call :sec "15. ROUND-TRIP INTEGRITY"

set "_IN=0"
for /f %%i in ('dir /b /s /a-d "%TEST%\nato\*" 2^>nul ^| find /c /v ""') do set "_IN=%%i"
mkdir "%OUT%\rt"
%PY% "%SYC%" a "%ARC%\rt.syc" "%TEST%\nato" -m xpszf1 -tar --crc32 --md5 -cfg "%INI%"
%PY% "%SYC%" x "%ARC%\rt.syc" -o "%OUT%\rt" -cfg "%INI%"
set "_OUT=0"
for /f %%i in ('dir /b /s /a-d "%OUT%\rt\*" 2^>nul ^| find /c /v ""') do set "_OUT=%%i"
if !_IN!==!_OUT! ( call :ok "round-trip nato: !_IN! files" ) else ( call :fail "round-trip nato" "!_IN! in vs !_OUT! out" )

set "_IN2=0"
for /f %%i in ('dir /b /s /a-d "%TEST%\Kodak-Photo-CD\png_24-bit\*" 2^>nul ^| find /c /v ""') do set "_IN2=%%i"
mkdir "%OUT%\rt_kodak"
%PY% "%SYC%" a "%ARC%\rt_kodak.syc" "%TEST%\Kodak-Photo-CD\png_24-bit" -m xpszf1 -tar -cfg "%INI%"
%PY% "%SYC%" x "%ARC%\rt_kodak.syc" -o "%OUT%\rt_kodak" -cfg "%INI%"
set "_OUT2=0"
for /f %%i in ('dir /b /s /a-d "%OUT%\rt_kodak\*" 2^>nul ^| find /c /v ""') do set "_OUT2=%%i"
if !_IN2!==!_OUT2! ( call :ok "round-trip Kodak: !_IN2! files" ) else ( call :fail "round-trip Kodak" "!_IN2! in vs !_OUT2! out" )

:: =============================================================================
call :sec "16. EDGE CASES"

%PY% "%SYC%" x "%SRCDIR%syc.ini" -o "%OUT%\inv" -cfg "%INI%" >nul 2>&1
if !errorlevel! neq 0 ( call :ok "invalid archive rejected" ) else ( call :fail "invalid archive rejected" "should fail" )

%PY% "%SYC%" x "%ARC%\nope.syc" -o "%OUT%\inv" -cfg "%INI%" >nul 2>&1
if !errorlevel! neq 0 ( call :ok "missing archive rejected" ) else ( call :fail "missing archive rejected" "should fail" )

%PY% "%SYC%" x "%ARC%\json_normal.syc" -o "%OUT%\inv" -f "nope.xyz" -cfg "%INI%" >nul 2>&1
if !errorlevel! neq 0 ( call :ok "-f no match rejected" ) else ( call :fail "-f no match rejected" "should fail" )

%PY% "%SYC%" a "%ARC%\spaces test.syc" "%TEST%\publicdomainvectors\jpg_24-bit\150dpi" -m xpszf1 -tar -cfg "%INI%"
call :chk %errorlevel% "spaces in archive name"

:: =============================================================================
set /a TOTAL=PASS+FAIL+SKIP
echo.
echo  ==================================
echo  Results: %TOTAL% tests
echo  ----------------------------------
echo   PASS: %PASS%
echo   FAIL: %FAIL%
echo   SKIP: %SKIP%
echo  ==================================
if %FAIL% GTR 0 ( echo  [!] Some tests FAILED ) else ( echo  [OK] All tests passed! )
echo.
echo  Log: %LOG%
echo.
pause
endlocal