#!/usr/bin/env python3
"""
Video Format Converter
Converts downloaded videos to more compatible formats
"""

import os
import sys
import subprocess
from pathlib import Path
import argparse
from colorama import init, Fore, Style

init(autoreset=True)

class VideoConverter:
    def __init__(self):
        self.supported_formats = {
            'mp4': 'MP4 (H.264) - Most compatible',
            'avi': 'AVI - Windows compatible',
            'mov': 'MOV - QuickTime format',
            'wmv': 'WMV - Windows Media Video',
            'mkv': 'MKV - Matroska container',
        }
    
    def check_ffmpeg(self):
        """Check if FFmpeg is installed"""
        try:
            result = subprocess.run(['ffmpeg', '-version'], 
                                  capture_output=True, text=True)
            return result.returncode == 0
        except FileNotFoundError:
            return False
    
    def install_ffmpeg_instructions(self):
        """Provide FFmpeg installation instructions"""
        print(f"{Fore.YELLOW}FFmpeg is required for video conversion.")
        print(f"{Fore.CYAN}Installation options:")
        print("1. Download from: https://ffmpeg.org/download.html")
        print("2. Using Chocolatey: choco install ffmpeg")
        print("3. Using Scoop: scoop install ffmpeg")
        print("4. Manual installation: Extract to a folder and add to PATH")
    
    def convert_video(self, input_file, output_format='mp4', quality='medium'):
        """Convert video to specified format"""
        if not self.check_ffmpeg():
            print(f"{Fore.RED}✗ FFmpeg not found!")
            self.install_ffmpeg_instructions()
            return False
        
        input_path = Path(input_file)
        if not input_path.exists():
            print(f"{Fore.RED}✗ Input file not found: {input_file}")
            return False
        
        # Create output filename
        output_path = input_path.with_suffix(f'.{output_format}')
        if output_path.exists():
            output_path = input_path.with_name(f"{input_path.stem}_converted.{output_format}")
        
        # Quality settings
        quality_settings = {
            'high': ['-crf', '18'],
            'medium': ['-crf', '23'],
            'low': ['-crf', '28'],
            'fast': ['-preset', 'fast', '-crf', '23']
        }
        
        # Build FFmpeg command
        cmd = [
            'ffmpeg',
            '-i', str(input_path),
            '-c:v', 'libx264',  # Use H.264 codec (most compatible)
            '-c:a', 'aac',      # Use AAC audio codec
            '-movflags', '+faststart',  # Optimize for web playback
        ]
        
        # Add quality settings
        if quality in quality_settings:
            cmd.extend(quality_settings[quality])
        
        cmd.append(str(output_path))
        
        try:
            print(f"{Fore.YELLOW}Converting {input_path.name} to {output_format.upper()}...")
            print(f"{Fore.CYAN}Output: {output_path.name}")
            
            # Run conversion
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"{Fore.GREEN}✓ Conversion successful!")
                print(f"Original size: {input_path.stat().st_size / (1024*1024):.1f} MB")
                print(f"Converted size: {output_path.stat().st_size / (1024*1024):.1f} MB")
                return True
            else:
                print(f"{Fore.RED}✗ Conversion failed!")
                print(f"Error: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"{Fore.RED}✗ Conversion error: {str(e)}")
            return False
    
    def batch_convert(self, directory, output_format='mp4', quality='medium'):
        """Convert all videos in a directory"""
        dir_path = Path(directory)
        if not dir_path.exists():
            print(f"{Fore.RED}✗ Directory not found: {directory}")
            return
        
        # Find video files
        video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v']
        video_files = []
        
        for ext in video_extensions:
            video_files.extend(dir_path.glob(f'*{ext}'))
        
        if not video_files:
            print(f"{Fore.YELLOW}No video files found in {directory}")
            return
        
        print(f"{Fore.CYAN}Found {len(video_files)} video files")
        successful = 0
        
        for video_file in video_files:
            print(f"\n{Fore.CYAN}Processing: {video_file.name}")
            if self.convert_video(video_file, output_format, quality):
                successful += 1
        
        print(f"\n{Fore.GREEN}Batch conversion completed!")
        print(f"✓ Successful: {successful}/{len(video_files)}")

def main():
    parser = argparse.ArgumentParser(
        description="Video Format Converter",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python video_converter.py video.mp4
  python video_converter.py video.mp4 -f avi -q high
  python video_converter.py downloads/ --batch -f mp4
        """
    )
    
    parser.add_argument('input', help='Input video file or directory')
    parser.add_argument('-f', '--format', choices=['mp4', 'avi', 'mov', 'wmv', 'mkv'],
                       default='mp4', help='Output format (default: mp4)')
    parser.add_argument('-q', '--quality', choices=['high', 'medium', 'low', 'fast'],
                       default='medium', help='Quality preset (default: medium)')
    parser.add_argument('--batch', action='store_true',
                       help='Convert all videos in directory')
    
    args = parser.parse_args()
    
    converter = VideoConverter()
    
    if args.batch:
        converter.batch_convert(args.input, args.format, args.quality)
    else:
        converter.convert_video(args.input, args.format, args.quality)

if __name__ == "__main__":
    main()