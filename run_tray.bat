@echo off
cd /d "%~dp0"
if exist "dist\LocalTranslator\LocalTranslator.exe" (
    start "" "dist\LocalTranslator\LocalTranslator.exe" --minimized
) else (
    start "" pythonw main.py --minimized
)
