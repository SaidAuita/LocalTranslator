@echo off
chcp 65001 >nul
echo Очистка кэша иконок Windows...
taskkill /f /im explorer.exe >nul 2>&1
timeout /t 2 /nobreak >nul
del /f /q "%LOCALAPPDATA%\IconCache.db" 2>nul
del /f /q "%LOCALAPPDATA%\Microsoft\Windows\Explorer\iconcache*" 2>nul
start explorer.exe
echo [OK] Кэш иконок Windows успешно очищен!
pause
