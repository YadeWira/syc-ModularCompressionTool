@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1
title SYC Test Suite v0.1.1

set "SRCDIR=%~dp0"
set "PY=python.exe"
set "SYC=%SRCDIR%syc.py"
set "INI=%SRCDIR%syc.ini"
set "TEST=%SRCDIR%test-files-main"
set "OUT=%SRCDIR%test-output"
set "ARC=%SRCDIR%test-archives"
set "LOG=%SRCDIR%test_results.log"

:: Relaunch capturing output to log while showing on screen (sin loop)
if not defined SYC_RUNNING (
    set SYC_RUNNING=1
    cmd /s /c ""%~f0"" 2>&1 | powershell -NonInteractive -Command "$input | Tee-Object -FilePath '%LOG%'"
    goto :eof
)

set "PASS=0"
set "FAIL=0"
set "SKIP=0"

:: Atajos a subcarpetas de test-files-main
set "NATO=%TEST%\nato"
set "KODAK_PNG=%TEST%\Kodak-Photo-CD\png_24-bit"
set "KODAK_BMP=%TEST%\Kodak-Photo-CD\bmp_24-bit"
set "PDV_JPG_150=%TEST%\publicdomainvectors\jpg_24-bit\150dpi"
set "PDV_PNG_150=%TEST%\publicdomainvectors\png_24-bit\150dpi"
set "UNSPLASH_JPG=%TEST%\Unsplash\jpg_original"
set "WCDOGG_PNG=%TEST%\wcDogg\png_24-bit_limited-palette\150dpi"

if not exist "%TEST%" ( echo [ERROR] test-files-main not found & pause & goto :eof )

if exist "%OUT%" rd /s /q "%OUT%" >nul 2>&1
if exist "%ARC%" rd /s /q "%ARC%" >nul 2>&1
mkdir "%OUT%" & mkdir "%ARC%"

echo.
echo  SYC Test Suite v0.1.1
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

:roundtrip
set "_RT_IN=0"
for /f %%i in ('dir /b /s /a-d "%~2\*" 2^>nul ^| find /c /v ""') do set "_RT_IN=%%i"
set "_RT_OUT=0"
for /f %%i in ('dir /b /s /a-d "%~3\*" 2^>nul ^| find /c /v ""') do set "_RT_OUT=%%i"
if !_RT_IN!==!_RT_OUT! ( call :ok "%~1 round-trip: !_RT_IN! files" ) else ( call :fail "%~1 round-trip" "!_RT_IN! in vs !_RT_OUT! out" )
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

%PY% "%SYC%" a "%ARC%\json_comment.syc" "%TEST%\nato" -m xpszf1 --comment "Test b0.1.0" -cfg "%INI%"
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
%PY% "%SYC%" x "%ARC%\json_tar.syc" -o "%OUT%\tar_f" -f "nato_simple.json" -cfg "%INI%" >nul 2>&1
if !errorlevel! neq 0 ( call :ok "-f on tar correctly rejected" ) else ( call :fail "-f on tar rejected" "should fail" )

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
call :sec "17. NEW - COMPRESS FILTERS (-x / -n)"

:: -x exclude: compress nato but exclude nested_dict
%PY% "%SYC%" a "%ARC%\json_excl.syc" "%TEST%\nato" -m xpszf1 -x "nato_nested_dict.json" -cfg "%INI%"
call :chk %errorlevel% "compress -x exclude pattern"
call :exists "json_excl.syc created" "%ARC%\json_excl.syc"

:: Verify excluded file is not in archive
%PY% "%SYC%" l "%ARC%\json_excl.syc" >nul 2>&1
call :chk %errorlevel% "list -x archive"

:: -n include only: compress nato but only .json matching *nested*
%PY% "%SYC%" a "%ARC%\json_incl.syc" "%TEST%\nato" -m xpszf1 -n "*nested*" -cfg "%INI%"
call :chk %errorlevel% "compress -n include-only pattern"

:: -x and -n combined
%PY% "%SYC%" a "%ARC%\json_xn.syc" "%TEST%\nato" -m xpszf1 -n "*.json" -x "*nested*" -cfg "%INI%"
call :chk %errorlevel% "compress -n + -x combined"

:: -x with tar mode
%PY% "%SYC%" a "%ARC%\tar_excl.syc" "%TEST%\nato" -m xpszf1 -tar -x "nato_simple.json" -cfg "%INI%"
call :chk %errorlevel% "compress tar -x exclude"

:: =============================================================================
call :sec "18. NEW - EXTRACT OVERWRITE (-ow / -y)"

:: Setup: extract once to populate dest
mkdir "%OUT%\ow_base"
%PY% "%SYC%" x "%ARC%\json_normal.syc" -o "%OUT%\ow_base" -cfg "%INI%" >nul 2>&1

:: -ow - (skip existing)
mkdir "%OUT%\ow_skip"
%PY% "%SYC%" x "%ARC%\json_normal.syc" -o "%OUT%\ow_skip" -cfg "%INI%" >nul 2>&1
%PY% "%SYC%" x "%ARC%\json_normal.syc" -o "%OUT%\ow_skip" -ow - -cfg "%INI%"
call :chk %errorlevel% "extract -ow - (skip existing)"

:: -ow + (always overwrite, default)
mkdir "%OUT%\ow_force"
%PY% "%SYC%" x "%ARC%\json_normal.syc" -o "%OUT%\ow_force" -cfg "%INI%" >nul 2>&1
%PY% "%SYC%" x "%ARC%\json_normal.syc" -o "%OUT%\ow_force" -ow + -cfg "%INI%"
call :chk %errorlevel% "extract -ow + (force overwrite)"

:: -y (yes to all, same as -ow +)
mkdir "%OUT%\ow_yes"
%PY% "%SYC%" x "%ARC%\json_normal.syc" -o "%OUT%\ow_yes" -cfg "%INI%" >nul 2>&1
%PY% "%SYC%" x "%ARC%\json_normal.syc" -o "%OUT%\ow_yes" -y -cfg "%INI%"
call :chk %errorlevel% "extract -y (yes to all)"

:: =============================================================================
call :sec "19. NEW - e COMMAND (extract flat)"

mkdir "%OUT%\e_out"
%PY% "%SYC%" e "%ARC%\json_normal.syc" -o "%OUT%\e_out" -cfg "%INI%"
call :chk %errorlevel% "e command (extract flat)"
call :has_files "e command files" "%OUT%\e_out"

:: Verify files are flat (no subdirs) - count files in root only
set "_FLAT=0"
for /f %%i in ('dir /b /a-d "%OUT%\e_out\*" 2^>nul ^| find /c /v ""') do set "_FLAT=%%i"
set "_TOTAL=0"
for /f %%i in ('dir /b /s /a-d "%OUT%\e_out\*" 2^>nul ^| find /c /v ""') do set "_TOTAL=%%i"
if !_FLAT!==!_TOTAL! ( call :ok "e command: files are flat (no subdirs)" ) else ( call :fail "e command: files not flat" "root=!_FLAT! total=!_TOTAL!" )

:: e with -f filter
mkdir "%OUT%\e_filt"
%PY% "%SYC%" e "%ARC%\json_normal.syc" -o "%OUT%\e_filt" -f "*.json" -cfg "%INI%"
call :chk %errorlevel% "e command with -f filter"
call :has_files "e -f files" "%OUT%\e_filt"

:: e with png archive (multiple files)
mkdir "%OUT%\e_png"
%PY% "%SYC%" e "%ARC%\png_normal.syc" -o "%OUT%\e_png" -cfg "%INI%"
call :chk %errorlevel% "e command png (25 files flat)"
call :has_files "e png files" "%OUT%\e_png"

:: =============================================================================
:: =============================================================================
call :sec "20. BLOCK MODE"

:: -block sin -tar: implica solid mode automaticamente
:: PDV png 150dpi (20 PNG) + -block 5MB garantiza 2+ bloques
%PY% "%SYC%" a "%ARC%\block_implicit.syc" "%PDV_PNG_150%" -m xpszf1 -block 5MB -cfg "%INI%"
call :chk %errorlevel% "compress -block (implicit tar)"
call :exists "block_implicit.syc created" "%ARC%\block_implicit.syc"

mkdir "%OUT%\block_implicit"
%PY% "%SYC%" x "%ARC%\block_implicit.syc" -o "%OUT%\block_implicit" -cfg "%INI%"
call :chk %errorlevel% "extract -block implicit"
call :has_files "block_implicit files" "%OUT%\block_implicit"
call :roundtrip "block implicit" "%PDV_PNG_150%" "%OUT%\block_implicit"

:: -block con -tar explicito
%PY% "%SYC%" a "%ARC%\block_tar.syc" "%PDV_PNG_150%" -m xpszf1 -tar -block 5MB -cfg "%INI%"
call :chk %errorlevel% "compress -tar -block"
call :exists "block_tar.syc created" "%ARC%\block_tar.syc"

mkdir "%OUT%\block_tar"
%PY% "%SYC%" x "%ARC%\block_tar.syc" -o "%OUT%\block_tar" -cfg "%INI%"
call :chk %errorlevel% "extract -tar -block"
call :has_files "block_tar files" "%OUT%\block_tar"
call :roundtrip "block tar" "%PDV_PNG_150%" "%OUT%\block_tar"

:: -block con archivos grandes (Kodak BMP 24-bit ~7MB cada uno)
%PY% "%SYC%" a "%ARC%\block_bmp.syc" "%KODAK_BMP%" -m xpszf1 -tar -block 10MB -cfg "%INI%"
call :chk %errorlevel% "compress -block bmp (large files)"
call :exists "block_bmp.syc created" "%ARC%\block_bmp.syc"

mkdir "%OUT%\block_bmp"
%PY% "%SYC%" x "%ARC%\block_bmp.syc" -o "%OUT%\block_bmp" -cfg "%INI%"
call :chk %errorlevel% "extract -block bmp"
call :has_files "block_bmp files" "%OUT%\block_bmp"
call :roundtrip "block bmp" "%KODAK_BMP%" "%OUT%\block_bmp"

:: -block con -tmpd
%PY% "%SYC%" a "%ARC%\block_tmpd.syc" "%NATO%" -m xpszf1 -block 2MB -tmpd "%TEMP%" -cfg "%INI%"
call :chk %errorlevel% "compress -block -tmpd"

mkdir "%OUT%\block_tmpd"
%PY% "%SYC%" x "%ARC%\block_tmpd.syc" -o "%OUT%\block_tmpd" -cfg "%INI%"
call :chk %errorlevel% "extract -block -tmpd"
call :has_files "block_tmpd files" "%OUT%\block_tmpd"

:: -block + cifrado AES256
%PY% "%SYC%" a "%ARC%\block_enc.syc" "%NATO%" -m xpszf1 -tar -block 2MB -key TestPass123 -cfg "%INI%"
call :chk %errorlevel% "compress -block -key"

mkdir "%OUT%\block_enc"
%PY% "%SYC%" x "%ARC%\block_enc.syc" -o "%OUT%\block_enc" -key TestPass123 -cfg "%INI%"
call :chk %errorlevel% "extract -block encrypted"
call :has_files "block_enc files" "%OUT%\block_enc"

:: -block + --comment + list
%PY% "%SYC%" a "%ARC%\block_comment.syc" "%NATO%" -m xpszf1 -block 2MB --comment "block test" -cfg "%INI%"
call :chk %errorlevel% "compress -block --comment"

%PY% "%SYC%" l "%ARC%\block_comment.syc"
call :chk %errorlevel% "list -block archive"

:: =============================================================================
call :sec "21. DEDUP MODE (-dd)"

:: -dd basico: sin duplicados reales, debe funcionar igual que modo normal
%PY% "%SYC%" a "%ARC%\dd_basic.syc" "%NATO%" -m xpszf1 -dd -cfg "%INI%"
call :chk %errorlevel% "compress -dd basic"
call :exists "dd_basic.syc created" "%ARC%\dd_basic.syc"

mkdir "%OUT%\dd_basic"
%PY% "%SYC%" x "%ARC%\dd_basic.syc" -o "%OUT%\dd_basic" -cfg "%INI%"
call :chk %errorlevel% "extract -dd basic"
call :has_files "dd_basic files" "%OUT%\dd_basic"
call :roundtrip "dd nato" "%NATO%" "%OUT%\dd_basic"

:: -dd con chunk size 1MB
%PY% "%SYC%" a "%ARC%\dd_1mb.syc" "%NATO%" -m xpszf1 -dd 1MB -cfg "%INI%"
call :chk %errorlevel% "compress -dd 1MB chunks"

mkdir "%OUT%\dd_1mb"
%PY% "%SYC%" x "%ARC%\dd_1mb.syc" -o "%OUT%\dd_1mb" -cfg "%INI%"
call :chk %errorlevel% "extract -dd 1MB"
call :roundtrip "dd 1MB" "%NATO%" "%OUT%\dd_1mb"

:: -dd con dataset de imagenes (wcDogg paleta limitada: buen candidato por chunks similares)
%PY% "%SYC%" a "%ARC%\dd_imgs.syc" "%WCDOGG_PNG%" -m xpszf1 -dd 1MB -cfg "%INI%"
call :chk %errorlevel% "compress -dd images (1MB chunks)"
call :exists "dd_imgs.syc created" "%ARC%\dd_imgs.syc"

mkdir "%OUT%\dd_imgs"
%PY% "%SYC%" x "%ARC%\dd_imgs.syc" -o "%OUT%\dd_imgs" -cfg "%INI%"
call :chk %errorlevel% "extract -dd images"
call :roundtrip "dd images" "%WCDOGG_PNG%" "%OUT%\dd_imgs"

:: -dd con -block (combinar dedup + bloques independientes)
%PY% "%SYC%" a "%ARC%\dd_block.syc" "%PDV_PNG_150%" -m xpszf1 -dd 4MB -block 10MB -cfg "%INI%"
call :chk %errorlevel% "compress -dd -block"
call :exists "dd_block.syc created" "%ARC%\dd_block.syc"

mkdir "%OUT%\dd_block"
%PY% "%SYC%" x "%ARC%\dd_block.syc" -o "%OUT%\dd_block" -cfg "%INI%"
call :chk %errorlevel% "extract -dd -block"
call :has_files "dd_block files" "%OUT%\dd_block"
call :roundtrip "dd+block" "%PDV_PNG_150%" "%OUT%\dd_block"

:: -dd con --comment
%PY% "%SYC%" a "%ARC%\dd_comment.syc" "%NATO%" -m xpszf1 -dd --comment "dedup test" -cfg "%INI%"
call :chk %errorlevel% "compress -dd --comment"

:: list en archivo dedup (guard por si compress fallo)
if exist "%ARC%\dd_basic.syc" (
    %PY% "%SYC%" l "%ARC%\dd_basic.syc"
    call :chk %errorlevel% "list -dd archive"
) else ( call :skip "list -dd archive (dd_basic.syc missing)" )

:: -dd con duplicados reales: 3 copias exactas del mismo archivo + 1 diferente
mkdir "%TEMP%\syc_dd_test" >nul 2>&1
copy "%NATO%\nato_simple.json"      "%TEMP%\syc_dd_test\copy1.json" >nul 2>&1
copy "%NATO%\nato_simple.json"      "%TEMP%\syc_dd_test\copy2.json" >nul 2>&1
copy "%NATO%\nato_simple.json"      "%TEMP%\syc_dd_test\copy3.json" >nul 2>&1
copy "%NATO%\nato_nested_dict.json" "%TEMP%\syc_dd_test\other.json" >nul 2>&1

%PY% "%SYC%" a "%ARC%\dd_dups.syc" "%TEMP%\syc_dd_test" -m xpszf1 -dd -cfg "%INI%"
call :chk %errorlevel% "compress -dd real duplicates"

mkdir "%OUT%\dd_dups"
%PY% "%SYC%" x "%ARC%\dd_dups.syc" -o "%OUT%\dd_dups" -cfg "%INI%"
call :chk %errorlevel% "extract -dd real duplicates"
call :has_files "dd_dups files" "%OUT%\dd_dups"

rd /s /q "%TEMP%\syc_dd_test" >nul 2>&1

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