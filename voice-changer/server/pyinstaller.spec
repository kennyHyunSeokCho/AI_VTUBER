# -*- mode: python ; coding: utf-8 -*-

# 한국어 주석: MMVCServerSIO.py를 단일 실행 파일로 빌드하는 스펙

import os
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

hiddenimports = []

a = Analysis(
    ['MMVCServerSIO.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        # 프론트엔드 정적 배포물 포함 (없으면 런타임에 상대경로 사용)
        ('../client/demo/dist', 'dist'),
        # 정적 모델 디렉토리 포함 (있을 경우)
        ('model_dir_static', 'model_dir_static'),
        # 사전학습 모델 디렉토리(비어있어도 구조 포함)
        ('pretrain', 'pretrain'),
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='MMVCServerSIO',
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
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='MMVCServerSIO'
)


