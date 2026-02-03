#!/usr/bin/env python3
"""
Precise script to fix the FFmpeg check function to prevent hanging
"""

def fix_ffmpeg_check():
    # Read the main.py file
    with open(r"c:\Users\KLS COMPUTER\Desktop\downloader tool\main.py", "r", encoding='utf-8') as f:
        content = f.read()
    
    # Define the exact original code block to replace
    original_block = '''    def check_ffmpeg(self):
        """Check if FFmpeg is available and provide guidance"""
        import subprocess
        try:
            # Try to run ffmpeg to check if it's available
            subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
            self.log("[OK] FFmpeg is available - full format conversion supported")
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.log("[!] FFmpeg not found - some format conversions may not work")
            self.log("[*] To install FFmpeg:")
            self.log("   1. Download from: https://ffmpeg.org/download.html")
            self.log("   2. Or use: winget install ffmpeg (Windows)")
            self.log("   3. Add to PATH environment variable")'''
    
    # Define the replacement code block
    new_block = '''    def check_ffmpeg(self):
        """Check if FFmpeg is available and provide guidance"""
        import subprocess
        try:
            # Try to run ffmpeg to check if it's available with timeout to prevent hanging
            result = subprocess.run(['ffmpeg', '-version'], capture_output=True, timeout=10)
            if result.returncode == 0:
                self.log("[OK] FFmpeg is available - full format conversion supported")
            else:
                self.log("[!] FFmpeg not found - some format conversions may not work")
                self.log("[*] To install FFmpeg:")
                self.log("   1. Download from: https://ffmpeg.org/download.html")
                self.log("   2. Or use: winget install ffmpeg (Windows)")
                self.log("   3. Add to PATH environment variable")
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            self.log("[!] FFmpeg not found - some format conversions may not work")
            self.log("[*] To install FFmpeg:")
            self.log("   1. Download from: https://ffmpeg.org/download.html")
            self.log("   2. Or use: winget install ffmpeg (Windows)")
            self.log("   3. Add to PATH environment variable")'''
    
    # Replace the block
    updated_content = content.replace(original_block, new_block)
    
    # Also fix other occurrences in the file
    # Replace subprocess.run with check=True to use timeout instead
    updated_content = updated_content.replace(
        "subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)",
        "result = subprocess.run(['ffmpeg', '-version'], capture_output=True, timeout=10)\n            if result.returncode != 0:"
    )
    
    # Write the updated content back to the file
    with open(r"c:\Users\KLS COMPUTER\Desktop\downloader tool\main.py", "w", encoding='utf-8') as f:
        f.write(updated_content)
    
    print("FFmpeg check function updated successfully!")

if __name__ == "__main__":
    fix_ffmpeg_check()