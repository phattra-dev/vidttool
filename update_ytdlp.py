#!/usr/bin/env python3
"""
Script to update yt-dlp and check for TikTok support
"""

import subprocess
import sys
import importlib.util
from colorama import init, Fore, Style

init(autoreset=True)

def run_command(command):
    """Run a command and return the result"""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def check_yt_dlp_version():
    """Check current yt-dlp version"""
    try:
        import yt_dlp
        print(f"{Fore.CYAN}Current yt-dlp version: {yt_dlp.version.__version__}")
        return True
    except ImportError:
        print(f"{Fore.RED}yt-dlp is not installed")
        return False

def update_yt_dlp():
    """Update yt-dlp to the latest version"""
    print(f"{Fore.YELLOW}Updating yt-dlp...")
    
    success, stdout, stderr = run_command("pip install --upgrade yt-dlp")
    
    if success:
        print(f"{Fore.GREEN}✓ yt-dlp updated successfully")
        print(stdout)
    else:
        print(f"{Fore.RED}✗ Failed to update yt-dlp")
        print(stderr)
    
    return success

def test_tiktok_extraction():
    """Test TikTok extraction with a sample URL"""
    print(f"{Fore.YELLOW}Testing TikTok extraction...")
    
    # Use a known working TikTok URL for testing
    test_url = "https://www.tiktok.com/@tiktok/video/7016451725845757189"  # Official TikTok account
    
    try:
        import yt_dlp
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,  # Just test extraction, don't download
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(test_url, download=False)
            
        if info:
            print(f"{Fore.GREEN}✓ TikTok extraction test successful")
            print(f"  Title: {info.get('title', 'Unknown')[:50]}...")
            return True
        else:
            print(f"{Fore.RED}✗ TikTok extraction test failed - no info returned")
            return False
            
    except Exception as e:
        print(f"{Fore.RED}✗ TikTok extraction test failed: {str(e)}")
        return False

def check_dependencies():
    """Check if all required dependencies are installed"""
    dependencies = ['yt_dlp', 'requests', 'colorama', 'tqdm']
    missing = []
    
    for dep in dependencies:
        spec = importlib.util.find_spec(dep)
        if spec is None:
            missing.append(dep)
    
    if missing:
        print(f"{Fore.RED}Missing dependencies: {', '.join(missing)}")
        print(f"{Fore.YELLOW}Install with: pip install {' '.join(missing)}")
        return False
    else:
        print(f"{Fore.GREEN}✓ All dependencies are installed")
        return True

def main():
    print(f"{Fore.CYAN}Video Downloader - yt-dlp Update & Test Tool")
    print("=" * 50)
    
    # Check current version
    has_ytdlp = check_yt_dlp_version()
    
    # Check dependencies
    deps_ok = check_dependencies()
    
    if not deps_ok:
        print(f"\n{Fore.YELLOW}Installing missing dependencies...")
        success, _, _ = run_command("pip install -r requirements.txt")
        if not success:
            print(f"{Fore.RED}Failed to install dependencies")
            return
    
    # Update yt-dlp
    if has_ytdlp:
        update_choice = input(f"\n{Fore.YELLOW}Update yt-dlp to latest version? (y/n): ").lower()
        if update_choice == 'y':
            update_yt_dlp()
            # Check version again
            check_yt_dlp_version()
    else:
        print(f"{Fore.YELLOW}Installing yt-dlp...")
        run_command("pip install yt-dlp")
        check_yt_dlp_version()
    
    # Test TikTok extraction
    print(f"\n{Fore.CYAN}Testing TikTok support...")
    tiktok_works = test_tiktok_extraction()
    
    # Summary
    print(f"\n{Fore.CYAN}Summary:")
    print(f"{'✓' if deps_ok else '✗'} Dependencies: {'OK' if deps_ok else 'Missing'}")
    print(f"{'✓' if has_ytdlp else '✗'} yt-dlp: {'Installed' if has_ytdlp else 'Not installed'}")
    print(f"{'✓' if tiktok_works else '✗'} TikTok support: {'Working' if tiktok_works else 'Issues detected'}")
    
    if not tiktok_works:
        print(f"\n{Fore.YELLOW}TikTok Troubleshooting Tips:")
        print("1. TikTok frequently changes their API - this is normal")
        print("2. Try using a VPN to change your location")
        print("3. Some videos may be region-locked or private")
        print("4. Consider using alternative TikTok downloaders")
        print("5. Check yt-dlp GitHub issues for latest TikTok status")

if __name__ == "__main__":
    main()