#!/usr/bin/env python3
"""
Advanced TikTok Bypass System
Multiple extraction methods with browser impersonation and proxy support
"""

import yt_dlp
import requests
import json
import re
import time
import random
from pathlib import Path
from urllib.parse import urlparse, parse_qs
import subprocess
import os

class TikTokAdvancedDownloader:
    """Advanced TikTok downloader with multiple bypass methods"""
    
    def __init__(self, output_dir="downloads"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # User agents for different browsers/devices
        self.user_agents = [
            # Mobile browsers (often work better for TikTok)
            'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1',
            'Mozilla/5.0 (Linux; Android 12; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Mobile Safari/537.36',
            'Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Mobile Safari/537.36',
            
            # Desktop browsers
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0',
        ]
    
    def extract_video_id(self, url):
        """Extract TikTok video ID from URL"""
        patterns = [
            r'/video/(\d+)',
            r'v=(\d+)',
            r'/(\d+)/?$',
            r'item_id=(\d+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    def method_1_standard_ytdlp(self, url, callback=None):
        """Method 1: Standard yt-dlp with optimized settings"""
        try:
            if callback:
                callback("[1/7] Trying standard yt-dlp...")
            
            opts = {
                'outtmpl': str(self.output_dir / '%(title)s.%(ext)s'),
                'format': 'best[ext=mp4]/best',
                'retries': 3,
                'fragment_retries': 5,
                'http_headers': {
                    'User-Agent': random.choice(self.user_agents),
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                }
            }
            
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                filename = ydl.prepare_filename(info)
                ydl.download([url])
                
                if Path(filename).exists():
                    return {'success': True, 'file': filename, 'method': 'standard'}
                    
        except Exception as e:
            if callback:
                callback(f"[1/7] Standard method failed: {str(e)[:100]}...")
        
        return {'success': False}
    
    def method_2_cookies(self, url, callback=None):
        """Method 2: Use cookies from browser"""
        try:
            if callback:
                callback("[2/7] Trying with browser cookies...")
            
            cookies_file = Path("cookies/tiktok_cookies.txt")
            if not cookies_file.exists():
                return {'success': False, 'error': 'No cookies file found'}
            
            opts = {
                'outtmpl': str(self.output_dir / '%(title)s.%(ext)s'),
                'format': 'best[ext=mp4]/best',
                'cookiefile': str(cookies_file),
                'retries': 3,
                'http_headers': {
                    'User-Agent': random.choice(self.user_agents),
                    'Referer': 'https://www.tiktok.com/',
                }
            }
            
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                filename = ydl.prepare_filename(info)
                ydl.download([url])
                
                if Path(filename).exists():
                    return {'success': True, 'file': filename, 'method': 'cookies'}
                    
        except Exception as e:
            if callback:
                callback(f"[2/7] Cookie method failed: {str(e)[:100]}...")
        
        return {'success': False}
    
    def method_3_impersonation(self, url, callback=None):
        """Method 3: Browser impersonation with curl-cffi"""
        try:
            if callback:
                callback("[3/7] Trying browser impersonation...")
            
            # Check if curl-cffi is available
            try:
                import curl_cffi
            except ImportError:
                return {'success': False, 'error': 'curl-cffi not installed'}
            
            opts = {
                'outtmpl': str(self.output_dir / '%(title)s.%(ext)s'),
                'format': 'best[ext=mp4]/best',
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36',
                }
            }
            
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                filename = ydl.prepare_filename(info)
                ydl.download([url])
                
                if Path(filename).exists():
                    return {'success': True, 'file': filename, 'method': 'impersonation'}
                    
        except Exception as e:
            if callback:
                callback(f"[3/7] Impersonation failed: {str(e)[:100]}...")
        
        return {'success': False}
    
    def method_4_mobile_app(self, url, callback=None):
        """Method 4: Simulate mobile app requests"""
        try:
            if callback:
                callback("[4/7] Trying mobile app simulation...")
            
            video_id = self.extract_video_id(url)
            if not video_id:
                return {'success': False, 'error': 'Could not extract video ID'}
            
            # Mobile app headers
            headers = {
                'User-Agent': 'com.ss.android.ugc.trill/494+TikTok+29.7.0+29.7.0+494+2023110702+f482441e7+release+Channel(googleplay)+aid(1233)',
                'Accept': 'application/json',
                'X-Requested-With': 'XMLHttpRequest',
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'same-origin',
            }
            
            # Try mobile API endpoint
            api_url = f"https://m.tiktok.com/api/item/detail/?itemId={video_id}"
            
            response = requests.get(api_url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                # Extract video URL from API response
                if 'itemInfo' in data and 'itemStruct' in data['itemInfo']:
                    video_data = data['itemInfo']['itemStruct']
                    if 'video' in video_data and 'downloadAddr' in video_data['video']:
                        download_url = video_data['video']['downloadAddr']
                        
                        # Download the video file
                        video_response = requests.get(download_url, headers=headers, stream=True)
                        if video_response.status_code == 200:
                            filename = self.output_dir / f"tiktok_{video_id}.mp4"
                            
                            with open(filename, 'wb') as f:
                                for chunk in video_response.iter_content(chunk_size=8192):
                                    f.write(chunk)
                            
                            return {'success': True, 'file': str(filename), 'method': 'mobile_api'}
                            
        except Exception as e:
            if callback:
                callback(f"[4/7] Mobile app method failed: {str(e)[:100]}...")
        
        return {'success': False}
    
    def method_5_selenium_browser(self, url, callback=None):
        """Method 5: Use Selenium to get video URL from browser"""
        try:
            if callback:
                callback("[5/7] Trying browser automation...")
            
            try:
                from selenium import webdriver
                from selenium.webdriver.chrome.options import Options
                from selenium.webdriver.common.by import By
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
            except ImportError:
                return {'success': False, 'error': 'Selenium not installed'}
            
            # Setup headless Chrome
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument(f'--user-agent={random.choice(self.user_agents)}')
            
            try:
                driver = webdriver.Chrome(options=chrome_options)
                driver.get(url)
                
                # Wait for video element to load
                wait = WebDriverWait(driver, 10)
                video_element = wait.until(EC.presence_of_element_located((By.TAG_NAME, "video")))
                
                # Get video source URL
                video_src = video_element.get_attribute('src')
                if video_src:
                    # Download the video
                    response = requests.get(video_src, stream=True)
                    if response.status_code == 200:
                        video_id = self.extract_video_id(url) or 'unknown'
                        filename = self.output_dir / f"tiktok_{video_id}.mp4"
                        
                        with open(filename, 'wb') as f:
                            for chunk in response.iter_content(chunk_size=8192):
                                f.write(chunk)
                        
                        driver.quit()
                        return {'success': True, 'file': str(filename), 'method': 'selenium'}
                
                driver.quit()
                
            except Exception as e:
                try:
                    driver.quit()
                except:
                    pass
                raise e
                
        except Exception as e:
            if callback:
                callback(f"[5/7] Browser automation failed: {str(e)[:100]}...")
        
        return {'success': False}
    
    def method_6_alternative_extractors(self, url, callback=None):
        """Method 6: Try alternative extractors/tools"""
        try:
            if callback:
                callback("[6/7] Trying alternative extractors...")
            
            # Try gallery-dl as alternative
            try:
                result = subprocess.run([
                    'gallery-dl', 
                    '--dest', str(self.output_dir),
                    url
                ], capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    # Check if file was downloaded
                    for file in self.output_dir.glob('*'):
                        if file.is_file() and file.stat().st_size > 1000:  # At least 1KB
                            return {'success': True, 'file': str(file), 'method': 'gallery-dl'}
                            
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass
            
        except Exception as e:
            if callback:
                callback(f"[6/7] Alternative extractors failed: {str(e)[:100]}...")
        
        return {'success': False}
    
    def method_7_proxy_rotation(self, url, callback=None):
        """Method 7: Try with different proxy/location"""
        try:
            if callback:
                callback("[7/7] Trying with proxy rotation...")
            
            # List of free proxy services (you might want to use paid ones for reliability)
            proxy_list = [
                # Add proxy servers here if available
                # 'http://proxy1:port',
                # 'http://proxy2:port',
            ]
            
            if not proxy_list:
                return {'success': False, 'error': 'No proxies configured'}
            
            for proxy in proxy_list:
                try:
                    opts = {
                        'outtmpl': str(self.output_dir / '%(title)s.%(ext)s'),
                        'format': 'best[ext=mp4]/best',
                        'proxy': proxy,
                        'http_headers': {
                            'User-Agent': random.choice(self.user_agents),
                        }
                    }
                    
                    with yt_dlp.YoutubeDL(opts) as ydl:
                        info = ydl.extract_info(url, download=False)
                        filename = ydl.prepare_filename(info)
                        ydl.download([url])
                        
                        if Path(filename).exists():
                            return {'success': True, 'file': filename, 'method': f'proxy_{proxy}'}
                            
                except Exception:
                    continue
                    
        except Exception as e:
            if callback:
                callback(f"[7/7] Proxy method failed: {str(e)[:100]}...")
        
        return {'success': False}
    
    def download_with_all_methods(self, url, callback=None):
        """Try all methods in sequence until one succeeds"""
        if callback:
            callback(f"[*] Starting advanced TikTok download: {url}")
        
        methods = [
            self.method_1_standard_ytdlp,
            self.method_2_cookies,
            self.method_3_impersonation,
            self.method_4_mobile_app,
            self.method_5_selenium_browser,
            self.method_6_alternative_extractors,
            self.method_7_proxy_rotation,
        ]
        
        for i, method in enumerate(methods, 1):
            try:
                result = method(url, callback)
                if result['success']:
                    if callback:
                        callback(f"[OK] Success with method {i}: {result['method']}")
                    return result
                    
                # Small delay between methods
                time.sleep(1)
                
            except Exception as e:
                if callback:
                    callback(f"[!] Method {i} crashed: {str(e)[:50]}...")
                continue
        
        # All methods failed
        if callback:
            callback("[X] All 7 methods failed")
            callback("[?] TikTok Advanced Workarounds:")
            callback("    1. Use ssstik.io (paste URL, download)")
            callback("    2. Use snaptik.app (reliable online service)")
            callback("    3. Use tikmate.online (no watermark)")
            callback("    4. Install TikTok Video Downloader browser extension")
            callback("    5. Use VPN to change your location")
            callback("    6. Export fresh cookies from logged-in browser")
            callback("    7. Wait for yt-dlp update (usually 1-3 days)")
        
        return {'success': False, 'error': 'All extraction methods failed'}


def test_advanced_downloader():
    """Test the advanced downloader"""
    downloader = TikTokAdvancedDownloader()
    
    # Test URL - replace with actual TikTok video URL
    test_url = "https://www.tiktok.com/@asmrfood128/video/7598354525556165901"
    
    def progress_callback(msg):
        print(msg)
    
    result = downloader.download_with_all_methods(test_url, progress_callback)
    
    if result['success']:
        print(f"\n✅ Download successful!")
        print(f"File: {result['file']}")
        print(f"Method: {result['method']}")
    else:
        print(f"\n❌ Download failed: {result.get('error', 'Unknown error')}")


if __name__ == "__main__":
    test_advanced_downloader()