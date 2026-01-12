"""
Build script to create standalone EXE for Video Downloader Tool
Run: python build_exe.py
     python build_exe.py --installer  (to also create Inno Setup installer)
"""

import subprocess
import sys
import os
import shutil
from pathlib import Path

def install_pyinstaller():
    """Install PyInstaller if not present"""
    try:
        import PyInstaller
        print("✓ PyInstaller already installed")
    except ImportError:
        print("Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("✓ PyInstaller installed")

def find_inno_setup():
    """Find Inno Setup compiler"""
    possible_paths = [
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
        r"C:\Program Files (x86)\Inno Setup 5\ISCC.exe",
        r"C:\Program Files\Inno Setup 5\ISCC.exe",
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    return None

def build_installer():
    """Build installer using Inno Setup"""
    print("\n" + "="*50)
    print("Building Installer with Inno Setup")
    print("="*50 + "\n")
    
    iscc_path = find_inno_setup()
    
    if not iscc_path:
        print("❌ Inno Setup not found!")
        print("\nTo create an installer, please install Inno Setup:")
        print("   Download from: https://jrsoftware.org/isdl.php")
        print("\nAlternatively, you can:")
        print("   1. Open setup.iss in Inno Setup")
        print("   2. Click Build > Compile")
        return False
    
    print(f"✓ Found Inno Setup: {iscc_path}")
    
    # Check if EXE exists
    if not os.path.exists("dist/VIDT.exe"):
        print("❌ dist/VIDT.exe not found! Run build_exe.py first.")
        return False
    
    # Create installer output directory
    os.makedirs("installer", exist_ok=True)
    
    # Run Inno Setup compiler
    print("\nCompiling installer...")
    result = subprocess.run([iscc_path, "setup.iss"], capture_output=True, text=True)
    
    if result.returncode == 0:
        print("\n" + "="*50)
        print("✅ INSTALLER CREATED SUCCESSFULLY!")
        print("="*50)
        print(f"\nInstaller ready at: installer/VIDT_Setup_1.0.0.exe")
        return True
    else:
        print("\n❌ Installer build failed!")
        print(result.stderr)
        return False

def build_exe():
    """Build the EXE file"""
    print("\n" + "="*50)
    print("Building VIDT EXE")
    print("="*50 + "\n")
    
    # Clean previous builds
    for folder in ['build', 'dist']:
        if os.path.exists(folder):
            print(f"Cleaning {folder}/...")
            shutil.rmtree(folder)
    
    # Determine icon path
    icon_path = None
    if os.path.exists("logo.ico"):
        icon_path = "logo.ico"
    elif os.path.exists("logo/logo.ico"):
        icon_path = "logo/logo.ico"
    elif os.path.exists("logo.png"):
        icon_path = "logo.png"
    elif os.path.exists("logo/logo.png"):
        icon_path = "logo/logo.png"
    
    # Build PyInstaller command
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",                    # Single EXE file
        "--windowed",                   # No console window
        "--name", "VIDT",               # EXE name
        "--clean",                      # Clean cache
        "--noconfirm",                  # Don't ask for confirmation
    ]
    
    # Add icon if available
    if icon_path:
        cmd.extend(["--icon", icon_path])
        print(f"✓ Using icon: {icon_path}")
    
    # Add logo as data file
    if os.path.exists("logo/logo.png"):
        cmd.extend(["--add-data", "logo/logo.png;logo"])
        print("✓ Including logo/logo.png")
    elif os.path.exists("logo.png"):
        cmd.extend(["--add-data", "logo.png;."])
        print("✓ Including logo.png")
    
    # Hidden imports for PyQt6 and yt-dlp
    hidden_imports = [
        "PyQt6.QtCore",
        "PyQt6.QtGui", 
        "PyQt6.QtWidgets",
        "yt_dlp",
        "requests",
        "certifi",
    ]
    
    for imp in hidden_imports:
        cmd.extend(["--hidden-import", imp])
    
    # Main script
    cmd.append("main.py")
    
    print("\nRunning PyInstaller...")
    print(f"Command: {' '.join(cmd)}\n")
    
    # Run PyInstaller
    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        print("\n" + "="*50)
        print("✅ BUILD SUCCESSFUL!")
        print("="*50)
        print(f"\nYour EXE is ready at: dist/VIDT.exe")
        print("\nTo distribute to users, just send them:")
        print("  • VIDT.exe (single file, ~50-80MB)")
        print("\nNote: Users need ffmpeg for some features.")
        print("They can download it from: https://ffmpeg.org/download.html")
    else:
        print("\n❌ Build failed! Check errors above.")
        return False
    
    return True

def create_distribution_folder():
    """Create a clean distribution folder"""
    dist_folder = Path("release")
    dist_folder.mkdir(exist_ok=True)
    
    exe_path = Path("dist/VIDT.exe")
    if exe_path.exists():
        shutil.copy(exe_path, dist_folder / "VIDT.exe")
        print(f"\n✓ Copied EXE to: release/VIDT.exe")
    
    # Copy installer if exists
    installer_path = Path("installer/VIDT_Setup_1.0.0.exe")
    if installer_path.exists():
        shutil.copy(installer_path, dist_folder / "VIDT_Setup_1.0.0.exe")
        print(f"✓ Copied installer to: release/VIDT_Setup_1.0.0.exe")
    
    # Create README for users
    readme_content = """# VIDT - Video Downloader Tool

## Installation Options

### Option 1: Installer (Recommended)
Run VIDT_Setup_1.0.0.exe for a full installation with:
- Start Menu shortcut
- Desktop shortcut (optional)
- Proper uninstaller

### Option 2: Portable
Just run VIDT.exe directly - no installation needed!

## How to Use
1. Run VIDT
2. Paste a video URL and click Download
3. Videos are saved to the 'downloads' folder

## Supported Platforms
- YouTube
- TikTok  
- Instagram
- Facebook
- Twitter/X
- And many more!

## Features
- Single video download
- Multiple video download
- Profile/Channel video download
- Quality selection
- Audio only mode
- Mute video option
- Subtitle download

## Optional: Install FFmpeg (for best quality)
Some features require FFmpeg. Download from:
https://ffmpeg.org/download.html

## Troubleshooting
- If downloads fail, try updating the app
- Make sure you have internet connection
- Some videos may be private or region-locked
"""
    
    with open(dist_folder / "README.txt", "w") as f:
        f.write(readme_content)
    print("✓ Created README.txt")
    
    print(f"\n📦 Distribution folder ready: release/")
    print("   Contents:")
    for f in dist_folder.iterdir():
        size = f.stat().st_size / (1024*1024)
        print(f"   • {f.name} ({size:.1f} MB)")

def print_usage():
    print("""
VIDT Build Script
=================

Usage:
  python build_exe.py              Build EXE only
  python build_exe.py --installer  Build EXE + Installer
  python build_exe.py --help       Show this help

Requirements:
  - PyInstaller (auto-installed)
  - Inno Setup 6 (for installer, download from https://jrsoftware.org/isdl.php)
""")

if __name__ == "__main__":
    if "--help" in sys.argv or "-h" in sys.argv:
        print_usage()
        sys.exit(0)
    
    install_pyinstaller()
    
    if build_exe():
        create_distribution_folder()
        
        if "--installer" in sys.argv:
            build_installer()
            # Update distribution folder with installer
            create_distribution_folder()
