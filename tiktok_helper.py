#!/usr/bin/env python3
"""
TikTok-specific helper functions and alternative extraction methods
"""

import re
import requests
import json
from urllib.parse import urlparse, parse_qs

class TikTokHelper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
    
    def extract_video_id(self, url):
        """Extract TikTok video ID from URL"""
        patterns = [
            r'/video/(\d+)',
            r'tiktok\.com/.*?/video/(\d+)',
            r'vm\.tiktok\.com/([A-Za-z0-9]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    def get_video_info_alternative(self, url):
        """Alternative method to get TikTok video info"""
        video_id = self.extract_video_id(url)
        if not video_id:
            return None
        
        try:
            # Try to get video page
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            # Extract JSON data from page
            json_pattern = r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__" type="application/json">(.*?)</script>'
            match = re.search(json_pattern, response.text)
            
            if match:
                data = json.loads(match.group(1))
                # Navigate through the data structure to find video info
                # This structure may change, so we need to be flexible
                return self.parse_tiktok_data(data)
            
            return None
            
        except Exception as e:
            print(f"Alternative extraction failed: {e}")
            return None
    
    def parse_tiktok_data(self, data):
        """Parse TikTok data structure"""
        try:
            # TikTok's data structure can vary, try different paths
            possible_paths = [
                ['__DEFAULT_SCOPE__', 'webapp.video-detail', 'itemInfo', 'itemStruct'],
                ['default', 'ItemModule', 'video'],
                ['props', 'pageProps', 'itemInfo', 'itemStruct'],
            ]
            
            for path in possible_paths:
                current = data
                try:
                    for key in path:
                        current = current[key]
                    
                    if current and 'video' in current:
                        return {
                            'title': current.get('desc', 'TikTok Video'),
                            'uploader': current.get('author', {}).get('nickname', 'Unknown'),
                            'duration': current.get('video', {}).get('duration', 0),
                            'view_count': current.get('stats', {}).get('playCount', 0),
                            'video_url': current.get('video', {}).get('playAddr', ''),
                        }
                except (KeyError, TypeError):
                    continue
            
            return None
            
        except Exception as e:
            print(f"Error parsing TikTok data: {e}")
            return None
    
    def suggest_alternatives(self, url):
        """Suggest alternative methods for TikTok downloads"""
        suggestions = [
            "1. Update yt-dlp to the latest version:",
            "   pip install --upgrade yt-dlp",
            "",
            "2. Try using cookies (if you have a TikTok account):",
            "   - Export cookies from your browser",
            "   - Use --cookies option with yt-dlp",
            "",
            "3. Alternative TikTok downloaders:",
            "   - TikTok Downloader browser extensions",
            "   - Online TikTok download services",
            "   - Mobile apps for TikTok downloading",
            "",
            "4. Check video accessibility:",
            "   - Ensure the video is public",
            "   - Try accessing from different regions (VPN)",
            "   - Check if the video still exists",
            "",
            "5. Wait and retry:",
            "   - TikTok frequently updates their anti-bot measures",
            "   - Try again in a few hours or days",
        ]
        
        return "\n".join(suggestions)

def test_tiktok_helper():
    """Test function for TikTok helper"""
    helper = TikTokHelper()
    test_url = "https://www.tiktok.com/@turquoisehorizon5/video/7579597815886728478"
    
    print("Testing TikTok Helper...")
    video_id = helper.extract_video_id(test_url)
    print(f"Extracted video ID: {video_id}")
    
    info = helper.get_video_info_alternative(test_url)
    if info:
        print("Alternative extraction successful:")
        for key, value in info.items():
            print(f"  {key}: {value}")
    else:
        print("Alternative extraction failed")
        print("\nSuggestions:")
        print(helper.suggest_alternatives(test_url))

if __name__ == "__main__":
    test_tiktok_helper()