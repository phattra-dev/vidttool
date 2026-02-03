# -*- mode: python ; coding: utf-8 -*-

# Comprehensive excludes to prevent import issues during build
excludes = [
    'rembg', 'onnxruntime', 'onnx', 'torch', 'torchvision', 'torchaudio', 'torchtext',
    'tensorflow', 'tf', 'cv2', 'opencv', 'sklearn', 'scipy', 'numpy.f2py',
    'backgroundremover', 'mediapipe', 'insightface', 'transformers', 'diffusers',
    'accelerate', 'bitsandbytes', 'xformers', 'triton', 'cupy', 'numba', 'jax', 'flax',
    'tensorrt', 'onnxsim', 'onnxoptimizer', 'onnx_tf', 'tf2onnx',
    'matplotlib.tests', 'numpy.tests', 'PIL.tests', 'setuptools', 'distutils',
    'test', 'tests', 'testing'
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('logo/logo.png', 'logo')],
    hiddenimports=[
        'PyQt6.QtCore', 'PyQt6.QtGui', 'PyQt6.QtWidgets', 
        'yt_dlp', 'requests', 'certifi', 'urllib3',
        'PIL', 'PIL.Image', 'PIL.ImageTk', 'PIL.ImageFilter',
        'json', 'base64', 'hashlib', 'hmac'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    [],
    exclude_binaries=True,
    name='VIDT',
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
    icon=['logo.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='VIDT',
)
