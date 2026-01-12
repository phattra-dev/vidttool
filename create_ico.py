"""
Create ICO file from PNG for Windows EXE icon
Run: python create_ico.py
"""

import subprocess
import sys

def install_pillow():
    try:
        from PIL import Image
        return True
    except ImportError:
        print("Installing Pillow...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow"])
        return True

def create_ico():
    install_pillow()
    from PIL import Image
    
    # Find PNG file
    png_path = None
    for path in ["logo/logo.png", "logo.png"]:
        try:
            img = Image.open(path)
            png_path = path
            break
        except:
            continue
    
    if not png_path:
        print("❌ No logo.png found!")
        return False
    
    print(f"✓ Found: {png_path}")
    
    # Open and convert to RGBA for transparency support
    img = Image.open(png_path)
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    
    # Create multiple sizes for ICO (Windows uses these sizes)
    sizes = [256, 128, 64, 48, 32, 16]
    
    # Resize images with high quality
    icons = []
    for size in sizes:
        # Use LANCZOS for high quality downscaling
        resized = img.resize((size, size), Image.Resampling.LANCZOS)
        icons.append(resized)
    
    # Save as ICO with all sizes embedded
    ico_path = "logo.ico"
    
    # The first image saves, append_images adds the rest
    icons[0].save(
        ico_path, 
        format='ICO',
        append_images=icons[1:],
        sizes=[(s, s) for s in sizes]
    )
    
    print(f"✅ Created: {ico_path}")
    print(f"   Included sizes: {', '.join([f'{s}x{s}' for s in sizes])}")
    print(f"\n💡 Tip: For best quality, use a source PNG that is at least 256x256 pixels")
    return True

if __name__ == "__main__":
    create_ico()
