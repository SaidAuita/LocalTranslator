@echo off
chcp 65001 >nul
title NLLB 1.3B Model Downloader
cd /d "%~dp0"

echo [Model Downloader] Checking and downloading Meta NLLB-200 1.3B INT8...
python download_1.3b_model.py
echo.
pause
