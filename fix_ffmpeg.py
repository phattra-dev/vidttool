#!/usr/bin/env python3
"""
Script to fix the FFmpeg check function to prevent hanging
"""

import re

def fix_ffmpeg_check():
    # Read the main.py file
    with open(r"c:\Users\KLS COMPUTER\Desktop\downloader tool\main.py", "r", encoding='utf-8') as f:
        content = f.read()
    
    # Define the pattern to find the problematic subprocess.run call
    # Look for the specific check_ffmpeg function
    pattern = r'(\s+try:\n\s+# Try to run ffmpeg to check if it\'s available\n\s+)subprocess\.run\(\[\'ffmpeg\', \'-version\'\], capture_output=True, check=True\)(\n\s+self\.log\("[^"]*FFmpeg is available[^"]*"\)\n\s+except \(subprocess\.CalledProcessError, FileNotFoundError\):)'
    
    # Replacement with timeout and proper error handling
    replacement = r'\1result = subprocess.run([\'ffmpeg\', \'-version\'], capture_output=True, timeout=10)\n\1if result.returncode == 0:\n\1    self.log("[OK] FFmpeg is available - full format conversion supported")\n\1else:\n\1    self.log("[!] FFmpeg not found - some format conversions may not work")\n\1    self.log("[*] To install FFmpeg:")\n\1    self.log("   1. Download from: https://ffmpeg.org/download.html")\n\1    self.log("   2. Or use: winget install ffmpeg (Windows)")\n\1    self.log("   3. Add to PATH environment variable")\n\1except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):'
    
    # Perform the substitution
    updated_content = re.sub(pattern, replacement, content)
    
    # Also fix the other instances in the file
    # Pattern for other ffmpeg checks
    other_pattern = r'(\s+)subprocess\.run\(\[\'ffmpeg\', \'-version\'\], capture_output=True, check=True\)'
    other_replacement = r'\1result = subprocess.run([\'ffmpeg\', \'-version\'], capture_output=True, timeout=10)\n\1if result.returncode != 0:'
    
    updated_content = re.sub(other_pattern, other_replacement, updated_content)
    
    # Write the updated content back to the file
    with open(r"c:\Users\KLS COMPUTER\Desktop\downloader tool\main.py", "w", encoding='utf-8') as f:
        f.write(updated_content)
    
    print("FFmpeg check function updated successfully!")

if __name__ == "__main__":
    fix_ffmpeg_check()