#!/usr/bin/env python3
"""
Enhanced TikTok Profile Extraction with Multiple Fallback Methods
"""

import subprocess
import requests
import json
import re
import time
from pathlib import Path

class TikTokProfileExtractor:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
        })
    
    def extract_profile_with_yt_dlp(self, profile_url, max_videos=None):
        """Try extracting profile with yt-dlp using various options"""
        print("[Method 1/4] Trying yt-dlp with enhanced options...")
        
        try:
            # Build command with aggressive options
            cmd = [
                'yt-dlp',
                '--flat-playlist',
                '--dump-json',
                '--user-agent', 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15',
                '--referer', 'https://www.tiktok.com/',
                '--extractor-retries', '10',
                '--fragment-retries', '10',
                '--retry-sleep', '3',
                '--sleep-interval', '1',
                '--max-sleep-interval', '5',
            ]
            
            if max_videos:
                cmd.extend(['--playlist-end', str(max_videos)])
            
            cmd.append(profile_url)
            
            print(f"Running: {' '.join(cmd[:5])}... (truncated)")
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0 and result.stdout.strip():
                videos = []
                for line in result.stdout.strip().split('\n'):
                    try:
                        video_data = json.loads(line)
                        videos.append({
                            'url': video_data.get('webpage_url', video_data.get('url', '')),
                            'title': video_data.get('title', 'TikTok Video'),
                            'id': video_data.get('id', ''),
                            'duration': video_data.get('duration', 0),
                            'uploader': video_data.get('uploader', 'Unknown'),
                            'upload_date': video_data.get('upload_date', ''),
                            'view_count': video_data.get('view_count', 0),
                            'like_count': video_data.get('like_count', 0),
                            'comment_count': video_data.get('comment_count', 0),
                            'share_count': video_data.get('repost_count', video_data.get('share_count', 0)),
                            'uploader_verified': video_data.get('uploader_verified', False),
                            'trending': video_data.get('trending', False),
                            'platform': 'TikTok'
                        })
                    except json.JSONDecodeError:
                        continue
                
                if videos:
                    print(f"[OK] yt-dlp succeeded! Found {len(videos)} videos")
                    return {
                        'success': True,
                        'videos': videos,
                        'total_found': len(videos),
                        'profile_name': self.extract_username(profile_url),
                        'platform': 'TikTok'
                    }
            
            print(f"[X] yt-dlp failed: {result.stderr[:200]}")
            
        except subprocess.TimeoutExpired:
            print("[X] yt-dlp timed out")
        except Exception as e:
            print(f"[X] yt-dlp error: {e}")
        
        return None
    
    def extract_profile_with_gallery_dl(self, profile_url, max_videos=None):
        """Try extracting profile with gallery-dl"""
        print("[Method 2/4] Trying gallery-dl...")
        
        try:
            cmd = [
                'gallery-dl',
                '--dump-json',
                '--no-download',
            ]
            
            if max_videos:
                cmd.extend(['--range', f'1-{max_videos}'])
            
            cmd.append(profile_url)
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
            
            if result.returncode == 0 and result.stdout.strip():
                videos = []
                for line in result.stdout.strip().split('\n'):
                    try:
                        video_data = json.loads(line)
                        if 'url' in video_data or 'webpage_url' in video_data:
                            videos.append({
                                'url': video_data.get('webpage_url', video_data.get('url', '')),
                                'title': video_data.get('description', video_data.get('title', 'TikTok Video')),
                                'id': video_data.get('id', ''),
                                'duration': 0,  # gallery-dl might not provide duration
                                'uploader': video_data.get('author', {}).get('name', 'Unknown') if isinstance(video_data.get('author'), dict) else video_data.get('author', 'Unknown'),
                                'upload_date': video_data.get('date', ''),
                                'view_count': video_data.get('count', {}).get('play', 0) if isinstance(video_data.get('count'), dict) else 0,
                                'like_count': video_data.get('count', {}).get('digg', 0) if isinstance(video_data.get('count'), dict) else 0,
                                'comment_count': video_data.get('count', {}).get('comment', 0) if isinstance(video_data.get('count'), dict) else 0,
                                'share_count': video_data.get('count', {}).get('share', 0) if isinstance(video_data.get('count'), dict) else 0,
                                'uploader_verified': video_data.get('author', {}).get('verified', False) if isinstance(video_data.get('author'), dict) else False,
                                'trending': False,  # gallery-dl doesn't provide trending info
                                'platform': 'TikTok'
                            })
                    except json.JSONDecodeError:
                        continue
                
                if videos:
                    print(f"[OK] gallery-dl succeeded! Found {len(videos)} videos")
                    return {
                        'success': True,
                        'videos': videos,
                        'total_found': len(videos),
                        'profile_name': self.extract_username(profile_url),
                        'platform': 'TikTok'
                    }
            
            print(f"[X] gallery-dl failed: {result.stderr[:200]}")
            
        except subprocess.TimeoutExpired:
            print("[X] gallery-dl timed out")
        except Exception as e:
            print(f"[X] gallery-dl error: {e}")
        
        return None
    
    def extract_profile_web_scraping(self, profile_url, max_videos=None):
        """Try web scraping approach"""
        print("[Method 3/4] Trying web scraping...")
        
        try:
            # Add delay to avoid rate limiting
            time.sleep(2)
            
            response = self.session.get(profile_url, timeout=30)
            response.raise_for_status()
            
            # Look for JSON data in the page
            json_patterns = [
                r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__" type="application/json">(.*?)</script>',
                r'<script id="SIGI_STATE" type="application/json">(.*?)</script>',
                r'window\.__INITIAL_STATE__\s*=\s*({.*?});',
            ]
            
            for pattern in json_patterns:
                matches = re.findall(pattern, response.text, re.DOTALL)
                for match in matches:
                    try:
                        data = json.loads(match)
                        videos = self.parse_profile_data(data, max_videos)
                        if videos:
                            print(f"[OK] Web scraping succeeded! Found {len(videos)} videos")
                            return {
                                'success': True,
                                'videos': videos,
                                'total_found': len(videos),
                                'profile_name': self.extract_username(profile_url),
                                'platform': 'TikTok'
                            }
                    except json.JSONDecodeError:
                        continue
            
            print("[X] Web scraping failed - no valid JSON data found")
            
        except Exception as e:
            print(f"[X] Web scraping error: {e}")
        
        return None
    
    def extract_profile_api_approach(self, profile_url, max_videos=None):
        """Try API-based approach"""
        print("[Method 4/4] Trying API approach...")
        
        try:
            username = self.extract_username(profile_url)
            if not username:
                print("[X] Could not extract username")
                return None
            
            # Try different API endpoints (these may not work due to CORS/auth)
            api_endpoints = [
                f"https://www.tiktok.com/api/user/detail/?uniqueId={username}",
                f"https://m.tiktok.com/api/user/detail/?uniqueId={username}",
            ]
            
            for endpoint in api_endpoints:
                try:
                    response = self.session.get(endpoint, timeout=15)
                    if response.status_code == 200:
                        data = response.json()
                        videos = self.parse_api_data(data, max_videos)
                        if videos:
                            print(f"[OK] API approach succeeded! Found {len(videos)} videos")
                            return {
                                'success': True,
                                'videos': videos,
                                'total_found': len(videos),
                                'profile_name': username,
                                'platform': 'TikTok'
                            }
                except Exception as e:
                    print(f"[X] API endpoint {endpoint} failed: {e}")
                    continue
            
            print("[X] All API endpoints failed")
            
        except Exception as e:
            print(f"[X] API approach error: {e}")
        
        return None
    
    def parse_profile_data(self, data, max_videos=None):
        """Parse profile data from web scraping"""
        videos = []
        
        try:
            # Try different data structure paths
            possible_paths = [
                ['default', 'webapp.user-detail', 'itemList'],
                ['UserModule', 'users'],
                ['ItemModule'],
            ]
            
            for path in possible_paths:
                current = data
                try:
                    for key in path:
                        current = current[key]
                    
                    if isinstance(current, dict):
                        # Look for video items
                        for key, value in current.items():
                            if isinstance(value, list):
                                for item in value:
                                    if isinstance(item, dict) and ('video' in item or 'id' in item):
                                        video_info = self.extract_video_info(item)
                                        if video_info:
                                            videos.append(video_info)
                                            if max_videos and len(videos) >= max_videos:
                                                return videos
                    elif isinstance(current, list):
                        for item in current:
                            if isinstance(item, dict):
                                video_info = self.extract_video_info(item)
                                if video_info:
                                    videos.append(video_info)
                                    if max_videos and len(videos) >= max_videos:
                                        return videos
                except (KeyError, TypeError):
                    continue
            
        except Exception as e:
            print(f"Error parsing profile data: {e}")
        
        return videos
    
    def parse_api_data(self, data, max_videos=None):
        """Parse data from API response"""
        # This would need to be implemented based on actual API response structure
        return []
    
    def extract_video_info(self, item):
        """Extract video information from item"""
        try:
            video_id = item.get('id', '')
            if not video_id:
                return None
            
            return {
                'url': f"https://www.tiktok.com/@{item.get('author', {}).get('uniqueId', 'unknown')}/video/{video_id}",
                'title': item.get('desc', 'TikTok Video'),
                'id': video_id,
                'duration': item.get('video', {}).get('duration', 0),
                'uploader': item.get('author', {}).get('nickname', 'Unknown'),
                'upload_date': '',
                'view_count': item.get('stats', {}).get('playCount', 0),
                'like_count': item.get('stats', {}).get('diggCount', 0),
                'comment_count': item.get('stats', {}).get('commentCount', 0),
                'share_count': item.get('stats', {}).get('shareCount', 0),
                'uploader_verified': item.get('author', {}).get('verified', False),
                'trending': False,  # Would need additional logic to determine trending
                'platform': 'TikTok'
            }
        except Exception:
            return None
    
    def extract_username(self, profile_url):
        """Extract username from TikTok profile URL"""
        patterns = [
            r'tiktok\.com/@([^/?]+)',
            r'tiktok\.com/([^/@?]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, profile_url)
            if match:
                return match.group(1)
        
        return None
    
    def extract_profile(self, profile_url, max_videos=None):
        """Main method to extract profile using all available methods"""
        print(f"[DEBUG] Extracting TikTok profile: {profile_url}")
        print(f"Max videos: {max_videos if max_videos else 'No limit'}")
        print("=" * 60)
        
        methods = [
            self.extract_profile_with_yt_dlp,
            self.extract_profile_with_gallery_dl,
            self.extract_profile_web_scraping,
            self.extract_profile_api_approach,
        ]
        
        for i, method in enumerate(methods, 1):
            try:
                result = method(profile_url, max_videos)
                if result and result.get('success'):
                    print(f"[SUCCESS] Method {i} worked!")
                    return result
            except Exception as e:
                print(f"[X] Method {i} crashed: {e}")
            
            print()  # Add spacing between methods
        
        print("[X] All extraction methods failed")
        return {
            'success': False,
            'error': 'All TikTok extraction methods failed. TikTok may have updated their anti-bot measures.',
            'suggestions': [
                "1. Update yt-dlp: pip install --upgrade yt-dlp",
                "2. Try using TikTok cookies if you have an account",
                "3. Use alternative services like ssstik.io or snaptik.app",
                "4. Wait and try again later (TikTok blocks may be temporary)",
                "5. Use a VPN to change your location"
            ]
        }

def test_profile_extraction():
    """Test the profile extractor"""
    extractor = TikTokProfileExtractor()
    
    # Test with the problematic URL
    test_url = "https://www.tiktok.com/@bellapoarch"
    result = extractor.extract_profile(test_url, max_videos=5)
    
    if result.get('success'):
        print(f"\n[OK] Found {len(result['videos'])} videos")
        for i, video in enumerate(result['videos'][:3], 1):
            print(f"{i}. {video['title'][:50]}...")
    else:
        print(f"\n[X] Failed: {result.get('error', 'Unknown error')}")
        if 'suggestions' in result:
            print("\n[!] Suggestions:")
            for suggestion in result['suggestions']:
                print(f"   {suggestion}")

if __name__ == "__main__":
    test_profile_extraction()