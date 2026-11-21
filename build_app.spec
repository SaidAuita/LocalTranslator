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
    'transformers.models.nllb.tokenization_nllb',
    'transformers.models.auto',
    'transformers.models.auto.tokenization_auto',
    'sentencepiece',
    'tokenizers',
    'app.languages_data',
    'app.i18n',
    'app.ui_snippet',
    'app.ui_tray',
    'app.ui_popup',
    'app.hotkey_service',
    'app.local_models',
    'app.layout_converter',
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

# Filter out heavy unneeded libraries (torch, etc.) from binaries and datas
filtered_binaries = []
for b in a.binaries:
    b_dest = b[0].lower()
    b_src = b[1].lower() if len(b) > 1 and b[1] else ""
    # Never filter ctranslate2 binaries (e.g. ctranslate2.dll, cudnn64_9.dll, libiomp5md.dll)
    if "ctranslate2" in b_dest or "ctranslate2" in b_src:
        filtered_binaries.append(b)
        continue
    # Filter out heavy torch CUDA runtime libraries (~3 GB)
    if any(k in b_dest or k in b_src for k in ['torch', 'c10', 'cublas', 'nvrtc', 'torchaudio', 'torchvision']) or ('cudnn' in b_dest or 'cudnn' in b_src):
        continue
    filtered_binaries.append(b)
a.binaries = filtered_binaries

filtered_datas = []
for d in a.datas:
    d_dest = d[0].lower()
    d_src = d[1].lower() if len(d) > 1 and d[1] else ""
    if any(k in d_dest or k in d_src for k in ['torch', 'torchaudio', 'torchvision']):
        continue
    filtered_datas.append(d)
a.datas = filtered_datas

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
    icon=os.path.join(SPECPATH, 'images', 'icon.ico'),
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
