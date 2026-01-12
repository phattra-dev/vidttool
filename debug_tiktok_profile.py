#!/usr/bin/env python3
"""
Debug script for TikTok profile extraction
"""

import yt_dlp
from main import VideoDownloader

def test_tiktok_profile():
    """Test TikTok profile extraction with detailed debugging"""
    
    test_url = "https://www.tiktok.com/@aidramalabs_anime2"
    
    print(f"Testing TikTok profile: {test_url}")
    print("=" * 60)
    
    # Test with our VideoDownloader class
    print("\n1. Testing with VideoDownloader class:")
    dl = VideoDownloader()
    result = dl.get_profile_videos(test_url, max_videos=100)
    
    if result['success']:
        print(f"✅ Success!")
        print(f"Profile: {result['profile_name']}")
        print(f"Platform: {result['platform']}")
        print(f"Videos found: {result['total_found']}")
        print(f"Raw total: {result.get('raw_total', 'Unknown')}")
        
        if result['videos']:
            print(f"\nFirst 5 videos:")
            for i, video in enumerate(result['videos'][:5], 1):
                print(f"{i}. {video['title']} ({video.get('duration', 0)}s)")
    else:
        print(f"❌ Failed: {result['error']}")
        if 'technical_error' in result:
            print(f"Technical error: {result['technical_error']}")
    
    print("\n" + "=" * 60)
    
    # Test with raw yt-dlp
    print("\n2. Testing with raw yt-dlp:")
    
    opts = {
        'quiet': False,
        'no_warnings': False,
        'extract_flat': True,
        'ignoreerrors': True,
        'no_color': True,
        'playlistend': 100,
    }
    
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            print("Extracting info...")
            info = ydl.extract_info(test_url, download=False)
            
            if info:
                print(f"✅ Raw extraction successful!")
                print(f"Type: {type(info)}")
                print(f"Keys: {list(info.keys())}")
                
                if 'entries' in info:
                    entries = info['entries']
                    print(f"Entries found: {len(entries)}")
                    
                    # Count valid entries
                    valid_entries = [e for e in entries if e and e.get('url')]
                    print(f"Valid entries with URLs: {len(valid_entries)}")
                    
                    # Show first few entries
                    print("\nFirst 5 entries:")
                    for i, entry in enumerate(entries[:5]):
                        if entry:
                            print(f"{i+1}. {entry.get('title', 'No title')} - URL: {bool(entry.get('url'))}")
                        else:
                            print(f"{i+1}. None entry")
                
                # Check for playlist info
                if 'playlist_count' in info:
                    print(f"Playlist count: {info['playlist_count']}")
                
                # Check uploader info
                uploader = info.get('uploader', info.get('channel', info.get('title', 'Unknown')))
                print(f"Uploader: {uploader}")
                
            else:
                print("❌ No info returned")
                
    except Exception as e:
        print(f"❌ Raw yt-dlp failed: {e}")
    
    print("\n" + "=" * 60)
    
    # Test with different options
    print("\n3. Testing with TikTok-specific options:")
    
    tiktok_opts = {
        'quiet': False,
        'extract_flat': True,
        'ignoreerrors': True,
        'extractor_args': {
            'tiktok': {
                'max_pages': 20,  # Try more pages
            }
        }
    }
    
    try:
        with yt_dlp.YoutubeDL(tiktok_opts) as ydl:
            print("Extracting with TikTok-specific options...")
            info = ydl.extract_info(test_url, download=False)
            
            if info and 'entries' in info:
                entries = info['entries']
                valid_entries = [e for e in entries if e and e.get('url')]
                print(f"✅ TikTok-specific extraction: {len(valid_entries)} valid videos")
            else:
                print("❌ TikTok-specific extraction failed")
                
    except Exception as e:
        print(f"❌ TikTok-specific extraction failed: {e}")

if __name__ == '__main__':
    test_tiktok_profile()