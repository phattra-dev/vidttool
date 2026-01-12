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

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QTextEdit, QComboBox, QCheckBox, QLabel,
    QProgressBar, QFileDialog, QMessageBox, QFrame, QGridLayout, QSizePolicy,
    QTabWidget, QDialog, QScrollArea, QListWidget, QListWidgetItem
)
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QSettings, QTimer
from PyQt6.QtGui import QFont, QIcon, QPixmap


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
            if url and url.startswith(('http://', 'https://')):
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
                self.parent_window.multi_log(f"🔄 Skipped duplicate: {dup_url[:50]}...")
        
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
            url_display = "⚠ " + url_display
        
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
            url_label.setToolTip(f"⚠ Problematic URL: {url}\n\nThis URL type may not work. Consider using direct video URLs instead.")
        else:
            url_label.setToolTip(url)  # Full URL on hover
        
        # Remove button
        remove_btn = QPushButton("✕")
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
        
        info_icon = QLabel("📋")
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
        
        copy_all_btn = QPushButton("📋 Copy All Info")
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
            status_icon = "❌"
            status_color = "#f85149"
            video_title = f"Video {index} - Error"
        else:
            status_icon = "✅"
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
        self.sender().setText("✅ Copied!")
        QTimer.singleShot(1500, lambda: self.sender().setText("📋 Copy All Info"))
    
    def style_button_primary(self, btn):
        btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #6366f1, stop:1 #4f46e5);
                color: white;
                border: none;
                border-radius: 10px;
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
                border-radius: 10px;
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
        
        title_icon = QLabel("📥")
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
        
        self.pause_btn = QPushButton("⏸ Pause")
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
        
        self.cancel_btn = QPushButton("⏹ Stop")
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
            self.pause_btn.setText("▶ Resume")
            self.video_status_label.setText("Downloads paused...")
        else:
            self.pause_btn.setText("⏸ Pause")
    
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
        self.setFixedSize(400, 150)
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
        
        if self.operation_type == "info":
            icon = "ℹ️"
            title_text = "Getting Video Information"
        else:
            icon = "⬇️"
            title_text = "Downloading Video"
        
        title_icon = QLabel(icon)
        title_icon.setStyleSheet("font-size: 20px; border: none; background: transparent;")
        
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
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background: rgba(248, 81, 73, 0.8);
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 11px;
                font-weight: bold;
                padding: 6px 16px;
                min-width: 60px;
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
        
        info_icon = QLabel("ℹ️")
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
            ("📺 Title:", self.video_data.get('title', 'Unknown')),
            ("👤 Uploader:", self.video_data.get('uploader', 'Unknown')),
            ("🌐 Platform:", self.video_data.get('platform', 'Unknown')),
            ("⏱️ Duration:", dur_str),
            ("👁️ Views:", views_str)
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
        
        copy_btn = QPushButton("📋 Copy Info")
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
        self.sender().setText("✅ Copied!")
        QTimer.singleShot(1500, lambda: self.sender().setText("📋 Copy Info"))
    
    def style_button_primary(self, btn):
        btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #6366f1, stop:1 #4f46e5);
                color: white;
                border: none;
                border-radius: 10px;
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
                border-radius: 10px;
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
        
        success_icon = QLabel("✅")
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
        
        view_btn = QPushButton("📁 View Video")
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
                border-radius: 8px;
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
                border-radius: 8px;
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
        header = QLabel("✅ Profile Found")
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
        info_layout.addWidget(self.create_info_row("👤 Profile", profile_name))
        info_layout.addWidget(self.create_info_row("📱 Platform", platform))
        info_layout.addWidget(self.create_info_row("📹 Videos", str(total_videos)))
        
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
        
        profile_icon = QLabel("👤")
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
        
        download_btn = QPushButton("📥 Start Download")
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
        
        details_label = QLabel(f"Duration: {duration_str} • Uploader: {video.get('uploader', 'Unknown')}")
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
                border-radius: 8px;
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
                border-radius: 8px;
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
        icon_label = QLabel("🎉")
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
        success_card = self.create_stat_card("✅", str(completed), "Successful", "#2ea043")
        stats_layout.addWidget(success_card)
        
        # Divider
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.VLine)
        divider.setStyleSheet("QFrame { color: #30363d; }")
        stats_layout.addWidget(divider)
        
        # Failed card
        failed_card = self.create_stat_card("❌", str(failed), "Failed", "#f85149")
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
            
            location_title = QLabel("📁 Download Location")
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
        open_folder_btn = QPushButton("📁 Open Folder")
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
                border-radius: 8px;
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
                border-radius: 8px;
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
        
    def run(self):
        total_urls = len(self.urls)
        completed = 0
        failed = 0
        successful_files = []
        failed_urls = []
        
        for i, url in enumerate(self.urls):
            if self.stopped:
                break
                
            # Wait if paused
            while self.paused and not self.stopped:
                self.msleep(100)
                
            if self.stopped:
                break
                
            self.video_started.emit(i, url)
            self.progress.emit(f"📥 Starting download {i+1}/{total_urls}: {url[:50]}...")
            
            try:
                # Create progress callback for current video
                def progress_callback(message):
                    self.progress.emit(f"[{i+1}/{total_urls}] {message}")
                    # Try to extract percentage from yt-dlp progress messages
                    if "%" in message and "Downloading:" in message:
                        try:
                            # Extract percentage from messages like "Downloading: 45.2%"
                            percent_str = message.split("%")[0].split()[-1]
                            percent = float(percent_str)
                            self.progress_percent.emit(int(percent), f"Video {i+1}/{total_urls}")
                        except:
                            pass
                    elif "Completed:" in message:
                        self.progress_percent.emit(100, f"Video {i+1}/{total_urls} complete")
                
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
                
                if result['success']:
                    completed += 1
                    file_path = str(result['file_path']) if result['file_path'] else ""
                    successful_files.append(file_path)
                    self.video_completed.emit(i, True, "Download complete", file_path)
                    self.progress.emit(f"✅ Completed {i+1}/{total_urls}: {url[:50]}")
                else:
                    failed += 1
                    failed_urls.append(url)
                    self.video_completed.emit(i, False, f"Failed: {result.get('error', 'Unknown error')}", "")
                    self.progress.emit(f"❌ Failed {i+1}/{total_urls}: {url[:50]}")
                    
            except Exception as e:
                failed += 1
                failed_urls.append(url)
                self.video_completed.emit(i, False, f"Error: {str(e)}", "")
                self.progress.emit(f"❌ Error {i+1}/{total_urls}: {str(e)}")
        
        # Send completion summary
        summary = {
            'total': total_urls,
            'completed': completed,
            'failed': failed,
            'successful_files': successful_files,
            'failed_urls': failed_urls,
            'stopped': self.stopped
        }
        self.batch_completed.emit(summary)
    
    def pause(self):
        self.paused = True
        
    def resume(self):
        self.paused = False
        
    def stop(self):
        self.stopped = True
        self.paused = False


class VideoDownloader:
    """Core downloader"""
    def __init__(self, output_dir="downloads"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.platforms = {
            'youtube.com': 'YouTube', 'youtu.be': 'YouTube',
            'tiktok.com': 'TikTok', 'facebook.com': 'Facebook',
            'fb.watch': 'Facebook', 'instagram.com': 'Instagram',
            'twitter.com': 'Twitter', 'x.com': 'Twitter',
            'vimeo.com': 'Vimeo', 'twitch.tv': 'Twitch'
        }
    
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
        
        # Facebook profile/page patterns
        elif 'facebook.com' in clean_url:
            return any(pattern in clean_url for pattern in [
                '/profile.php', '/pages/', '/people/'
            ]) or ('/watch/' not in clean_url and '/videos/' not in clean_url)
        
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
                
                if 'entries' in info:
                    print(f"Found {len(info['entries'])} entries")
                    # Playlist/channel with multiple videos
                    for i, entry in enumerate(info['entries']):
                        if entry and entry.get('url'):
                            video_info = {
                                'url': entry['url'],
                                'title': entry.get('title', f'Video {i+1}'),
                                'id': entry.get('id', ''),
                                'duration': entry.get('duration', 0),
                                'uploader': info.get('uploader', entry.get('uploader', 'Unknown')),
                                'upload_date': entry.get('upload_date', ''),
                                'view_count': entry.get('view_count', 0)
                            }
                            videos.append(video_info)
                        elif entry is None:
                            print(f"Skipping None entry at index {i}")
                        else:
                            print(f"Skipping entry without URL at index {i}: {entry.get('title', 'No title')}")
                
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
                          "• facebook.com/watch/?v=VIDEO_ID\n"
                          "• facebook.com/USERNAME/videos/VIDEO_ID")
        
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

    def download(self, url, quality='best', audio_only=False, subtitle=False, format_pref='Force H.264 (Compatible)', force_convert=False, use_caption=True, mute_video=False, callback=None):
        # Detect platform to use appropriate filename template
        platform = self.detect_platform(url)
        
        # For TikTok, use description (full caption) instead of title (truncated)
        if 'TikTok' in platform:
            safe_template = str(self.output_dir / '%(description)s.%(ext)s')
        else:
            safe_template = str(self.output_dir / '%(title)s.%(ext)s')
        
        opts = {
            'outtmpl': safe_template,
            'retries': 3,
            'restrictfilenames': False,  # Keep spaces, don't replace with _
            'windowsfilenames': True,    # Make filenames Windows-compatible
            'trim_file_name': 210,       # Allow longer filenames (max 210 for Windows)
        }
        
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
        
        if callback:
            def hook(d):
                if d['status'] == 'downloading' and 'total_bytes' in d:
                    pct = d['downloaded_bytes'] / d['total_bytes'] * 100
                    callback(f"Downloading: {pct:.1f}%")
                elif d['status'] == 'finished':
                    callback(f"✓ Completed: {d['filename']}")
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
                        height = quality[:-1]
                        opts['format'] = f'best[vcodec*=avc1][height<={height}]/best[vcodec*=h264][height<={height}]/best[format_id*=download][height<={height}]/best[format_id!*=bytevc1][height<={height}]/best[height<={height}]'
                elif 'Facebook' in platform:
                    # Facebook-specific format selection - more permissive
                    if quality == 'best':
                        opts['format'] = 'best[ext=mp4]/best'
                    else:
                        height = quality[:-1]
                        opts['format'] = f'best[ext=mp4][height<={height}]/best[height<={height}]'
                else:
                    # General format selection for other platforms
                    if quality == 'best':
                        opts['format'] = 'best[vcodec*=avc1]/best[vcodec*=h264]/best[ext=mp4]/best'
                    else:
                        height = quality[:-1]
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
                            callback("🔧 FFmpeg available - will convert if needed")
                    except (subprocess.CalledProcessError, FileNotFoundError):
                        if callback:
                            callback("⚠ FFmpeg not found - downloading best available format")
                        # Don't add post-processor if FFmpeg is not available
                
            elif format_pref == 'Convert to H.264':
                # Download any format but convert to H.264 (only if FFmpeg available)
                opts['format'] = 'best' if quality == 'best' else f'best[height<={quality[:-1]}]'
                try:
                    import subprocess
                    subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
                    opts['postprocessors'] = [{
                        'key': 'FFmpegVideoConvertor',
                        'preferedformat': 'mp4',
                    }]
                    if callback:
                        callback("🔧 Will convert to H.264 using FFmpeg")
                except (subprocess.CalledProcessError, FileNotFoundError):
                    if callback:
                        callback("⚠ FFmpeg not found - downloading without conversion")
                
            elif format_pref == 'mp4 (H.264)':
                # Try to get H.264 but don't convert
                if quality == 'best':
                    opts['format'] = 'best[ext=mp4][vcodec*=avc1]/best[ext=mp4][vcodec*=h264]/best[ext=mp4]/best'
                else:
                    height = quality[:-1]
                    opts['format'] = f'best[ext=mp4][vcodec*=avc1][height<={height}]/best[ext=mp4][vcodec*=h264][height<={height}]/best[ext=mp4][height<={height}]/best[height<={height}]'
                    
            elif format_pref == 'webm':
                opts['format'] = 'best[ext=webm]/best' if quality == 'best' else f'best[ext=webm][height<={quality[:-1]}]/best[height<={quality[:-1]}]'
            else:  # 'any'
                opts['format'] = 'best' if quality == 'best' else f'best[height<={quality[:-1]}]'
        
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
                    callback("⚠ Format selection failed, trying simpler format...")
                
                # Create simpler options
                simple_opts = opts.copy()
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
            if callback:
                callback(f"✗ Error: {e}")
            return {'success': False, 'error': str(e)}


class Worker(QThread):
    progress = pyqtSignal(str)
    progress_percent = pyqtSignal(int, str)  # percentage, message
    done = pyqtSignal(bool, str, str)  # success, message, file_path
    info = pyqtSignal(dict)
    
    def __init__(self, dl, url, opts):
        super().__init__()
        self.dl, self.url, self.opts = dl, url, opts
    
    def run(self):
        try:
            if self.opts.get('op') == 'info':
                self.progress_percent.emit(10, "Connecting...")
                self.progress.emit("🔍 Getting video information...")
                
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
                    self.progress.emit(f"❌ Error: {error_msg}")
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
                    self.progress.emit(f"🔍 Worker: success=True, file_path='{file_path}'")
                    self.done.emit(True, "Download complete", file_path)
                else:
                    self.progress_percent.emit(100, "Failed")
                    self.progress.emit(f"🔍 Worker: success=False, error='{result.get('error', 'Unknown error')}'")
                    self.done.emit(False, f"Download failed: {result.get('error', 'Unknown error')}", "")
                    
        except Exception as e:
            self.done.emit(False, str(e), "")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.dl = VideoDownloader()
        self.worker = None
        self.multi_worker = None  # For multiple downloads
        self._loading_settings = False  # Flag to prevent auto-save during loading
        
        # Initialize settings for persistence
        self.settings = QSettings("VideoDownloader", "VideoDownloaderPro")
        
        self.setup_ui()
        self.load_settings()  # Load saved settings after UI setup
        
        # Add a small delay to ensure UI is fully ready, then retry setting directory
        QTimer.singleShot(100, self.retry_set_directory)
        
        # Check for FFmpeg and show info
        QTimer.singleShot(500, self.check_ffmpeg)
        
        # Clean up any old log persistence and show welcome message
        QTimer.singleShot(1000, self.setup_fresh_log)
        
        # Set up periodic auto-save for text areas (every 30 seconds)
        self.auto_save_timer = QTimer()
        self.auto_save_timer.timeout.connect(self.periodic_save)
        self.auto_save_timer.start(30000)  # 30 seconds
    
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
            self.log("🧹 Removed old text content persistence - all text areas starting fresh")
        
        # Show welcome message
        self.show_welcome_message()
        
        # Debug: Show what settings keys exist
        all_keys = self.settings.allKeys()
        text_related_keys = [key for key in all_keys if any(word in key.lower() for word in ['log', 'info', 'progress', 'content'])]
        if text_related_keys:
            self.log(f"🔍 Debug: Found text-related settings keys: {text_related_keys}")
        else:
            self.log("✅ Confirmed: No text content settings found - all text areas will start fresh")

    def update_download_status(self, status, color="#58a6ff"):
        """Update the single download status label"""
        if hasattr(self, 'download_status_label'):
            self.download_status_label.setText(status)
            self.download_status_label.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 11px; border: none; background: transparent;")

    def clear_log(self):
        """Clear log and show a fresh start message"""
        self.log_text.clear()
        self.log("📝 Log cleared - Ready for new operations")

    def show_welcome_message(self):
        """Show welcome message in log since it doesn't persist"""
        self.log("🎬 Video Downloader Tool - Ready!")
        self.log("💡 Tip: Use the Help button (❓) in Multiple Download tab for URL format guidance")
        self.log("📋 Paste video URLs and click 'Get Info' to check compatibility")
        self.log("⚙️ All your settings and URLs are automatically saved")
        self.log("─" * 50)

    def check_ffmpeg(self):
        """Check if FFmpeg is available and provide guidance"""
        import subprocess
        try:
            # Try to run ffmpeg to check if it's available
            subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
            self.log("✅ FFmpeg is available - full format conversion supported")
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.log("⚠ FFmpeg not found - some format conversions may not work")
            self.log("💡 To install FFmpeg:")
            self.log("   1. Download from: https://ffmpeg.org/download.html")
            self.log("   2. Or use: winget install ffmpeg (Windows)")
            self.log("   3. Add to PATH environment variable")

    def retry_set_directory(self):
        """Retry setting the output directory after UI is fully loaded"""
        try:
            stored_dir = self.settings.value("output_directory", "downloads")
            if stored_dir and stored_dir != "downloads":
                self.log(f"🔄 Retrying to set directory: '{stored_dir}'")
                self._loading_settings = True  # Prevent auto-save during retry
                self.output.setText(stored_dir)
                self._loading_settings = False  # Re-enable auto-save
                self.dl.output_dir = Path(stored_dir)
                # Verify it worked this time
                actual_text = self.output.text()
                self.log(f"🔄 After retry, output field shows: '{actual_text}'")
        except Exception as e:
            self.log(f"⚠ Retry failed: {e}")
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
                        self.log(f"🔄 Successfully restored {added_count} URLs from previous session")
                        # Update the URL status after loading
                        if hasattr(self, 'update_url_status'):
                            self.update_url_status()
        except Exception as e:
            self.log(f"⚠ Failed to restore URLs: {e}")
            self._loading_settings = False  # Ensure flag is reset

    def setup_ui(self):
        # Remove default window frame to create custom title bar
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setWindowTitle("Video Downloader Tool")
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
        
        # Add tabs to widget
        self.tab_widget.addTab(self.single_tab, "Single Download")
        self.tab_widget.addTab(self.multiple_tab, "Multiple Download")
        self.tab_widget.addTab(self.profile_tab, "Profile Video Download")
        
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
        
        self.dl_btn = QPushButton("⬇  Download")
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
        self.quality.addItems(["best", "1080p", "720p", "480p"])
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
        
        paste_urls_btn = QPushButton("📋 Paste URLs")
        paste_urls_btn.setFixedHeight(32)
        paste_urls_btn.clicked.connect(self.paste_multiple_urls)
        self.style_btn_secondary(paste_urls_btn)
        
        select_all_btn = QPushButton("☑ Select All")
        select_all_btn.setFixedHeight(32)
        select_all_btn.clicked.connect(lambda: self.url_list_widget.select_all(True))
        self.style_btn_secondary(select_all_btn)
        
        deselect_all_btn = QPushButton("☐ Deselect All")
        deselect_all_btn.setFixedHeight(32)
        deselect_all_btn.clicked.connect(lambda: self.url_list_widget.select_all(False))
        self.style_btn_secondary(deselect_all_btn)
        
        clear_urls_btn = QPushButton("🗑 Clear All")
        clear_urls_btn.setFixedHeight(32)
        clear_urls_btn.clicked.connect(self.clear_all_urls)
        self.style_btn_secondary(clear_urls_btn)
        
        # URL status label
        self.url_status_label = QLabel("No URLs added")
        self.url_status_label.setStyleSheet("color: #7d8590; font-size: 11px; font-style: italic; border: none; background: transparent;")
        
        # Help button for URL formats
        help_btn = QPushButton("❓ Help")
        help_btn.setFixedHeight(32)
        help_btn.clicked.connect(self.show_url_help)
        self.style_btn_secondary(help_btn)
        
        self.multi_info_btn = QPushButton("Get Info")
        self.multi_info_btn.setFixedHeight(32)
        self.multi_info_btn.clicked.connect(self.get_multiple_info)
        self.style_btn_green(self.multi_info_btn)
        
        # Download control buttons - positioned near Get Info
        self.multi_pause_btn = QPushButton("⏸ Pause")
        self.multi_pause_btn.setFixedHeight(32)
        self.multi_pause_btn.clicked.connect(self.pause_multiple_downloads)
        self.multi_pause_btn.setEnabled(False)
        self.style_btn_secondary(self.multi_pause_btn)
        
        self.multi_stop_btn = QPushButton("⏹ Stop")
        self.multi_stop_btn.setFixedHeight(32)
        self.multi_stop_btn.clicked.connect(self.stop_multiple_downloads)
        self.multi_stop_btn.setEnabled(False)
        self.style_btn_secondary(self.multi_stop_btn)
        
        self.multi_download_btn = QPushButton("⬇ Start Downloads")
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
        self.multi_quality.addItems(["best", "1080p", "720p", "480p"])
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
        
        paste_urls_btn = QPushButton("📋 Paste URLs")
        paste_urls_btn.setFixedHeight(32)
        paste_urls_btn.clicked.connect(self.paste_profile_urls)
        self.style_btn_secondary(paste_urls_btn)
        
        select_all_btn = QPushButton("☑ Select All")
        select_all_btn.setFixedHeight(32)
        select_all_btn.clicked.connect(lambda: self.profile_url_list_widget.select_all(True))
        self.style_btn_secondary(select_all_btn)
        
        deselect_all_btn = QPushButton("☐ Deselect All")
        deselect_all_btn.setFixedHeight(32)
        deselect_all_btn.clicked.connect(lambda: self.profile_url_list_widget.select_all(False))
        self.style_btn_secondary(deselect_all_btn)
        
        clear_urls_btn = QPushButton("🗑 Clear All")
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
        
        self.profile_download_btn = QPushButton("⬇ Download Videos")
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
        self.profile_quality.addItems(["best", "1080p", "720p", "480p", "360p"])
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
        self.multi_info_text.append(f"🔍 Getting info for {len(selected_urls)} selected videos...")
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
        self.multi_info_text.append(f"✅ Info check completed for {len(selected_urls)} videos")
        self.multi_info_text.append("📋 Results shown in dialog - check individual video details")
        
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
        title = QLabel("📋 Supported Video URL Formats")
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
<b style="color: #2ea043;">✅ SUPPORTED PLATFORMS:</b><br><br>

<b style="color: #58a6ff;">YouTube:</b><br>
• youtube.com/watch?v=VIDEO_ID<br>
• youtu.be/VIDEO_ID<br>
• youtube.com/playlist?list=PLAYLIST_ID<br><br>

<b style="color: #58a6ff;">Facebook:</b><br>
• facebook.com/watch/?v=VIDEO_ID<br>
• facebook.com/USERNAME/videos/VIDEO_ID<br>
• fb.watch/VIDEO_ID<br><br>

<b style="color: #58a6ff;">TikTok:</b><br>
• tiktok.com/@username/video/VIDEO_ID<br>
• vm.tiktok.com/SHORT_CODE<br><br>

<b style="color: #58a6ff;">Instagram:</b><br>
• instagram.com/p/POST_ID<br>
• instagram.com/reel/REEL_ID<br><br>

<b style="color: #58a6ff;">Twitter/X:</b><br>
• twitter.com/username/status/TWEET_ID<br>
• x.com/username/status/TWEET_ID<br><br>

<b style="color: #58a6ff;">Other Platforms:</b><br>
• Vimeo, Twitch, Dailymotion, and 1000+ more<br><br>

<b style="color: #f85149;">❌ NOT SUPPORTED:</b><br>
• Profile/channel URLs (use direct video links)<br>
• Share URLs (copy the original video URL)<br>
• Private or restricted videos<br>
• Live streams (in most cases)<br><br>

<b style="color: #ffab00;">💡 TIPS:</b><br>
• Always use direct video URLs, not profile links<br>
• If a URL doesn't work, try copying it again from the source<br>
• Some platforms may require the video to be public<br>
• Check the video is still available and not deleted
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
        self.multi_log("🗑 Cleared all URLs")
    
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
                    self.multi_log("▶️ Downloads resumed from dialog")
                else:
                    self.multi_worker.pause()
                    self.multi_log("⏸ Downloads paused from dialog")
        
        self.multi_progress_dialog.pause_btn.clicked.connect(handle_dialog_pause)
        
        self.multi_worker.start()
        
        # Update UI state
        self.multi_download_btn.setEnabled(False)
        self.multi_pause_btn.setEnabled(True)
        self.multi_stop_btn.setEnabled(True)
        
        self.multi_log(f"🚀 Starting batch download of {len(selected_urls)} selected videos...")
        self.update_multi_status(f"Downloading: 0/{len(selected_urls)} completed")

    def paste_multiple_urls(self):
        """Paste multiple URLs from clipboard"""
        clipboard_text = QApplication.clipboard().text()
        if clipboard_text.strip():
            # Debug: Show what was pasted
            lines = clipboard_text.strip().split('\n')
            self.multi_log(f"📋 Pasting {len(lines)} lines from clipboard:")
            for i, line in enumerate(lines[:5], 1):  # Show first 5 lines
                if line.strip():
                    self.multi_log(f"   {i}. {line.strip()[:60]}...")
            if len(lines) > 5:
                self.multi_log(f"   ... and {len(lines)-5} more lines")
            
            added_count, invalid_count, problematic_count = self.url_list_widget.add_urls_from_text(clipboard_text)
            
            # Detailed results
            self.multi_log(f"📊 Results: {added_count} valid, {problematic_count} problematic, {invalid_count} invalid")
            
            if added_count > 0:
                self.multi_log(f"✅ Added {added_count} valid URLs")
            if problematic_count > 0:
                self.multi_log(f"⚠ Added {problematic_count} problematic URLs (may not work)")
            if invalid_count > 0:
                self.multi_log(f"❌ Skipped {invalid_count} invalid URLs")
            
            if added_count == 0 and problematic_count == 0:
                if invalid_count > 0:
                    self.multi_log(f"❌ Found only invalid URLs in clipboard")
                else:
                    self.multi_log("⚠ No valid URLs found in clipboard")
        else:
            self.multi_log("⚠ Clipboard is empty")
        
        # Update status after pasting
        self.update_url_status()

    
    def pause_multiple_downloads(self):
        """Pause/Resume multiple downloads"""
        if self.multi_worker:
            if self.multi_worker.paused:
                self.multi_worker.resume()
                self.multi_pause_btn.setText("⏸ Pause")
                self.multi_log("▶️ Downloads resumed")
                self.update_multi_status("Downloading (resumed)")
            else:
                self.multi_worker.pause()
                self.multi_pause_btn.setText("▶️ Resume")
                self.multi_log("⏸ Downloads paused")
                self.update_multi_status("Paused")
    
    def stop_multiple_downloads(self):
        """Stop multiple downloads"""
        if self.multi_worker:
            self.multi_worker.stop()
            self.multi_log("⏹ Downloads stopped by user")
            self.update_multi_status("Stopped")
    
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
            self.multi_log("⏹ Multiple downloads cancelled by user")

    def on_multi_video_started(self, index, url):
        """Handle when a video download starts"""
        self.multi_log(f"📥 [{index+1}] Starting: {url[:60]}...")
        if hasattr(self, 'multi_progress_dialog'):
            self.multi_progress_dialog.start_video(index, url)
    
    def on_multi_video_completed(self, index, success, message, file_path):
        """Handle when a video download completes"""
        status = "✅" if success else "❌"
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
        self.multi_pause_btn.setText("⏸ Pause")
        
        # Show completion summary
        if stopped:
            self.multi_log(f"⏹ Batch stopped: {completed}/{total} completed, {failed} failed")
            self.update_multi_status(f"Stopped: {completed}/{total} completed")
        else:
            self.multi_log(f"🎉 Batch complete: {completed}/{total} successful, {failed} failed")
            self.update_multi_status(f"Complete: {completed}/{total} successful")
        
        # Show failed URLs if any
        if summary['failed_urls']:
            self.multi_log("❌ Failed URLs:")
            for url in summary['failed_urls']:
                self.multi_log(f"   • {url}")
        
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
                border-radius: 8px;
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
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
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
            app_icon.setText("⬇")
            app_icon.setStyleSheet("font-size: 18px; color: #58a6ff; border: 0px; background: none; outline: 0px;")
        
        # App title
        app_title = QLabel("Video Downloader Tool")
        app_title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        app_title.setFrameStyle(QLabel.Shape.NoFrame)
        app_title.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        app_title.setStyleSheet("color: #ffffff; border: 0px; background: none; outline: 0px;")
        
        left_section.addWidget(app_icon)
        left_section.addWidget(app_title)
        
        # === CENTER: Toolbar Actions ===
        center_section = QHBoxLayout()
        center_section.setSpacing(8)
        
        # Quick action buttons in title bar
        self.tb_paste_btn = self.create_titlebar_btn("📋", "Paste")
        self.tb_paste_btn.clicked.connect(self.paste_url)
        
        self.tb_info_btn = self.create_titlebar_btn("ℹ️", "Info")
        self.tb_info_btn.clicked.connect(self.get_info)
        
        self.tb_download_btn = self.create_titlebar_btn("⬇️", "Download")
        self.tb_download_btn.clicked.connect(self.download)
        
        # Separator
        sep = QFrame()
        sep.setFixedSize(1, 25)
        sep.setStyleSheet("background: #404040; border: none;")
        
        self.tb_folder_btn = self.create_titlebar_btn("📁", "Folder")
        self.tb_folder_btn.clicked.connect(self.open_downloads_folder)
        
        self.tb_settings_btn = self.create_titlebar_btn("⚙️", "Settings")
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
        
        # Status indicator
        self.title_status = QLabel("Ready")
        self.title_status.setFont(QFont("Segoe UI", 9))
        self.title_status.setFixedWidth(220)
        self.title_status.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.title_status.setFrameStyle(QLabel.Shape.NoFrame)
        self.title_status.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.title_status.setStyleSheet("color: #00ff88; border: 0px; background: none; outline: 0px; margin-right: 10px;")
        
        # Window control buttons
        minimize_btn = self.create_window_btn("🗕", "Minimize")
        minimize_btn.clicked.connect(self.showMinimized)
        
        maximize_btn = self.create_window_btn("🗖", "Maximize")
        maximize_btn.clicked.connect(self.toggle_maximize)
        
        close_btn = self.create_window_btn("✕", "Close")
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
                color: #ffffff;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.1);
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
                border-radius: 10px;
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
                border-radius: 10px;
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
                border-radius: 10px;
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
            self.log("📁 Opened downloads folder")
        except Exception as e:
            self.log(f"❌ Failed to open folder: {e}")
    
    def show_settings(self):
        """Show a modern settings dialog"""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QCheckBox
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Settings")
        dialog.setFixedSize(350, 250)
        dialog.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        dialog.setStyleSheet("""
            QDialog {
                background: #2a2a3a;
                color: #ffffff;
                border: 2px solid #404040;
                border-radius: 12px;
            }
            QLabel {
                color: #ffffff;
                font-size: 12px;
                border: none;
            }
        """)
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(20)
        layout.setContentsMargins(25, 25, 25, 25)
        
        # Title
        title = QLabel("Application Settings")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #00ff88; font-size: 14px;")
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
        
        dialog.exec()
        self.log("⚙️ Settings accessed")
    
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
        self.log(f"🔧 update_output_directory called with: '{directory}'")
        self.output.setText(directory)
        self.dl.output_dir = Path(directory)
        
        # Immediately save and verify
        self.settings.setValue("output_directory", directory)
        self.settings.sync()
        
        # Verify what was actually saved
        saved_value = self.settings.value("output_directory", "FAILED")
        self.log(f"🔧 Immediately after save, settings contains: '{saved_value}'")
        
        self.log(f"📁 Output directory updated: {directory}")

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
                f"• Get profile information and download multiple videos\n"
                f"• Or continue to get info for this URL as-is?",
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
                "• facebook.com/watch/?v=VIDEO_ID\n"
                "• facebook.com/USERNAME/videos/VIDEO_ID\n"
                "• fb.watch/VIDEO_ID")
            return
        
        self.log(f"🔍 Getting info for: {url[:60]}...")
        self.start_worker('info', url)
    
    def get_profile_info(self, profile_url):
        """Get information about a profile and show download options"""
        self.log(f"🔍 Getting profile info for: {profile_url[:60]}...")
        
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
            self.log(f"✅ Found {data.get('total_found', 0)} videos in profile: {data.get('profile_name', 'Unknown')}")
            
            # Show profile download dialog
            profile_dialog = ProfileDownloadDialog(self, data)
            if profile_dialog.exec() == QDialog.DialogCode.Accepted:
                settings = profile_dialog.get_download_settings()
                self.start_profile_download(data, settings)
        else:
            error_msg = data if isinstance(data, str) else "Failed to get profile information"
            self.log(f"❌ Profile info failed: {error_msg}")
            QMessageBox.warning(self, "Profile Info Failed", f"Could not get profile information:\n\n{error_msg}")
    
    def start_profile_download(self, profile_data, settings):
        """Start downloading videos from profile"""
        videos = settings['videos']
        max_videos = settings['max_videos']
        
        # Limit videos if specified
        if max_videos and len(videos) > max_videos:
            videos = videos[:max_videos]
        
        # Extract URLs from video data
        video_urls = [video['url'] for video in videos if video.get('url')]
        
        if not video_urls:
            QMessageBox.warning(self, "No Videos", "No valid video URLs found in this profile.")
            return
        
        self.log(f"🚀 Starting download of {len(video_urls)} videos from profile: {profile_data.get('profile_name', 'Unknown')}")
        
        # Use the existing multiple download functionality
        self.start_multiple_download_with_urls(video_urls)
    
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
        
        self.profile_videos_text.clear()
        self.profile_videos_text.append(f"🔍 Getting info for {len(selected_urls)} profile(s)...")
        
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
            
            self.profile_videos_text.append(f"\n📊 Total: {self.profile_info_total_videos} videos from {len(self.profile_info_urls)} profile(s)")
            self.profile_info_btn.setEnabled(True)
            self.profile_download_btn.setEnabled(True)
            
            # Show completion message
            QMessageBox.information(
                self,
                "Profile Info Complete",
                f"✅ Finished getting info for {len(self.profile_info_urls)} profile(s)\n\n"
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
            self.profile_videos_text.append(f"   ✅ {profile_name}: {total_found} videos found")
            self.profile_info_total_videos += total_found
            self.profile_info_results.append(data)
        else:
            error_msg = data if isinstance(data, str) else "Unknown error"
            self.profile_videos_text.append(f"   ❌ Error: {error_msg[:50]}")
        
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
        
        self.profile_videos_text.clear()
        self.profile_videos_text.append(f"🚀 Starting download for {len(selected_urls)} profile(s)...")
        self.profile_progress_text.clear()
        
        # Disable buttons during processing
        self.profile_info_btn.setEnabled(False)
        self.profile_download_btn.setEnabled(False)
        
        # Store profiles to process
        self.pending_profile_urls = selected_urls.copy()
        self.current_profile_index = 0
        self.total_profiles = len(selected_urls)
        self.all_profile_data = []  # Store profile name + videos for subfolder creation
        
        # Show progress dialog for gathering videos
        self.profile_download_dialog = ProgressDialog(self, "Gathering Profile Videos", "info")
        self.profile_download_dialog.status_label.setText(f"Processing 0/{len(selected_urls)} profiles...")
        self.profile_download_dialog.show()
        
        # Start processing first profile
        self.process_next_profile()
    
    def process_next_profile(self):
        """Process the next profile in the queue"""
        if self.current_profile_index >= len(self.pending_profile_urls):
            # Close gathering dialog
            if hasattr(self, 'profile_download_dialog'):
                self.profile_download_dialog.close()
            
            # All profiles processed, now download videos profile by profile
            if self.all_profile_data:
                total_videos = sum(len(p['videos']) for p in self.all_profile_data)
                self.total_profile_videos = total_videos  # Store for progress tracking
                self.profile_videos_completed = 0  # Counter for completed videos
                self.profile_videos_text.append(f"\n📥 Starting download of {total_videos} videos from {len(self.all_profile_data)} profile(s)...")
                
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
                self.profile_videos_text.append("\n❌ No videos found in any profile")
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
        
        self.profile_progress_text.append(f"\n📁 Downloading {len(video_urls)} videos from: {profile_name}")
        
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
        icon_label = QLabel("✅")
        icon_label.setStyleSheet("font-size: 32px;")
        title_label = QLabel("Profile Download Complete!")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #2ea043;")
        title_layout.addWidget(icon_label)
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        layout.addLayout(title_layout)
        
        # Stats
        stats_label = QLabel(
            f"📊 Results:\n"
            f"   • Profiles: {len(self.all_profile_data)}\n"
            f"   • Successful: {self.total_successful}\n"
            f"   • Failed: {self.total_failed}"
        )
        stats_label.setStyleSheet("font-size: 13px; color: #f0f6fc;")
        layout.addWidget(stats_label)
        
        layout.addStretch()
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        open_folder_btn = QPushButton("📂 Open Folder")
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
        self.profile_progress_text.append(f"   ✅ {profile_data['name']}: {successful} downloaded, {failed} failed")
        
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
            f"✅ Download completed!\n\n"
            f"Successful: {successful}\n"
            f"Failed: {failed}\n"
            f"Total: {successful + failed}"
        )
        
        self.profile_status_label.setText(f"Completed: {successful} downloaded, {failed} failed")
    
    def handle_multi_profile_result(self, success, data):
        """Handle result from one profile in multi-profile download"""
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
            
            self.profile_videos_text.append(f"   ✅ {profile_name}: {len(video_urls)} videos added")
        else:
            error_msg = data if isinstance(data, str) else "Unknown error"
            self.profile_videos_text.append(f"   ❌ Error: {error_msg[:50]}")
        
        # Process next profile
        self.current_profile_index += 1
        self.process_next_profile()
    
    def paste_profile_urls(self):
        """Paste multiple profile URLs from clipboard"""
        clipboard_text = QApplication.clipboard().text()
        if clipboard_text.strip():
            added_count, invalid_count, problematic_count = self.profile_url_list_widget.add_urls_from_text(clipboard_text)
            
            if added_count > 0:
                self.profile_videos_text.append(f"✅ Added {added_count} profile URL(s)")
            if invalid_count > 0:
                self.profile_videos_text.append(f"❌ Skipped {invalid_count} invalid URL(s)")
            
            self.update_profile_url_status()
        else:
            self.profile_videos_text.append("⚠ Clipboard is empty")
    
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
                self.profile_videos_text.append(f"❌ No videos found in profile: {profile_name}")
        else:
            error_msg = data if isinstance(data, str) else "Failed to get profile information"
            self.profile_videos_text.clear()
            self.profile_videos_text.append(f"❌ Failed to get profile info:")
            self.profile_videos_text.append(f"Error: {error_msg}")
    
    def start_profile_download_with_settings(self, profile_data, settings):
        """Start downloading videos from profile with custom settings"""
        videos = profile_data.get('videos', [])
        max_videos = settings['max_videos']
        
        # Limit videos if specified
        if max_videos and len(videos) > max_videos:
            videos = videos[:max_videos]
        
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
        self.profile_progress_text.append(f"🚀 Starting download of {len(video_urls)} videos from: {profile_name}")
        self.profile_progress_text.append(f"📁 Saving to: {output_dir}")
        self.profile_progress_text.append("")
        
        # Create download settings for the worker
        download_settings = {
            'quality': settings['quality'],
            'audio': settings['audio'],
            'subtitle': settings['subtitle'],
            'format': settings['format'],
            'convert': settings['convert'],
            'use_caption': True
        }
        
        # Create and show progress dialog
        self.profile_multi_progress_dialog = MultipleProgressDialog(self, len(video_urls))
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
            self.profile_progress_text.append(f"⏹ Profile download stopped: {completed}/{total} completed, {failed} failed")
            self.profile_status_label.setText(f"Stopped: {completed}/{total} completed")
        else:
            self.profile_progress_text.append(f"🎉 Profile download complete: {completed}/{total} successful, {failed} failed")
            self.profile_status_label.setText(f"Complete: {completed}/{total} successful")
        
        # Show modern completion dialog
        dialog = BatchCompleteDialog(self, summary)
        dialog.exec()
    
    def pause_profile_downloads(self):
        """Pause/Resume profile downloads"""
        if hasattr(self, 'profile_multi_worker'):
            if self.profile_multi_worker.paused:
                self.profile_multi_worker.resume()
                self.profile_multi_progress_dialog.pause_btn.setText("⏸ Pause")
                self.profile_status_label.setText("Resuming profile downloads...")
            else:
                self.profile_multi_worker.pause()
                self.profile_multi_progress_dialog.pause_btn.setText("▶ Resume")
                self.profile_status_label.setText("Paused")
    
    def stop_profile_downloads(self):
        """Stop profile downloads"""
        if hasattr(self, 'profile_multi_worker'):
            self.profile_multi_worker.stop()
            self.profile_status_label.setText("Stopping profile downloads...")
            if hasattr(self, 'profile_multi_progress_dialog'):
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
            self.profile_videos_text.append(f"✅ Profile: {profile_name}")
            self.profile_videos_text.append(f"📱 Platform: {platform}")
            self.profile_videos_text.append(f"📹 Found {total_videos} videos")
            
            if total_videos > 0:
                self.profile_videos_text.append("")
                self.profile_videos_text.append("� Cloick 'Download Videos' to start!")
            
            # Show modern info dialog
            info_dialog = ProfileInfoDialog(self, data)
            info_dialog.exec()
        else:
            error_msg = data if isinstance(data, str) else "Failed to get profile information"
            self.profile_videos_text.clear()
            self.profile_videos_text.append(f"❌ Failed to get profile info:")
            self.profile_videos_text.append(f"Error: {error_msg}")
            self.profile_videos_text.append("")
            self.profile_videos_text.append("💡 Tips:")
            self.profile_videos_text.append("• Make sure the profile is public")
            self.profile_videos_text.append("• Check if the URL is correct")
            self.profile_videos_text.append("• Try copying the URL again")
    
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
                    self.profile_videos_text.append("⏹ Download cancelled by user")
            else:
                self.profile_videos_text.clear()
                self.profile_videos_text.append(f"❌ No videos found in profile: {profile_name}")
        else:
            error_msg = data if isinstance(data, str) else "Failed to get profile information"
            self.profile_videos_text.clear()
            self.profile_videos_text.append(f"❌ Failed to get profile info:")
            self.profile_videos_text.append(f"Error: {error_msg}")
    
    def start_multiple_download_with_urls(self, urls):
        """Start multiple downloads with a provided list of URLs"""
        if not urls:
            return
        
        # Set up download settings (use current settings from UI)
        settings = {
            'quality': self.multi_quality.currentText(),
            'audio': self.multi_audio_cb.isChecked(),
            'subtitle': self.multi_subtitle_cb.isChecked(),
            'format': self.multi_format.currentText(),
            'convert': False,
            'use_caption': True
        }
        
        # Set output directory
        self.dl.output_dir = Path(self.multi_output.text() or "downloads")
        self.dl.output_dir.mkdir(exist_ok=True)
        
        # Create and show progress dialog
        self.multi_progress_dialog = MultipleProgressDialog(self, len(urls))
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
        self.update_multi_status(f"Downloading {len(urls)} videos...")
        
        # Update UI state
        self.multi_download_btn.setEnabled(False)
        self.multi_pause_btn.setEnabled(True)
        self.multi_stop_btn.setEnabled(True)
    
    def browse_profile_output(self):
        """Browse for profile output directory"""
        folder = QFileDialog.getExistingDirectory(self, "Select Profile Download Directory")
        if folder:
            self.profile_output.setText(folder)
    
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
    
    def handle_progress_dialog_close(self, result):
        """Handle when progress dialog is closed (including cancel)"""
        if hasattr(self, 'progress_dialog') and self.progress_dialog.cancelled:
            # User cancelled the operation
            if self.worker and self.worker.isRunning():
                self.worker.terminate()  # Stop the worker thread
                self.worker.wait()       # Wait for it to finish
            
            # Reset UI state
            self.dl_btn.setEnabled(True)
            self.info_btn.setEnabled(True)
            self.update_title_status("Cancelled", "#ffaa00")
            self.update_download_status("Operation cancelled by user", "#ffaa00")
            self.log("⏹ Operation cancelled by user")

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
            self.log(f"{'✓' if ok else '✗'} {msg}")
        
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
            self.log(f"🔍 Raw stored directory: '{stored_dir}'")
            
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
            self.log(f"📁 About to set output field to: '{output_dir}'")
            
            # Ensure the output field exists and is ready
            if hasattr(self, 'output') and self.output is not None:
                self.output.setText(output_dir)
                # Force the UI to update
                self.output.repaint()
                # Verify it was actually set
                actual_text = self.output.text()
                self.log(f"📁 Output field now shows: '{actual_text}'")
                self.dl.output_dir = Path(output_dir)
                self.log(f"📁 VideoDownloader output_dir set to: {self.dl.output_dir}")
            else:
                self.log("⚠ Output field not ready yet, will retry later")
            
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
                self.log(f"📁 Multiple download output directory set to: '{multi_output_dir}'")
            
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
                self.log(f"📁 Profile download output directory set to: '{profile_output_dir}'")
            
            # Profile info and progress content - NOT persisted (starts fresh each session)
            if hasattr(self, 'profile_videos_text'):
                self.profile_videos_text.clear()
            if hasattr(self, 'profile_progress_text'):
                self.profile_progress_text.clear()
            
            self.log("✓ Settings loaded from previous session")
            
        except Exception as e:
            self.log(f"⚠ Could not load some settings: {e}")
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
            
            # Sync settings to disk
            self.settings.sync()
            
            if not silent:
                self.log("✓ Settings saved successfully")
            
        except Exception as e:
            if not silent:
                self.log(f"⚠ Could not save some settings: {e}")
    
    def closeEvent(self, event):
        """Handle application close event to save settings"""
        try:
            # Force save all settings before closing
            self.save_settings()
            self.log("🔒 Application closing - settings saved")
        except Exception as e:
            self.log(f"⚠ Error saving settings on close: {e}")
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
            
            self.log("✓ All settings reset to defaults")

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
    app.setApplicationName("Video Downloader Tool")
    
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
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()