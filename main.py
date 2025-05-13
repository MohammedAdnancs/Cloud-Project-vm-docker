import sys
import os
import logging
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout,
    QHBoxLayout, QLabel, QLineEdit, QComboBox, QPushButton, QSpinBox,
    QFileDialog, QTableWidget, QTableWidgetItem, QGroupBox, 
    QMessageBox, QHeaderView, QProgressBar, QSplitter, QToolBar,
    QStatusBar, QAction, QMenu, QSystemTrayIcon, QStyleFactory,
    QFrame
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, pyqtSlot, QSettings, QSize
from PyQt5.QtGui import QIcon, QFont, QPixmap, QColor, QPalette

# Get the absolute path to the script directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
from dialog.settings_dialog import SettingsDialog
from dialog.about_dialog import AboutDialog

# Helper function to get icon path
def get_icon_path(icon_name):
    print (os.path.join(SCRIPT_DIR, "resources", "icons", icon_name))
    return os.path.join(SCRIPT_DIR, "resources", "icons", icon_name)

from services.disk_manager import DiskManager
from services.vm_manager import VMManager

# Setup logging
os.makedirs('data', exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
# Create file handler
file_handler = logging.FileHandler('data/cloud_vm_gui.log')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

# Get logger
logger = logging.getLogger('cloud_vm_gui')
logger.addHandler(file_handler)

class WorkerThread(QThread):
    """Worker thread for long operations"""
    finished = pyqtSignal(bool, str)
    progress = pyqtSignal(int)
    
    def __init__(self, task, *args, **kwargs):
        super().__init__()
        self.task = task
        self.args = args
        self.kwargs = kwargs
    
    def run(self):
        try:
            # Simulate progress for operations
            for i in range(0, 101, 10):
                self.progress.emit(i)
                if i < 100:  # Don't sleep on the last iteration
                    self.msleep(100)
            
            # Execute the actual task
            result = self.task(*self.args, **self.kwargs)
            self.finished.emit(*result)
        except Exception as e:
            logger.error(f"Error in worker thread: {str(e)}")
            self.finished.emit(False, f"Operation failed: {str(e)}")

class DiskManagerTab(QWidget):
    """Tab for managing virtual disks"""
    
    # Define a signal for notifying when disks change
    disks_changed = pyqtSignal()
    def __init__(self, disk_manager):
        super().__init__()
        self.disk_manager = disk_manager
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Create disk section
        create_group = QGroupBox("Create Virtual Disk")
        create_layout = QVBoxLayout()
        create_layout.setSpacing(15)
        
        form_layout = QHBoxLayout()
        form_layout.setSpacing(20)
        
        # Disk name input
        name_layout = QVBoxLayout()
        name_layout.setSpacing(8)
        name_label = QLabel("Disk Name:")
        name_label.setStyleSheet("font-weight: bold;")
        name_layout.addWidget(name_label)
        self.disk_name_input = QLineEdit()
        self.disk_name_input.setPlaceholderText("Enter disk name")
        name_layout.addWidget(self.disk_name_input)
        form_layout.addLayout(name_layout)
        
        # Disk size input
        size_layout = QVBoxLayout()
        size_layout.setSpacing(8)
        size_label = QLabel("Size:")
        size_label.setStyleSheet("font-weight: bold;")
        size_layout.addWidget(size_label)
        size_input_layout = QHBoxLayout()
        self.disk_size_input = QSpinBox()
        self.disk_size_input.setRange(1, 10000)
        self.disk_size_input.setValue(10)
        size_input_layout.addWidget(self.disk_size_input)
        self.disk_size_unit = QComboBox()
        self.disk_size_unit.addItems(["MB", "GB"])
        self.disk_size_unit.setCurrentIndex(1)  # Default to GB
        size_input_layout.addWidget(self.disk_size_unit)
        size_layout.addLayout(size_input_layout)
        form_layout.addLayout(size_layout)
        
        # Disk format selection
        format_layout = QVBoxLayout()
        format_layout.setSpacing(8)
        format_label = QLabel("Format:")
        format_label.setStyleSheet("font-weight: bold;")
        format_layout.addWidget(format_label)
        self.disk_format_select = QComboBox()
        self.disk_format_select.addItems(["qcow2", "raw", "vmdk", "vdi", "vhd"])
        format_layout.addWidget(self.disk_format_select)
        form_layout.addLayout(format_layout)
        
        create_layout.addLayout(form_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        create_layout.addWidget(self.progress_bar)
          # Create button
        button_layout = QHBoxLayout()
        self.create_button = QPushButton("Create Disk")
        self.create_button.setIcon(QIcon(get_icon_path("disk.png")))
        self.create_button.setIconSize(QSize(20, 20))
        self.create_button.clicked.connect(self.create_disk)
        button_layout.addStretch()
        button_layout.addWidget(self.create_button)
        button_layout.addStretch()
        create_layout.addLayout(button_layout)
        
        create_group.setLayout(create_layout)
        layout.addWidget(create_group)
        
        # List of disks
        list_group = QGroupBox("Available Disks")
        list_layout = QVBoxLayout()
        self.disks_table = QTableWidget(0, 4)        
        self.disks_table.setHorizontalHeaderLabels(["Name", "Size", "Format", "Actions"])
        self.disks_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        list_layout.addWidget(self.disks_table)
        
        refresh_button = QPushButton("Refresh List")
        refresh_button.setIcon(QIcon(get_icon_path("refresh.png")))
        refresh_button.clicked.connect(self.refresh_disks)
        refresh_button.setStyleSheet("QPushButton { color: white; background-color: #2a82da; padding: 6px 12px; font-weight: bold; }")
        list_layout.addWidget(refresh_button)
        
        list_group.setLayout(list_layout)
        layout.addWidget(list_group)
        
        self.setLayout(layout)
        
        # Initial load
        self.refresh_disks()
    
    def create_disk(self):
        """Create a new virtual disk"""
        name = self.disk_name_input.text().strip()
        size = str(self.disk_size_input.value())
        unit = self.disk_size_unit.currentText()
        fmt = self.disk_format_select.currentText()
        
        if not name:
            QMessageBox.warning(self, "Error", "Please enter a disk name")
            return
        
        # Convert size to QEMU format (e.g. 10G, 500M)
        size_str = size + unit[0]
        
        # Disable UI elements during operation
        self.create_button.setEnabled(False)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        
        # Create disk in a worker thread
        self.worker = WorkerThread(self.disk_manager.create_disk, name, size_str, fmt)
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.on_disk_created)
        self.worker.start()
    def update_progress(self, value):
        self.progress_bar.setValue(value)
    
    def on_disk_created(self, success, message):
        """Handle disk creation result"""
        self.create_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        if success:
            QMessageBox.information(self, "Success", message)
            self.disk_name_input.clear()
            self.disk_size_input.setValue(10)
            self.refresh_disks()
            # Emit the signal to notify that disks have changed
            self.disks_changed.emit()
        else:            QMessageBox.warning(self, "Error", message)
    
    def refresh_disks(self):
        """Refresh the list of disks"""
        disks = self.disk_manager.list_disks()
        
        self.disks_table.setRowCount(0)
        
        row = 0
        for name, info in disks.items():
            self.disks_table.insertRow(row)
            
            # Name
            self.disks_table.setItem(row, 0, QTableWidgetItem(name))
            
            # Size
            size_gb = info['size'] / (1024**3)
            size_text = f"{size_gb:.2f} GB" if size_gb >= 1 else f"{info['size'] / (1024**2):.2f} MB"
            self.disks_table.setItem(row, 1, QTableWidgetItem(size_text))
            
            # Format
            self.disks_table.setItem(row, 2, QTableWidgetItem(info.get('format', 'unknown')))
              # Delete action
            delete_btn = QPushButton("Delete")
            delete_btn.setStyleSheet("QPushButton { color: white; font-weight: bold; }")  # Force white text
            delete_btn.clicked.connect(lambda checked, disk_name=name: self.delete_disk(disk_name))
            self.disks_table.setCellWidget(row, 3, delete_btn)
            row += 1
        
        # Emit the signal to notify that disks have changed
        self.disks_changed.emit()
    
    def delete_disk(self, disk_name):
        """Delete a virtual disk"""
        reply = QMessageBox.question(
            self, 'Confirm Deletion',
            f"Are you sure you want to delete disk '{disk_name}'?\n\nThis action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            success, message = self.disk_manager.delete_disk(disk_name)
            if success:
                QMessageBox.information(self, "Success", message)
                self.refresh_disks()
                # Emit the signal to notify that disks have changed
                self.disks_changed.emit()
            else:
                QMessageBox.warning(self, "Error", message)

class VMManagerTab(QWidget):
    """Tab for managing virtual machines"""
    
    def __init__(self, vm_manager, disk_manager):
        super().__init__()
        self.vm_manager = vm_manager
        self.disk_manager = disk_manager
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()

        # Create VM section
        create_group = QGroupBox("Create Virtual Machine")
        create_layout = QVBoxLayout()
        create_layout.setSpacing(15)
        form_layout = QVBoxLayout()
        form_layout.setSpacing(10)
        
        # VM name input
        name_layout = QHBoxLayout()
        name_layout.setSpacing(0)
        name_layout.setContentsMargins(0, 0, 0, 0)
        name_label = QLabel("VM Name:")
        name_label.setStyleSheet("font-weight: bold;")
        name_label.setFixedWidth(60)
        self.vm_name_input = QLineEdit()
        self.vm_name_input.setPlaceholderText("Enter VM name")
        self.vm_name_input.setFixedWidth(150)
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.vm_name_input)
        name_layout.addStretch()
        form_layout.addLayout(name_layout)
        
        # Memory input
        memory_layout = QHBoxLayout()
        memory_layout.setSpacing(0)
        memory_layout.setContentsMargins(0, 0, 0, 0)
        memory_label = QLabel("Memory (MB):")
        memory_label.setStyleSheet("font-weight: bold;")
        memory_label.setFixedWidth(90)
        memory_layout.addWidget(memory_label)
        self.vm_memory_input = QSpinBox()
        self.vm_memory_input.setRange(128, 32768)
        self.vm_memory_input.setValue(1024)
        self.vm_memory_input.setSingleStep(128)
        self.vm_memory_input.setFixedWidth(120)
        memory_layout.addWidget(self.vm_memory_input)
        memory_layout.addStretch()
        form_layout.addLayout(memory_layout)
        
        # CPU input
        cpu_layout = QHBoxLayout()
        cpu_layout.setSpacing(0)
        cpu_layout.setContentsMargins(0, 0, 0, 0)
        cpu_label = QLabel("CPUs:")
        cpu_label.setStyleSheet("font-weight: bold;")
        cpu_label.setFixedWidth(40)
        cpu_layout.addWidget(cpu_label)
        self.vm_cpu_input = QSpinBox()
        
        self.vm_cpu_input.setRange(1, 16)
        self.vm_cpu_input.setValue(1)
        self.vm_cpu_input.setFixedWidth(70)
        cpu_layout.addWidget(self.vm_cpu_input)
        cpu_layout.addStretch()
        form_layout.addLayout(cpu_layout)
        
        # Disk selection
        disk_layout = QHBoxLayout()
        disk_layout.setSpacing(0)
        disk_layout.setContentsMargins(0, 0, 0, 0)
        disk_label = QLabel("Disk:")
        disk_label.setStyleSheet("font-weight: bold;")
        disk_label.setFixedWidth(40)
        disk_layout.addWidget(disk_label)
        self.vm_disk_select = QComboBox()
        self.vm_disk_select.setFixedWidth(180)
        disk_layout.addWidget(self.vm_disk_select)
        disk_layout.addStretch()
        form_layout.addLayout(disk_layout)

        # ISO selection     
        iso_layout = QHBoxLayout()
        iso_layout.setSpacing(0)
        iso_layout.setContentsMargins(0, 0, 0, 0)
        iso_label = QLabel("Boot ISO:")
        iso_label.setStyleSheet("font-weight: bold;")
        iso_label.setFixedWidth(60)
        iso_layout.addWidget(iso_label)
        self.vm_iso_select = QComboBox()
        self.vm_iso_select.addItem("None")
        self.vm_iso_select.setFixedWidth(180)
        iso_layout.addWidget(self.vm_iso_select)
        iso_layout.addSpacing(10)
        self.vm_iso_browse = QPushButton("Browse...")
        self.vm_iso_browse.setIcon(QIcon(get_icon_path("refresh.png")))
        self.vm_iso_browse.clicked.connect(self.browse_iso)
        iso_layout.addWidget(self.vm_iso_browse)
        iso_layout.addStretch()
        form_layout.addLayout(iso_layout)
        create_layout.addLayout(form_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        create_layout.addWidget(self.progress_bar)
          # Create button
        button_layout = QHBoxLayout()
        self.create_button = QPushButton("Create VM")
        self.create_button.setIcon(QIcon(get_icon_path("vm.png")))
        self.create_button.setIconSize(QSize(20, 20))
        self.create_button.clicked.connect(self.create_vm)
        button_layout.addStretch()
        button_layout.addWidget(self.create_button)
        button_layout.addStretch()
        create_layout.addLayout(button_layout)
        
        create_group.setLayout(create_layout)
        layout.addWidget(create_group)
        
        # List of VMs
        list_group = QGroupBox("Available Virtual Machines")
        list_layout = QVBoxLayout()
        
        self.vms_table = QTableWidget(0, 5)        
        self.vms_table.setHorizontalHeaderLabels(["Name", "Memory", "CPUs", "Disk", "Actions"])
        self.vms_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        list_layout.addWidget(self.vms_table)
        refresh_button = QPushButton("Refresh List")
        refresh_button.setIcon(QIcon(get_icon_path("refresh.png")))
        refresh_button.clicked.connect(self.refresh_vms)
        list_layout.addWidget(refresh_button)
        
        list_group.setLayout(list_layout)
        layout.addWidget(list_group)
        self.setLayout(layout)
        
        # Initial load
        self.refresh_disks()
        self.refresh_isos()
        self.refresh_vms()
    
    def refresh_disks(self):
        """Refresh the list of available disks"""
        self.vm_disk_select.clear()
        
        disks = self.disk_manager.list_disks()
        
        if not disks:
            # Add a placeholder item to indicate no disks are available
            self.vm_disk_select.addItem("No disks available")
            self.vm_disk_select.setEnabled(False)
        else:
            self.vm_disk_select.setEnabled(True)
            for name in disks:
                self.vm_disk_select.addItem(name)
    
    def refresh_isos(self):
        """Refresh the list of available ISO files"""
        self.vm_iso_select.clear()
        self.vm_iso_select.addItem("None")
        
        for iso_path in self.vm_manager.list_isos():
            self.vm_iso_select.addItem(os.path.basename(iso_path), iso_path)
    
    def browse_iso(self):
        """Browse for an ISO file"""
        file_dialog = QFileDialog()
        iso_path, _ = file_dialog.getOpenFileName(
            self, "Select ISO File", "", "ISO Files (*.iso);;All Files (*)"
        )
        
        if iso_path:
            # Copy the ISO to the ISOs directory if it's not already there
            filename = os.path.basename(iso_path)
            dest_path = os.path.join(self.vm_manager.isos_dir, filename)
            
            if iso_path != dest_path:
                import shutil
                try:
                    os.makedirs(self.vm_manager.isos_dir, exist_ok=True)
                    shutil.copy2(iso_path, dest_path)
                    QMessageBox.information(self, "ISO Imported", f"ISO file '{filename}' has been imported.")
                    self.refresh_isos()
                    
                    # Select the newly added ISO
                    index = self.vm_iso_select.findText(filename)
                    if index >= 0:
                        self.vm_iso_select.setCurrentIndex(index)
                    
                except Exception as e:
                    QMessageBox.warning(self, "Error", f"Failed to import ISO: {str(e)}")
            else:
                # If the ISO is already in the right place, just select it
                index = self.vm_iso_select.findText(filename)
                if index >= 0:
                    self.vm_iso_select.setCurrentIndex(index)
    
    def create_vm(self):
        """Create a new virtual machine"""
        name = self.vm_name_input.text().strip()
        memory = self.vm_memory_input.value()
        cpus = self.vm_cpu_input.value()
        
        if not name:
            QMessageBox.warning(self, "Error", "Please enter a VM name")
            return
        
        if self.vm_disk_select.count() == 0:
            QMessageBox.warning(self, "Error", "No disks available. Please create a disk first.")
            return
        
        disk_name = self.vm_disk_select.currentText()
        
        # Get ISO path if selected
        iso_path = None
        if self.vm_iso_select.currentIndex() > 0:  # Not "None"
            iso_path = self.vm_iso_select.currentData()
        
        # Disable UI elements during operation
        self.create_button.setEnabled(False)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        
        # Create VM in a worker thread
        self.worker = WorkerThread(self.vm_manager.create_vm, name, memory, cpus, disk_name, iso_path)
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.on_vm_created)
        self.worker.start()
    
    def update_progress(self, value):
        self.progress_bar.setValue(value)
    
    def on_vm_created(self, success, message):
        """Handle VM creation result"""
        self.create_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        if success:
            QMessageBox.information(self, "Success", message)
            self.vm_name_input.clear()
            self.vm_memory_input.setValue(1024)
            self.vm_cpu_input.setValue(1)
            self.vm_iso_select.setCurrentIndex(0)  # Reset to "None"
            self.refresh_vms()
        else:
            QMessageBox.warning(self, "Error", message)
    
    def refresh_vms(self):
        """Refresh the list of VMs"""
        vms = self.vm_manager.list_vms()
        
        self.vms_table.setRowCount(0)
        
        row = 0
        for name, info in vms.items():
            self.vms_table.insertRow(row)
            
            # Name
            self.vms_table.setItem(row, 0, QTableWidgetItem(name))
            
            # Memory
            self.vms_table.setItem(row, 1, QTableWidgetItem(f"{info.get('memory', 0)} MB"))
            
            # CPUs
            self.vms_table.setItem(row, 2, QTableWidgetItem(str(info.get('cpus', 1))))
            
            # Disk
            disk_name = "unknown"
            for disk_name, disk_info in self.disk_manager.list_disks().items():
                if disk_info['path'] == info.get('disk', ''):
                    break
            self.vms_table.setItem(row, 3, QTableWidgetItem(disk_name))
            
            # Actions
            actions_widget = QWidget()
            actions_layout = QHBoxLayout()
            actions_layout.setContentsMargins(0, 0, 0, 0)
            actions_layout.setSpacing(8)  # Add space between buttons

            # Common button style
            button_style = """
                QPushButton {
                    background-color: #0078D7;
                    color: white;
                    font-weight: bold;
                    border: none;
                    padding: 5px 12px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #005A9E;
                }
                QPushButton:pressed {
                    background-color: #003E73;
                }
            """

            start_btn = QPushButton("Start")
            start_btn.setStyleSheet(button_style)
            start_btn.clicked.connect(lambda checked, vm_name=name: self.start_vm(vm_name))

            delete_btn = QPushButton("Delete")
            delete_btn.setStyleSheet(button_style.replace("#0078D7", "#D83B01").replace("#005A9E", "#A42600").replace("#003E73", "#750B1C"))
            delete_btn.clicked.connect(lambda checked, vm_name=name: self.delete_vm(vm_name))

            actions_layout.addWidget(start_btn)
            actions_layout.addWidget(delete_btn)
            actions_widget.setLayout(actions_layout)
            self.vms_table.setColumnWidth(4, 250)
            self.vms_table.setCellWidget(row, 4, actions_widget)

            
            row += 1
    
    def start_vm(self, vm_name):
        """Start a virtual machine"""
        reply = QMessageBox.question(
            self, 'Start Virtual Machine',
            f"Do you want to start VM '{vm_name}'?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
        )
        
        if reply == QMessageBox.Yes:
            # Start VM in a worker thread
            self.worker = WorkerThread(self.vm_manager.start_vm, vm_name)
            self.worker.finished.connect(lambda success, message: self.on_vm_started(success, message, vm_name))
            self.worker.start()
            
            # Show a simple "starting" message
            QMessageBox.information(self, "Starting VM", f"Starting VM '{vm_name}'...")
    
    def on_vm_started(self, success, message, vm_name):
        """Handle VM start result"""
        if not success:
            QMessageBox.warning(self, "Error", f"Failed to start VM '{vm_name}': {message}")
    
    def delete_vm(self, vm_name):
        """Delete a virtual machine"""
        reply = QMessageBox.question(
            self, 'Confirm Deletion',
            f"Are you sure you want to delete VM '{vm_name}'?\n\nThis will only delete the VM configuration, not the disk.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            success, message = self.vm_manager.delete_vm(vm_name)
            if success:
                QMessageBox.information(self, "Success", message)
                self.refresh_vms()
            else:
                QMessageBox.warning(self, "Error", message)

class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        self.settings = QSettings("CloudVMManager", "CloudVM")
        self.disk_manager = DiskManager()
        self.vm_manager = VMManager()
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("Cloud VM Manager")
        self.setGeometry(100, 100, 900, 700)
        
        # Create toolbar
        self.create_toolbar()
        
        # Create status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Ready")
          # Create tabs
        self.tabs = QTabWidget()        # Disk manager tab
        self.disk_tab = DiskManagerTab(self.disk_manager)
        self.tabs.addTab(self.disk_tab, QIcon(get_icon_path("disk.png")), "Virtual Disks")
        
        # VM manager tab
        self.vm_tab = VMManagerTab(self.vm_manager, self.disk_manager)
        self.tabs.addTab(self.vm_tab, QIcon(get_icon_path("vm.png")), "Virtual Machines")
        
        # Connect the disks_changed signal to the VM tab's refresh_disks method
        self.disk_tab.disks_changed.connect(self.vm_tab.refresh_disks)
        
        # Set central widget
        self.setCentralWidget(self.tabs)
    
    def create_toolbar(self):
        """Create the toolbar with actions"""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setIconSize(QSize(24, 24))
        toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)  # Show text beside icons
        self.addToolBar(toolbar)
        
        # Refresh action
        refresh_icon = QIcon("refresh.png")
        refresh_action = QAction(refresh_icon, "Refresh", self)
        refresh_action.setStatusTip("Refresh disk and VM lists")
        refresh_action.triggered.connect(self.refresh_all)
        toolbar.addAction(refresh_action)
        
        toolbar.addSeparator()
          # Create disk action
        disk_icon = QIcon(get_icon_path("disk.png"))
        create_disk_action = QAction(disk_icon, "Create Disk", self)
        create_disk_action.setStatusTip("Create a new virtual disk")
        create_disk_action.triggered.connect(self.show_create_disk)
        toolbar.addAction(create_disk_action)
          # Create VM action
        vm_icon = QIcon(get_icon_path("vm.png"))
        create_vm_action = QAction(vm_icon, "Create VM", self)
        create_vm_action.setStatusTip("Create a new virtual machine")
        create_vm_action.triggered.connect(self.show_create_vm)
        toolbar.addAction(create_vm_action)
        
        toolbar.addSeparator()
          # Settings action
        settings_icon = QIcon(get_icon_path("settings.png"))
        settings_action = QAction(settings_icon, "Settings", self)
        settings_action.setStatusTip("Configure application settings")
        settings_action.triggered.connect(self.show_settings)
        toolbar.addAction(settings_action)
        
        # Create menu bar
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("&File")
        file_menu.addAction(refresh_action)
        file_menu.addSeparator()
        file_menu.addAction(settings_action)
        file_menu.addSeparator()
        
        exit_action = QAction("E&xit", self)
        exit_action.setStatusTip("Exit the application")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Disk menu
        disk_menu = menubar.addMenu("&Disks")
        disk_menu.addAction(create_disk_action)
        
        # Import disk action
        import_disk_action = QAction("Import Disk...", self)
        import_disk_action.setStatusTip("Import an existing disk file")
        import_disk_action.triggered.connect(self.import_disk)
        disk_menu.addAction(import_disk_action)
        
        # VM menu
        vm_menu = menubar.addMenu("&Virtual Machines")
        vm_menu.addAction(create_vm_action)
        
        # Import ISO action
        import_iso_action = QAction("Import ISO...", self)
        import_iso_action.setStatusTip("Import an ISO image")
        import_iso_action.triggered.connect(self.import_iso)
        vm_menu.addAction(import_iso_action)
        
        # Help menu
        help_menu = menubar.addMenu("&Help")
        
        about_action = QAction("&About", self)
        about_action.setStatusTip("About Cloud VM Manager")
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def refresh_all(self):
        """Refresh all components"""
        self.disk_tab.refresh_disks()
        self.vm_tab.refresh_vms()
        self.vm_tab.refresh_disks()
        self.vm_tab.refresh_isos()
        self.statusBar.showMessage("Refreshed all data", 3000)
    
    def show_create_disk(self):
        """Switch to the disk tab and focus on the create disk form"""
        self.tabs.setCurrentIndex(0)  # Switch to disk tab
        self.disk_tab.disk_name_input.setFocus()
    
    def show_create_vm(self):
        """Switch to the VM tab and focus on the create VM form"""
        self.tabs.setCurrentIndex(1)  # Switch to VM tab
        self.vm_tab.vm_name_input.setFocus()
    
    def show_settings(self):
        """Show the settings dialog"""
        dialog = SettingsDialog(self)
        dialog.exec_()
    
    def import_disk(self):
        """Import an existing disk file"""
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(
            self, "Import Disk File", "", 
            "All Supported Formats (*.qcow2 *.raw *.vmdk *.vdi *.vhd);;QCOW2 Files (*.qcow2);;Raw Files (*.raw);;VMDK Files (*.vmdk);;VDI Files (*.vdi);;VHD Files (*.vhd);;All Files (*)"
        )
        
        if file_path:
            # Get the base name without extension as suggested disk name
            basename = os.path.basename(file_path)
            suggested_name = os.path.splitext(basename)[0]
            
            # Prompt for a name
            disk_name, ok = QMessageBox.question(
                self, 
                "Import Disk", 
                f"Would you like to import disk '{basename}' with the name '{suggested_name}'?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            
            if ok == QMessageBox.Yes:
                import shutil
                target_path = os.path.join(self.disk_manager.disks_dir, basename)
                
                try:                    # Copy the file to the disks directory
                    shutil.copy2(file_path, target_path)
                    
                    # Force a refresh of the disks
                    self.disk_manager._validate_registry()
                    self.disk_tab.refresh_disks()
                    
                    # Signal VM tab to refresh disks as well
                    self.disk_tab.disks_changed.emit()
                    
                    QMessageBox.information(self, "Success", f"Disk '{basename}' imported successfully.")
                    self.statusBar.showMessage(f"Imported disk: {basename}", 3000)
                except Exception as e:                    QMessageBox.warning(self, "Error", f"Failed to import disk: {str(e)}")
    
    def import_iso(self):
        """Import an ISO image"""
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(
            self, "Import ISO File", "", "ISO Files (*.iso);;All Files (*)"
        )
        
        if file_path:
            basename = os.path.basename(file_path)
            target_path = os.path.join(self.vm_manager.isos_dir, basename)
            
            try:
                # Create ISOs directory if it doesn't exist
                os.makedirs(self.vm_manager.isos_dir, exist_ok=True)
                
                # Copy the ISO file
                import shutil
                shutil.copy2(file_path, target_path)
                
                # Refresh the ISO list
                self.vm_tab.refresh_isos()
                
                QMessageBox.information(self, "Success", f"ISO '{basename}' imported successfully.")
                self.statusBar.showMessage(f"Imported ISO: {basename}", 3000)
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to import ISO: {str(e)}")
    
    def show_about(self):
        """Show about dialog"""
        dialog = AboutDialog(self)
        dialog.exec_()

def apply_stylesheet(app):
    """Apply a modern stylesheet to the application"""
    # Import styles from our new styles module
    from resources.styles_new import get_dark_palette, get_stylesheet
    
    # Set fusion style as base
    app.setStyle('Fusion')
    
    # Apply custom dark palette
    app.setPalette(get_dark_palette())
    
    # Apply custom stylesheet
    app.setStyleSheet(get_stylesheet())

def main():
    app = QApplication(sys.argv)
    
    # Apply modern styling
    apply_stylesheet(app)
      # Set application icon
    app_icon = QIcon(get_icon_path("app_icon.png"))
    app.setWindowIcon(app_icon)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()