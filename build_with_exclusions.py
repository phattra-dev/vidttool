#!/usr/bin/env python3
"""
Build script that uses environment variables to exclude problematic packages
"""
import os
import sys
import subprocess

# Set environment variables to prevent PyInstaller from analyzing problematic packages
os.environ['PYINSTALLER_EXCLUDE_REMBG'] = '1'
os.environ['PYINSTALLER_EXCLUDE_ONNX'] = '1'

# Create a minimal spec file that avoids the problematic imports
spec_content = '''# -*- mode: python ; coding: utf-8 -*-

import os

# Block problematic imports at the module level
import sys
class BlockImport:
    def __init__(self, *args):
        self.blocked = set(args)
    
    def find_spec(self, name, path, target=None):
        if any(blocked in name for blocked in self.blocked):
            return None
        return None
    
    def find_module(self, name, path=None):
        if any(blocked in name for blocked in self.blocked):
            return None
        return None

# Install the import blocker
sys.meta_path.insert(0, BlockImport('rembg', 'onnxruntime', 'onnx', 'torch', 'tensorflow'))

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('logo/logo.png', 'logo')],
    hiddenimports=[
        'PyQt6.QtCore', 'PyQt6.QtGui', 'PyQt6.QtWidgets', 
        'yt_dlp', 'requests', 'certifi', 'urllib3',
        'PIL', 'PIL.Image', 'PIL.ImageFilter'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'rembg', 'onnxruntime', 'onnx', 'torch', 'torchvision', 'tensorflow', 
        'cv2', 'backgroundremover', 'mediapipe', 'sklearn', 'scipy',
        'matplotlib.tests', 'numpy.tests', 'test', 'tests'
    ],
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
'''

# Write the spec file
with open('VIDT_safe.spec', 'w') as f:
    f.write(spec_content)

# Run PyInstaller with the safe spec
try:
    print("Building with safe exclusions...")
    result = subprocess.run([
        sys.executable, '-m', 'PyInstaller', 
        '--clean', '--noconfirm', 'VIDT_safe.spec'
    ], capture_output=True, text=True)
    
    print("STDOUT:", result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    
    if result.returncode == 0:
        print("✅ Build successful!")
    else:
        print("❌ Build failed with return code:", result.returncode)
        
except Exception as e:
    print(f"❌ Build error: {e}")