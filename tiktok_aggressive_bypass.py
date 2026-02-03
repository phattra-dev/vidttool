#!/usr/bin/env python3
"""
Aggressive TikTok Bypass - Try Multiple Approaches
"""

import subprocess
import requests
import json
import re
from pathlib import Path

def try_gallery_dl(url):
    """Try gallery-dl as alternative"""
    try:
        print("[1/4] Trying gallery-dl...")
        result = subprocess.run([
            'gallery-dl', 
            '--dest', 'downloads',
            url
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("[OK] gallery-dl succeeded!")
            return True
        else:
            print(f"[X] gallery-dl failed: {result.stderr[:100]}")
    except Exception as e:
        print(f"[X] gallery-dl error: {e}")
    return False

def try_yt_dlp_latest(url):
    """Try with latest yt-dlp and aggressive options"""
    try:
        print("[2/4] Trying yt-dlp with aggressive options...")
        result = subprocess.run([
            'yt-dlp',
            '--user-agent', 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15',
            '--referer', 'https://www.tiktok.com/',
            '--add-header', 'Accept:text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            '--add-header', 'Accept-Language:en-US,en;q=0.9',
            '--extractor-retries', '5',
            '--fragment-retries', '10',
            '--retry-sleep', '2',
            '-o', 'downloads/%(title)s.%(ext)s',
            url
        ], capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            print("[OK] yt-dlp with aggressive options succeeded!")
            return True
        else:
            print(f"[X] yt-dlp aggressive failed: {result.stderr[:100]}")
    except Exception as e:
        print(f"[X] yt-dlp aggressive error: {e}")
    return False

def try_api_extraction(url):
    """Try to extract using TikTok API endpoints"""
    try:
        print("[3/4] Trying API extraction...")
        
        # Extract video ID
        video_id_match = re.search(r'/video/(\d+)', url)
        if not video_id_match:
            print("[X] Could not extract video ID")
            return False
        
        video_id = video_id_match.group(1)
        print(f"Video ID: {video_id}")
        
        # Try different API endpoints
        api_urls = [
            f"https://api.tiktokv.com/aweme/v1/feed/?aweme_id={video_id}",
            f"https://m.tiktok.com/api/item/detail/?itemId={video_id}",
            f"https://www.tiktok.com/api/item/detail/?itemId={video_id}",
        ]
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15',
            'Accept': 'application/json',
            'Referer': 'https://www.tiktok.com/',
        }
        
        for api_url in api_urls:
            try:
                response = requests.get(api_url, headers=headers, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    print(f"[OK] API response received from {api_url}")
                    # You would need to parse the JSON to extract video URL
                    # This is complex and changes frequently
                    return False  # For now, just report success in getting data
            except Exception as e:
                print(f"[X] API {api_url} failed: {e}")
        
        print("[X] All API endpoints failed")
        return False
        
    except Exception as e:
        print(f"[X] API extraction error: {e}")
    return False

def try_browser_simulation(url):
    """Try browser simulation with selenium"""
    try:
        print("[4/4] Trying browser simulation...")
        
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
        except ImportError:
            print("[X] Selenium not installed")
            return False
        
        # Setup headless Chrome
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15')
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(url)
        
        # Wait for video element
        wait = WebDriverWait(driver, 10)
        video_element = wait.until(EC.presence_of_element_located((By.TAG_NAME, "video")))
        
        video_src = video_element.get_attribute('src')
        if video_src:
            print(f"[OK] Found video source: {video_src[:50]}...")
            
            # Try to download the video
            response = requests.get(video_src, stream=True)
            if response.status_code == 200:
                filename = Path("downloads") / f"tiktok_video.mp4"
                filename.parent.mkdir(exist_ok=True)
                
                with open(filename, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                driver.quit()
                print(f"[OK] Browser simulation succeeded! File: {filename}")
                return True
        
        driver.quit()
        print("[X] Browser simulation failed - no video source found")
        return False
        
    except Exception as e:
        print(f"[X] Browser simulation error: {e}")
        try:
            driver.quit()
        except:
            pass
    return False

def aggressive_tiktok_download(url):
    """Try all aggressive methods"""
    print(f"[!] Aggressive TikTok Download: {url}")
    print("=" * 60)
    
    methods = [
        try_gallery_dl,
        try_yt_dlp_latest, 
        try_api_extraction,
        try_browser_simulation,
    ]
    
    for method in methods:
        if method(url):
            print(f"\n[SUCCESS] Video downloaded successfully!")
            return True
        print()
    
    print("[X] All aggressive methods failed")
    print("\n[!] Alternative options:")
    print("1. Use ssstik.io - paste URL and download")
    print("2. Use snaptik.app - reliable online service") 
    print("3. Use VPN to change location")
    print("4. Wait for yt-dlp update")
    return False

if __name__ == "__main__":
    # Test with the URL you're having trouble with
    test_url = "https://www.tiktok.com/@khaby.lame/video/7137423965982174469"
    aggressive_tiktok_download(test_url)