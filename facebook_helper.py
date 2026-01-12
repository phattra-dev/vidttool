"""
Facebook Profile Video Extractor
Aggressive approach to extract video URLs from Facebook profiles/reels pages
"""

import re
import requests
from urllib.parse import urlparse, urljoin, parse_qs
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
        all_videos = []
        found_ids = set()
        
        try:
            if callback:
                callback(f"🔍 Fetching Facebook page: {profile_url}")
            
            # Method 1: Direct page scraping (multiple pages if possible)
            videos, ids = self._scrape_page_for_videos(profile_url, callback)
            all_videos.extend(videos)
            found_ids.update(ids)
            
            if callback:
                callback(f"📹 Found {len(found_ids)} videos from main page")
            
            # Method 2: Try videos tab URL
            if '/reels' in profile_url:
                videos_url = profile_url.replace('/reels', '/videos')
            elif '/videos' not in profile_url:
                # Try to construct videos URL
                base_url = profile_url.rstrip('/')
                if not base_url.endswith('/videos'):
                    videos_url = base_url + '/videos'
                else:
                    videos_url = None
            else:
                videos_url = None
            
            if videos_url and videos_url != profile_url:
                if callback:
                    callback(f"📂 Also checking videos tab...")
                videos, ids = self._scrape_page_for_videos(videos_url, callback)
                for v in videos:
                    if v['id'] not in found_ids:
                        all_videos.append(v)
                        found_ids.add(v['id'])
            
            # Method 3: Try mobile version for more videos
            if len(found_ids) < max_videos:
                if callback:
                    callback(f"📱 Trying mobile version for more videos...")
                mobile_url = profile_url.replace('www.facebook.com', 'm.facebook.com')
                videos, ids = self._scrape_mobile_page(mobile_url, callback)
                for v in videos:
                    if v['id'] not in found_ids:
                        all_videos.append(v)
                        found_ids.add(v['id'])
            
            # Method 4: Try to find GraphQL/API data
            if len(found_ids) < max_videos:
                if callback:
                    callback(f"🔎 Deep scanning for more videos...")
                videos, ids = self._extract_from_graphql(profile_url, callback)
                for v in videos:
                    if v['id'] not in found_ids:
                        all_videos.append(v)
                        found_ids.add(v['id'])
            
            # Limit results
            if max_videos and len(all_videos) > max_videos:
                all_videos = all_videos[:max_videos]
            
            if callback:
                callback(f"✅ Total unique videos found: {len(all_videos)}")
            
            return {
                'success': len(all_videos) > 0,
                'videos': all_videos,
                'total_found': len(all_videos),
                'error': None if all_videos else 'Could not find any videos on this page. Facebook may require login for this profile.'
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
        found_ids = set()
        
        try:
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
                r'"videoID":"(\d+)"',
                # More patterns
                r'content_id=(\d{10,})',
                r'"attachmentID":"(\d{10,})"',
                r'"story_bucket_id":"(\d{10,})"',
                r'"post_id":"(\d{10,})"',
                r'data-video-id="(\d+)"',
                r'"creation_story":{"id":"(\d+)"',
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, html)
                for match in matches:
                    if match and len(match) >= 10:  # Valid video ID (at least 10 digits)
                        if match.isdigit():
                            found_ids.add(match)
            
            # Convert IDs to URLs
            for video_id in found_ids:
                video_url = f'https://www.facebook.com/watch/?v={video_id}'
                videos.append({
                    'url': video_url,
                    'id': video_id,
                    'title': f'Facebook Video {video_id}'
                })
            
        except Exception as e:
            if callback:
                callback(f"⚠️ Error scraping page: {str(e)[:50]}")
        
        return videos, found_ids
    
    def _scrape_mobile_page(self, url, callback=None):
        """Try mobile version which sometimes has simpler HTML"""
        videos = []
        found_ids = set()
        
        try:
            # Mobile headers
            mobile_headers = {
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
            }
            
            response = self.session.get(url, headers=mobile_headers, timeout=30)
            html = response.text
            
            # Look for video links in mobile HTML
            patterns = [
                r'href="[^"]*?/watch/\?v=(\d+)"',
                r'href="[^"]*?/video\.php\?v=(\d+)"',
                r'href="[^"]*?/reel/(\d+)"',
                r'data-video-id="(\d+)"',
                r'/story\.php\?story_fbid=(\d+)',
                r'video_id=(\d+)',
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, html)
                for match in matches:
                    if match and len(match) >= 10 and match.isdigit():
                        found_ids.add(match)
            
            for video_id in found_ids:
                videos.append({
                    'url': f'https://www.facebook.com/watch/?v={video_id}',
                    'id': video_id,
                    'title': f'Facebook Video {video_id}'
                })
                
        except Exception as e:
            if callback:
                callback(f"⚠️ Mobile scrape error: {str(e)[:50]}")
        
        return videos, found_ids
    
    def _extract_from_graphql(self, url, callback=None):
        """Extract video IDs from GraphQL/JSON data in page"""
        videos = []
        found_ids = set()
        
        try:
            response = self.session.get(url, timeout=30)
            html = response.text
            
            # Look for JSON data blocks
            json_patterns = [
                r'data-sjs>(\{.*?\})</script>',
                r'type="application/json">(\{.*?\})</script>',
                r'__bbox":(\{.*?\}),"',
            ]
            
            # Also look for specific video-related JSON structures
            video_json_patterns = [
                r'"edges":\s*\[(.*?)\]',
                r'"nodes":\s*\[(.*?)\]',
                r'"videos":\s*\[(.*?)\]',
            ]
            
            # Extract all potential video IDs from the entire page
            all_ids = re.findall(r'"(?:video_id|videoId|id)"\s*:\s*"(\d{10,})"', html)
            found_ids.update(all_ids)
            
            # Also look for URLs with video IDs
            url_ids = re.findall(r'/(?:watch|video|reel)[^"]*?[?&]v=(\d{10,})', html)
            found_ids.update(url_ids)
            
            for video_id in found_ids:
                videos.append({
                    'url': f'https://www.facebook.com/watch/?v={video_id}',
                    'id': video_id,
                    'title': f'Facebook Video {video_id}'
                })
                
        except Exception as e:
            if callback:
                callback(f"⚠️ GraphQL scan error: {str(e)[:50]}")
        
        return videos, found_ids


def get_facebook_profile_videos(profile_url, max_videos=50, callback=None):
    """
    Main function to extract videos from Facebook profile
    """
    extractor = FacebookExtractor()
    return extractor.extract_videos_from_profile(profile_url, max_videos, callback)


if __name__ == "__main__":
    # Test
    test_url = "https://www.facebook.com/leakenainoffice/reels/"
    result = get_facebook_profile_videos(test_url, max_videos=100, callback=print)
    print(f"\nTotal videos found: {result['total_found']}")
    if result['videos']:
        print("First 5 videos:")
        for v in result['videos'][:5]:
            print(f"  - {v['url']}")
