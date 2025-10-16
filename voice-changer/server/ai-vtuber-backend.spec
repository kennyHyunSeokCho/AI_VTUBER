# -*- mode: python ; coding: utf-8 -*-

# 한국어 주석: MMVCServerSIO.py를 'ai-vtuber-backend' 이름의 단일 실행 파일로 빌드

block_cipher = None

a = Analysis(
    ['MMVCServerSIO.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        # 프론트엔드 정적 배포물 포함
        ('../client/demo/dist', 'dist'),
        # 정적 모델 디렉토리 포함
        ('model_dir_static', 'model_dir_static'),
        # 사전학습 모델 디렉토리 포함
        ('pretrain', 'pretrain'),
    ],
    hiddenimports=[],
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
    name='ai-vtuber-backend',
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
    name='ai-vtuber-backend'
)


