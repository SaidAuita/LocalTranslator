@echo off
chcp 65001 >nul
title Local Translator (NLLB 1.3B + LM Studio)
cd /d "%~dp0"

:: Register CUDA 12 DLLs if available
if exist "%LOCALAPPDATA%\Programs\Ollama\lib\ollama\cuda_v12" (
    set "PATH=%LOCALAPPDATA%\Programs\Ollama\lib\ollama\cuda_v12;%PATH%"
)

:: Check Python
where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found in PATH!
    echo Please install Python 3.10+ and add it to PATH.
    pause
    exit /b 1
)

echo [Local Translator] Starting application...
python main.py

if errorlevel 1 (
    echo.
    echo [ERROR] Application exited with an error.
    pause
)
