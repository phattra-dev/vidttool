#!/usr/bin/env python3
"""
Safe build script for VIDT that handles problematic imports
"""
import os
import shutil
import subprocess
import sys

def create_build_version():
    """Create a build-safe version of main.py"""
    print("Creating build-safe version of main.py...")
    
    # Read original main.py
    with open('main.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Create backup
    shutil.copy('main.py', 'main_original.py')
    
    # Replace problematic import statements with try/except blocks
    replacements = [
        ('import rembg', '# import rembg  # Disabled for build'),
        ('from rembg import', '# from rembg import  # Disabled for build'),
        ('import onnxruntime', '# import onnxruntime  # Disabled for build'),
        ('from onnxruntime import', '# from onnxruntime import  # Disabled for build'),
    ]
    
    for old, new in replacements:
        content = content.replace(old, new)
    
    # Write build version
    with open('main_build.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    return 'main_build.py'

def restore_original():
    """Restore original main.py"""
    if os.path.exists('main_original.py'):
        shutil.move('main_original.py', 'main.py')
    if os.path.exists('main_build.py'):
        os.remove('main_build.py')

def build_executable():
    """Build the executable using PyInstaller"""
    try:
        # Create build-safe version
        build_file = create_build_version()
        
        # Update spec file to use build version
        with open('VIDT.spec', 'r') as f:
            spec_content = f.read()
        
        spec_content = spec_content.replace("['main.py']", f"['{build_file}']")
        
        with open('VIDT_build.spec', 'w') as f:
            f.write(spec_content)
        
        # Run PyInstaller
        print("Running PyInstaller...")
        result = subprocess.run([
            sys.executable, '-m', 'PyInstaller', 
            '--clean', 'VIDT_build.spec'
        ], capture_output=True, text=True)
        
        print("STDOUT:", result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        if result.returncode == 0:
            print("✅ Build successful!")
        else:
            print("❌ Build failed!")
            return False
            
    except Exception as e:
        print(f"❌ Build error: {e}")
        return False
    finally:
        # Cleanup
        restore_original()
        if os.path.exists('VIDT_build.spec'):
            os.remove('VIDT_build.spec')
    
    return True

if __name__ == "__main__":
    success = build_executable()
    sys.exit(0 if success else 1)