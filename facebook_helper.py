"""
Facebook Profile Video Extractor
Aggressive approach to extract video URLs from Facebook profiles/reels pages
"""

import re
import requests
from urllib.parse import urlparse, urljoin
import json
import time


class FacebookExtractor:
    """Extract video URLs from Facebook profile pages"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        })
    
    def extract_videos_from_profile(self, profile_url, max_videos=50, callback=None):
        """
        Extract video URLs from a Facebook profile/reels page
        Returns list of video URLs that can be downloaded with yt-dlp
        """
        videos = []
        
        try:
            if callback:
                callback(f"🔍 Fetching Facebook page: {profile_url}")
            
            # Try multiple methods
            
            # Method 1: Direct page scraping
            videos = self._scrape_page_for_videos(profile_url, callback)
            
            if not videos:
                # Method 2: Try mobile version
                mobile_url = profile_url.replace('www.facebook.com', 'm.facebook.com')
                videos = self._scrape_mobile_page(mobile_url, callback)
            
            if not videos:
                # Method 3: Try to find video IDs in page source
                videos = self._extract_video_ids_from_source(profile_url, callback)
            
            # Limit results
            if max_videos and len(videos) > max_videos:
                videos = videos[:max_videos]
            
            return {
                'success': len(videos) > 0,
                'videos': videos,
                'total_found': len(videos),
                'error': None if videos else 'Could not find any videos on this page'
            }
            
        except Exception as e:
            return {
                'success': False,
                'videos': [],
                'total_found': 0,
                'error': str(e)
            }
    
    def _scrape_page_for_videos(self, url, callback=None):
        """Scrape page HTML for video URLs"""
        videos = []
        
        try:
            if callback:
                callback("📄 Scanning page for video links...")
            
            response = self.session.get(url, timeout=30)
            html = response.text
            
            # Pattern 1: Look for video URLs in various formats
            patterns = [
                # Facebook video watch URLs
                r'facebook\.com/watch/\?v=(\d+)',
                r'facebook\.com/watch\?v=(\d+)',
                r'fb\.watch/([a-zA-Z0-9_-]+)',
                # Reel URLs
                r'facebook\.com/reel/(\d+)',
                r'facebook\.com/reels/(\d+)',
                # Video URLs
                r'facebook\.com/[^/]+/videos/(\d+)',
                r'/videos/(\d+)',
                # Video IDs in JSON data
                r'"video_id":"(\d+)"',
                r'"videoId":"(\d+)"',
                r'"id":"(\d+)","__typename":"Video"',
                r'video_id=(\d+)',
            ]
            
            found_ids = set()
            for pattern in patterns:
                matches = re.findall(pattern, html)
                for match in matches:
                    if match and len(match) > 5:  # Valid video ID
                        found_ids.add(match)
            
            if callback:
                callback(f"📹 Found {len(found_ids)} potential video IDs")
            
            # Convert IDs to URLs
            for video_id in found_ids:
                if video_id.isdigit():
                    video_url = f'https://www.facebook.com/watch/?v={video_id}'
                else:
                    video_url = f'https://fb.watch/{video_id}'
                
                videos.append({
                    'url': video_url,
                    'id': video_id,
                    'title': f'Facebook Video {video_id}'
                })
            
        except Exception as e:
            if callback:
                callback(f"⚠️ Error scraping page: {str(e)}")
        
        return videos
    
    def _scrape_mobile_page(self, url, callback=None):
        """Try mobile version which sometimes has simpler HTML"""
        videos = []
        
        try:
            if callback:
                callback("📱 Trying mobile version...")
            
            # Mobile headers
            mobile_headers = {
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
            }
            
            response = self.session.get(url, headers=mobile_headers, timeout=30)
            html = response.text
            
            # Look for video links in mobile HTML
            patterns = [
                r'href="(/watch/\?v=\d+)"',
                r'href="(/video\.php\?v=\d+)"',
                r'href="(/reel/\d+)"',
                r'data-video-id="(\d+)"',
            ]
            
            found_ids = set()
            for pattern in patterns:
                matches = re.findall(pattern, html)
                for match in matches:
                    # Extract video ID
                    id_match = re.search(r'(\d{10,})', match)
                    if id_match:
                        found_ids.add(id_match.group(1))
            
            for video_id in found_ids:
                videos.append({
                    'url': f'https://www.facebook.com/watch/?v={video_id}',
                    'id': video_id,
                    'title': f'Facebook Video {video_id}'
                })
                
        except Exception as e:
            if callback:
                callback(f"⚠️ Mobile scrape error: {str(e)}")
        
        return videos
    
    def _extract_video_ids_from_source(self, url, callback=None):
        """Extract video IDs from page source/scripts"""
        videos = []
        
        try:
            if callback:
                callback("🔎 Deep scanning page source...")
            
            response = self.session.get(url, timeout=30)
            html = response.text
            
            # Look for video data in script tags
            script_patterns = [
                r'"video_id"\s*:\s*"(\d+)"',
                r'"videoID"\s*:\s*"(\d+)"',
                r'"playable_url"\s*:\s*"([^"]+)"',
                r'"playable_url_quality_hd"\s*:\s*"([^"]+)"',
                r'video_ids\s*:\s*\[([^\]]+)\]',
            ]
            
            found_ids = set()
            for pattern in script_patterns:
                matches = re.findall(pattern, html)
                for match in matches:
                    if match.isdigit() and len(match) > 10:
                        found_ids.add(match)
            
            # Also look for encoded video URLs
            encoded_patterns = [
                r'\\u0025\\u0032\\u0046watch\\u0025\\u0032\\u0046\\u0025\\u0033\\u0046v\\u0025\\u0033\\u0044(\d+)',
            ]
            
            for pattern in encoded_patterns:
                matches = re.findall(pattern, html)
                found_ids.update(matches)
            
            for video_id in found_ids:
                videos.append({
                    'url': f'https://www.facebook.com/watch/?v={video_id}',
                    'id': video_id,
                    'title': f'Facebook Video {video_id}'
                })
                
        except Exception as e:
            if callback:
                callback(f"⚠️ Source scan error: {str(e)}")
        
        return videos


def get_facebook_profile_videos(profile_url, max_videos=50, callback=None):
    """
    Main function to extract videos from Facebook profile
    """
    extractor = FacebookExtractor()
    return extractor.extract_videos_from_profile(profile_url, max_videos, callback)


if __name__ == "__main__":
    # Test
    test_url = "https://www.facebook.com/leakenainoffice/reels/"
    result = get_facebook_profile_videos(test_url, callback=print)
    print(f"\nResult: {result}")
