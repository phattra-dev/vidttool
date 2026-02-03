#!/usr/bin/env python3
"""
Build script for VIDT v1.2.2
Creates both installer and portable versions
"""

import subprocess
import shutil
import os
from pathlib import Path

def build_release():
    """Build VIDT v1.2.2 release"""
    print("🚀 Building VIDT v1.2.2...")
    
    # Clean previous builds
    if Path("build").exists():
        shutil.rmtree("build")
    if Path("dist").exists():
        shutil.rmtree("dist")
    
    print("📦 Building executable with PyInstaller...")
    
    # Build with PyInstaller (directory-based for stability)
    cmd = [
        "pyinstaller",
        "--name=VIDT",
        "--windowed",
        "--onedir",  # Directory-based (not onefile)
        "--icon=logo.ico",
        "--add-data=logo.png;.",
        "--add-data=cookies;cookies",
        "--add-data=version.json;.",
        "--hidden-import=requests",
        "--hidden-import=yt_dlp",
        "--hidden-import=PyQt6",
        "--hidden-import=PIL",
        "--collect-all=yt_dlp",
        "--collect-all=requests",
        "--noconfirm",
        "main.py"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ Build failed: {result.stderr}")
        return False
    
    print("✅ Executable built successfully!")
    
    # Copy to release directory
    release_dir = Path("release")
    release_dir.mkdir(exist_ok=True)
    
    # Copy executable
    if Path("dist/VIDT").exists():
        print("📁 Copying to release directory...")
        if Path("release/VIDT").exists():
            shutil.rmtree("release/VIDT")
        shutil.copytree("dist/VIDT", "release/VIDT")
        
        # Copy main executable to root of release
        if Path("release/VIDT/VIDT.exe").exists():
            shutil.copy2("release/VIDT/VIDT.exe", "release/VIDT.exe")
    
    print("🎯 Creating installer with Inno Setup...")
    
    # Build installer (requires Inno Setup)
    try:
        inno_cmd = [
            "iscc",
            "setup.iss"
        ]
        
        inno_result = subprocess.run(inno_cmd, capture_output=True, text=True)
        
        if inno_result.returncode == 0:
            print("✅ Installer created successfully!")
            
            # Move installer to release directory
            installer_files = list(Path("installer").glob("VIDT_Setup_1.2.2.exe"))
            if installer_files:
                shutil.copy2(installer_files[0], "release/VIDT_Setup_1.2.2.exe")
                print("📦 Installer copied to release directory")
        else:
            print(f"⚠️ Installer creation failed: {inno_result.stderr}")
            print("💡 Manual installer creation may be needed")
    
    except FileNotFoundError:
        print("⚠️ Inno Setup not found - skipping installer creation")
        print("💡 Install Inno Setup to create installer automatically")
    
    # Create portable ZIP
    print("📦 Creating portable version...")
    
    if Path("release/VIDT").exists():
        # Create portable ZIP
        shutil.make_archive("release/VIDT_v1.2.2_Portable", 'zip', "release", "VIDT")
        print("✅ Portable ZIP created!")
    
    # Create README for release
    readme_content = """# VIDT v1.2.2 Release Files

## Installation Options

### 1. Installer (Recommended)
- **File**: VIDT_Setup_1.2.2.exe
- **Size**: ~58MB
- **Installation**: Run installer, follow prompts
- **Features**: Start menu shortcuts, uninstaller, auto-updates

### 2. Portable Version
- **File**: VIDT_v1.2.2_Portable.zip
- **Size**: ~45MB (compressed)
- **Installation**: Extract anywhere, run VIDT.exe
- **Features**: No installation required, fully portable

### 3. Standalone Executable
- **File**: VIDT.exe
- **Size**: ~2MB (requires VIDT folder)
- **Usage**: Run directly from release folder
- **Note**: Requires all supporting files in same directory

## What's New in v1.2.2

🔥 **MAJOR FIXES**:
- TikTok downloads fully restored
- Fixed empty folder issue
- Fixed HEVC codec prompts
- Facebook downloads working
- Version consistency fixed

See RELEASE_v1.2.2_SUMMARY.md for complete changelog.

## System Requirements

- Windows 10 or later
- ~100MB free disk space
- Internet connection for downloads
- Optional: FFmpeg for format conversion

## Support

For issues or questions, check the documentation or create an issue on GitHub.
"""
    
    with open("release/README.txt", "w", encoding="utf-8") as f:
        f.write(readme_content)
    
    print("\n🎉 VIDT v1.2.2 build complete!")
    print("\n📁 Release files created:")
    
    release_files = list(Path("release").glob("*"))
    for file in sorted(release_files):
        if file.is_file():
            size = file.stat().st_size / (1024*1024)
            print(f"   📄 {file.name} ({size:.1f}MB)")
    
    print(f"\n✅ Ready for release!")
    return True

if __name__ == "__main__":
    build_release()