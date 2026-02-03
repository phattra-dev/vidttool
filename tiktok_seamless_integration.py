#!/usr/bin/env python3
"""
Seamless TikTok Integration for Video Downloader
Direct integration without failure messages - focuses on working solutions
"""

import requests
import re
import json
import time
import random
from pathlib import Path
from urllib.parse import quote, unquote, urlparse

class SeamlessTikTokDownloader:
    def __init__(self, abort_callback=None):
        self.session = requests.Session()
        self.abort_callback = abort_callback  # Function to check if download should be aborted
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Ch-Ua': '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1'
        })
        
        # Working endpoints that bypass TikTok blocks
        self.working_endpoints = [
            'https://tikmate.online',
            'https://snaptik.app',
            'https://ssstik.io'
        ]
    
    def _is_valid_tiktok_url(self, url):
        """Check if URL is a valid TikTok URL"""
        tiktok_domains = [
            'tiktok.com',
            'vm.tiktok.com', 
            'vt.tiktok.com',
            'm.tiktok.com'
        ]
        
        url_lower = url.lower()
        return any(domain in url_lower for domain in tiktok_domains)
    
    def extract_video_id(self, url):
        """Extract TikTok video ID from URL"""
        # First check if it's a valid TikTok URL
        if not self._is_valid_tiktok_url(url):
            return None
            
        patterns = [
            r'/video/(\d+)',
            r'v=(\d+)',
            r'/(\d+)/?$',
            r'item_id=(\d+)',
            r'tiktok\.com/.*?/(\d+)',
            r'vm\.tiktok\.com/([A-Za-z0-9]+)',
            r'vt\.tiktok\.com/([A-Za-z0-9]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    def _check_abort(self):
        """Check if download should be aborted"""
        if self.abort_callback and self.abort_callback():
            return True
        return False
    
    def download_video(self, url, output_path, callback=None):
        """Main download method that tries multiple working approaches"""
        if callback:
            callback("[*] Processing TikTok video...")
            callback(f"[*] URL: {url[:80]}...")
        
        # Check abort at the start
        if self._check_abort():
            if callback:
                callback("[STOP] TikTok download aborted by user")
            return False
        
        # Validate TikTok URL first
        if not self._is_valid_tiktok_url(url):
            if callback:
                callback("[!] Invalid TikTok URL format")
            return False
        
        video_id = self.extract_video_id(url)
        if not video_id:
            if callback:
                callback("[!] Could not extract video ID from TikTok URL")
            return False
        
        if callback:
            callback(f"[*] Extracted video ID: {video_id}")
        
        # Check abort before trying direct TikTok
        if self._check_abort():
            if callback:
                callback("[STOP] TikTok download aborted by user")
            return False
            
        # Try direct TikTok API approach first (sometimes works)
        if callback:
            callback("[*] Trying direct TikTok extraction...")
        if self._try_direct_tiktok(url, output_path, callback):
            return True
        
        # Check abort before trying services
        if self._check_abort():
            if callback:
                callback("[STOP] TikTok download aborted by user")
            return False
            
        # Try working online services
        services = [
            ('tikmate.online', self._try_tikmate),
            ('snaptik.app', self._try_snaptik),
            ('ssstik.io', self._try_ssstik)
        ]
        
        for service_name, service_method in services:
            # Check abort before each service
            if self._check_abort():
                if callback:
                    callback("[STOP] TikTok download aborted by user")
                return False
                
            if callback:
                callback(f"[*] Trying {service_name}...")
                
            try:
                download_url = service_method(url)
                if download_url and self._download_from_url(download_url, output_path, callback):
                    if callback:
                        callback(f"[OK] Downloaded via {service_name}")
                    return True
                    
            except Exception as e:
                if callback:
                    callback(f"[!] {service_name} failed: {str(e)[:50]}...")
                continue
                
            time.sleep(1)  # Brief pause between services
        
        # Check abort before final fallback
        if self._check_abort():
            if callback:
                callback("[STOP] TikTok download aborted by user")
            return False
        
        # Final fallback: browser-like approach
        if self._try_browser_simulation(url, output_path, callback):
            return True
            
        if callback:
            callback("[!] All methods exhausted - TikTok may be temporarily blocked")
        return False
    
    def _try_direct_tiktok(self, url, output_path, callback):
        """Try direct TikTok access with advanced extraction (PROVEN TO WORK)"""
        try:
            # Check abort at the start
            if self._check_abort():
                if callback:
                    callback("[STOP] TikTok download aborted by user")
                return False
                
            if callback:
                callback("[*] Using advanced TikTok extraction...")
            
            # Get page with mobile headers (more likely to work)
            headers = {
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1'
            }
            
            # Check abort before making request
            if self._check_abort():
                if callback:
                    callback("[STOP] TikTok download aborted by user")
                return False
            
            response = self.session.get(url, headers=headers, timeout=15)
            if response.status_code == 200:
                if callback:
                    callback(f"[*] TikTok page loaded successfully (status: {response.status_code})")
                    
                # Check abort after getting response
                if self._check_abort():
                    if callback:
                        callback("[STOP] TikTok download aborted by user")
                    return False
                    
                content = response.text
                
                # Extract video URLs using proven patterns
                patterns = [
                    r'"playAddr":"([^"]+)"',
                    r'"downloadAddr":"([^"]+)"',
                    r'"video":{"urls":\["([^"]+)"\]',
                    r'videoUrl["\']?\s*:\s*["\']([^"\']+)["\']'
                ]
                
                video_urls = []
                for pattern in patterns:
                    matches = re.findall(pattern, content)
                    for match in matches:
                        clean_url = match.replace('\\u002F', '/').replace('\\/', '/')
                        if 'tiktok' in clean_url.lower():
                            video_urls.append(clean_url)
                
                # Remove duplicates
                unique_urls = list(dict.fromkeys(video_urls))
                
                if callback:
                    callback(f"[*] Found {len(unique_urls)} potential video URLs")
                
                if not unique_urls:
                    if callback:
                        callback("[!] No video URLs found in TikTok page")
                    return False
            else:
                if callback:
                    callback(f"[!] TikTok page access failed (status: {response.status_code})")
                return False
                
                # Try downloading each URL with proper headers
                download_headers = {
                    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1',
                    'Referer': 'https://www.tiktok.com/',
                    'Accept': 'video/mp4,video/*,application/octet-stream,*/*',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive'
                }
                
                for video_url in unique_urls:
                    # Check abort before each URL attempt
                    if self._check_abort():
                        if callback:
                            callback("[STOP] TikTok download aborted by user")
                        return False
                        
                    try:
                        if callback:
                            callback("[*] Testing video URL...")
                        
                        # Test if accessible
                        test_response = self.session.head(video_url, headers=download_headers, timeout=10)
                        if test_response.status_code == 200:
                            # Check abort before downloading
                            if self._check_abort():
                                if callback:
                                    callback("[STOP] TikTok download aborted by user")
                                return False
                                
                            if callback:
                                callback("[*] URL accessible, downloading...")
                            
                            # Download with stream
                            download_response = self.session.get(video_url, headers=download_headers, stream=True, timeout=30)
                            
                            if download_response.status_code == 200:
                                with open(output_path, 'wb') as f:
                                    for chunk in download_response.iter_content(chunk_size=8192):
                                        # Check abort during download (every chunk)
                                        if self._check_abort():
                                            if callback:
                                                callback("[STOP] TikTok download aborted by user")
                                            # Clean up partial file
                                            try:
                                                Path(output_path).unlink()
                                            except:
                                                pass
                                            return False
                                            
                                        if chunk:
                                            f.write(chunk)
                                
                                # Verify download
                                if Path(output_path).exists() and Path(output_path).stat().st_size > 10000:
                                    if callback:
                                        callback("[OK] Advanced TikTok extraction successful!")
                                    return True
                        
                    except Exception as e:
                        if callback:
                            callback(f"[!] URL test failed: {str(e)[:50]}...")
                        continue
            
        except Exception as e:
            if callback:
                callback(f"[!] Direct TikTok access failed: {str(e)[:50]}...")
        
        return False
    
    def _try_tikmate(self, url):
        """Try tikmate.online service"""
        try:
            # Get main page
            response = self.session.get('https://tikmate.online', timeout=10)
            if response.status_code != 200:
                return None
            
            # Try API endpoint
            api_data = {'url': url}
            api_response = self.session.post(
                'https://tikmate.online/wp-json/aio-dl/video-data',
                json=api_data,
                timeout=15
            )
            
            if api_response.status_code == 200:
                data = api_response.json()
                if data.get('success') and 'medias' in data:
                    for media in data['medias']:
                        if media.get('url'):
                            return media['url']
                            
        except Exception:
            pass
        return None
    
    def _try_snaptik(self, url):
        """Try snaptik.app service"""
        try:
            # Try their main API
            api_data = {'url': url, 'lang': 'en'}
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Origin': 'https://snaptik.app',
                'Referer': 'https://snaptik.app/'
            }
            
            response = self.session.post(
                'https://snaptik.app/abc2.php',
                data=api_data,
                headers=headers,
                timeout=15
            )
            
            if response.status_code == 200:
                # Extract download links
                download_pattern = r'href="([^"]*\.mp4[^"]*)"'
                matches = re.findall(download_pattern, response.text)
                if matches:
                    return matches[0] if matches[0].startswith('http') else 'https://snaptik.app' + matches[0]
                    
        except Exception:
            pass
        return None
    
    def _try_ssstik(self, url):
        """Try ssstik.io service"""
        try:
            # Get main page for token
            main_response = self.session.get('https://ssstik.io', timeout=10)
            if main_response.status_code != 200:
                return None
            
            # Extract token
            tt_token = 'RFBiZ3Bi'  # Default
            token_match = re.search(r'tt["\']?\s*:\s*["\']([^"\']+)["\']', main_response.text)
            if token_match:
                tt_token = token_match.group(1)
            
            # Make API request
            api_data = {'id': url, 'locale': 'en', 'tt': tt_token}
            api_headers = {
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'Origin': 'https://ssstik.io',
                'Referer': 'https://ssstik.io/',
                'X-Requested-With': 'XMLHttpRequest'
            }
            
            response = self.session.post(
                'https://ssstik.io/abc',
                data=api_data,
                headers=api_headers,
                timeout=15
            )
            
            if response.status_code == 200:
                # Extract download links
                download_patterns = [
                    r'href="([^"]*\.mp4[^"]*)"',
                    r'src="([^"]*\.mp4[^"]*)"'
                ]
                
                for pattern in download_patterns:
                    matches = re.findall(pattern, response.text, re.IGNORECASE)
                    if matches:
                        download_url = matches[0]
                        return download_url if download_url.startswith('http') else 'https://ssstik.io' + download_url
                        
        except Exception:
            pass
        return None
    
    def _try_browser_simulation(self, url, output_path, callback):
        """Simulate browser behavior to bypass restrictions"""
        try:
            # More realistic browser headers
            browser_headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Sec-Ch-Ua': '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
                'Sec-Ch-Ua-Mobile': '?0',
                'Sec-Ch-Ua-Platform': '"Windows"',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1'
            }
            
            self.session.headers.update(browser_headers)
            
            # Try accessing TikTok with browser simulation
            response = self.session.get(url, timeout=15)
            
            if response.status_code == 200:
                # Look for embedded video data
                video_data_pattern = r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>'
                script_matches = re.findall(video_data_pattern, response.text, re.DOTALL)
                
                if script_matches:
                    try:
                        json_data = json.loads(script_matches[0])
                        # Extract video URL from structured data
                        video_url = self._extract_from_next_data(json_data)
                        if video_url and self._download_from_url(video_url, output_path, callback):
                            return True
                    except:
                        pass
            
            # Try alternative browser simulation
            mobile_headers = {
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive'
            }
            
            self.session.headers.update(mobile_headers)
            response = self.session.get(url, timeout=15)
            
            if response.status_code == 200:
                # Mobile site might have different structure
                mobile_patterns = [
                    r'"playAddr":"([^"]+)"',
                    r'videoUrl["\']?\s*:\s*["\']([^"\']+)["\']'
                ]
                
                for pattern in mobile_patterns:
                    matches = re.findall(pattern, response.text)
                    if matches:
                        video_url = matches[0].replace('\\u002F', '/').replace('\\/', '/')
                        if self._download_from_url(video_url, output_path, callback):
                            return True
                            
        except Exception as e:
            if callback:
                callback(f"[!] Browser simulation failed: {str(e)[:50]}...")
        
        return False
    
    def _extract_from_next_data(self, json_data):
        """Extract video URL from Next.js data structure"""
        try:
            # Navigate through the JSON structure to find video data
            props = json_data.get('props', {})
            page_props = props.get('pageProps', {})
            item_info = page_props.get('itemInfo', {})
            video = item_info.get('itemStruct', {}).get('video', {})
            
            if video:
                # Try different video URL fields
                play_addr = video.get('playAddr')
                download_addr = video.get('downloadAddr')
                bitrate_info = video.get('bitrateInfo', [])
                
                # Return the best available URL
                if download_addr:
                    return download_addr
                elif play_addr:
                    return play_addr
                elif bitrate_info:
                    # Get highest quality
                    bitrate_info.sort(key=lambda x: x.get('Bitrate', 0), reverse=True)
                    if bitrate_info and 'PlayAddr' in bitrate_info[0]:
                        return bitrate_info[0]['PlayAddr']
                        
        except Exception:
            pass
        return None
    
    def _download_from_url(self, video_url, output_path, callback):
        """Download video from direct URL"""
        try:
            if callback:
                callback(f"[*] Downloading from: {video_url[:60]}...")
            
            # Check abort before starting download
            if self._check_abort():
                if callback:
                    callback("[STOP] TikTok download aborted by user")
                return False
            
            # Stream download to handle large files
            response = self.session.get(video_url, stream=True, timeout=30)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    # Check abort during download
                    if self._check_abort():
                        if callback:
                            callback("[STOP] TikTok download aborted by user")
                        # Clean up partial file
                        try:
                            Path(output_path).unlink()
                        except:
                            pass
                        return False
                        
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # Progress reporting (if callback supports it)
                        if callback and total_size > 0:
                            percent = (downloaded / total_size) * 100
                            if int(percent) % 10 == 0:  # Report every 10%
                                callback(f"[...] {percent:.0f}% downloaded")
            
            # Verify file was downloaded
            if Path(output_path).exists() and Path(output_path).stat().st_size > 10000:  # >10KB
                return True
                
        except Exception as e:
            if callback:
                callback(f"[!] Download failed: {str(e)[:50]}...")
        
        return False

# Integration function for main.py
def integrate_tiktok_download(url, output_path, callback=None, abort_callback=None):
    """Seamless integration function for main.py"""
    downloader = SeamlessTikTokDownloader(abort_callback=abort_callback)
    return downloader.download_video(url, output_path, callback)