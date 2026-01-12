#!/usr/bin/env python3
"""
Quick test for TikTok URL detection
"""

from main import VideoDownloader

# Test the specific TikTok URL
test_url = "https://www.tiktok.com/@aidramalabs_anime2?_r=1&_t=ZT-92lUF9PqvuA"

dl = VideoDownloader()

print(f"Testing URL: {test_url}")
print(f"Platform: {dl.detect_platform(test_url)}")
print(f"Is Profile URL: {dl.is_profile_url(test_url)}")

# Test URL validation
is_valid, message = dl.validate_url(test_url)
print(f"Valid: {is_valid}, Message: {message}")

# Show clean URL
from urllib.parse import urlparse
parsed = urlparse(test_url)
clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
print(f"Clean URL: {clean_url}")

# Test detection logic step by step
clean_lower = clean_url.lower()
print(f"Has tiktok.com: {'tiktok.com' in clean_lower}")
print(f"Has /@: {'/@' in clean_lower}")
print(f"Has /video/: {'/video/' in clean_lower}")
print(f"Should be profile: {'/@' in clean_lower and '/video/' not in clean_lower}")