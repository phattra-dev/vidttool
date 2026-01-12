#!/usr/bin/env python3
"""
Create a simple logo/icon for the application
"""

from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont, QLinearGradient
from PyQt6.QtCore import Qt, QRect
import sys

def create_app_icon(size=256):
    """Create application icon"""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    # Create gradient background
    gradient = QLinearGradient(0, 0, size, size)
    gradient.setColorAt(0, QColor("#007acc"))
    gradient.setColorAt(1, QColor("#1177bb"))
    
    # Draw rounded rectangle background
    painter.setBrush(gradient)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(0, 0, size, size, size//8, size//8)
    
    # Draw download arrow
    painter.setPen(QColor("#ffffff"))
    painter.setBrush(QColor("#ffffff"))
    
    # Arrow shaft
    shaft_width = size // 8
    shaft_height = size // 3
    shaft_x = (size - shaft_width) // 2
    shaft_y = size // 4
    painter.drawRect(shaft_x, shaft_y, shaft_width, shaft_height)
    
    # Arrow head
    head_size = size // 4
    head_x = (size - head_size) // 2
    head_y = shaft_y + shaft_height - size // 16
    
    points = [
        (head_x, head_y),
        (head_x + head_size, head_y),
        (size // 2, head_y + head_size // 2)
    ]
    
    from PyQt6.QtGui import QPolygon
    from PyQt6.QtCore import QPoint
    
    polygon = QPolygon([QPoint(x, y) for x, y in points])
    painter.drawPolygon(polygon)
    
    # Add text
    painter.setFont(QFont("Arial", size // 12, QFont.Weight.Bold))
    text_rect = QRect(0, size - size//4, size, size//6)
    painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, "DL")
    
    painter.end()
    return pixmap

def main():
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # Create different sizes
    sizes = [16, 32, 48, 64, 128, 256]
    
    for size in sizes:
        icon = create_app_icon(size)
        icon.save(f"icon_{size}.png")
        print(f"Created icon_{size}.png")
    
    # Create main icon
    main_icon = create_app_icon(256)
    main_icon.save("icon.png")
    print("Created icon.png")
    
    print("✅ Icons created successfully!")

if __name__ == "__main__":
    main()