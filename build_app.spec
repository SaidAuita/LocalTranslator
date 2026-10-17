# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from PyInstaller.utils.hooks import collect_all, collect_data_files

block_cipher = None

datas = []
binaries = []
hiddenimports = [
    'pynput.keyboard._win32',
    'pynput.mouse._win32',
    'win32clipboard',
    'win32con',
    'requests',
    'urllib3',
    'certifi',
    'transformers',
    'transformers.models.nllb',
    'transformers.models.auto',
    'sentencepiece',
    'tokenizers',
    'app.languages_data',
    'app.i18n',
    'app.ui_snippet',
    'app.ui_tray',
    'app.ui_popup',
    'app.hotkey_service',
]

# Collect ctranslate2 package and DLLs
try:
    c2_datas, c2_binaries, c2_hidden = collect_all('ctranslate2')
    datas += c2_datas
    binaries += c2_binaries
    hiddenimports += c2_hidden
except Exception as e:
    print(f"Warning collecting ctranslate2: {e}")

# Collect tokenizers data
try:
    datas += collect_data_files('tokenizers')
except Exception:
    pass

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'torch', 'tensorflow', 'tensorboard', 'keras',
        'scipy', 'sklearn', 'cv2', 'PIL', 'matplotlib',
        'IPython', 'notebook', 'tkinter', 'pytest'
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='LocalTranslator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='LocalTranslator',
)
