import os
import sys
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QTextBrowser
from PyQt5.QtGui import QPixmap, QFont
from PyQt5.QtCore import Qt, QSize

class AboutDialog(QDialog):
    """Dialog displaying information about the application"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("About Cloud VM Manager")
        self.setMinimumSize(600, 400)
        
        layout = QVBoxLayout()
        
        # Header section
        header_layout = QHBoxLayout()
          # App logo
        logo_label = QLabel()
        logo_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                'resources', 'icons', 'app_logo.png')
        logo_pixmap = QPixmap(logo_path)
        if not logo_pixmap.isNull():
            logo_label.setPixmap(logo_pixmap.scaled(QSize(96, 96), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            # Text instead of logo
            logo_label.setText("VM")
            logo_label.setStyleSheet("font-size: 36px; font-weight: bold; color: #336699; background-color: #e0e0e0; padding: 10px;")
            logo_label.setAlignment(Qt.AlignCenter)
            logo_label.setFixedSize(64, 64)
        
        header_layout.addWidget(logo_label)
        
        # App name and version
        title_layout = QVBoxLayout()
        
        app_name = QLabel("Cloud VM Manager")
        app_name.setFont(QFont("", 16, QFont.Bold))
        title_layout.addWidget(app_name)
        
        version = QLabel("Version 1.0.0")
        version.setFont(QFont("", 10))
        title_layout.addWidget(version)
        
        header_layout.addLayout(title_layout)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Description
        description = QTextBrowser()
        description.setReadOnly(True)
        description.setOpenExternalLinks(True)
        description.setHtml("""
        <h3>Cloud VM Manager</h3>
        <p>A user-friendly graphical interface for managing QEMU virtual machines.</p>
        
        <h4>Features:</h4>
        <ul>
            <li>Create and manage virtual disks in various formats (qcow2, raw, vmdk, vdi, vhd)</li>
            <li>Create and run virtual machines with customizable memory and CPU settings</li>
            <li>Boot VMs from ISO images for OS installation</li>
            <li>Import existing disk images and ISO files</li>
        </ul>
        
        <h4>Requirements:</h4>
        <ul>
            <li>Python 3.6 or higher</li>
            <li>QEMU (latest version recommended)</li>
            <li>PyQt5</li>
        </ul>
        
        <h4>External Resources:</h4>
        <p>
            <a href="https://www.qemu.org/">QEMU</a> - The open source machine emulator and virtualizer<br>
            <a href="https://www.python.org/">Python</a> - Programming language<br>
            <a href="https://www.riverbankcomputing.com/software/pyqt/">PyQt</a> - Python bindings for Qt
        </p>
        
        <p>&copy; 2023 Cloud VM Manager Team</p>
        """)
        
        layout.addWidget(description)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.accept)
        button_layout.addWidget(ok_button)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
