#!/usr/bin/env python3
"""
TikTok OCR Caption Extractor
Extracts text overlays/captions that are burned into TikTok videos
"""

import cv2
import numpy as np
from pathlib import Path
import re
import json

try:
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False

class TikTokOCRExtractor:
    def __init__(self):
        self.ocr_reader = None
        if EASYOCR_AVAILABLE:
            try:
                self.ocr_reader = easyocr.Reader(['en'])
            except:
                pass
    
    def extract_captions_from_video(self, video_path, output_path=None, callback=None):
        """Extract text overlays from TikTok video using OCR"""
        
        if not OCR_AVAILABLE and not EASYOCR_AVAILABLE:
            if callback:
                callback("[!] OCR libraries not available. Install: pip install pytesseract easyocr")
            return False
        
        video_path = Path(video_path)
        if not video_path.exists():
            if callback:
                callback(f"[!] Video file not found: {video_path}")
            return False
        
        if callback:
            callback("[*] Extracting text overlays from TikTok video...")
        
        try:
            # Open video
            cap = cv2.VideoCapture(str(video_path))
            if not cap.isOpened():
                if callback:
                    callback("[!] Could not open video file")
                return False
            
            # Get video properties
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = total_frames / fps if fps > 0 else 0
            
            if callback:
                callback(f"[*] Video: {duration:.1f}s, {fps:.1f} FPS, {total_frames} frames")
            
            # Extract text from key frames
            captions = []
            frame_interval = max(1, int(fps * 0.5))  # Sample every 0.5 seconds
            
            frame_count = 0
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Process every nth frame
                if frame_count % frame_interval == 0:
                    timestamp = frame_count / fps
                    text = self._extract_text_from_frame(frame, timestamp)
                    
                    if text:
                        captions.append({
                            'timestamp': timestamp,
                            'text': text,
                            'frame': frame_count
                        })
                        
                        if callback:
                            callback(f"[*] Frame {frame_count}: Found text")
                
                frame_count += 1
                
                # Progress update
                if callback and frame_count % (frame_interval * 10) == 0:
                    progress = (frame_count / total_frames) * 100
                    callback(f"[...] Processing: {progress:.1f}%")
            
            cap.release()
            
            if callback:
                callback(f"[OK] Extracted text from {len(captions)} frames")
            
            # Clean and merge captions
            cleaned_captions = self._clean_and_merge_captions(captions)
            
            # Save captions
            if output_path:
                self._save_captions(cleaned_captions, output_path, duration)
                if callback:
                    callback(f"[OK] Captions saved to: {output_path}")
            
            return cleaned_captions
            
        except Exception as e:
            if callback:
                callback(f"[!] OCR extraction failed: {str(e)}")
            return False
    
    def _extract_text_from_frame(self, frame, timestamp):
        """Extract text from a single frame"""
        try:
            # Convert to RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Focus on bottom area where TikTok captions usually appear
            height, width = rgb_frame.shape[:2]
            
            # TikTok captions are typically in the bottom 1/3 of the video
            caption_area = rgb_frame[int(height * 0.6):, :]
            
            # Preprocess for better OCR
            gray = cv2.cvtColor(caption_area, cv2.COLOR_RGB2GRAY)
            
            # Enhance contrast
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            enhanced = clahe.apply(gray)
            
            # Try different thresholding methods
            texts = []
            
            # Method 1: EasyOCR (if available)
            if self.ocr_reader:
                try:
                    results = self.ocr_reader.readtext(enhanced)
                    for (bbox, text, confidence) in results:
                        if confidence > 0.5 and len(text.strip()) > 2:
                            texts.append(text.strip())
                except:
                    pass
            
            # Method 2: Tesseract (if available)
            if OCR_AVAILABLE and not texts:
                try:
                    # Binary threshold
                    _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                    text = pytesseract.image_to_string(binary, config='--psm 6')
                    if text.strip():
                        texts.append(text.strip())
                    
                    # Inverted binary
                    _, inv_binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
                    text = pytesseract.image_to_string(inv_binary, config='--psm 6')
                    if text.strip():
                        texts.append(text.strip())
                except:
                    pass
            
            # Return the best text found
            if texts:
                # Choose the longest meaningful text
                best_text = max(texts, key=len)
                # Clean up common OCR errors
                best_text = re.sub(r'[^\w\s\.,!?\'"-]', '', best_text)
                best_text = re.sub(r'\s+', ' ', best_text).strip()
                
                if len(best_text) > 2:
                    return best_text
            
            return None
            
        except Exception as e:
            return None
    
    def _clean_and_merge_captions(self, captions):
        """Clean and merge similar captions"""
        if not captions:
            return []
        
        # Group similar captions
        merged = []
        current_group = [captions[0]]
        
        for i in range(1, len(captions)):
            current_text = captions[i]['text']
            prev_text = current_group[-1]['text']
            
            # Check similarity (simple approach)
            similarity = self._text_similarity(current_text, prev_text)
            time_diff = captions[i]['timestamp'] - current_group[-1]['timestamp']
            
            if similarity > 0.7 and time_diff < 3.0:  # Similar text within 3 seconds
                current_group.append(captions[i])
            else:
                # Process current group
                if current_group:
                    merged_caption = self._merge_caption_group(current_group)
                    if merged_caption:
                        merged.append(merged_caption)
                current_group = [captions[i]]
        
        # Process last group
        if current_group:
            merged_caption = self._merge_caption_group(current_group)
            if merged_caption:
                merged.append(merged_caption)
        
        return merged
    
    def _text_similarity(self, text1, text2):
        """Calculate simple text similarity"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0
    
    def _merge_caption_group(self, group):
        """Merge a group of similar captions"""
        if not group:
            return None
        
        # Use the longest text as the main caption
        best_caption = max(group, key=lambda x: len(x['text']))
        
        start_time = group[0]['timestamp']
        end_time = group[-1]['timestamp'] + 1.0  # Add 1 second duration
        
        return {
            'start': start_time,
            'end': end_time,
            'text': best_caption['text']
        }
    
    def _save_captions(self, captions, output_path, duration):
        """Save captions in SRT format"""
        output_path = Path(output_path)
        
        srt_content = ""
        for i, caption in enumerate(captions, 1):
            start_time = self._seconds_to_srt_time(caption['start'])
            end_time = self._seconds_to_srt_time(caption['end'])
            
            srt_content += f"{i}\n"
            srt_content += f"{start_time} --> {end_time}\n"
            srt_content += f"{caption['text']}\n\n"
        
        # Save SRT file
        srt_path = output_path.with_suffix('.srt')
        with open(srt_path, 'w', encoding='utf-8') as f:
            f.write(srt_content)
        
        # Save JSON for debugging
        json_path = output_path.with_suffix('.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(captions, f, indent=2, ensure_ascii=False)
    
    def _seconds_to_srt_time(self, seconds):
        """Convert seconds to SRT time format"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millisecs = int((seconds % 1) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millisecs:03d}"

def extract_tiktok_captions(video_path, callback=None):
    """Main function to extract TikTok captions"""
    extractor = TikTokOCRExtractor()
    
    video_path = Path(video_path)
    output_path = video_path.with_suffix('')  # Remove extension for base name
    
    return extractor.extract_captions_from_video(video_path, output_path, callback)

if __name__ == "__main__":
    print("TikTok OCR Caption Extractor")
    print("=" * 40)
    print("This tool extracts text overlays from TikTok videos using OCR")
    print("Requirements: pip install opencv-python pytesseract easyocr")
    print()
    
    # Example usage
    video_file = "path/to/tiktok_video.mp4"
    print(f"To use: extract_tiktok_captions('{video_file}')")