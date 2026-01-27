#!/usr/bin/env python3
"""
Multi-Platform Video Downloader Tool
Supports: YouTube, TikTok, Facebook, Instagram, Twitter, and more
"""

import os
import sys
import json
import argparse
from pathlib import Path
from urllib.parse import urlparse
import yt_dlp
from colorama import init, Fore, Style
from tqdm import tqdm

try:
    from tiktok_helper import TikTokHelper
except ImportError:
    TikTokHelper = None

# Initialize colorama for cross-platform colored output
init(autoreset=True)

class VideoDownloader:
    def __init__(self, output_dir="downloads"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Initialize TikTok helper if available
        self.tiktok_helper = TikTokHelper() if TikTokHelper else None
        
        # Supported platforms
        self.supported_platforms = {
            'youtube.com': 'YouTube',
            'youtu.be': 'YouTube',
            'tiktok.com': 'TikTok',
            'facebook.com': 'Facebook',
            'fb.watch': 'Facebook',
            'instagram.com': 'Instagram',
            'twitter.com': 'Twitter',
            'x.com': 'Twitter',
            'vimeo.com': 'Vimeo',
            'dailymotion.com': 'Dailymotion',
            'twitch.tv': 'Twitch'
        }
    
    def detect_platform(self, url):
        """Detect the platform from URL"""
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower()
        
        # Remove www. prefix
        if domain.startswith('www.'):
            domain = domain[4:]
        
        for platform_domain, platform_name in self.supported_platforms.items():
            if platform_domain in domain:
                return platform_name
        
        return "Unknown"
    
    def get_video_info(self, url):
        """Get video information without downloading"""
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
        }
        
        # TikTok-specific handling with fallback methods
        if 'tiktok.com' in url.lower():
            print(f"[*] TikTok detected - trying multiple methods...")
            
            # Method 1: Try standard extraction
            try:
                print(f"[1/3] Trying standard extraction...")
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    if info:
                        print(f"[OK] Standard extraction successful")
                        return {
                            'title': info.get('title', 'Unknown'),
                            'uploader': info.get('uploader', 'Unknown'),
                            'duration': info.get('duration', 0),
                            'view_count': info.get('view_count', 0),
                            'upload_date': info.get('upload_date', 'Unknown'),
                            'formats': len(info.get('formats', [])),
                            'platform': self.detect_platform(url)
                        }
            except Exception as e:
                print(f"[!] Standard method failed: {str(e)[:100]}...")
            
            # Method 2: Try with cookies if available
            cookies_file = Path("cookies/tiktok_cookies.txt")
            if cookies_file.exists() and cookies_file.stat().st_size > 500:  # Check if cookies file has content
                try:
                    print(f"[2/3] Trying with cookies...")
                    ydl_opts_cookies = ydl_opts.copy()
                    ydl_opts_cookies['cookiefile'] = str(cookies_file)
                    
                    with yt_dlp.YoutubeDL(ydl_opts_cookies) as ydl:
                        info = ydl.extract_info(url, download=False)
                        if info:
                            print(f"[OK] Cookie extraction successful")
                            return {
                                'title': info.get('title', 'Unknown'),
                                'uploader': info.get('uploader', 'Unknown'),
                                'duration': info.get('duration', 0),
                                'view_count': info.get('view_count', 0),
                                'upload_date': info.get('upload_date', 'Unknown'),
                                'formats': len(info.get('formats', [])),
                                'platform': self.detect_platform(url)
                            }
                except Exception as e:
                    print(f"[!] Cookie method failed: {str(e)[:100]}...")
            
            # Method 3: Try with alternative user agent
            try:
                print(f"[3/3] Trying with mobile user agent...")
                ydl_opts_alt = ydl_opts.copy()
                ydl_opts_alt['http_headers'] = {
                    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9',
                }
                
                with yt_dlp.YoutubeDL(ydl_opts_alt) as ydl:
                    info = ydl.extract_info(url, download=False)
                    if info:
                        print(f"[OK] Alternative user agent successful")
                        return {
                            'title': info.get('title', 'Unknown'),
                            'uploader': info.get('uploader', 'Unknown'),
                            'duration': info.get('duration', 0),
                            'view_count': info.get('view_count', 0),
                            'upload_date': info.get('upload_date', 'Unknown'),
                            'formats': len(info.get('formats', [])),
                            'platform': self.detect_platform(url)
                        }
            except Exception as e:
                print(f"[!] Alternative method failed: {str(e)[:100]}...")
            
            # All TikTok methods failed
            print(f"[X] All TikTok extraction methods failed")
            print(f"[?] TikTok Workarounds:")
            print(f"    1. Use browser extension: TikTok Video Downloader")
            print(f"    2. Try online service: ssstik.io or snaptik.app")
            print(f"    3. Use VPN to change location")
            print(f"    4. Export cookies from browser (see cookies/tiktok_cookies.txt)")
            print(f"    5. Wait for yt-dlp update (usually fixed within days)")
            
            return None
        
        # Standard extraction for non-TikTok URLs
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return {
                    'title': info.get('title', 'Unknown'),
                    'uploader': info.get('uploader', 'Unknown'),
                    'duration': info.get('duration', 0),
                    'view_count': info.get('view_count', 0),
                    'upload_date': info.get('upload_date', 'Unknown'),
                    'formats': len(info.get('formats', [])),
                    'platform': self.detect_platform(url)
                }
        except Exception as e:
            return None
    
    def format_duration(self, seconds):
        """Format duration from seconds to HH:MM:SS"""
        if not seconds:
            return "Unknown"
        
        # Ensure seconds is an integer
        seconds = int(seconds)
        
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"
    
    def format_views(self, views):
        """Format view count"""
        if not views:
            return "Unknown"
        
        if views >= 1_000_000:
            return f"{views / 1_000_000:.1f}M"
        elif views >= 1_000:
            return f"{views / 1_000:.1f}K"
        else:
            return str(views)
    
    def progress_hook(self, d):
        """Progress hook for yt-dlp"""
        if d['status'] == 'downloading':
            if 'total_bytes' in d:
                percent = d['downloaded_bytes'] / d['total_bytes'] * 100
                print(f"\r{Fore.CYAN}Downloading: {percent:.1f}%", end='', flush=True)
            elif 'total_bytes_estimate' in d:
                percent = d['downloaded_bytes'] / d['total_bytes_estimate'] * 100
                print(f"\r{Fore.CYAN}Downloading: {percent:.1f}% (estimated)", end='', flush=True)
        elif d['status'] == 'finished':
            print(f"\r{Fore.GREEN}✓ Download completed: {d['filename']}")
    
    def get_tiktok_options(self):
        """Get TikTok-specific options to handle extraction issues"""
        return {
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            },
            'extractor_args': {
                'tiktok': {
                    'webpage_download_timeout': 30,
                    'api_hostname': 'api.tiktokv.com',
                }
            },
            'sleep_interval': 1,
            'max_sleep_interval': 5,
        }
    
    def download_video(self, url, quality='best', audio_only=False, subtitle=False, custom_name=None, format_pref='any'):
        """Download video with specified options"""
        platform = self.detect_platform(url)
        self._format_pref = format_pref
        
        # Base options
        ydl_opts = {
            'outtmpl': str(self.output_dir / '%(title)s.%(ext)s'),
            'progress_hooks': [self.progress_hook],
            'retries': 3,
            'fragment_retries': 3,
            'skip_unavailable_fragments': True,
        }
        
        # Platform-specific options
        if platform == 'TikTok':
            print(f"{Fore.YELLOW}Applying TikTok-specific settings...")
            tiktok_opts = self.get_tiktok_options()
            ydl_opts.update(tiktok_opts)
        
        # Custom filename
        if custom_name:
            ydl_opts['outtmpl'] = str(self.output_dir / f'{custom_name}.%(ext)s')
        
        # Quality selection
        if audio_only:
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
        else:
            # Format preference
            format_preference = ''
            if hasattr(self, '_format_pref') and self._format_pref != 'any':
                format_preference = f'[ext={self._format_pref}]'
            
            if quality == 'best':
                ydl_opts['format'] = f'best{format_preference}'
            elif quality == 'worst':
                ydl_opts['format'] = f'worst{format_preference}'
            else:
                # Specific quality (e.g., '720p', '1080p')
                height = quality[:-1]
                ydl_opts['format'] = f'best[height<={height}]{format_preference}'
        
        # Subtitle options
        if subtitle:
            ydl_opts['writesubtitles'] = True
            ydl_opts['writeautomaticsub'] = True
        
        # First attempt with standard options
        try:
            print(f"{Fore.YELLOW}Platform detected: {platform}")
            print(f"{Fore.BLUE}Starting download...")
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            print(f"{Fore.GREEN}✓ Successfully downloaded from {platform}")
            return True
            
        except Exception as e:
            error_msg = str(e).lower()
            
            # TikTok-specific error handling
            if platform == 'TikTok' and ('sigi state' in error_msg or 'json' in error_msg):
                print(f"{Fore.YELLOW}TikTok extraction failed, trying alternative methods...")
                return self.try_tiktok_fallbacks(url, ydl_opts)
            
            print(f"{Fore.RED}✗ Error downloading video: {str(e)}")
            
            # Try with different user agent for other platforms
            if 'http' in error_msg or 'forbidden' in error_msg:
                print(f"{Fore.YELLOW}Trying with different user agent...")
                return self.try_with_fallback_headers(url, ydl_opts)
            
            return False
    
    def try_tiktok_fallbacks(self, url, base_opts):
        """Try multiple fallback methods for TikTok"""
        fallback_methods = [
            # Method 1: Different API approach
            {
                'extractor_args': {
                    'tiktok': {
                        'api_hostname': 'api.tiktokv.com',
                        'app_version': '34.1.2',
                        'manifest_app_version': '2023403020',
                    }
                },
                'http_headers': {
                    'User-Agent': 'com.zhiliaoapp.musically/2023403020 (Linux; U; Android 13; en_US; Pixel 7; Build/TQ3A.230805.001; Cronet/119.0.6045.31)',
                }
            },
            # Method 2: Web scraping approach
            {
                'extractor_args': {
                    'tiktok': {
                        'webpage_download_timeout': 60,
                    }
                },
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
                    'Accept': '*/*',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Referer': 'https://www.tiktok.com/',
                }
            },
            # Method 3: Minimal options
            {
                'http_headers': {
                    'User-Agent': 'TikTok 26.2.0 rv:262018 (iPhone; iOS 14.4.2; en_US) Cronet',
                },
                'extractor_args': {},
            }
        ]
        
        for i, method in enumerate(fallback_methods, 1):
            try:
                print(f"{Fore.CYAN}Trying TikTok fallback method {i}...")
                
                # Create new options with fallback method
                fallback_opts = base_opts.copy()
                fallback_opts.update(method)
                
                with yt_dlp.YoutubeDL(fallback_opts) as ydl:
                    ydl.download([url])
                
                print(f"{Fore.GREEN}✓ TikTok download successful with method {i}")
                return True
                
            except Exception as e:
                print(f"{Fore.RED}Method {i} failed: {str(e)[:100]}...")
                continue
        
        print(f"{Fore.RED}✗ All TikTok fallback methods failed")
        
        # Try alternative helper if available
        if self.tiktok_helper:
            print(f"{Fore.CYAN}Trying alternative TikTok extraction...")
            alt_info = self.tiktok_helper.get_video_info_alternative(url)
            if alt_info:
                print(f"{Fore.YELLOW}Alternative method found video info but cannot download directly")
                print(f"Title: {alt_info.get('title', 'Unknown')}")
                print(f"Uploader: {alt_info.get('uploader', 'Unknown')}")
        
        print(f"{Fore.YELLOW}Suggestions:")
        if self.tiktok_helper:
            suggestions = self.tiktok_helper.suggest_alternatives(url)
            print(suggestions)
        else:
            print(f"  1. Update yt-dlp: pip install --upgrade yt-dlp")
            print(f"  2. Try again later (TikTok may be blocking requests)")
            print(f"  3. Use a VPN if you're in a restricted region")
            print(f"  4. Check if the video is still available")
        
        return False
    
    def try_with_fallback_headers(self, url, base_opts):
        """Try download with different headers for other platforms"""
        try:
            print(f"{Fore.CYAN}Retrying with fallback headers...")
            
            fallback_opts = base_opts.copy()
            fallback_opts['http_headers'] = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            with yt_dlp.YoutubeDL(fallback_opts) as ydl:
                ydl.download([url])
            
            print(f"{Fore.GREEN}✓ Download successful with fallback headers")
            return True
            
        except Exception as e:
            print(f"{Fore.RED}✗ Fallback method also failed: {str(e)}")
            return False
    
    def batch_download(self, urls, **kwargs):
        """Download multiple videos"""
        successful = 0
        failed = 0
        
        print(f"{Fore.MAGENTA}Starting batch download of {len(urls)} videos...")
        
        for i, url in enumerate(urls, 1):
            print(f"\n{Fore.CYAN}[{i}/{len(urls)}] Processing: {url}")
            
            if self.download_video(url, **kwargs):
                successful += 1
            else:
                failed += 1
        
        print(f"\n{Fore.GREEN}Batch download completed!")
        print(f"✓ Successful: {successful}")
        print(f"✗ Failed: {failed}")
    
    def list_formats(self, url):
        """List available formats for a video"""
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                print(f"{Fore.CYAN}Available formats for: {info.get('title', 'Unknown')}")
                print("-" * 80)
                
                formats = info.get('formats', [])
                for fmt in formats:
                    format_id = fmt.get('format_id', 'N/A')
                    ext = fmt.get('ext', 'N/A')
                    resolution = fmt.get('resolution', 'N/A')
                    filesize = fmt.get('filesize', 0)
                    
                    size_str = f"{filesize / (1024*1024):.1f}MB" if filesize else "Unknown"
                    
                    print(f"ID: {format_id:10} | Ext: {ext:5} | Resolution: {resolution:15} | Size: {size_str}")
                
                return True
                
        except Exception as e:
            print(f"{Fore.RED}✗ Error getting formats: {str(e)}")
            return False


def main():
    parser = argparse.ArgumentParser(
        description="Multi-Platform Video Downloader",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python video_downloader.py "https://youtube.com/watch?v=example"
  python video_downloader.py -q 720p -s "https://tiktok.com/@user/video/123"
  python video_downloader.py -a "https://youtube.com/watch?v=example"
  python video_downloader.py -i "https://youtube.com/watch?v=example"
  python video_downloader.py -f formats.txt --batch
        """
    )
    
    parser.add_argument('url', nargs='?', help='Video URL to download')
    parser.add_argument('-q', '--quality', choices=['best', 'worst', '720p', '1080p', '480p'], 
                       default='best', help='Video quality (default: best)')
    parser.add_argument('--format', choices=['mp4', 'webm', 'any'], default='any',
                       help='Preferred video format (default: any)')
    parser.add_argument('-a', '--audio-only', action='store_true', 
                       help='Download audio only (MP3)')
    parser.add_argument('-s', '--subtitle', action='store_true', 
                       help='Download subtitles')
    parser.add_argument('-o', '--output', default='downloads', 
                       help='Output directory (default: downloads)')
    parser.add_argument('-n', '--name', help='Custom filename')
    parser.add_argument('-i', '--info', action='store_true', 
                       help='Show video information only')
    parser.add_argument('-l', '--list-formats', action='store_true', 
                       help='List available formats')
    parser.add_argument('-f', '--file', help='File containing URLs for batch download')
    parser.add_argument('--batch', action='store_true', 
                       help='Enable batch download mode')
    
    args = parser.parse_args()
    
    # Create downloader instance
    downloader = VideoDownloader(args.output)
    
    # Handle batch download
    if args.batch and args.file:
        try:
            with open(args.file, 'r') as f:
                urls = [line.strip() for line in f if line.strip()]
            
            downloader.batch_download(
                urls,
                quality=args.quality,
                audio_only=args.audio_only,
                subtitle=args.subtitle,
                custom_name=args.name
            )
        except FileNotFoundError:
            print(f"{Fore.RED}✗ File not found: {args.file}")
            return
    
    # Handle single URL operations
    elif args.url:
        # Show video info
        if args.info:
            info = downloader.get_video_info(args.url)
            if info:
                print(f"{Fore.CYAN}Video Information:")
                print("-" * 50)
                print(f"Title: {info['title']}")
                print(f"Uploader: {info['uploader']}")
                print(f"Platform: {info['platform']}")
                print(f"Duration: {downloader.format_duration(info['duration'])}")
                print(f"Views: {downloader.format_views(info['view_count'])}")
                print(f"Upload Date: {info['upload_date']}")
                print(f"Available Formats: {info['formats']}")
            else:
                print(f"{Fore.RED}✗ Could not get video information")
        
        # List formats
        elif args.list_formats:
            downloader.list_formats(args.url)
        
        # Download video
        else:
            downloader.download_video(
                args.url,
                quality=args.quality,
                audio_only=args.audio_only,
                subtitle=args.subtitle,
                custom_name=args.name,
                format_pref=args.format
            )
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()