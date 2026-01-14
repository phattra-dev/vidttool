"""
Facebook Profile Video Extractor
Aggressive approach to extract video URLs from Facebook profiles/reels pages
Includes direct video download capability to bypass yt-dlp issues
Now with Selenium support for better extraction
"""

import re
import requests
from urllib.parse import urlparse, urljoin, parse_qs
import json
import time
import os

# Try to import Selenium-based extractor
SELENIUM_AVAILABLE = False
try:
    from facebook_selenium import (
        extract_facebook_videos_selenium,
        download_facebook_video_selenium,
        SELENIUM_AVAILABLE as SELENIUM_IMPORTED
    )
    SELENIUM_AVAILABLE = SELENIUM_IMPORTED
except ImportError:
    pass


class FacebookDirectDownloader:
    """Direct Facebook video downloader - bypasses yt-dlp for problematic videos"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
        # Note: Don't try to load browser cookies - causes issues when browser is open
        # Most public Facebook videos work without authentication
    
    def extract_video_url(self, video_page_url, callback=None):
        """
        Extract direct video URL from a Facebook video page
        Returns dict with 'success', 'video_url', 'quality', 'error'
        """
        try:
            if callback:
                callback(f"🔍 Fetching video page...")
            
            # Try multiple methods to get the video URL
            video_urls = []
            
            # Method 1: Try the watch page directly
            response = self.session.get(video_page_url, timeout=30)
            html = response.text
            
            # Look for HD video URL - many patterns
            hd_patterns = [
                r'"hd_src":"([^"]+)"',
                r'"hd_src_no_ratelimit":"([^"]+)"',
                r'hd_src\\?":\\?"([^"\\]+)',
                r'"playable_url_quality_hd":"([^"]+)"',
                r'"browser_native_hd_url":"([^"]+)"',
                r'"playable_url":"([^"]+)".*?"quality":"hd"',
                r'"progressive_url":"([^"]+)".*?"quality":"HD"',
                r'"hd":"([^"]+)"',
                r'FBQualityLabel=\\?"hd\\?"[^}]*url\\?":\\?"([^"\\]+)',
            ]
            
            for pattern in hd_patterns:
                matches = re.findall(pattern, html)
                for match in matches:
                    url = self._clean_url(match)
                    if url and self._is_valid_video_url(url):
                        video_urls.append(('hd', url))
            
            # Look for SD video URL
            sd_patterns = [
                r'"sd_src":"([^"]+)"',
                r'"sd_src_no_ratelimit":"([^"]+)"',
                r'sd_src\\?":\\?"([^"\\]+)',
                r'"playable_url":"([^"]+)"',
                r'"browser_native_sd_url":"([^"]+)"',
                r'"progressive_url":"([^"]+)"',
                r'"sd":"([^"]+)"',
                r'FBQualityLabel=\\?"sd\\?"[^}]*url\\?":\\?"([^"\\]+)',
            ]
            
            for pattern in sd_patterns:
                matches = re.findall(pattern, html)
                for match in matches:
                    url = self._clean_url(match)
                    if url and self._is_valid_video_url(url):
                        video_urls.append(('sd', url))
            
            # Method 2: Look for video URLs in script tags
            script_patterns = [
                r'<script[^>]*>.*?"playable_url":"([^"]+)".*?</script>',
                r'"video_url":"([^"]+)"',
                r'"src":"(https://[^"]*video[^"]*\.mp4[^"]*)"',
                r'"src":"(https://[^"]*scontent[^"]*)"',
            ]
            
            for pattern in script_patterns:
                matches = re.findall(pattern, html, re.DOTALL)
                for match in matches:
                    url = self._clean_url(match)
                    if url and self._is_valid_video_url(url):
                        video_urls.append(('unknown', url))
            
            # Method 3: Try mobile version (often has simpler structure)
            if not video_urls:
                mobile_url = video_page_url.replace('www.facebook.com', 'm.facebook.com')
                try:
                    mobile_headers = {
                        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15'
                    }
                    mobile_response = self.session.get(mobile_url, headers=mobile_headers, timeout=30)
                    mobile_html = mobile_response.text
                    
                    # Mobile patterns
                    mobile_patterns = [
                        r'data-store="[^"]*?src[^"]*?:.*?(https[^"\\]+\.mp4[^"\\]*)',
                        r'"src":"(https[^"]+\.mp4[^"]*)"',
                        r'<source[^>]+src="([^"]+)"',
                        r'href="(https://[^"]*video[^"]*)"',
                    ]
                    
                    for pattern in mobile_patterns:
                        matches = re.findall(pattern, mobile_html)
                        for match in matches:
                            url = self._clean_url(match)
                            if url and self._is_valid_video_url(url):
                                video_urls.append(('sd', url))
                except:
                    pass
            
            # Method 4: Try basic mobile version
            if not video_urls:
                basic_url = video_page_url.replace('www.facebook.com', 'mbasic.facebook.com')
                try:
                    basic_response = self.session.get(basic_url, timeout=30)
                    basic_html = basic_response.text
                    
                    # Look for video links
                    basic_patterns = [
                        r'href="([^"]*video_redirect[^"]*)"',
                        r'href="(https://[^"]*\.mp4[^"]*)"',
                    ]
                    
                    for pattern in basic_patterns:
                        matches = re.findall(pattern, basic_html)
                        for match in matches:
                            url = self._clean_url(match)
                            if url:
                                # Follow redirect if needed
                                if 'video_redirect' in url:
                                    try:
                                        redirect_resp = self.session.head(url, allow_redirects=True, timeout=10)
                                        url = redirect_resp.url
                                    except:
                                        pass
                                if self._is_valid_video_url(url):
                                    video_urls.append(('sd', url))
                except:
                    pass
            
            if video_urls:
                # Prefer HD, then SD
                hd_urls = [u for q, u in video_urls if q == 'hd']
                sd_urls = [u for q, u in video_urls if q == 'sd']
                other_urls = [u for q, u in video_urls if q not in ('hd', 'sd')]
                
                best_url = (hd_urls[0] if hd_urls else 
                           sd_urls[0] if sd_urls else 
                           other_urls[0] if other_urls else None)
                
                if best_url:
                    quality = 'hd' if hd_urls else 'sd'
                    return {
                        'success': True,
                        'video_url': best_url,
                        'quality': quality,
                        'error': None
                    }
            
            return {
                'success': False,
                'video_url': None,
                'quality': None,
                'error': 'Could not find video URL - video may require Facebook login'
            }
            
        except Exception as e:
            return {
                'success': False,
                'video_url': None,
                'quality': None,
                'error': str(e)
            }
    
    def _clean_url(self, url):
        """Clean and decode URL"""
        if not url:
            return None
        # Decode unicode escapes
        url = url.replace('\\/', '/')
        url = url.replace('\\u0025', '%')
        url = url.replace('\\u003d', '=')
        url = url.replace('\\u0026', '&')
        # Decode other escapes
        try:
            url = url.encode().decode('unicode_escape')
        except:
            pass
        return url
    
    def _is_valid_video_url(self, url):
        """Check if URL looks like a valid video URL"""
        if not url:
            return False
        # Must be HTTPS
        if not url.startswith('https://'):
            return False
        # Should contain video-related domains
        video_domains = ['video', 'fbcdn', 'fbvideo', 'scontent']
        if not any(d in url.lower() for d in video_domains):
            return False
        # Should have video extension or be a streaming URL
        if '.mp4' in url or 'bytestart' in url or 'efg=' in url:
            return True
        return False
    
    def download_video(self, video_url, output_path, callback=None):
        """Download video from direct URL"""
        try:
            if callback:
                callback(f"📥 Downloading video...")
            
            response = self.session.get(video_url, stream=True, timeout=60)
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
                            callback(f"📥 Downloading: {percent}%")
            
            if callback:
                callback(f"✅ Download complete: {output_path}")
            
            return {'success': True, 'file_path': output_path, 'error': None}
            
        except Exception as e:
            return {'success': False, 'file_path': None, 'error': str(e)}


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
        # Track IDs that are confirmed as videos vs other content types
        self.confirmed_video_ids = set()
        self.rejected_ids = set()
        # Direct downloader for validation
        self.direct_downloader = FacebookDirectDownloader()
    
    def _quick_validate_video(self, video_id):
        """Quick check if video ID has downloadable content"""
        try:
            url = f'https://www.facebook.com/watch/?v={video_id}'
            result = self.direct_downloader.extract_video_url(url)
            return result['success']
        except:
            return False
    
    def _is_likely_video_id(self, video_id, html_context=""):
        """Check if an ID is likely a video ID based on context"""
        # Skip IDs we've already rejected
        if video_id in self.rejected_ids:
            return False
        
        # Already confirmed
        if video_id in self.confirmed_video_ids:
            return True
        
        # Facebook video IDs are typically 15-19 digits
        if len(video_id) < 10 or len(video_id) > 20:
            self.rejected_ids.add(video_id)
            return False
        
        # Check if this ID appears in a video-specific context in the HTML
        video_contexts = [
            f'watch/?v={video_id}',
            f'watch?v={video_id}',
            f'/videos/{video_id}',
            f'/reel/{video_id}',
            f'/reels/{video_id}',
            f'"video_id":"{video_id}"',
            f'"videoId":"{video_id}"',
            f'"__typename":"Video".*?"{video_id}"',
        ]
        
        for ctx in video_contexts:
            if ctx in html_context:
                self.confirmed_video_ids.add(video_id)
                return True
        
        # If we found it but can't confirm context, still include it
        # (will be filtered by download failures)
        return True
    
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
            
            # Method 5: Try reels page if not already checked
            if len(found_ids) < max_videos and '/reels' not in profile_url:
                if callback:
                    callback(f"🎬 Checking reels page...")
                base_url = profile_url.rstrip('/')
                reels_url = base_url + '/reels'
                videos, ids = self._scrape_page_for_videos(reels_url, callback)
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
        priority_ids = set()  # IDs found in clear video contexts
        
        try:
            response = self.session.get(url, timeout=30)
            html = response.text
            
            # HIGH PRIORITY: Patterns that clearly indicate video content
            priority_patterns = [
                # Facebook video watch URLs - most reliable
                r'facebook\.com/watch/\?v=(\d{10,})',
                r'facebook\.com/watch\?v=(\d{10,})',
                r'/watch/\?v=(\d{10,})',
                r'watch\?v=(\d{10,})',
                # Reel URLs - very reliable
                r'facebook\.com/reel/(\d{10,})',
                r'facebook\.com/reels/(\d{10,})',
                r'/reel/(\d{10,})',
                # Video URLs with username
                r'facebook\.com/[^/]+/videos/(\d{10,})',
                # Video ID in JSON with Video typename
                r'"id":"(\d{10,})","__typename":"Video"',
                r'"__typename":"Video"[^}]*"id":"(\d{10,})"',
                r'"__typename":"ShortsVideo"[^}]*"id":"(\d{10,})"',
                # Playable video patterns
                r'"playable_url[^"]*"[^}]*"video_id":"(\d{10,})"',
                r'"video_id":"(\d{10,})"[^}]*"playable_url',
            ]
            
            # MEDIUM PRIORITY: Patterns that might be videos
            medium_patterns = [
                r'"video_id":"(\d{10,})"',
                r'"videoId":"(\d{10,})"',
                r'"videoID":"(\d{10,})"',
                r'data-video-id="(\d{10,})"',
                r'"attachedVideo"[^}]*"id":"(\d{10,})"',
                r'"creation_story"[^}]*"id":"(\d{10,})"',
                r'"short_form_video_context"[^}]*"id":"(\d{10,})"',
            ]
            
            # LOW PRIORITY: Generic patterns (might catch non-video IDs)
            low_patterns = [
                r'/videos/(\d{10,})',
                r'video_id=(\d{10,})',
                r'"media"[^}]*"id":"(\d{10,})"',
            ]
            
            # Extract priority IDs first
            for pattern in priority_patterns:
                matches = re.findall(pattern, html)
                for match in matches:
                    if match and match.isdigit() and len(match) >= 10:
                        priority_ids.add(match)
                        found_ids.add(match)
            
            # Then medium priority
            for pattern in medium_patterns:
                matches = re.findall(pattern, html)
                for match in matches:
                    if match and match.isdigit() and len(match) >= 10:
                        found_ids.add(match)
            
            # Always use low priority patterns too - we need more videos
            for pattern in low_patterns:
                matches = re.findall(pattern, html)
                for match in matches:
                    if match and match.isdigit() and len(match) >= 10:
                        # Validate against context
                        if self._is_likely_video_id(match, html):
                                found_ids.add(match)
            
            # Convert IDs to URLs - prioritize confirmed video IDs first
            sorted_ids = list(priority_ids) + [id for id in found_ids if id not in priority_ids]
            
            for video_id in sorted_ids:
                video_url = f'https://www.facebook.com/watch/?v={video_id}'
                videos.append({
                    'url': video_url,
                    'id': video_id,
                    'title': f'Facebook Video {video_id}',
                    'priority': 'high' if video_id in priority_ids else 'normal'
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
            
            # Look for video links in mobile HTML - prioritize clear video patterns
            patterns = [
                r'href="[^"]*?/watch/\?v=(\d{10,})"',
                r'href="[^"]*?/video\.php\?v=(\d{10,})"',
                r'href="[^"]*?/reel/(\d{10,})"',
                r'data-video-id="(\d{10,})"',
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
            
            # Look for video IDs specifically associated with Video typename
            video_type_pattern = r'"id":"(\d{10,})"[^}]*"__typename":"Video"'
            matches = re.findall(video_type_pattern, html)
            found_ids.update(matches)
            
            # Also try reverse order
            video_type_pattern2 = r'"__typename":"Video"[^}]*"id":"(\d{10,})"'
            matches = re.findall(video_type_pattern2, html)
            found_ids.update(matches)
            
            # Look for video_id fields specifically
            video_id_pattern = r'"video_id":"(\d{10,})"'
            matches = re.findall(video_id_pattern, html)
            found_ids.update(matches)
            
            # Look for URLs with video IDs
            url_ids = re.findall(r'/watch/?\?v=(\d{10,})', html)
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
    Uses Selenium if available for better extraction, falls back to requests
    """
    # Try Selenium first (better for logged-in sessions)
    if SELENIUM_AVAILABLE:
        if callback:
            callback("🚀 Using Selenium browser for better extraction...")
        try:
            result = extract_facebook_videos_selenium(profile_url, max_videos, callback)
            if result['success'] and result['total_found'] > 0:
                return result
            if callback:
                callback("⚠ Selenium extraction found no videos, trying fallback...")
        except Exception as e:
            if callback:
                callback(f"⚠ Selenium failed: {str(e)[:50]}, trying fallback...")
    
    # Fallback to requests-based extraction
    if callback:
        callback("📡 Using requests-based extraction...")
    extractor = FacebookExtractor()
    return extractor.extract_videos_from_profile(profile_url, max_videos, callback)


def try_direct_facebook_download(video_url, output_dir, filename=None, callback=None):
    """
    Try to download a Facebook video directly (bypassing yt-dlp)
    Uses Selenium if available for better success rate
    
    Returns: dict with 'success', 'file_path', 'error'
    """
    # Try Selenium first
    if SELENIUM_AVAILABLE:
        if callback:
            callback("🌐 Trying Selenium browser download...")
        try:
            result = download_facebook_video_selenium(video_url, output_dir, callback)
            if result['success']:
                return result
            if callback:
                callback("⚠ Selenium download failed, trying direct method...")
        except Exception as e:
            if callback:
                callback(f"⚠ Selenium error: {str(e)[:30]}")
    
    # Fallback to direct download
    downloader = FacebookDirectDownloader()
    
    # Extract direct video URL
    result = downloader.extract_video_url(video_url, callback)
    
    if not result['success']:
        return {
            'success': False,
            'file_path': None,
            'error': result['error']
        }
    
    # Generate filename if not provided
    if not filename:
        # Extract video ID from URL
        video_id_match = re.search(r'v=(\d+)', video_url)
        video_id = video_id_match.group(1) if video_id_match else 'facebook_video'
        filename = f"Facebook_{video_id}_{result['quality']}.mp4"
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, filename)
    
    # Download the video
    return downloader.download_video(result['video_url'], output_path, callback)


if __name__ == "__main__":
    # Test
    test_url = "https://www.facebook.com/leakenainoffice/reels/"
    result = get_facebook_profile_videos(test_url, max_videos=100, callback=print)
    print(f"\nTotal videos found: {result['total_found']}")
    if result['videos']:
        print("First 5 videos:")
        for v in result['videos'][:5]:
            print(f"  - {v['url']}")
