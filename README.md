# Multi-Platform Video Downloader

A powerful Python tool for downloading videos from multiple platforms including YouTube, TikTok, Facebook, Instagram, Twitter, and more.

## Features

### Supported Platforms
- **YouTube** (youtube.com, youtu.be)
- **TikTok** (tiktok.com)
- **Facebook** (facebook.com, fb.watch)
- **Instagram** (instagram.com)
- **Twitter/X** (twitter.com, x.com)
- **Vimeo** (vimeo.com)
- **Dailymotion** (dailymotion.com)
- **Twitch** (twitch.tv)

### Key Features
- **Multiple Quality Options**: Download in best, worst, or specific resolutions (1080p, 720p, 480p)
- **Audio-Only Downloads**: Extract audio as MP3 files
- **Subtitle Support**: Download video subtitles automatically
- **Batch Downloads**: Process multiple URLs from a text file
- **Video Information**: Get detailed info without downloading
- **Format Listing**: View all available formats for any video
- **Custom Naming**: Set custom filenames for downloads
- **Progress Tracking**: Real-time download progress
- **GUI Interface**: User-friendly graphical interface
- **Cross-Platform**: Works on Windows, macOS, and Linux

## Installation

1. **Clone or download the project files**

2. **Install Python dependencies:**
```bash
pip install -r requirements.txt
```

3. **Install FFmpeg (required for audio extraction):**
   - **Windows**: Download from https://ffmpeg.org/download.html
   - **macOS**: `brew install ffmpeg`
   - **Linux**: `sudo apt install ffmpeg` (Ubuntu/Debian)

## Usage

### Command Line Interface

#### Basic Download
```bash
python video_downloader.py "https://youtube.com/watch?v=example"
```

#### Download with Options
```bash
# Download in 720p quality
python video_downloader.py -q 720p "https://youtube.com/watch?v=example"

# Download audio only (MP3)
python video_downloader.py -a "https://youtube.com/watch?v=example"

# Download with subtitles
python video_downloader.py -s "https://youtube.com/watch?v=example"

# Custom output directory and filename
python video_downloader.py -o "my_videos" -n "my_video" "https://youtube.com/watch?v=example"
```

#### Get Video Information
```bash
python video_downloader.py -i "https://youtube.com/watch?v=example"
```

#### List Available Formats
```bash
python video_downloader.py -l "https://youtube.com/watch?v=example"
```

#### Batch Download
```bash
# Create a text file with URLs (one per line)
echo "https://youtube.com/watch?v=example1" > urls.txt
echo "https://tiktok.com/@user/video/123" >> urls.txt

# Download all URLs
python video_downloader.py -f urls.txt --batch
```

### GUI Interface

Launch the graphical interface:
```bash
python gui_downloader.py
```

The GUI provides:
- Easy URL input
- Quality selection dropdown
- Audio-only and subtitle checkboxes
- Output directory browser
- Real-time progress tracking
- Download log display
- Batch download from file

## Command Line Options

```
positional arguments:
  url                   Video URL to download

optional arguments:
  -h, --help            Show help message
  -q, --quality         Video quality: best, worst, 720p, 1080p, 480p
  -a, --audio-only      Download audio only (MP3)
  -s, --subtitle        Download subtitles
  -o, --output          Output directory (default: downloads)
  -n, --name            Custom filename
  -i, --info            Show video information only
  -l, --list-formats    List available formats
  -f, --file            File containing URLs for batch download
  --batch               Enable batch download mode
```

## Examples

### Single Video Downloads
```bash
# YouTube video in best quality
python video_downloader.py "https://youtube.com/watch?v=dQw4w9WgXcQ"

# TikTok video as audio only
python video_downloader.py -a "https://tiktok.com/@user/video/123456"

# Instagram video with subtitles
python video_downloader.py -s "https://instagram.com/p/ABC123/"

# Facebook video in 720p
python video_downloader.py -q 720p "https://facebook.com/watch/?v=123456"
```

### Batch Operations
```bash
# Get info for multiple videos
python video_downloader.py -i "https://youtube.com/watch?v=example1"
python video_downloader.py -i "https://tiktok.com/@user/video/123"

# Batch download with custom settings
python video_downloader.py -f my_urls.txt --batch -q 720p -s
```

## File Structure

```
video-downloader/
├── video_downloader.py    # Main CLI application
├── gui_downloader.py      # GUI application
├── requirements.txt       # Python dependencies
├── README.md             # This file
└── downloads/            # Default download directory (created automatically)
```

## Troubleshooting TikTok Downloads

TikTok frequently updates their anti-bot measures, which can cause download failures. Here are solutions:

### Quick Fixes

1. **Update yt-dlp** (most important):
```bash
pip install --upgrade yt-dlp
```

2. **Run the update script**:
```bash
python update_ytdlp.py
```

3. **Try the enhanced downloader** with TikTok-specific handling:
```bash
python video_downloader.py "https://tiktok.com/@user/video/123"
```

### Common TikTok Errors

**"Unable to extract sigi state"** or **"JSON decode error"**:
- This happens when TikTok blocks automated requests
- The tool automatically tries multiple fallback methods
- Wait a few hours and try again
- Use a VPN to change your location

**"Video unavailable"**:
- Check if the video is still public
- Some videos are region-locked
- Private accounts cannot be accessed

### Alternative Solutions

If the main downloader fails, try:
1. Browser extensions for TikTok downloading
2. Online TikTok download services
3. Mobile apps designed for TikTok downloads
4. Screen recording as a last resort

### Platform-Specific Notes

- **TikTok**: Some videos may require cookies for access
- **Instagram**: Private accounts are not accessible
- **Facebook**: Some videos may require login
- **Twitter**: Video availability depends on privacy settings

## Legal Notice

This tool is for educational and personal use only. Please respect:
- Platform terms of service
- Copyright laws
- Content creators' rights
- Fair use guidelines

Always ensure you have permission to download content, especially for commercial use.

## Dependencies

- **yt-dlp**: Core video downloading functionality
- **requests**: HTTP requests handling
- **colorama**: Cross-platform colored terminal output
- **tqdm**: Progress bars
- **tkinter**: GUI interface (included with Python)

## Contributing

Feel free to contribute by:
- Reporting bugs
- Suggesting new features
- Adding support for more platforms
- Improving the user interface

## License

This project is open source. Use responsibly and in accordance with applicable laws and platform terms of service.