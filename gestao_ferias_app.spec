# -*- mode: python ; coding: utf-8 -*-

import os
from pathlib import Path

block_cipher = None

# Definir ROOT_DIR e STATIC_ROOT
ROOT_DIR = Path(os.getcwd())
STATIC_ROOT = os.path.join(ROOT_DIR, 'staticfiles')

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        (os.path.join('gestao_colaboradores', 'templates', 'gestao_colaboradores'), 'gestao_colaboradores/templates/gestao_colaboradores'),
        (os.path.join('gestao_colaboradores', 'static'), 'gestao_colaboradores/static'),
        (STATIC_ROOT, 'staticfiles'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='gestao_ferias_app',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None  # Se você tiver um ícone, especifique aqui
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='gestao_ferias_app',
)
