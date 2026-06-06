@echo off
echo =========================================
echo Building Smart Image Compressor Pro
echo =========================================
echo.

echo [1/3] Cleaning old builds...
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul
del /q /f *.spec 2>nul

echo.
echo [2/3] Running PyInstaller...
:: Build standalone exe without console window
pyinstaller --noconsole --onefile --windowed --version-file="version.txt" --icon="assets\icon.ico" --name="SmartImageCompressorPro" --collect-all="customtkinter" --collect-all="tkinterdnd2" main.py

if not exist dist\SmartImageCompressorPro.exe (
    echo.
    echo ERROR: PyInstaller failed to generate the executable.
    pause
    exit /b 1
)

echo.
echo [3/3] Creating Installer...
set ISCC="C:\Users\koush\AppData\Local\Programs\Inno Setup 6\iscc.exe"
if exist %ISCC% (
    %ISCC% "installer\setup.iss"
    echo.
    echo SUCCESS: Installer generated at SmartImageCompressorPro_Setup.exe
) else (
    echo.
    echo Inno Setup Compiler (iscc.exe) not found at expected location.
    echo Please compile "installer\setup.iss" manually to generate the setup file.
)

echo.
pause
