#!/usr/bin/env python3
"""
Multi-Platform Image Downloader
Supports: Pinterest, Google Images, Instagram, Twitter, Tumblr, Flickr, DeviantArt, and direct URLs
"""

import os
import re
import json
import time
import hashlib
import requests
from pathlib import Path
from urllib.parse import urlparse, urljoin, unquote, parse_qs
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional, Callable

# Optional imports for advanced features
try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False


class ImageDownloader:
    """Professional multi-platform image downloader with batch support"""
    
    # Supported platforms and their patterns
    PLATFORMS = {
        'pinterest': ['pinterest.com', 'pin.it'],
        'instagram': ['instagram.com', 'instagr.am'],
        'twitter': ['twitter.com', 'x.com', 'pbs.twimg.com'],
        'tumblr': ['tumblr.com'],
        'flickr': ['flickr.com', 'flic.kr'],
        'deviantart': ['deviantart.com'],
        'google': ['google.com/imgres', 'images.google'],
        'imgur': ['imgur.com', 'i.imgur.com'],
        'reddit': ['reddit.com', 'i.redd.it', 'preview.redd.it'],
        'pixiv': ['pixiv.net'],
        'artstation': ['artstation.com'],
        'unsplash': ['unsplash.com'],
        'pexels': ['pexels.com'],
        'direct': []  # Direct image URLs
    }
    
    # Common image extensions
    IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg', '.ico', '.tiff', '.tif'}
    
    # User agents for different scenarios
    USER_AGENTS = {
        'desktop': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'mobile': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
        'bot': 'Mozilla/5.0 (compatible; ImageBot/1.0; +http://example.com/bot)'
    }
    
    def __init__(self, output_dir: str = "downloads/images"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.session = self._create_session()
        self.driver = None
        self.downloaded_hashes = set()  # Track downloaded images to avoid duplicates
        
        # Load existing files to avoid re-downloading
        self._load_existing_files()
        
    def _load_existing_files(self):
        """Load hashes of existing files to avoid re-downloading duplicates"""
        try:
            # Scan output directory and subdirectories for existing images
            for file_path in self.output_dir.rglob('*'):
                if file_path.is_file() and file_path.suffix.lower() in self.IMAGE_EXTENSIONS:
                    try:
                        with open(file_path, 'rb') as f:
                            content = f.read()
                            file_hash = self._get_file_hash(content)
                            self.downloaded_hashes.add(file_hash)
                    except:
                        continue  # Skip files we can't read
        except:
            pass  # If directory scanning fails, continue without pre-loading
        
    def _create_session(self) -> requests.Session:
        """Create a requests session with proper headers"""
        session = requests.Session()
        session.headers.update({
            'User-Agent': self.USER_AGENTS['desktop'],
            'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'DNT': '1',
        })
        return session
    
    def _get_selenium_driver(self):
        """Get or create Selenium WebDriver for JavaScript-heavy sites"""
        if not SELENIUM_AVAILABLE:
            return None
        
        if self.driver is None:
            try:
                options = Options()
                options.add_argument('--headless')
                options.add_argument('--disable-gpu')
                options.add_argument('--no-sandbox')
                options.add_argument('--disable-dev-shm-usage')
                options.add_argument('--disable-extensions')
                options.add_argument('--disable-plugins')
                options.add_argument('--disable-images')
                options.add_argument('--disable-web-security')
                options.add_argument('--disable-features=VizDisplayCompositor')
                options.add_argument('--disable-logging')
                options.add_argument('--log-level=3')
                options.add_argument('--silent')
                options.add_argument('--disable-background-timer-throttling')
                options.add_argument('--disable-backgrounding-occluded-windows')
                options.add_argument('--disable-renderer-backgrounding')
                options.add_argument(f'--user-agent={self.USER_AGENTS["desktop"]}')
                options.add_argument('--window-size=1920,1080')
                options.add_argument('--page-load-strategy=eager')
                
                # Suppress DevTools and GPU messages
                options.add_experimental_option('excludeSwitches', ['enable-logging'])
                options.add_experimental_option('useAutomationExtension', False)
                options.add_experimental_option('excludeSwitches', ['enable-automation'])
                
                # Create service
                service = Service(ChromeDriverManager().install())
                
                # Create driver directly - no complex timeout handling
                self.driver = webdriver.Chrome(service=service, options=options)
                self.driver.set_page_load_timeout(10)
                self.driver.implicitly_wait(3)
                
            except Exception as e:
                print(f"Failed to create Selenium driver: {e}")
                return None
        
        return self.driver
    
    def close(self):
        """Clean up resources"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None
        self.session.close()

    
    def detect_platform(self, url: str) -> str:
        """Detect the platform from URL"""
        url_lower = url.lower()
        
        # Check for base64 data URL
        if url_lower.startswith('data:image/'):
            return 'base64'
        
        for platform, patterns in self.PLATFORMS.items():
            for pattern in patterns:
                if pattern in url_lower:
                    return platform
        
        # Check if it's a direct image URL
        parsed = urlparse(url)
        ext = Path(parsed.path).suffix.lower()
        if ext in self.IMAGE_EXTENSIONS:
            return 'direct'
        
        return 'unknown'
    
    def _get_file_hash(self, content: bytes) -> str:
        """Get MD5 hash of content for duplicate detection"""
        return hashlib.md5(content).hexdigest()
    
    def _sanitize_filename(self, filename: str, max_length: int = 200) -> str:
        """Sanitize filename for Windows compatibility"""
        # Remove invalid characters
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        filename = re.sub(r'[^\x00-\x7F]+', '_', filename)
        filename = re.sub(r'\s+', ' ', filename).strip()
        
        # Limit length
        if len(filename) > max_length:
            name, ext = os.path.splitext(filename)
            filename = name[:max_length - len(ext)] + ext
        
        return filename or 'image'
    
    def _get_extension_from_content_type(self, content_type: str) -> str:
        """Get file extension from content type"""
        mapping = {
            'image/jpeg': '.jpg',
            'image/png': '.png',
            'image/gif': '.gif',
            'image/webp': '.webp',
            'image/svg+xml': '.svg',
            'image/bmp': '.bmp',
            'image/tiff': '.tiff',
            'image/x-icon': '.ico',
        }
        return mapping.get(content_type.split(';')[0].strip(), '.jpg')
    
    def download_image(self, url: str, filename: str = None, 
                       subfolder: str = None, callback: Callable = None,
                       pinterest_max: int = 50) -> Dict:
        """
        Download a single image from URL
        
        Args:
            url: Image URL to download
            filename: Custom filename (optional)
            subfolder: Subfolder within output directory (optional)
            callback: Progress callback function (optional)
            pinterest_max: Max images for Pinterest search URLs (default 50)
            
        Returns:
            Dict with success status, file_path, and error message if any
        """
        try:
            if callback:
                callback(f"📥 Downloading: {url[:60]}...")
            
            # Determine output path
            output_path = self.output_dir
            if subfolder:
                output_path = output_path / self._sanitize_filename(subfolder)
                output_path.mkdir(parents=True, exist_ok=True)
            
            # Handle different platforms
            platform = self.detect_platform(url)
            
            if platform == 'base64':
                return self._download_base64(url, output_path, filename, callback)
            elif platform == 'pinterest':
                return self._download_pinterest(url, output_path, filename, callback, pinterest_max)
            elif platform == 'instagram':
                return self._download_instagram(url, output_path, filename, callback)
            elif platform == 'google':
                return self._download_google_image(url, output_path, filename, callback)
            elif platform == 'twitter':
                return self._download_twitter(url, output_path, filename, callback)
            elif platform == 'imgur':
                return self._download_imgur(url, output_path, filename, callback)
            else:
                return self._download_direct(url, output_path, filename, callback)
                
        except Exception as e:
            error_msg = str(e)
            if callback:
                callback(f"❌ Error: {error_msg}")
            return {'success': False, 'error': error_msg, 'url': url}
    
    def _download_direct(self, url: str, output_path: Path, 
                         filename: str = None, callback: Callable = None) -> Dict:
        """Download image from direct URL with duplicate detection"""
        try:
            # Make request with streaming
            response = self.session.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            # Get content type and determine extension
            content_type = response.headers.get('Content-Type', 'image/jpeg')
            
            # Download content first to check for duplicates
            content = response.content
            
            # Check for duplicates by hash
            file_hash = self._get_file_hash(content)
            if file_hash in self.downloaded_hashes:
                if callback:
                    callback(f"⏭ Skipped duplicate (same content)")
                return {'success': True, 'file_path': '', 'skipped': True, 'reason': 'duplicate_hash'}
            
            # Determine filename
            if not filename:
                # Try to get from URL
                parsed = urlparse(url)
                url_filename = Path(unquote(parsed.path)).name
                if url_filename and '.' in url_filename:
                    filename = url_filename
                else:
                    # Generate from hash (this ensures unique names for same content)
                    ext = self._get_extension_from_content_type(content_type)
                    filename = f"image_{file_hash[:12]}{ext}"
            
            filename = self._sanitize_filename(filename)
            
            # Ensure proper extension
            if not any(filename.lower().endswith(ext) for ext in self.IMAGE_EXTENSIONS):
                ext = self._get_extension_from_content_type(content_type)
                filename += ext
            
            file_path = output_path / filename
            
            # Check if file already exists with same content
            if file_path.exists():
                try:
                    with open(file_path, 'rb') as existing_file:
                        existing_content = existing_file.read()
                        existing_hash = self._get_file_hash(existing_content)
                        if existing_hash == file_hash:
                            if callback:
                                callback(f"⏭ Skipped duplicate (file exists): {filename}")
                            self.downloaded_hashes.add(file_hash)
                            return {'success': True, 'file_path': str(file_path), 'skipped': True, 'reason': 'duplicate_file'}
                except:
                    pass  # If we can't read the existing file, continue with download
            
            # Handle filename conflicts (different content, same name)
            counter = 1
            original_path = file_path
            while file_path.exists():
                stem = original_path.stem
                suffix = original_path.suffix
                file_path = output_path / f"{stem}_{counter}{suffix}"
                counter += 1
            
            # Save file
            with open(file_path, 'wb') as f:
                f.write(content)
            
            # Add to downloaded hashes to prevent future duplicates
            self.downloaded_hashes.add(file_hash)
            
            # Get file size
            file_size = len(content)
            size_str = f"{file_size / 1024:.1f}KB" if file_size < 1024*1024 else f"{file_size / 1024 / 1024:.1f}MB"
            
            if callback:
                callback(f"✅ Saved: {file_path.name} ({size_str})")
            
            return {
                'success': True,
                'file_path': str(file_path),
                'size': file_size,
                'platform': 'direct'
            }
            
        except requests.exceptions.RequestException as e:
            return {'success': False, 'error': f"Download failed: {str(e)}", 'url': url}

    def _download_base64(self, data_url: str, output_path: Path,
                         filename: str = None, callback: Callable = None) -> Dict:
        """Download image from base64 data URL"""
        import base64
        
        try:
            if callback:
                callback("🔍 Decoding base64 image...")
            
            # Parse the data URL
            # Format: data:image/jpeg;base64,/9j/4AAQ...
            if not data_url.startswith('data:'):
                return {'success': False, 'error': 'Invalid data URL format', 'url': data_url[:50]}
            
            # Extract mime type and data
            header, encoded = data_url.split(',', 1)
            
            # Get mime type (e.g., "image/jpeg" from "data:image/jpeg;base64")
            mime_part = header.split(':')[1] if ':' in header else ''
            mime_type = mime_part.split(';')[0] if ';' in mime_part else mime_part
            
            # Determine extension from mime type
            ext_map = {
                'image/jpeg': '.jpg',
                'image/jpg': '.jpg',
                'image/png': '.png',
                'image/gif': '.gif',
                'image/webp': '.webp',
                'image/bmp': '.bmp',
                'image/svg+xml': '.svg',
                'image/tiff': '.tiff',
                'image/x-icon': '.ico'
            }
            ext = ext_map.get(mime_type, '.jpg')
            
            # Decode base64 data
            try:
                content = base64.b64decode(encoded)
            except Exception as e:
                return {'success': False, 'error': f'Failed to decode base64: {str(e)}', 'url': data_url[:50]}
            
            # Generate filename if not provided
            if not filename:
                filename = f"base64_image_{int(time.time())}_{hash(data_url) % 10000}{ext}"
            else:
                # Ensure proper extension
                if not any(filename.lower().endswith(e) for e in self.IMAGE_EXTENSIONS):
                    filename += ext
            
            filename = self._sanitize_filename(filename)
            file_path = output_path / filename
            
            # Check for duplicates
            file_hash = self._get_file_hash(content)
            if file_hash in self.downloaded_hashes:
                if callback:
                    callback(f"⏭ Skipped duplicate: {filename}")
                return {'success': True, 'file_path': str(file_path), 'skipped': True, 'reason': 'duplicate'}
            
            # Handle filename conflicts
            counter = 1
            original_path = file_path
            while file_path.exists():
                stem = original_path.stem
                suffix = original_path.suffix
                file_path = output_path / f"{stem}_{counter}{suffix}"
                counter += 1
            
            # Save file
            with open(file_path, 'wb') as f:
                f.write(content)
            
            self.downloaded_hashes.add(file_hash)
            
            # Get file size
            file_size = len(content)
            size_str = f"{file_size / 1024:.1f}KB" if file_size < 1024*1024 else f"{file_size / 1024 / 1024:.1f}MB"
            
            if callback:
                callback(f"✅ Saved: {file_path.name} ({size_str})")
            
            return {
                'success': True,
                'file_path': str(file_path),
                'size': file_size,
                'platform': 'base64'
            }
            
        except Exception as e:
            return {'success': False, 'error': f"Base64 decode failed: {str(e)}", 'url': data_url[:50]}

    
    def _download_pinterest(self, url: str, output_path: Path,
                            filename: str = None, callback: Callable = None,
                            pinterest_max: int = 50) -> Dict:
        """Download image from Pinterest - supports both pins and search URLs"""
        try:
            # Check if this is a Pinterest search URL - handle these specially
            if '/search/' in url or 'q=' in url:
                if callback:
                    callback("🔍 Pinterest search URL detected - extracting images...")
                return self._download_pinterest_search(url, output_path, callback, pinterest_max)
            
            if callback:
                callback("🔍 Extracting Pinterest image...")
            
            # For regular Pinterest pins, use fast HTTP requests only - NO SELENIUM
            headers = {
                'User-Agent': self.USER_AGENTS['desktop'],
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Referer': 'https://www.pinterest.com/',
                'DNT': '1',
            }
            
            # Handle short URLs (pin.it) - follow redirects to get full URL
            if 'pin.it' in url:
                if callback:
                    callback("🔗 Resolving Pinterest short URL...")
                try:
                    redirect_response = self.session.head(url, headers=headers, allow_redirects=True, timeout=10)
                    if redirect_response.url and 'pinterest' in redirect_response.url:
                        url = redirect_response.url
                        if callback:
                            callback(f"🔗 Resolved to: {url[:60]}...")
                except Exception as e:
                    if callback:
                        callback(f"⚠️ Could not resolve short URL, trying original...")
            
            # Get the page content
            response = self.session.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            # Try to find the original image URL using multiple methods
            image_url = None
            
            # Method 1: Look for og:image meta tag (most reliable)
            if BS4_AVAILABLE:
                soup = BeautifulSoup(response.text, 'html.parser')
                og_image = soup.find('meta', property='og:image')
                if og_image and og_image.get('content'):
                    image_url = og_image['content']
                    if callback:
                        callback(f"📷 Found og:image")
            
            # Method 2: Regex patterns for Pinterest image URLs
            if not image_url:
                patterns = [
                    r'"originals":\s*{\s*"url":\s*"([^"]+)"',
                    r'"orig":\s*{\s*"url":\s*"([^"]+)"',
                    r'"736x":\s*{\s*"url":\s*"([^"]+)"',
                    r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"',
                    r'"url":\s*"(https://i\.pinimg\.com/[^"]+)"',
                ]
                for pattern in patterns:
                    match = re.search(pattern, response.text)
                    if match:
                        image_url = match.group(1)
                        if 'pinimg.com' in image_url:
                            break
            
            # Method 3: Find any pinimg.com URL in the page
            if not image_url:
                if callback:
                    callback("🔍 Searching for Pinterest CDN URLs...")
                pinimg_patterns = [
                    r'(https://i\.pinimg\.com/originals/[a-zA-Z0-9/._-]+\.(?:jpg|jpeg|png|gif|webp))',
                    r'(https://i\.pinimg\.com/736x/[a-zA-Z0-9/._-]+\.(?:jpg|jpeg|png|gif|webp))',
                    r'(https://i\.pinimg\.com/564x/[a-zA-Z0-9/._-]+\.(?:jpg|jpeg|png|gif|webp))',
                ]
                for pattern in pinimg_patterns:
                    matches = re.findall(pattern, response.text)
                    if matches:
                        image_url = matches[0]
                        if callback:
                            callback(f"📷 Found CDN URL: {image_url[:50]}...")
                        break
            
            if not image_url:
                return {'success': False, 'error': 'Could not find image URL on Pinterest page. The pin may be private or deleted.', 'url': url}
            
            # Clean up URL and try to get highest resolution
            original_url = image_url
            image_url = image_url.replace('\\/', '/').replace('\\u002F', '/')
            high_res_url = self._get_pinterest_high_res(image_url)
            
            if callback:
                if high_res_url != image_url:
                    callback(f"🔍 Upgraded to higher resolution")
                    callback(f"   Original: {image_url[:60]}...")
                    callback(f"   High-res: {high_res_url[:60]}...")
                else:
                    callback(f"📷 Using found URL: {image_url[:60]}...")
            
            image_url = high_res_url
            
            if callback:
                callback(f"📥 Downloading image...")
            
            return self._download_direct(image_url, output_path, filename, callback)
            
        except Exception as e:
            return {'success': False, 'error': f"Pinterest download failed: {str(e)}", 'url': url}

    
    def _download_pinterest_search(self, url: str, output_path: Path,
                                    callback: Callable = None, max_images: int = 20) -> Dict:
        """Download images from Pinterest search results - hybrid approach with duplicate removal"""
        try:
            if callback:
                callback(f"🔍 Extracting images from Pinterest search (max {max_images})...")
            
            # First try HTTP-only approach (fast but limited)
            image_urls = self._get_pinterest_search_http(url, callback, min(max_images, 10))
            
            # If we need more images and have Selenium available, use it
            if len(image_urls) < max_images and SELENIUM_AVAILABLE:
                if callback:
                    callback(f"📜 Found {len(image_urls)} images with HTTP, using browser for more...")
                selenium_urls = self._get_pinterest_search_selenium(url, callback, max_images)
                
                # Combine and deduplicate URLs
                for url_item in selenium_urls:
                    if url_item not in image_urls and len(image_urls) < max_images:
                        image_urls.append(url_item)
            
            elif len(image_urls) < max_images and not SELENIUM_AVAILABLE:
                if callback:
                    callback(f"⚠️ Only found {len(image_urls)} images with HTTP. Install Selenium for more: pip install selenium webdriver-manager")
            
            if not image_urls:
                return {'success': False, 'error': 'No images found in Pinterest search results. Try a different search term.', 'url': url}
            
            # Remove duplicate URLs (same URL appearing multiple times)
            unique_urls = []
            seen_urls = set()
            for img_url in image_urls:
                if img_url not in seen_urls:
                    seen_urls.add(img_url)
                    unique_urls.append(img_url)
            
            if callback:
                callback(f"📊 Found {len(unique_urls)} unique images (removed {len(image_urls) - len(unique_urls)} duplicate URLs)")
            
            # Download all found images
            downloaded = 0
            failed = 0
            skipped = 0
            
            for i, img_url in enumerate(unique_urls[:max_images], 1):
                if callback:
                    callback(f"📥 Downloading image {i}/{len(unique_urls[:max_images])}...")
                
                result = self._download_direct(img_url, output_path, None, None)
                if result.get('success'):
                    if result.get('skipped'):
                        skipped += 1
                    else:
                        downloaded += 1
                else:
                    failed += 1
            
            return {
                'success': downloaded > 0,
                'downloaded': downloaded,
                'failed': failed,
                'skipped': skipped,
                'total': len(unique_urls[:max_images]),
                'message': f'Downloaded {downloaded}/{len(unique_urls[:max_images])} images from Pinterest search ({skipped} duplicates skipped)'
            }
                
        except Exception as e:
            return {'success': False, 'error': f"Pinterest search download failed: {str(e)}", 'url': url}
    
    def _get_pinterest_search_http(self, url: str, callback: Callable = None, max_images: int = 10) -> List[str]:
        """Get Pinterest search images using HTTP only (fast but limited)"""
        try:
            headers = {
                'User-Agent': self.USER_AGENTS['desktop'],
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Referer': 'https://www.pinterest.com/',
                'DNT': '1',
            }
            
            response = self.session.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            image_urls = []
            
            # Look for Pinterest CDN URLs in the HTML
            pinimg_patterns = [
                r'(https://i\.pinimg\.com/originals/[a-zA-Z0-9/._-]+\.(?:jpg|jpeg|png|gif|webp))',
                r'(https://i\.pinimg\.com/736x/[a-zA-Z0-9/._-]+\.(?:jpg|jpeg|png|gif|webp))',
                r'(https://i\.pinimg\.com/564x/[a-zA-Z0-9/._-]+\.(?:jpg|jpeg|png|gif|webp))',
                r'(https://i\.pinimg\.com/474x/[a-zA-Z0-9/._-]+\.(?:jpg|jpeg|png|gif|webp))',
            ]
            
            for pattern in pinimg_patterns:
                matches = re.findall(pattern, response.text)
                for match in matches:
                    if match not in image_urls:
                        # Try to upgrade to highest resolution
                        high_res_url = self._get_pinterest_high_res(match)
                        image_urls.append(high_res_url)
                        if len(image_urls) >= max_images:
                            break
                if len(image_urls) >= max_images:
                    break
            
            return image_urls
            
        except Exception as e:
            if callback:
                callback(f"⚠️ HTTP search failed: {str(e)}")
            return []
    
    def _get_pinterest_search_selenium(self, url: str, callback: Callable = None, max_images: int = 50) -> List[str]:
        """Get Pinterest search images using Selenium (slower but gets more images)"""
        if not SELENIUM_AVAILABLE:
            return []
        
        driver = None
        try:
            if callback:
                callback("🌐 Starting browser (this may take a moment)...")
            
            driver = self._get_selenium_driver()
            if not driver:
                if callback:
                    callback("❌ Could not start browser")
                return []
            
            if callback:
                callback("📱 Loading Pinterest search page...")
            
            driver.get(url)
            time.sleep(2)  # Wait for initial load
            
            if callback:
                callback("📜 Scrolling to find more images...")
            
            image_urls = []
            scroll_count = 0
            max_scrolls = max(5, max_images // 15)  # Adjust scrolls based on desired images
            no_new_images_count = 0
            
            while len(image_urls) < max_images and scroll_count < max_scrolls:
                # Find pin images
                prev_count = len(image_urls)
                try:
                    pins = driver.find_elements(By.CSS_SELECTOR, 'img[src*="pinimg.com"]')
                    
                    for pin in pins:
                        if len(image_urls) >= max_images:
                            break
                        
                        try:
                            src = pin.get_attribute('src')
                            if src and 'pinimg.com' in src:
                                # Upgrade resolution in URL directly
                                high_res_url = self._get_pinterest_high_res(src)
                                
                                if high_res_url not in image_urls:
                                    image_urls.append(high_res_url)
                                    if callback and len(image_urls) % 10 == 0:
                                        callback(f"🔍 Browser found: {len(image_urls)} images...")
                        except:
                            continue
                except:
                    pass
                
                # Check if we found new images
                if len(image_urls) == prev_count:
                    no_new_images_count += 1
                    if no_new_images_count >= 3:
                        if callback:
                            callback("📜 No more new images found, finishing...")
                        break
                else:
                    no_new_images_count = 0
                
                # Scroll down to load more images
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1.5)
                scroll_count += 1
            
            if callback:
                callback(f"✅ Browser finished - found {len(image_urls)} images")
            
            return image_urls
            
        except Exception as e:
            if callback:
                callback(f"⚠️ Browser search failed: {str(e)}")
            return []
        
        finally:
            # Always clean up driver
            if driver:
                try:
                    driver.quit()
                except:
                    pass
            self.driver = None
    
    def _extract_pinterest_image_from_json(self, data, depth=0) -> Optional[str]:
        """Recursively extract image URL from Pinterest JSON data"""
        if depth > 10:  # Prevent infinite recursion
            return None
        
        if isinstance(data, dict):
            # Look for image URLs in common Pinterest JSON structures
            for key in ['originals', 'orig', '736x', '564x', '474x']:
                if key in data and isinstance(data[key], dict):
                    if 'url' in data[key]:
                        return data[key]['url']
            
            # Recurse into nested structures
            for value in data.values():
                result = self._extract_pinterest_image_from_json(value, depth + 1)
                if result:
                    return result
        
        elif isinstance(data, list):
            for item in data:
                result = self._extract_pinterest_image_from_json(item, depth + 1)
                if result:
                    return result
        
        return None
    
    def _get_pinterest_high_res(self, url: str) -> str:
        """Try to get highest resolution Pinterest image"""
        if not url or 'pinimg.com' not in url:
            return url
            
        # Pinterest URL patterns: /236x/, /474x/, /564x/, /736x/, /originals/
        # Also handle newer patterns like /1200x/ and other sizes
        resolutions = ['originals', '1200x', '736x', '564x', '474x', '236x']
        
        # First, try to replace any existing resolution with 'originals'
        for res in resolutions[1:]:  # Skip 'originals' in this loop
            if f'/{res}/' in url:
                # Try 'originals' first
                originals_url = url.replace(f'/{res}/', '/originals/')
                try:
                    response = self.session.head(originals_url, timeout=5)
                    if response.status_code == 200:
                        return originals_url
                except:
                    pass
                
                # If originals doesn't work, try other high resolutions
                for higher_res in resolutions:
                    if higher_res == res or higher_res == 'originals':
                        continue
                    test_url = url.replace(f'/{res}/', f'/{higher_res}/')
                    try:
                        response = self.session.head(test_url, timeout=5)
                        if response.status_code == 200:
                            return test_url
                    except:
                        continue
                break
        
        # If no resolution pattern found, try to add originals path
        if '/originals/' not in url and 'pinimg.com' in url:
            # Try to construct originals URL
            parts = url.split('/')
            for i, part in enumerate(parts):
                if 'pinimg.com' in part and i + 1 < len(parts):
                    # Insert 'originals' after the domain
                    parts.insert(i + 1, 'originals')
                    originals_url = '/'.join(parts)
                    try:
                        response = self.session.head(originals_url, timeout=5)
                        if response.status_code == 200:
                            return originals_url
                    except:
                        pass
                    break
        
        return url

    def _download_instagram(self, url: str, output_path: Path,
                            filename: str = None, callback: Callable = None) -> Dict:
        """Download image from Instagram"""
        try:
            if callback:
                callback("🔍 Extracting Instagram image...")
            
            # Instagram requires special handling - try multiple methods
            headers = {
                'User-Agent': self.USER_AGENTS['mobile'],
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            }
            
            response = self.session.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            image_url = None
            
            # Method 1: og:image meta tag
            if BS4_AVAILABLE:
                soup = BeautifulSoup(response.text, 'html.parser')
                og_image = soup.find('meta', property='og:image')
                if og_image and og_image.get('content'):
                    image_url = og_image['content']
            
            # Method 2: Regex patterns
            if not image_url:
                patterns = [
                    r'"display_url":\s*"([^"]+)"',
                    r'"src":\s*"([^"]+\.jpg[^"]*)"',
                    r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"',
                ]
                for pattern in patterns:
                    match = re.search(pattern, response.text)
                    if match:
                        image_url = match.group(1).replace('\\u0026', '&')
                        break
            
            if not image_url:
                return {'success': False, 'error': 'Could not find image URL. Instagram may require login.', 'url': url}
            
            return self._download_direct(image_url, output_path, filename, callback)
            
        except Exception as e:
            return {'success': False, 'error': f"Instagram download failed: {str(e)}", 'url': url}

    
    def _download_google_image(self, url: str, output_path: Path,
                               filename: str = None, callback: Callable = None) -> Dict:
        """Download image from Google Images result"""
        try:
            if callback:
                callback("🔍 Extracting Google Images URL...")
            
            # Parse Google Images URL to get actual image URL
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            
            # Google Images stores the actual URL in 'imgurl' parameter
            if 'imgurl' in params:
                image_url = params['imgurl'][0]
                return self._download_direct(image_url, output_path, filename, callback)
            
            # Try to extract from page
            response = self.session.get(url, timeout=30)
            
            # Look for actual image URL in response
            patterns = [
                r'"ou":"([^"]+)"',  # Original URL in JSON
                r'imgurl=([^&]+)',   # URL parameter
            ]
            
            for pattern in patterns:
                match = re.search(pattern, response.text)
                if match:
                    image_url = unquote(match.group(1))
                    return self._download_direct(image_url, output_path, filename, callback)
            
            return {'success': False, 'error': 'Could not extract image URL from Google', 'url': url}
            
        except Exception as e:
            return {'success': False, 'error': f"Google image download failed: {str(e)}", 'url': url}
    
    def _download_twitter(self, url: str, output_path: Path,
                          filename: str = None, callback: Callable = None) -> Dict:
        """Download image from Twitter/X"""
        try:
            # Check if it's already a direct image URL
            if 'pbs.twimg.com' in url:
                # Try to get highest quality
                if ':' in url and not url.endswith(':orig'):
                    url = url.rsplit(':', 1)[0] + ':orig'
                elif '?' not in url:
                    url = url + '?format=jpg&name=orig'
                return self._download_direct(url, output_path, filename, callback)
            
            if callback:
                callback("🔍 Extracting Twitter image...")
            
            # For tweet URLs, try to extract image
            response = self.session.get(url, timeout=30)
            
            image_url = None
            
            # Look for og:image
            if BS4_AVAILABLE:
                soup = BeautifulSoup(response.text, 'html.parser')
                og_image = soup.find('meta', property='og:image')
                if og_image and og_image.get('content'):
                    image_url = og_image['content']
            
            if not image_url:
                # Regex fallback
                match = re.search(r'(https://pbs\.twimg\.com/media/[^"\'>\s]+)', response.text)
                if match:
                    image_url = match.group(1)
            
            if image_url:
                # Get highest quality
                if ':' in image_url and not image_url.endswith(':orig'):
                    image_url = image_url.rsplit(':', 1)[0] + ':orig'
                return self._download_direct(image_url, output_path, filename, callback)
            
            return {'success': False, 'error': 'Could not find image in tweet', 'url': url}
            
        except Exception as e:
            return {'success': False, 'error': f"Twitter download failed: {str(e)}", 'url': url}
    
    def _download_imgur(self, url: str, output_path: Path,
                        filename: str = None, callback: Callable = None) -> Dict:
        """Download image from Imgur"""
        try:
            # Check if it's already a direct image URL
            if 'i.imgur.com' in url:
                return self._download_direct(url, output_path, filename, callback)
            
            if callback:
                callback("🔍 Extracting Imgur image...")
            
            # Extract image ID from URL
            match = re.search(r'imgur\.com/(?:a/|gallery/)?([a-zA-Z0-9]+)', url)
            if match:
                image_id = match.group(1)
                
                # Try direct URL patterns
                for ext in ['.png', '.jpg', '.gif']:
                    direct_url = f'https://i.imgur.com/{image_id}{ext}'
                    try:
                        response = self.session.head(direct_url, timeout=10)
                        if response.status_code == 200:
                            return self._download_direct(direct_url, output_path, filename, callback)
                    except:
                        continue
            
            # Fallback: try to get from page
            response = self.session.get(url, timeout=30)
            
            if BS4_AVAILABLE:
                soup = BeautifulSoup(response.text, 'html.parser')
                og_image = soup.find('meta', property='og:image')
                if og_image and og_image.get('content'):
                    return self._download_direct(og_image['content'], output_path, filename, callback)
            
            return {'success': False, 'error': 'Could not extract Imgur image URL', 'url': url}
            
        except Exception as e:
            return {'success': False, 'error': f"Imgur download failed: {str(e)}", 'url': url}

    
    def batch_download(self, urls: List[str], subfolder: str = None,
                       callback: Callable = None, max_workers: int = 4) -> Dict:
        """
        Download multiple images in parallel
        
        Args:
            urls: List of image URLs
            subfolder: Subfolder for all downloads
            callback: Progress callback
            max_workers: Number of parallel downloads
            
        Returns:
            Summary dict with success/failure counts
        """
        results = {
            'total': len(urls),
            'successful': 0,
            'failed': 0,
            'skipped': 0,
            'files': [],
            'errors': []
        }
        
        if callback:
            callback(f"📦 Starting batch download of {len(urls)} images...")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self.download_image, url, None, subfolder, callback): url
                for url in urls
            }
            
            for i, future in enumerate(as_completed(futures), 1):
                url = futures[future]
                try:
                    result = future.result()
                    if result['success']:
                        if result.get('skipped'):
                            results['skipped'] += 1
                        else:
                            results['successful'] += 1
                            results['files'].append(result.get('file_path', ''))
                    else:
                        results['failed'] += 1
                        results['errors'].append({'url': url, 'error': result.get('error', 'Unknown')})
                except Exception as e:
                    results['failed'] += 1
                    results['errors'].append({'url': url, 'error': str(e)})
                
                if callback:
                    callback(f"📊 Progress: {i}/{len(urls)} ({results['successful']} saved, {results['failed']} failed)")
        
        if callback:
            callback(f"✅ Batch complete: {results['successful']} saved, {results['failed']} failed, {results['skipped']} skipped")
        
        return results
    
    def search_and_download(self, query: str, platform: str = 'google',
                            max_images: int = 10, callback: Callable = None) -> Dict:
        """
        Search for images and download them
        
        Args:
            query: Search query
            platform: Platform to search (google, pinterest, etc.)
            max_images: Maximum number of images to download
            callback: Progress callback
            
        Returns:
            Summary dict
        """
        if not SELENIUM_AVAILABLE:
            return {'success': False, 'error': 'Selenium required for search. Install with: pip install selenium webdriver-manager'}
        
        if callback:
            callback(f"🔍 Searching for '{query}' on {platform}...")
        
        driver = self._get_selenium_driver()
        if not driver:
            return {'success': False, 'error': 'Could not initialize browser'}
        
        try:
            image_urls = []
            
            if platform == 'google':
                image_urls = self._search_google_images(driver, query, max_images, callback)
            elif platform == 'pinterest':
                image_urls = self._search_pinterest(driver, query, max_images, callback)
            else:
                return {'success': False, 'error': f'Search not supported for {platform}'}
            
            if not image_urls:
                return {'success': False, 'error': 'No images found'}
            
            if callback:
                callback(f"📥 Found {len(image_urls)} images, starting download...")
            
            # Create subfolder for search results
            subfolder = self._sanitize_filename(f"{platform}_{query}")
            
            return self.batch_download(image_urls, subfolder, callback)
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _search_google_images(self, driver, query: str, max_images: int, 
                              callback: Callable = None) -> List[str]:
        """Search Google Images and extract URLs"""
        try:
            search_url = f"https://www.google.com/search?q={query}&tbm=isch"
            driver.get(search_url)
            time.sleep(2)
            
            image_urls = []
            scroll_count = 0
            max_scrolls = max_images // 20 + 2
            
            while len(image_urls) < max_images and scroll_count < max_scrolls:
                # Find image elements
                images = driver.find_elements(By.CSS_SELECTOR, 'img.rg_i, img.Q4LuWd')
                
                for img in images:
                    if len(image_urls) >= max_images:
                        break
                    
                    try:
                        # Click to load full resolution
                        img.click()
                        time.sleep(0.5)
                        
                        # Find the full resolution image
                        full_imgs = driver.find_elements(By.CSS_SELECTOR, 'img.n3VNCb, img.iPVvYb')
                        for full_img in full_imgs:
                            src = full_img.get_attribute('src')
                            if src and src.startswith('http') and 'google' not in src:
                                if src not in image_urls:
                                    image_urls.append(src)
                                    if callback:
                                        callback(f"🔍 Found: {len(image_urls)}/{max_images}")
                                break
                    except:
                        continue
                
                # Scroll down
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1)
                scroll_count += 1
                
                # Click "Show more results" if present
                try:
                    show_more = driver.find_element(By.CSS_SELECTOR, '.mye4qd')
                    if show_more.is_displayed():
                        show_more.click()
                        time.sleep(2)
                except:
                    pass
            
            return image_urls[:max_images]
            
        except Exception as e:
            if callback:
                callback(f"⚠ Search error: {e}")
            return []
    
    def _search_pinterest(self, driver, query: str, max_images: int,
                          callback: Callable = None) -> List[str]:
        """Search Pinterest and extract image URLs"""
        try:
            search_url = f"https://www.pinterest.com/search/pins/?q={query}"
            driver.get(search_url)
            time.sleep(3)
            
            image_urls = []
            scroll_count = 0
            max_scrolls = max_images // 25 + 2
            
            while len(image_urls) < max_images and scroll_count < max_scrolls:
                # Find pin images
                pins = driver.find_elements(By.CSS_SELECTOR, 'img[src*="pinimg.com"]')
                
                for pin in pins:
                    if len(image_urls) >= max_images:
                        break
                    
                    src = pin.get_attribute('src')
                    if src and 'pinimg.com' in src:
                        # Try to get higher resolution
                        high_res = self._get_pinterest_high_res(src)
                        if high_res not in image_urls:
                            image_urls.append(high_res)
                            if callback:
                                callback(f"🔍 Found: {len(image_urls)}/{max_images}")
                
                # Scroll down
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                scroll_count += 1
            
            return image_urls[:max_images]
            
        except Exception as e:
            if callback:
                callback(f"⚠ Pinterest search error: {e}")
            return []
    
    def extract_images_from_page(self, url: str, min_size: int = 100,
                                 callback: Callable = None) -> List[str]:
        """
        Extract all image URLs from a webpage - fast HTTP-only approach
        
        Args:
            url: Page URL to extract images from
            min_size: Minimum image dimension to include
            callback: Progress callback
            
        Returns:
            List of image URLs
        """
        try:
            if callback:
                callback(f"🔍 Scanning page for images: {url[:50]}...")
            
            # Use fast HTTP requests only - avoid Selenium completely
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            image_urls = []
            
            if BS4_AVAILABLE:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Find all img tags
                for img in soup.find_all('img'):
                    src = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
                    if src:
                        # Make absolute URL
                        src = urljoin(url, src)
                        if src.startswith('http'):
                            image_urls.append(src)
                
                # Find background images in style attributes
                for elem in soup.find_all(style=True):
                    style = elem['style']
                    matches = re.findall(r'url\(["\']?([^"\')\s]+)["\']?\)', style)
                    for match in matches:
                        src = urljoin(url, match)
                        if src.startswith('http'):
                            image_urls.append(src)
                
                # Find og:image and other meta images
                for meta in soup.find_all('meta', property=re.compile(r'image')):
                    content = meta.get('content')
                    if content and content.startswith('http'):
                        image_urls.append(content)
            
            else:
                # Regex fallback when BeautifulSoup not available
                patterns = [
                    r'<img[^>]+src=["\']([^"\']+)["\']',
                    r'url\(["\']?([^"\')\s]+\.(?:jpg|jpeg|png|gif|webp))["\']?\)',
                ]
                for pattern in patterns:
                    matches = re.findall(pattern, response.text, re.IGNORECASE)
                    for match in matches:
                        src = urljoin(url, match)
                        if src.startswith('http'):
                            image_urls.append(src)
            
            # Remove duplicates while preserving order
            seen = set()
            unique_urls = []
            for img_url in image_urls:
                if img_url not in seen:
                    seen.add(img_url)
                    unique_urls.append(img_url)
            
            if callback:
                callback(f"📊 Found {len(unique_urls)} images on page")
            
            return unique_urls
            
        except Exception as e:
            if callback:
                callback(f"⚠ Error scanning page: {e}")
            return []



# Convenience function for quick downloads
def download_image(url: str, output_dir: str = "downloads/images") -> Dict:
    """Quick function to download a single image"""
    downloader = ImageDownloader(output_dir)
    try:
        return downloader.download_image(url)
    finally:
        downloader.close()


def batch_download_images(urls: List[str], output_dir: str = "downloads/images") -> Dict:
    """Quick function to download multiple images"""
    downloader = ImageDownloader(output_dir)
    try:
        return downloader.batch_download(urls)
    finally:
        downloader.close()
