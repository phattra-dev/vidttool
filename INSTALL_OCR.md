# TikTok Caption OCR Installation Guide

To extract text overlays/captions from TikTok videos, you need to install OCR (Optical Character Recognition) libraries.

## Required Libraries

### 1. OpenCV (Computer Vision)
```bash
pip install opencv-python
```

### 2. EasyOCR (Recommended - Better accuracy)
```bash
pip install easyocr
```

### 3. Tesseract OCR (Alternative)
```bash
pip install pytesseract
```

**For Tesseract, you also need to install the Tesseract engine:**

#### Windows:
1. Download from: https://github.com/UB-Mannheim/tesseract/wiki
2. Install the .exe file
3. Add to PATH or set TESSDATA_PREFIX environment variable

#### macOS:
```bash
brew install tesseract
```

#### Linux (Ubuntu/Debian):
```bash
sudo apt-get install tesseract-ocr
```

## Quick Install (All at once)
```bash
pip install opencv-python easyocr pytesseract
```

## How It Works

When you enable "Download Subtitles" for TikTok videos, the tool will:

1. **Download the video** normally
2. **Analyze video frames** to find text overlays
3. **Extract text** using OCR from the bottom area where captions usually appear
4. **Create subtitle files** (.srt) with the extracted text and timestamps
5. **Save both** video and subtitle files together

## Features

- **Smart Detection**: Focuses on bottom area where TikTok captions appear
- **Multiple OCR Engines**: Uses EasyOCR (preferred) or Tesseract as fallback
- **Text Cleaning**: Removes OCR artifacts and merges similar captions
- **Proper Timing**: Creates accurate timestamps for when text appears
- **SRT Format**: Compatible with all video players

## Example Output

After downloading a TikTok video with captions, you'll get:
- `tiktok_123456789.mp4` (the video)
- `tiktok_123456789.srt` (extracted captions)
- `tiktok_123456789.json` (debug info)

## Troubleshooting

### "OCR libraries not installed" error:
```bash
pip install opencv-python easyocr
```

### "No text overlays found" message:
- The video might not have text overlays
- Text might be too small or unclear
- Try with a different TikTok video that has clear text

### Poor OCR accuracy:
- EasyOCR generally works better than Tesseract for TikTok videos
- Make sure the video quality is good
- Some artistic fonts may not be recognized well

## Testing

Use the test script to verify OCR functionality:
```bash
python test_tiktok_captions.py
```

Replace the test URL with a real TikTok video that has text overlays to see the extraction in action.