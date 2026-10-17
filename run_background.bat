@echo off
chcp 65001 >nul
cd /d "%~dp0"

:: Register CUDA 12 DLLs if available
if exist "%LOCALAPPDATA%\Programs\Ollama\lib\ollama\cuda_v12" (
    set "PATH=%LOCALAPPDATA%\Programs\Ollama\lib\ollama\cuda_v12;%PATH%"
)

:: Run silently into system tray without console window
start "" pythonw main.py --minimized
