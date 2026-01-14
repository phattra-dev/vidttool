"""
Facebook Video Extractor using Selenium
Uses browser automation to extract videos from Facebook profiles
SAFE MODE: No cookies, no account access - only public videos
"""

import re
import os
import time
import requests
from pathlib import Path

# Try to import Selenium
SELENIUM_AVAILABLE = False
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    SELENIUM_AVAILABLE = True
except ImportError:
    pass


class FacebookSeleniumExtractor:
    """Extract Facebook videos using Selenium browser automation - SAFE MODE (no cookies)"""
    
    def __init__(self, headless=True):
        self.driver = None
        self.headless = headless
        
    def _init_driver(self):
        """Initialize Chrome driver - anonymous browsing (safe, no account risk)"""
        if not SELENIUM_AVAILABLE:
            return False
            
        try:
            options = Options()
            
            # SAFE MODE: No cookies, no profile - completely anonymous
            # This means only public videos will be accessible
            
            if self.headless:
                options.add_argument('--headless=new')
            
            options.add_argument('--disable-gpu')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_experimental_option('excludeSwitches', ['enable-automation'])
            options.add_experimental_option('useAutomationExtension', False)
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            self.driver = webdriver.Chrome(options=options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            return True
        except Exception as e:
            print(f"Failed to init driver: {e}")
            return False
    
    def _close_driver(self):
        """Close the browser driver"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None
    
    def extract_videos_from_profile(self, profile_url, max_videos=50, callback=None):
        """
        Extract video URLs from Facebook profile using Selenium
        Tries multiple page types (reels, videos) to find more content
        """
        if not SELENIUM_AVAILABLE:
            return {
                'success': False,
                'videos': [],
                'total_found': 0,
                'error': 'Selenium not available'
            }
        
        try:
            if callback:
                callback("🌐 Starting browser...")
            
            if not self._init_driver():
                return {
                    'success': False,
                    'videos': [],
                    'total_found': 0,
                    'error': 'Could not initialize browser'
                }
            
            # Build list of pages to try
            pages_to_try = [profile_url]
            base_url = profile_url.rstrip('/')
            
            # Remove any existing section and add alternates
            for section in ['/reels', '/videos', '/posts']:
                base_url = base_url.replace(section, '')
            base_url = base_url.rstrip('/')
            
            # Add all video-related pages
            if '/reels' not in profile_url:
                pages_to_try.append(base_url + '/reels')
            if '/videos' not in profile_url:
                pages_to_try.append(base_url + '/videos')
            
            all_found_ids = set()
            
            for page_url in pages_to_try:
                if max_videos and len(all_found_ids) >= max_videos:
                    break
                
                page_type = 'reels' if '/reels' in page_url else 'videos' if '/videos' in page_url else 'main'
                if callback:
                    callback(f"📄 Checking {page_type} page...")
                
                try:
                    self.driver.get(page_url)
                    time.sleep(3)
                    
                    # Scroll and extract from this page
                    page_ids = self._scroll_and_extract(max_videos, len(all_found_ids), callback)
                    
                    new_count = len(page_ids - all_found_ids)
                    all_found_ids.update(page_ids)
                    
                    if callback and new_count > 0:
                        callback(f"📊 Found {new_count} new videos from {page_type} (total: {len(all_found_ids)})")
                        
                except Exception as e:
                    if callback:
                        callback(f"⚠ Error on {page_type}: {str(e)[:30]}")
                    continue
            
            self._close_driver()
            
            # Convert to video list
            videos = []
            for vid in all_found_ids:
                videos.append({
                    'url': f'https://www.facebook.com/watch/?v={vid}',
                    'id': vid,
                    'title': f'Facebook Video {vid}'
                })
            
            # Limit results
            if max_videos and len(videos) > max_videos:
                videos = videos[:max_videos]
            
            if callback:
                callback(f"✅ Total unique videos found: {len(videos)}")
            
            return {
                'success': len(videos) > 0,
                'videos': videos,
                'total_found': len(videos),
                'error': None if videos else 'No videos found. Profile may require login to see more content.'
            }
            
        except Exception as e:
            self._close_driver()
            return {
                'success': False,
                'videos': [],
                'total_found': 0,
                'error': str(e)
            }
    
    def _scroll_and_extract(self, max_videos, current_count, callback=None):
        """Scroll current page and extract video IDs - AGGRESSIVE scrolling"""
        found_ids = set()
        
        # AGGRESSIVE scroll parameters - scroll much more
        remaining = (max_videos - current_count) if max_videos else 1000
        if remaining > 100:
            max_scrolls = 150  # Very aggressive for large requests
        elif remaining > 50:
            max_scrolls = 80
        elif remaining > 25:
            max_scrolls = 50
        else:
            max_scrolls = 30
        
        scroll_count = 0
        last_count = 0
        no_new_count = 0
        
        while scroll_count < max_scrolls:
            # Get page source and extract video IDs
            html = self.driver.page_source
            new_ids = self._extract_video_ids(html)
            found_ids.update(new_ids)
            
            # Check if we have enough
            total = current_count + len(found_ids)
            if max_videos and total >= max_videos:
                break
            
            # Try clicking load more buttons frequently
            if scroll_count % 3 == 0:
                self._try_click_load_more()
            
            # Check for new videos - be more patient
            if len(found_ids) == last_count:
                no_new_count += 1
                # Be very patient - wait for up to 8 scrolls with no new content
                if no_new_count >= 8:
                    break
            else:
                no_new_count = 0
                last_count = len(found_ids)
            
            scroll_count += 1
            
            # Scroll down with different techniques
            if scroll_count % 4 == 0:
                # Scroll up a bit then down to trigger lazy loading
                self.driver.execute_script("window.scrollBy(0, -500);")
                time.sleep(0.3)
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            elif scroll_count % 2 == 0:
                # Scroll by viewport height
                self.driver.execute_script("window.scrollBy(0, window.innerHeight * 1.5);")
            else:
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            
            time.sleep(0.8)  # Faster scrolling
        
        return found_ids
    
    def _try_click_load_more(self):
        """Try to click any 'load more' buttons - more aggressive"""
        try:
            selectors = [
                "//div[contains(text(), 'See more')]",
                "//span[contains(text(), 'See more')]",
                "//div[@role='button'][contains(., 'more')]",
                "//a[contains(text(), 'See All')]",
                "//span[contains(text(), 'See All')]",
                "//div[contains(@class, 'load')]",
            ]
            for selector in selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for elem in elements[:3]:  # Click up to 3
                        try:
                            elem.click()
                            time.sleep(0.3)
                        except:
                            pass
                except:
                    pass
        except:
            pass
    
    def _extract_video_ids(self, html):
        """Extract video IDs from page HTML"""
        found_ids = set()
        
        patterns = [
            r'/watch/\?v=(\d{10,})',
            r'/reel/(\d{10,})',
            r'"video_id":"(\d{10,})"',
            r'"videoId":"(\d{10,})"',
            r'"id":"(\d{10,})","__typename":"Video"',
            r'"__typename":"Video"[^}]*"id":"(\d{10,})"',
            r'facebook\.com/[^/]+/videos/(\d{10,})',
            r'"playable_url[^"]*"[^}]*"video_id":"(\d{10,})"',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, html)
            for match in matches:
                if match and match.isdigit() and 10 <= len(match) <= 20:
                    found_ids.add(match)
        
        return found_ids
    
    def extract_video_url(self, video_page_url, callback=None):
        """Extract direct video URL from a Facebook video page"""
        if not SELENIUM_AVAILABLE:
            return {'success': False, 'video_url': None, 'quality': None, 'error': 'Selenium not available'}
        
        try:
            if not self._init_driver():
                return {'success': False, 'video_url': None, 'quality': None, 'error': 'Could not initialize browser'}
            
            self.driver.get(video_page_url)
            time.sleep(3)
            
            html = self.driver.page_source
            video_urls = []
            
            # HD patterns
            for pattern in [r'"hd_src":"([^"]+)"', r'"playable_url_quality_hd":"([^"]+)"']:
                for match in re.findall(pattern, html):
                    url = self._clean_url(match)
                    if url and self._is_valid_video_url(url):
                        video_urls.append(('hd', url))
            
            # SD patterns
            for pattern in [r'"sd_src":"([^"]+)"', r'"playable_url":"([^"]+)"']:
                for match in re.findall(pattern, html):
                    url = self._clean_url(match)
                    if url and self._is_valid_video_url(url):
                        video_urls.append(('sd', url))
            
            self._close_driver()
            
            if video_urls:
                hd = [u for q, u in video_urls if q == 'hd']
                sd = [u for q, u in video_urls if q == 'sd']
                best = hd[0] if hd else (sd[0] if sd else None)
                if best:
                    return {'success': True, 'video_url': best, 'quality': 'hd' if hd else 'sd', 'error': None}
            
            return {'success': False, 'video_url': None, 'quality': None, 'error': 'Could not find video URL'}
            
        except Exception as e:
            self._close_driver()
            return {'success': False, 'video_url': None, 'quality': None, 'error': str(e)}
    
    def _clean_url(self, url):
        if not url:
            return None
        url = url.replace('\\/', '/').replace('\\u0025', '%').replace('\\u003d', '=').replace('\\u0026', '&')
        try:
            url = url.encode().decode('unicode_escape')
        except:
            pass
        return url
    
    def _is_valid_video_url(self, url):
        if not url or not url.startswith('https://'):
            return False
        if not any(d in url.lower() for d in ['video', 'fbcdn', 'fbvideo', 'scontent']):
            return False
        return '.mp4' in url or 'bytestart' in url or 'efg=' in url


def download_video_direct(video_url, output_path, callback=None):
    """Download video from direct URL"""
    try:
        session = requests.Session()
        session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
        
        response = session.get(video_url, stream=True, timeout=120)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if callback and total_size > 0:
                        percent = int(downloaded * 100 / total_size)
                        if percent % 20 == 0:
                            callback(f"📥 Downloading: {percent}%")
        
        return {'success': True, 'file_path': output_path, 'error': None}
    except Exception as e:
        return {'success': False, 'file_path': None, 'error': str(e)}


def extract_facebook_videos_selenium(profile_url, max_videos=50, callback=None):
    """Extract videos from Facebook profile using Selenium"""
    if not SELENIUM_AVAILABLE:
        return {'success': False, 'videos': [], 'total_found': 0, 'error': 'Selenium not installed'}
    
    extractor = FacebookSeleniumExtractor(headless=True)
    return extractor.extract_videos_from_profile(profile_url, max_videos, callback)


def download_facebook_video_selenium(video_url, output_dir, callback=None):
    """Download a Facebook video using Selenium"""
    if not SELENIUM_AVAILABLE:
        return {'success': False, 'file_path': None, 'error': 'Selenium not installed'}
    
    extractor = FacebookSeleniumExtractor(headless=True)
    result = extractor.extract_video_url(video_url, callback)
    
    if not result['success']:
        return {'success': False, 'file_path': None, 'error': result['error']}
    
    video_id = re.search(r'v=(\d+)', video_url)
    video_id = video_id.group(1) if video_id else 'facebook_video'
    filename = f"Facebook_{video_id}_{result['quality']}.mp4"
    
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, filename)
    
    return download_video_direct(result['video_url'], output_path, callback)
