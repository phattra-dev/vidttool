#!/usr/bin/env python3
"""
TikTok Download Fix - Multiple Methods and Workarounds
"""

import subprocess
import sys
import os
import time
import requests
import json
import re
from pathlib import Path
from colorama import init, Fore, Style

init(autoreset=True)

class TikTokDownloadFix:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0',
        })
    
    def method_1_update_ytdlp(self):
        """Method 1: Force update yt-dlp to latest development version"""
        print(f"{Fore.YELLOW}Method 1: Updating yt-dlp to latest development version...")
        
        try:
            # Try installing from GitHub (development version)
            cmd = "pip install --upgrade --force-reinstall git+https://github.com/yt-dlp/yt-dlp.git"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"{Fore.GREEN}✓ Development version installed successfully")
                return True
            else:
                print(f"{Fore.RED}✗ Failed to install development version")
                print(result.stderr)
                return False
                
        except Exception as e:
            print(f"{Fore.RED}✗ Error: {e}")
            return False
    
    def method_2_alternative_extractors(self):
        """Method 2: Try alternative yt-dlp extractors"""
        print(f"{Fore.YELLOW}Method 2: Testing alternative extractors...")
        
        extractors = [
            "TikTok",
            "TikTokUser", 
            "TikTokSound",
            "TikTokEffect",
            "TikTokTag",
            "TikTokLive"
        ]
        
        for extractor in extractors:
            try:
                cmd = f'yt-dlp --list-extractors | findstr /i "{extractor}"'
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                if result.returncode == 0 and result.stdout.strip():
                    print(f"{Fore.GREEN}✓ {extractor} extractor available")
                else:
                    print(f"{Fore.RED}✗ {extractor} extractor not found")
            except:
                pass
        
        return True
    
    def method_3_cookies_setup(self):
        """Method 3: Set up cookies for TikTok access"""
        print(f"{Fore.YELLOW}Method 3: Setting up cookies for TikTok access...")
        
        cookies_dir = Path("cookies")
        cookies_dir.mkdir(exist_ok=True)
        
        cookies_file = cookies_dir / "tiktok_cookies.txt"
        
        if not cookies_file.exists():
            print(f"{Fore.CYAN}Creating cookies template...")
            
            cookie_template = """# Netscape HTTP Cookie File
# This is a generated file! Do not edit.

# To use cookies:
# 1. Install a browser extension like "Get cookies.txt LOCALLY"
# 2. Visit TikTok.com and log in
# 3. Export cookies and save as tiktok_cookies.txt
# 4. Use with: yt-dlp --cookies cookies/tiktok_cookies.txt [URL]

# Example cookie format:
# .tiktok.com	TRUE	/	FALSE	1234567890	sessionid	your_session_id_here
"""
            
            cookies_file.write_text(cookie_template)
            print(f"{Fore.GREEN}✓ Cookie template created at: {cookies_file}")
            print(f"{Fore.CYAN}Instructions:")
            print("1. Install browser extension: 'Get cookies.txt LOCALLY'")
            print("2. Visit tiktok.com and log in")
            print("3. Export cookies and replace the template file")
            print("4. Use cookies with downloads")
        else:
            print(f"{Fore.GREEN}✓ Cookies file already exists: {cookies_file}")
        
        return True
    
    def method_4_proxy_setup(self):
        """Method 4: Set up proxy/VPN recommendations"""
        print(f"{Fore.YELLOW}Method 4: Proxy/VPN setup recommendations...")
        
        proxy_info = """
TikTok Proxy/VPN Setup:

1. Free VPN Options:
   - ProtonVPN (free tier)
   - Windscribe (free tier)
   - TunnelBear (free tier)

2. Proxy Settings for yt-dlp:
   --proxy http://proxy-server:port
   --proxy socks5://proxy-server:port

3. Recommended Locations:
   - United States
   - United Kingdom
   - Canada
   - Germany

4. Usage Example:
   yt-dlp --proxy http://your-proxy:8080 [TikTok URL]
"""
        
        print(f"{Fore.CYAN}{proxy_info}")
        return True
    
    def method_5_alternative_tools(self):
        """Method 5: Alternative TikTok download tools"""
        print(f"{Fore.YELLOW}Method 5: Alternative TikTok download tools...")
        
        alternatives = """
Alternative TikTok Download Tools:

1. Browser Extensions:
   - TikTok Video Downloader (Chrome/Firefox)
   - SaveTik (Browser extension)
   - TikMate (Browser extension)

2. Online Services:
   - ssstik.io
   - tikmate.online
   - tiktokdownload.online
   - snaptik.app

3. Desktop Applications:
   - 4K Video Downloader
   - JDownloader2
   - Internet Download Manager (IDM)

4. Mobile Apps:
   - TikTok Downloader (Android)
   - Documents by Readdle (iOS)

5. Python Libraries:
   - TikTokApi (pip install TikTokApi)
   - tiktok-scraper (npm package)
"""
        
        print(f"{Fore.CYAN}{alternatives}")
        return True
    
    def method_6_ytdlp_config(self):
        """Method 6: Create optimized yt-dlp config"""
        print(f"{Fore.YELLOW}Method 6: Creating optimized yt-dlp configuration...")
        
        config_dir = Path.home() / "AppData" / "Roaming" / "yt-dlp"
        config_dir.mkdir(parents=True, exist_ok=True)
        
        config_file = config_dir / "config"
        
        config_content = """# yt-dlp configuration for TikTok
# Place this file in: %APPDATA%/yt-dlp/config

# Output format
-o "downloads/%(uploader)s - %(title)s.%(ext)s"

# Quality preferences
-f "best[height<=1080]/best"

# User agent rotation
--user-agent "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# Retry settings
--retries 5
--fragment-retries 5

# Rate limiting (be nice to servers)
--limit-rate 1M

# Ignore errors and continue
--ignore-errors

# Extract metadata
--write-info-json
--write-thumbnail

# TikTok specific options
--extractor-args "tiktok:webpage_download_timeout=30"

# Cookies (uncomment if you have cookies file)
# --cookies "cookies/tiktok_cookies.txt"

# Proxy (uncomment if using proxy)
# --proxy "http://your-proxy:8080"
"""
        
        config_file.write_text(config_content)
        print(f"{Fore.GREEN}✓ Configuration created at: {config_file}")
        return True
    
    def test_download(self, url):
        """Test download with various methods"""
        print(f"{Fore.YELLOW}Testing download with URL: {url}")
        
        methods = [
            ("Standard yt-dlp", f'yt-dlp "{url}"'),
            ("With cookies", f'yt-dlp --cookies cookies/tiktok_cookies.txt "{url}"'),
            ("Simulate only", f'yt-dlp --simulate "{url}"'),
            ("Extract info", f'yt-dlp --dump-json "{url}"'),
            ("Force extractor", f'yt-dlp --force-generic-extractor "{url}"'),
        ]
        
        for method_name, command in methods:
            print(f"\n{Fore.CYAN}Trying: {method_name}")
            try:
                result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    print(f"{Fore.GREEN}✓ {method_name} - SUCCESS")
                    return True
                else:
                    print(f"{Fore.RED}✗ {method_name} - FAILED")
                    if result.stderr:
                        print(f"Error: {result.stderr[:200]}...")
            except subprocess.TimeoutExpired:
                print(f"{Fore.YELLOW}⏱ {method_name} - TIMEOUT")
            except Exception as e:
                print(f"{Fore.RED}✗ {method_name} - ERROR: {e}")
        
        return False
    
    def run_all_fixes(self):
        """Run all fix methods"""
        print(f"{Fore.CYAN}TikTok Download Fix - Running All Methods")
        print("=" * 60)
        
        methods = [
            ("Update yt-dlp", self.method_1_update_ytdlp),
            ("Check extractors", self.method_2_alternative_extractors),
            ("Setup cookies", self.method_3_cookies_setup),
            ("Proxy info", self.method_4_proxy_setup),
            ("Alternative tools", self.method_5_alternative_tools),
            ("Create config", self.method_6_ytdlp_config),
        ]
        
        results = {}
        
        for method_name, method_func in methods:
            print(f"\n{Fore.CYAN}Running: {method_name}")
            print("-" * 40)
            try:
                results[method_name] = method_func()
            except Exception as e:
                print(f"{Fore.RED}Error in {method_name}: {e}")
                results[method_name] = False
        
        # Summary
        print(f"\n{Fore.CYAN}SUMMARY")
        print("=" * 30)
        for method, success in results.items():
            status = "✓" if success else "✗"
            color = Fore.GREEN if success else Fore.RED
            print(f"{color}{status} {method}")
        
        print(f"\n{Fore.YELLOW}Next Steps:")
        print("1. Try downloading with cookies if you have a TikTok account")
        print("2. Use a VPN to change your location")
        print("3. Try alternative download tools listed above")
        print("4. Wait for yt-dlp updates (TikTok issues are usually fixed quickly)")
        print("5. Check yt-dlp GitHub issues for latest status")

def main():
    fixer = TikTokDownloadFix()
    
    if len(sys.argv) > 1:
        # Test with provided URL
        test_url = sys.argv[1]
        fixer.test_download(test_url)
    else:
        # Run all fixes
        fixer.run_all_fixes()

if __name__ == "__main__":
    main()