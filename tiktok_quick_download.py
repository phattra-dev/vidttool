#!/usr/bin/env python3
"""
Quick TikTok Download Helper - Alternative methods when yt-dlp fails
"""

import webbrowser
import sys
from urllib.parse import quote

def quick_tiktok_download(url):
    """Open TikTok URL in various online downloaders"""
    print(f"🎬 TikTok Quick Download Helper")
    print(f"URL: {url}")
    print("-" * 50)
    
    # Online services
    services = [
        ("ssstik.io", f"https://ssstik.io/en"),
        ("snaptik.app", f"https://snaptik.app/"),
        ("tikmate.online", f"https://tikmate.online/"),
        ("tiktokdownload.online", f"https://tiktokdownload.online/"),
    ]
    
    print("🌐 Opening online TikTok downloaders...")
    print("📋 Copy and paste your TikTok URL in each service:")
    print(f"   {url}")
    print()
    
    for name, service_url in services:
        print(f"Opening {name}...")
        webbrowser.open(service_url)
    
    print(f"\n✅ Opened {len(services)} TikTok download services")
    print(f"📝 Instructions:")
    print(f"   1. Paste your TikTok URL in any of the opened websites")
    print(f"   2. Click download")
    print(f"   3. Choose quality and save")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        url = sys.argv[1]
        quick_tiktok_download(url)
    else:
        url = input("Enter TikTok URL: ").strip()
        if url:
            quick_tiktok_download(url)
        else:
            print("No URL provided")