#!/usr/bin/env python3
"""
Download videos in Windows-compatible format
Forces H.264/MP4 format that works on all Windows systems
"""

import yt_dlp
import sys
from pathlib import Path
from colorama import init, Fore

init(autoreset=True)

def download_compatible_video(url, output_dir="downloads"):
    """Download video in Windows-compatible format"""
    
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Force H.264/MP4 format - most compatible with Windows
    ydl_opts = {
        'outtmpl': str(output_path / '%(title)s.%(ext)s'),
        'format': 'best[ext=mp4][vcodec^=avc1]/best[ext=mp4]/best',  # Prefer H.264 MP4
        'postprocessors': [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4',
        }],
        'prefer_ffmpeg': True,
    }
    
    try:
        print(f"{Fore.YELLOW}Downloading in Windows-compatible format...")
        print(f"{Fore.CYAN}URL: {url}")
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Get video info first
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'Unknown')
            print(f"{Fore.GREEN}Title: {title}")
            
            # Download
            ydl.download([url])
            
        print(f"{Fore.GREEN}✓ Download completed in compatible format!")
        print(f"{Fore.CYAN}The video should now play in Windows Media Player")
        
    except Exception as e:
        print(f"{Fore.RED}✗ Download failed: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python download_compatible.py <video_url>")
        print("Example: python download_compatible.py 'https://tiktok.com/@user/video/123'")
        sys.exit(1)
    
    url = sys.argv[1]
    download_compatible_video(url)