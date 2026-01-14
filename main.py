#!/usr/bin/env python3
"""
Video Downloader Tool - Clean Modern Interface
"""

import sys
import os
from pathlib import Path
from urllib.parse import urlparse
import yt_dlp
from colorama import init, Fore

init(autoreset=True)

# Import Facebook helper for profile extraction
try:
    from facebook_helper import get_facebook_profile_videos, try_direct_facebook_download
    FACEBOOK_HELPER_AVAILABLE = True
except ImportError:
    FACEBOOK_HELPER_AVAILABLE = False
    try_direct_facebook_download = None

# Import Image downloader
try:
    from image_downloader import ImageDownloader
    IMAGE_DOWNLOADER_AVAILABLE = True
except ImportError:
    IMAGE_DOWNLOADER_AVAILABLE = False
    ImageDownloader = None

# Import License client
try:
    from license_client import get_license_client, LicenseClient
    LICENSE_CLIENT_AVAILABLE = True
except ImportError:
    LICENSE_CLIENT_AVAILABLE = False
    get_license_client = None
    LicenseClient = None

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QTextEdit, QComboBox, QCheckBox, QLabel,
    QProgressBar, QFileDialog, QMessageBox, QFrame, QGridLayout, QSizePolicy,
    QTabWidget, QDialog, QScrollArea, QListWidget, QListWidgetItem, QSpinBox,
    QProgressDialog, QDoubleSpinBox, QGroupBox, QColorDialog
)
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QSettings, QTimer, QUrl
from PyQt6.QtGui import QFont, QIcon, QPixmap, QDesktopServices, QColor


class URLListWidget(QWidget):
    """Custom widget for managing URLs with checkboxes"""
    
    def __init__(self, parent=None):
        super().__init__()
        self.parent_window = parent
        self.urls = []
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # Scroll area for URL list
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFixedHeight(80)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background: #21262d;
                border: none;
                border-radius: 6px;
            }
            QScrollBar:vertical {
                background: #161b22;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #30363d;
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #58a6ff;
            }
        """)
        
        # Container for URL checkboxes
        self.url_container = QWidget()
        self.url_layout = QVBoxLayout(self.url_container)
        self.url_layout.setContentsMargins(8, 8, 8, 8)
        self.url_layout.setSpacing(4)
        
        # Placeholder label
        self.placeholder_label = QLabel("Click 'Paste URLs' to add multiple video links from clipboard")
        self.placeholder_label.setStyleSheet("""
            QLabel {
                color: #7d8590;
                font-size: 12px;
                font-style: italic;
                border: none;
                background: transparent;
                padding: 20px;
            }
        """)
        self.placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.url_layout.addWidget(self.placeholder_label)
        
        self.scroll_area.setWidget(self.url_container)
        layout.addWidget(self.scroll_area)
    
    def notify_parent(self):
        """Notify parent window of URL changes"""
        if self.parent_window and hasattr(self.parent_window, 'update_url_status'):
            self.parent_window.update_url_status()
        # Also trigger auto-save when URLs change
        if self.parent_window and hasattr(self.parent_window, 'auto_save_settings'):
            self.parent_window.auto_save_settings()
    
    def add_urls_from_text(self, text):
        """Add URLs from text (one per line)"""
        lines = text.strip().split('\n')
        new_urls = []
        invalid_urls = []
        problematic_urls = []
        duplicate_urls = []
        
        for line in lines:
            url = line.strip()
            # Accept http/https URLs and data: URLs (base64 images)
            if url and (url.startswith(('http://', 'https://')) or url.startswith('data:image/')):
                if url not in [u['url'] for u in self.urls]:  # Avoid duplicates
                    # Check for problematic URLs
                    if ('facebook.com/people/' in url and 'pfbid' in url) or 'facebook.com/share/' in url:
                        problematic_urls.append(url)
                    else:
                        new_urls.append(url)
                else:
                    duplicate_urls.append(url)
            elif url:  # Non-empty but invalid URL
                invalid_urls.append(url)
        
        # Log duplicates if any
        if duplicate_urls and self.parent_window:
            for dup_url in duplicate_urls:
                self.parent_window.multi_log(f"[SKIP] Skipped duplicate: {dup_url[:50]}...")
        
        if new_urls:
            self.placeholder_label.hide()
            for url in new_urls:
                self.add_url_checkbox(url)
        
        # Add problematic URLs but warn about them
        if problematic_urls:
            self.placeholder_label.hide()
            for url in problematic_urls:
                self.add_url_checkbox(url, is_problematic=True)
        
        self.notify_parent()
        return len(new_urls), len(invalid_urls), len(problematic_urls)
    
    def add_url_checkbox(self, url, is_problematic=False):
        """Add a single URL with checkbox"""
        url_frame = QFrame()
        
        # Different styling for problematic URLs
        if is_problematic:
            url_frame.setStyleSheet("""
                QFrame {
                    background: rgba(248, 81, 73, 0.1);
                    border: 1px solid #f85149;
                    border-radius: 4px;
                    margin: 1px;
                }
                QFrame:hover {
                    border-color: #ff6b6b;
                    background: rgba(248, 81, 73, 0.2);
                }
            """)
        else:
            url_frame.setStyleSheet("""
                QFrame {
                    background: rgba(33, 38, 45, 0.5);
                    border: 1px solid #30363d;
                    border-radius: 4px;
                    margin: 1px;
                }
                QFrame:hover {
                    border-color: #58a6ff;
                    background: rgba(88, 166, 255, 0.1);
                }
            """)
        
        url_layout = QHBoxLayout(url_frame)
        url_layout.setContentsMargins(8, 4, 8, 4)
        url_layout.setSpacing(8)
        
        # Checkbox
        checkbox = QCheckBox()
        checkbox.setChecked(True)  # Default to checked
        checkbox.toggled.connect(self.notify_parent)  # Update status when checkbox changes
        checkbox.setStyleSheet("""
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 2px solid #30363d;
                border-radius: 3px;
                background: #21262d;
            }
            QCheckBox::indicator:hover {
                border-color: #58a6ff;
            }
            QCheckBox::indicator:checked {
                background: #58a6ff;
                border-color: #58a6ff;
            }
        """)
        
        # URL label (truncated)
        url_display = url[:80] + "..." if len(url) > 80 else url
        if is_problematic:
            url_display = "[!] " + url_display
        
        url_label = QLabel(url_display)
        url_label.setStyleSheet(f"""
            QLabel {{
                color: {'#f85149' if is_problematic else '#f0f6fc'};
                font-size: 11px;
                border: none;
                background: transparent;
            }}
        """)
        
        # Set tooltip with warning for problematic URLs
        if is_problematic:
            url_label.setToolTip(f"[!] Problematic URL: {url}\n\nThis URL type may not work. Consider using direct video URLs instead.")
        else:
            url_label.setToolTip(url)  # Full URL on hover
        
        # Remove button
        remove_btn = QPushButton("X")
        remove_btn.setFixedSize(20, 20)
        remove_btn.setStyleSheet("""
            QPushButton {
                background: #e74c3c;
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #c0392b;
            }
        """)
        remove_btn.clicked.connect(lambda: self.remove_url_item(url_frame, url))
        
        url_layout.addWidget(checkbox)
        url_layout.addWidget(url_label, 1)  # Stretch to fill space
        url_layout.addWidget(remove_btn)
        
        # Store URL data
        url_data = {
            'url': url,
            'checkbox': checkbox,
            'frame': url_frame,
            'is_problematic': is_problematic
        }
        self.urls.append(url_data)
        
        # Add to layout
        self.url_layout.addWidget(url_frame)
    
    def remove_url_item(self, frame, url):
        """Remove a URL item"""
        # Remove from layout and delete widget
        self.url_layout.removeWidget(frame)
        frame.deleteLater()
        
        # Remove from urls list
        self.urls = [u for u in self.urls if u['url'] != url]
        
        # Show placeholder if no URLs left
        if not self.urls:
            self.placeholder_label.show()
        
        self.notify_parent()
    
    def get_selected_urls(self):
        """Get list of selected (checked) URLs"""
        return [u['url'] for u in self.urls if u['checkbox'].isChecked()]
    
    def get_all_urls(self):
        """Get all URLs regardless of selection"""
        return [u['url'] for u in self.urls]
    
    def clear_all(self):
        """Clear all URLs"""
        for url_data in self.urls:
            url_data['frame'].deleteLater()
        self.urls.clear()
        self.placeholder_label.show()
        self.notify_parent()
    
    def select_all(self, checked=True):
        """Select or deselect all URLs"""
        for url_data in self.urls:
            url_data['checkbox'].setChecked(checked)
        self.notify_parent()


class MultipleVideoInfoDialog(QDialog):
    def __init__(self, parent, video_data_list):
        super().__init__(parent)
        self.video_data_list = video_data_list
        self.setup_dialog()
    
    def setup_dialog(self):
        self.setWindowTitle("Multiple Videos Information")
        self.setFixedSize(600, 500)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint)
        
        # Apply modern dark theme styling
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1e1e2e, stop:1 #11111b);
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 16px;
            }
            QLabel {
                color: #cdd6f4;
                font-size: 12px;
                border: none;
                background: transparent;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title with icon
        title_layout = QHBoxLayout()
        
        info_icon = QLabel("[i]")
        info_icon.setStyleSheet("font-size: 24px; border: none; background: transparent;")
        
        title_label = QLabel(f"Information for {len(self.video_data_list)} Videos")
        title_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #58a6ff; font-size: 14px; border: none; background: transparent;")
        
        title_layout.addWidget(info_icon)
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        
        layout.addLayout(title_layout)
        
        # Scrollable content for multiple videos
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                background: #21262d;
                border: 1px solid #30363d;
                border-radius: 8px;
            }
            QScrollBar:vertical {
                background: #161b22;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background: #30363d;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #58a6ff;
            }
        """)
        
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(15)
        
        # Add each video's info
        for i, video_data in enumerate(self.video_data_list, 1):
            video_frame = self.create_video_info_frame(i, video_data)
            content_layout.addWidget(video_frame)
        
        scroll.setWidget(content_widget)
        layout.addWidget(scroll)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        copy_all_btn = QPushButton("Copy All Info")
        copy_all_btn.clicked.connect(self.copy_all_info)
        self.style_button_secondary(copy_all_btn)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        self.style_button_primary(close_btn)
        
        button_layout.addStretch()
        button_layout.addWidget(copy_all_btn)
        button_layout.addSpacing(10)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
    
    def create_video_info_frame(self, index, video_data):
        """Create a frame for individual video info"""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background: rgba(33, 38, 45, 0.5);
                border: 1px solid #30363d;
                border-radius: 8px;
                padding: 12px;
                margin: 2px;
            }
        """)
        
        layout = QVBoxLayout(frame)
        layout.setSpacing(8)
        
        # Video number and status
        header_layout = QHBoxLayout()
        
        if video_data.get('error'):
            status_icon = "[X]"
            status_color = "#f85149"
            video_title = f"Video {index} - Error"
        else:
            status_icon = "[OK]"
            status_color = "#2ea043"
            video_title = f"Video {index} - {video_data.get('title', 'Unknown')[:40]}..."
        
        status_label = QLabel(f"{status_icon} {video_title}")
        status_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        status_label.setStyleSheet(f"color: {status_color}; border: none; background: transparent;")
        
        header_layout.addWidget(status_label)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Video details or error message
        if video_data.get('error'):
            error_msg = video_data.get('message', 'Unknown error')
            error_label = QLabel(f"Error: {error_msg}")
            error_label.setStyleSheet("color: #f85149; font-size: 11px; border: none; background: transparent;")
            error_label.setWordWrap(True)
            layout.addWidget(error_label)
            
            # Add URL for reference
            url_label = QLabel(f"URL: {video_data.get('url', 'Unknown')}")
            url_label.setStyleSheet("color: #7d8590; font-size: 10px; border: none; background: transparent;")
            url_label.setWordWrap(True)
            layout.addWidget(url_label)
        else:
            # Format duration
            dur = video_data.get('duration', 0)
            dur_str = f"{int(dur)//60}:{int(dur)%60:02d}" if dur else "Unknown"
            
            # Format views
            views = video_data.get('views', 0)
            if views >= 1e6:
                views_str = f"{views/1e6:.1f}M"
            elif views >= 1e3:
                views_str = f"{views/1e3:.1f}K"
            else:
                views_str = str(views) if views > 0 else "Unknown"
            
            # Create compact info layout
            info_grid = QGridLayout()
            info_grid.setSpacing(5)
            
            info_items = [
                ("Platform:", video_data.get('platform', 'Unknown')),
                ("Duration:", dur_str),
                ("Uploader:", video_data.get('uploader', 'Unknown')),
                ("Views:", views_str)
            ]
            
            for row, (label, value) in enumerate(info_items):
                label_widget = QLabel(label)
                label_widget.setStyleSheet("color: #58a6ff; font-size: 10px; font-weight: bold; border: none; background: transparent;")
                
                value_widget = QLabel(value)
                value_widget.setStyleSheet("color: #f0f6fc; font-size: 10px; border: none; background: transparent;")
                
                info_grid.addWidget(label_widget, row // 2, (row % 2) * 2)
                info_grid.addWidget(value_widget, row // 2, (row % 2) * 2 + 1)
            
            layout.addLayout(info_grid)
        
        return frame
    
    def copy_all_info(self):
        """Copy all video info to clipboard"""
        info_text = f"Multiple Videos Information ({len(self.video_data_list)} videos):\n\n"
        
        for i, video_data in enumerate(self.video_data_list, 1):
            info_text += f"=== Video {i} ===\n"
            
            if video_data.get('error'):
                info_text += f"Status: Error\n"
                info_text += f"Error: {video_data.get('message', 'Unknown error')}\n"
                info_text += f"URL: {video_data.get('url', 'Unknown')}\n"
            else:
                dur = video_data.get('duration', 0)
                dur_str = f"{int(dur)//60}:{int(dur)%60:02d}" if dur else "Unknown"
                
                views = video_data.get('views', 0)
                if views >= 1e6:
                    views_str = f"{views/1e6:.1f}M"
                elif views >= 1e3:
                    views_str = f"{views/1e3:.1f}K"
                else:
                    views_str = str(views) if views > 0 else "Unknown"
                
                info_text += f"Title: {video_data.get('title', 'Unknown')}\n"
                info_text += f"Uploader: {video_data.get('uploader', 'Unknown')}\n"
                info_text += f"Platform: {video_data.get('platform', 'Unknown')}\n"
                info_text += f"Duration: {dur_str}\n"
                info_text += f"Views: {views_str}\n"
            
            info_text += "\n"
        
        QApplication.clipboard().setText(info_text)
        
        # Show brief confirmation
        self.sender().setText("Copied!")
        QTimer.singleShot(1500, lambda: self.sender().setText("Copy All Info"))
    
    def style_button_primary(self, btn):
        btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #6366f1, stop:1 #4f46e5);
                color: white;
                border: none;
                border-radius: 0px;
                font-size: 13px;
                font-weight: bold;
                padding: 10px 20px;
                min-width: 80px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #818cf8, stop:1 #6366f1);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #4f46e5, stop:1 #4338ca);
            }
        """)
    
    def style_button_secondary(self, btn):
        btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #374151, stop:1 #1f2937);
                color: #e5e7eb;
                border: 1px solid #4b5563;
                border-radius: 0px;
                font-size: 12px;
                font-weight: 600;
                padding: 10px 20px;
                min-width: 100px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #4b5563, stop:1 #374151);
                border-color: #6366f1;
                color: #f3f4f6;
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1f2937, stop:1 #111827);
            }
        """)


class MultipleProgressDialog(QDialog):
    def __init__(self, parent, total_videos):
        super().__init__(parent)
        self.total_videos = total_videos
        self.current_video = 0
        self.setup_dialog()
    
    def setup_dialog(self):
        self.setWindowTitle("Multiple Downloads Progress")
        self.setFixedSize(500, 180)  # Wider dialog, shorter height
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint)
        
        # Apply dark theme styling
        self.setStyleSheet("""
            QDialog {
                background: #161b22;
                color: #f0f6fc;
                border: 2px solid #30363d;
                border-radius: 12px;
            }
            QLabel {
                color: #f0f6fc;
                font-size: 13px;
                border: none;
                background: transparent;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(25, 25, 25, 25)
        
        # Title with icon
        title_layout = QHBoxLayout()
        
        title_icon = QLabel("[v]")
        title_icon.setStyleSheet("font-size: 20px; border: none; background: transparent;")
        
        title_label = QLabel(f"Downloading {self.total_videos} Videos")
        title_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #58a6ff; font-size: 12px; border: none; background: transparent;")
        
        title_layout.addWidget(title_icon)
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        
        layout.addLayout(title_layout)
        
        # Current video status - more concise
        self.video_status_label = QLabel("Preparing downloads...")
        self.video_status_label.setStyleSheet("color: #f0f6fc; font-size: 12px; border: none; background: transparent;")
        self.video_status_label.setWordWrap(True)  # Allow text wrapping
        layout.addWidget(self.video_status_label)
        
        # Single progress bar - overall progress only
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(24)  # Taller for better visibility
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background: #21262d;
                border: 1px solid #30363d;
                border-radius: 12px;
                text-align: center;
                font-size: 12px;
                font-weight: bold;
                color: #f0f6fc;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #238636, stop:1 #2ea043);
                border-radius: 11px;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.pause_btn = QPushButton("Pause")
        self.pause_btn.clicked.connect(self.toggle_pause)
        self.pause_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 193, 7, 0.8);
                color: #000;
                border: none;
                border-radius: 6px;
                font-size: 11px;
                font-weight: bold;
                padding: 6px 12px;
                min-width: 60px;
            }
            QPushButton:hover {
                background: rgba(255, 193, 7, 1.0);
            }
        """)
        
        self.cancel_btn = QPushButton("Stop")
        self.cancel_btn.clicked.connect(self.cancel_operation)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background: rgba(248, 81, 73, 0.8);
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 11px;
                font-weight: bold;
                padding: 6px 12px;
                min-width: 60px;
            }
            QPushButton:hover {
                background: rgba(248, 81, 73, 1.0);
            }
        """)
        
        button_layout.addWidget(self.pause_btn)
        button_layout.addSpacing(10)
        button_layout.addWidget(self.cancel_btn)
        layout.addLayout(button_layout)
        
        # Track states
        self.cancelled = False
        self.paused = False
    
    def update_progress(self, completed, total, current_video_name=""):
        """Update progress based on completed videos"""
        percentage = (completed / total) * 100 if total > 0 else 0
        self.progress_bar.setValue(int(percentage))
        self.progress_bar.setFormat(f"{completed}/{total} videos ({int(percentage)}%)")
        
        # Update status message
        if completed >= total:
            self.video_status_label.setText("All downloads completed!")
            # Auto-close after 2 seconds
            QTimer.singleShot(2000, self.accept)
        elif current_video_name:
            # Truncate long video names
            short_name = current_video_name[:60] + "..." if len(current_video_name) > 60 else current_video_name
            self.video_status_label.setText(f"Video {completed + 1}/{total}: {short_name}")
    
    def update_current_progress(self, percentage, message=""):
        """Update current video progress - simplified to just update status"""
        if message and "Video" in message:
            # Extract video info from message if available
            pass  # We'll handle this in update_progress instead
    
    def start_video(self, index, url):
        """Called when a new video starts downloading"""
        self.current_video = index + 1
        # Extract a cleaner name from URL
        video_name = url.split('/')[-1] if '/' in url else url
        self.update_progress(index, self.total_videos, video_name)
    
    def complete_video(self, index, success):
        """Called when a video completes"""
        completed = index + 1
        self.update_progress(completed, self.total_videos)
    
    def toggle_pause(self):
        """Toggle pause/resume"""
        self.paused = not self.paused
        if self.paused:
            self.pause_btn.setText("Resume")
            self.video_status_label.setText("Downloads paused...")
        else:
            self.pause_btn.setText("Pause")
    
    def cancel_operation(self):
        """Handle cancel button click"""
        self.cancelled = True
        self.reject()
    
    def closeEvent(self, event):
        """Handle dialog close event"""
        self.cancelled = True
        event.accept()


class ProgressDialog(QDialog):
    def __init__(self, parent, title="Processing", operation_type="download"):
        super().__init__(parent)
        self.operation_type = operation_type
        self.setup_dialog(title)
    
    def setup_dialog(self, title):
        self.setWindowTitle(title)
        self.setFixedSize(400, 180)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint)
        
        # Apply dark theme styling
        self.setStyleSheet("""
            QDialog {
                background: #161b22;
                color: #f0f6fc;
                border: 2px solid #30363d;
                border-radius: 12px;
            }
            QLabel {
                color: #f0f6fc;
                font-size: 13px;
                border: none;
                background: transparent;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title with icon
        title_layout = QHBoxLayout()
        
        if self.operation_type == "info":
            icon = "[i]"
            title_text = "Getting Video Information"
        else:
            icon = "[v]"
            title_text = "Downloading Video"
        
        title_icon = QLabel(icon)
        title_icon.setStyleSheet("font-size: 18px; border: none; background: transparent;")
        
        title_label = QLabel(title_text)
        title_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #58a6ff; font-size: 12px; border: none; background: transparent;")
        
        title_layout.addWidget(title_icon)
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        
        layout.addLayout(title_layout)
        
        # Status message
        self.status_label = QLabel("Initializing...")
        self.status_label.setStyleSheet("color: #f0f6fc; font-size: 11px; border: none; background: transparent;")
        layout.addWidget(self.status_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(20)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background: #21262d;
                border: 1px solid #30363d;
                border-radius: 10px;
                text-align: center;
                font-size: 11px;
                font-weight: bold;
                color: #f0f6fc;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #238636, stop:1 #2ea043);
                border-radius: 9px;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        # Cancel button
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.cancel_operation)
        self.cancel_btn.setFixedHeight(28)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background: rgba(248, 81, 73, 0.8);
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 11px;
                font-weight: bold;
                padding: 6px 16px;
                min-width: 70px;
            }
            QPushButton:hover {
                background: rgba(248, 81, 73, 1.0);
            }
            QPushButton:pressed {
                background: rgba(220, 53, 69, 1.0);
            }
        """)
        
        button_layout.addWidget(self.cancel_btn)
        layout.addLayout(button_layout)
        
        # Track if operation was cancelled
        self.cancelled = False
    
    def update_progress(self, percentage, message=""):
        """Update progress bar and status message"""
        self.progress_bar.setValue(int(percentage))
        if message:
            self.status_label.setText(message)
        
        # Update progress bar format
        self.progress_bar.setFormat(f"{int(percentage)}%")
        
        # Auto-close when complete
        if percentage >= 100:
            QTimer.singleShot(1000, self.accept)  # Close after 1 second
    
    def cancel_operation(self):
        """Handle cancel button click"""
        self.cancelled = True
        self.reject()
    
    def closeEvent(self, event):
        """Handle dialog close event"""
        self.cancelled = True
        event.accept()


class VideoInfoDialog(QDialog):
    def __init__(self, parent, video_data):
        super().__init__(parent)
        self.video_data = video_data
        self.setup_dialog()
    
    def setup_dialog(self):
        self.setWindowTitle("Video Information")
        self.setFixedSize(450, 300)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint)
        
        # Apply dark theme styling
        self.setStyleSheet("""
            QDialog {
                background: #161b22;
                color: #f0f6fc;
                border: 2px solid #30363d;
                border-radius: 12px;
            }
            QLabel {
                color: #f0f6fc;
                font-size: 13px;
                border: none;
                background: transparent;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(25, 25, 25, 25)
        
        # Title with icon
        title_layout = QHBoxLayout()
        
        info_icon = QLabel("[i]")
        info_icon.setStyleSheet("font-size: 24px; border: none; background: transparent;")
        
        title_label = QLabel("Video Information")
        title_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #58a6ff; font-size: 14px; border: none; background: transparent;")
        
        title_layout.addWidget(info_icon)
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        
        layout.addLayout(title_layout)
        
        # Video information content
        info_frame = QFrame()
        info_frame.setStyleSheet("""
            QFrame {
                background: #21262d;
                border: 1px solid #30363d;
                border-radius: 8px;
                padding: 15px;
            }
        """)
        info_layout = QVBoxLayout(info_frame)
        info_layout.setSpacing(12)
        
        # Format duration
        dur = self.video_data.get('duration', 0)
        if dur:
            dur = int(dur)
            dur_str = f"{dur//60}:{dur%60:02d}"
        else:
            dur_str = "Unknown"
        
        # Format views
        views = self.video_data.get('views', 0)
        if views >= 1e6:
            views_str = f"{views/1e6:.1f}M"
        elif views >= 1e3:
            views_str = f"{views/1e3:.1f}K"
        else:
            views_str = str(views) if views > 0 else "Unknown"
        
        # Create info labels
        info_items = [
            ("Title:", self.video_data.get('title', 'Unknown')),
            ("Uploader:", self.video_data.get('uploader', 'Unknown')),
            ("Platform:", self.video_data.get('platform', 'Unknown')),
            ("Duration:", dur_str),
            ("Views:", views_str)
        ]
        
        for label, value in info_items:
            item_layout = QHBoxLayout()
            
            label_widget = QLabel(label)
            label_widget.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
            label_widget.setStyleSheet("color: #58a6ff; min-width: 100px;")
            label_widget.setFixedWidth(100)
            
            value_widget = QLabel(value)
            value_widget.setFont(QFont("Segoe UI", 11))
            value_widget.setStyleSheet("color: #f0f6fc;")
            value_widget.setWordWrap(True)
            
            item_layout.addWidget(label_widget)
            item_layout.addWidget(value_widget, 1)
            
            info_layout.addLayout(item_layout)
        
        layout.addWidget(info_frame)
        layout.addStretch()
        
        # Buttons
        button_layout = QHBoxLayout()
        
        copy_btn = QPushButton("Copy Info")
        copy_btn.clicked.connect(self.copy_info)
        self.style_button_secondary(copy_btn)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        self.style_button_primary(close_btn)
        
        button_layout.addStretch()
        button_layout.addWidget(copy_btn)
        button_layout.addSpacing(10)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
    
    def copy_info(self):
        """Copy video info to clipboard"""
        dur = self.video_data.get('duration', 0)
        dur_str = f"{int(dur)//60}:{int(dur)%60:02d}" if dur else "Unknown"
        
        views = self.video_data.get('views', 0)
        if views >= 1e6:
            views_str = f"{views/1e6:.1f}M"
        elif views >= 1e3:
            views_str = f"{views/1e3:.1f}K"
        else:
            views_str = str(views) if views > 0 else "Unknown"
        
        info_text = f"""Video Information:
Title: {self.video_data.get('title', 'Unknown')}
Uploader: {self.video_data.get('uploader', 'Unknown')}
Platform: {self.video_data.get('platform', 'Unknown')}
Duration: {dur_str}
Views: {views_str}"""
        
        QApplication.clipboard().setText(info_text)
        
        # Show brief confirmation
        self.sender().setText("Copied!")
        QTimer.singleShot(1500, lambda: self.sender().setText("Copy Info"))
    
    def style_button_primary(self, btn):
        btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #6366f1, stop:1 #4f46e5);
                color: white;
                border: none;
                border-radius: 0px;
                font-size: 13px;
                font-weight: bold;
                padding: 10px 20px;
                min-width: 80px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #818cf8, stop:1 #6366f1);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #4f46e5, stop:1 #4338ca);
            }
        """)
    
    def style_button_secondary(self, btn):
        btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #374151, stop:1 #1f2937);
                color: #e5e7eb;
                border: 1px solid #4b5563;
                border-radius: 0px;
                font-size: 12px;
                font-weight: 600;
                padding: 10px 20px;
                min-width: 80px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #4b5563, stop:1 #374151);
                border-color: #6366f1;
                color: #f3f4f6;
            }
            QPushButton:pressed {
                background: rgba(88, 166, 255, 0.1);
            }
        """)


class SuccessDialog(QDialog):
    def __init__(self, parent, message, file_path=None):
        super().__init__(parent)
        self.file_path = file_path
        self.setup_dialog(message)
    
    def setup_dialog(self, message):
        self.setWindowTitle("Download Complete")
        self.setFixedSize(400, 200)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint)
        
        # Apply dark theme styling
        self.setStyleSheet("""
            QDialog {
                background: #161b22;
                color: #f0f6fc;
                border: 2px solid #30363d;
                border-radius: 12px;
            }
            QLabel {
                color: #f0f6fc;
                font-size: 13px;
                border: none;
                background: transparent;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(25, 25, 25, 25)
        
        # Success icon and title
        title_layout = QHBoxLayout()
        
        success_icon = QLabel("[OK]")
        success_icon.setStyleSheet("font-size: 24px; border: none; background: transparent;")
        
        title_label = QLabel("Download Successful!")
        title_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #2ea043; font-size: 14px; border: none; background: transparent;")
        
        title_layout.addWidget(success_icon)
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        
        layout.addLayout(title_layout)
        
        # Message
        msg_label = QLabel(message)
        msg_label.setWordWrap(True)
        msg_label.setStyleSheet("color: #f0f6fc; font-size: 12px; border: none; background: transparent;")
        layout.addWidget(msg_label)
        
        layout.addStretch()
        
        # Buttons
        button_layout = QHBoxLayout()
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.reject)
        self.style_button_secondary(close_btn)
        
        view_btn = QPushButton("View Video")
        view_btn.clicked.connect(self.view_video)
        self.style_button_primary(view_btn)
        
        button_layout.addStretch()
        button_layout.addWidget(close_btn)
        button_layout.addSpacing(10)
        button_layout.addWidget(view_btn)
        
        layout.addLayout(button_layout)
    
    def style_button_primary(self, btn):
        btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #238636, stop:1 #2ea043);
                color: white;
                border: none;
                border-radius: 0px;
                font-size: 13px;
                font-weight: bold;
                padding: 8px 16px;
                min-width: 100px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2ea043, stop:1 #238636);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1e6f2f, stop:1 #238636);
            }
        """)
    
    def style_button_secondary(self, btn):
        btn.setStyleSheet("""
            QPushButton {
                background: rgba(33, 38, 45, 0.8);
                color: #f0f6fc;
                border: 2px solid #30363d;
                border-radius: 0px;
                font-size: 12px;
                font-weight: bold;
                padding: 8px 16px;
                min-width: 80px;
            }
            QPushButton:hover {
                border-color: #58a6ff;
                background: rgba(22, 27, 34, 0.9);
                color: #58a6ff;
            }
            QPushButton:pressed {
                background: rgba(88, 166, 255, 0.1);
            }
        """)
    
    def view_video(self):
        """Open file explorer and navigate to the downloaded video"""
        if self.file_path and Path(self.file_path).exists():
            import subprocess
            import platform
            
            try:
                system = platform.system()
                if system == "Windows":
                    # Use explorer with /select to highlight the file
                    subprocess.run(['explorer', '/select,', str(self.file_path)])
                elif system == "Darwin":  # macOS
                    subprocess.run(['open', '-R', str(self.file_path)])
                else:  # Linux
                    # Open the directory containing the file
                    subprocess.run(['xdg-open', str(Path(self.file_path).parent)])
                
                self.accept()  # Close dialog after opening
                
            except Exception as e:
                # Fallback: just open the directory
                try:
                    directory = Path(self.file_path).parent
                    if system == "Windows":
                        subprocess.run(['explorer', str(directory)])
                    elif system == "Darwin":
                        subprocess.run(['open', str(directory)])
                    else:
                        subprocess.run(['xdg-open', str(directory)])
                    self.accept()
                except:
                    # If all else fails, just close the dialog
                    QMessageBox.warning(self, "Error", f"Could not open file location: {e}")
        else:
            QMessageBox.warning(self, "Error", "Video file not found or path not available")


class ProfileInfoDialog(QDialog):
    """Simple clean dialog to display profile information"""
    def __init__(self, parent, profile_data):
        super().__init__(parent)
        self.profile_data = profile_data
        self.setup_dialog()
    
    def setup_dialog(self):
        self.setWindowTitle("Profile Information")
        self.setFixedSize(420, 380)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint)
        
        self.setStyleSheet("""
            QDialog {
                background: #161b22;
                color: #f0f6fc;
            }
            QLabel { color: #f0f6fc; background: transparent; border: none; }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header = QLabel("[OK] Profile Found")
        header.setStyleSheet("color: #3fb950; font-size: 18px; font-weight: bold;")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)
        
        # Info frame
        info_frame = QFrame()
        info_frame.setStyleSheet("""
            QFrame {
                background: #21262d;
                border: 1px solid #30363d;
                border-radius: 8px;
            }
        """)
        info_layout = QVBoxLayout(info_frame)
        info_layout.setSpacing(8)
        info_layout.setContentsMargins(15, 15, 15, 15)
        
        profile_name = self.profile_data.get('profile_name', 'Unknown')
        platform = self.profile_data.get('platform', 'Unknown')
        total_videos = self.profile_data.get('total_found', 0)
        
        # Simple info rows
        info_layout.addWidget(self.create_info_row("Profile", profile_name))
        info_layout.addWidget(self.create_info_row("Platform", platform))
        info_layout.addWidget(self.create_info_row("Videos", str(total_videos)))
        
        layout.addWidget(info_frame)
        
        # Video list
        list_label = QLabel(f"Video List ({total_videos})")
        list_label.setStyleSheet("color: #8b949e; font-size: 11px;")
        layout.addWidget(list_label)
        
        self.videos_text = QTextEdit()
        self.videos_text.setReadOnly(True)
        self.videos_text.setStyleSheet("""
            QTextEdit {
                background: #0d1117;
                color: #c9d1d9;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 8px;
                font-size: 11px;
            }
        """)
        
        videos = self.profile_data.get('videos', [])
        for i, video in enumerate(videos[:30], 1):
            title = video.get('title', 'Unknown')[:50]
            self.videos_text.append(f"{i}. {title}")
        if len(videos) > 30:
            self.videos_text.append(f"... +{len(videos) - 30} more")
        
        layout.addWidget(self.videos_text)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.setFixedHeight(36)
        close_btn.clicked.connect(self.accept)
        close_btn.setStyleSheet("""
            QPushButton {
                background: #238636;
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover { background: #2ea043; }
        """)
        layout.addWidget(close_btn)
    
    def create_info_row(self, label, value):
        row = QFrame()
        row.setStyleSheet("background: transparent; border: none;")
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        
        lbl = QLabel(label)
        lbl.setStyleSheet("color: #8b949e; font-size: 12px;")
        lbl.setFixedWidth(90)
        
        val = QLabel(value)
        val.setStyleSheet("color: #f0f6fc; font-size: 12px; font-weight: bold;")
        val.setWordWrap(True)
        
        row_layout.addWidget(lbl)
        row_layout.addWidget(val, 1)
        return row


class ProfileDownloadDialog(QDialog):
    def __init__(self, parent, profile_info):
        super().__init__(parent)
        self.profile_info = profile_info
        self.selected_videos = []
        self.setup_dialog()
    
    def setup_dialog(self):
        self.setWindowTitle("Profile Video Download")
        self.setFixedSize(600, 500)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint)
        
        # Apply dark theme styling
        self.setStyleSheet("""
            QDialog {
                background: #161b22;
                color: #f0f6fc;
                border: 2px solid #30363d;
                border-radius: 12px;
            }
            QLabel {
                color: #f0f6fc;
                font-size: 12px;
                border: none;
                background: transparent;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(25, 25, 25, 25)
        
        # Header with profile info
        header_layout = QHBoxLayout()
        
        profile_icon = QLabel("[P]")
        profile_icon.setStyleSheet("font-size: 24px; border: none; background: transparent;")
        
        profile_info_layout = QVBoxLayout()
        profile_info_layout.setSpacing(4)
        
        profile_name = QLabel(f"Profile: {self.profile_info.get('profile_name', 'Unknown')}")
        profile_name.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        profile_name.setStyleSheet("color: #58a6ff; font-size: 13px; font-weight: bold;")
        
        video_count = QLabel(f"Found {self.profile_info.get('total_found', 0)} videos on {self.profile_info.get('platform', 'Unknown')}")
        video_count.setStyleSheet("color: #7d8590; font-size: 11px;")
        
        profile_info_layout.addWidget(profile_name)
        profile_info_layout.addWidget(video_count)
        
        header_layout.addWidget(profile_icon)
        header_layout.addLayout(profile_info_layout)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Download options
        options_frame = QFrame()
        options_frame.setStyleSheet("""
            QFrame {
                background: rgba(33, 38, 45, 0.6);
                border: 1px solid #30363d;
                border-radius: 8px;
                padding: 15px;
            }
        """)
        
        options_layout = QVBoxLayout(options_frame)
        options_layout.setSpacing(10)
        
        # Max videos setting
        max_videos_layout = QHBoxLayout()
        max_videos_label = QLabel("Maximum videos to download:")
        max_videos_label.setStyleSheet("color: #f0f6fc; font-size: 11px; font-weight: bold;")
        
        self.max_videos_spin = QComboBox()
        
        # Adjust options based on how many videos were found
        total_found = self.profile_info.get('total_found', 0)
        raw_total = self.profile_info.get('raw_total', total_found)
        
        options = ["10", "25", "50", "100", "200"]
        
        # Add the exact number found if it's not in our standard options
        if total_found > 0 and str(total_found) not in options:
            options.append(str(total_found))
        
        # Add "All available" option
        if total_found > 0:
            options.append(f"All available ({total_found})")
        else:
            options.append("All available")
        
        self.max_videos_spin.addItems(options)
        
        # Set default selection based on videos found
        if total_found <= 25:
            self.max_videos_spin.setCurrentText(f"All available ({total_found})" if total_found > 0 else "All available")
        elif total_found <= 50:
            self.max_videos_spin.setCurrentText("50")
        else:
            self.max_videos_spin.setCurrentText("100")
        
        self.max_videos_spin.setStyleSheet("""
            QComboBox {
                background: #21262d;
                color: #f0f6fc;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 6px;
                font-size: 11px;
                min-width: 150px;
            }
            QComboBox:hover {
                border-color: #58a6ff;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #7d8590;
                margin-right: 5px;
            }
        """)
        
        max_videos_layout.addWidget(max_videos_label)
        max_videos_layout.addWidget(self.max_videos_spin)
        max_videos_layout.addStretch()
        
        # Sort order
        sort_layout = QHBoxLayout()
        sort_label = QLabel("Download order:")
        sort_label.setStyleSheet("color: #f0f6fc; font-size: 11px; font-weight: bold;")
        
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["Newest first", "Oldest first", "Most popular"])
        self.sort_combo.setStyleSheet(self.max_videos_spin.styleSheet())
        
        sort_layout.addWidget(sort_label)
        sort_layout.addWidget(self.sort_combo)
        sort_layout.addStretch()
        
        options_layout.addLayout(max_videos_layout)
        options_layout.addLayout(sort_layout)
        
        layout.addWidget(options_frame)
        
        # Video preview list
        preview_label = QLabel("Video Preview:")
        preview_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        preview_label.setStyleSheet("color: #58a6ff; font-size: 11px; font-weight: bold;")
        layout.addWidget(preview_label)
        
        # Scrollable video list
        self.video_list = QScrollArea()
        self.video_list.setWidgetResizable(True)
        self.video_list.setFixedHeight(200)
        self.video_list.setStyleSheet("""
            QScrollArea {
                background: #21262d;
                border: 1px solid #30363d;
                border-radius: 6px;
            }
            QScrollBar:vertical {
                background: #161b22;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #30363d;
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #58a6ff;
            }
        """)
        
        self.populate_video_list()
        layout.addWidget(self.video_list)
        
        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        self.style_button_secondary(cancel_btn)
        
        download_btn = QPushButton("Start Download")
        download_btn.clicked.connect(self.accept)
        self.style_button_primary(download_btn)
        
        button_layout.addStretch()
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(download_btn)
        
        layout.addLayout(button_layout)
    
    def populate_video_list(self):
        """Populate the video preview list"""
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setSpacing(4)
        container_layout.setContentsMargins(8, 8, 8, 8)
        
        videos = self.profile_info.get('videos', [])[:10]  # Show first 10 for preview
        
        if not videos:
            no_videos_label = QLabel("No videos found in this profile")
            no_videos_label.setStyleSheet("color: #7d8590; font-style: italic; padding: 20px;")
            no_videos_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            container_layout.addWidget(no_videos_label)
        else:
            for i, video in enumerate(videos):
                video_frame = self.create_video_preview_item(video, i + 1)
                container_layout.addWidget(video_frame)
            
            if len(self.profile_info.get('videos', [])) > 10:
                more_label = QLabel(f"... and {len(self.profile_info.get('videos', [])) - 10} more videos")
                more_label.setStyleSheet("color: #7d8590; font-style: italic; padding: 8px; text-align: center;")
                more_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                container_layout.addWidget(more_label)
        
        self.video_list.setWidget(container)
    
    def create_video_preview_item(self, video, index):
        """Create a preview item for a video"""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background: rgba(33, 38, 45, 0.5);
                border: 1px solid #30363d;
                border-radius: 4px;
                margin: 1px;
                padding: 8px;
            }
            QFrame:hover {
                border-color: #58a6ff;
                background: rgba(88, 166, 255, 0.1);
            }
        """)
        
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(10)
        
        # Video number
        number_label = QLabel(f"{index}.")
        number_label.setStyleSheet("color: #58a6ff; font-weight: bold; font-size: 10px; min-width: 20px;")
        
        # Video info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        
        title = video.get('title', 'Unknown Title')
        if len(title) > 60:
            title = title[:60] + "..."
        
        title_label = QLabel(title)
        title_label.setStyleSheet("color: #f0f6fc; font-size: 10px; font-weight: bold;")
        
        # Duration and uploader
        duration = video.get('duration', 0)
        duration_str = f"{int(duration)//60}:{int(duration)%60:02d}" if duration else "Unknown"
        
        details_label = QLabel(f"Duration: {duration_str} - Uploader: {video.get('uploader', 'Unknown')}")
        details_label.setStyleSheet("color: #7d8590; font-size: 9px;")
        
        info_layout.addWidget(title_label)
        info_layout.addWidget(details_label)
        
        layout.addWidget(number_label)
        layout.addLayout(info_layout, 1)
        
        return frame
    
    def get_download_settings(self):
        """Get the selected download settings"""
        max_videos_text = self.max_videos_spin.currentText()
        
        # Parse the max videos setting
        max_videos = None
        if "All available" in max_videos_text:
            max_videos = None  # No limit
        else:
            try:
                max_videos = int(max_videos_text)
            except ValueError:
                max_videos = None
        
        return {
            'max_videos': max_videos,
            'sort_order': self.sort_combo.currentText(),
            'videos': self.profile_info.get('videos', [])
        }
    
    def style_button_primary(self, btn):
        btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #238636, stop:1 #2ea043);
                color: white;
                border: none;
                border-radius: 0px;
                font-size: 12px;
                font-weight: bold;
                padding: 8px 16px;
                min-width: 120px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #2ea043, stop:1 #238636);
            }
        """)
    
    def style_button_secondary(self, btn):
        btn.setStyleSheet("""
            QPushButton {
                background: rgba(33, 38, 45, 0.8);
                color: #f0f6fc;
                border: 2px solid #30363d;
                border-radius: 0px;
                font-size: 12px;
                font-weight: bold;
                padding: 8px 16px;
                min-width: 80px;
            }
            QPushButton:hover {
                border-color: #58a6ff;
                background: rgba(22, 27, 34, 0.9);
                color: #58a6ff;
            }
        """)


class BatchCompleteDialog(QDialog):
    def __init__(self, parent, summary):
        super().__init__(parent)
        self.summary = summary
        self.parent_window = parent
        self.setup_dialog()
    
    def setup_dialog(self):
        self.setWindowTitle("Batch Download Complete")
        self.setFixedSize(420, 260)  # Smaller size
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint)
        
        # Apply modern dark theme styling
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #1a1d23, stop:1 #161b22);
                color: #f0f6fc;
                border: 2px solid #30363d;
                border-radius: 12px;
            }
            QLabel {
                color: #f0f6fc;
                font-size: 12px;
                border: none;
                background: transparent;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)  # Reduced spacing
        layout.setContentsMargins(20, 20, 20, 20)  # Smaller margins
        
        # Header section with icon and title
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)
        
        # Success icon - smaller
        icon_label = QLabel("[*]")
        icon_label.setStyleSheet("""
            QLabel {
                font-size: 24px;
                border: none;
                background: transparent;
                padding: 4px;
            }
        """)
        
        # Title and subtitle
        title_section = QVBoxLayout()
        title_section.setSpacing(2)
        
        title_label = QLabel("Batch Download Complete")
        title_label.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))  # Smaller font
        title_label.setStyleSheet("""
            QLabel {
                color: #2ea043;
                font-size: 13px;
                font-weight: bold;
                border: none;
                background: transparent;
            }
        """)
        
        completed = self.summary['completed']
        failed = self.summary['failed']
        total = self.summary['total']
        
        subtitle_text = f"Downloaded {completed} of {total} videos successfully"
        if failed > 0:
            subtitle_text = f"Completed with {failed} error{'s' if failed != 1 else ''}"
        
        subtitle_label = QLabel(subtitle_text)
        subtitle_label.setStyleSheet("""
            QLabel {
                color: #7d8590;
                font-size: 11px;
                border: none;
                background: transparent;
            }
        """)
        
        title_section.addWidget(title_label)
        title_section.addWidget(subtitle_label)
        
        header_layout.addWidget(icon_label)
        header_layout.addLayout(title_section)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Stats section with modern cards - more compact
        stats_frame = QFrame()
        stats_frame.setStyleSheet("""
            QFrame {
                background: rgba(33, 38, 45, 0.6);
                border: 1px solid #30363d;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        
        stats_layout = QHBoxLayout(stats_frame)
        stats_layout.setSpacing(15)
        
        # Success card
        success_card = self.create_stat_card("[OK]", str(completed), "Successful", "#2ea043")
        stats_layout.addWidget(success_card)
        
        # Divider
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.VLine)
        divider.setStyleSheet("QFrame { color: #30363d; }")
        stats_layout.addWidget(divider)
        
        # Failed card
        failed_card = self.create_stat_card("[X]", str(failed), "Failed", "#f85149")
        stats_layout.addWidget(failed_card)
        
        layout.addWidget(stats_frame)
        
        # Download location info - more compact
        if self.summary['successful_files']:
            location_frame = QFrame()
            location_frame.setStyleSheet("""
                QFrame {
                    background: rgba(88, 166, 255, 0.1);
                    border: 1px solid rgba(88, 166, 255, 0.3);
                    border-radius: 6px;
                    padding: 8px;
                }
            """)
            
            location_layout = QVBoxLayout(location_frame)
            location_layout.setSpacing(4)
            
            location_title = QLabel("Download Location")
            location_title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            location_title.setStyleSheet("color: #58a6ff; font-size: 10px; font-weight: bold;")
            
            # Get the download directory path
            download_path = str(self.parent_window.dl.output_dir) if hasattr(self.parent_window, 'dl') else "downloads"
            location_path = QLabel(download_path)
            location_path.setStyleSheet("""
                QLabel {
                    color: #f0f6fc;
                    font-size: 10px;
                    font-family: 'Consolas', 'Monaco', monospace;
                    background: rgba(33, 38, 45, 0.5);
                    padding: 3px 6px;
                    border-radius: 3px;
                }
            """)
            location_path.setWordWrap(True)
            
            location_layout.addWidget(location_title)
            location_layout.addWidget(location_path)
            
            layout.addWidget(location_frame)
        
        layout.addStretch()
        
        # Action buttons - smaller
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        self.style_button_secondary(close_btn)
        
        # Open folder button
        open_folder_btn = QPushButton("Open Folder")
        open_folder_btn.clicked.connect(self.open_folder)
        self.style_button_primary(open_folder_btn)
        
        button_layout.addStretch()
        button_layout.addWidget(close_btn)
        button_layout.addWidget(open_folder_btn)
        
        layout.addLayout(button_layout)
    
    def create_stat_card(self, icon, number, label, color):
        """Create a compact stat card"""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background: transparent;
                border: none;
                padding: 6px;
            }}
        """)
        
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(3)
        card_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Icon - smaller
        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 16px; border: none; background: transparent;")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Number - smaller
        number_label = QLabel(number)
        number_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        number_label.setStyleSheet(f"""
            QLabel {{
                color: {color};
                font-size: 14px;
                font-weight: bold;
                border: none;
                background: transparent;
            }}
        """)
        number_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Label - smaller
        text_label = QLabel(label)
        text_label.setStyleSheet("""
            QLabel {
                color: #7d8590;
                font-size: 10px;
                border: none;
                background: transparent;
            }
        """)
        text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        card_layout.addWidget(icon_label)
        card_layout.addWidget(number_label)
        card_layout.addWidget(text_label)
        
        return card
    
    def open_folder(self):
        """Open the downloads folder"""
        if hasattr(self.parent_window, 'open_downloads_folder'):
            self.parent_window.open_downloads_folder()
        self.accept()
    
    def style_button_primary(self, btn):
        btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #238636, stop:1 #2ea043);
                color: white;
                border: none;
                border-radius: 0px;
                font-size: 12px;
                font-weight: bold;
                padding: 8px 16px;
                min-width: 100px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #2ea043, stop:1 #238636);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #1e6f2f, stop:1 #238636);
            }
        """)
    
    def style_button_secondary(self, btn):
        btn.setStyleSheet("""
            QPushButton {
                background: rgba(33, 38, 45, 0.8);
                color: #f0f6fc;
                border: 2px solid #30363d;
                border-radius: 0px;
                font-size: 12px;
                font-weight: bold;
                padding: 8px 16px;
                min-width: 80px;
            }
            QPushButton:hover {
                border-color: #58a6ff;
                background: rgba(22, 27, 34, 0.9);
                color: #58a6ff;
            }
            QPushButton:pressed {
                background: rgba(88, 166, 255, 0.1);
            }
        """)


class ImageDownloadProgressDialog(QDialog):
    """Modern progress dialog for image downloads"""
    def __init__(self, parent, total_images):
        super().__init__(parent)
        self.total_images = total_images
        self.cancelled = False
        self.setup_dialog()
    
    def setup_dialog(self):
        self.setWindowTitle("Downloading Images")
        self.setFixedSize(450, 200)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint)
        
        # Apply dark theme styling
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #1a1d23, stop:1 #161b22);
                color: #f0f6fc;
                border: 2px solid #30363d;
                border-radius: 12px;
            }
            QLabel {
                color: #f0f6fc;
                font-size: 12px;
                border: none;
                background: transparent;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(25, 25, 25, 25)
        
        # Header with icon
        header_layout = QHBoxLayout()
        
        icon_label = QLabel("[IMG]")
        icon_label.setStyleSheet("font-size: 24px; border: none; background: transparent;")
        
        title_label = QLabel("Downloading Images")
        title_label.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #58a6ff; font-size: 13px; font-weight: bold;")
        
        header_layout.addWidget(icon_label)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Status message
        self.status_label = QLabel(f"Preparing to download {self.total_images} images...")
        self.status_label.setStyleSheet("color: #f0f6fc; font-size: 11px;")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        
        # Current URL label
        self.url_label = QLabel("")
        self.url_label.setStyleSheet("""
            color: #7d8590; 
            font-size: 10px; 
            font-family: 'Consolas', monospace;
            background: rgba(33, 38, 45, 0.5);
            padding: 4px 8px;
            border-radius: 4px;
        """)
        self.url_label.setWordWrap(True)
        layout.addWidget(self.url_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, self.total_images)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(22)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background: #21262d;
                border: 1px solid #30363d;
                border-radius: 11px;
                text-align: center;
                font-size: 11px;
                font-weight: bold;
                color: #f0f6fc;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #238636, stop:1 #2ea043);
                border-radius: 10px;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        # Stats row
        self.stats_label = QLabel("0 saved | 0 failed")
        self.stats_label.setStyleSheet("color: #7d8590; font-size: 10px;")
        self.stats_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.stats_label)
        
        # Cancel button
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.cancel_download)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background: rgba(248, 81, 73, 0.8);
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 11px;
                font-weight: bold;
                padding: 6px 20px;
                min-width: 80px;
            }
            QPushButton:hover {
                background: rgba(248, 81, 73, 1.0);
            }
            QPushButton:pressed {
                background: rgba(220, 53, 69, 1.0);
            }
        """)
        
        button_layout.addWidget(self.cancel_btn)
        layout.addLayout(button_layout)
    
    def update_progress(self, current, url, successful, failed):
        """Update progress display"""
        self.progress_bar.setValue(current)
        self.progress_bar.setFormat(f"{current}/{self.total_images}")
        self.status_label.setText(f"Downloading image {current} of {self.total_images}...")
        self.url_label.setText(url[:70] + "..." if len(url) > 70 else url)
        self.stats_label.setText(f"[OK] {successful} saved | [X] {failed} failed")
        QApplication.processEvents()
    
    def cancel_download(self):
        """Handle cancel button click"""
        self.cancelled = True
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setText("Stopping...")
        self.status_label.setText("Stopping download...")
    
    def closeEvent(self, event):
        """Handle dialog close event"""
        self.cancelled = True
        event.accept()


class ImageDownloadCompleteDialog(QDialog):
    """Modern completion dialog for image downloads"""
    def __init__(self, parent, successful, failed, skipped, output_dir, was_cancelled=False):
        super().__init__(parent)
        self.successful = successful
        self.failed = failed
        self.skipped = skipped
        self.output_dir = output_dir
        self.was_cancelled = was_cancelled
        self.setup_dialog()
    
    def setup_dialog(self):
        # Determine title based on results, not just cancelled flag
        if self.was_cancelled and self.successful == 0:
            title = "Download Cancelled"
            icon = "[!]"
            title_text = "Download Cancelled"
            title_color = "#f0883e"
        elif self.successful > 0:
            title = "Download Complete"
            icon = "[OK]"
            title_text = f"Downloaded {self.successful} image{'s' if self.successful != 1 else ''}"
            title_color = "#2ea043"
        elif self.failed > 0:
            title = "Download Failed"
            icon = "[X]"
            title_text = "Download Failed"
            title_color = "#f85149"
        else:
            title = "Download Complete"
            icon = "[OK]"
            title_text = "Download Complete"
            title_color = "#2ea043"
        
        self.setWindowTitle(title)
        self.setFixedSize(420, 240)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint)
        
        # Apply dark theme styling
        self.setStyleSheet("""
            QDialog {
                background: #161b22;
                color: #f0f6fc;
                border: 2px solid #30363d;
                border-radius: 12px;
            }
            QLabel {
                color: #f0f6fc;
                border: none;
                background: transparent;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header with icon
        header_layout = QHBoxLayout()
        
        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 24px;")
        
        title_label = QLabel(title_text)
        title_label.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        title_label.setStyleSheet(f"color: {title_color}; font-size: 13px;")
        
        header_layout.addWidget(icon_label)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # Stats row - horizontal compact layout
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(20)
        
        # Saved
        saved_label = QLabel(f"[OK] {self.successful} Saved")
        saved_label.setStyleSheet("color: #2ea043; font-size: 12px; font-weight: bold;")
        stats_layout.addWidget(saved_label)
        
        # Failed
        failed_label = QLabel(f"[X] {self.failed} Failed")
        failed_label.setStyleSheet("color: #f85149; font-size: 12px; font-weight: bold;")
        stats_layout.addWidget(failed_label)
        
        # Skipped
        skipped_label = QLabel(f"[>>] {self.skipped} Skipped")
        skipped_label.setStyleSheet("color: #7d8590; font-size: 12px; font-weight: bold;")
        stats_layout.addWidget(skipped_label)
        
        stats_layout.addStretch()
        layout.addLayout(stats_layout)
        
        # Output location
        location_frame = QFrame()
        location_frame.setStyleSheet("""
            QFrame {
                background: rgba(88, 166, 255, 0.1);
                border: 1px solid rgba(88, 166, 255, 0.3);
                border-radius: 6px;
                padding: 8px;
            }
        """)
        
        location_layout = QVBoxLayout(location_frame)
        location_layout.setSpacing(2)
        location_layout.setContentsMargins(8, 6, 8, 6)
        
        location_title = QLabel("Output Location")
        location_title.setStyleSheet("color: #58a6ff; font-size: 10px; font-weight: bold;")
        
        location_path = QLabel(self.output_dir)
        location_path.setStyleSheet("""
            color: #f0f6fc;
            font-size: 10px;
            font-family: 'Consolas', monospace;
            background: rgba(33, 38, 45, 0.5);
            padding: 3px 6px;
            border-radius: 3px;
        """)
        location_path.setWordWrap(True)
        
        location_layout.addWidget(location_title)
        location_layout.addWidget(location_path)
        layout.addWidget(location_frame)
        
        layout.addStretch()
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        self.style_button_secondary(close_btn)
        
        open_btn = QPushButton("Open Folder")
        open_btn.clicked.connect(self.open_folder)
        self.style_button_primary(open_btn)
        
        button_layout.addStretch()
        button_layout.addWidget(close_btn)
        button_layout.addWidget(open_btn)
        layout.addLayout(button_layout)
    
    def open_folder(self):
        """Open the output folder"""
        import subprocess
        import platform
        
        try:
            system = platform.system()
            if system == "Windows":
                subprocess.run(['explorer', str(self.output_dir)])
            elif system == "Darwin":
                subprocess.run(['open', str(self.output_dir)])
            else:
                subprocess.run(['xdg-open', str(self.output_dir)])
            self.accept()
        except Exception as e:
            pass
    
    def style_button_primary(self, btn):
        btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #238636, stop:1 #2ea043);
                color: white;
                border: none;
                border-radius: 0px;
                font-size: 12px;
                font-weight: bold;
                padding: 8px 16px;
                min-width: 100px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #2ea043, stop:1 #238636);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #1e6f2f, stop:1 #238636);
            }
        """)
    
    def style_button_secondary(self, btn):
        btn.setStyleSheet("""
            QPushButton {
                background: rgba(33, 38, 45, 0.8);
                color: #f0f6fc;
                border: 2px solid #30363d;
                border-radius: 0px;
                font-size: 12px;
                font-weight: bold;
                padding: 8px 16px;
                min-width: 80px;
            }
            QPushButton:hover {
                border-color: #58a6ff;
                background: rgba(22, 27, 34, 0.9);
                color: #58a6ff;
            }
            QPushButton:pressed {
                background: rgba(88, 166, 255, 0.1);
            }
        """)


class VideoEditCompleteDialog(QDialog):
    """Modern dialog for video editing completion"""
    def __init__(self, parent, successful, failed, output_folder, stopped=False):
        super().__init__(parent)
        self.successful = successful
        self.failed = failed
        self.output_folder = output_folder
        self.stopped = stopped
        self.setup_dialog()
    
    def setup_dialog(self):
        self.setWindowTitle("Edit Complete")
        self.setFixedSize(420, 320)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint)
        
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1a1f2e, stop:1 #0d1117);
                color: #e6edf3;
            }
            QLabel {
                color: #e6edf3;
                background: transparent;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)
        
        # Header with icon
        header_layout = QHBoxLayout()
        
        if self.stopped:
            icon_text = "!"
            icon_color = "#ffab00"
            title_text = "Editing Stopped"
        elif self.failed > 0 and self.successful == 0:
            icon_text = "X"
            icon_color = "#f85149"
            title_text = "Editing Failed"
        else:
            icon_text = "OK"  # checkmark
            icon_color = "#2ea043"
            title_text = "Editing Complete"
        
        icon_label = QLabel(icon_text)
        icon_label.setFixedSize(50, 50)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet(f"""
            QLabel {{
                background: {icon_color};
                color: white;
                border-radius: 25px;
                font-size: 24px;
                font-weight: bold;
            }}
        """)
        header_layout.addWidget(icon_label)
        
        title_label = QLabel(title_text)
        title_label.setStyleSheet(f"color: {icon_color}; font-size: 18px; font-weight: bold; margin-left: 12px;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # Stats cards
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(12)
        
        # Successful card
        success_card = QFrame()
        success_card.setStyleSheet("""
            QFrame {
                background: rgba(46, 160, 67, 0.15);
                border: 1px solid #2ea043;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        success_layout = QVBoxLayout(success_card)
        success_layout.setSpacing(4)
        success_num = QLabel(str(self.successful))
        success_num.setStyleSheet("color: #2ea043; font-size: 28px; font-weight: bold;")
        success_num.setAlignment(Qt.AlignmentFlag.AlignCenter)
        success_layout.addWidget(success_num)
        success_text = QLabel("Successful")
        success_text.setStyleSheet("color: #7d8590; font-size: 11px;")
        success_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        success_layout.addWidget(success_text)
        stats_layout.addWidget(success_card)
        
        # Failed card
        failed_card = QFrame()
        failed_card.setStyleSheet("""
            QFrame {
                background: rgba(248, 81, 73, 0.15);
                border: 1px solid #f85149;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        failed_layout = QVBoxLayout(failed_card)
        failed_layout.setSpacing(4)
        failed_num = QLabel(str(self.failed))
        failed_num.setStyleSheet("color: #f85149; font-size: 28px; font-weight: bold;")
        failed_num.setAlignment(Qt.AlignmentFlag.AlignCenter)
        failed_layout.addWidget(failed_num)
        failed_text = QLabel("Failed")
        failed_text.setStyleSheet("color: #7d8590; font-size: 11px;")
        failed_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        failed_layout.addWidget(failed_text)
        stats_layout.addWidget(failed_card)
        
        layout.addLayout(stats_layout)
        
        # Output folder
        folder_frame = QFrame()
        folder_frame.setStyleSheet("""
            QFrame {
                background: rgba(45, 51, 59, 0.5);
                border: 1px solid #30363d;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        folder_layout = QVBoxLayout(folder_frame)
        folder_layout.setSpacing(4)
        
        folder_title = QLabel("Output Location")
        folder_title.setStyleSheet("color: #58a6ff; font-size: 11px; font-weight: bold;")
        folder_layout.addWidget(folder_title)
        
        folder_path = QLabel(self.output_folder)
        folder_path.setStyleSheet("color: #8b949e; font-size: 10px;")
        folder_path.setWordWrap(True)
        folder_layout.addWidget(folder_path)
        
        layout.addWidget(folder_frame)
        
        layout.addStretch()
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        btn_layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #e6edf3;
                border: 1px solid #444c56;
                border-radius: 6px;
                padding: 10px 24px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.05);
                border-color: #58a6ff;
            }
        """)
        btn_layout.addWidget(close_btn)
        
        open_btn = QPushButton("Open Folder")
        open_btn.clicked.connect(self.open_folder)
        open_btn.setStyleSheet("""
            QPushButton {
                background: #238636;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 24px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #2ea043;
            }
        """)
        btn_layout.addWidget(open_btn)
        
        layout.addLayout(btn_layout)
    
    def open_folder(self):
        import subprocess
        import platform
        try:
            if platform.system() == 'Windows':
                subprocess.run(['explorer', self.output_folder])
            elif platform.system() == 'Darwin':
                subprocess.run(['open', self.output_folder])
            else:
                subprocess.run(['xdg-open', self.output_folder])
        except Exception:
            pass
        self.accept()


class LicenseActivationDialog(QDialog):
    """Modern license activation dialog with dark overlay"""
    
    def __init__(self, parent=None, license_client=None):
        super().__init__(parent)
        self.license_client = license_client
        self.activated = False
        self._parent = parent
        self.setup_dialog()
    
    def setup_dialog(self):
        self.setWindowTitle("License Activation")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Match parent window size if available, otherwise use screen
        if self._parent:
            self.setGeometry(self._parent.geometry())
        else:
            screen = QApplication.primaryScreen().geometry()
            self.setGeometry(screen)
        
        # Main layout - overlay on parent window
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Dark overlay background
        overlay = QWidget()
        overlay.setStyleSheet("background-color: rgba(0, 0, 0, 180);")
        overlay_layout = QVBoxLayout(overlay)
        overlay_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Center dialog card
        card = QWidget()
        card.setFixedSize(520, 480)
        card.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #1a1f2e, stop:1 #0d1117);
                border-radius: 16px;
                border: 1px solid #30363d;
            }
        """)
        
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(20)
        card_layout.setContentsMargins(40, 30, 40, 40)
        
        # Close button row
        close_row = QHBoxLayout()
        close_row.addStretch()
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(32, 32)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #8b949e;
                border: none;
                border-radius: 16px;
                font-size: 18px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.1);
                color: #f85149;
            }
        """)
        close_btn.clicked.connect(self.reject)
        close_row.addWidget(close_btn)
        card_layout.addLayout(close_row)
        
        # Header
        header = QLabel("🔐 License Activation")
        header.setStyleSheet("font-size: 24px; font-weight: bold; color: #58a6ff; background: transparent; border: none;")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(header)
        
        # Description
        desc = QLabel("Enter your license key to activate the application.\nYou can purchase a license from our website.")
        desc.setStyleSheet("color: #8b949e; font-size: 13px; background: transparent; border: none;")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(desc)
        
        card_layout.addSpacing(10)
        
        # License key input
        key_label = QLabel("License Key")
        key_label.setStyleSheet("font-size: 12px; color: #8b949e; font-weight: bold; background: transparent; border: none;")
        card_layout.addWidget(key_label)
        
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("XXXX-XXXX-XXXX-XXXX")
        self.key_input.setMaxLength(19)
        self.key_input.setStyleSheet("""
            QLineEdit {
                background: #2d333b;
                color: #e6edf3;
                border: 2px solid #444c56;
                border-radius: 8px;
                padding: 12px 16px;
                font-size: 16px;
                font-family: 'Consolas', monospace;
                letter-spacing: 2px;
            }
            QLineEdit:focus {
                border-color: #58a6ff;
            }
        """)
        self.key_input.textChanged.connect(self.format_license_key)
        card_layout.addWidget(self.key_input)
        
        # Status label
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("font-size: 12px; background: transparent; border: none;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self.status_label)
        
        card_layout.addStretch()
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        
        self.activate_btn = QPushButton("Activate License")
        self.activate_btn.setMinimumHeight(48)
        self.activate_btn.setStyleSheet("""
            QPushButton {
                background: #238636;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 14px 32px;
                font-size: 15px;
                font-weight: bold;
                min-width: 200px;
            }
            QPushButton:hover {
                background: #2ea043;
            }
            QPushButton:disabled {
                background: #21262d;
                color: #484f58;
            }
        """)
        self.activate_btn.clicked.connect(self.activate_license)
        btn_layout.addWidget(self.activate_btn)
        
        card_layout.addLayout(btn_layout)
        
        # Trial info
        trial_info = QLabel("Need a license? Visit our website or contact support.")
        trial_info.setStyleSheet("color: #6e7681; font-size: 11px; background: transparent; border: none;")
        trial_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(trial_info)
        
        overlay_layout.addWidget(card)
        main_layout.addWidget(overlay)
    
    def format_license_key(self, text):
        """Auto-format license key with dashes"""
        # Remove all non-alphanumeric characters
        clean = ''.join(c for c in text.upper() if c.isalnum())
        
        # Add dashes every 4 characters
        formatted = '-'.join([clean[i:i+4] for i in range(0, len(clean), 4)])
        
        # Update input without triggering signal loop
        if formatted != text:
            self.key_input.blockSignals(True)
            self.key_input.setText(formatted[:19])  # Max 19 chars (XXXX-XXXX-XXXX-XXXX)
            self.key_input.setCursorPosition(len(formatted[:19]))
            self.key_input.blockSignals(False)
    
    def activate_license(self):
        """Validate and activate the license"""
        license_key = self.key_input.text().strip()
        
        if len(license_key) < 19:
            self.status_label.setText("⚠️ Please enter a valid license key")
            self.status_label.setStyleSheet("color: #d29922; font-size: 12px;")
            return
        
        self.activate_btn.setEnabled(False)
        self.activate_btn.setText("Validating...")
        self.status_label.setText("🔄 Connecting to license server...")
        self.status_label.setStyleSheet("color: #8b949e; font-size: 12px;")
        QApplication.processEvents()
        
        if self.license_client:
            result = self.license_client.validate(license_key)
            
            if result.get("valid"):
                self.status_label.setText("✅ License activated successfully!")
                self.status_label.setStyleSheet("color: #3fb950; font-size: 12px;")
                self.activated = True
                
                # Show success message
                QTimer.singleShot(1500, self.accept)
            else:
                error = result.get("error", "Unknown error")
                self.status_label.setText(f"❌ {error}")
                self.status_label.setStyleSheet("color: #f85149; font-size: 12px;")
                self.activate_btn.setEnabled(True)
                self.activate_btn.setText("Activate License")
        else:
            self.status_label.setText("❌ License system not available")
            self.status_label.setStyleSheet("color: #f85149; font-size: 12px;")
            self.activate_btn.setEnabled(True)
            self.activate_btn.setText("Activate License")

class VideoEditSettingsDialog(QDialog):
    """Dialog for video editing settings - Modern professional design"""
    def __init__(self, parent, settings=None):
        super().__init__(parent)
        self.settings = settings or {}
        self.setup_dialog()
        # Apply initial state based on loaded settings
        self.apply_initial_state()
    
    def apply_initial_state(self):
        """Apply initial enabled/disabled state based on settings"""
        # Resolution custom fields
        self.on_resolution_changed(self.resolution_combo.currentText())
        # Trim fields
        self.on_trim_toggled(self.enable_trim.isChecked())
        # Logo fields
        self.on_logo_toggled(self.enable_logo.isChecked())
    
    def setup_dialog(self):
        self.setWindowTitle("Video Edit Settings")
        self.setFixedSize(950, 720)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint)
        
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #1a1f2e, stop:1 #0d1117);
                color: #e6edf3;
            }
            QLabel {
                color: #8b949e;
                background: transparent;
                font-size: 11px;
            }
            QComboBox {
                background: #2d333b;
                color: #e6edf3;
                border: 1px solid #444c56;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 12px;
            }
            QComboBox:hover {
                border-color: #58a6ff;
            }
            QComboBox:disabled {
                background: #161b22;
                color: #484f58;
                border-color: #30363d;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid #8b949e;
                margin-right: 8px;
            }
            QComboBox QAbstractItemView {
                background: #2d333b;
                color: #e6edf3;
                border: 1px solid #444c56;
                selection-background-color: #388bfd;
            }
            QSpinBox, QDoubleSpinBox {
                background: #2d333b;
                color: #e6edf3;
                border: 1px solid #444c56;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 12px;
            }
            QSpinBox:hover, QDoubleSpinBox:hover {
                border-color: #58a6ff;
            }
            QSpinBox:disabled, QDoubleSpinBox:disabled {
                background: #161b22;
                color: #484f58;
                border-color: #30363d;
            }
            QLineEdit {
                background: #2d333b;
                color: #e6edf3;
                border: 1px solid #444c56;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 12px;
            }
            QLineEdit:hover { border-color: #58a6ff; }
            QLineEdit:disabled {
                background: #161b22;
                color: #484f58;
                border-color: #30363d;
            }
            QCheckBox {
                color: #e6edf3;
                spacing: 8px;
                font-size: 12px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 2px solid #444c56;
                background: #22272e;
            }
            QCheckBox::indicator:hover { border-color: #58a6ff; }
            QCheckBox::indicator:checked {
                background: #58a6ff;
                border-color: #58a6ff;
            }
        """)
        
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # === 3 PANEL LAYOUT ===
        panels_layout = QHBoxLayout()
        panels_layout.setSpacing(12)
        
        # --- PANEL 1: Output ---
        panel1 = QFrame()
        panel1.setObjectName("panel")
        panel1.setStyleSheet("QFrame#panel { background: rgba(45,51,59,0.4); border: 1px solid #30363d; border-radius: 10px; }")
        p1_layout = QVBoxLayout(panel1)
        p1_layout.setSpacing(8)
        p1_layout.setContentsMargins(14, 14, 14, 14)
        
        p1_header = QLabel("[>] OUTPUT")
        p1_header.setStyleSheet("color: #58a6ff; font-weight: bold; font-size: 11px;")
        p1_layout.addWidget(p1_header)
        
        res_label = QLabel("Resolution")
        p1_layout.addWidget(res_label)
        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems(["Original", "4K", "2K", "1080p", "720p", "480p", "Custom"])
        self.resolution_combo.setCurrentText(self.settings.get('resolution', 'Original'))
        self.resolution_combo.currentTextChanged.connect(self.on_resolution_changed)
        p1_layout.addWidget(self.resolution_combo)
        
        size_row = QHBoxLayout()
        size_row.setSpacing(6)
        self.custom_width = QSpinBox()
        self.custom_width.setRange(100, 7680)
        self.custom_width.setValue(self.settings.get('custom_width', 1920))
        self.custom_width.setEnabled(False)
        self.custom_width.setPrefix("W:")
        size_row.addWidget(self.custom_width)
        self.custom_height = QSpinBox()
        self.custom_height.setRange(100, 4320)
        self.custom_height.setValue(self.settings.get('custom_height', 1080))
        self.custom_height.setEnabled(False)
        self.custom_height.setPrefix("H:")
        size_row.addWidget(self.custom_height)
        p1_layout.addLayout(size_row)
        
        fmt_label = QLabel("Format")
        p1_layout.addWidget(fmt_label)
        self.output_format = QComboBox()
        self.output_format.addItems(["MP4 (H.264)", "MP4 (H.265)", "WebM", "AVI", "MOV", "MKV"])
        self.output_format.setCurrentText(self.settings.get('output_format', 'MP4 (H.264)'))
        p1_layout.addWidget(self.output_format)
        
        crf_label = QLabel("Quality (CRF)")
        p1_layout.addWidget(crf_label)
        self.quality_crf = QSpinBox()
        self.quality_crf.setRange(0, 51)
        self.quality_crf.setValue(self.settings.get('quality_crf', 23))
        p1_layout.addWidget(self.quality_crf)
        p1_layout.addStretch()
        panels_layout.addWidget(panel1)
        
        # --- PANEL 2: Playback & Trim ---
        panel2 = QFrame()
        panel2.setObjectName("panel")
        panel2.setStyleSheet("QFrame#panel { background: rgba(45,51,59,0.4); border: 1px solid #30363d; border-radius: 10px; }")
        p2_layout = QVBoxLayout(panel2)
        p2_layout.setSpacing(8)
        p2_layout.setContentsMargins(14, 14, 14, 14)
        
        p2_header = QLabel("[~] PLAYBACK")
        p2_header.setStyleSheet("color: #58a6ff; font-weight: bold; font-size: 11px;")
        p2_layout.addWidget(p2_header)
        
        speed_vol_row = QHBoxLayout()
        speed_vol_row.setSpacing(6)
        speed_col = QVBoxLayout()
        speed_col.setSpacing(2)
        speed_col.addWidget(QLabel("Speed"))
        self.speed = QDoubleSpinBox()
        self.speed.setRange(0.25, 4.0)
        self.speed.setSingleStep(0.25)
        self.speed.setValue(self.settings.get('speed', 1.0))
        self.speed.setSuffix("x")
        speed_col.addWidget(self.speed)
        speed_vol_row.addLayout(speed_col)
        vol_col = QVBoxLayout()
        vol_col.setSpacing(2)
        vol_col.addWidget(QLabel("Volume"))
        self.volume = QSpinBox()
        self.volume.setRange(0, 300)
        self.volume.setValue(self.settings.get('volume', 100))
        self.volume.setSuffix("%")
        vol_col.addWidget(self.volume)
        speed_vol_row.addLayout(vol_col)
        p2_layout.addLayout(speed_vol_row)
        
        self.mute_audio = QCheckBox("Mute Audio")
        self.mute_audio.setChecked(self.settings.get('mute_audio', False))
        p2_layout.addWidget(self.mute_audio)
        
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background: #30363d;")
        p2_layout.addWidget(sep)
        
        p2_trim = QLabel("[/] TRIM")
        p2_trim.setStyleSheet("color: #58a6ff; font-weight: bold; font-size: 11px;")
        p2_layout.addWidget(p2_trim)
        
        self.enable_trim = QCheckBox("Enable Trim")
        self.enable_trim.setChecked(self.settings.get('enable_trim', False))
        self.enable_trim.toggled.connect(self.on_trim_toggled)
        p2_layout.addWidget(self.enable_trim)
        
        trim_row = QHBoxLayout()
        trim_row.setSpacing(6)
        start_col = QVBoxLayout()
        start_col.setSpacing(2)
        start_col.addWidget(QLabel("Start"))
        self.trim_start = QDoubleSpinBox()
        self.trim_start.setRange(0, 99999)
        self.trim_start.setValue(self.settings.get('trim_start', 0))
        self.trim_start.setSuffix("s")
        self.trim_start.setEnabled(False)
        start_col.addWidget(self.trim_start)
        trim_row.addLayout(start_col)
        end_col = QVBoxLayout()
        end_col.setSpacing(2)
        end_col.addWidget(QLabel("End"))
        self.trim_end = QDoubleSpinBox()
        self.trim_end.setRange(0, 99999)
        self.trim_end.setValue(self.settings.get('trim_end', 0))
        self.trim_end.setSuffix("s")
        self.trim_end.setEnabled(False)
        end_col.addWidget(self.trim_end)
        trim_row.addLayout(end_col)
        p2_layout.addLayout(trim_row)
        p2_layout.addStretch()
        panels_layout.addWidget(panel2)
        
        # --- PANEL 3: Watermark ---
        panel3 = QFrame()
        panel3.setObjectName("panel")
        panel3.setStyleSheet("QFrame#panel { background: rgba(45,51,59,0.4); border: 1px solid #30363d; border-radius: 10px; }")
        p3_layout = QVBoxLayout(panel3)
        p3_layout.setSpacing(8)
        p3_layout.setContentsMargins(14, 14, 14, 14)
        
        p3_header = QLabel("[*] WATERMARK")
        p3_header.setStyleSheet("color: #58a6ff; font-weight: bold; font-size: 11px;")
        p3_layout.addWidget(p3_header)
        
        self.enable_logo = QCheckBox("Enable Watermark")
        self.enable_logo.setChecked(self.settings.get('enable_logo', False))
        self.enable_logo.toggled.connect(self.on_logo_toggled)
        p3_layout.addWidget(self.enable_logo)
        
        # Watermark type selector
        type_label = QLabel("Type")
        p3_layout.addWidget(type_label)
        self.watermark_type = QComboBox()
        self.watermark_type.addItems(["Image", "Text"])
        self.watermark_type.setCurrentText(self.settings.get('watermark_type', 'Image'))
        self.watermark_type.setEnabled(False)
        self.watermark_type.currentTextChanged.connect(self.on_watermark_type_changed)
        p3_layout.addWidget(self.watermark_type)
        
        # Image watermark controls
        self.image_watermark_widget = QWidget()
        image_layout = QVBoxLayout(self.image_watermark_widget)
        image_layout.setContentsMargins(0, 0, 0, 0)
        image_layout.setSpacing(6)
        
        file_row = QHBoxLayout()
        file_row.setSpacing(4)
        self.logo_path = QLineEdit()
        self.logo_path.setPlaceholderText("Logo image...")
        self.logo_path.setText(self.settings.get('logo_path', ''))
        self.logo_path.setEnabled(False)
        file_row.addWidget(self.logo_path)
        self.browse_logo_btn = QPushButton("...")
        self.browse_logo_btn.setFixedWidth(30)
        self.browse_logo_btn.clicked.connect(self.browse_logo)
        self.browse_logo_btn.setEnabled(False)
        self.browse_logo_btn.setStyleSheet("QPushButton { background: #2d333b; color: #e6edf3; border: 1px solid #444c56; border-radius: 6px; padding: 4px; } QPushButton:hover { border-color: #58a6ff; } QPushButton:disabled { background: #161b22; color: #484f58; }")
        file_row.addWidget(self.browse_logo_btn)
        image_layout.addLayout(file_row)
        
        # Logo shape (for image only)
        shape_label_img = QLabel("Shape")
        image_layout.addWidget(shape_label_img)
        self.logo_shape = QComboBox()
        self.logo_shape.addItems(["None", "Circle", "Rounded", "Square", "Triangle"])
        self.logo_shape.setCurrentText(self.settings.get('logo_shape', 'None'))
        self.logo_shape.setEnabled(False)
        image_layout.addWidget(self.logo_shape)
        
        p3_layout.addWidget(self.image_watermark_widget)
        
        # Text watermark controls
        self.text_watermark_widget = QWidget()
        text_layout = QVBoxLayout(self.text_watermark_widget)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(6)
        
        text_input_label = QLabel("Text")
        text_layout.addWidget(text_input_label)
        self.watermark_text = QLineEdit()
        self.watermark_text.setPlaceholderText("Enter watermark text...")
        self.watermark_text.setText(self.settings.get('watermark_text', ''))
        self.watermark_text.setEnabled(False)
        text_layout.addWidget(self.watermark_text)
        
        # Font size and color row
        font_row = QHBoxLayout()
        font_row.setSpacing(6)
        
        font_col = QVBoxLayout()
        font_col.setSpacing(2)
        font_col.addWidget(QLabel("Font Size"))
        self.text_font_size = QSpinBox()
        self.text_font_size.setRange(12, 200)
        self.text_font_size.setValue(self.settings.get('text_font_size', 48))
        self.text_font_size.setEnabled(False)
        font_col.addWidget(self.text_font_size)
        font_row.addLayout(font_col)
        
        color_col = QVBoxLayout()
        color_col.setSpacing(2)
        color_col.addWidget(QLabel("Color"))
        self.text_color_btn = QPushButton()
        self.text_color = self.settings.get('text_color', '#FFFFFF')
        self.text_color_btn.setStyleSheet(f"QPushButton {{ background: {self.text_color}; border: 1px solid #444c56; border-radius: 6px; min-height: 28px; }} QPushButton:hover {{ border-color: #58a6ff; }} QPushButton:disabled {{ background: #484f58; }}")
        self.text_color_btn.clicked.connect(self.pick_text_color)
        self.text_color_btn.setEnabled(False)
        color_col.addWidget(self.text_color_btn)
        font_row.addLayout(color_col)
        
        text_layout.addLayout(font_row)
        
        p3_layout.addWidget(self.text_watermark_widget)
        self.text_watermark_widget.hide()  # Hidden by default (Image is default)
        
        # Common controls for both types
        pos_label = QLabel("Position")
        p3_layout.addWidget(pos_label)
        self.logo_position = QComboBox()
        self.logo_position.addItems(["Top-Left", "Top-Right", "Bottom-Left", "Bottom-Right", "Center"])
        self.logo_position.setCurrentText(self.settings.get('logo_position', 'Bottom-Right'))
        self.logo_position.setEnabled(False)
        p3_layout.addWidget(self.logo_position)
        
        op_scale_row = QHBoxLayout()
        op_scale_row.setSpacing(6)
        op_col = QVBoxLayout()
        op_col.setSpacing(2)
        op_col.addWidget(QLabel("Opacity"))
        self.logo_opacity = QSpinBox()
        self.logo_opacity.setRange(10, 100)
        self.logo_opacity.setValue(self.settings.get('logo_opacity', 80))
        self.logo_opacity.setSuffix("%")
        self.logo_opacity.setEnabled(False)
        op_col.addWidget(self.logo_opacity)
        op_scale_row.addLayout(op_col)
        scale_col = QVBoxLayout()
        scale_col.setSpacing(2)
        scale_col.addWidget(QLabel("Scale"))
        self.logo_scale = QSpinBox()
        self.logo_scale.setRange(5, 100)
        self.logo_scale.setValue(self.settings.get('logo_scale', 15))
        self.logo_scale.setSuffix("%")
        self.logo_scale.setEnabled(False)
        scale_col.addWidget(self.logo_scale)
        op_scale_row.addLayout(scale_col)
        p3_layout.addLayout(op_scale_row)
        
        # Animation options
        anim_label = QLabel("Animation")
        p3_layout.addWidget(anim_label)
        self.watermark_animation = QComboBox()
        self.watermark_animation.addItems([
            "None", 
            "Fade In", 
            "Fade In/Out",
            "Slide In Left",
            "Slide In Right", 
            "Slide In Top",
            "Slide In Bottom",
            "Zoom In",
            "Pulse"
        ])
        self.watermark_animation.setCurrentText(self.settings.get('watermark_animation', 'None'))
        self.watermark_animation.setEnabled(False)
        self.watermark_animation.setToolTip("Animation effect for watermark appearance")
        p3_layout.addWidget(self.watermark_animation)
        
        # Animation duration
        anim_dur_row = QHBoxLayout()
        anim_dur_row.setSpacing(6)
        anim_dur_col = QVBoxLayout()
        anim_dur_col.setSpacing(2)
        anim_dur_col.addWidget(QLabel("Duration"))
        self.animation_duration = QDoubleSpinBox()
        self.animation_duration.setRange(0.5, 5.0)
        self.animation_duration.setSingleStep(0.5)
        self.animation_duration.setValue(self.settings.get('animation_duration', 1.0))
        self.animation_duration.setSuffix("s")
        self.animation_duration.setEnabled(False)
        self.animation_duration.setToolTip("Animation duration in seconds")
        anim_dur_col.addWidget(self.animation_duration)
        anim_dur_row.addLayout(anim_dur_col)
        anim_dur_row.addStretch()
        p3_layout.addLayout(anim_dur_row)
        
        p3_layout.addStretch()
        panels_layout.addWidget(panel3)
        
        main_layout.addLayout(panels_layout)
        
        # === OUTPUT OPTIONS ROW ===
        output_frame = QFrame()
        output_frame.setStyleSheet("QFrame { background: rgba(45,51,59,0.3); border: 1px solid #30363d; border-radius: 8px; }")
        output_layout = QHBoxLayout(output_frame)
        output_layout.setContentsMargins(12, 8, 12, 8)
        output_layout.setSpacing(20)
        
        output_title = QLabel("OUTPUT:")
        output_title.setStyleSheet("color: #58a6ff; font-weight: bold; font-size: 11px;")
        output_layout.addWidget(output_title)
        
        self.replace_original = QCheckBox("Replace Original")
        self.replace_original.setChecked(self.settings.get('replace_original', False))
        self.replace_original.setToolTip("Overwrite the original video file")
        output_layout.addWidget(self.replace_original)
        
        self.same_folder = QCheckBox("Same Folder")
        self.same_folder.setChecked(self.settings.get('same_folder', False))
        self.same_folder.setToolTip("Save edited video in the same folder as original")
        output_layout.addWidget(self.same_folder)
        
        self.add_suffix = QCheckBox("Add '_edited' Suffix")
        self.add_suffix.setChecked(self.settings.get('add_suffix', True))
        self.add_suffix.setToolTip("Add '_edited' to the output filename")
        output_layout.addWidget(self.add_suffix)
        
        output_layout.addStretch()
        main_layout.addWidget(output_frame)
        
        # === BUTTONS ===
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("QPushButton { background: transparent; color: #e6edf3; border: 1px solid #444c56; border-radius: 6px; padding: 10px 24px; font-size: 12px; font-weight: bold; } QPushButton:hover { background: rgba(255,255,255,0.05); border-color: #58a6ff; }")
        btn_layout.addWidget(cancel_btn)
        
        apply_btn = QPushButton("Apply")
        apply_btn.clicked.connect(self.accept)
        apply_btn.setStyleSheet("QPushButton { background: #238636; color: white; border: none; border-radius: 6px; padding: 10px 24px; font-size: 12px; font-weight: bold; } QPushButton:hover { background: #2ea043; }")
        btn_layout.addWidget(apply_btn)
        
        main_layout.addLayout(btn_layout)
        
        # Apply initial watermark type visibility
        self.on_watermark_type_changed(self.watermark_type.currentText())
    
    def on_resolution_changed(self, text):
        is_custom = text == "Custom"
        self.custom_width.setEnabled(is_custom)
        self.custom_height.setEnabled(is_custom)
    
    def on_logo_toggled(self, checked):
        self.watermark_type.setEnabled(checked)
        self.logo_position.setEnabled(checked)
        self.logo_opacity.setEnabled(checked)
        self.logo_scale.setEnabled(checked)
        self.watermark_animation.setEnabled(checked)
        self.animation_duration.setEnabled(checked)
        # Update type-specific controls
        if checked:
            self.on_watermark_type_changed(self.watermark_type.currentText())
        else:
            # Disable all type-specific controls
            self.logo_path.setEnabled(False)
            self.browse_logo_btn.setEnabled(False)
            self.logo_shape.setEnabled(False)
            self.watermark_text.setEnabled(False)
            self.text_font_size.setEnabled(False)
            self.text_color_btn.setEnabled(False)
    
    def on_watermark_type_changed(self, text):
        is_image = text == "Image"
        is_enabled = self.enable_logo.isChecked()
        
        # Show/hide appropriate widgets
        self.image_watermark_widget.setVisible(is_image)
        self.text_watermark_widget.setVisible(not is_image)
        
        # Enable/disable controls based on type and enabled state
        self.logo_path.setEnabled(is_image and is_enabled)
        self.browse_logo_btn.setEnabled(is_image and is_enabled)
        self.logo_shape.setEnabled(is_image and is_enabled)
        
        self.watermark_text.setEnabled(not is_image and is_enabled)
        self.text_font_size.setEnabled(not is_image and is_enabled)
        self.text_color_btn.setEnabled(not is_image and is_enabled)
    
    def pick_text_color(self):
        color = QColorDialog.getColor(QColor(self.text_color), self, "Select Text Color")
        if color.isValid():
            self.text_color = color.name()
            self.text_color_btn.setStyleSheet(f"QPushButton {{ background: {self.text_color}; border: 1px solid #444c56; border-radius: 6px; min-height: 28px; }} QPushButton:hover {{ border-color: #58a6ff; }} QPushButton:disabled {{ background: #484f58; }}")
    
    def on_trim_toggled(self, checked):
        self.trim_start.setEnabled(checked)
        self.trim_end.setEnabled(checked)
    
    def browse_logo(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Logo Image", "", 
            "Images (*.png *.jpg *.jpeg *.gif *.bmp *.webp);;All Files (*)"
        )
        if file_path:
            self.logo_path.setText(file_path)
    
    def get_settings(self):
        return {
            'resolution': self.resolution_combo.currentText(),
            'custom_width': self.custom_width.value(),
            'custom_height': self.custom_height.value(),
            'enable_logo': self.enable_logo.isChecked(),
            'watermark_type': self.watermark_type.currentText(),
            'logo_path': self.logo_path.text(),
            'logo_position': self.logo_position.currentText(),
            'logo_opacity': self.logo_opacity.value(),
            'logo_scale': self.logo_scale.value(),
            'logo_shape': self.logo_shape.currentText(),
            'watermark_text': self.watermark_text.text(),
            'text_font_size': self.text_font_size.value(),
            'text_color': self.text_color,
            'watermark_animation': self.watermark_animation.currentText(),
            'animation_duration': self.animation_duration.value(),
            'enable_trim': self.enable_trim.isChecked(),
            'trim_start': self.trim_start.value(),
            'trim_end': self.trim_end.value(),
            'mute_audio': self.mute_audio.isChecked(),
            'volume': self.volume.value(),
            'speed': self.speed.value(),
            'output_format': self.output_format.currentText(),
            'quality_crf': self.quality_crf.value(),
            'replace_original': self.replace_original.isChecked(),
            'same_folder': self.same_folder.isChecked(),
            'add_suffix': self.add_suffix.isChecked()
        }


class ProfileInfoWorker(QThread):
    progress = pyqtSignal(int, str)  # percentage, message
    done = pyqtSignal(bool, object)  # success, data
    
    def __init__(self, dl, profile_url):
        super().__init__()
        self.dl = dl
        self.profile_url = profile_url
    
    def run(self):
        try:
            self.progress.emit(10, "Connecting to profile...")
            
            # Get profile videos with higher limit for better extraction
            result = self.dl.get_profile_videos(self.profile_url, max_videos=500)
            
            self.progress.emit(50, "Extracting video list...")
            
            if result['success']:
                self.progress.emit(100, "Profile info extracted!")
                self.done.emit(True, result)
            else:
                self.progress.emit(100, "Failed")
                self.done.emit(False, result.get('error', 'Unknown error'))
                
        except Exception as e:
            self.progress.emit(100, "Failed")
            self.done.emit(False, str(e))


class MultipleDownloadWorker(QThread):
    progress = pyqtSignal(str)  # Progress message
    progress_percent = pyqtSignal(int, str)  # Current video percentage, message
    video_started = pyqtSignal(int, str)  # index, url
    video_completed = pyqtSignal(int, bool, str, str)  # index, success, message, file_path
    batch_completed = pyqtSignal(dict)  # summary statistics
    
    def __init__(self, dl, urls, settings):
        super().__init__()
        self.dl = dl
        self.urls = urls
        self.settings = settings
        self.paused = False
        self.stopped = False
        self._current_download_aborted = False
        self.target_success = settings.get('target_success')  # Target number of successful downloads
        
    def run(self):
        total_urls = len(self.urls)
        completed = 0
        failed = 0
        successful_files = []
        failed_urls = []
        
        for i, url in enumerate(self.urls):
            if self.stopped:
                self.progress.emit("[STOP] Downloads stopped by user")
                break
            
            # Check if we've reached target successful downloads
            if self.target_success and completed >= self.target_success:
                self.progress.emit(f"[OK] Reached target of {self.target_success} successful downloads")
                break
                
            # Wait if paused
            while self.paused and not self.stopped:
                self.msleep(100)
                
            if self.stopped:
                self.progress.emit("[STOP] Downloads stopped by user")
                break
            
            self._current_download_aborted = False
            self.video_started.emit(i, url)
            
            # Show progress with target info if set
            if self.target_success:
                self.progress.emit(f"[DL] Downloading {completed + 1}/{self.target_success} (attempt {i+1}): {url[:50]}...")
            else:
                self.progress.emit(f"[DL] Starting download {i+1}/{total_urls}: {url[:50]}...")
            
            try:
                # Create progress callback for current video that checks stop flag
                def progress_callback(message):
                    if self.stopped:
                        self._current_download_aborted = True
                        raise Exception("Download stopped by user")
                    
                    # Show progress with target info if set
                    if self.target_success:
                        self.progress.emit(f"[{completed + 1}/{self.target_success}] {message}")
                    else:
                        self.progress.emit(f"[{i+1}/{total_urls}] {message}")
                    
                    # Try to extract percentage from yt-dlp progress messages
                    if "%" in message and "Downloading:" in message:
                        try:
                            # Extract percentage from messages like "Downloading: 45.2%"
                            percent_str = message.split("%")[0].split()[-1]
                            percent = float(percent_str)
                            target = self.target_success if self.target_success else total_urls
                            self.progress_percent.emit(int(percent), f"Video {completed + 1}/{target}")
                        except:
                            pass
                    elif "Completed:" in message:
                        target = self.target_success if self.target_success else total_urls
                        self.progress_percent.emit(100, f"Video {completed + 1}/{target} complete")
                
                result = self.dl.download(
                    url,
                    self.settings.get('quality', 'best'),
                    self.settings.get('audio', False),
                    self.settings.get('subtitle', False),
                    self.settings.get('format', 'Force H.264 (Compatible)'),
                    self.settings.get('convert', False),
                    self.settings.get('use_caption', True),
                    self.settings.get('mute', False),
                    progress_callback
                )
                
                if self.stopped or self._current_download_aborted:
                    self.progress.emit("[STOP] Downloads stopped by user")
                    break
                
                if result['success']:
                    completed += 1
                    file_path = str(result['file_path']) if result['file_path'] else ""
                    successful_files.append(file_path)
                    self.video_completed.emit(i, True, "Download complete", file_path)
                    
                    if self.target_success:
                        self.progress.emit(f"[OK] Downloaded {completed}/{self.target_success}: {url[:50]}")
                    else:
                        self.progress.emit(f"[OK] Completed {i+1}/{total_urls}: {url[:50]}")
                else:
                    failed += 1
                    failed_urls.append(url)
                    self.video_completed.emit(i, False, f"Failed: {result.get('error', 'Unknown error')}", "")
                    
                    if self.target_success:
                        self.progress.emit(f"[X] Failed (will try next): {url[:50]}")
                    else:
                        self.progress.emit(f"[X] Failed {i+1}/{total_urls}: {url[:50]}")
                    
            except Exception as e:
                if self.stopped or "stopped by user" in str(e).lower():
                    self.progress.emit("[STOP] Downloads stopped by user")
                    break
                failed += 1
                failed_urls.append(url)
                self.video_completed.emit(i, False, f"Error: {str(e)}", "")
                
                if self.target_success:
                    self.progress.emit(f"[X] Error (will try next): {str(e)[:50]}")
                else:
                    self.progress.emit(f"[X] Error {i+1}/{total_urls}: {str(e)}")
        
        # Send completion summary
        summary = {
            'total': total_urls,
            'completed': completed,
            'failed': failed,
            'successful_files': successful_files,
            'failed_urls': failed_urls,
            'stopped': self.stopped,
            'target_success': self.target_success,
            'target_reached': self.target_success and completed >= self.target_success
        }
        self.batch_completed.emit(summary)
    
    def pause(self):
        self.paused = True
        
    def resume(self):
        self.paused = False
        
    def stop(self):
        self.stopped = True
        self.paused = False
        # Also set abort flag on downloader
        if hasattr(self.dl, 'abort_download'):
            self.dl.abort_download = True


class VideoDownloader:
    """Core downloader with professional error handling and recovery"""
    def __init__(self, output_dir="downloads"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.abort_download = False  # Flag to abort current download
        self.platforms = {
            'youtube.com': 'YouTube', 'youtu.be': 'YouTube',
            'tiktok.com': 'TikTok', 'facebook.com': 'Facebook',
            'fb.watch': 'Facebook', 'instagram.com': 'Instagram',
            'twitter.com': 'Twitter', 'x.com': 'Twitter',
            'vimeo.com': 'Vimeo', 'twitch.tv': 'Twitch'
        }
        # Cleanup temp files on init
        self.cleanup_temp_files()
    
    def cleanup_temp_files(self, specific_file=None):
        """Clean up leftover temp files (.ytdl, .part) that can cause permission errors"""
        try:
            if specific_file:
                # Clean specific file's temp files
                base_path = Path(specific_file)
                temp_extensions = ['.ytdl', '.part', '.temp', '.tmp']
                for ext in temp_extensions:
                    temp_file = Path(str(base_path) + ext)
                    if temp_file.exists():
                        try:
                            temp_file.unlink()
                        except:
                            pass
            else:
                # Clean all temp files in output directory
                if self.output_dir.exists():
                    for temp_file in self.output_dir.glob('*.ytdl'):
                        try:
                            temp_file.unlink()
                        except:
                            pass
                    for temp_file in self.output_dir.glob('*.part'):
                        try:
                            # Only delete .part files older than 1 hour (might be active downloads)
                            import time
                            if time.time() - temp_file.stat().st_mtime > 3600:
                                temp_file.unlink()
                        except:
                            pass
        except Exception:
            pass  # Silently ignore cleanup errors
    
    def check_file_locked(self, filepath):
        """Check if a file is locked by another process"""
        try:
            if not Path(filepath).exists():
                return False
            # Try to open file exclusively
            with open(filepath, 'a'):
                return False
        except (IOError, PermissionError):
            return True
    
    def wait_for_file_unlock(self, filepath, timeout=10, callback=None):
        """Wait for a file to become unlocked"""
        import time
        start_time = time.time()
        while time.time() - start_time < timeout:
            if not self.check_file_locked(filepath):
                return True
            if callback:
                callback(f"[...] Waiting for file access... ({int(timeout - (time.time() - start_time))}s)")
            time.sleep(1)
        return False
    
    def detect_platform(self, url):
        domain = urlparse(url).netloc.lower().replace('www.', '')
        for k, v in self.platforms.items():
            if k in domain:
                return v
        return "Unknown"
    
    def is_profile_url(self, url):
        """Detect if URL is a profile/channel URL rather than a single video"""
        # Remove query parameters for better detection
        from urllib.parse import urlparse
        parsed = urlparse(url)
        clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}".lower()
        
        # YouTube channel/user patterns
        if 'youtube.com' in clean_url or 'youtu.be' in clean_url:
            return any(pattern in clean_url for pattern in [
                '/channel/', '/user/', '/c/', '/@', '/playlist'
            ])
        
        # TikTok profile patterns
        elif 'tiktok.com' in clean_url:
            # TikTok profile: tiktok.com/@username (without /video/)
            return '/@' in clean_url and '/video/' not in clean_url
        
        # Instagram profile patterns
        elif 'instagram.com' in clean_url:
            # Instagram profile: instagram.com/username (without /p/ or /reel/)
            return '/p/' not in clean_url and '/reel/' not in clean_url and '/stories/' not in clean_url
        
        # Facebook profile/page patterns - including reels and videos pages
        elif 'facebook.com' in clean_url or 'fb.watch' in clean_url:
            # Single video patterns - these are NOT profiles
            single_video_patterns = [
                '/watch/?v=', '/watch?v=', '/reel/', '/share/r/', '/share/v/',
                'fb.watch/', '/video.php', '/videos/'
            ]
            # Check if it's a single video URL
            is_single_video = any(pattern in url.lower() for pattern in single_video_patterns)
            if is_single_video:
                return False
            
            # Profile/page patterns
            profile_patterns = [
                '/videos', '/reels', '/profile.php', '/pages/', '/people/'
            ]
            is_profile = any(pattern in clean_url for pattern in profile_patterns)
            return is_profile
        
        # Twitter profile patterns
        elif 'twitter.com' in clean_url or 'x.com' in clean_url:
            # Twitter profile: twitter.com/username (without /status/)
            return '/status/' not in clean_url
        
        return False
    
    def get_profile_videos(self, profile_url, max_videos=200):
        """Extract video URLs from a profile/channel"""
        try:
            # Platform-specific options for better extraction
            platform = self.detect_platform(profile_url)
            
            # Special handling for Facebook - use custom extractor
            if platform == 'Facebook' and FACEBOOK_HELPER_AVAILABLE:
                print(f"Using Facebook helper for: {profile_url}")
                # Fetch 3x more videos to account for high failure rate on Facebook
                # Many Facebook video IDs are invalid, private, or require login
                fetch_count = int(max_videos * 3) if max_videos else 500
                result = get_facebook_profile_videos(profile_url, fetch_count, callback=print)
                
                if result['success'] and result['videos']:
                    videos = []
                    for v in result['videos']:
                        videos.append({
                            'url': v['url'],
                            'title': v.get('title', 'Facebook Video'),
                            'id': v.get('id', ''),
                            'duration': 0,
                            'uploader': 'Facebook',
                            'upload_date': '',
                            'view_count': 0
                        })
                    
                    return {
                        'success': True,
                        'videos': videos,
                        'profile_name': 'Facebook Profile',
                        'total_found': len(videos),
                        'platform': 'Facebook',
                        'raw_total': len(videos)
                    }
                else:
                    # Fall back to yt-dlp method
                    print("Facebook helper failed, trying yt-dlp...")
            
            opts = {
                'quiet': False,  # Enable some output for debugging
                'no_warnings': False,
                'extract_flat': True,  # Only get URLs, don't download
                'ignoreerrors': True,  # Continue on errors
                'no_color': True,  # Disable ANSI colors
            }
            
            # Set appropriate limits based on platform and user preference
            if max_videos and max_videos > 0:
                opts['playlistend'] = max_videos
            else:
                # No limit - get all videos (can be slow for large channels)
                pass
            
            # Platform-specific optimizations
            if platform == 'TikTok':
                # TikTok-specific options for better profile extraction
                opts.update({
                    'extractor_args': {
                        'tiktok': {
                            'max_pages': 10,  # Increase page limit for TikTok
                        }
                    }
                })
            elif platform == 'YouTube':
                # YouTube-specific options
                opts.update({
                    'playlistreverse': False,  # Get newest first
                })
            elif platform == 'Facebook':
                # Facebook-specific options
                # Note: Don't use cookiesfrombrowser - causes errors when browser is open
                # The Facebook helper handles extraction without needing cookies
                opts['extract_flat'] = 'in_playlist'
            
            print(f"Extracting videos from {platform} profile: {profile_url}")
            print(f"Max videos limit: {max_videos if max_videos else 'No limit'}")
            
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(profile_url, download=False)
                
                if not info:
                    return {'success': False, 'error': 'Could not extract profile information'}
                
                print(f"Raw info type: {type(info)}")
                print(f"Info keys: {list(info.keys()) if isinstance(info, dict) else 'Not a dict'}")
                
                # Handle different types of results
                videos = []
                
                def extract_videos_from_entries(entries, depth=0):
                    """Recursively extract videos from nested entries"""
                    extracted = []
                    for i, entry in enumerate(entries):
                        if entry is None:
                            continue
                        
                        # Check if this entry has nested entries (like YouTube tabs)
                        if 'entries' in entry and entry['entries']:
                            print(f"{'  '*depth}Found nested playlist: {entry.get('title', 'Unknown')} with {len(entry['entries'])} items")
                            nested = extract_videos_from_entries(entry['entries'], depth + 1)
                            extracted.extend(nested)
                        elif entry.get('url') or entry.get('webpage_url'):
                            # This is an actual video
                            url = entry.get('url') or entry.get('webpage_url')
                            video_info = {
                                'url': url,
                                'title': entry.get('title', f'Video {i+1}'),
                                'id': entry.get('id', ''),
                                'duration': entry.get('duration', 0),
                                'uploader': entry.get('uploader', info.get('uploader', 'Unknown')),
                                'upload_date': entry.get('upload_date', ''),
                                'view_count': entry.get('view_count', 0)
                            }
                            extracted.append(video_info)
                        elif entry.get('id'):
                            # Has ID but no URL - construct YouTube URL
                            video_id = entry.get('id')
                            if platform == 'YouTube' and video_id:
                                url = f'https://www.youtube.com/watch?v={video_id}'
                                video_info = {
                                    'url': url,
                                    'title': entry.get('title', f'Video {i+1}'),
                                    'id': video_id,
                                    'duration': entry.get('duration', 0),
                                    'uploader': entry.get('uploader', info.get('uploader', 'Unknown')),
                                    'upload_date': entry.get('upload_date', ''),
                                    'view_count': entry.get('view_count', 0)
                                }
                                extracted.append(video_info)
                    return extracted
                
                if 'entries' in info:
                    print(f"Found {len(info['entries'])} top-level entries")
                    videos = extract_videos_from_entries(info['entries'])
                
                elif info.get('url'):
                    print("Single video found (unusual for profile)")
                    # Single video (shouldn't happen for profiles, but handle it)
                    video_info = {
                        'url': info['url'],
                        'title': info.get('title', 'Unknown'),
                        'id': info.get('id', ''),
                        'duration': info.get('duration', 0),
                        'uploader': info.get('uploader', 'Unknown'),
                        'upload_date': info.get('upload_date', ''),
                        'view_count': info.get('view_count', 0)
                    }
                    videos.append(video_info)
                else:
                    print("No entries or URL found in info")
                    print(f"Available keys: {list(info.keys())}")
                
                # Limit to max_videos if specified
                if max_videos and len(videos) > max_videos:
                    videos = videos[:max_videos]
                
                print(f"Successfully extracted {len(videos)} videos")
                
                return {
                    'success': True,
                    'videos': videos,
                    'profile_name': info.get('uploader', info.get('title', info.get('channel', 'Unknown'))),
                    'total_found': len(videos),
                    'platform': platform,
                    'raw_total': info.get('playlist_count', len(videos))  # Sometimes yt-dlp knows the real total
                }
                
        except Exception as e:
            error_msg = str(e)
            print(f"Error extracting profile: {error_msg}")
            
            # Clean up error message
            import re
            error_msg = re.sub(r'\x1b\[[0-9;]*m', '', error_msg)
            error_msg = re.sub(r'^ERROR:\s*', '', error_msg)
            
            return {
                'success': False,
                'error': self.get_user_friendly_error(error_msg, profile_url),
                'technical_error': error_msg
            }
    
    def validate_url(self, url):
        """Validate URL and provide helpful feedback"""
        if not url.startswith(('http://', 'https://')):
            return False, "URL must start with http:// or https://"
        
        # Check for known problematic patterns
        if 'facebook.com/people/' in url and 'pfbid' in url:
            return False, ("This appears to be a Facebook profile URL. "
                          "Please use direct video post URLs instead:\n"
                          "- facebook.com/watch/?v=VIDEO_ID\n"
                          "- facebook.com/USERNAME/videos/VIDEO_ID")
        
        if 'facebook.com/share/' in url:
            return False, ("This is a Facebook share URL. "
                          "Please copy the direct video URL from the post instead.")
        
        # Add more validation rules as needed
        return True, "URL appears valid"
    
    def get_user_friendly_error(self, error_msg, url):
        """Convert technical error messages to user-friendly ones"""
        error_lower = error_msg.lower()
        
        if 'unsupported url' in error_lower:
            if 'facebook.com' in url:
                return "This Facebook URL format is not supported. Try using direct video post URLs instead."
            elif 'instagram.com' in url:
                return "This Instagram URL format is not supported. Try using direct post URLs."
            elif 'tiktok.com' in url:
                return "This TikTok URL format is not supported. Try using direct video URLs."
            else:
                return "This URL format is not supported by the video downloader."
        
        elif 'private video' in error_lower or 'access denied' in error_lower:
            return "This video is private or access is restricted."
        
        elif 'video not found' in error_lower or '404' in error_lower:
            return "Video not found. The URL may be incorrect or the video may have been deleted."
        
        elif 'geo' in error_lower and 'block' in error_lower:
            return "This video is geo-blocked and not available in your region."
        
        elif 'age' in error_lower and 'restrict' in error_lower:
            return "This video is age-restricted and cannot be accessed."
        
        # Permission and file access errors
        elif 'permission denied' in error_lower or 'errno 13' in error_lower:
            return "File access denied. Close File Explorer and try again, or check antivirus settings."
        
        elif 'winerror 10054' in error_lower or 'connection was forcibly closed' in error_lower:
            return "Connection interrupted by server. The download will retry automatically."
        
        elif 'connection' in error_lower and ('reset' in error_lower or 'refused' in error_lower):
            return "Connection failed. Check your internet connection and try again."
        
        elif 'timeout' in error_lower:
            return "Connection timed out. The server may be slow or your connection unstable."
        
        # JavaScript runtime warning (not an error, but informational)
        elif 'javascript runtime' in error_lower or 'js runtime' in error_lower:
            return "Some video formats unavailable (JS runtime not installed). Download will continue with available formats."
        
        # SABR streaming (YouTube specific)
        elif 'sabr streaming' in error_lower:
            return "YouTube is using new streaming format. Download will continue with available formats."
        
        # Rate limiting
        elif 'rate limit' in error_lower or 'too many requests' in error_lower:
            return "Too many requests. Please wait a moment before trying again."
        
        # Return cleaned original message if no specific case matches
        return error_msg

    def get_info(self, url):
        try:
            # Add more detailed options for better error reporting
            opts = {
                'quiet': False,  # Allow some output for debugging
                'no_warnings': False,
                'extract_flat': False,
                'ignoreerrors': False,
                'no_color': True  # Disable ANSI color codes in error messages
            }
            
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                # For TikTok, use description as title (contains full caption)
                platform = self.detect_platform(url)
                if 'TikTok' in platform:
                    # TikTok: description has full caption, title is truncated
                    title = info.get('description') or info.get('title', 'Unknown')
                else:
                    title = info.get('title', 'Unknown')
                
                return {
                    'title': title,
                    'uploader': info.get('uploader', 'Unknown'),
                    'duration': info.get('duration', 0),
                    'views': info.get('view_count', 0),
                    'platform': platform
                }
        except Exception as e:
            # Clean up error message by removing ANSI color codes
            error_msg = str(e)
            # Remove ANSI escape sequences
            import re
            error_msg = re.sub(r'\x1b\[[0-9;]*m', '', error_msg)
            # Remove "ERROR:" prefix if present
            error_msg = re.sub(r'^ERROR:\s*', '', error_msg)
            
            # Get user-friendly error message
            friendly_msg = self.get_user_friendly_error(error_msg, url)
            
            return {
                'error': True,
                'message': friendly_msg,
                'technical_error': error_msg,  # Keep original for debugging
                'platform': self.detect_platform(url)
            }
    
    def sanitize_filename(self, filename):
        """Sanitize filename for Windows compatibility"""
        import re
        # Remove or replace problematic characters
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)  # Windows forbidden chars
        filename = re.sub(r'[^\x00-\x7F]+', '_', filename)  # Non-ASCII characters
        filename = re.sub(r'[^\w\s-]', '_', filename)       # Keep only word chars, spaces, hyphens
        filename = re.sub(r'\s+', ' ', filename)            # Collapse multiple spaces
        filename = filename.strip()                         # Remove leading/trailing spaces
        
        # Limit length (Windows max filename is ~255, but path limit is 260)
        if len(filename) > 200:
            filename = filename[:200]
        
        # Ensure it's not empty
        if not filename:
            filename = "video"
        
        return filename

    def download(self, url, quality='best', audio_only=False, subtitle=False, format_pref='Force H.264 (Compatible)', force_convert=False, use_caption=True, mute_video=False, callback=None, retry_count=0):
        """Download video with professional error handling and automatic recovery"""
        MAX_RETRIES = 3
        
        # Reset abort flag at start of each download
        self.abort_download = False
        
        # Clean up any leftover temp files before starting
        self.cleanup_temp_files()
        
        # Detect platform to use appropriate filename template
        platform = self.detect_platform(url)
        
        # For TikTok, use description (full caption) instead of title (truncated)
        if 'TikTok' in platform:
            safe_template = str(self.output_dir / '%(description)s.%(ext)s')
        else:
            safe_template = str(self.output_dir / '%(title)s.%(ext)s')
        
        opts = {
            'outtmpl': safe_template,
            'retries': 5,                # Increased retries
            'fragment_retries': 10,      # More fragment retries for HLS streams
            'file_access_retries': 5,    # Retry on file access errors
            'skip_unavailable_fragments': True,  # Skip bad fragments instead of failing
            'restrictfilenames': False,  # Keep spaces, don't replace with _
            'windowsfilenames': True,    # Make filenames Windows-compatible
            'trim_file_name': 210,       # Allow longer filenames (max 210 for Windows)
            'noprogress': False,         # Show progress
            'continuedl': True,          # Continue partial downloads
            'nopart': False,             # Use .part files for resumable downloads
            'buffersize': 1024 * 16,     # 16KB buffer for smoother downloads
            'http_chunk_size': 10485760, # 10MB chunks for better reliability
        }
        
        # Note: Don't use cookiesfrombrowser here - it causes errors when browser is open
        # The direct Facebook downloader handles cookies separately
        
        # Add mute video postprocessor (removes audio track)
        if mute_video and not audio_only:
            opts['postprocessors'] = opts.get('postprocessors', [])
            opts['postprocessors'].append({
                'key': 'FFmpegVideoRemuxer',
                'preferedformat': 'mp4',
            })
            opts['postprocessor_args'] = {
                'FFmpegVideoRemuxer': ['-an']  # -an removes audio
            }
        
        # Create abort-aware callback wrapper
        original_callback = callback
        def abort_aware_callback(msg):
            if self.abort_download:
                raise Exception("Download aborted by user")
            if original_callback:
                original_callback(msg)
        
        # Track permission errors for smart retry
        permission_error_count = [0]
        last_filename = [None]
        
        if callback:
            def hook(d):
                # Check abort flag on every progress update
                if self.abort_download:
                    raise Exception("Download aborted by user")
                
                # Track the filename for cleanup
                if 'filename' in d:
                    last_filename[0] = d['filename']
                
                if d['status'] == 'downloading':
                    if 'total_bytes' in d:
                        pct = d['downloaded_bytes'] / d['total_bytes'] * 100
                        speed = d.get('speed', 0)
                        speed_str = f" @ {speed/1024/1024:.1f}MB/s" if speed else ""
                        abort_aware_callback(f"Downloading: {pct:.1f}%{speed_str}")
                    elif 'total_bytes_estimate' in d:
                        pct = d['downloaded_bytes'] / d['total_bytes_estimate'] * 100
                        abort_aware_callback(f"Downloading: {pct:.1f}% (estimated)")
                    elif 'fragment_index' in d and 'fragment_count' in d:
                        # HLS/fragmented download progress
                        frag_pct = d['fragment_index'] / d['fragment_count'] * 100
                        abort_aware_callback(f"Downloading: {frag_pct:.1f}% (fragment {d['fragment_index']}/{d['fragment_count']})")
                elif d['status'] == 'finished':
                    abort_aware_callback(f"Completed: {Path(d['filename']).name}")
                elif d['status'] == 'error':
                    # Handle errors in progress hook
                    error_msg = d.get('error', 'Unknown error')
                    if 'permission denied' in str(error_msg).lower():
                        permission_error_count[0] += 1
                        if last_filename[0]:
                            self.cleanup_temp_files(last_filename[0])
            opts['progress_hooks'] = [hook]
        
        # For TikTok, first get info and clean the description, then download
        if 'TikTok' in platform:
            try:
                with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                    info = ydl.extract_info(url, download=False)
                    if info and info.get('description'):
                        # Keep description with # symbols, only remove problematic Windows chars
                        clean_desc = info['description']
                        # Remove only problematic Windows filename chars (# is allowed)
                        for char in ['<', '>', ':', '"', '/', '\\', '|', '?', '*']:
                            clean_desc = clean_desc.replace(char, '')
                        # Calculate max filename length based on output path
                        # Windows max path is 260, leave room for extension (.mp4 = 4 chars)
                        output_path_len = len(str(self.output_dir)) + 1  # +1 for separator
                        max_filename_len = 255 - output_path_len - 10  # -10 for extension and safety
                        max_filename_len = max(50, min(max_filename_len, 210))  # Between 50-210
                        # Use cleaned description as title for filename
                        safe_template = str(self.output_dir / f'{clean_desc[:max_filename_len]}.%(ext)s')
                        opts['outtmpl'] = safe_template
            except:
                pass  # Fall back to default template
        
        # Helper function to convert quality string to height
        def get_height_from_quality(q):
            quality_map = {
                '8K': '4320',
                '4K': '2160',
                '2K': '1440',
                '1080p': '1080',
                '720p': '720',
                '480p': '480',
                '360p': '360',
                '240p': '240',
                '144p': '144'
            }
            return quality_map.get(q, q[:-1] if q.endswith('p') else q)
        
        if audio_only:
            opts['format'] = 'bestaudio/best'
            opts['postprocessors'] = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3'}]
        else:
            # Handle different format preferences with aggressive codec control
            if format_pref == 'Force H.264 (Compatible)':
                # Most aggressive approach for different platforms
                platform = self.detect_platform(url)
                
                if 'TikTok' in platform:
                    # TikTok-specific format selection to avoid HEVC
                    if quality == 'best':
                        opts['format'] = 'best[vcodec*=avc1]/best[vcodec*=h264]/best[format_id*=download]/best[format_id!*=bytevc1]/best'
                    else:
                        height = get_height_from_quality(quality)
                        opts['format'] = f'best[vcodec*=avc1][height<={height}]/best[vcodec*=h264][height<={height}]/best[format_id*=download][height<={height}]/best[format_id!*=bytevc1][height<={height}]/best[height<={height}]'
                elif 'Facebook' in platform:
                    # Facebook-specific format selection - use format IDs that Facebook provides
                    if quality == 'best':
                        # Facebook uses 'hd' and 'sd' format IDs, try those first
                        opts['format'] = 'hd/sd/best[ext=mp4]/best'
                    else:
                        height = get_height_from_quality(quality)
                        # For quality selection, still try hd/sd first as fallback
                        opts['format'] = f'best[ext=mp4][height<={height}]/best[height<={height}]/hd/sd/best'
                elif 'YouTube' in platform:
                    # YouTube-specific format selection to handle SABR streaming
                    # Prefer formats that don't require JS runtime
                    if quality == 'best':
                        opts['format'] = 'best[vcodec*=avc1]/best[vcodec*=h264]/bestvideo[vcodec*=avc1]+bestaudio/best'
                    else:
                        height = get_height_from_quality(quality)
                        opts['format'] = f'best[vcodec*=avc1][height<={height}]/best[vcodec*=h264][height<={height}]/bestvideo[vcodec*=avc1][height<={height}]+bestaudio/best[height<={height}]'
                    
                    # Add YouTube-specific extractor args to improve reliability
                    opts['extractor_args'] = opts.get('extractor_args', {})
                    opts['extractor_args']['youtube'] = {
                        'player_client': ['android', 'web'],  # Use multiple clients for better format availability
                        'skip': ['dash', 'hls'],  # Skip problematic formats when possible
                    }
                else:
                    # General format selection for other platforms
                    if quality == 'best':
                        opts['format'] = 'best[vcodec*=avc1]/best[vcodec*=h264]/best[ext=mp4]/best'
                    else:
                        height = get_height_from_quality(quality)
                        opts['format'] = f'best[vcodec*=avc1][height<={height}]/best[vcodec*=h264][height<={height}]/best[ext=mp4][height<={height}]/best[height<={height}]'
                
                # Add post-processor to convert to H.264 if HEVC is still downloaded
                if force_convert or format_pref == 'Force H.264 (Compatible)':
                    try:
                        # Only add converter if FFmpeg is available
                        import subprocess
                        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
                        opts['postprocessors'] = [{
                            'key': 'FFmpegVideoConvertor',
                            'preferedformat': 'mp4',
                        }]
                        if callback:
                            callback("[*] FFmpeg available - will convert if needed")
                    except (subprocess.CalledProcessError, FileNotFoundError):
                        if callback:
                            callback("[!] FFmpeg not found - downloading best available format")
                        # Don't add post-processor if FFmpeg is not available
                
            elif format_pref == 'Convert to H.264':
                # Download any format but convert to H.264 (only if FFmpeg available)
                opts['format'] = 'best' if quality == 'best' else f'best[height<={get_height_from_quality(quality)}]'
                try:
                    import subprocess
                    subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
                    opts['postprocessors'] = [{
                        'key': 'FFmpegVideoConvertor',
                        'preferedformat': 'mp4',
                    }]
                    if callback:
                        callback("[*] Will convert to H.264 using FFmpeg")
                except (subprocess.CalledProcessError, FileNotFoundError):
                    if callback:
                        callback("[!] FFmpeg not found - downloading without conversion")
                
            elif format_pref == 'mp4 (H.264)':
                # Try to get H.264 but don't convert
                if quality == 'best':
                    opts['format'] = 'best[ext=mp4][vcodec*=avc1]/best[ext=mp4][vcodec*=h264]/best[ext=mp4]/best'
                else:
                    height = get_height_from_quality(quality)
                    opts['format'] = f'best[ext=mp4][vcodec*=avc1][height<={height}]/best[ext=mp4][vcodec*=h264][height<={height}]/best[ext=mp4][height<={height}]/best[height<={height}]'
                    
            elif format_pref == 'webm':
                height = get_height_from_quality(quality)
                opts['format'] = 'best[ext=webm]/best' if quality == 'best' else f'best[ext=webm][height<={height}]/best[height<={height}]'
            else:  # 'any'
                height = get_height_from_quality(quality)
                opts['format'] = 'best' if quality == 'best' else f'best[height<={height}]'
        
        if subtitle:
            opts['writesubtitles'] = True
        
        try:
            if callback:
                callback(f"Platform: {self.detect_platform(url)}")
            
            # Store the downloaded file path
            downloaded_file = None
            
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    # Extract info to get the final filename
                    info = ydl.extract_info(url, download=False)
                    expected_filename = ydl.prepare_filename(info)
                    
                    # Download the video
                    ydl.download([url])
                    
                    # The actual file might have a different extension after processing
                    base_path = Path(expected_filename).with_suffix('')
                    possible_extensions = ['.mp4', '.webm', '.mkv', '.avi', '.mov']
                    
                    for ext in possible_extensions:
                        potential_file = base_path.with_suffix(ext)
                        if potential_file.exists():
                            downloaded_file = potential_file
                            break
                    
                    # If not found, try the original expected filename
                    if not downloaded_file and Path(expected_filename).exists():
                        downloaded_file = Path(expected_filename)
                        
            except Exception as format_error:
                # If format selection fails, try with simpler format
                if callback:
                    callback("[!] Format selection failed, trying simpler format...")
                
                # Create simpler options
                simple_opts = opts.copy()
                
                # For Facebook, try hd/sd format IDs first, then fall back to best
                platform = self.detect_platform(url)
                if 'Facebook' in platform:
                    simple_opts['format'] = 'hd/sd/best'
                else:
                    simple_opts['format'] = 'best'  # Just get the best available format
                
                with yt_dlp.YoutubeDL(simple_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    expected_filename = ydl.prepare_filename(info)
                    ydl.download([url])
                    
                    # Find the downloaded file
                    base_path = Path(expected_filename).with_suffix('')
                    possible_extensions = ['.mp4', '.webm', '.mkv', '.avi', '.mov']
                    
                    for ext in possible_extensions:
                        potential_file = base_path.with_suffix(ext)
                        if potential_file.exists():
                            downloaded_file = potential_file
                            break
                    
                    if not downloaded_file and Path(expected_filename).exists():
                        downloaded_file = Path(expected_filename)
            
            return {'success': True, 'file_path': downloaded_file}
            
        except Exception as e:
            error_str = str(e).lower()
            
            # Clean up temp files after error
            if last_filename[0]:
                self.cleanup_temp_files(last_filename[0])
            
            # Handle permission denied errors with smart retry
            if 'permission denied' in error_str or 'errno 13' in error_str:
                if retry_count < MAX_RETRIES:
                    if callback:
                        callback(f"[!] File access error, cleaning up and retrying ({retry_count + 1}/{MAX_RETRIES})...")
                    
                    # Clean up all temp files
                    self.cleanup_temp_files()
                    
                    # Wait a moment for file handles to release
                    import time
                    time.sleep(2)
                    
                    # Retry the download
                    return self.download(url, quality, audio_only, subtitle, format_pref, 
                                        force_convert, use_caption, mute_video, callback, retry_count + 1)
                else:
                    if callback:
                        callback("[X] File access error persists. Try:")
                        callback("   - Close File Explorer in the download folder")
                        callback("   - Add folder to antivirus exclusions")
                        callback("   - Delete .ytdl and .part files manually")
                    return {'success': False, 'error': 'Permission denied - file locked by another process'}
            
            # Handle connection errors with retry
            if 'connection' in error_str or 'timeout' in error_str or 'winError 10054' in error_str.lower():
                if retry_count < MAX_RETRIES:
                    if callback:
                        callback(f"[!] Connection error, retrying ({retry_count + 1}/{MAX_RETRIES})...")
                    
                    import time
                    time.sleep(3 * (retry_count + 1))  # Exponential backoff
                    
                    return self.download(url, quality, audio_only, subtitle, format_pref,
                                        force_convert, use_caption, mute_video, callback, retry_count + 1)
            
            # For Facebook errors, always try direct download as fallback
            platform = self.detect_platform(url)
            if 'Facebook' in platform and try_direct_facebook_download:
                if callback:
                    callback("[!] yt-dlp failed, trying direct Facebook download...")
                
                # Try direct download method
                try:
                    direct_result = try_direct_facebook_download(
                        url, 
                        str(self.output_dir), 
                        callback=callback
                    )
                    if direct_result['success']:
                        return {'success': True, 'file_path': Path(direct_result['file_path'])}
                    else:
                        if callback:
                            callback(f"[!] Direct download also failed: {direct_result['error']}")
                except Exception as direct_error:
                    if callback:
                        callback(f"[!] Direct download error: {direct_error}")
            
            # Final cleanup
            self.cleanup_temp_files()
            
            # Provide user-friendly error message
            friendly_error = self.get_user_friendly_error(str(e), url)
            if callback:
                callback(f"[X] Error: {friendly_error}")
            return {'success': False, 'error': friendly_error}


class Worker(QThread):
    progress = pyqtSignal(str)
    progress_percent = pyqtSignal(int, str)  # percentage, message
    done = pyqtSignal(bool, str, str)  # success, message, file_path
    info = pyqtSignal(dict)
    
    def __init__(self, dl, url, opts):
        super().__init__()
        self.dl, self.url, self.opts = dl, url, opts
        self.stopped = False
    
    def stop(self):
        """Stop the worker"""
        self.stopped = True
    
    def run(self):
        try:
            if self.stopped:
                return
                
            if self.opts.get('op') == 'info':
                self.progress_percent.emit(10, "Connecting...")
                self.progress.emit("[?] Getting video information...")
                
                self.progress_percent.emit(30, "Extracting info...")
                data = self.dl.get_info(self.url)
                
                if data and not data.get('error'):
                    self.progress_percent.emit(100, "Info retrieved")
                    self.info.emit(data)
                    # Don't log success message since we show dialog
                    self.done.emit(True, "", "")  # Empty message to avoid log clutter
                elif data and data.get('error'):
                    error_msg = data.get('message', 'Unknown error')
                    self.progress_percent.emit(100, "Failed")
                    self.progress.emit(f"[X] Error: {error_msg}")
                    self.done.emit(False, f"Failed to get info: {error_msg}", "")
                else:
                    self.progress_percent.emit(100, "Failed")
                    self.done.emit(False, "Failed to get info: No data returned", "")
            else:
                self.progress_percent.emit(5, "Starting download...")
                
                # Create a progress callback that updates percentage
                def progress_callback(message):
                    self.progress.emit(message)
                    # Try to extract percentage from yt-dlp progress messages
                    if "%" in message and "Downloading:" in message:
                        try:
                            # Extract percentage from messages like "Downloading: 45.2%"
                            percent_str = message.split("%")[0].split()[-1]
                            percent = float(percent_str)
                            self.progress_percent.emit(int(percent), "Downloading...")
                        except:
                            pass
                    elif "Completed:" in message:
                        self.progress_percent.emit(95, "Processing...")
                
                result = self.dl.download(
                    self.url,
                    self.opts.get('quality', 'best'),
                    self.opts.get('audio', False),
                    self.opts.get('subtitle', False),
                    self.opts.get('format', 'Force H.264 (Compatible)'),
                    self.opts.get('convert', False),
                    self.opts.get('use_caption', True),
                    self.opts.get('mute', False),
                    progress_callback
                )
                
                if result['success']:
                    self.progress_percent.emit(100, "Complete")
                    file_path = str(result['file_path']) if result['file_path'] else ""
                    self.progress.emit(f"[?] Worker: success=True, file_path='{file_path}'")
                    self.done.emit(True, "Download complete", file_path)
                else:
                    self.progress_percent.emit(100, "Failed")
                    self.progress.emit(f"[?] Worker: success=False, error='{result.get('error', 'Unknown error')}'")
                    self.done.emit(False, f"Download failed: {result.get('error', 'Unknown error')}", "")
                    
        except Exception as e:
            self.done.emit(False, str(e), "")


class MainWindow(QMainWindow):
    VERSION = "1.1.8"
    APP_ID = None  # Unique installation ID
    
    def __init__(self):
        super().__init__()
        self.dl = VideoDownloader()
        self.worker = None
        self.multi_worker = None  # For multiple downloads
        self._loading_settings = False  # Flag to prevent auto-save during loading
        
        # Initialize settings for persistence
        self.settings = QSettings("VideoDownloader", "VideoDownloaderPro")
        
        # Generate or load unique App ID for this installation
        self.app_id = self.get_or_create_app_id()
        
        self.setup_ui()
        self.load_settings()  # Load saved settings after UI setup
        
        # Add a small delay to ensure UI is fully ready, then retry setting directory
        QTimer.singleShot(100, self.retry_set_directory)
        
        # Check for FFmpeg and show info
        QTimer.singleShot(500, self.check_ffmpeg)
        
        # Check for updates
        QTimer.singleShot(2000, self.check_for_updates)
        
        # Clean up any old log persistence and show welcome message
        QTimer.singleShot(1000, self.setup_fresh_log)
        
        # Set up periodic auto-save for text areas (every 30 seconds)
        self.auto_save_timer = QTimer()
        self.auto_save_timer.timeout.connect(self.periodic_save)
        self.auto_save_timer.start(30000)  # 30 seconds
    
    def update_license_display(self):
        """Update the license info display in title bar"""
        try:
            if LICENSE_CLIENT_AVAILABLE:
                client = get_license_client()
                if client.is_valid() and client.license_key:
                    key_short = client.license_key[:4] + "..." + client.license_key[-4:]
                    days = client.get_days_remaining()
                    
                    if days is None:
                        days_text = "Lifetime"
                        color = "#22c55e"  # Green for lifetime
                    elif days > 30:
                        days_text = f"{days} days"
                        color = "#22c55e"  # Green
                    elif days > 7:
                        days_text = f"{days} days"
                        color = "#f59e0b"  # Orange/yellow warning
                    elif days > 0:
                        days_text = f"{days} days"
                        color = "#ef4444"  # Red urgent
                    else:
                        days_text = "Expired"
                        color = "#ef4444"
                    
                    self.license_info_label.setText(f"🔑 {key_short} • {days_text}")
                    self.license_info_label.setStyleSheet(f"color: {color}; border: 0px; background: none; outline: 0px; margin-right: 15px;")
                else:
                    self.license_info_label.setText("🔑 No License")
                    self.license_info_label.setStyleSheet("color: #6b7280; border: 0px; background: none; outline: 0px; margin-right: 15px;")
            else:
                self.license_info_label.setText("")
        except Exception as e:
            self.license_info_label.setText("")
    
    def get_or_create_app_id(self):
        """Get existing App ID or create a new unique one for this installation"""
        import uuid
        
        # Try to load existing App ID
        app_id = self.settings.value("app_id", None)
        
        if not app_id:
            # Generate new unique App ID
            app_id = str(uuid.uuid4()).upper()[:8]  # Short 8-char ID like "A1B2C3D4"
            self.settings.setValue("app_id", app_id)
            self.settings.sync()
        
        return app_id
    
    def get_app_info(self):
        """Get app info including App ID for display/management"""
        return {
            "app_id": self.app_id,
            "version": self.VERSION,
            "machine_id": get_license_client().machine_hash[:12] if LICENSE_CLIENT_AVAILABLE else "N/A"
        }
    
    def setup_fresh_log(self):
        """Ensure log and multiple download text areas start completely fresh"""
        # Clear any existing content
        self.log_text.clear()
        if hasattr(self, 'info_text'):
            self.info_text.clear()
        if hasattr(self, 'multi_info_text'):
            self.multi_info_text.clear()
        if hasattr(self, 'multi_progress_text'):
            self.multi_progress_text.clear()
        
        # Remove any old content from settings if it exists
        settings_to_remove = ["log_content", "multi_info_content", "multi_progress_content", "info_content"]
        removed_any = False
        
        for setting in settings_to_remove:
            if self.settings.contains(setting):
                self.settings.remove(setting)
                removed_any = True
        
        if removed_any:
            self.settings.sync()
            self.log("[~] Removed old text content persistence - all text areas starting fresh")
        
        # Show welcome message
        self.show_welcome_message()
        
        # Debug: Show what settings keys exist
        all_keys = self.settings.allKeys()
        text_related_keys = [key for key in all_keys if any(word in key.lower() for word in ['log', 'info', 'progress', 'content'])]
        if text_related_keys:
            self.log(f"[?] Debug: Found text-related settings keys: {text_related_keys}")
        else:
            self.log("[OK] Confirmed: No text content settings found - all text areas will start fresh")

    def update_download_status(self, status, color="#58a6ff"):
        """Update the single download status label"""
        if hasattr(self, 'download_status_label'):
            self.download_status_label.setText(status)
            self.download_status_label.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 11px; border: none; background: transparent;")

    def clear_log(self):
        """Clear log and show a fresh start message"""
        self.log_text.clear()
        self.log("[N] Log cleared - Ready for new operations")

    def show_welcome_message(self):
        """Show welcome message in log since it doesn't persist"""
        self.log(f"[V] VIDT - Video Downloader Tool v{self.VERSION} - Ready!")
        self.log("[*] Tip: Use the Help button ([?]) in Multiple Download tab for URL format guidance")
        self.log("[L] Paste video URLs and click 'Get Info' to check compatibility")
        self.log("[S] All your settings and URLs are automatically saved")
        self.log("-" * 50)

    def check_ffmpeg(self):
        """Check if FFmpeg is available and provide guidance"""
        import subprocess
        try:
            # Try to run ffmpeg to check if it's available
            subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
            self.log("[OK] FFmpeg is available - full format conversion supported")
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.log("[!] FFmpeg not found - some format conversions may not work")
            self.log("[*] To install FFmpeg:")
            self.log("   1. Download from: https://ffmpeg.org/download.html")
            self.log("   2. Or use: winget install ffmpeg (Windows)")
            self.log("   3. Add to PATH environment variable")

    def check_for_updates(self):
        """Check for new version from GitHub"""
        self.log("[~] Checking for updates...")
        
        try:
            import requests
            
            # Fetch version.json from GitHub raw
            url = "https://raw.githubusercontent.com/phattra-dev/vidttool/main/version.json"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                latest_version = data.get('version', '0.0.0')
                
                # Compare versions
                def version_tuple(v):
                    try:
                        return tuple(map(int, v.split('.')))
                    except:
                        return (0, 0, 0)
                
                current = version_tuple(self.VERSION)
                latest = version_tuple(latest_version)
                
                if latest > current:
                    # New version available
                    self.log(f"[!] Update available: v{latest_version}")
                    changelog = data.get('changelog', [])
                    download_url = data.get('download_url', '')
                    self.show_update_dialog(latest_version, changelog, download_url)
                else:
                    self.log(f"[OK] You have the latest version (v{self.VERSION})")
            else:
                self.log(f"[!] Update check failed: HTTP {response.status_code}")
        except Exception as e:
            self.log(f"[!] Update check failed: {e}")

    def show_update_dialog(self, new_version, changelog, download_url):
        """Show update available dialog with auto-update option"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Update Available")
        dialog.setFixedSize(500, 420)
        dialog.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #1a1f2e, stop:1 #0d1117);
                color: #e6edf3;
            }
            QLabel { color: #e6edf3; background: transparent; }
            QProgressBar {
                background: #21262d;
                border: 1px solid #30363d;
                border-radius: 6px;
                height: 20px;
                text-align: center;
                color: white;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #238636, stop:1 #2ea043);
                border-radius: 5px;
            }
            QPushButton {
                background: #238636;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 12px 24px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover { background: #2ea043; }
            QPushButton:disabled { background: #21262d; color: #484f58; }
            QPushButton#later {
                background: transparent;
                border: 1px solid #444c56;
                color: #8b949e;
            }
            QPushButton#later:hover { border-color: #58a6ff; color: #e6edf3; }
        """)
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(16)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Header
        header = QLabel(f"🚀 New Version Available!")
        header.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)
        
        # Version info
        version_info = QLabel(f"v{self.VERSION} → v{new_version}")
        version_info.setFont(QFont("Segoe UI", 14))
        version_info.setStyleSheet("color: #58a6ff;")
        version_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version_info)
        
        # Changelog
        changelog_label = QLabel("What's New:")
        changelog_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        layout.addWidget(changelog_label)
        
        changelog_text = QTextEdit()
        changelog_text.setReadOnly(True)
        changelog_text.setStyleSheet("""
            QTextEdit {
                background: rgba(45,51,59,0.5);
                border: 1px solid #30363d;
                border-radius: 8px;
                padding: 10px;
                color: #8b949e;
                font-size: 12px;
            }
        """)
        changelog_text.setPlainText("\n".join([f"• {item}" for item in changelog[:8]]))
        changelog_text.setMaximumHeight(120)
        layout.addWidget(changelog_text)
        
        # Progress bar (hidden initially)
        progress_bar = QProgressBar()
        progress_bar.setVisible(False)
        progress_bar.setFormat("%p% - Downloading update...")
        layout.addWidget(progress_bar)
        
        # Status label
        status_label = QLabel("")
        status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_label.setStyleSheet("color: #8b949e; font-size: 12px;")
        layout.addWidget(status_label)
        
        layout.addStretch()
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        
        later_btn = QPushButton("Remind Me Later")
        later_btn.setObjectName("later")
        later_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(later_btn)
        
        update_btn = QPushButton("⬇ Update Now")
        btn_layout.addWidget(update_btn)
        
        layout.addLayout(btn_layout)
        
        # Store references for the update function
        dialog.progress_bar = progress_bar
        dialog.status_label = status_label
        dialog.update_btn = update_btn
        dialog.later_btn = later_btn
        dialog.download_url = download_url
        dialog.new_version = new_version
        
        def start_update():
            self.download_and_install_update(dialog)
        
        update_btn.clicked.connect(start_update)
        dialog.exec()

    def download_and_install_update(self, dialog):
        """Download update and install it automatically"""
        import requests
        import tempfile
        import subprocess
        
        dialog.update_btn.setEnabled(False)
        dialog.later_btn.setEnabled(False)
        dialog.progress_bar.setVisible(True)
        dialog.progress_bar.setValue(0)
        dialog.status_label.setText("Preparing download...")
        QApplication.processEvents()
        
        try:
            # Download the installer
            response = requests.get(dialog.download_url, stream=True, timeout=60)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            # Save to temp directory
            temp_dir = Path(tempfile.gettempdir())
            installer_path = temp_dir / f"VIDT_Setup_{dialog.new_version}.exe"
            
            dialog.status_label.setText(f"Downloading... (0 / {total_size // 1024 // 1024} MB)")
            QApplication.processEvents()
            
            with open(installer_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            progress = int((downloaded / total_size) * 100)
                            dialog.progress_bar.setValue(progress)
                            dialog.status_label.setText(f"Downloading... ({downloaded // 1024 // 1024} / {total_size // 1024 // 1024} MB)")
                            QApplication.processEvents()
            
            dialog.progress_bar.setValue(100)
            dialog.status_label.setText("Download complete! Starting installer...")
            QApplication.processEvents()
            
            # Log success
            self.log(f"[OK] Update downloaded to: {installer_path}")
            
            # Run the installer silently and close current app
            QTimer.singleShot(1000, lambda: self.run_installer_and_exit(installer_path))
            
        except Exception as e:
            dialog.status_label.setText(f"Download failed: {str(e)[:50]}")
            dialog.status_label.setStyleSheet("color: #f85149; font-size: 12px;")
            dialog.update_btn.setEnabled(True)
            dialog.later_btn.setEnabled(True)
            dialog.progress_bar.setVisible(False)
            self.log(f"[X] Update download failed: {e}")

    def run_installer_and_exit(self, installer_path):
        """Run the installer and exit the current application"""
        import subprocess
        
        try:
            # Start the installer
            subprocess.Popen([str(installer_path)], shell=True)
            self.log("[OK] Installer started, closing application...")
            
            # Close the application
            QApplication.quit()
        except Exception as e:
            self.log(f"[X] Failed to start installer: {e}")

    def retry_set_directory(self):
        """Retry setting the output directory after UI is fully loaded"""
        try:
            stored_dir = self.settings.value("output_directory", "downloads")
            if stored_dir and stored_dir != "downloads":
                self.log(f"[R] Retrying to set directory: '{stored_dir}'")
                self._loading_settings = True  # Prevent auto-save during retry
                self.output.setText(stored_dir)
                self._loading_settings = False  # Re-enable auto-save
                self.dl.output_dir = Path(stored_dir)
                # Verify it worked this time
                actual_text = self.output.text()
                self.log(f"[R] After retry, output field shows: '{actual_text}'")
        except Exception as e:
            self.log(f"[!] Retry failed: {e}")
            self._loading_settings = False  # Ensure flag is reset
        
        # Also retry loading multiple download URLs after UI is ready
        self.retry_load_multi_urls()
    
    def retry_load_multi_urls(self):
        """Retry loading multiple download URLs after UI is fully ready"""
        try:
            saved_urls = self.settings.value("multi_urls", [])
            if saved_urls and hasattr(self, 'url_list_widget'):
                # Convert saved URLs to text format and add them
                urls_text = '\n'.join(saved_urls)
                if urls_text.strip():
                    self._loading_settings = True  # Prevent auto-save during loading
                    added_count, invalid_count = self.url_list_widget.add_urls_from_text(urls_text)
                    self._loading_settings = False  # Re-enable auto-save
                    if added_count > 0:
                        self.log(f"[R] Successfully restored {added_count} URLs from previous session")
                        # Update the URL status after loading
                        if hasattr(self, 'update_url_status'):
                            self.update_url_status()
        except Exception as e:
            self.log(f"[!] Failed to restore URLs: {e}")
            self._loading_settings = False  # Ensure flag is reset

    def setup_ui(self):
        # Remove default window frame to create custom title bar
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setWindowTitle(f"VIDT - Video Downloader Tool v{self.VERSION}")
        self.setFixedSize(1400, 750)
        self.center_window()
        
        # Try to set icon - multiple paths for dev and EXE
        logo_paths = [Path("logo/logo.png"), Path("logo.png")]
        if getattr(sys, 'frozen', False):
            base_path = Path(sys._MEIPASS)
            logo_paths.insert(0, base_path / "logo" / "logo.png")
            logo_paths.insert(1, base_path / "logo.png")
        
        for logo_path in logo_paths:
            try:
                if logo_path.exists():
                    self.setWindowIcon(QIcon(str(logo_path)))
                    break
            except:
                continue
        
        # Main widget
        main = QWidget()
        main.setStyleSheet("""
            QWidget {
                background: #0a0a0a;
                color: #ffffff;
            }
        """)
        self.setCentralWidget(main)
        main_layout = QVBoxLayout(main)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # === CUSTOM WINDOW TITLE BAR ===
        self.create_custom_titlebar(main_layout)
        
        # === CONTENT AREA ===
        content_widget = QWidget()
        content_widget.setStyleSheet("""
            QWidget {
                background: #0a0a0a;
                color: #ffffff;
            }
        """)
        layout = QVBoxLayout(content_widget)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)
        main_layout.addWidget(content_widget)
        
        # === TAB WIDGET ===
        self.tab_widget = QTabWidget()
        self.style_tabs(self.tab_widget)
        
        # Create tabs
        self.single_tab = self.create_single_download_tab()
        self.multiple_tab = self.create_multiple_download_tab()
        self.profile_tab = self.create_profile_download_tab()
        self.image_tab = self.create_image_download_tab()
        self.edit_tab = self.create_edit_videos_tab()
        
        # Add tabs to widget
        self.tab_widget.addTab(self.single_tab, "Single Download")
        self.tab_widget.addTab(self.multiple_tab, "Multiple Download")
        self.tab_widget.addTab(self.profile_tab, "Profile Video Download")
        self.tab_widget.addTab(self.image_tab, "Image Download")
        self.tab_widget.addTab(self.edit_tab, "Edit Videos")
        
        # Connect tab change to auto-save
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        
        layout.addWidget(self.tab_widget)
        
        # === APPLY MAIN WINDOW STYLING ===
        self.setStyleSheet("""
            QMainWindow {
                background: #0a0a0a;
                color: #ffffff;
                border: 2px solid #404040;
                border-radius: 8px;
            }
            QWidget {
                font-family: 'Segoe UI', 'SF Pro Display', system-ui;
                background: #0a0a0a;
                color: #ffffff;
            }
            QLabel {
                border: none;
                background: transparent;
                margin: 0;
                padding: 0;
                outline: none;
                selection-background-color: transparent;
            }
            QToolTip {
                background: #2a2a3a;
                color: #ffffff;
                border: 1px solid #404040;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
            }
        """)
        
    def create_single_download_tab(self):
        """Create the Single Download tab content"""
        tab_widget = QWidget()
        layout = QVBoxLayout(tab_widget)
        layout.setSpacing(16)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # === URL SECTION ===
        url_frame = self.create_section("Enter Video URL")
        url_layout = QVBoxLayout()
        url_layout.setSpacing(12)
        
        # URL input row
        url_row = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Paste video URL here...")
        self.url_input.setFixedHeight(44)
        self.style_input(self.url_input)
        self.url_input.textChanged.connect(self.auto_save_settings)
        
        paste_btn = QPushButton("Paste")
        paste_btn.setFixedSize(70, 44)
        paste_btn.clicked.connect(self.paste_url)
        self.style_btn_secondary(paste_btn)
        
        url_row.addWidget(self.url_input)
        url_row.addWidget(paste_btn)
        
        # Buttons row
        btn_row = QHBoxLayout()
        
        self.info_btn = QPushButton("Get Info")
        self.info_btn.setFixedHeight(38)
        self.info_btn.setMinimumWidth(100)
        self.info_btn.clicked.connect(self.get_info)
        self.style_btn_green(self.info_btn)
        
        self.dl_btn = QPushButton("Download")
        self.dl_btn.setFixedHeight(38)
        self.dl_btn.setMinimumWidth(140)
        self.dl_btn.clicked.connect(self.download)
        self.style_btn_primary(self.dl_btn)
        
        btn_row.addStretch()
        btn_row.addWidget(self.info_btn)
        btn_row.addSpacing(10)
        btn_row.addWidget(self.dl_btn)
        
        url_layout.addLayout(url_row)
        url_layout.addLayout(btn_row)
        url_frame.layout().addLayout(url_layout)
        layout.addWidget(url_frame)
        
        # === OPTIONS SECTION ===
        opt_frame = self.create_section("Download Options")
        opt_grid = QGridLayout()
        opt_grid.setSpacing(16)
        opt_grid.setColumnStretch(1, 1)
        opt_grid.setColumnStretch(3, 1)
        
        # Quality
        opt_grid.addWidget(self.create_label("Quality:"), 0, 0)
        self.quality = QComboBox()
        self.quality.addItems(["best", "8K", "4K", "2K", "1080p", "720p", "480p", "360p"])
        self.style_combo(self.quality)
        self.quality.currentTextChanged.connect(self.auto_save_settings)
        opt_grid.addWidget(self.quality, 0, 1)
        
        # Format
        opt_grid.addWidget(self.create_label("Format:"), 0, 2)
        self.format = QComboBox()
        self.format.addItems(["Force H.264 (Compatible)", "mp4 (H.264)", "webm", "any", "Convert to H.264"])
        self.style_combo(self.format)
        self.format.currentTextChanged.connect(self.auto_save_settings)
        opt_grid.addWidget(self.format, 0, 3)
        
        # Checkboxes
        self.audio_cb = QCheckBox("Audio Only (MP3)")
        self.subtitle_cb = QCheckBox("Download Subtitles")
        self.mute_cb = QCheckBox("Mute Video (No Audio)")
        self.convert_cb = QCheckBox("Force convert to compatible format (slower but always playable)")
        self.style_checkbox(self.audio_cb)
        self.style_checkbox(self.subtitle_cb)
        self.style_checkbox(self.mute_cb)
        self.style_checkbox(self.convert_cb)
        self.audio_cb.toggled.connect(self.auto_save_settings)
        self.subtitle_cb.toggled.connect(self.auto_save_settings)
        self.mute_cb.toggled.connect(self.auto_save_settings)
        self.convert_cb.toggled.connect(self.auto_save_settings)
        # Disable mute when audio only is checked (and vice versa)
        self.audio_cb.toggled.connect(lambda checked: self.mute_cb.setEnabled(not checked))
        self.mute_cb.toggled.connect(lambda checked: self.audio_cb.setEnabled(not checked))
        opt_grid.addWidget(self.audio_cb, 1, 0, 1, 2)
        opt_grid.addWidget(self.subtitle_cb, 1, 2, 1, 1)
        opt_grid.addWidget(self.mute_cb, 1, 3, 1, 1)
        opt_grid.addWidget(self.convert_cb, 2, 0, 1, 4)
        
        # Output
        opt_grid.addWidget(self.create_label("Save to:"), 3, 0)
        out_row = QHBoxLayout()
        self.output = QLineEdit()  # Don't set default value here
        self.output.setPlaceholderText("downloads")
        self.output.setFixedHeight(36)
        self.style_input(self.output)
        self.output.textChanged.connect(self.auto_save_settings)
        
        browse_btn = QPushButton("Browse")
        browse_btn.setFixedSize(70, 36)
        browse_btn.clicked.connect(self.browse)
        self.style_btn_secondary(browse_btn)
        
        out_row.addWidget(self.output)
        out_row.addWidget(browse_btn)
        opt_grid.addLayout(out_row, 3, 1, 1, 3)
        
        opt_frame.layout().addLayout(opt_grid)
        layout.addWidget(opt_frame)
        
        # === INFO & LOG (side by side) ===
        bottom = QHBoxLayout()
        bottom.setSpacing(12)
        
        # Info
        info_frame = self.create_section("Video Info")
        self.info_text = QTextEdit()
        self.info_text.setFixedHeight(120)  # Consistent with multiple download tab
        self.info_text.setReadOnly(True)
        self.info_text.setPlaceholderText("Click 'Get Info' to see video details...")
        self.style_text(self.info_text)
        info_frame.layout().addWidget(self.info_text)
        
        # Log
        log_frame = self.create_section("Download Log")
        log_layout = QVBoxLayout()
        log_layout.setSpacing(4)
        
        # Status summary
        self.download_status_label = QLabel("Ready for single video download")
        self.download_status_label.setStyleSheet("color: #58a6ff; font-weight: bold; font-size: 11px; border: none; background: transparent;")
        log_layout.addWidget(self.download_status_label)
        
        # Log text area
        self.log_text = QTextEdit()
        self.log_text.setFixedHeight(120)  # Consistent with multiple download tab
        self.log_text.setReadOnly(True)
        self.log_text.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)  # Enable word wrapping
        self.style_text(self.log_text)
        log_layout.addWidget(self.log_text)
        
        log_frame.layout().addLayout(log_layout)
        
        bottom.addWidget(info_frame)
        bottom.addWidget(log_frame)
        layout.addLayout(bottom)
        
        # === PROGRESS ===
        self.progress = QProgressBar()
        self.progress.setFixedHeight(8)  # Slightly taller for better visibility
        self.progress.setTextVisible(True)  # Show percentage text
        self.progress.setVisible(False)
        self.progress.setStyleSheet("""
            QProgressBar {
                background: #21262d;
                border: 1px solid #30363d;
                border-radius: 4px;
                text-align: center;
                font-size: 11px;
                font-weight: bold;
                color: #f0f6fc;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #238636, stop:1 #2ea043);
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.progress)
        
        return tab_widget
    
    def create_multiple_download_tab(self):
        """Create the Multiple Download tab content"""
        tab_widget = QWidget()
        layout = QVBoxLayout(tab_widget)
        layout.setSpacing(12)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Multiple URLs section
        urls_frame = self.create_section("Multiple Video URLs")
        urls_layout = QVBoxLayout()
        urls_layout.setSpacing(8)
        
        # URL list with checkboxes
        self.url_list_widget = URLListWidget(self)
        urls_layout.addWidget(self.url_list_widget)
        
        # URL management buttons
        url_btn_row = QHBoxLayout()
        url_btn_row.setSpacing(8)
        
        paste_urls_btn = QPushButton("Paste URLs")
        paste_urls_btn.setFixedHeight(32)
        paste_urls_btn.clicked.connect(self.paste_multiple_urls)
        self.style_btn_secondary(paste_urls_btn)
        
        select_all_btn = QPushButton("Select All")
        select_all_btn.setFixedHeight(32)
        select_all_btn.clicked.connect(lambda: self.url_list_widget.select_all(True))
        self.style_btn_secondary(select_all_btn)
        
        deselect_all_btn = QPushButton("Deselect All")
        deselect_all_btn.setFixedHeight(32)
        deselect_all_btn.clicked.connect(lambda: self.url_list_widget.select_all(False))
        self.style_btn_secondary(deselect_all_btn)
        
        clear_urls_btn = QPushButton("Clear All")
        clear_urls_btn.setFixedHeight(32)
        clear_urls_btn.clicked.connect(self.clear_all_urls)
        self.style_btn_secondary(clear_urls_btn)
        
        # URL status label
        self.url_status_label = QLabel("No URLs added")
        self.url_status_label.setStyleSheet("color: #7d8590; font-size: 11px; font-style: italic; border: none; background: transparent;")
        
        # Help button for URL formats
        help_btn = QPushButton("Help")
        help_btn.setFixedHeight(32)
        help_btn.clicked.connect(self.show_url_help)
        self.style_btn_secondary(help_btn)
        
        self.multi_info_btn = QPushButton("Get Info")
        self.multi_info_btn.setFixedHeight(32)
        self.multi_info_btn.clicked.connect(self.get_multiple_info)
        self.style_btn_green(self.multi_info_btn)
        
        # Download control buttons - positioned near Get Info
        self.multi_pause_btn = QPushButton("Pause")
        self.multi_pause_btn.setFixedHeight(32)
        self.multi_pause_btn.clicked.connect(self.pause_multiple_downloads)
        self.multi_pause_btn.setEnabled(False)
        self.style_btn_secondary(self.multi_pause_btn)
        
        self.multi_stop_btn = QPushButton("Stop")
        self.multi_stop_btn.setFixedHeight(32)
        self.multi_stop_btn.clicked.connect(self.stop_multiple_downloads)
        self.multi_stop_btn.setEnabled(False)
        self.style_btn_secondary(self.multi_stop_btn)
        
        self.multi_download_btn = QPushButton("Start Downloads")
        self.multi_download_btn.setFixedHeight(32)
        self.multi_download_btn.setMinimumWidth(120)
        self.multi_download_btn.clicked.connect(self.start_multiple_downloads)
        self.style_btn_primary(self.multi_download_btn)
        
        url_btn_row.addWidget(paste_urls_btn)
        url_btn_row.addWidget(select_all_btn)
        url_btn_row.addWidget(deselect_all_btn)
        url_btn_row.addWidget(clear_urls_btn)
        url_btn_row.addWidget(help_btn)
        url_btn_row.addWidget(self.url_status_label)
        url_btn_row.addSpacing(15)
        url_btn_row.addWidget(self.multi_info_btn)
        url_btn_row.addSpacing(15)
        url_btn_row.addWidget(self.multi_pause_btn)
        url_btn_row.addWidget(self.multi_stop_btn)
        url_btn_row.addWidget(self.multi_download_btn)
        
        urls_layout.addLayout(url_btn_row)
        urls_frame.layout().addLayout(urls_layout)
        layout.addWidget(urls_frame)
        
        # === DOWNLOAD OPTIONS SECTION ===
        multi_opt_frame = self.create_section("Download Options")
        multi_opt_grid = QGridLayout()
        multi_opt_grid.setSpacing(10)
        multi_opt_grid.setColumnStretch(1, 1)
        multi_opt_grid.setColumnStretch(3, 1)
        
        # Quality & Format
        multi_opt_grid.addWidget(self.create_label("Quality:"), 0, 0)
        self.multi_quality = QComboBox()
        self.multi_quality.addItems(["best", "8K", "4K", "2K", "1080p", "720p", "480p", "360p"])
        self.multi_quality.setFixedHeight(32)
        self.style_combo(self.multi_quality)
        self.multi_quality.currentTextChanged.connect(self.auto_save_settings)
        multi_opt_grid.addWidget(self.multi_quality, 0, 1)
        
        multi_opt_grid.addWidget(self.create_label("Format:"), 0, 2)
        self.multi_format = QComboBox()
        self.multi_format.addItems(["Force H.264 (Compatible)", "mp4 (H.264)", "webm", "any"])
        self.multi_format.setFixedHeight(32)
        self.style_combo(self.multi_format)
        self.multi_format.currentTextChanged.connect(self.auto_save_settings)
        multi_opt_grid.addWidget(self.multi_format, 0, 3)
        
        # Checkboxes
        self.multi_audio_cb = QCheckBox("Audio Only (MP3)")
        self.multi_subtitle_cb = QCheckBox("Download Subtitles")
        self.multi_mute_cb = QCheckBox("Mute Video")
        self.style_checkbox(self.multi_audio_cb)
        self.style_checkbox(self.multi_subtitle_cb)
        self.style_checkbox(self.multi_mute_cb)
        self.multi_audio_cb.toggled.connect(self.auto_save_settings)
        self.multi_subtitle_cb.toggled.connect(self.auto_save_settings)
        self.multi_mute_cb.toggled.connect(self.auto_save_settings)
        self.multi_audio_cb.toggled.connect(lambda checked: self.multi_mute_cb.setEnabled(not checked))
        self.multi_mute_cb.toggled.connect(lambda checked: self.multi_audio_cb.setEnabled(not checked))
        multi_opt_grid.addWidget(self.multi_audio_cb, 1, 0, 1, 1)
        multi_opt_grid.addWidget(self.multi_subtitle_cb, 1, 1, 1, 1)
        multi_opt_grid.addWidget(self.multi_mute_cb, 1, 2, 1, 2)
        
        # Output directory
        multi_opt_grid.addWidget(self.create_label("Save to:"), 2, 0)
        multi_out_row = QHBoxLayout()
        self.multi_output = QLineEdit()
        self.multi_output.setPlaceholderText("downloads")
        self.multi_output.setFixedHeight(32)
        self.style_input(self.multi_output)
        self.multi_output.textChanged.connect(self.auto_save_settings)
        
        multi_browse_btn = QPushButton("Browse")
        multi_browse_btn.setFixedSize(70, 32)
        multi_browse_btn.clicked.connect(self.browse_multi_output)
        self.style_btn_secondary(multi_browse_btn)
        
        multi_out_row.addWidget(self.multi_output)
        multi_out_row.addWidget(multi_browse_btn)
        multi_opt_grid.addLayout(multi_out_row, 2, 1, 1, 3)
        
        multi_opt_frame.layout().addLayout(multi_opt_grid)
        layout.addWidget(multi_opt_frame)
        
        # === INFO & PROGRESS (side by side) ===
        bottom = QHBoxLayout()
        bottom.setSpacing(12)
        
        # Video Info
        multi_info_frame = self.create_section("Videos Info")
        self.multi_info_text = QTextEdit()
        self.multi_info_text.setFixedHeight(120)  # Increased from 80 to 120
        self.multi_info_text.setReadOnly(True)
        self.multi_info_text.setPlaceholderText("Click 'Get Info' to see videos details...")
        self.style_text(self.multi_info_text)
        multi_info_frame.layout().addWidget(self.multi_info_text)
        
        # Progress Log
        progress_frame = self.create_section("Download Progress")
        progress_layout = QVBoxLayout()
        progress_layout.setSpacing(4)
        
        # Status summary
        self.multi_status_label = QLabel("Ready to download multiple videos")
        self.multi_status_label.setStyleSheet("color: #58a6ff; font-weight: bold; font-size: 11px; border: none; background: transparent;")
        progress_layout.addWidget(self.multi_status_label)
        
        # Progress text area
        self.multi_progress_text = QTextEdit()
        self.multi_progress_text.setFixedHeight(120)  # Increased from 80 to 120
        self.multi_progress_text.setReadOnly(True)
        self.multi_progress_text.setPlaceholderText("Multiple download progress will appear here...")
        self.style_text(self.multi_progress_text)
        progress_layout.addWidget(self.multi_progress_text)
        
        progress_frame.layout().addLayout(progress_layout)
        
        bottom.addWidget(multi_info_frame)
        bottom.addWidget(progress_frame)
        layout.addLayout(bottom)
        
        # Initialize URL status
        self.update_url_status()
        
        return tab_widget
    
    def create_profile_download_tab(self):
        """Create the Profile Video Download tab - matching Multiple Download layout"""
        tab_widget = QWidget()
        layout = QVBoxLayout(tab_widget)
        layout.setSpacing(12)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # === PROFILE URLs SECTION ===
        urls_frame = self.create_section("Profile/Channel URLs")
        urls_layout = QVBoxLayout()
        urls_layout.setSpacing(8)
        
        # URL list with checkboxes
        self.profile_url_list_widget = URLListWidget(self)
        self.profile_url_list_widget.placeholder_label.setText("Click 'Paste URLs' to add multiple profile links from clipboard")
        urls_layout.addWidget(self.profile_url_list_widget)
        
        # URL management buttons row
        url_btn_row = QHBoxLayout()
        url_btn_row.setSpacing(8)
        
        paste_urls_btn = QPushButton("Paste URLs")
        paste_urls_btn.setFixedHeight(32)
        paste_urls_btn.clicked.connect(self.paste_profile_urls)
        self.style_btn_secondary(paste_urls_btn)
        
        select_all_btn = QPushButton("Select All")
        select_all_btn.setFixedHeight(32)
        select_all_btn.clicked.connect(lambda: self.profile_url_list_widget.select_all(True))
        self.style_btn_secondary(select_all_btn)
        
        deselect_all_btn = QPushButton("Deselect All")
        deselect_all_btn.setFixedHeight(32)
        deselect_all_btn.clicked.connect(lambda: self.profile_url_list_widget.select_all(False))
        self.style_btn_secondary(deselect_all_btn)
        
        clear_urls_btn = QPushButton("Clear All")
        clear_urls_btn.setFixedHeight(32)
        clear_urls_btn.clicked.connect(lambda: (self.profile_url_list_widget.clear_all(), self.update_profile_url_status()))
        self.style_btn_secondary(clear_urls_btn)
        
        # URL status label
        self.profile_url_status = QLabel("No profile URLs added")
        self.profile_url_status.setStyleSheet("color: #7d8590; font-size: 11px; font-style: italic; border: none; background: transparent;")
        
        # Action buttons
        self.profile_info_btn = QPushButton("Get Info")
        self.profile_info_btn.setFixedHeight(32)
        self.profile_info_btn.clicked.connect(self.get_profile_info_from_tab)
        self.style_btn_green(self.profile_info_btn)
        
        self.profile_download_btn = QPushButton("Download Videos")
        self.profile_download_btn.setFixedHeight(32)
        self.profile_download_btn.setMinimumWidth(120)
        self.profile_download_btn.clicked.connect(self.download_profile_from_tab)
        self.style_btn_primary(self.profile_download_btn)
        
        url_btn_row.addWidget(paste_urls_btn)
        url_btn_row.addWidget(select_all_btn)
        url_btn_row.addWidget(deselect_all_btn)
        url_btn_row.addWidget(clear_urls_btn)
        url_btn_row.addWidget(self.profile_url_status)
        url_btn_row.addStretch()
        url_btn_row.addWidget(self.profile_info_btn)
        url_btn_row.addSpacing(8)
        url_btn_row.addWidget(self.profile_download_btn)
        
        urls_layout.addLayout(url_btn_row)
        urls_frame.layout().addLayout(urls_layout)
        layout.addWidget(urls_frame)
        
        # === DOWNLOAD OPTIONS SECTION ===
        options_frame = self.create_section("Download Options")
        options_grid = QGridLayout()
        options_grid.setSpacing(10)
        options_grid.setColumnStretch(1, 1)
        options_grid.setColumnStretch(3, 1)
        options_grid.setColumnStretch(5, 1)
        
        # Quality, Format, Max Videos in one row
        options_grid.addWidget(self.create_label("Quality:"), 0, 0)
        self.profile_quality = QComboBox()
        self.profile_quality.addItems(["best", "8K", "4K", "2K", "1080p", "720p", "480p", "360p"])
        self.profile_quality.setFixedHeight(32)
        self.style_combo(self.profile_quality)
        self.profile_quality.currentTextChanged.connect(self.auto_save_settings)
        options_grid.addWidget(self.profile_quality, 0, 1)
        
        options_grid.addWidget(self.create_label("Format:"), 0, 2)
        self.profile_format = QComboBox()
        self.profile_format.addItems(["Force H.264 (Compatible)", "mp4 (H.264)", "webm", "any"])
        self.profile_format.setFixedHeight(32)
        self.style_combo(self.profile_format)
        self.profile_format.currentTextChanged.connect(self.auto_save_settings)
        options_grid.addWidget(self.profile_format, 0, 3)
        
        options_grid.addWidget(self.create_label("Max Videos:"), 0, 4)
        self.profile_max_videos = QComboBox()
        self.profile_max_videos.addItems(["10", "25", "50", "100", "All available"])
        self.profile_max_videos.setCurrentText("50")
        self.profile_max_videos.setFixedHeight(32)
        self.style_combo(self.profile_max_videos)
        self.profile_max_videos.currentTextChanged.connect(self.auto_save_settings)
        options_grid.addWidget(self.profile_max_videos, 0, 5)
        
        # Checkboxes row
        self.profile_audio_cb = QCheckBox("Audio Only (MP3)")
        self.profile_subtitle_cb = QCheckBox("Download Subtitles")
        self.profile_mute_cb = QCheckBox("Mute Video")
        self.profile_create_subfolder_cb = QCheckBox("Create Subfolder")
        self.profile_create_subfolder_cb.setChecked(True)
        self.style_checkbox(self.profile_audio_cb)
        self.style_checkbox(self.profile_subtitle_cb)
        self.style_checkbox(self.profile_mute_cb)
        self.style_checkbox(self.profile_create_subfolder_cb)
        self.profile_audio_cb.toggled.connect(self.auto_save_settings)
        self.profile_subtitle_cb.toggled.connect(self.auto_save_settings)
        self.profile_mute_cb.toggled.connect(self.auto_save_settings)
        self.profile_create_subfolder_cb.toggled.connect(self.auto_save_settings)
        self.profile_audio_cb.toggled.connect(lambda checked: self.profile_mute_cb.setEnabled(not checked))
        self.profile_mute_cb.toggled.connect(lambda checked: self.profile_audio_cb.setEnabled(not checked))
        options_grid.addWidget(self.profile_audio_cb, 1, 0, 1, 1)
        options_grid.addWidget(self.profile_subtitle_cb, 1, 1, 1, 1)
        options_grid.addWidget(self.profile_mute_cb, 1, 2, 1, 1)
        options_grid.addWidget(self.profile_create_subfolder_cb, 1, 3, 1, 3)
        
        # Output directory row
        options_grid.addWidget(self.create_label("Save to:"), 2, 0)
        output_row = QHBoxLayout()
        self.profile_output = QLineEdit()
        self.profile_output.setPlaceholderText("downloads/profiles")
        self.profile_output.setFixedHeight(32)
        self.style_input(self.profile_output)
        self.profile_output.textChanged.connect(self.auto_save_settings)
        
        browse_btn = QPushButton("Browse")
        browse_btn.setFixedSize(70, 32)
        browse_btn.clicked.connect(self.browse_profile_output)
        self.style_btn_secondary(browse_btn)
        
        output_row.addWidget(self.profile_output)
        output_row.addWidget(browse_btn)
        options_grid.addLayout(output_row, 2, 1, 1, 5)
        
        options_frame.layout().addLayout(options_grid)
        layout.addWidget(options_frame)
        
        # === INFO & PROGRESS (side by side) ===
        bottom = QHBoxLayout()
        bottom.setSpacing(12)
        
        # Profile Info (left)
        info_frame = self.create_section("Profile Information")
        self.profile_videos_text = QTextEdit()
        self.profile_videos_text.setMinimumHeight(150)
        self.profile_videos_text.setReadOnly(True)
        self.profile_videos_text.setPlaceholderText("Click 'Get Info' to see profile details...")
        self.style_text(self.profile_videos_text)
        info_frame.layout().addWidget(self.profile_videos_text)
        
        # Progress (right)
        progress_frame = self.create_section("Download Progress")
        progress_layout = QVBoxLayout()
        progress_layout.setSpacing(4)
        
        self.profile_status_label = QLabel("Ready to download profile videos")
        self.profile_status_label.setStyleSheet("color: #58a6ff; font-weight: bold; font-size: 11px; border: none; background: transparent;")
        progress_layout.addWidget(self.profile_status_label)
        
        self.profile_progress_text = QTextEdit()
        self.profile_progress_text.setMinimumHeight(150)
        self.profile_progress_text.setReadOnly(True)
        self.profile_progress_text.setPlaceholderText("Download progress will appear here...")
        self.style_text(self.profile_progress_text)
        progress_layout.addWidget(self.profile_progress_text)
        
        progress_frame.layout().addLayout(progress_layout)
        
        bottom.addWidget(info_frame, 1)  # Stretch factor 1
        bottom.addWidget(progress_frame, 1)  # Stretch factor 1
        layout.addLayout(bottom, 1)  # Allow bottom section to stretch
        
        return tab_widget
    
    def create_image_download_tab(self):
        """Create Image Download tab - matching other tabs style"""
        tab_widget = QWidget()
        layout = QVBoxLayout(tab_widget)
        layout.setSpacing(12)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # === URL INPUT SECTION ===
        url_frame = self.create_section("Image URLs")
        url_layout = QVBoxLayout()
        url_layout.setSpacing(8)
        
        # URL list with checkboxes (same as other tabs)
        self.image_url_list_widget = URLListWidget(self)
        self.image_url_list_widget.placeholder_label.setText("Click 'Paste URLs' to add image links from clipboard")
        url_layout.addWidget(self.image_url_list_widget)
        
        # URL management buttons row
        url_btn_row = QHBoxLayout()
        url_btn_row.setSpacing(8)
        
        paste_urls_btn = QPushButton("Paste URLs")
        paste_urls_btn.setFixedHeight(32)
        paste_urls_btn.clicked.connect(self.paste_image_urls)
        self.style_btn_secondary(paste_urls_btn)
        
        select_all_btn = QPushButton("Select All")
        select_all_btn.setFixedHeight(32)
        select_all_btn.clicked.connect(lambda: self.image_url_list_widget.select_all(True))
        self.style_btn_secondary(select_all_btn)
        
        deselect_all_btn = QPushButton("Deselect All")
        deselect_all_btn.setFixedHeight(32)
        deselect_all_btn.clicked.connect(lambda: self.image_url_list_widget.select_all(False))
        self.style_btn_secondary(deselect_all_btn)
        
        clear_urls_btn = QPushButton("Clear All")
        clear_urls_btn.setFixedHeight(32)
        clear_urls_btn.clicked.connect(lambda: (self.image_url_list_widget.clear_all(), self.update_image_url_status()))
        self.style_btn_secondary(clear_urls_btn)
        
        # URL status label
        self.image_url_status = QLabel("No image URLs added")
        self.image_url_status.setStyleSheet("color: #7d8590; font-size: 11px; font-style: italic; border: none; background: transparent;")
        
        # Download button
        self.image_download_btn = QPushButton("Download Images")
        self.image_download_btn.setFixedHeight(32)
        self.image_download_btn.setMinimumWidth(120)
        self.image_download_btn.clicked.connect(self.download_images)
        self.style_btn_primary(self.image_download_btn)
        
        # Options button
        options_btn = QPushButton("Options")
        options_btn.setFixedHeight(32)
        options_btn.setMinimumWidth(80)
        options_btn.clicked.connect(self.show_image_options_dialog)
        self.style_btn_secondary(options_btn)
        
        url_btn_row.addWidget(paste_urls_btn)
        url_btn_row.addWidget(select_all_btn)
        url_btn_row.addWidget(deselect_all_btn)
        url_btn_row.addWidget(clear_urls_btn)
        url_btn_row.addWidget(self.image_url_status)
        url_btn_row.addStretch()
        url_btn_row.addWidget(self.image_download_btn)
        url_btn_row.addSpacing(8)
        url_btn_row.addWidget(options_btn)
        
        url_layout.addLayout(url_btn_row)
        url_frame.layout().addLayout(url_layout)
        layout.addWidget(url_frame)
        
        # === OPTIONS ROW ===
        options_frame = self.create_section("Save Location")
        options_row = QHBoxLayout()
        options_row.setSpacing(10)
        
        options_row.addWidget(self.create_label("Save to:"))
        self.image_output = QLineEdit()
        self.image_output.setText("downloads/images")
        self.image_output.setFixedHeight(32)
        self.style_input(self.image_output)
        self.image_output.textChanged.connect(self.auto_save_settings)
        options_row.addWidget(self.image_output)
        
        browse_btn = QPushButton("Browse")
        browse_btn.setFixedHeight(32)
        browse_btn.setMinimumWidth(80)
        browse_btn.clicked.connect(self.browse_image_output)
        self.style_btn_secondary(browse_btn)
        options_row.addWidget(browse_btn)
        
        options_frame.layout().addLayout(options_row)
        layout.addWidget(options_frame)
        
        # === PROGRESS SECTION ===
        progress_frame = self.create_section("Progress")
        progress_layout = QVBoxLayout()
        progress_layout.setSpacing(8)
        
        # Progress header with stats
        header_row = QHBoxLayout()
        
        self.image_status_label = QLabel("Ready to download")
        self.image_status_label.setStyleSheet("""
            QLabel {
                color: #58a6ff;
                font-size: 12px;
                font-weight: bold;
                border: none;
                background: transparent;
            }
        """)
        header_row.addWidget(self.image_status_label)
        
        header_row.addStretch()
        
        # Stats labels
        self.image_stats_label = QLabel("")
        self.image_stats_label.setStyleSheet("color: #7d8590; font-size: 11px; border: none; background: transparent;")
        header_row.addWidget(self.image_stats_label)
        
        # Stop button
        self.image_stop_btn = QPushButton("Stop")
        self.image_stop_btn.setFixedSize(60, 26)
        self.image_stop_btn.setEnabled(False)
        self.image_stop_btn.clicked.connect(self.stop_image_download)
        self.image_stop_btn.setStyleSheet("""
            QPushButton {
                background: #da3633;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #f85149;
            }
            QPushButton:disabled {
                background: #21262d;
                color: #7d8590;
            }
        """)
        header_row.addWidget(self.image_stop_btn)
        
        progress_layout.addLayout(header_row)
        
        # Progress bar
        self.image_progress_bar = QProgressBar()
        self.image_progress_bar.setFixedHeight(8)
        self.image_progress_bar.setValue(0)
        self.image_progress_bar.setTextVisible(False)
        self.image_progress_bar.setStyleSheet("""
            QProgressBar {
                background: #21262d;
                border: none;
                border-radius: 4px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #238636, stop:1 #3fb950);
                border-radius: 4px;
            }
        """)
        progress_layout.addWidget(self.image_progress_bar)
        
        # Log area
        self.image_progress_text = QTextEdit()
        self.image_progress_text.setReadOnly(True)
        self.image_progress_text.setPlaceholderText("Download activity will appear here...")
        self.image_progress_text.setStyleSheet("""
            QTextEdit {
                background: #0d1117;
                color: #c9d1d9;
                border: 1px solid #21262d;
                border-radius: 6px;
                padding: 8px;
                font-size: 11px;
                font-family: 'Consolas', 'Monaco', monospace;
            }
        """)
        progress_layout.addWidget(self.image_progress_text)
        
        progress_frame.layout().addLayout(progress_layout)
        layout.addWidget(progress_frame, 1)
        
        # Default option values (will be set by dialog)
        self._image_subfolder = True
        self._image_skip_duplicates = True
        self._image_highres = True
        self._image_skip_icons = True
        self._image_overwrite = False
        self._image_format = "All formats"
        self._image_concurrent = 4
        self._image_min_size = 0
        self._image_pinterest_max = 50  # Max images for Pinterest search URLs
        
        self.image_download_stopped = False
        
        return tab_widget
    
    def create_edit_videos_tab(self):
        """Create Edit Videos tab for batch video editing"""
        tab_widget = QWidget()
        layout = QVBoxLayout(tab_widget)
        layout.setSpacing(12)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # === INPUT SOURCE ===
        input_label = QLabel("Input (Folder or Video):")
        input_label.setStyleSheet("color: #58a6ff; font-weight: bold; font-size: 12px;")
        layout.addWidget(input_label)
        
        input_row = QHBoxLayout()
        input_row.setSpacing(8)
        self.edit_input_folder = QLineEdit()
        self.edit_input_folder.setPlaceholderText("Select folder or video file...")
        self.edit_input_folder.setFixedHeight(32)
        self.style_input(self.edit_input_folder)
        self.edit_input_folder.textChanged.connect(self.update_edit_video_count)
        input_row.addWidget(self.edit_input_folder)
        
        browse_folder_btn = QPushButton("Folder")
        browse_folder_btn.setFixedSize(70, 32)
        browse_folder_btn.clicked.connect(self.browse_edit_input_folder)
        self.style_btn_secondary(browse_folder_btn)
        input_row.addWidget(browse_folder_btn)
        
        browse_file_btn = QPushButton("File")
        browse_file_btn.setFixedSize(60, 32)
        browse_file_btn.clicked.connect(self.browse_edit_input_file)
        self.style_btn_secondary(browse_file_btn)
        input_row.addWidget(browse_file_btn)
        layout.addLayout(input_row)
        
        # Video count
        self.edit_video_count = QLabel("No folder selected")
        self.edit_video_count.setStyleSheet("color: #7d8590; font-size: 10px; margin-bottom: 5px;")
        layout.addWidget(self.edit_video_count)
        
        # === OUTPUT FOLDER ===
        output_label = QLabel("Output Folder:")
        output_label.setStyleSheet("color: #58a6ff; font-weight: bold; font-size: 12px;")
        layout.addWidget(output_label)
        
        output_row = QHBoxLayout()
        output_row.setSpacing(8)
        self.edit_output_folder = QLineEdit()
        self.edit_output_folder.setPlaceholderText("Select output folder for edited videos...")
        self.edit_output_folder.setText("downloads/edited")
        self.edit_output_folder.setFixedHeight(32)
        self.style_input(self.edit_output_folder)
        output_row.addWidget(self.edit_output_folder)
        
        browse_output_btn = QPushButton("Browse")
        browse_output_btn.setFixedSize(80, 32)
        browse_output_btn.clicked.connect(self.browse_edit_output)
        self.style_btn_secondary(browse_output_btn)
        output_row.addWidget(browse_output_btn)
        layout.addLayout(output_row)
        
        layout.addSpacing(5)
        
        # === SETTINGS & ACTIONS ROW ===
        actions_row = QHBoxLayout()
        actions_row.setSpacing(10)
        
        # Settings button
        settings_btn = QPushButton("Edit Settings")
        settings_btn.setFixedHeight(36)
        settings_btn.setMinimumWidth(120)
        settings_btn.clicked.connect(self.show_edit_settings_dialog)
        self.style_btn_secondary(settings_btn)
        actions_row.addWidget(settings_btn)
        
        # Current settings label
        self.edit_settings_label = QLabel("Default settings")
        self.edit_settings_label.setStyleSheet("color: #7d8590; font-size: 11px;")
        actions_row.addWidget(self.edit_settings_label, 1)
        
        # Start button
        self.start_edit_btn = QPushButton("Start Editing")
        self.start_edit_btn.setFixedHeight(36)
        self.start_edit_btn.setMinimumWidth(130)
        self.start_edit_btn.clicked.connect(self.start_video_editing)
        self.style_btn_green(self.start_edit_btn)
        actions_row.addWidget(self.start_edit_btn)
        
        # Stop button
        self.stop_edit_btn = QPushButton("Stop")
        self.stop_edit_btn.setFixedSize(60, 36)
        self.stop_edit_btn.setEnabled(False)
        self.stop_edit_btn.clicked.connect(self.stop_video_editing)
        self.stop_edit_btn.setStyleSheet("""
            QPushButton {
                background: rgba(248, 81, 73, 0.8);
                color: white;
                border: none;
                border-radius: 0px;
                font-weight: bold;
            }
            QPushButton:hover { background: rgba(248, 81, 73, 1.0); }
            QPushButton:disabled { background: #21262d; color: #484f58; }
        """)
        actions_row.addWidget(self.stop_edit_btn)
        layout.addLayout(actions_row)
        
        layout.addSpacing(5)
        
        # === PROGRESS SECTION ===
        progress_label = QLabel("[G] Progress:")
        progress_label.setStyleSheet("color: #58a6ff; font-weight: bold; font-size: 12px;")
        layout.addWidget(progress_label)
        
        # Progress bar row
        progress_row = QHBoxLayout()
        progress_row.setSpacing(10)
        self.edit_progress_bar = QProgressBar()
        self.edit_progress_bar.setFixedHeight(18)
        self.edit_progress_bar.setStyleSheet("""
            QProgressBar {
                background: #21262d;
                border: none;
                border-radius: 0px;
                text-align: center;
                color: #f0f6fc;
                font-size: 10px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #238636, stop:1 #2ea043);
            }
        """)
        progress_row.addWidget(self.edit_progress_bar)
        
        self.edit_status_label = QLabel("Ready")
        self.edit_status_label.setStyleSheet("color: #7d8590; font-size: 11px; min-width: 80px;")
        self.edit_status_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        progress_row.addWidget(self.edit_status_label)
        layout.addLayout(progress_row)
        
        # Log text
        self.edit_log_text = QTextEdit()
        self.edit_log_text.setReadOnly(True)
        self.edit_log_text.setPlaceholderText("Edit log will appear here...")
        self.edit_log_text.setStyleSheet("""
            QTextEdit {
                background: #0d1117;
                color: #c9d1d9;
                border: none;
                border-radius: 0px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 11px;
                padding: 8px;
            }
        """)
        layout.addWidget(self.edit_log_text, 1)
        
        # Initialize edit settings
        self._edit_settings = {
            'resolution': 'Original',
            'enable_logo': False,
            'logo_path': '',
            'logo_position': 'Bottom-Right',
            'logo_opacity': 80,
            'logo_scale': 15,
            'enable_trim': False,
            'trim_start': 0,
            'trim_end': 0,
            'mute_audio': False,
            'volume': 100,
            'speed': 1.0,
            'output_format': 'MP4 (H.264)',
            'quality_crf': 23
        }
        self._edit_stopped = False
        
        return tab_widget
    
    def show_image_options_dialog(self):
        """Show image download options dialog"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Image Download Options")
        dialog.setFixedSize(450, 450)
        dialog.setStyleSheet("""
            QDialog {
                background: #161b22;
                color: #f0f6fc;
                border: 1px solid #30363d;
                border-radius: 12px;
            }
            QLabel {
                color: #f0f6fc;
                font-size: 12px;
                border: none;
                background: transparent;
            }
            QCheckBox {
                color: #f0f6fc;
                font-size: 12px;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #30363d;
                border-radius: 4px;
                background: #21262d;
            }
            QCheckBox::indicator:checked {
                background: #238636;
                border-color: #238636;
            }
            QComboBox {
                background: #21262d;
                color: #f0f6fc;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 13px;
                min-width: 160px;
                min-height: 32px;
            }
            QComboBox::drop-down {
                border: none;
                width: 24px;
            }
            QComboBox::down-arrow {
                width: 12px;
                height: 12px;
            }
            QSpinBox {
                background: #21262d;
                color: #f0f6fc;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 13px;
                min-width: 80px;
                min-height: 32px;
            }
        """)
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(15)
        layout.setContentsMargins(25, 25, 25, 25)
        
        # Title
        title = QLabel("Download Options")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #58a6ff;")
        layout.addWidget(title)
        
        # Options grid
        options_layout = QVBoxLayout()
        options_layout.setSpacing(12)
        
        # Checkboxes
        subfolder_cb = QCheckBox("Create subfolder by platform")
        subfolder_cb.setChecked(self._image_subfolder)
        options_layout.addWidget(subfolder_cb)
        
        skip_dup_cb = QCheckBox("Skip duplicate images")
        skip_dup_cb.setChecked(self._image_skip_duplicates)
        options_layout.addWidget(skip_dup_cb)
        
        highres_cb = QCheckBox("Get highest resolution")
        highres_cb.setChecked(self._image_highres)
        options_layout.addWidget(highres_cb)
        
        skip_icons_cb = QCheckBox("Skip icons and thumbnails")
        skip_icons_cb.setChecked(self._image_skip_icons)
        options_layout.addWidget(skip_icons_cb)
        
        overwrite_cb = QCheckBox("Overwrite existing files")
        overwrite_cb.setChecked(self._image_overwrite)
        options_layout.addWidget(overwrite_cb)
        
        options_layout.addSpacing(15)
        
        # Format filter
        format_row = QHBoxLayout()
        format_label = QLabel("Image format:")
        format_label.setFixedWidth(150)
        format_row.addWidget(format_label)
        format_combo = QComboBox()
        format_combo.addItems(["All formats", "JPG/JPEG", "PNG", "GIF", "WebP"])
        format_combo.setCurrentText(self._image_format)
        format_row.addWidget(format_combo)
        format_row.addStretch()
        options_layout.addLayout(format_row)
        
        # Concurrent downloads
        concurrent_row = QHBoxLayout()
        concurrent_label = QLabel("Concurrent downloads:")
        concurrent_label.setFixedWidth(150)
        concurrent_row.addWidget(concurrent_label)
        concurrent_spin = QSpinBox()
        concurrent_spin.setRange(1, 10)
        concurrent_spin.setValue(self._image_concurrent)
        concurrent_row.addWidget(concurrent_spin)
        concurrent_row.addStretch()
        options_layout.addLayout(concurrent_row)
        
        # Min size
        size_row = QHBoxLayout()
        size_label = QLabel("Minimum size (KB):")
        size_label.setFixedWidth(150)
        size_row.addWidget(size_label)
        min_size_spin = QSpinBox()
        min_size_spin.setRange(0, 10000)
        min_size_spin.setValue(self._image_min_size)
        size_row.addWidget(min_size_spin)
        size_row.addStretch()
        options_layout.addLayout(size_row)
        
        # Pinterest max images
        pinterest_row = QHBoxLayout()
        pinterest_label = QLabel("Pinterest search max:")
        pinterest_label.setFixedWidth(150)
        pinterest_label.setToolTip("Maximum images to download from Pinterest search URLs")
        pinterest_row.addWidget(pinterest_label)
        pinterest_spin = QSpinBox()
        pinterest_spin.setRange(10, 500)
        pinterest_spin.setValue(self._image_pinterest_max)
        pinterest_spin.setToolTip("Maximum images to download from Pinterest search URLs")
        pinterest_row.addWidget(pinterest_spin)
        pinterest_row.addStretch()
        options_layout.addLayout(pinterest_row)
        
        layout.addLayout(options_layout)
        layout.addStretch()
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        def save_and_close():
            # Save values
            self._image_subfolder = subfolder_cb.isChecked()
            self._image_skip_duplicates = skip_dup_cb.isChecked()
            self._image_highres = highres_cb.isChecked()
            self._image_skip_icons = skip_icons_cb.isChecked()
            self._image_overwrite = overwrite_cb.isChecked()
            self._image_format = format_combo.currentText()
            self._image_concurrent = concurrent_spin.value()
            self._image_min_size = min_size_spin.value()
            self._image_pinterest_max = pinterest_spin.value()
            dialog.accept()
        
        save_btn = QPushButton("Save")
        save_btn.setFixedSize(100, 36)
        save_btn.clicked.connect(save_and_close)
        save_btn.setStyleSheet("""
            QPushButton {
                background: #238636;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #2ea043;
            }
        """)
        btn_layout.addWidget(save_btn)
        
        layout.addLayout(btn_layout)
        
        # Center dialog on screen
        screen = QApplication.primaryScreen().geometry()
        dialog_x = (screen.width() - dialog.width()) // 2
        dialog_y = (screen.height() - dialog.height()) // 2
        dialog.move(dialog_x, dialog_y)
        
        dialog.exec()
    
    def stop_image_download(self):
        """Stop ongoing image download"""
        self.image_download_stopped = True
        self.image_status_label.setText("Stopping...")
        self.image_stop_btn.setEnabled(False)
    
    def get_multiple_info(self):
        """Get info for multiple URLs using dialog display"""
        selected_urls = self.url_list_widget.get_selected_urls()
        if not selected_urls:
            QMessageBox.warning(self, "Warning", "Please add URLs and select which ones to get info for")
            return
        
        # Check for TikTok profile URLs
        tiktok_profile_urls = [url for url in selected_urls if self.is_tiktok_profile_url(url)]
        if tiktok_profile_urls:
            QMessageBox.warning(
                self, 
                "TikTok Profile URL Detected",
                f"This type of URL can't be used in this feature.\n\n"
                f"Found {len(tiktok_profile_urls)} TikTok profile URL(s) in your selection.\n\n"
                f"Please use the 'Profile Video Download' tab instead to download videos from TikTok profiles."
            )
            return
        
        # Check for problematic URLs and warn user
        problematic_urls = []
        for url in selected_urls:
            if ('facebook.com/people/' in url and 'pfbid' in url) or 'facebook.com/share/' in url:
                problematic_urls.append(url)
        
        if problematic_urls:
            reply = QMessageBox.question(self, "URL Notice", 
                f"Found {len(problematic_urls)} problematic URLs which may not work.\n\n"
                "These URL types are not well supported. Please use direct video post URLs instead.\n\n"
                "Continue anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.No:
                return
        
        # Show progress in the text area while processing
        self.multi_info_text.clear()
        self.multi_info_text.append(f"[?] Getting info for {len(selected_urls)} selected videos...")
        self.multi_info_text.append("Please wait...")
        
        # Process URLs and collect results
        video_results = []
        
        for i, url in enumerate(selected_urls):
            try:
                # Update progress
                self.multi_info_text.append(f"[{i+1}/{len(selected_urls)}] Checking: {url[:50]}...")
                QApplication.processEvents()  # Allow UI to update
                
                info = self.dl.get_info(url)
                if info and not info.get('error'):
                    # Add URL to the data for reference
                    info['url'] = url
                    video_results.append(info)
                elif info and info.get('error'):
                    # Add error info with URL
                    error_data = {
                        'error': True,
                        'message': info.get('message', 'Unknown error'),
                        'url': url,
                        'platform': info.get('platform', 'Unknown')
                    }
                    video_results.append(error_data)
                else:
                    # Add failure info
                    error_data = {
                        'error': True,
                        'message': 'Failed to get info - no data returned',
                        'url': url,
                        'platform': 'Unknown'
                    }
                    video_results.append(error_data)
                    
            except Exception as e:
                # Add exception info
                error_data = {
                    'error': True,
                    'message': f'Exception: {str(e)}',
                    'url': url,
                    'platform': 'Unknown'
                }
                video_results.append(error_data)
        
        # Clear the progress text
        self.multi_info_text.clear()
        self.multi_info_text.append(f"[OK] Info check completed for {len(selected_urls)} videos")
        self.multi_info_text.append("[L] Results shown in dialog - check individual video details")
        
        # Show results in dialog
        if video_results:
            dialog = MultipleVideoInfoDialog(self, video_results)
            dialog.exec()
        else:
            QMessageBox.information(self, "No Results", "No video information could be retrieved.")
    
    def show_url_help(self):
        """Show help dialog with supported URL formats"""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QScrollArea
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Supported URL Formats")
        dialog.setFixedSize(500, 400)
        dialog.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint)
        dialog.setStyleSheet("""
            QDialog {
                background: #161b22;
                color: #f0f6fc;
                border: 2px solid #30363d;
                border-radius: 12px;
            }
            QLabel {
                color: #f0f6fc;
                font-size: 12px;
                border: none;
                background: transparent;
            }
        """)
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title = QLabel("[L] Supported Video URL Formats")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #58a6ff; font-size: 14px; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # Scrollable content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                background: #21262d;
                border: 1px solid #30363d;
                border-radius: 6px;
            }
        """)
        
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        
        help_text = """
<b style="color: #2ea043;">[OK] SUPPORTED PLATFORMS:</b><br><br>

<b style="color: #58a6ff;">YouTube:</b><br>
- youtube.com/watch?v=VIDEO_ID<br>
- youtu.be/VIDEO_ID<br>
- youtube.com/playlist?list=PLAYLIST_ID<br><br>

<b style="color: #58a6ff;">Facebook:</b><br>
- facebook.com/watch/?v=VIDEO_ID<br>
- facebook.com/USERNAME/videos/VIDEO_ID<br>
- fb.watch/VIDEO_ID<br><br>

<b style="color: #58a6ff;">TikTok:</b><br>
- tiktok.com/@username/video/VIDEO_ID<br>
- vm.tiktok.com/SHORT_CODE<br><br>

<b style="color: #58a6ff;">Instagram:</b><br>
- instagram.com/p/POST_ID<br>
- instagram.com/reel/REEL_ID<br><br>

<b style="color: #58a6ff;">Twitter/X:</b><br>
- twitter.com/username/status/TWEET_ID<br>
- x.com/username/status/TWEET_ID<br><br>

<b style="color: #58a6ff;">Other Platforms:</b><br>
- Vimeo, Twitch, Dailymotion, and 1000+ more<br><br>

<b style="color: #f85149;">[X] NOT SUPPORTED:</b><br>
- Profile/channel URLs (use direct video links)<br>
- Share URLs (copy the original video URL)<br>
- Private or restricted videos<br>
- Live streams (in most cases)<br><br>

<b style="color: #ffab00;">[*] TIPS:</b><br>
- Always use direct video URLs, not profile links<br>
- If a URL doesn't work, try copying it again from the source<br>
- Some platforms may require the video to be public<br>
- Check the video is still available and not deleted
        """
        
        content_label = QLabel(help_text)
        content_label.setWordWrap(True)
        content_label.setStyleSheet("font-size: 11px; line-height: 1.4;")
        content_layout.addWidget(content_label)
        
        scroll.setWidget(content_widget)
        layout.addWidget(scroll)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        self.style_btn_primary(close_btn)
        layout.addWidget(close_btn)
        
        dialog.exec()

    def clear_all_urls(self):
        """Clear all URLs and update status"""
        self.url_list_widget.clear_all()
        self.update_url_status()
        self.multi_log("[D] Cleared all URLs")
    
    def update_url_status(self):
        """Update the URL status label"""
        total_urls = len(self.url_list_widget.get_all_urls())
        selected_urls = len(self.url_list_widget.get_selected_urls())
        
        if total_urls == 0:
            self.url_status_label.setText("No URLs added")
            self.url_status_label.setStyleSheet("color: #7d8590; font-size: 11px; font-style: italic; border: none; background: transparent;")
        else:
            self.url_status_label.setText(f"{selected_urls}/{total_urls} URLs selected")
            if selected_urls == 0:
                self.url_status_label.setStyleSheet("color: #f85149; font-size: 11px; font-weight: bold; border: none; background: transparent;")
            else:
                self.url_status_label.setStyleSheet("color: #2ea043; font-size: 11px; font-weight: bold; border: none; background: transparent;")
    
    def browse_multi_output(self):
        """Browse for multiple download output directory"""
        folder = QFileDialog.getExistingDirectory(self, "Select Folder for Multiple Downloads")
        if folder:
            self.multi_output.setText(folder)
        """Browse for multiple download output directory"""
        folder = QFileDialog.getExistingDirectory(self, "Select Folder for Multiple Downloads")
        if folder:
            self.multi_output.setText(folder)
    
    def start_multiple_downloads(self):
        """Start downloading multiple URLs"""
        selected_urls = self.url_list_widget.get_selected_urls()
        if not selected_urls:
            QMessageBox.warning(self, "Warning", "Please add URLs and select which ones to download")
            return
        
        # Check for TikTok profile URLs
        tiktok_profile_urls = [url for url in selected_urls if self.is_tiktok_profile_url(url)]
        if tiktok_profile_urls:
            QMessageBox.warning(
                self, 
                "TikTok Profile URL Detected",
                f"This type of URL can't be used in this feature.\n\n"
                f"Found {len(tiktok_profile_urls)} TikTok profile URL(s) in your selection.\n\n"
                f"Please use the 'Profile Video Download' tab instead to download videos from TikTok profiles."
            )
            return
        
        # Get settings from Multiple Download tab
        settings = {
            'quality': self.multi_quality.currentText(),
            'audio': self.multi_audio_cb.isChecked(),
            'subtitle': self.multi_subtitle_cb.isChecked(),
            'format': self.multi_format.currentText(),
            'convert': False,  # Can add checkbox later if needed
            'use_caption': True,  # Default to true for multiple downloads
            'mute': self.multi_mute_cb.isChecked()
        }
        
        # Update output directory
        output_dir = self.multi_output.text().strip() or "downloads"
        self.dl.output_dir = Path(output_dir)
        self.dl.output_dir.mkdir(exist_ok=True)
        
        # Create and show multiple progress dialog
        self.multi_progress_dialog = MultipleProgressDialog(self, len(selected_urls))
        self.multi_progress_dialog.show()
        
        # Start multiple download worker
        self.multi_worker = MultipleDownloadWorker(self.dl, selected_urls, settings)
        self.multi_worker.progress.connect(self.multi_log)
        # Remove the current progress connection since we simplified it
        # self.multi_worker.progress_percent.connect(self.multi_progress_dialog.update_current_progress)
        self.multi_worker.video_started.connect(self.on_multi_video_started)
        self.multi_worker.video_completed.connect(self.on_multi_video_completed)
        self.multi_worker.batch_completed.connect(self.on_multi_batch_completed)
        
        # Connect dialog controls to worker
        self.multi_progress_dialog.finished.connect(self.handle_multi_progress_dialog_close)
        
        # Connect pause/resume functionality
        def handle_dialog_pause():
            if hasattr(self, 'multi_worker') and self.multi_worker:
                if self.multi_progress_dialog.paused:
                    self.multi_worker.resume()
                    self.multi_log("[>] Downloads resumed from dialog")
                else:
                    self.multi_worker.pause()
                    self.multi_log("[||] Downloads paused from dialog")
        
        self.multi_progress_dialog.pause_btn.clicked.connect(handle_dialog_pause)
        
        self.multi_worker.start()
        
        # Update UI state
        self.multi_download_btn.setEnabled(False)
        self.multi_pause_btn.setEnabled(True)
        self.multi_stop_btn.setEnabled(True)
        
        self.multi_log(f"[!] Starting batch download of {len(selected_urls)} selected videos...")
        self.update_multi_status(f"Downloading: 0/{len(selected_urls)} completed")

    def paste_multiple_urls(self):
        """Paste multiple URLs from clipboard"""
        clipboard_text = QApplication.clipboard().text()
        if clipboard_text.strip():
            # Debug: Show what was pasted
            lines = clipboard_text.strip().split('\n')
            self.multi_log(f"[L] Pasting {len(lines)} lines from clipboard:")
            for i, line in enumerate(lines[:5], 1):  # Show first 5 lines
                if line.strip():
                    self.multi_log(f"   {i}. {line.strip()[:60]}...")
            if len(lines) > 5:
                self.multi_log(f"   ... and {len(lines)-5} more lines")
            
            added_count, invalid_count, problematic_count = self.url_list_widget.add_urls_from_text(clipboard_text)
            
            # Detailed results
            self.multi_log(f"[G] Results: {added_count} valid, {problematic_count} problematic, {invalid_count} invalid")
            
            if added_count > 0:
                self.multi_log(f"[OK] Added {added_count} valid URLs")
            if problematic_count > 0:
                self.multi_log(f"[!] Added {problematic_count} problematic URLs (may not work)")
            if invalid_count > 0:
                self.multi_log(f"[X] Skipped {invalid_count} invalid URLs")
            
            if added_count == 0 and problematic_count == 0:
                if invalid_count > 0:
                    self.multi_log(f"[X] Found only invalid URLs in clipboard")
                else:
                    self.multi_log("[!] No valid URLs found in clipboard")
        else:
            self.multi_log("[!] Clipboard is empty")
        
        # Update status after pasting
        self.update_url_status()

    
    def pause_multiple_downloads(self):
        """Pause/Resume multiple downloads"""
        if self.multi_worker:
            if self.multi_worker.paused:
                self.multi_worker.resume()
                self.multi_pause_btn.setText("Pause")
                self.multi_log("Downloads resumed")
                self.update_multi_status("Downloading (resumed)")
            else:
                self.multi_worker.pause()
                self.multi_pause_btn.setText("Resume")
                self.multi_log("Downloads paused")
                self.update_multi_status("Paused")
    
    def stop_multiple_downloads(self):
        """Stop multiple downloads"""
        if self.multi_worker:
            self.multi_worker.stop()
            # Force terminate if still running after a short wait
            if self.multi_worker.isRunning():
                self.multi_worker.terminate()
                self.multi_worker.wait(2000)  # Wait up to 2 seconds
            self.multi_log("[STOP] Downloads stopped by user")
            self.update_multi_status("Stopped")
            # Reset UI
            self.multi_download_btn.setEnabled(True)
            self.multi_pause_btn.setEnabled(False)
            self.multi_stop_btn.setEnabled(False)
    
    def handle_multi_progress_dialog_close(self, result):
        """Handle when multiple progress dialog is closed"""
        if hasattr(self, 'multi_progress_dialog') and self.multi_progress_dialog.cancelled:
            # User cancelled the operation
            if self.multi_worker and self.multi_worker.isRunning():
                self.multi_worker.stopped = True
                self.multi_worker.terminate()
                self.multi_worker.wait()
            
            # Reset UI state
            self.multi_download_btn.setEnabled(True)
            self.multi_pause_btn.setEnabled(False)
            self.multi_stop_btn.setEnabled(False)
            self.update_multi_status("Cancelled by user")
            self.multi_log("[STOP] Multiple downloads cancelled by user")

    def on_multi_video_started(self, index, url):
        """Handle when a video download starts"""
        self.multi_log(f"[DL] [{index+1}] Starting: {url[:60]}...")
        if hasattr(self, 'multi_progress_dialog'):
            self.multi_progress_dialog.start_video(index, url)
    
    def on_multi_video_completed(self, index, success, message, file_path):
        """Handle when a video download completes"""
        status = "[OK]" if success else "[X]"
        self.multi_log(f"{status} [{index+1}] {message}")
        if hasattr(self, 'multi_progress_dialog'):
            self.multi_progress_dialog.complete_video(index, success)
    
    def on_multi_batch_completed(self, summary):
        """Handle when all downloads are complete"""
        total = summary['total']
        completed = summary['completed']
        failed = summary['failed']
        stopped = summary['stopped']
        
        # Reset UI state
        self.multi_download_btn.setEnabled(True)
        self.multi_pause_btn.setEnabled(False)
        self.multi_stop_btn.setEnabled(False)
        self.multi_pause_btn.setText("Pause")
        
        # Show completion summary
        if stopped:
            self.multi_log(f"[STOP] Batch stopped: {completed}/{total} completed, {failed} failed")
            self.update_multi_status(f"Stopped: {completed}/{total} completed")
        else:
            self.multi_log(f"[*] Batch complete: {completed}/{total} successful, {failed} failed")
            self.update_multi_status(f"Complete: {completed}/{total} successful")
        
        # Show failed URLs if any
        if summary['failed_urls']:
            self.multi_log("[X] Failed URLs:")
            for url in summary['failed_urls']:
                self.multi_log(f"   - {url}")
        
        # Show completion dialog
        if completed > 0:
            self.show_multi_completion_dialog(summary)
    
    def show_multi_completion_dialog(self, summary):
        """Show modern completion dialog for multiple downloads"""
        dialog = BatchCompleteDialog(self, summary)
        dialog.exec()
    
    def multi_log(self, message):
        """Add message to multiple download log"""
        self.multi_progress_text.append(message)
        self.multi_progress_text.verticalScrollBar().setValue(
            self.multi_progress_text.verticalScrollBar().maximum()
        )
    
    def update_multi_status(self, status):
        """Update multiple download status label"""
        self.multi_status_label.setText(status)

    def style_tabs(self, tab_widget):
        """Style the tab widget"""
        tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #30363d;
                border-radius: 0px;
                background: #161b22;
                margin-top: 2px;
            }
            QTabWidget::tab-bar {
                alignment: left;
            }
            QTabBar::tab {
                background: #21262d;
                color: #7d8590;
                padding: 8px 16px;
                margin-right: 2px;
                border-radius: 0px;
                font-weight: 500;
                min-width: 120px;
            }
            QTabBar::tab:hover {
                background: #30363d;
                color: #f0f6fc;
            }
            QTabBar::tab:selected {
                background: #58a6ff;
                color: #ffffff;
                font-weight: bold;
            }
            QTabBar::tab:!selected {
                margin-top: 2px;
            }
        """)

    def create_custom_titlebar(self, main_layout):
        """Create custom window title bar with modern toolbar"""
        titlebar = QFrame()
        titlebar.setFixedHeight(50)
        titlebar.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #1e1e2e, stop:0.5 #2a2a3a, stop:1 #1e1e2e);
                border-bottom: 1px solid #404040;
            }
        """)
        
        titlebar_layout = QHBoxLayout(titlebar)
        titlebar_layout.setContentsMargins(15, 0, 5, 0)
        titlebar_layout.setSpacing(15)
        
        # === LEFT: App Icon & Title ===
        left_section = QHBoxLayout()
        left_section.setSpacing(10)
        
        # App icon - try multiple paths for dev and EXE
        app_icon = QLabel()
        app_icon.setFrameStyle(QLabel.Shape.NoFrame)
        app_icon.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        app_icon.setStyleSheet("border: 0px; background: none; outline: 0px;")
        
        logo_loaded = False
        logo_paths = [
            Path("logo/logo.png"),
            Path("logo.png"),
            Path(__file__).parent / "logo" / "logo.png",
            Path(__file__).parent / "logo.png",
        ]
        
        # For PyInstaller EXE
        import sys
        if getattr(sys, 'frozen', False):
            base_path = Path(sys._MEIPASS)
            logo_paths.insert(0, base_path / "logo" / "logo.png")
            logo_paths.insert(1, base_path / "logo.png")
        
        for logo_path in logo_paths:
            try:
                if logo_path.exists():
                    pix = QPixmap(str(logo_path)).scaled(24, 24, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    if not pix.isNull():
                        app_icon.setPixmap(pix)
                        logo_loaded = True
                        break
            except:
                continue
        
        if not logo_loaded:
            app_icon.setText("V")
            app_icon.setStyleSheet("font-size: 18px; color: #58a6ff; border: 0px; background: none; outline: 0px;")
        
        # App title
        app_title = QLabel("VIDT - Video Downloader Tool")
        app_title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        app_title.setFrameStyle(QLabel.Shape.NoFrame)
        app_title.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        app_title.setStyleSheet("color: #ffffff; border: 0px; background: none; outline: 0px;")
        
        # Version label (green color)
        version_label = QLabel(f"v{self.VERSION}")
        version_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        version_label.setFrameStyle(QLabel.Shape.NoFrame)
        version_label.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        version_label.setStyleSheet("color: #22c55e; border: 0px; background: none; outline: 0px; margin-left: 5px;")
        
        # App ID label (for management)
        app_id_label = QLabel(f"[{self.app_id}]")
        app_id_label.setFont(QFont("Segoe UI", 9))
        app_id_label.setFrameStyle(QLabel.Shape.NoFrame)
        app_id_label.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        app_id_label.setStyleSheet("color: #6b7280; border: 0px; background: none; outline: 0px; margin-left: 8px;")
        app_id_label.setToolTip(f"Installation ID: {self.app_id}")
        
        left_section.addWidget(app_icon)
        left_section.addWidget(app_title)
        left_section.addWidget(version_label)
        left_section.addWidget(app_id_label)
        
        # === CENTER: Toolbar Actions ===
        center_section = QHBoxLayout()
        center_section.setSpacing(8)
        
        # Quick action buttons in title bar
        self.tb_paste_btn = self.create_titlebar_btn("\U0001F4CB", "Paste")  # clipboard
        self.tb_paste_btn.clicked.connect(self.paste_url)
        
        self.tb_info_btn = self.create_titlebar_btn("\u2139", "Info")  # info
        self.tb_info_btn.clicked.connect(self.get_info)
        
        self.tb_download_btn = self.create_titlebar_btn("\u2B07", "Download")  # down arrow
        self.tb_download_btn.clicked.connect(self.download)
        
        # Separator
        sep = QFrame()
        sep.setFixedSize(1, 25)
        sep.setStyleSheet("background: #404040; border: none;")
        
        self.tb_folder_btn = self.create_titlebar_btn("\U0001F4C1", "Folder")  # folder
        self.tb_folder_btn.clicked.connect(self.open_downloads_folder)
        
        self.tb_settings_btn = self.create_titlebar_btn("\u2699", "Settings")  # gear
        self.tb_settings_btn.clicked.connect(self.show_settings)
        
        center_section.addWidget(self.tb_paste_btn)
        center_section.addWidget(self.tb_info_btn)
        center_section.addWidget(self.tb_download_btn)
        center_section.addWidget(sep)
        center_section.addWidget(self.tb_folder_btn)
        center_section.addWidget(self.tb_settings_btn)
        
        # === RIGHT: Window Controls ===
        right_section = QHBoxLayout()
        right_section.setSpacing(0)
        
        # License info indicator
        self.license_info_label = QLabel("")
        self.license_info_label.setFont(QFont("Segoe UI", 9))
        self.license_info_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.license_info_label.setFrameStyle(QLabel.Shape.NoFrame)
        self.license_info_label.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.license_info_label.setStyleSheet("color: #58a6ff; border: 0px; background: none; outline: 0px; margin-right: 15px;")
        self.update_license_display()
        
        # Status indicator
        self.title_status = QLabel("Ready")
        self.title_status.setFont(QFont("Segoe UI", 9))
        self.title_status.setFixedWidth(220)
        self.title_status.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.title_status.setFrameStyle(QLabel.Shape.NoFrame)
        self.title_status.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.title_status.setStyleSheet("color: #00ff88; border: 0px; background: none; outline: 0px; margin-right: 10px;")
        
        # Window control buttons
        minimize_btn = self.create_window_btn("\u2014", "Minimize")  # em dash
        minimize_btn.clicked.connect(self.showMinimized)
        
        maximize_btn = self.create_window_btn("\u25A1", "Maximize")  # white square
        maximize_btn.clicked.connect(self.toggle_maximize)
        
        close_btn = self.create_window_btn("\u2715", "Close")  # multiplication x
        close_btn.clicked.connect(self.close)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #ffffff;
                font-size: 14px;
                font-weight: bold;
                padding: 0;
            }
            QPushButton:hover {
                background: #ff4444;
                color: white;
            }
        """)
        
        right_section.addWidget(self.license_info_label)
        right_section.addWidget(self.title_status)
        right_section.addWidget(minimize_btn)
        right_section.addWidget(maximize_btn)
        right_section.addWidget(close_btn)
        
        # === ASSEMBLE TITLEBAR ===
        titlebar_layout.addLayout(left_section)
        titlebar_layout.addStretch()
        titlebar_layout.addLayout(center_section)
        titlebar_layout.addStretch()
        titlebar_layout.addLayout(right_section)
        
        # Make titlebar draggable
        titlebar.mousePressEvent = self.titlebar_mouse_press
        titlebar.mouseMoveEvent = self.titlebar_mouse_move
        
        main_layout.addWidget(titlebar)
    
    def create_titlebar_btn(self, icon, tooltip):
        """Create button for title bar toolbar"""
        btn = QPushButton(icon)
        btn.setFixedSize(32, 32)
        btn.setToolTip(tooltip)
        btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 16px;
                color: #ffffff;
                font-size: 12px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.2);
                border-color: rgba(255, 255, 255, 0.4);
            }
            QPushButton:pressed {
                background: rgba(255, 255, 255, 0.3);
            }
        """)
        return btn
    
    def create_window_btn(self, icon, tooltip):
        """Create window control button"""
        btn = QPushButton(icon)
        btn.setFixedSize(45, 30)
        btn.setToolTip(tooltip)
        btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #8b949e;
                font-size: 16px;
                font-family: Consolas, monospace;
                font-weight: normal;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.1);
                color: #ffffff;
            }
        """)
        return btn
    
    def toggle_maximize(self):
        """Toggle window maximize state"""
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()
    
    def titlebar_mouse_press(self, event):
        """Handle mouse press on title bar for dragging"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
    
    def titlebar_mouse_move(self, event):
        """Handle mouse move for window dragging"""
        if event.buttons() == Qt.MouseButton.LeftButton and hasattr(self, 'drag_position'):
            self.move(event.globalPosition().toPoint() - self.drag_position)

    def center_window(self):
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)
    
    def create_section(self, title):
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background: #161b22;
                border: 1px solid #21262d;
                border-radius: 10px;
            }
        """)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)
        
        label = QLabel(title)
        label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        label.setStyleSheet("color: #58a6ff; border: none;")
        layout.addWidget(label)
        
        return frame
    
    def create_label(self, text):
        label = QLabel(text)
        label.setStyleSheet("color: #f0f6fc; font-weight: bold; border: none;")
        return label
    
    def style_input(self, widget):
        widget.setStyleSheet("""
            QLineEdit {
                background: #21262d;
                border: 2px solid #30363d;
                border-radius: 6px;
                color: #f0f6fc;
                padding: 8px 12px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #58a6ff;
            }
            QLineEdit::placeholder {
                color: #7d8590;
            }
        """)
    
    def style_combo(self, widget):
        widget.setFixedHeight(36)
        widget.setStyleSheet("""
            QComboBox {
                background: rgba(33, 38, 45, 0.9);
                border: 2px solid #30363d;
                border-radius: 8px;
                color: #f0f6fc;
                padding: 6px 12px;
                font-size: 13px;
                font-weight: 500;
                min-width: 80px;
            }
            QComboBox:hover {
                border-color: #58a6ff;
                background: rgba(22, 27, 34, 0.95);
            }
            QComboBox:focus {
                border-color: #58a6ff;
                background: rgba(22, 27, 34, 1.0);
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 30px;
                border: none;
                background: transparent;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 6px solid transparent;
                border-right: 6px solid transparent;
                border-top: 8px solid #f0f6fc;
                margin-right: 8px;
            }
            QComboBox::down-arrow:hover {
                border-top-color: #58a6ff;
            }
            QComboBox QAbstractItemView {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #21262d, stop:1 #161b22);
                color: #f0f6fc;
                selection-background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #58a6ff, stop:1 #4a90e2);
                selection-color: #ffffff;
                border: 2px solid #58a6ff;
                border-radius: 8px;
                padding: 4px;
                font-size: 13px;
                font-weight: 500;
                outline: none;
            }
            QComboBox QAbstractItemView::item {
                background: transparent;
                color: #f0f6fc;
                padding: 8px 12px;
                margin: 2px;
                border-radius: 6px;
                min-height: 20px;
            }
            QComboBox QAbstractItemView::item:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 rgba(88, 166, 255, 0.3), stop:1 rgba(74, 144, 226, 0.3));
                color: #ffffff;
            }
            QComboBox QAbstractItemView::item:selected {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #58a6ff, stop:1 #4a90e2);
                color: #ffffff;
                font-weight: bold;
            }
        """)
    
    def style_checkbox(self, widget):
        widget.setStyleSheet("""
            QCheckBox {
                color: #f0f6fc;
                font-size: 13px;
                spacing: 8px;
                border: none;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #30363d;
                border-radius: 4px;
                background: #21262d;
            }
            QCheckBox::indicator:hover {
                border-color: #58a6ff;
            }
            QCheckBox::indicator:checked {
                background: #58a6ff;
                border-color: #58a6ff;
            }
        """)
    
    def style_text(self, widget):
        widget.setStyleSheet("""
            QTextEdit {
                background: #21262d;
                border: none;
                border-radius: 6px;
                color: #f0f6fc;
                padding: 10px;
                font-size: 12px;
            }
            QScrollBar:vertical {
                background: #161b22;
                width: 12px;
                border-radius: 6px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: #30363d;
                border-radius: 6px;
                min-height: 20px;
                margin: 2px;
            }
            QScrollBar::handle:vertical:hover {
                background: #58a6ff;
            }
            QScrollBar::handle:vertical:pressed {
                background: #4a90e2;
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                border: none;
                background: none;
                height: 0px;
            }
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {
                background: transparent;
            }
            QScrollBar:horizontal {
                background: #161b22;
                height: 12px;
                border-radius: 6px;
                margin: 0;
            }
            QScrollBar::handle:horizontal {
                background: #30363d;
                border-radius: 6px;
                min-width: 20px;
                margin: 2px;
            }
            QScrollBar::handle:horizontal:hover {
                background: #58a6ff;
            }
            QScrollBar::handle:horizontal:pressed {
                background: #4a90e2;
            }
            QScrollBar::add-line:horizontal,
            QScrollBar::sub-line:horizontal {
                border: none;
                background: none;
                width: 0px;
            }
            QScrollBar::add-page:horizontal,
            QScrollBar::sub-page:horizontal {
                background: transparent;
            }
        """)
    
    def style_btn_green(self, btn):
        btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #22c55e, stop:1 #16a34a);
                color: white;
                border: none;
                border-radius: 0px;
                font-size: 13px;
                font-weight: bold;
                padding: 8px 24px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #4ade80, stop:1 #22c55e);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #16a34a, stop:1 #15803d);
            }
            QPushButton:disabled {
                background: #374151;
                color: #6b7280;
            }
        """)
    
    def style_btn_primary(self, btn):
        btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #6366f1, stop:1 #4f46e5);
                color: white;
                border: none;
                border-radius: 0px;
                font-size: 13px;
                font-weight: bold;
                padding: 8px 24px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #818cf8, stop:1 #6366f1);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #4f46e5, stop:1 #4338ca);
            }
            QPushButton:disabled {
                background: #374151;
                color: #6b7280;
            }
        """)
    
    def style_btn_secondary(self, btn):
        btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #374151, stop:1 #1f2937);
                color: #e5e7eb;
                border: 1px solid #4b5563;
                border-radius: 0px;
                font-size: 12px;
                font-weight: 600;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #4b5563, stop:1 #374151);
                border-color: #6366f1;
                color: #f3f4f6;
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1f2937, stop:1 #111827);
            }
            QPushButton:disabled {
                background: #1f2937;
                color: #4b5563;
                border-color: #374151;
            }
        """)
    
    def open_downloads_folder(self):
        """Open the downloads folder in file explorer"""
        import subprocess
        import platform
        
        folder_path = Path(self.output.text() or "downloads")
        folder_path.mkdir(exist_ok=True)
        
        try:
            if platform.system() == "Windows":
                subprocess.run(["explorer", str(folder_path)])
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", str(folder_path)])
            else:  # Linux
                subprocess.run(["xdg-open", str(folder_path)])
            self.log("[F] Opened downloads folder")
        except Exception as e:
            self.log(f"[X] Failed to open folder: {e}")
    
    def show_settings(self):
        """Show a modern settings dialog"""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QCheckBox
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Settings")
        dialog.setFixedSize(350, 250)
        dialog.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint)
        dialog.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1e1e2e, stop:1 #11111b);
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 16px;
            }
            QLabel {
                color: #cdd6f4;
                font-size: 12px;
                border: none;
            }
        """)
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(20)
        layout.setContentsMargins(25, 25, 25, 25)
        
        # Title
        title = QLabel("[S] Application Settings")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #89b4fa; font-size: 14px;")
        layout.addWidget(title)
        
        # Settings options
        auto_open_cb = QCheckBox("Auto-open downloads folder")
        auto_open_cb.setChecked(self.settings.value("auto_open_folder", True, type=bool))
        self.style_checkbox(auto_open_cb)
        
        notifications_cb = QCheckBox("Show notifications")
        notifications_cb.setChecked(self.settings.value("show_notifications", True, type=bool))
        self.style_checkbox(notifications_cb)
        
        remember_settings_cb = QCheckBox("Remember all settings on exit")
        remember_settings_cb.setChecked(self.settings.value("remember_settings", True, type=bool))
        self.style_checkbox(remember_settings_cb)
        
        layout.addWidget(auto_open_cb)
        layout.addWidget(notifications_cb)
        layout.addWidget(remember_settings_cb)
        layout.addStretch()
        
        # Save settings when dialog is accepted
        def save_dialog_settings():
            self.settings.setValue("auto_open_folder", auto_open_cb.isChecked())
            self.settings.setValue("show_notifications", notifications_cb.isChecked())
            self.settings.setValue("remember_settings", remember_settings_cb.isChecked())
            self.save_settings()
            dialog.accept()
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        reset_btn = QPushButton("Reset All")
        reset_btn.clicked.connect(self.reset_all_settings)
        self.style_btn_secondary(reset_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        self.style_btn_secondary(cancel_btn)
        
        ok_btn = QPushButton("Save")
        ok_btn.clicked.connect(save_dialog_settings)
        self.style_btn_primary(ok_btn)
        
        btn_layout.addWidget(reset_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(ok_btn)
        
        layout.addLayout(btn_layout)
        
        # Center the dialog on parent window
        dialog.move(
            self.x() + (self.width() - dialog.width()) // 2,
            self.y() + (self.height() - dialog.height()) // 2
        )
        
        dialog.exec()
        self.log("[S] Settings accessed")
    
    def update_title_status(self, status, color="#00ff88"):
        """Update the title bar status"""
        # Only update if text or color actually changed to prevent flickering
        current_text = self.title_status.text()
        if current_text != status:
            self.title_status.setText(status)
        # Only update style if color changed
        if not hasattr(self, '_last_status_color') or self._last_status_color != color:
            self._last_status_color = color
            self.title_status.setStyleSheet(f"color: {color}; border: 0px; background: none; outline: 0px; margin-right: 15px;")

    def paste_url(self):
        self.url_input.setText(QApplication.clipboard().text())
    
    def update_output_directory(self, directory):
        """Update output directory and ensure it's saved"""
        self.log(f"[*] update_output_directory called with: '{directory}'")
        self.output.setText(directory)
        self.dl.output_dir = Path(directory)
        
        # Immediately save and verify
        self.settings.setValue("output_directory", directory)
        self.settings.sync()
        
        # Verify what was actually saved
        saved_value = self.settings.value("output_directory", "FAILED")
        self.log(f"[*] Immediately after save, settings contains: '{saved_value}'")
        
        self.log(f"[F] Output directory updated: {directory}")

    def browse(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            self.update_output_directory(folder)
    
    def log(self, msg):
        self.log_text.append(msg)
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())
    
    def get_info(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Warning", "Please enter a URL")
            return
        
        # Basic URL validation
        if not url.startswith(('http://', 'https://')):
            QMessageBox.warning(self, "Invalid URL", "Please enter a valid URL starting with http:// or https://")
            return
        
        # Check if URL is a TikTok profile URL (not a video URL)
        if self.is_tiktok_profile_url(url):
            QMessageBox.warning(
                self, 
                "TikTok Profile URL Detected",
                "This type of URL can't be used in this feature.\n\n"
                "This appears to be a TikTok profile URL, not a video URL.\n\n"
                "Please use the 'Profile Video Download' tab instead to download videos from TikTok profiles."
            )
            return
        
        # Check if this is a profile URL
        if self.dl.is_profile_url(url):
            reply = QMessageBox.question(self, "Profile URL Detected", 
                f"This appears to be a profile/channel URL rather than a single video.\n\n"
                f"Would you like to:\n"
                f"- Get profile information and download multiple videos\n"
                f"- Or continue to get info for this URL as-is?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes)
            
            if reply == QMessageBox.StandardButton.Yes:
                self.get_profile_info(url)
                return
        
        # Check for known problematic URL patterns
        if 'facebook.com/people/' in url and 'pfbid' in url:
            QMessageBox.information(self, "URL Notice", 
                "This appears to be a Facebook profile URL. For Facebook videos, please use direct video post URLs instead of profile links.\n\n"
                "Supported Facebook URL formats:\n"
                "- facebook.com/watch/?v=VIDEO_ID\n"
                "- facebook.com/USERNAME/videos/VIDEO_ID\n"
                "- fb.watch/VIDEO_ID")
            return
        
        self.log(f"[?] Getting info for: {url[:60]}...")
        self.start_worker('info', url)
    
    def get_profile_info(self, profile_url):
        """Get information about a profile and show download options"""
        self.log(f"[?] Getting profile info for: {profile_url[:60]}...")
        
        # Show progress dialog
        progress_dialog = ProgressDialog(self, "Getting Profile Information", "info")
        progress_dialog.show()
        
        # Start profile info worker
        self.profile_worker = ProfileInfoWorker(self.dl, profile_url)
        self.profile_worker.progress.connect(progress_dialog.update_progress)
        self.profile_worker.done.connect(lambda success, data: self.handle_profile_info_result(success, data, progress_dialog))
        self.profile_worker.start()
    
    def handle_profile_info_result(self, success, data, progress_dialog):
        """Handle profile info extraction result"""
        progress_dialog.close()
        
        if success:
            self.log(f"[OK] Found {data.get('total_found', 0)} videos in profile: {data.get('profile_name', 'Unknown')}")
            
            # Show profile download dialog
            profile_dialog = ProfileDownloadDialog(self, data)
            if profile_dialog.exec() == QDialog.DialogCode.Accepted:
                settings = profile_dialog.get_download_settings()
                self.start_profile_download(data, settings)
        else:
            error_msg = data if isinstance(data, str) else "Failed to get profile information"
            self.log(f"[X] Profile info failed: {error_msg}")
            QMessageBox.warning(self, "Profile Info Failed", f"Could not get profile information:\n\n{error_msg}")
    
    def start_profile_download(self, profile_data, settings):
        """Start downloading videos from profile"""
        videos = settings['videos']
        max_videos = settings['max_videos']
        
        # Pass more videos than requested to account for failures
        # The downloader will stop when it reaches the target successful downloads
        if max_videos:
            # Take 3x more videos as buffer for Facebook's high failure rate
            buffer_count = int(max_videos * 3)
            if len(videos) > buffer_count:
                videos = videos[:buffer_count]
        
        # Extract URLs from video data
        video_urls = [video['url'] for video in videos if video.get('url')]
        
        if not video_urls:
            QMessageBox.warning(self, "No Videos", "No valid video URLs found in this profile.")
            return
        
        self.log(f"[!] Starting download of up to {max_videos if max_videos else len(video_urls)} videos from profile: {profile_data.get('profile_name', 'Unknown')}")
        self.log(f"   (Prepared {len(video_urls)} URLs to handle potential failures)")
        
        # Use the existing multiple download functionality with target count
        self.start_multiple_download_with_urls(video_urls, target_success=max_videos)
    
    def get_profile_info_from_tab(self):
        """Get profile info from the profile tab"""
        selected_urls = self.profile_url_list_widget.get_selected_urls()
        if not selected_urls:
            QMessageBox.warning(self, "Warning", "Please add profile URLs and select which ones to get info for")
            return
        
        # Check for TikTok video URLs (not profile URLs)
        video_urls = [url for url in selected_urls if self.is_tiktok_video_url(url)]
        if video_urls:
            QMessageBox.warning(
                self, 
                "TikTok Video URL Detected",
                f"Found {len(video_urls)} TikTok video URL(s) in your selection.\n\n"
                "This feature is for profile URLs only.\n\n"
                "Please use the 'Single Download' or 'Multiple Download' tab for video URLs."
            )
            return
        
        # Check for Facebook single video URLs (not profile URLs)
        fb_video_urls = [url for url in selected_urls if self.is_facebook_single_video_url(url)]
        if fb_video_urls:
            QMessageBox.warning(
                self, 
                "Facebook Video URL Detected",
                f"Found {len(fb_video_urls)} Facebook video URL(s) in your selection.\n\n"
                "This appears to be a single video link, not a profile page.\n\n"
                "Please use the 'Single Download' or 'Multiple Download' tab for video URLs."
            )
            return
        
        self.profile_videos_text.clear()
        self.profile_videos_text.append(f"[?] Getting info for {len(selected_urls)} profile(s)...")
        
        # Disable buttons during processing
        self.profile_info_btn.setEnabled(False)
        self.profile_download_btn.setEnabled(False)
        
        # Store URLs to process
        self.profile_info_urls = selected_urls.copy()
        self.profile_info_index = 0
        self.profile_info_total_videos = 0
        self.profile_info_results = []
        
        # Show progress dialog
        self.profile_info_dialog = ProgressDialog(self, "Getting Profile Information", "info")
        self.profile_info_dialog.status_label.setText(f"Processing 0/{len(selected_urls)} profiles...")
        self.profile_info_dialog.show()
        
        # Start processing first profile using worker
        self.process_next_profile_info()
    
    def process_next_profile_info(self):
        """Process next profile for info gathering"""
        if self.profile_info_index >= len(self.profile_info_urls):
            # All done - close progress dialog
            if hasattr(self, 'profile_info_dialog'):
                self.profile_info_dialog.close()
            
            self.profile_videos_text.append(f"\n[G] Total: {self.profile_info_total_videos} videos from {len(self.profile_info_urls)} profile(s)")
            self.profile_info_btn.setEnabled(True)
            self.profile_download_btn.setEnabled(True)
            
            # Show completion message
            QMessageBox.information(
                self,
                "Profile Info Complete",
                f"[OK] Finished getting info for {len(self.profile_info_urls)} profile(s)\n\n"
                f"Total videos found: {self.profile_info_total_videos}"
            )
            return
        
        url = self.profile_info_urls[self.profile_info_index]
        self.profile_videos_text.append(f"\n[{self.profile_info_index + 1}/{len(self.profile_info_urls)}] {url[:50]}...")
        
        # Update progress dialog
        if hasattr(self, 'profile_info_dialog'):
            progress = int((self.profile_info_index / len(self.profile_info_urls)) * 100)
            self.profile_info_dialog.progress_bar.setValue(progress)
            self.profile_info_dialog.status_label.setText(f"Processing {self.profile_info_index + 1}/{len(self.profile_info_urls)} profiles...")
        
        # Use worker thread
        self.profile_info_worker = ProfileInfoWorker(self.dl, url)
        self.profile_info_worker.done.connect(self.handle_profile_info_result)
        self.profile_info_worker.start()
    
    def handle_profile_info_result(self, success, data):
        """Handle result from profile info worker"""
        if success:
            profile_name = data.get('profile_name', 'Unknown')
            total_found = data.get('total_found', 0)
            self.profile_videos_text.append(f"   [OK] {profile_name}: {total_found} videos found")
            self.profile_info_total_videos += total_found
            self.profile_info_results.append(data)
        else:
            error_msg = data if isinstance(data, str) else "Unknown error"
            self.profile_videos_text.append(f"   [X] Error: {error_msg[:50]}")
        
        # Process next
        self.profile_info_index += 1
        self.process_next_profile_info()
    
    def download_profile_from_tab(self):
        """Download profile videos directly from tab"""
        selected_urls = self.profile_url_list_widget.get_selected_urls()
        if not selected_urls:
            QMessageBox.warning(self, "Warning", "Please add profile URLs and select which ones to download")
            return
        
        # Check for TikTok video URLs (not profile URLs)
        video_urls = [url for url in selected_urls if self.is_tiktok_video_url(url)]
        if video_urls:
            QMessageBox.warning(
                self, 
                "TikTok Video URL Detected",
                f"Found {len(video_urls)} TikTok video URL(s) in your selection.\n\n"
                "This feature is for profile URLs only.\n\n"
                "Please use the 'Single Download' or 'Multiple Download' tab for video URLs."
            )
            return
        
        # Check for Facebook single video URLs (not profile URLs)
        fb_video_urls = [url for url in selected_urls if self.is_facebook_single_video_url(url)]
        if fb_video_urls:
            QMessageBox.warning(
                self, 
                "Facebook Video URL Detected",
                f"Found {len(fb_video_urls)} Facebook video URL(s) in your selection.\n\n"
                "This appears to be a single video link, not a profile page.\n\n"
                "Please use the 'Single Download' or 'Multiple Download' tab for video URLs."
            )
            return
        
        self.profile_videos_text.clear()
        self.profile_videos_text.append(f"[!] Starting download for {len(selected_urls)} profile(s)...")
        self.profile_progress_text.clear()
        
        # Disable buttons during processing
        self.profile_info_btn.setEnabled(False)
        self.profile_download_btn.setEnabled(False)
        
        # Store profiles to process
        self.pending_profile_urls = selected_urls.copy()
        self.current_profile_index = 0
        self.total_profiles = len(selected_urls)
        self.all_profile_data = []  # Store profile name + videos for subfolder creation
        self.profile_gathering_cancelled = False  # Track cancel state
        
        # Show progress dialog for gathering videos
        self.profile_download_dialog = ProgressDialog(self, "Gathering Profile Videos", "info")
        self.profile_download_dialog.status_label.setText(f"Processing 0/{len(selected_urls)} profiles...")
        self.profile_download_dialog.cancel_btn.clicked.connect(self.cancel_profile_gathering)
        self.profile_download_dialog.show()
        
        # Start processing first profile
        self.process_next_profile()
    
    def cancel_profile_gathering(self):
        """Cancel the profile gathering process"""
        self.profile_gathering_cancelled = True
        if hasattr(self, 'profile_worker') and self.profile_worker and self.profile_worker.isRunning():
            self.profile_worker.terminate()
            self.profile_worker.wait(1000)
        if hasattr(self, 'profile_download_dialog'):
            self.profile_download_dialog.close()
        self.profile_videos_text.append("\n[STOP] Profile gathering cancelled by user")
        self.profile_info_btn.setEnabled(True)
        self.profile_download_btn.setEnabled(True)
    
    def process_next_profile(self):
        """Process the next profile in the queue"""
        # Check if cancelled
        if self.profile_gathering_cancelled:
            return
            
        if self.current_profile_index >= len(self.pending_profile_urls):
            # Close gathering dialog
            if hasattr(self, 'profile_download_dialog'):
                self.profile_download_dialog.close()
            
            # All profiles processed, now download videos profile by profile
            if self.all_profile_data:
                total_videos = sum(len(p['videos']) for p in self.all_profile_data)
                self.total_profile_videos = total_videos  # Store for progress tracking
                self.profile_videos_completed = 0  # Counter for completed videos
                self.profile_videos_text.append(f"\n[DL] Starting download of {total_videos} videos from {len(self.all_profile_data)} profile(s)...")
                
                # Create single progress dialog for all profiles
                self.profile_multi_dialog = MultipleProgressDialog(self, total_videos)
                self.profile_multi_dialog.setWindowTitle(f"Downloading from {len(self.all_profile_data)} Profiles")
                self.profile_multi_dialog.show()
                
                # Start downloading profiles one by one
                self.current_download_profile_index = 0
                self.total_successful = 0
                self.total_failed = 0
                self.download_next_profile_videos()
            else:
                self.profile_videos_text.append("\n[X] No videos found in any profile")
                self.profile_info_btn.setEnabled(True)
                self.profile_download_btn.setEnabled(True)
            return
        
        url = self.pending_profile_urls[self.current_profile_index]
        self.profile_videos_text.append(f"\n[{self.current_profile_index + 1}/{self.total_profiles}] Getting videos from: {url[:50]}...")
        
        # Update progress dialog
        if hasattr(self, 'profile_download_dialog'):
            progress = int((self.current_profile_index / len(self.pending_profile_urls)) * 100)
            self.profile_download_dialog.progress_bar.setValue(progress)
            self.profile_download_dialog.status_label.setText(f"Processing {self.current_profile_index + 1}/{len(self.pending_profile_urls)} profiles...")
        
        # Start profile info worker
        self.profile_worker = ProfileInfoWorker(self.dl, url)
        self.profile_worker.done.connect(self.handle_multi_profile_result)
        self.profile_worker.start()
    
    def download_next_profile_videos(self):
        """Download videos from the next profile in queue"""
        if self.current_download_profile_index >= len(self.all_profile_data):
            # All done - close progress dialog
            if hasattr(self, 'profile_multi_dialog') and self.profile_multi_dialog:
                self.profile_multi_dialog.close()
            
            self.profile_info_btn.setEnabled(True)
            self.profile_download_btn.setEnabled(True)
            
            # Show modern completion dialog with Open Folder button
            self.show_profile_download_complete_dialog()
            return
        
        profile_data = self.all_profile_data[self.current_download_profile_index]
        profile_name = profile_data['name']
        video_urls = profile_data['videos']
        
        if not video_urls:
            self.current_download_profile_index += 1
            self.download_next_profile_videos()
            return
        
        # Reset current profile counters
        self.current_profile_successful = 0
        self.current_profile_failed = 0
        
        self.profile_progress_text.append(f"\n[F] Downloading {len(video_urls)} videos from: {profile_name}")
        
        # Get settings
        settings = self.get_profile_download_settings()
        download_settings = {
            'quality': settings.get('quality', 'best'),
            'audio': settings.get('audio', False),
            'subtitle': settings.get('subtitle', False),
            'format': settings.get('format', 'Force H.264 (Compatible)'),
            'convert': False,
            'use_caption': True,
            'mute': settings.get('mute', False)
        }
        
        # Set output directory with subfolder for this profile
        base_output = settings.get('output_dir', 'downloads/profiles')
        self.profile_base_output = base_output  # Store for Open Folder button
        if settings.get('create_subfolder', True):
            # Clean profile name for folder
            safe_name = "".join(c for c in profile_name if c.isalnum() or c in (' ', '-', '_')).strip()
            safe_name = safe_name[:50] if len(safe_name) > 50 else safe_name
            output_dir = Path(base_output) / safe_name
        else:
            output_dir = Path(base_output)
        
        self.dl.output_dir = output_dir
        self.dl.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Update progress dialog title for current profile (don't reset progress bar!)
        if hasattr(self, 'profile_multi_dialog') and self.profile_multi_dialog:
            self.profile_multi_dialog.setWindowTitle(f"Downloading: {profile_name} ({self.current_download_profile_index + 1}/{len(self.all_profile_data)} profiles)")
            self.profile_multi_dialog.video_status_label.setText(f"Starting {profile_name}...")
        
        # Start download worker
        self.profile_multi_worker = MultipleDownloadWorker(self.dl, video_urls, download_settings)
        self.profile_multi_worker.progress.connect(lambda msg: self.profile_progress_text.append(msg))
        self.profile_multi_worker.video_started.connect(self.on_profile_video_started)
        self.profile_multi_worker.video_completed.connect(self.on_profile_video_completed)
        self.profile_multi_worker.batch_completed.connect(self.on_single_profile_batch_completed)
        self.profile_multi_worker.start()
    
    def on_profile_video_started(self, index, url):
        """Handle when a profile video download starts"""
        if hasattr(self, 'profile_multi_dialog') and self.profile_multi_dialog:
            # Calculate videos completed so far (from previous profiles + current profile)
            profile_name = self.all_profile_data[self.current_download_profile_index]['name']
            current_profile_video = index + 1
            total_completed = getattr(self, 'profile_videos_completed', 0)
            total_videos = getattr(self, 'total_profile_videos', 1)
            
            self.profile_multi_dialog.video_status_label.setText(
                f"{profile_name}: Video {current_profile_video} | Overall: {total_completed}/{total_videos}"
            )
    
    def on_profile_video_completed(self, index, success, message, file_path):
        """Handle when a profile video download completes"""
        # Increment completed counter
        self.profile_videos_completed = getattr(self, 'profile_videos_completed', 0) + 1
        
        # Track success/fail for current profile
        if success:
            self.current_profile_successful = getattr(self, 'current_profile_successful', 0) + 1
        else:
            self.current_profile_failed = getattr(self, 'current_profile_failed', 0) + 1
        
        if hasattr(self, 'profile_multi_dialog') and self.profile_multi_dialog:
            total_completed = self.profile_videos_completed
            total_videos = getattr(self, 'total_profile_videos', 1)
            
            # Update progress bar
            percentage = int((total_completed / total_videos) * 100) if total_videos > 0 else 0
            self.profile_multi_dialog.progress_bar.setValue(percentage)
            self.profile_multi_dialog.progress_bar.setFormat(f"{total_completed}/{total_videos} videos ({percentage}%)")
    
    def show_profile_download_complete_dialog(self):
        """Show modern completion dialog with Open Folder button"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Download Complete")
        dialog.setFixedSize(400, 200)
        dialog.setStyleSheet("""
            QDialog {
                background: #161b22;
                color: #f0f6fc;
                border: 2px solid #30363d;
                border-radius: 12px;
            }
            QLabel {
                color: #f0f6fc;
                border: none;
                background: transparent;
            }
        """)
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(15)
        layout.setContentsMargins(25, 25, 25, 25)
        
        # Success icon and title
        title_layout = QHBoxLayout()
        icon_label = QLabel("[OK]")
        icon_label.setStyleSheet("font-size: 32px;")
        title_label = QLabel("Profile Download Complete!")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #2ea043;")
        title_layout.addWidget(icon_label)
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        layout.addLayout(title_layout)
        
        # Stats
        stats_label = QLabel(
            f"[G] Results:\n"
            f"   - Profiles: {len(self.all_profile_data)}\n"
            f"   - Successful: {self.total_successful}\n"
            f"   - Failed: {self.total_failed}"
        )
        stats_label.setStyleSheet("font-size: 13px; color: #f0f6fc;")
        layout.addWidget(stats_label)
        
        layout.addStretch()
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        open_folder_btn = QPushButton("Open Folder")
        open_folder_btn.setStyleSheet("""
            QPushButton {
                background: #238636;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #2ea043;
            }
        """)
        open_folder_btn.clicked.connect(lambda: self.open_profile_output_folder(dialog))
        
        close_btn = QPushButton("Close")
        close_btn.setStyleSheet("""
            QPushButton {
                background: #21262d;
                color: #f0f6fc;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                border-color: #58a6ff;
            }
        """)
        close_btn.clicked.connect(dialog.accept)
        
        btn_layout.addStretch()
        btn_layout.addWidget(open_folder_btn)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)
        
        dialog.exec()
        
        self.profile_status_label.setText(f"Completed: {self.total_successful} downloaded, {self.total_failed} failed")
    
    def open_profile_output_folder(self, dialog=None):
        """Open the profile output folder in file explorer"""
        import subprocess
        folder = getattr(self, 'profile_base_output', 'downloads/profiles')
        folder_path = Path(folder)
        if folder_path.exists():
            subprocess.Popen(f'explorer "{folder_path.absolute()}"')
        if dialog:
            dialog.accept()
    
    def on_single_profile_batch_completed(self, stats):
        """Handle when one profile's videos are all downloaded"""
        # DON'T close dialog here - keep it open for all profiles
        
        successful = stats.get('completed', 0)
        failed = stats.get('failed', 0)
        
        self.total_successful += successful
        self.total_failed += failed
        
        profile_data = self.all_profile_data[self.current_download_profile_index]
        self.profile_progress_text.append(f"   [OK] {profile_data['name']}: {successful} downloaded, {failed} failed")
        
        # Move to next profile
        self.current_download_profile_index += 1
        self.download_next_profile_videos()
    
    def on_profile_batch_completed(self, stats):
        """Handle when all profile videos are downloaded (legacy)"""
        if hasattr(self, 'profile_multi_dialog'):
            self.profile_multi_dialog.close()
        
        self.profile_info_btn.setEnabled(True)
        self.profile_download_btn.setEnabled(True)
        
        # Show completion message
        QMessageBox.information(
            self,
            "Profile Download Complete",
            f"[OK] Download completed!\n\n"
            f"Successful: {successful}\n"
            f"Failed: {failed}\n"
            f"Total: {successful + failed}"
        )
        
        self.profile_status_label.setText(f"Completed: {successful} downloaded, {failed} failed")
    
    def handle_multi_profile_result(self, success, data):
        """Handle result from one profile in multi-profile download"""
        # Check if cancelled
        if hasattr(self, 'profile_gathering_cancelled') and self.profile_gathering_cancelled:
            return
            
        if success:
            profile_name = data.get('profile_name', 'Unknown')
            videos = data.get('videos', [])
            
            # Get max videos setting
            settings = self.get_profile_download_settings()
            max_videos = settings.get('max_videos', 50)
            
            # Limit videos per profile
            if max_videos and len(videos) > max_videos:
                videos = videos[:max_videos]
            
            # Extract URLs
            video_urls = [video['url'] for video in videos if video.get('url')]
            
            # Store profile data with name for subfolder creation
            if video_urls:
                self.all_profile_data.append({
                    'name': profile_name,
                    'videos': video_urls
                })
            
            self.profile_videos_text.append(f"   [OK] {profile_name}: {len(video_urls)} videos added")
        else:
            error_msg = data if isinstance(data, str) else "Unknown error"
            self.profile_videos_text.append(f"   [X] Error: {error_msg[:50]}")
        
        # Process next profile
        self.current_profile_index += 1
        self.process_next_profile()
    
    def paste_profile_urls(self):
        """Paste multiple profile URLs from clipboard"""
        clipboard_text = QApplication.clipboard().text()
        if clipboard_text.strip():
            added_count, invalid_count, problematic_count = self.profile_url_list_widget.add_urls_from_text(clipboard_text)
            
            if added_count > 0:
                self.profile_videos_text.append(f"[OK] Added {added_count} profile URL(s)")
            if invalid_count > 0:
                self.profile_videos_text.append(f"[X] Skipped {invalid_count} invalid URL(s)")
            
            self.update_profile_url_status()
        else:
            self.profile_videos_text.append("[!] Clipboard is empty")
    
    def update_profile_url_status(self):
        """Update the profile URL count status"""
        total = len(self.profile_url_list_widget.urls)
        selected = len(self.profile_url_list_widget.get_selected_urls())
        if hasattr(self, 'profile_url_status'):
            self.profile_url_status.setText(f"{selected}/{total} profile URLs selected")
    
    def handle_profile_download_from_tab(self, success, data, progress_dialog):
        """Handle profile download result from profile tab with settings"""
        progress_dialog.close()
        
        if success:
            profile_name = data.get('profile_name', 'Unknown')
            total_videos = data.get('total_found', 0)
            
            if total_videos > 0:
                # Get settings from profile tab
                settings = self.get_profile_download_settings()
                
                # Start profile download with tab settings
                self.start_profile_download_with_settings(data, settings)
            else:
                self.profile_videos_text.clear()
                self.profile_videos_text.append(f"[X] No videos found in profile: {profile_name}")
        else:
            error_msg = data if isinstance(data, str) else "Failed to get profile information"
            self.profile_videos_text.clear()
            self.profile_videos_text.append(f"[X] Failed to get profile info:")
            self.profile_videos_text.append(f"Error: {error_msg}")
    
    def start_profile_download_with_settings(self, profile_data, settings):
        """Start downloading videos from profile with custom settings"""
        videos = profile_data.get('videos', [])
        max_videos = settings['max_videos']
        
        # Apply 3x buffer to account for Facebook's high failure rate
        # The downloader will stop when it reaches the target successful downloads
        if max_videos:
            buffer_count = int(max_videos * 3)
            if len(videos) > buffer_count:
                videos = videos[:buffer_count]
        
        # Extract URLs from video data
        video_urls = [video['url'] for video in videos if video.get('url')]
        
        if not video_urls:
            QMessageBox.warning(self, "No Videos", "No valid video URLs found in this profile.")
            return
        
        profile_name = profile_data.get('profile_name', 'Unknown')
        
        # Set up output directory with profile subfolder if enabled
        base_output = Path(settings['output_dir'])
        if settings['create_subfolder']:
            # Sanitize profile name for folder
            safe_name = "".join(c for c in profile_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
            output_dir = base_output / safe_name
        else:
            output_dir = base_output
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Update downloader output directory
        self.dl.output_dir = output_dir
        
        self.profile_progress_text.clear()
        self.profile_progress_text.append(f"[!] Starting download of up to {max_videos if max_videos else len(video_urls)} videos from: {profile_name}")
        self.profile_progress_text.append(f"   (Prepared {len(video_urls)} URLs to handle potential failures)")
        self.profile_progress_text.append(f"[F] Saving to: {output_dir}")
        self.profile_progress_text.append("")
        
        # Create download settings for the worker - include target_success
        download_settings = {
            'quality': settings['quality'],
            'audio': settings['audio'],
            'subtitle': settings['subtitle'],
            'format': settings['format'],
            'convert': settings['convert'],
            'use_caption': True,
            'target_success': max_videos  # Stop when we reach this many successful downloads
        }
        
        # Create and show progress dialog - show target count, not buffer count
        display_count = max_videos if max_videos else len(video_urls)
        self.profile_multi_progress_dialog = MultipleProgressDialog(self, display_count)
        self.profile_multi_progress_dialog.setWindowTitle("Profile Download Progress")
        self.profile_multi_progress_dialog.show()
        
        # Start multiple download worker for profile
        self.profile_multi_worker = MultipleDownloadWorker(self.dl, video_urls, download_settings)
        self.profile_multi_worker.progress.connect(self.profile_progress_log)
        self.profile_multi_worker.video_started.connect(self.on_profile_video_started)
        self.profile_multi_worker.video_completed.connect(self.on_profile_video_completed)
        self.profile_multi_worker.batch_completed.connect(self.on_profile_batch_completed)
        
        # Connect dialog controls to worker
        self.profile_multi_progress_dialog.pause_btn.clicked.disconnect()
        self.profile_multi_progress_dialog.cancel_btn.clicked.disconnect()
        self.profile_multi_progress_dialog.pause_btn.clicked.connect(self.pause_profile_downloads)
        self.profile_multi_progress_dialog.cancel_btn.clicked.connect(self.stop_profile_downloads)
        
        self.profile_multi_worker.start()
        self.profile_status_label.setText(f"Downloading {len(video_urls)} videos from profile...")
    
    def profile_progress_log(self, message):
        """Add message to profile download log"""
        self.profile_progress_text.append(message)
        self.profile_progress_text.verticalScrollBar().setValue(
            self.profile_progress_text.verticalScrollBar().maximum()
        )
    
    # Note: on_profile_video_started and on_profile_video_completed are defined earlier
    # for the multi-profile download feature
    
    def on_profile_batch_completed(self, summary):
        """Handle when profile batch download is complete"""
        if hasattr(self, 'profile_multi_progress_dialog'):
            self.profile_multi_progress_dialog.close()
        
        completed = summary['completed']
        failed = summary['failed']
        total = summary['total']
        
        # Show completion summary in profile progress
        self.profile_progress_text.append("")
        self.profile_progress_text.append("=" * 50)
        if summary.get('stopped'):
            self.profile_progress_text.append(f"[STOP] Profile download stopped: {completed}/{total} completed, {failed} failed")
            self.profile_status_label.setText(f"Stopped: {completed}/{total} completed")
        else:
            self.profile_progress_text.append(f"[*] Profile download complete: {completed}/{total} successful, {failed} failed")
            self.profile_status_label.setText(f"Complete: {completed}/{total} successful")
        
        # Show modern completion dialog
        dialog = BatchCompleteDialog(self, summary)
        dialog.exec()
    
    def pause_profile_downloads(self):
        """Pause/Resume profile downloads"""
        if hasattr(self, 'profile_multi_worker'):
            if self.profile_multi_worker.paused:
                self.profile_multi_worker.resume()
                self.profile_multi_progress_dialog.pause_btn.setText("Pause")
                self.profile_status_label.setText("Resuming profile downloads...")
            else:
                self.profile_multi_worker.pause()
                self.profile_multi_progress_dialog.pause_btn.setText("Resume")
                self.profile_status_label.setText("Paused")
    
    def stop_profile_downloads(self):
        """Stop profile downloads"""
        if hasattr(self, 'profile_multi_worker') and self.profile_multi_worker:
            self.profile_multi_worker.stopped = True
            self.profile_multi_worker.stop()
            self.profile_status_label.setText("Stopping downloads...")
            self.profile_log("[STOP] Stopping profile downloads...")
            
            # Give it a moment to stop gracefully
            self.profile_multi_worker.wait(500)
            
            # Force terminate if still running
            if self.profile_multi_worker.isRunning():
                self.profile_log("[!] Force stopping download thread...")
                self.profile_multi_worker.terminate()
                self.profile_multi_worker.wait(1000)
            
            self.profile_status_label.setText("Downloads stopped")
            self.profile_log("[STOP] Profile downloads stopped by user")
            
        if hasattr(self, 'profile_multi_progress_dialog') and self.profile_multi_progress_dialog:
            self.profile_multi_progress_dialog.close()
    
    def handle_profile_tab_result(self, success, data, progress_dialog):
        """Handle profile info result from profile tab"""
        progress_dialog.close()
        
        if success:
            profile_name = data.get('profile_name', 'Unknown')
            total_videos = data.get('total_found', 0)
            platform = data.get('platform', 'Unknown')
            
            # Update the profile tab text area with summary
            self.profile_videos_text.clear()
            self.profile_videos_text.append(f"[OK] Profile: {profile_name}")
            self.profile_videos_text.append(f"[M] Platform: {platform}")
            self.profile_videos_text.append(f"[V] Found {total_videos} videos")
            
            if total_videos > 0:
                self.profile_videos_text.append("")
                self.profile_videos_text.append("[*] Click 'Download Videos' to start!")
            
            # Show modern info dialog
            info_dialog = ProfileInfoDialog(self, data)
            info_dialog.exec()
        else:
            error_msg = data if isinstance(data, str) else "Failed to get profile information"
            self.profile_videos_text.clear()
            self.profile_videos_text.append(f"[X] Failed to get profile info:")
            self.profile_videos_text.append(f"Error: {error_msg}")
            self.profile_videos_text.append("")
            self.profile_videos_text.append("[*] Tips:")
            self.profile_videos_text.append("- Make sure the profile is public")
            self.profile_videos_text.append("- Check if the URL is correct")
            self.profile_videos_text.append("- Try copying the URL again")
    
    def handle_profile_download_result(self, success, data, progress_dialog):
        """Handle profile download result from profile tab"""
        progress_dialog.close()
        
        if success:
            profile_name = data.get('profile_name', 'Unknown')
            total_videos = data.get('total_found', 0)
            
            if total_videos > 0:
                # Show profile download dialog
                profile_dialog = ProfileDownloadDialog(self, data)
                if profile_dialog.exec() == QDialog.DialogCode.Accepted:
                    settings = profile_dialog.get_download_settings()
                    self.start_profile_download(data, settings)
                else:
                    self.profile_videos_text.append("[STOP] Download cancelled by user")
            else:
                self.profile_videos_text.clear()
                self.profile_videos_text.append(f"[X] No videos found in profile: {profile_name}")
        else:
            error_msg = data if isinstance(data, str) else "Failed to get profile information"
            self.profile_videos_text.clear()
            self.profile_videos_text.append(f"[X] Failed to get profile info:")
            self.profile_videos_text.append(f"Error: {error_msg}")
    
    def start_multiple_download_with_urls(self, urls, target_success=None):
        """Start multiple downloads with a provided list of URLs
        
        Args:
            urls: List of URLs to download
            target_success: Optional target number of successful downloads. 
                           If set, will stop after reaching this many successes.
        """
        if not urls:
            return
        
        # Set up download settings (use current settings from UI)
        settings = {
            'quality': self.multi_quality.currentText(),
            'audio': self.multi_audio_cb.isChecked(),
            'subtitle': self.multi_subtitle_cb.isChecked(),
            'format': self.multi_format.currentText(),
            'convert': False,
            'use_caption': True,
            'target_success': target_success  # Pass target to worker
        }
        
        # Set output directory
        self.dl.output_dir = Path(self.multi_output.text() or "downloads")
        self.dl.output_dir.mkdir(exist_ok=True)
        
        # Create and show progress dialog - show target if set, otherwise total URLs
        display_count = target_success if target_success else len(urls)
        self.multi_progress_dialog = MultipleProgressDialog(self, display_count)
        self.multi_progress_dialog.show()
        
        # Start multiple download worker
        self.multi_worker = MultipleDownloadWorker(self.dl, urls, settings)
        self.multi_worker.progress.connect(self.multi_log)
        self.multi_worker.video_started.connect(self.on_multi_video_started)
        self.multi_worker.video_completed.connect(self.on_multi_video_completed)
        self.multi_worker.batch_completed.connect(self.on_multi_batch_completed)
        
        # Connect dialog controls to worker
        self.multi_progress_dialog.pause_btn.clicked.disconnect()  # Remove old connections
        self.multi_progress_dialog.cancel_btn.clicked.disconnect()
        self.multi_progress_dialog.pause_btn.clicked.connect(self.pause_multiple_downloads)
        self.multi_progress_dialog.cancel_btn.clicked.connect(self.stop_multiple_downloads)
        
        self.multi_worker.start()
        status_msg = f"Downloading up to {target_success} videos..." if target_success else f"Downloading {len(urls)} videos..."
        self.update_multi_status(status_msg)
        
        # Update UI state
        self.multi_download_btn.setEnabled(False)
        self.multi_pause_btn.setEnabled(True)
        self.multi_stop_btn.setEnabled(True)
    
    def browse_profile_output(self):
        """Browse for profile output directory"""
        folder = QFileDialog.getExistingDirectory(self, "Select Profile Download Directory")
        if folder:
            self.profile_output.setText(folder)
    
    # === VIDEO EDIT METHODS ===
    
    def browse_edit_input_folder(self):
        """Browse for input folder containing videos"""
        folder = QFileDialog.getExistingDirectory(self, "Select Input Folder")
        if folder:
            self.edit_input_folder.setText(folder)
            self.update_edit_video_count()
    
    def browse_edit_input_file(self):
        """Browse for a single video file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Video File", "",
            "Video Files (*.mp4 *.avi *.mkv *.mov *.wmv *.flv *.webm *.m4v *.mpeg *.mpg);;All Files (*)"
        )
        if file_path:
            self.edit_input_folder.setText(file_path)
            self.update_edit_video_count()
    
    def browse_edit_output(self):
        """Browse for output folder"""
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder:
            self.edit_output_folder.setText(folder)
    
    def update_edit_video_count(self):
        """Update the video count label"""
        input_path = self.edit_input_folder.text().strip()
        if not input_path:
            self.edit_video_count.setText("No input selected")
            return
            
        path = Path(input_path)
        if not path.exists():
            self.edit_video_count.setText("Path does not exist")
            return
            
        video_extensions = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.mpeg', '.mpg'}
        
        if path.is_file():
            # Single file selected
            if path.suffix.lower() in video_extensions:
                self.edit_video_count.setText(f"1 video selected: {path.name}")
            else:
                self.edit_video_count.setText("Selected file is not a video")
        elif path.is_dir():
            # Folder selected
            videos = [f for f in path.iterdir() if f.suffix.lower() in video_extensions]
            self.edit_video_count.setText(f"Found {len(videos)} video(s) in folder")
        else:
            self.edit_video_count.setText("Invalid path")
    
    def show_edit_settings_dialog(self):
        """Show video edit settings dialog"""
        dialog = VideoEditSettingsDialog(self, self._edit_settings)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._edit_settings = dialog.get_settings()
            # Save settings to persist
            self.save_settings(silent=True)
            # Update settings label
            self.update_edit_settings_label()
    
    def update_edit_settings_label(self):
        """Update the edit settings summary label"""
        if not hasattr(self, 'edit_settings_label') or not hasattr(self, '_edit_settings'):
            return
        settings_summary = []
        if self._edit_settings.get('resolution', 'Original') != 'Original':
            settings_summary.append(self._edit_settings['resolution'].split()[0])
        if self._edit_settings.get('enable_logo', False):
            settings_summary.append("Logo")
        if self._edit_settings.get('enable_trim', False):
            settings_summary.append("Trim")
        if self._edit_settings.get('mute_audio', False):
            settings_summary.append("Muted")
        if self._edit_settings.get('speed', 1.0) != 1.0:
            settings_summary.append(f"{self._edit_settings['speed']}x")
        if self._edit_settings.get('output_format', 'MP4 (H.264)') != 'MP4 (H.264)':
            settings_summary.append(self._edit_settings['output_format'].split()[0])
        
        if settings_summary:
            self.edit_settings_label.setText(", ".join(settings_summary))
        else:
            self.edit_settings_label.setText("Default settings")
    
    def edit_log(self, message):
        """Add message to edit log"""
        self.edit_log_text.append(message)
        self.edit_log_text.verticalScrollBar().setValue(
            self.edit_log_text.verticalScrollBar().maximum()
        )
        QApplication.processEvents()
    
    def stop_video_editing(self):
        """Stop video editing process"""
        self._edit_stopped = True
        self.edit_status_label.setText("Stopping...")
        # Don't disable stop button yet - let the process finish stopping

    def show_ffmpeg_required_dialog(self):
        """Show FFmpeg required dialog with download options"""
        dialog = QDialog(self)
        dialog.setWindowTitle("FFmpeg Required")
        dialog.setFixedSize(520, 400)
        dialog.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #1a1f2e, stop:1 #0d1117);
                color: #e6edf3;
            }
            QLabel { color: #e6edf3; background: transparent; }
            QPushButton {
                background: #238636;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: bold;
            }
            QPushButton:hover { background: #2ea043; }
            QPushButton#cancel {
                background: transparent;
                border: 1px solid #444c56;
                color: #8b949e;
            }
            QPushButton#cancel:hover { border-color: #58a6ff; color: #e6edf3; }
        """)
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(12)
        layout.setContentsMargins(25, 25, 25, 25)
        
        # Header with icon
        header = QLabel("⚠️ FFmpeg Required")
        header.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)
        
        # Description
        desc = QLabel(
            "FFmpeg is a free tool needed for video editing.\n"
            "Follow these simple steps to install it:"
        )
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setStyleSheet("color: #8b949e; font-size: 12px;")
        layout.addWidget(desc)
        
        # Instructions - clearer steps
        instructions = QLabel(
            "Step 1: Click 'Download FFmpeg' button below\n\n"
            "Step 2: Click the green 'ffmpeg-release-essentials.zip' link\n\n"
            "Step 3: Extract the zip file to C:\\ffmpeg\n\n"
            "Step 4: Add FFmpeg to Windows PATH:\n"
            "   • Press Win+R, type 'sysdm.cpl' and press Enter\n"
            "   • Click 'Advanced' tab → 'Environment Variables'\n"
            "   • Under 'System variables', find 'Path' and click 'Edit'\n"
            "   • Click 'New' and add: C:\\ffmpeg\\bin\n"
            "   • Click OK on all windows\n\n"
            "Step 5: Restart VIDT"
        )
        instructions.setStyleSheet("""
            background: rgba(45,51,59,0.5);
            border: 1px solid #30363d;
            border-radius: 8px;
            padding: 12px;
            color: #8b949e;
            font-size: 11px;
        """)
        layout.addWidget(instructions)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("cancel")
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(cancel_btn)
        
        # Auto install button
        auto_btn = QPushButton("Auto Install FFmpeg")
        auto_btn.setStyleSheet("background: #58a6ff;")
        auto_btn.clicked.connect(lambda: (dialog.accept(), self.auto_install_ffmpeg()))
        btn_layout.addWidget(auto_btn)
        
        # Manual download button
        download_btn = QPushButton("Manual Download")
        download_btn.setObjectName("cancel")
        download_btn.clicked.connect(lambda: (
            QDesktopServices.openUrl(QUrl("https://www.gyan.dev/ffmpeg/builds/")),
            dialog.accept()
        ))
        btn_layout.addWidget(download_btn)
        
        layout.addLayout(btn_layout)
        
        dialog.exec()
    
    def auto_install_ffmpeg(self):
        """Automatically download and install FFmpeg"""
        import zipfile
        import shutil
        import os
        import requests
        
        # Create progress dialog
        progress = QProgressDialog("Connecting...", "Cancel", 0, 100, self)
        progress.setWindowTitle("Installing FFmpeg")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.setAutoClose(False)
        progress.setAutoReset(False)
        progress.setValue(0)
        progress.show()
        QApplication.processEvents()
        
        try:
            # FFmpeg download URL (essentials build - smaller ~80MB)
            url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
            
            # Download location
            app_dir = Path(os.environ.get('LOCALAPPDATA', os.path.expanduser('~'))) / 'VIDT'
            app_dir.mkdir(parents=True, exist_ok=True)
            zip_path = app_dir / 'ffmpeg.zip'
            ffmpeg_dir = app_dir / 'ffmpeg'
            
            progress.setLabelText("Connecting to server...")
            QApplication.processEvents()
            
            # Download with progress
            response = requests.get(url, stream=True, timeout=30)
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            progress.setLabelText(f"Downloading FFmpeg ({total_size // 1024 // 1024}MB)...")
            QApplication.processEvents()
            
            with open(zip_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=65536):  # 64KB chunks
                    if progress.wasCanceled():
                        zip_path.unlink(missing_ok=True)
                        return
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        percent = int((downloaded / total_size) * 60)  # 0-60% for download
                        progress.setValue(percent)
                        mb_done = downloaded // 1024 // 1024
                        mb_total = total_size // 1024 // 1024
                        progress.setLabelText(f"Downloading... {mb_done}MB / {mb_total}MB")
                    QApplication.processEvents()
            
            if progress.wasCanceled():
                zip_path.unlink(missing_ok=True)
                return
            
            progress.setLabelText("Extracting files...")
            progress.setValue(65)
            QApplication.processEvents()
            
            # Extract
            if ffmpeg_dir.exists():
                shutil.rmtree(ffmpeg_dir)
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # Get the root folder name in zip
                root_folder = zip_ref.namelist()[0].split('/')[0]
                zip_ref.extractall(app_dir)
                
                # Rename to ffmpeg
                extracted_dir = app_dir / root_folder
                if extracted_dir.exists():
                    extracted_dir.rename(ffmpeg_dir)
            
            progress.setValue(80)
            QApplication.processEvents()
            
            # Clean up zip
            zip_path.unlink()
            
            progress.setLabelText("Adding to system PATH...")
            progress.setValue(85)
            QApplication.processEvents()
            
            # Add to user PATH
            bin_path = str(ffmpeg_dir / 'bin')
            
            # Update user PATH via registry
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Environment', 0, winreg.KEY_ALL_ACCESS)
            try:
                current_path, _ = winreg.QueryValueEx(key, 'Path')
            except WindowsError:
                current_path = ''
            
            if bin_path.lower() not in current_path.lower():
                new_path = f"{current_path};{bin_path}" if current_path else bin_path
                winreg.SetValueEx(key, 'Path', 0, winreg.REG_EXPAND_SZ, new_path)
            
            winreg.CloseKey(key)
            
            # Notify system of environment change
            import ctypes
            HWND_BROADCAST = 0xFFFF
            WM_SETTINGCHANGE = 0x1A
            ctypes.windll.user32.SendMessageW(HWND_BROADCAST, WM_SETTINGCHANGE, 0, "Environment")
            
            # Update current process PATH
            os.environ['PATH'] = bin_path + ';' + os.environ.get('PATH', '')
            
            progress.setValue(100)
            progress.setLabelText("Complete!")
            QApplication.processEvents()
            
            progress.close()
            
            QMessageBox.information(self, "Success", 
                "FFmpeg installed successfully!\n\n"
                "You can now use video editing features.\n"
                "Please restart VIDT for best results.")
                
        except requests.exceptions.Timeout:
            progress.close()
            QMessageBox.warning(self, "Error", 
                "Connection timed out.\n\n"
                "Please check your internet connection and try again.")
        except Exception as e:
            progress.close()
            QMessageBox.warning(self, "Error", 
                f"Failed to install FFmpeg:\n{str(e)}\n\n"
                "Please try manual installation.")
    
    def start_video_editing(self):
        """Start batch video editing"""
        input_path = self.edit_input_folder.text().strip()
        output_folder = self.edit_output_folder.text().strip()
        
        if not input_path or not Path(input_path).exists():
            QMessageBox.warning(self, "Error", "Please select a valid input file or folder")
            return
        
        if not output_folder:
            QMessageBox.warning(self, "Error", "Please select an output folder")
            return
        
        # Create output folder
        Path(output_folder).mkdir(parents=True, exist_ok=True)
        
        # Get video files - handle both single file and folder
        video_extensions = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.mpeg', '.mpg'}
        input_path_obj = Path(input_path)
        
        if input_path_obj.is_file():
            # Single file
            if input_path_obj.suffix.lower() in video_extensions:
                videos = [input_path_obj]
            else:
                QMessageBox.warning(self, "Error", "Selected file is not a supported video format")
                return
        else:
            # Folder
            videos = [f for f in input_path_obj.iterdir() if f.suffix.lower() in video_extensions]
        
        if not videos:
            QMessageBox.warning(self, "Error", "No video files found")
            return
        
        # Check FFmpeg
        try:
            import subprocess
            subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            # Show dialog with download option
            self.show_ffmpeg_required_dialog()
            return
        
        # Reset UI
        self._edit_stopped = False
        self.edit_log_text.clear()
        self.edit_progress_bar.setMaximum(len(videos))
        self.edit_progress_bar.setValue(0)
        self.start_edit_btn.setEnabled(False)
        self.stop_edit_btn.setEnabled(True)
        
        self.edit_log(f"Starting edit of {len(videos)} video(s)...")
        self.edit_log(f"Input: {input_path}")
        self.edit_log(f"Output: {output_folder}")
        self.edit_log("")
        
        successful = 0
        failed = 0
        
        for i, video_path in enumerate(videos, 1):
            if self._edit_stopped:
                self.edit_log("\nStopped by user")
                break
            
            self.edit_status_label.setText(f"Processing {i}/{len(videos)}...")
            self.edit_progress_bar.setValue(i)
            QApplication.processEvents()
            
            self.edit_log(f"[{i}/{len(videos)}] {video_path.name}")
            
            try:
                result = self.process_video(video_path, output_folder)
                if self._edit_stopped:
                    # Don't count stopped as failed
                    self.edit_log(f"   [!] Stopped")
                    break
                elif result['success']:
                    successful += 1
                    self.edit_log(f"   [OK] Saved: {result['output_name']}")
                else:
                    failed += 1
                    self.edit_log(f"   [X] Error: {result['error']}")
            except Exception as e:
                if not self._edit_stopped:
                    failed += 1
                    self.edit_log(f"   [X] Error: {str(e)}")
        
        # Complete
        self.edit_log("")
        if self._edit_stopped:
            self.edit_log(f"Stopped: {successful} successful, {failed} failed")
            self.edit_status_label.setText("Stopped")
        else:
            self.edit_log(f"Complete: {successful} successful, {failed} failed")
            self.edit_status_label.setText("Complete")
        
        self.start_edit_btn.setEnabled(True)
        self.stop_edit_btn.setEnabled(False)
        
        # Show modern completion dialog
        dialog = VideoEditCompleteDialog(self, successful, failed, output_folder, stopped=self._edit_stopped)
        dialog.exec()
        
        # Reset stopped flag after dialog closes
        self._edit_stopped = False
    
    def process_video(self, video_path, output_folder):
        """Process a single video with FFmpeg"""
        import subprocess
        
        settings = self._edit_settings
        
        # Determine output folder based on settings
        if settings.get('same_folder', False):
            output_path = video_path.parent
        else:
            output_path = Path(output_folder)
        
        # Determine output extension
        format_map = {
            'MP4 (H.264)': '.mp4',
            'MP4 (H.265/HEVC)': '.mp4',
            'WebM': '.webm',
            'AVI': '.avi',
            'MOV': '.mov',
            'MKV': '.mkv'
        }
        ext = format_map.get(settings['output_format'], '.mp4')
        
        # Determine output filename based on settings
        if settings.get('replace_original', False):
            # Use temp file, then replace original
            output_name = video_path.stem + "_temp_edit" + ext
            output_file = output_path / output_name
            replace_original = True
        elif settings.get('add_suffix', True):
            output_name = video_path.stem + "_edited" + ext
            output_file = output_path / output_name
            replace_original = False
        else:
            output_name = video_path.stem + ext
            output_file = output_path / output_name
            replace_original = False
        
        # Build FFmpeg command
        cmd = ['ffmpeg', '-y', '-i', str(video_path)]
        
        # Build filter complex
        filters = []
        
        # Resolution
        if settings['resolution'] != 'Original':
            res_map = {
                '4K (3840x2160)': '3840:2160',
                '2K (2560x1440)': '2560:1440',
                '1080p (1920x1080)': '1920:1080',
                '720p (1280x720)': '1280:720',
                '480p (854x480)': '854:480',
                'Custom': f"{settings['custom_width']}:{settings['custom_height']}"
            }
            scale = res_map.get(settings['resolution'])
            if scale:
                filters.append(f"scale={scale}:force_original_aspect_ratio=decrease,pad={scale.split(':')[0]}:{scale.split(':')[1]}:(ow-iw)/2:(oh-ih)/2")
        
        # Speed
        if settings['speed'] != 1.0:
            filters.append(f"setpts={1/settings['speed']}*PTS")
        
        # Apply video filters
        if filters:
            cmd.extend(['-vf', ','.join(filters)])
        
        # Audio filters
        audio_filters = []
        if settings['speed'] != 1.0:
            audio_filters.append(f"atempo={settings['speed']}")
        if settings['volume'] != 100:
            audio_filters.append(f"volume={settings['volume']/100}")
        
        if settings['mute_audio']:
            cmd.extend(['-an'])
        elif audio_filters:
            cmd.extend(['-af', ','.join(audio_filters)])
        else:
            # Copy audio codec if no audio filters
            cmd.extend(['-c:a', 'copy'])
        
        # Trim
        if settings['enable_trim']:
            if settings['trim_start'] > 0:
                cmd.extend(['-ss', str(settings['trim_start'])])
            if settings['trim_end'] > 0:
                cmd.extend(['-to', str(settings['trim_end'])])
        
        # Codec settings
        if 'H.264' in settings['output_format']:
            cmd.extend(['-c:v', 'libx264', '-crf', str(settings['quality_crf'])])
        elif 'H.265' in settings['output_format']:
            cmd.extend(['-c:v', 'libx265', '-crf', str(settings['quality_crf'])])
        elif 'WebM' in settings['output_format']:
            cmd.extend(['-c:v', 'libvpx-vp9', '-crf', str(settings['quality_crf']), '-b:v', '0'])
        
        # Add logo/watermark
        if settings['enable_logo']:
            watermark_type = settings.get('watermark_type', 'Image')
            pos_map = {
                'Top-Left': '10:10',
                'Top-Right': 'W-w-10:10',
                'Bottom-Left': '10:H-h-10',
                'Bottom-Right': 'W-w-10:H-h-10',
                'Center': '(W-w)/2:(H-h)/2'
            }
            pos = pos_map.get(settings['logo_position'], 'W-w-10:H-h-10')
            opacity = settings['logo_opacity'] / 100
            
            if watermark_type == 'Text' and settings.get('watermark_text'):
                # Text watermark using drawtext filter
                text = settings['watermark_text'].replace("'", "\\'").replace(":", "\\:")
                font_size = settings.get('text_font_size', 48)
                text_color = settings.get('text_color', '#FFFFFF').lstrip('#')
                
                # Get animation settings
                animation = settings.get('watermark_animation', 'None')
                anim_duration = settings.get('animation_duration', 1.0)
                
                # Convert hex color to FFmpeg format with opacity
                alpha_hex = hex(int(opacity * 255))[2:].zfill(2)
                fontcolor = f"{text_color}@{opacity}"
                
                # Position mapping for drawtext (different from overlay)
                text_pos_map = {
                    'Top-Left': 'x=10:y=10',
                    'Top-Right': 'x=w-tw-10:y=10',
                    'Bottom-Left': 'x=10:y=h-th-10',
                    'Bottom-Right': 'x=w-tw-10:y=h-th-10',
                    'Center': 'x=(w-tw)/2:y=(h-th)/2'
                }
                base_pos = text_pos_map.get(settings['logo_position'], 'x=w-tw-10:y=h-th-10')
                
                # Build drawtext filter with animation
                if animation == 'Fade In':
                    # Fade in from transparent to full opacity
                    alpha_expr = f"if(lt(t,{anim_duration}),{opacity}*t/{anim_duration},{opacity})"
                    text_filter = f"drawtext=text='{text}':fontsize={font_size}:fontcolor={text_color}@%{{eif\\:{alpha_expr}\\:d}}:{base_pos}"
                elif animation == 'Fade In/Out':
                    # Fade in at start, fade out at end (last 2 seconds)
                    alpha_expr = f"if(lt(t,{anim_duration}),{opacity}*t/{anim_duration},if(gt(t,duration-{anim_duration}),{opacity}*(duration-t)/{anim_duration},{opacity}))"
                    text_filter = f"drawtext=text='{text}':fontsize={font_size}:fontcolor={text_color}:{base_pos}:alpha='{alpha_expr}'"
                elif animation == 'Slide In Left':
                    x_expr = f"if(lt(t,{anim_duration}),-tw+((w-tw-10+tw)*t/{anim_duration}),w-tw-10)" if 'Right' in settings['logo_position'] else f"if(lt(t,{anim_duration}),-tw+(10+tw)*t/{anim_duration},10)"
                    y_part = base_pos.split(':')[1] if ':' in base_pos else 'y=10'
                    text_filter = f"drawtext=text='{text}':fontsize={font_size}:fontcolor={fontcolor}:x='{x_expr}':{y_part}"
                elif animation == 'Slide In Right':
                    x_expr = f"if(lt(t,{anim_duration}),w-((w-10)*t/{anim_duration}),10)" if 'Left' in settings['logo_position'] else f"if(lt(t,{anim_duration}),w-((10+tw)*t/{anim_duration}),w-tw-10)"
                    y_part = base_pos.split(':')[1] if ':' in base_pos else 'y=10'
                    text_filter = f"drawtext=text='{text}':fontsize={font_size}:fontcolor={fontcolor}:x='{x_expr}':{y_part}"
                elif animation == 'Slide In Top':
                    x_part = base_pos.split(':')[0] if ':' in base_pos else 'x=10'
                    y_target = '10' if 'Top' in settings['logo_position'] else 'h-th-10'
                    y_expr = f"if(lt(t,{anim_duration}),-th+({y_target}+th)*t/{anim_duration},{y_target})"
                    text_filter = f"drawtext=text='{text}':fontsize={font_size}:fontcolor={fontcolor}:{x_part}:y='{y_expr}'"
                elif animation == 'Slide In Bottom':
                    x_part = base_pos.split(':')[0] if ':' in base_pos else 'x=10'
                    y_target = '10' if 'Top' in settings['logo_position'] else 'h-th-10'
                    y_expr = f"if(lt(t,{anim_duration}),h-(h-{y_target})*t/{anim_duration},{y_target})"
                    text_filter = f"drawtext=text='{text}':fontsize={font_size}:fontcolor={fontcolor}:{x_part}:y='{y_expr}'"
                elif animation == 'Zoom In':
                    # Zoom from small to full size
                    size_expr = f"if(lt(t,{anim_duration}),{font_size}*t/{anim_duration},{font_size})"
                    text_filter = f"drawtext=text='{text}':fontsize='{size_expr}':fontcolor={fontcolor}:{base_pos}"
                elif animation == 'Pulse':
                    # Pulsing opacity effect
                    alpha_expr = f"{opacity}*(0.5+0.5*sin(t*3.14159))"
                    text_filter = f"drawtext=text='{text}':fontsize={font_size}:fontcolor={text_color}:{base_pos}:alpha='{alpha_expr}'"
                else:
                    # No animation
                    text_filter = f"drawtext=text='{text}':fontsize={font_size}:fontcolor={fontcolor}:{base_pos}"
                
                if filters:
                    filters.append(text_filter)
                else:
                    filters = [text_filter]
                
                # Apply all filters
                if filters:
                    cmd.extend(['-vf', ','.join(filters)])
                    
            elif watermark_type == 'Image' and settings.get('logo_path') and Path(settings['logo_path']).exists():
                # Image watermark
                scale_pct = settings['logo_scale'] / 100
                logo_shape = settings.get('logo_shape', 'None')
                animation = settings.get('watermark_animation', 'None')
                anim_duration = settings.get('animation_duration', 1.0)
                logo_path = settings['logo_path']
                
                # Check if logo is an animated GIF
                is_animated_gif = logo_path.lower().endswith('.gif')
                
                # Rebuild command with logo
                # For animated GIFs: use -stream_loop -1 to loop infinitely before the input
                if is_animated_gif:
                    # -stream_loop -1 must come before -i for the file to loop
                    cmd = ['ffmpeg', '-y', '-i', str(video_path), '-ignore_loop', '0', '-stream_loop', '-1', '-i', logo_path]
                else:
                    cmd = ['ffmpeg', '-y', '-i', str(video_path), '-i', logo_path]
                
                # Build base logo processing (scale and shape)
                if logo_shape == 'Circle':
                    logo_base = f"[1:v]scale=iw*{scale_pct}:-1,format=rgba,geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='if(gt(pow(X-W/2,2)+pow(Y-H/2,2),pow(min(W,H)/2,2)),0,alpha(X,Y))'"
                elif logo_shape == 'Rounded':
                    logo_base = f"[1:v]scale=iw*{scale_pct}:-1,format=rgba,geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='if(gt(pow(max(0,abs(X-W/2)-W/2+min(W,H)*0.15),2)+pow(max(0,abs(Y-H/2)-H/2+min(W,H)*0.15),2),pow(min(W,H)*0.15,2)),0,alpha(X,Y))'"
                elif logo_shape == 'Square':
                    logo_base = f"[1:v]scale=iw*{scale_pct}:-1,crop='min(iw,ih)':'min(iw,ih)',format=rgba"
                elif logo_shape == 'Triangle':
                    logo_base = f"[1:v]scale=iw*{scale_pct}:-1,format=rgba,geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='if(lt(Y,H*(1-abs(X-W/2)/(W/2))),alpha(X,Y),0)'"
                else:
                    logo_base = f"[1:v]scale=iw*{scale_pct}:-1,format=rgba"
                
                # For animated GIFs, use shortest=1 to end when main video ends
                overlay_opts = ":shortest=1" if is_animated_gif else ""
                
                # Build overlay position with animation
                if animation == 'Fade In':
                    alpha_expr = f"if(lt(t,{anim_duration}),{opacity}*t/{anim_duration},{opacity})"
                    logo_filter = f"{logo_base},colorchannelmixer=aa={opacity}[logo];[0:v][logo]overlay={pos}:format=auto:alpha=premultiplied:enable='gte(t,0)'"
                    # Use fade filter for smoother fade
                    logo_filter = f"{logo_base}[logotmp];[logotmp]fade=t=in:st=0:d={anim_duration}:alpha=1,colorchannelmixer=aa={opacity}[logo];[0:v][logo]overlay={pos}{overlay_opts}"
                elif animation == 'Fade In/Out':
                    logo_filter = f"{logo_base}[logotmp];[logotmp]fade=t=in:st=0:d={anim_duration}:alpha=1,fade=t=out:st=9999:d={anim_duration}:alpha=1,colorchannelmixer=aa={opacity}[logo];[0:v][logo]overlay={pos}{overlay_opts}"
                elif animation == 'Slide In Left':
                    # Slide from left edge
                    if 'Right' in settings['logo_position']:
                        x_expr = f"if(lt(t,{anim_duration}),-overlay_w+(W-overlay_w-10+overlay_w)*t/{anim_duration},W-overlay_w-10)"
                    else:
                        x_expr = f"if(lt(t,{anim_duration}),-overlay_w+(10+overlay_w)*t/{anim_duration},10)"
                    y_val = '10' if 'Top' in settings['logo_position'] else ('(H-overlay_h)/2' if 'Center' in settings['logo_position'] else 'H-overlay_h-10')
                    logo_filter = f"{logo_base},colorchannelmixer=aa={opacity}[logo];[0:v][logo]overlay=x='{x_expr}':y={y_val}{overlay_opts}"
                elif animation == 'Slide In Right':
                    # Slide from right edge
                    if 'Left' in settings['logo_position']:
                        x_expr = f"if(lt(t,{anim_duration}),W-(W-10)*t/{anim_duration},10)"
                    else:
                        x_expr = f"if(lt(t,{anim_duration}),W-(W-W+overlay_w+10)*t/{anim_duration},W-overlay_w-10)"
                    y_val = '10' if 'Top' in settings['logo_position'] else ('(H-overlay_h)/2' if 'Center' in settings['logo_position'] else 'H-overlay_h-10')
                    logo_filter = f"{logo_base},colorchannelmixer=aa={opacity}[logo];[0:v][logo]overlay=x='{x_expr}':y={y_val}{overlay_opts}"
                elif animation == 'Slide In Top':
                    # Slide from top
                    x_val = '10' if 'Left' in settings['logo_position'] else ('(W-overlay_w)/2' if 'Center' in settings['logo_position'] else 'W-overlay_w-10')
                    if 'Bottom' in settings['logo_position']:
                        y_expr = f"if(lt(t,{anim_duration}),-overlay_h+(H-overlay_h-10+overlay_h)*t/{anim_duration},H-overlay_h-10)"
                    else:
                        y_expr = f"if(lt(t,{anim_duration}),-overlay_h+(10+overlay_h)*t/{anim_duration},10)"
                    logo_filter = f"{logo_base},colorchannelmixer=aa={opacity}[logo];[0:v][logo]overlay=x={x_val}:y='{y_expr}'{overlay_opts}"
                elif animation == 'Slide In Bottom':
                    # Slide from bottom
                    x_val = '10' if 'Left' in settings['logo_position'] else ('(W-overlay_w)/2' if 'Center' in settings['logo_position'] else 'W-overlay_w-10')
                    if 'Top' in settings['logo_position']:
                        y_expr = f"if(lt(t,{anim_duration}),H-(H-10)*t/{anim_duration},10)"
                    else:
                        y_expr = f"if(lt(t,{anim_duration}),H-(H-H+overlay_h+10)*t/{anim_duration},H-overlay_h-10)"
                    logo_filter = f"{logo_base},colorchannelmixer=aa={opacity}[logo];[0:v][logo]overlay=x={x_val}:y='{y_expr}'{overlay_opts}"
                elif animation == 'Zoom In':
                    # Zoom from small to full size
                    scale_expr = f"if(lt(t,{anim_duration}),iw*{scale_pct}*t/{anim_duration},iw*{scale_pct})"
                    logo_filter = f"[1:v]scale=w='{scale_expr}':h=-1,format=rgba,colorchannelmixer=aa={opacity}[logo];[0:v][logo]overlay={pos}{overlay_opts}"
                elif animation == 'Pulse':
                    # Pulsing effect using opacity
                    pulse_opacity = f"{opacity}*(0.6+0.4*sin(t*3.14159*2))"
                    logo_filter = f"{logo_base}[logotmp];[logotmp]colorchannelmixer=aa='{pulse_opacity}'[logo];[0:v][logo]overlay={pos}{overlay_opts}"
                else:
                    # No animation
                    logo_filter = f"{logo_base},colorchannelmixer=aa={opacity}[logo];[0:v][logo]overlay={pos}{overlay_opts}"
                
                if filters:
                    cmd.extend(['-filter_complex', f"{logo_filter},{','.join(filters)}"])
                else:
                    cmd.extend(['-filter_complex', logo_filter])
                
                # Re-add audio settings for image watermark path
                if settings['mute_audio']:
                    cmd.extend(['-an'])
                elif audio_filters:
                    cmd.extend(['-af', ','.join(audio_filters)])
                else:
                    cmd.extend(['-c:a', 'copy'])
                
                # Re-add codec settings
                if 'H.264' in settings['output_format']:
                    cmd.extend(['-c:v', 'libx264', '-crf', str(settings['quality_crf'])])
                elif 'H.265' in settings['output_format']:
                    cmd.extend(['-c:v', 'libx265', '-crf', str(settings['quality_crf'])])
                elif 'WebM' in settings['output_format']:
                    cmd.extend(['-c:v', 'libvpx-vp9', '-crf', str(settings['quality_crf']), '-b:v', '0'])
        
        # Copy all subtitle streams and metadata
        cmd.extend(['-c:s', 'copy'])  # Copy subtitle streams
        cmd.extend(['-map_metadata', '0'])  # Copy metadata from input
        
        cmd.append(str(output_file))
        
        # Run FFmpeg with Popen for interruptible processing
        try:
            import time
            import os
            
            # On Windows, use CREATE_NEW_PROCESS_GROUP for better termination
            creation_flags = 0
            if hasattr(subprocess, 'CREATE_NO_WINDOW'):
                creation_flags |= subprocess.CREATE_NO_WINDOW
            if hasattr(subprocess, 'CREATE_NEW_PROCESS_GROUP'):
                creation_flags |= subprocess.CREATE_NEW_PROCESS_GROUP
            
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                creationflags=creation_flags
            )
            
            # Store process reference for stopping
            self._current_ffmpeg_process = process
            
            # Read stderr in non-blocking way to show progress
            import threading
            import queue
            
            stderr_queue = queue.Queue()
            last_progress = ""
            
            def read_stderr():
                try:
                    for line in iter(process.stderr.readline, b''):
                        if line:
                            stderr_queue.put(line.decode('utf-8', errors='replace'))
                except:
                    pass
            
            stderr_thread = threading.Thread(target=read_stderr, daemon=True)
            stderr_thread.start()
            
            # Poll process and check for stop flag
            while process.poll() is None:
                if self._edit_stopped:
                    # Force kill on Windows
                    try:
                        if os.name == 'nt':
                            # Windows: use taskkill for reliable termination
                            subprocess.run(['taskkill', '/F', '/T', '/PID', str(process.pid)], 
                                         capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
                        else:
                            process.terminate()
                            process.wait(timeout=2)
                    except:
                        try:
                            process.kill()
                        except:
                            pass
                    
                    # Clean up partial output file
                    if output_file.exists():
                        try:
                            time.sleep(0.5)  # Wait for file handle release
                            os.remove(str(output_file))
                        except:
                            pass
                    self._current_ffmpeg_process = None
                    return {'success': False, 'error': 'Stopped by user'}
                
                # Check for progress updates from FFmpeg
                try:
                    while True:
                        line = stderr_queue.get_nowait()
                        if 'time=' in line:
                            # Extract time progress
                            import re
                            match = re.search(r'time=(\d+:\d+:\d+\.\d+)', line)
                            if match:
                                progress_time = match.group(1)
                                if progress_time != last_progress:
                                    last_progress = progress_time
                                    self.edit_status_label.setText(f"Encoding: {progress_time}")
                except queue.Empty:
                    pass
                
                time.sleep(0.05)  # Faster polling
                QApplication.processEvents()
            
            self._current_ffmpeg_process = None
            
            # Collect remaining stderr
            remaining_stderr = b''
            try:
                remaining_stderr = process.stderr.read()
            except:
                pass
            
            # Get result
            stdout, stderr = process.communicate()
            
            if process.returncode == 0:
                # Handle replace original option
                if replace_original:
                    try:
                        original_path = str(video_path)
                        # Delete original
                        os.remove(original_path)
                        # Rename temp to original name (with new extension)
                        final_name = video_path.stem + ext
                        final_path = video_path.parent / final_name
                        os.rename(str(output_file), str(final_path))
                        return {'success': True, 'output_name': final_name}
                    except Exception as e:
                        return {'success': False, 'error': f'Failed to replace original: {str(e)}'}
                return {'success': True, 'output_name': output_name}
            else:
                error_msg = stderr.decode('utf-8', errors='replace')[:200] if stderr else 'Unknown error'
                return {'success': False, 'error': error_msg}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    # === IMAGE DOWNLOAD METHODS ===
    
    def browse_image_output(self):
        """Browse for image output directory"""
        folder = QFileDialog.getExistingDirectory(self, "Select Image Download Directory")
        if folder:
            self.image_output.setText(folder)
    
    def paste_image_urls(self):
        """Paste image URLs from clipboard"""
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        if text:
            added, invalid, problematic = self.image_url_list_widget.add_urls_from_text(text)
            self.update_image_url_status()
            
            if added > 0:
                self.image_log(f"[OK] Added {added} image URL(s)")
            if invalid > 0:
                self.image_log(f"[!] Skipped {invalid} invalid URL(s)")
        else:
            QMessageBox.information(self, "Info", "Clipboard is empty")
    
    def update_image_url_status(self):
        """Update the image URL status label"""
        total = len(self.image_url_list_widget.urls)
        selected = len(self.image_url_list_widget.get_selected_urls())
        
        if total == 0:
            self.image_url_status.setText("No image URLs added")
        else:
            self.image_url_status.setText(f"{selected}/{total} selected")
    
    def image_log(self, message):
        """Log message to image progress text"""
        self.image_progress_text.append(message)
        # Auto-scroll to bottom
        scrollbar = self.image_progress_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        QApplication.processEvents()
    
    def download_images(self):
        """Download images from URL list"""
        if not IMAGE_DOWNLOADER_AVAILABLE:
            QMessageBox.warning(self, "Error", 
                "Image downloader module not available.\n\n"
                "Please ensure image_downloader.py is in the same directory.")
            return
        
        # Get URLs from list widget
        urls = self.image_url_list_widget.get_selected_urls()
        if not urls:
            QMessageBox.warning(self, "Warning", "Please add and select image URLs to download")
            return
        
        # Get output directory
        output_dir = self.image_output.text().strip() or "downloads/images"
        
        # Reset stop flag
        self.image_download_stopped = False
        
        # Create modern progress dialog
        progress_dialog = ImageDownloadProgressDialog(self, len(urls))
        progress_dialog.show()
        
        # Setup UI
        self.image_progress_text.clear()
        self.image_progress_bar.setValue(0)
        self.image_progress_bar.setMaximum(len(urls))
        self.image_status_label.setText(f"Downloading {len(urls)} images...")
        self.image_stats_label.setText("")
        self.image_download_btn.setEnabled(False)
        self.image_stop_btn.setEnabled(True)
        
        # Create downloader
        try:
            downloader = ImageDownloader(output_dir)
            
            successful = 0
            failed = 0
            skipped = 0
            
            for i, url in enumerate(urls, 1):
                if self.image_download_stopped or progress_dialog.cancelled:
                    self.image_log("Stopped by user")
                    break
                
                # Update progress dialog
                progress_dialog.update_progress(i, url, successful, failed)
                
                # Update progress
                self.image_progress_bar.setValue(i)
                self.image_stats_label.setText(f"{successful} saved | {failed} failed")
                self.image_status_label.setText(f"Downloading {i}/{len(urls)}...")
                QApplication.processEvents()
                
                # Determine subfolder by platform (use saved option)
                subfolder = None
                if self._image_subfolder:
                    platform = downloader.detect_platform(url)
                    if platform not in ['unknown', 'direct']:
                        subfolder = platform.capitalize()
                
                # Download
                self.image_log(f"[{i}/{len(urls)}] {url[:60]}...")
                result = downloader.download_image(
                    url, 
                    subfolder=subfolder, 
                    callback=self.image_log,
                    pinterest_max=self._image_pinterest_max
                )
                
                if result['success']:
                    # Handle batch results (e.g., Pinterest search URLs)
                    if 'downloaded' in result:
                        successful += result.get('downloaded', 0)
                        failed += result.get('failed', 0)
                        if result.get('message'):
                            self.image_log(result['message'])
                    else:
                        # Single image result
                        # Check min size filter
                        file_size = result.get('size', 0)
                        if self._image_min_size > 0 and file_size < self._image_min_size * 1024:
                            skipped += 1
                            self.image_log(f"Skipped (too small): {file_size/1024:.1f}KB")
                        elif result.get('skipped'):
                            skipped += 1
                        else:
                            successful += 1
                else:
                    failed += 1
                
                # Process events to keep UI responsive
                QApplication.processEvents()
            
            # Close progress dialog
            progress_dialog.close()
            
            # Final summary
            self.image_log("")
            self.image_log(f"Complete: {successful} saved, {failed} failed, {skipped} skipped")
            self.image_status_label.setText("Download complete")
            self.image_stats_label.setText(f"{successful} saved | {failed} failed | {skipped} skipped")
            self.image_progress_bar.setValue(len(urls))
            
            downloader.close()
            
            # Show modern finish dialog
            was_cancelled = self.image_download_stopped or progress_dialog.cancelled
            complete_dialog = ImageDownloadCompleteDialog(
                self, successful, failed, skipped, output_dir, was_cancelled
            )
            complete_dialog.exec()
            
        except Exception as e:
            progress_dialog.close()
            self.image_log(f"Error: {str(e)}")
            self.image_status_label.setText("Error occurred")
            QMessageBox.critical(self, "Download Error", f"An error occurred during download:\n\n{str(e)}")
        
        finally:
            self.image_download_btn.setEnabled(True)
            self.image_stop_btn.setEnabled(False)
    
    def search_and_download_images(self):
        """Search for images and download them"""
        if not IMAGE_DOWNLOADER_AVAILABLE:
            QMessageBox.warning(self, "Error", 
                "Image downloader module not available.\n\n"
                "Please ensure image_downloader.py is in the same directory.")
            return
        
        query = self.image_search_input.text().strip()
        if not query:
            QMessageBox.warning(self, "Warning", "Please enter a search query")
            return
        
        platform_text = self.image_search_platform.currentText()
        platform = 'google' if 'Google' in platform_text else 'pinterest'
        max_images = self.image_search_max.value()
        output_dir = self.image_output.text().strip() or "downloads/images"
        
        # Clear progress
        self.image_progress_text.clear()
        self.image_status_label.setText(f"Searching for '{query}'...")
        self.image_search_btn.setEnabled(False)
        
        try:
            downloader = ImageDownloader(output_dir)
            
            self.image_log(f"[?] Searching {platform_text} for '{query}'...")
            self.image_log(f"[G] Max images: {max_images}")
            QApplication.processEvents()
            
            result = downloader.search_and_download(query, platform, max_images, callback=self.image_log)
            
            if result.get('success', False) or result.get('successful', 0) > 0:
                self.image_log("")
                self.image_log(f"[OK] Search complete!")
                self.image_status_label.setText(f"Done: {result.get('successful', 0)} images saved")
            else:
                error = result.get('error', 'Unknown error')
                self.image_log(f"[X] Search failed: {error}")
                self.image_status_label.setText("Search failed")
                
                if 'Selenium' in error:
                    self.image_log("")
                    self.image_log("[*] Tip: Install Selenium for search feature:")
                    self.image_log("   pip install selenium webdriver-manager")
            
            downloader.close()
            
        except Exception as e:
            self.image_log(f"[X] Error: {str(e)}")
            self.image_status_label.setText("Error occurred")
        
        finally:
            self.image_search_btn.setEnabled(True)
    
    def extract_images_from_page(self):
        """Extract all images from a webpage"""
        if not IMAGE_DOWNLOADER_AVAILABLE:
            QMessageBox.warning(self, "Error", 
                "Image downloader module not available.\n\n"
                "Please ensure image_downloader.py is in the same directory.")
            return
        
        page_url = self.image_page_input.text().strip()
        if not page_url:
            QMessageBox.warning(self, "Warning", "Please enter a page URL")
            return
        
        if not page_url.startswith(('http://', 'https://')):
            page_url = 'https://' + page_url
        
        # Clear progress
        self.image_progress_text.clear()
        self.image_status_label.setText("Extracting images from page...")
        self.image_extract_btn.setEnabled(False)
        
        try:
            downloader = ImageDownloader()
            
            self.image_log(f"[?] Scanning page: {page_url}")
            QApplication.processEvents()
            
            image_urls = downloader.extract_images_from_page(page_url, callback=self.image_log)
            
            if image_urls:
                self.image_log(f"[OK] Found {len(image_urls)} images")
                self.image_log("")
                
                # Ask user if they want to add to download list
                reply = QMessageBox.question(
                    self, 
                    "Images Found",
                    f"Found {len(image_urls)} images on the page.\n\n"
                    f"Add them to the download list?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    # Add URLs to the list
                    added = 0
                    for url in image_urls:
                        result = self.image_url_list_widget.add_urls_from_text(url)
                        added += result[0]
                    
                    self.update_image_url_status()
                    self.image_log(f"[OK] Added {added} images to download list")
                    self.image_status_label.setText(f"Added {added} images to list")
            else:
                self.image_log("[X] No images found on page")
                self.image_status_label.setText("No images found")
            
            downloader.close()
            
        except Exception as e:
            self.image_log(f"[X] Error: {str(e)}")
            self.image_status_label.setText("Error occurred")
        
        finally:
            self.image_extract_btn.setEnabled(True)
    
    def style_spinbox(self, spinbox):
        """Style a spinbox widget"""
        spinbox.setStyleSheet("""
            QSpinBox {
                background: #21262d;
                color: #f0f6fc;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 12px;
            }
            QSpinBox:hover {
                border-color: #58a6ff;
            }
            QSpinBox:focus {
                border-color: #58a6ff;
                background: #161b22;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                background: #30363d;
                border: none;
                width: 16px;
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                background: #58a6ff;
            }
            QSpinBox::up-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-bottom: 4px solid #f0f6fc;
            }
            QSpinBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 4px solid #f0f6fc;
            }
        """)
    
    def get_profile_download_settings(self):
        """Get profile download settings from the UI"""
        max_videos_text = self.profile_max_videos.currentText()
        max_videos = None if max_videos_text == "All available" else int(max_videos_text)
        
        # Determine output directory
        output_dir = self.profile_output.text().strip() or "downloads/profiles"
        
        return {
            'quality': self.profile_quality.currentText(),
            'audio': self.profile_audio_cb.isChecked(),
            'subtitle': self.profile_subtitle_cb.isChecked(),
            'format': self.profile_format.currentText(),
            'convert': False,
            'mute': self.profile_mute_cb.isChecked(),
            'max_videos': max_videos,
            'sort_order': 'newest',
            'output_dir': output_dir,
            'create_subfolder': self.profile_create_subfolder_cb.isChecked(),
            'add_date': False,
            'add_index': False,
            'skip_existing': True
        }
    
    def download(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Warning", "Please enter a URL")
            return
        
        # Check if URL is a TikTok profile URL (not a video URL)
        if self.is_tiktok_profile_url(url):
            QMessageBox.warning(
                self, 
                "TikTok Profile URL Detected",
                "This type of URL can't be used in this feature.\n\n"
                "This appears to be a TikTok profile URL, not a video URL.\n\n"
                "Please use the 'Profile Video Download' tab instead to download videos from TikTok profiles."
            )
            return
        
        self.dl.output_dir = Path(self.output.text() or "downloads")
        self.dl.output_dir.mkdir(exist_ok=True)
        
        self.start_worker('download', url, {
            'quality': self.quality.currentText(),
            'audio': self.audio_cb.isChecked(),
            'subtitle': self.subtitle_cb.isChecked(),
            'format': self.format.currentText(),
            'convert': self.convert_cb.isChecked(),
            'mute': self.mute_cb.isChecked()
        })
    
    def is_tiktok_profile_url(self, url):
        """Check if URL is a TikTok profile URL (not a video URL)"""
        from urllib.parse import urlparse
        parsed = urlparse(url)
        clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}".lower()
        
        # TikTok profile: tiktok.com/@username (without /video/)
        if 'tiktok.com' in clean_url:
            return '/@' in clean_url and '/video/' not in clean_url
        return False
    
    def is_tiktok_video_url(self, url):
        """Check if URL is a TikTok video URL (not a profile URL)"""
        from urllib.parse import urlparse
        parsed = urlparse(url)
        clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}".lower()
        
        # Short TikTok URLs (vt.tiktok.com, vm.tiktok.com) are always video links
        if 'vt.tiktok.com' in clean_url or 'vm.tiktok.com' in clean_url:
            return True
        
        # TikTok video: tiktok.com/@username/video/VIDEO_ID
        if 'tiktok.com' in clean_url:
            return '/video/' in clean_url
        return False
    
    def is_facebook_single_video_url(self, url):
        """Check if URL is a Facebook single video URL (not a profile URL)"""
        url_lower = url.lower()
        
        # Single video patterns
        single_video_patterns = [
            '/share/r/',      # Share reel links
            '/share/v/',      # Share video links
            '/watch/?v=',     # Watch page with video ID
            '/watch?v=',      # Watch page with video ID (no trailing ?)
            'fb.watch/',      # Short video links
            '/video.php',     # Old video links
            '/reel/',         # Direct reel links (but not /reels/ which is profile)
        ]
        
        # Check for single video patterns
        for pattern in single_video_patterns:
            if pattern in url_lower:
                return True
        
        # Check for /videos/ with a video ID (e.g., /videos/123456789)
        import re
        if re.search(r'/videos/\d{5,}', url_lower):
            return True
        
        return False
    
    def handle_progress_dialog_close(self, result):
        """Handle when progress dialog is closed (including cancel)"""
        if hasattr(self, 'progress_dialog') and self.progress_dialog.cancelled:
            # User cancelled the operation
            if self.worker and self.worker.isRunning():
                self.worker.stop()  # Set stop flag first
                self.worker.terminate()  # Force stop the worker thread
                self.worker.wait(2000)  # Wait up to 2 seconds
            
            # Reset UI state
            self.dl_btn.setEnabled(True)
            self.info_btn.setEnabled(True)
            self.update_title_status("Cancelled", "#ffaa00")
            self.update_download_status("Operation cancelled by user", "#ffaa00")
            self.log("[STOP] Operation cancelled by user")

    def update_progress(self, percentage, message=""):
        """Update progress bar with percentage and optional message"""
        if hasattr(self, 'progress'):
            self.progress.setValue(int(percentage))
            if message:
                self.progress.setFormat(f"{int(percentage)}% - {message}")
            else:
                self.progress.setFormat(f"{int(percentage)}%")

    def start_worker(self, op, url, extra=None):
        if self.worker and self.worker.isRunning():
            return
        
        opts = {'op': op}
        if extra:
            opts.update(extra)
        
        # Create and show progress dialog
        if op == 'info':
            self.progress_dialog = ProgressDialog(self, "Getting Video Information", "info")
        else:
            self.progress_dialog = ProgressDialog(self, "Downloading Video", "download")
        
        # Connect cancel functionality
        self.progress_dialog.finished.connect(self.handle_progress_dialog_close)
        
        # Show dialog non-modally so it can be updated
        self.progress_dialog.show()
        
        self.worker = Worker(self.dl, url, opts)
        self.worker.progress.connect(self.log)
        self.worker.progress_percent.connect(self.progress_dialog.update_progress)  # Connect to dialog
        self.worker.done.connect(self.on_done)
        self.worker.info.connect(self.show_info)
        self.worker.start()
        
        # Hide the old progress bar since we're using dialog now
        self.progress.setVisible(False)
        self.dl_btn.setEnabled(False)
        self.info_btn.setEnabled(False)
        
        # Update title bar status and download status
        if op == 'info':
            self.update_title_status("Getting info...", "#ffaa00")
            self.update_download_status("Getting video information...", "#ffaa00")
        else:
            self.update_title_status("Downloading...", "#0088ff")
            self.update_download_status("Downloading video...", "#0088ff")
    
    def on_done(self, ok, msg, file_path=""):
        # Close progress dialog if it exists
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            if ok:
                self.progress_dialog.update_progress(100, "Complete!")
            else:
                self.progress_dialog.update_progress(100, "Failed")
            # Dialog will auto-close after showing completion
        
        self.progress.setVisible(False)
        self.dl_btn.setEnabled(True)
        self.info_btn.setEnabled(True)
        
        # Only log non-empty messages to avoid clutter
        if msg.strip():
            self.log(f"{'[OK]' if ok else '[X]'} {msg}")
        
        # Update title bar status and download status
        if ok:
            self.update_title_status("Ready", "#00ff88")
            if msg and 'complete' in msg.lower():
                self.update_download_status("Download completed successfully", "#2ea043")
            else:
                self.update_download_status("Ready for single video download", "#58a6ff")
        else:
            self.update_title_status("Error", "#ff4444")
            self.update_download_status("Operation failed - ready to try again", "#f85149")
        
        # Show custom success dialog with file path
        if ok and msg and 'complete' in msg.lower():
            dialog = SuccessDialog(self, msg, file_path)
            dialog.exec()
    
    def show_info(self, data):
        # Show video info in a dialog instead of the info text area
        dialog = VideoInfoDialog(self, data)
        dialog.exec()
        
        # Update status
        self.update_download_status("Video info retrieved - ready to download", "#2ea043")
        
        # Also update the info text area for reference (but don't log it)
        dur = data.get('duration', 0)
        if dur:
            dur = int(dur)
            dur_str = f"{dur//60}:{dur%60:02d}"
        else:
            dur_str = "Unknown"
        
        views = data.get('views', 0)
        views_str = f"{views/1e6:.1f}M" if views >= 1e6 else f"{views/1e3:.1f}K" if views >= 1e3 else str(views)
        
        self.info_text.setHtml(f"""
            <b style="color:#58a6ff">Title:</b> {data.get('title', 'Unknown')}<br>
            <b style="color:#58a6ff">Uploader:</b> {data.get('uploader', 'Unknown')}<br>
            <b style="color:#58a6ff">Platform:</b> {data.get('platform', 'Unknown')}<br>
            <b style="color:#58a6ff">Duration:</b> {dur_str}<br>
            <b style="color:#58a6ff">Views:</b> {views_str}
        """)
    
    def load_settings(self):
        """Load all persistent settings"""
        self._loading_settings = True  # Prevent auto-save during loading
        try:
            # Debug: Check what's actually in settings
            stored_dir = self.settings.value("output_directory", "downloads")
            self.log(f"[?] Raw stored directory: '{stored_dir}'")
            
            # Window geometry and position
            geometry = self.settings.value("geometry")
            if geometry:
                self.restoreGeometry(geometry)
            
            # Current tab index
            current_tab = self.settings.value("current_tab", 0, type=int)
            if hasattr(self, 'tab_widget') and 0 <= current_tab < self.tab_widget.count():
                self.tab_widget.setCurrentIndex(current_tab)
            
            # URL input
            last_url = self.settings.value("last_url", "")
            if last_url:
                self.url_input.setText(last_url)
            
            # Quality setting
            quality = self.settings.value("quality", "best")
            index = self.quality.findText(quality)
            if index >= 0:
                self.quality.setCurrentIndex(index)
            
            # Format setting
            format_val = self.settings.value("format", "Force H.264 (Compatible)")
            index = self.format.findText(format_val)
            if index >= 0:
                self.format.setCurrentIndex(index)
            
            # Checkbox states
            self.audio_cb.setChecked(self.settings.value("audio_only", False, type=bool))
            self.subtitle_cb.setChecked(self.settings.value("subtitles", False, type=bool))
            
            # Handle newer checkboxes that might not exist in older versions
            if hasattr(self, 'convert_cb'):
                self.convert_cb.setChecked(self.settings.value("force_convert", False, type=bool))
            if hasattr(self, 'caption_name_cb'):
                self.caption_name_cb.setChecked(self.settings.value("use_caption", True, type=bool))
            
            # Output directory
            output_dir = self.settings.value("output_directory", "downloads")
            self.log(f"[F] About to set output field to: '{output_dir}'")
            
            # Ensure the output field exists and is ready
            if hasattr(self, 'output') and self.output is not None:
                self.output.setText(output_dir)
                # Force the UI to update
                self.output.repaint()
                # Verify it was actually set
                actual_text = self.output.text()
                self.log(f"[F] Output field now shows: '{actual_text}'")
                self.dl.output_dir = Path(output_dir)
                self.log(f"[F] VideoDownloader output_dir set to: {self.dl.output_dir}")
            else:
                self.log("[!] Output field not ready yet, will retry later")
            
            # Force sync settings to ensure they're properly loaded
            self.settings.sync()
            
            # Log content - NOT persisted (starts fresh each session)
            # Explicitly remove any old log_content that might exist
            if self.settings.contains("log_content"):
                self.settings.remove("log_content")
            # Ensure log starts completely empty
            self.log_text.clear()
            
            # Info content - NOT persisted (starts fresh each session)
            # Explicitly remove any old info_content that might exist
            if self.settings.contains("info_content"):
                self.settings.remove("info_content")
            
            # Ensure info area starts completely empty
            if hasattr(self, 'info_text'):
                self.info_text.clear()
            
            # === MULTIPLE DOWNLOAD TAB PERSISTENCE ===
            # Multiple download quality and format settings
            multi_quality = self.settings.value("multi_quality", "best")
            if hasattr(self, 'multi_quality'):
                index = self.multi_quality.findText(multi_quality)
                if index >= 0:
                    self.multi_quality.setCurrentIndex(index)
            
            multi_format = self.settings.value("multi_format", "Force H.264 (Compatible)")
            if hasattr(self, 'multi_format'):
                index = self.multi_format.findText(multi_format)
                if index >= 0:
                    self.multi_format.setCurrentIndex(index)
            
            # Multiple download checkbox states
            if hasattr(self, 'multi_audio_cb'):
                self.multi_audio_cb.setChecked(self.settings.value("multi_audio_only", False, type=bool))
            if hasattr(self, 'multi_subtitle_cb'):
                self.multi_subtitle_cb.setChecked(self.settings.value("multi_subtitles", False, type=bool))
            
            # Multiple download output directory
            multi_output_dir = self.settings.value("multi_output_directory", "downloads")
            if hasattr(self, 'multi_output'):
                self.multi_output.setText(multi_output_dir)
                self.log(f"[F] Multiple download output directory set to: '{multi_output_dir}'")
            
            # Multiple download URLs will be loaded in retry_load_multi_urls() after UI is ready
            
            # Multiple download info and progress content - NOT persisted (starts fresh each session)
            # Explicitly remove any old content that might exist
            if self.settings.contains("multi_info_content"):
                self.settings.remove("multi_info_content")
            if self.settings.contains("multi_progress_content"):
                self.settings.remove("multi_progress_content")
            
            # Ensure these areas start completely empty
            if hasattr(self, 'multi_info_text'):
                self.multi_info_text.clear()
            if hasattr(self, 'multi_progress_text'):
                self.multi_progress_text.clear()
            
            # === PROFILE DOWNLOAD TAB PERSISTENCE ===
            # Profile URLs (multiple)
            profile_urls = self.settings.value("profile_urls", "")
            if hasattr(self, 'profile_url_list_widget') and profile_urls:
                self.profile_url_list_widget.add_urls_from_text(profile_urls)
                self.update_profile_url_status()
            
            # Profile quality setting
            profile_quality = self.settings.value("profile_quality", "best")
            if hasattr(self, 'profile_quality'):
                index = self.profile_quality.findText(profile_quality)
                if index >= 0:
                    self.profile_quality.setCurrentIndex(index)
            
            # Profile format setting
            profile_format = self.settings.value("profile_format", "Force H.264 (Compatible)")
            if hasattr(self, 'profile_format'):
                index = self.profile_format.findText(profile_format)
                if index >= 0:
                    self.profile_format.setCurrentIndex(index)
            
            # Profile max videos setting
            profile_max = self.settings.value("profile_max_videos", "50")
            if hasattr(self, 'profile_max_videos'):
                index = self.profile_max_videos.findText(profile_max)
                if index >= 0:
                    self.profile_max_videos.setCurrentIndex(index)
            
            # Profile checkbox states
            if hasattr(self, 'profile_audio_cb'):
                self.profile_audio_cb.setChecked(self.settings.value("profile_audio_only", False, type=bool))
            if hasattr(self, 'profile_subtitle_cb'):
                self.profile_subtitle_cb.setChecked(self.settings.value("profile_subtitles", False, type=bool))
            if hasattr(self, 'profile_create_subfolder_cb'):
                self.profile_create_subfolder_cb.setChecked(self.settings.value("profile_create_subfolder", True, type=bool))
            
            # Profile output directory
            profile_output_dir = self.settings.value("profile_output_directory", "downloads/profiles")
            if hasattr(self, 'profile_output'):
                self.profile_output.setText(profile_output_dir)
                self.log(f"[F] Profile download output directory set to: '{profile_output_dir}'")
            
            # Profile info and progress content - NOT persisted (starts fresh each session)
            if hasattr(self, 'profile_videos_text'):
                self.profile_videos_text.clear()
            if hasattr(self, 'profile_progress_text'):
                self.profile_progress_text.clear()
            
            # === IMAGE DOWNLOAD TAB PERSISTENCE ===
            # Image download URLs
            image_urls = self.settings.value("image_urls", "")
            if hasattr(self, 'image_url_list_widget') and image_urls:
                self.image_url_list_widget.add_urls_from_text(image_urls)
                self.update_image_url_status()
            
            # Image download output directory
            image_output_dir = self.settings.value("image_output_directory", "downloads/images")
            if hasattr(self, 'image_output'):
                self.image_output.setText(image_output_dir)
                self.log(f"[F] Image download output directory set to: '{image_output_dir}'")
            
            # Image download options
            if hasattr(self, '_image_subfolder'):
                self._image_subfolder = self.settings.value("image_subfolder", True, type=bool)
            if hasattr(self, '_image_skip_duplicates'):
                self._image_skip_duplicates = self.settings.value("image_skip_duplicates", True, type=bool)
            if hasattr(self, '_image_highres'):
                self._image_highres = self.settings.value("image_highres", True, type=bool)
            if hasattr(self, '_image_min_size'):
                self._image_min_size = self.settings.value("image_min_size", 0, type=int)
            if hasattr(self, '_image_pinterest_max'):
                self._image_pinterest_max = self.settings.value("image_pinterest_max", 50, type=int)
            if hasattr(self, '_image_format'):
                self._image_format = self.settings.value("image_format", "All formats")
            if hasattr(self, '_image_concurrent'):
                self._image_concurrent = self.settings.value("image_concurrent", 4, type=int)
            
            # Image progress content - NOT persisted (starts fresh each session)
            if hasattr(self, 'image_progress_text'):
                self.image_progress_text.clear()
            
            # === EDIT VIDEOS TAB PERSISTENCE ===
            edit_input = self.settings.value("edit_input_path", "")
            if hasattr(self, 'edit_input_folder') and edit_input:
                self.edit_input_folder.setText(edit_input)
                self.update_edit_video_count()
            
            edit_output = self.settings.value("edit_output_path", "downloads/edited")
            if hasattr(self, 'edit_output_folder'):
                self.edit_output_folder.setText(edit_output)
            
            # Load edit video settings
            edit_settings_json = self.settings.value("edit_video_settings", "")
            if edit_settings_json:
                try:
                    import json
                    self._edit_settings = json.loads(edit_settings_json)
                    # Update settings label
                    self.update_edit_settings_label()
                except:
                    self._edit_settings = {}
            
            self.log("[OK] Settings loaded from previous session")
            
        except Exception as e:
            self.log(f"[!] Could not load some settings: {e}")
        finally:
            self._loading_settings = False  # Re-enable auto-save
    
    def save_settings(self, silent=False):
        """Save all persistent settings"""
        try:
            # Window geometry and position
            self.settings.setValue("geometry", self.saveGeometry())
            
            # Current tab index
            if hasattr(self, 'tab_widget'):
                self.settings.setValue("current_tab", self.tab_widget.currentIndex())
            
            # URL input
            self.settings.setValue("last_url", self.url_input.text())
            
            # Quality and format settings
            self.settings.setValue("quality", self.quality.currentText())
            self.settings.setValue("format", self.format.currentText())
            
            # Checkbox states
            self.settings.setValue("audio_only", self.audio_cb.isChecked())
            self.settings.setValue("subtitles", self.subtitle_cb.isChecked())
            
            # Handle newer checkboxes that might not exist in older versions
            if hasattr(self, 'convert_cb'):
                self.settings.setValue("force_convert", self.convert_cb.isChecked())
            if hasattr(self, 'caption_name_cb'):
                self.settings.setValue("use_caption", self.caption_name_cb.isChecked())
            
            # Output directory
            current_dir = self.output.text().strip()
            if not current_dir:  # If empty, use default
                current_dir = "downloads"
            self.settings.setValue("output_directory", current_dir)
            
            # === MULTIPLE DOWNLOAD TAB PERSISTENCE ===
            # Multiple download quality and format settings
            if hasattr(self, 'multi_quality'):
                self.settings.setValue("multi_quality", self.multi_quality.currentText())
            if hasattr(self, 'multi_format'):
                self.settings.setValue("multi_format", self.multi_format.currentText())
            
            # Multiple download checkbox states
            if hasattr(self, 'multi_audio_cb'):
                self.settings.setValue("multi_audio_only", self.multi_audio_cb.isChecked())
            if hasattr(self, 'multi_subtitle_cb'):
                self.settings.setValue("multi_subtitles", self.multi_subtitle_cb.isChecked())
            
            # Multiple download output directory
            if hasattr(self, 'multi_output'):
                multi_current_dir = self.multi_output.text().strip()
                if not multi_current_dir:
                    multi_current_dir = "downloads"
                self.settings.setValue("multi_output_directory", multi_current_dir)
            
            # Multiple download URLs
            if hasattr(self, 'url_list_widget'):
                all_urls = self.url_list_widget.get_all_urls()
                self.settings.setValue("multi_urls", all_urls)
            
            # Multiple download info and progress content - NOT persisted (removed for fresh start each session)
            # Removed: multi_info_content and multi_progress_content saving
            
            # === PROFILE DOWNLOAD TAB PERSISTENCE ===
            # Profile URLs (multiple)
            if hasattr(self, 'profile_url_list_widget'):
                urls = self.profile_url_list_widget.get_all_urls()
                self.settings.setValue("profile_urls", "\n".join(urls))
            
            # Profile quality and format settings
            if hasattr(self, 'profile_quality'):
                self.settings.setValue("profile_quality", self.profile_quality.currentText())
            if hasattr(self, 'profile_format'):
                self.settings.setValue("profile_format", self.profile_format.currentText())
            if hasattr(self, 'profile_max_videos'):
                self.settings.setValue("profile_max_videos", self.profile_max_videos.currentText())
            
            # Profile checkbox states
            if hasattr(self, 'profile_audio_cb'):
                self.settings.setValue("profile_audio_only", self.profile_audio_cb.isChecked())
            if hasattr(self, 'profile_subtitle_cb'):
                self.settings.setValue("profile_subtitles", self.profile_subtitle_cb.isChecked())
            if hasattr(self, 'profile_create_subfolder_cb'):
                self.settings.setValue("profile_create_subfolder", self.profile_create_subfolder_cb.isChecked())
            
            # Profile output directory
            if hasattr(self, 'profile_output'):
                profile_current_dir = self.profile_output.text().strip()
                if not profile_current_dir:
                    profile_current_dir = "downloads/profiles"
                self.settings.setValue("profile_output_directory", profile_current_dir)
            
            # === IMAGE DOWNLOAD TAB PERSISTENCE ===
            # Image download URLs
            if hasattr(self, 'image_url_list_widget'):
                urls = self.image_url_list_widget.get_all_urls()
                self.settings.setValue("image_urls", "\n".join(urls))
            
            # Image download output directory
            if hasattr(self, 'image_output'):
                image_current_dir = self.image_output.text().strip()
                if not image_current_dir:
                    image_current_dir = "downloads/images"
                self.settings.setValue("image_output_directory", image_current_dir)
            
            # Image download options
            if hasattr(self, '_image_subfolder'):
                self.settings.setValue("image_subfolder", self._image_subfolder)
            if hasattr(self, '_image_skip_duplicates'):
                self.settings.setValue("image_skip_duplicates", self._image_skip_duplicates)
            if hasattr(self, '_image_highres'):
                self.settings.setValue("image_highres", self._image_highres)
            if hasattr(self, '_image_min_size'):
                self.settings.setValue("image_min_size", self._image_min_size)
            if hasattr(self, '_image_pinterest_max'):
                self.settings.setValue("image_pinterest_max", self._image_pinterest_max)
            if hasattr(self, '_image_format'):
                self.settings.setValue("image_format", self._image_format)
            if hasattr(self, '_image_concurrent'):
                self.settings.setValue("image_concurrent", self._image_concurrent)
            
            # === EDIT VIDEOS TAB PERSISTENCE ===
            if hasattr(self, 'edit_input_folder'):
                self.settings.setValue("edit_input_path", self.edit_input_folder.text())
            if hasattr(self, 'edit_output_folder'):
                self.settings.setValue("edit_output_path", self.edit_output_folder.text())
            if hasattr(self, '_edit_settings'):
                import json
                self.settings.setValue("edit_video_settings", json.dumps(self._edit_settings))
            
            # Sync settings to disk
            self.settings.sync()
            
            if not silent:
                self.log("[OK] Settings saved successfully")
            
        except Exception as e:
            if not silent:
                self.log(f"[!] Could not save some settings: {e}")
    
    def closeEvent(self, event):
        """Handle application close event to save settings"""
        try:
            # Force save all settings before closing
            self.save_settings()
            self.log("[?] Application closing - settings saved")
        except Exception as e:
            self.log(f"[!] Error saving settings on close: {e}")
        event.accept()
    
    def reset_all_settings(self):
        """Reset all settings to defaults"""
        reply = QMessageBox.question(self, "Reset Settings", 
                                   "Are you sure you want to reset all settings to defaults?",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            # Clear all settings
            self.settings.clear()
            
            # Explicitly ensure log_content is removed
            if self.settings.contains("log_content"):
                self.settings.remove("log_content")
            
            # Reset UI to defaults
            self.url_input.clear()
            self.quality.setCurrentIndex(0)  # "best"
            self.format.setCurrentIndex(0)   # "Force H.264 (Compatible)"
            self.audio_cb.setChecked(False)
            self.subtitle_cb.setChecked(False)
            if hasattr(self, 'convert_cb'):
                self.convert_cb.setChecked(False)
            if hasattr(self, 'caption_name_cb'):
                self.caption_name_cb.setChecked(True)
            self.output.setText("downloads")
            self.log_text.clear()  # Clear log but don't persist it
            self.info_text.clear()
            
            # Reset Multiple Download Tab to defaults
            if hasattr(self, 'multi_quality'):
                self.multi_quality.setCurrentIndex(0)  # "best"
            if hasattr(self, 'multi_format'):
                self.multi_format.setCurrentIndex(0)   # "Force H.264 (Compatible)"
            if hasattr(self, 'multi_audio_cb'):
                self.multi_audio_cb.setChecked(False)
            if hasattr(self, 'multi_subtitle_cb'):
                self.multi_subtitle_cb.setChecked(False)
            if hasattr(self, 'multi_output'):
                self.multi_output.setText("downloads")
            if hasattr(self, 'url_list_widget'):
                self.url_list_widget.clear_all()
            if hasattr(self, 'multi_info_text'):
                self.multi_info_text.clear()
            if hasattr(self, 'multi_progress_text'):
                self.multi_progress_text.clear()
            
            # Reset window position
            self.center_window()
            
            # Reset to first tab
            if hasattr(self, 'tab_widget'):
                self.tab_widget.setCurrentIndex(0)
            
            self.log("[OK] All settings reset to defaults")

    def on_tab_changed(self, index):
        """Handle tab change to save current state"""
        try:
            if not self._loading_settings:
                # Save current state when switching tabs
                self.auto_save_settings()
                
                # Update status based on current tab
                tab_names = ["Single Download", "Multiple Download", "Profile Video Download"]
                if 0 <= index < len(tab_names):
                    self.update_title_status(f"Ready - {tab_names[index]}", "#00ff88")
        except Exception as e:
            # Don't let tab switching fail due to save errors
            pass

    def periodic_save(self):
        """Periodically save text content that might change during use"""
        try:
            if not self._loading_settings:
                # Multiple download info and progress content - NOT persisted (removed for fresh start each session)
                # Removed: multi_info_content and multi_progress_content saving
                
                # Log content - NOT persisted (removed for fresh start each session)
                # Removed: log_content saving
                
                # Video info content - NOT persisted (removed for fresh start each session)
                # Removed: info_content saving
                
                # Save URLs in case they changed
                if hasattr(self, 'url_list_widget'):
                    all_urls = self.url_list_widget.get_all_urls()
                    self.settings.setValue("multi_urls", all_urls)
                
                self.settings.sync()
        except Exception as e:
            # Don't spam the log with periodic save errors
            pass

    def auto_save_settings(self):
        """Auto-save settings when values change"""
        try:
            # Don't auto-save while we're loading settings
            if self._loading_settings:
                return
            # This will be called when important values change - save silently
            self.save_settings(silent=True)
        except Exception as e:
            # Don't spam the log with auto-save errors
            pass


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("VIDT - Video Downloader Tool")
    
    # Set app icon - try multiple paths for dev and EXE
    logo_paths = [
        Path("logo/logo.png"),
        Path("logo.png"),
    ]
    
    # For PyInstaller EXE
    if getattr(sys, 'frozen', False):
        base_path = Path(sys._MEIPASS)
        logo_paths.insert(0, base_path / "logo" / "logo.png")
        logo_paths.insert(1, base_path / "logo.png")
    
    for logo_path in logo_paths:
        try:
            if logo_path.exists():
                app.setWindowIcon(QIcon(str(logo_path)))
                break
        except:
            continue
    
    # License check (optional - set SKIP_LICENSE=1 to bypass)
    import os
    skip_license = os.environ.get('SKIP_LICENSE', '0') == '1'
    
    if LICENSE_CLIENT_AVAILABLE and not skip_license:
        license_client = get_license_client()
        
        # Create a helper class to handle cross-thread signals
        from PyQt6.QtCore import QObject, pyqtSignal
        
        class LicenseSignalHandler(QObject):
            license_disabled = pyqtSignal(str)
            
            def __init__(self):
                super().__init__()
                self.license_disabled.connect(self._show_disabled_dialog)
            
            def _show_disabled_dialog(self, message):
                from PyQt6.QtWidgets import QMessageBox
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Icon.Critical)
                msg.setWindowTitle("License Disabled")
                msg.setText("Your license has been disabled by the administrator.")
                msg.setInformativeText("Please contact support or purchase a new license.")
                msg.setStandardButtons(QMessageBox.StandardButton.Ok)
                msg.setStyleSheet("""
                    QMessageBox {
                        background-color: #1a1a2e;
                        color: #ffffff;
                    }
                    QMessageBox QLabel {
                        color: #ffffff;
                        font-size: 13px;
                    }
                    QMessageBox QPushButton {
                        background-color: #e74c3c;
                        color: white;
                        border: none;
                        padding: 8px 24px;
                        border-radius: 6px;
                        font-weight: bold;
                        min-width: 80px;
                    }
                    QMessageBox QPushButton:hover {
                        background-color: #c0392b;
                    }
                """)
                msg.exec()
                QApplication.quit()
        
        license_signal_handler = LicenseSignalHandler()
        
        # Set up real-time license revocation handler
        def handle_license_disabled(message):
            """Called INSTANTLY when license is disabled by admin"""
            print(f"LICENSE DISABLED: {message}")
            license_signal_handler.license_disabled.emit(message)
        
        license_client.on_license_disabled(handle_license_disabled)
        
        # Create main window first (will be shown in background)
        window = MainWindow()
        window.show()
        QApplication.processEvents()
        
        # Check if already has valid cached license
        if not license_client.is_valid():
            # Try to validate with server
            result = license_client.validate()
            
            if not result.get("valid"):
                # Show activation dialog over the main window
                dialog = LicenseActivationDialog(window, license_client)
                if dialog.exec() != QDialog.DialogCode.Accepted or not dialog.activated:
                    # User cancelled or activation failed
                    sys.exit(0)
        
        # Update license display after successful validation
        window.update_license_display()
        
        # Start background validation (real-time monitoring)
        license_client.start_background_validation()
        
        sys.exit(app.exec())
    else:
        window = MainWindow()
        window.show()
        sys.exit(app.exec())


if __name__ == "__main__":
    main()