"""
Style definitions for the Cloud VM Manager application.
Contains the dark theme stylesheet and palette settings.
"""

from PyQt5.QtGui import QPalette, QColor
from PyQt5.QtCore import Qt

def get_dark_palette():
    """Create and return a dark palette for the application."""
    palette = QPalette()
    
    # Set window colors
    palette.setColor(QPalette.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.WindowText, Qt.white)
    
    # Set widget colors
    palette.setColor(QPalette.Base, QColor(25, 25, 25))
    palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.Text, Qt.white)
    palette.setColor(QPalette.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ButtonText, Qt.white)
    
    # Set highlight colors
    palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.HighlightedText, Qt.white)
    
    # Set disabled colors
    palette.setColor(QPalette.Disabled, QPalette.Text, QColor(150, 150, 150))
    palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(150, 150, 150))
    
    return palette

def get_stylesheet():
    """Return the stylesheet for the application."""
    return """
    QMainWindow, QDialog {
        background-color: #353535;
    }
    
    QTabWidget::pane {
        border: 1px solid #444;
        border-radius: 3px;
    }
    
    QTabBar::tab {
        background-color: #2a2a2a;
        color: #b1b1b1;
        padding: 8px 15px;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
    }
    
    QTabBar::tab:selected {
        background-color: #3a3a3a;
        color: white;
    }
    
    QGroupBox {
        background-color: #2d2d2d;
        border: 1px solid #444;
        border-radius: 3px;
        margin-top: 12px;
        font-weight: bold;
    }
    
    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: 10px;
        padding: 0 3px;
    }
    
    /* Button styling */
    QPushButton {
        background-color: #2a82da;
        color: white;
        border: 1px solid #1c6ab7;
        border-radius: 4px;
        padding: 6px 12px;
        min-width: 80px;
        font-weight: bold;
        outline: none;
    }


    QPushButton:hover {
        background-color: #3294e6;
        border: 1px solid #2a82da;
    }
    
    QPushButton:pressed {
        background-color: #2372c0;
    }
    
    QPushButton:disabled {
        background-color: #555;
        color: #888;
    }
    
    /* Make table buttons more visible */
    QTableWidget QPushButton {
        background-color: #2a82da;
        color: white;
        border: 1px solid #1c6ab7;
        border-radius: 3px;
        padding: 4px 8px;
        min-width: 60px;
        font-weight: bold;
        text-align: center;
    }
    
    /* Text input controls */
    QLineEdit, QComboBox {
        background-color: #1e1e1e;
        color: white;
        padding: 8px;
    }

    QSpinBox{
        padding: 5px;
        background-color: #1e1e1e;
    }
    
    QTableWidget {
        gridline-color: #353535;
        background-color: #1e1e1e;
        color: white;
        border: 1px solid #444;
        border-radius: 3px;
    }
    
    QHeaderView::section {
        background-color: #2a2a2a;
        color: white;
        padding: 5px;
        border: 1px solid #444;
    }
    
    QProgressBar {
        border: 1px solid #444;
        border-radius: 3px;
        background-color: #1e1e1e;
        text-align: center;
        color: white;
    }
    
    QProgressBar::chunk {
        background-color: #2a82da;
        width: 10px;
        margin: 0.5px;
    }
    
    QScrollBar:vertical {
        border: none;
        background-color: #2a2a2a;
        width: 10px;
        margin: 15px 0 15px 0;
    }
    
    QScrollBar::handle:vertical {
        background-color: #5c5c5c;
        min-height: 30px;
        border-radius: 5px;
    }
    
    QScrollBar::handle:vertical:hover {
        background-color: #7a7a7a;
    }
    """
