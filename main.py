import sys
import os
import logging
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout,
    QHBoxLayout, QLabel, QLineEdit, QComboBox, QPushButton, QSpinBox,
    QFileDialog, QTableWidget, QTableWidgetItem, QGroupBox, 
    QMessageBox, QHeaderView, QProgressBar, QSplitter, QToolBar,
    QStatusBar, QAction, QMenu, QSystemTrayIcon, QStyleFactory,
    QFrame, QTextEdit, QRadioButton, QCheckBox, QInputDialog, QDialog
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
from services.docker_manager import DockerManager

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
        """Create a new virtual disk with validation"""
        name = self.disk_name_input.text().strip()
        size = str(self.disk_size_input.value())
        unit = self.disk_size_unit.currentText()
        fmt = self.disk_format_select.currentText()
        
        # Client-side validation
        if not name:
            QMessageBox.warning(self, "Error", "Please enter a disk name")
            self.disk_name_input.setFocus()
            return
            
        # Check for invalid characters in disk name
        import re
        if not re.match(r'^[a-zA-Z0-9_\-\.]+$', name):
            QMessageBox.warning(self, "Error", "Disk name can only contain letters, numbers, underscores, hyphens, and periods")
            self.disk_name_input.setFocus()
            return
            
        # Validate size
        if self.disk_size_input.value() <= 0:
            QMessageBox.warning(self, "Error", "Disk size must be greater than zero")
            self.disk_size_input.setFocus()
            return
            
        # Set reasonable upper limits based on unit to prevent UI errors
        max_sizes = {'MB': 1024*10, 'GB': 1024, 'TB': 64}
        current_unit = self.disk_size_unit.currentText()
        if self.disk_size_input.value() > max_sizes.get(current_unit, 1024):
            QMessageBox.warning(
                self, 
                "Large Disk Size", 
                f"The disk size of {size}{unit[0]} exceeds recommended maximum of {max_sizes[current_unit]}{unit[0]}.\n\n"
                "Are you sure you want to create this disk? It might fail or consume too much space.",
                QMessageBox.Yes | QMessageBox.No
            ) 
            if QMessageBox.No:
                self.disk_size_input.setFocus()
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
        """Create a new virtual machine with validation"""
        name = self.vm_name_input.text().strip()
        memory = self.vm_memory_input.value()
        cpus = self.vm_cpu_input.value()
        
        # Client-side validation
        if not name:
            QMessageBox.warning(self, "Error", "Please enter a VM name")
            self.vm_name_input.setFocus()
            return
            
        # Check for invalid characters in VM name
        import re
        if not re.match(r'^[a-zA-Z0-9_\-\.]+$', name):
            QMessageBox.warning(self, "Error", "VM name can only contain letters, numbers, underscores, hyphens, and periods")
            self.vm_name_input.setFocus()
            return
        
        # Validate memory and CPU
        if memory <= 0:
            QMessageBox.warning(self, "Error", "Memory must be greater than zero")
            self.vm_memory_input.setFocus()
            return
            
        if memory < 128:
            QMessageBox.warning(self, "Error", "Memory must be at least 128MB")
            self.vm_memory_input.setFocus()
            return
            
        if cpus <= 0:
            QMessageBox.warning(self, "Error", "CPU count must be greater than zero")
            self.vm_cpu_input.setFocus()
            return
            
        if cpus > 16:
            QMessageBox.warning(self, "Error", "CPU count exceeds maximum allowed (16)")
            self.vm_cpu_input.setFocus()
            return
        
        if self.vm_disk_select.count() == 0:
            QMessageBox.warning(self, "Error", "No disks available. Please create a disk first.")
            return
        
        # Refresh disk list to ensure we have the latest disks
        self.refresh_disks()
        
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

class DockerManagerTab(QWidget):
    """Tab for managing Docker containers and images"""    
    def __init__(self, docker_manager):
        super().__init__()
        self.docker_manager = docker_manager
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
          # Create Dockerfile Project section
        create_dockerfile_group = QGroupBox("Create Docker Project")
        create_dockerfile_layout = QVBoxLayout()
        
        # Project name
        project_name_layout = QHBoxLayout()
        project_name_label = QLabel("Project Name:")
        project_name_label.setStyleSheet("font-weight: bold;")
        project_name_label.setFixedWidth(100)
        self.project_name_input = QLineEdit()
        self.project_name_input.setPlaceholderText("Enter project name (folder will be created in dockerfiles directory)")
        project_name_layout.addWidget(project_name_label)
        project_name_layout.addWidget(self.project_name_input)
        create_dockerfile_layout.addLayout(project_name_layout)
        
        # Dockerfile content
        dockerfile_content_label = QLabel("Dockerfile Content:")
        dockerfile_content_label.setStyleSheet("font-weight: bold;")
        create_dockerfile_layout.addWidget(dockerfile_content_label)
        
        self.dockerfile_content = QTextEdit()
        self.dockerfile_content.setPlaceholderText("Enter Dockerfile content here...\nExample:\nFROM python:3.9-slim\nWORKDIR /app\nCOPY . .\nCOPY requirements.txt .\nRUN pip install -r requirements.txt\nCOPY app.py .\nCMD [\"python\", \"app.py\"]")
        self.dockerfile_content.setMinimumHeight(120)
        create_dockerfile_layout.addWidget(self.dockerfile_content)
        
        # Requirements.txt
        requirements_layout = QHBoxLayout()
        requirements_label = QLabel("Requirements.txt:")
        requirements_label.setStyleSheet("font-weight: bold;")
        requirements_label.setFixedWidth(120)
        requirements_layout_inner = QVBoxLayout()
        
        self.requirements_text = QTextEdit()
        self.requirements_text.setPlaceholderText("Enter Python package requirements\nExample:\nflask==2.0.1\nnumpy>=1.20.0\npandas")
        self.requirements_text.setMaximumHeight(100)
        
        requirements_file_layout = QHBoxLayout()
        self.requirements_file_path = QLineEdit()
        self.requirements_file_path.setPlaceholderText("Or select an existing requirements.txt file")
        requirements_browse_btn = QPushButton("Browse...")
        requirements_browse_btn.clicked.connect(self.browse_requirements_file)
        requirements_file_layout.addWidget(self.requirements_file_path)
        requirements_file_layout.addWidget(requirements_browse_btn)
        
        requirements_layout_inner.addWidget(self.requirements_text)
        requirements_layout_inner.addLayout(requirements_file_layout)
        requirements_layout.addWidget(requirements_label)
        requirements_layout.addLayout(requirements_layout_inner)
        create_dockerfile_layout.addLayout(requirements_layout)
        
        # Entry point file
        entrypoint_layout = QHBoxLayout()
        entrypoint_label = QLabel("Entry Point:")
        entrypoint_label.setStyleSheet("font-weight: bold;")
        entrypoint_label.setFixedWidth(120)
        entrypoint_layout_inner = QVBoxLayout()
        
        entrypoint_file_layout = QHBoxLayout()
        self.entrypoint_filename = QLineEdit()
        self.entrypoint_filename.setPlaceholderText("Entry point filename (e.g., app.py)")
        entrypoint_file_layout.addWidget(self.entrypoint_filename)
        
        entrypoint_layout_inner.addLayout(entrypoint_file_layout)
        
        self.entrypoint_content = QTextEdit()
        self.entrypoint_content.setPlaceholderText("Enter your application code here...\nExample for a simple Flask app:\n\nfrom flask import Flask\n\napp = Flask(__name__)\n\n@app.route('/')\ndef hello():\n    return 'Hello, Docker!'\n\nif __name__ == '__main__':\n    app.run(host='0.0.0.0', port=5000)")
        self.entrypoint_content.setMaximumHeight(100)
        
        entrypoint_layout_inner.addWidget(self.entrypoint_content)
        
        # Browse existing file option
        entrypoint_existing_layout = QHBoxLayout()
        self.entrypoint_file_path = QLineEdit()
        self.entrypoint_file_path.setPlaceholderText("Or select an existing file")
        entrypoint_browse_btn = QPushButton("Browse...")
        entrypoint_browse_btn.clicked.connect(self.browse_entrypoint_file)
        entrypoint_existing_layout.addWidget(self.entrypoint_file_path)
        entrypoint_existing_layout.addWidget(entrypoint_browse_btn)
        
        entrypoint_layout_inner.addLayout(entrypoint_existing_layout)
        entrypoint_layout.addWidget(entrypoint_label)
        entrypoint_layout.addLayout(entrypoint_layout_inner)
        create_dockerfile_layout.addLayout(entrypoint_layout)
        
        # Create button
        create_btn_layout = QHBoxLayout()
        create_btn_layout.addStretch()
        self.create_project_btn = QPushButton("Create Docker Project")
        self.create_project_btn.clicked.connect(self.create_docker_project)
        create_btn_layout.addWidget(self.create_project_btn)
        create_btn_layout.addStretch()
        create_dockerfile_layout.addLayout(create_btn_layout)
        
        create_dockerfile_group.setLayout(create_dockerfile_layout)
        layout.addWidget(create_dockerfile_group)
        
        # Build Image section
        build_group = QGroupBox("Build Docker Image")
        build_layout = QVBoxLayout()
        
        dockerfile_layout = QHBoxLayout()
        dockerfile_label = QLabel("Dockerfile:")
        dockerfile_label.setStyleSheet("font-weight: bold;")
        dockerfile_label.setFixedWidth(70)
        self.build_dockerfile_path = QLineEdit()
        self.build_dockerfile_path.setPlaceholderText("Path to Dockerfile")
        dockerfile_browse_btn = QPushButton("Browse...")
        dockerfile_browse_btn.clicked.connect(self.browse_build_dockerfile)
        dockerfile_layout.addWidget(dockerfile_label)
        dockerfile_layout.addWidget(self.build_dockerfile_path)
        dockerfile_layout.addWidget(dockerfile_browse_btn)
        build_layout.addLayout(dockerfile_layout)
        
        image_layout = QHBoxLayout()
        image_label = QLabel("Image Name:")
        image_label.setStyleSheet("font-weight: bold;")
        image_label.setFixedWidth(90)
        self.image_name_input = QLineEdit()
        self.image_name_input.setPlaceholderText("Image name and tag (e.g., myapp:latest)")
        image_layout.addWidget(image_label)
        image_layout.addWidget(self.image_name_input)
        build_layout.addLayout(image_layout)
        
        # Progress bar
        self.build_progress = QProgressBar()
        self.build_progress.setVisible(False)
        build_layout.addWidget(self.build_progress)
        
        build_btn_layout = QHBoxLayout()
        build_btn_layout.addStretch()
        self.build_image_btn = QPushButton("Build Image")
        self.build_image_btn.clicked.connect(self.build_image)
        build_btn_layout.addWidget(self.build_image_btn)
        build_btn_layout.addStretch()
        build_layout.addLayout(build_btn_layout)
        
        build_group.setLayout(build_layout)
        layout.addWidget(build_group)
        
        self.setLayout(layout)

    def browse_requirements_file(self):
        """Browse for a requirements.txt file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Requirements File", "", "Requirements (*.txt);;All Files (*)"
        )
        
        if file_path:
            self.requirements_file_path.setText(file_path)
            # Read the content of the file and populate the text field
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                    self.requirements_text.setPlainText(content)
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Could not read file: {str(e)}")
    
    def browse_entrypoint_file(self):
        """Browse for an entry point file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Entry Point File", "", "Python Files (*.py);;All Files (*)"
        )
        
        if file_path:
            self.entrypoint_file_path.setText(file_path)
            # Extract the filename for the entry point
            self.entrypoint_filename.setText(os.path.basename(file_path))
            # Read the content of the file and populate the text field
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                    self.entrypoint_content.setPlainText(content)
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Could not read file: {str(e)}")
    
    def browse_build_dockerfile(self):
        """Browse for a Dockerfile to build from"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Dockerfile", "", "Dockerfile (Dockerfile);;All Files (*)"
        )
        
        if file_path:
            self.build_dockerfile_path.setText(file_path)
    
    def create_docker_project(self):
        """Create a Docker project with Dockerfile, requirements.txt and entry point"""
        # Validate inputs
        project_name = self.project_name_input.text().strip()
        dockerfile_content = self.dockerfile_content.toPlainText().strip()
        
        if not project_name:
            QMessageBox.warning(self, "Error", "Please enter a project name")
            return
            
        if not dockerfile_content:
            QMessageBox.warning(self, "Error", "Please enter Dockerfile content")
            return
        
        # Get requirements content (either from text field or file)
        requirements_content = None
        if self.requirements_text.toPlainText().strip():
            requirements_content = self.requirements_text.toPlainText().strip()
        elif self.requirements_file_path.text().strip():
            try:
                with open(self.requirements_file_path.text().strip(), 'r') as f:
                    requirements_content = f.read().strip()
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Could not read requirements file: {str(e)}")
                return
        
        # Get entry point content and filename
        entrypoint_content = None
        entrypoint_file = None
        
        if self.entrypoint_filename.text().strip():
            entrypoint_file = self.entrypoint_filename.text().strip()
            
            if self.entrypoint_content.toPlainText().strip():
                entrypoint_content = self.entrypoint_content.toPlainText().strip()
            elif self.entrypoint_file_path.text().strip():
                try:
                    with open(self.entrypoint_file_path.text().strip(), 'r') as f:
                        entrypoint_content = f.read().strip()
                except Exception as e:
                    QMessageBox.warning(self, "Error", f"Could not read entry point file: {str(e)}")
                    return
        
        # Create the Docker project
        success, message, project_path = self.docker_manager.create_dockerfile_project(
            project_name, 
            dockerfile_content, 
            requirements_content, 
            entrypoint_content, 
            entrypoint_file
        )
        
        if success:
            QMessageBox.information(self, "Success", message)
            # Clear fields
            self.project_name_input.clear()
            self.dockerfile_content.clear()
            self.requirements_text.clear()
            self.requirements_file_path.clear()
            self.entrypoint_filename.clear()
            self.entrypoint_content.clear()
            self.entrypoint_file_path.clear()
            
            # Ask user if they want to build an image from this Docker project
            reply = QMessageBox.question(
                self, 'Build Image',
                "Do you want to build a Docker image from this project?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                dockerfile_path = os.path.join(project_path, "Dockerfile")
                self.build_dockerfile_path.setText(dockerfile_path)
                # Use project name as suggested image name
                self.image_name_input.setText(f"{project_name.lower()}:latest")
                self.image_name_input.setFocus()
        else:
            QMessageBox.warning(self, "Error", message)
    
    def update_build_progress(self, value):
        self.build_progress.setValue(value)

    def build_image(self):
        """Build a Docker image from a Dockerfile"""
        dockerfile_path = self.build_dockerfile_path.text().strip()
        image_name = self.image_name_input.text().strip()
        
        if not dockerfile_path:
            QMessageBox.warning(self, "Error", "Please specify a Dockerfile path")
            return
        
        if not image_name:
            QMessageBox.warning(self, "Error", "Please enter an image name and tag")
            return
        
        # If building from a Docker project in dockerfiles directory, check if it's properly structured
        project_dir = os.path.dirname(dockerfile_path)
        is_project_structure = False
        
        if project_dir.startswith(self.docker_manager.dockerfiles_dir) and project_dir != self.docker_manager.dockerfiles_dir:
            # This is a Docker project in the dockerfiles directory
            project_name = os.path.basename(project_dir)
            requirements_path = os.path.join(project_dir, "requirements.txt")
            
            # Verify it has the required files
            dockerfile_exists = os.path.exists(dockerfile_path)
            if not dockerfile_exists:
                QMessageBox.warning(self, "Error", f"Dockerfile not found in project: {project_name}")
                return
                  # Check if this is a complete Docker project structure
            if os.path.exists(requirements_path):
                is_project_structure = True
                
                # Check if there's an entry point file
                entry_point = None
                entry_point_files = []
                for file in os.listdir(project_dir):
                    if file.endswith('.py') and file != "__init__.py" and file != "requirements.txt" and file != "Dockerfile":
                        entry_point_files.append(file)
                
                if entry_point_files:
                    entry_point = entry_point_files[0] if len(entry_point_files) == 1 else ', '.join(entry_point_files)
                
                # Show what's happening to the user with more details
                cmd_display = f"cd {project_dir}\ndocker build -t {image_name} ."
                details = f"Building image from project directory using:\n\n{cmd_display}\n\n"
                details += f"Project directory: {project_dir}\n"
                details += f"Found files:\n- Dockerfile\n- requirements.txt"
                if entry_point:
                    details += f"\n- {entry_point}"
                
                QMessageBox.information(self, "Building Docker Image", details)
        
        # Disable UI elements during build
        self.build_image_btn.setEnabled(False)
        self.build_progress.setValue(0)
        self.build_progress.setVisible(True)
        
        # Create worker thread for building the image
        self.worker = WorkerThread(self.docker_manager.build_image, dockerfile_path, image_name)
        self.worker.progress.connect(self.update_build_progress)
        self.worker.finished.connect(self.on_image_built)
        self.worker.start()
         
    def refresh_containers(self):

        """Refresh the list of Docker containers (always showing all containers)"""
        success, message, containers = self.docker_manager.list_containers(True)
        
        self.containers_table.setRowCount(0)
        print(f"Found {len(containers)} containers")
        
        if not success:
            QMessageBox.warning(self, "Error", message)
            return
        
        row = 0
        for container in containers:
            self.containers_table.insertRow(row)
            
            # ID
            self.containers_table.setItem(row, 0, QTableWidgetItem(container['id']))
            
            # Name
            self.containers_table.setItem(row, 1, QTableWidgetItem(container['name']))
            
            # Image
            self.containers_table.setItem(row, 2, QTableWidgetItem(container['image']))
            
            # Status with color indicator
            status_text = container['status']
            status_item = QTableWidgetItem(status_text)
            
            # Set color based on container status
            if "Up " in status_text:  # Running container
                status_item.setForeground(QColor("#00AA00"))  # Green for running
                status_item.setIcon(QIcon.fromTheme("media-playback-start", QIcon()))
            else:  # Stopped, exited, or other states
                status_item.setForeground(QColor("#D83B01"))  # Red/Orange for stopped
                status_item.setIcon(QIcon.fromTheme("media-playback-stop", QIcon()))
                
            self.containers_table.setItem(row, 3, status_item)
            
            # Ports
            self.containers_table.setItem(row, 4, QTableWidgetItem(container['ports']))
            
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
                    padding: 5px 10px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #005A9E;
                }
                QPushButton:pressed {
                    background-color: #003E73;
                }
            """
              # Add appropriate action buttons based on container status
            if "Up " in container['status']:  # Running container
                stop_btn = QPushButton("Stop")
                stop_btn.setStyleSheet(button_style.replace("#0078D7", "#D83B01").replace("#005A9E", "#A42600").replace("#003E73", "#750B1C"))
                stop_btn.clicked.connect(lambda checked, cont_id=container['id']: self.stop_container(cont_id))
                actions_layout.addWidget(stop_btn)
            else:  # Stopped container
                start_btn = QPushButton("Start")
                start_btn.setStyleSheet(button_style)  # Use blue color for start
                start_btn.clicked.connect(lambda checked, cont_id=container['id']: self.start_container(cont_id))
                actions_layout.addWidget(start_btn)
            
            # Add delete button for all containers
            delete_btn = QPushButton("Remove")
            delete_btn.setStyleSheet(button_style.replace("#0078D7", "#555555").replace("#005A9E", "#333333").replace("#003E73", "#111111"))
            delete_btn.clicked.connect(lambda checked, cont_id=container['id']: self.remove_container(cont_id))
            actions_layout.addWidget(delete_btn)
            
            actions_widget.setLayout(actions_layout)
            self.containers_table.setCellWidget(row, 5, actions_widget)
            
            row += 1

    def on_image_built(self, success, message):
        """Handle Docker image build result"""
        self.build_image_btn.setEnabled(True)
        self.build_progress.setVisible(False)
        
        if success:
            # Check if this was a project build
            dockerfile_path = self.build_dockerfile_path.text().strip()
            project_dir = os.path.dirname(dockerfile_path)
            is_project_structure = (project_dir.startswith(self.docker_manager.dockerfiles_dir) and 
                                  project_dir != self.docker_manager.dockerfiles_dir and
                                  os.path.exists(os.path.join(project_dir, "requirements.txt")))
            
            if is_project_structure:
                # Show more detailed success message for project builds
                project_name = os.path.basename(project_dir)
                image_name = self.image_name_input.text().strip()
                
                success_msg = f"Successfully built Docker image: {image_name}\n\n"
                success_msg += f"The image was built using all files from project: {project_name}\n"
                success_msg += "You can now run a container from this image."
                
                QMessageBox.information(self, "Build Success", success_msg)
            else:
                QMessageBox.information(self, "Success", message)
                
            self.build_dockerfile_path.clear()
            self.image_name_input.clear()
        else:
            QMessageBox.warning(self, "Error", message)

class DockerResourcesTab(QWidget):

    def __init__(self, docker_resources):
        super().__init__()
        self.docker_manager = docker_resources
        self.init_ui()  

    def init_ui(self):
        layout = QVBoxLayout()
    # Docker Images and Containers section
        docker_resources_group = QGroupBox("Docker Resources")
        docker_resources_layout = QVBoxLayout()
        
        # Tabs for Images and Containers
        resources_tabs = QTabWidget()
        
        # Images tab
        images_tab = QWidget()
        images_layout = QVBoxLayout()
        
        # Images actions
        images_actions_layout = QHBoxLayout()
        
        refresh_images_btn = QPushButton("Refresh")
        refresh_images_btn.clicked.connect(self.refresh_images)
        images_actions_layout.addWidget(refresh_images_btn)
        
        pull_image_btn = QPushButton("Pull Image")
        pull_image_btn.clicked.connect(self.pull_image)
        images_actions_layout.addWidget(pull_image_btn)
        
        search_local_btn = QPushButton("Search Local")
        search_local_btn.clicked.connect(self.search_local_images)
        images_actions_layout.addWidget(search_local_btn)
        
        search_hub_btn = QPushButton("Search DockerHub")
        search_hub_btn.clicked.connect(self.search_dockerhub)
        images_actions_layout.addWidget(search_hub_btn)
        
        images_layout.addLayout(images_actions_layout)
        
        # Images table
        self.images_table = QTableWidget(0, 5)
        self.images_table.setHorizontalHeaderLabels(["Name:Tag", "ID", "Size", "Created", "Actions"])
        self.images_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.images_table.setColumnWidth(4, 250)
        images_layout.addWidget(self.images_table)
        
        images_tab.setLayout(images_layout)
        resources_tabs.addTab(images_tab, "Images")
        
        # Containers tab
        containers_tab = QWidget()
        containers_layout = QVBoxLayout()
        
        # Container actions
        containers_actions_layout = QHBoxLayout()
        
        refresh_containers_btn = QPushButton("Refresh")
        refresh_containers_btn.clicked.connect(self.refresh_containers)
        containers_actions_layout.addWidget(refresh_containers_btn)
        run_container_btn = QPushButton("Run Container")
        run_container_btn.clicked.connect(self.run_container)
        containers_actions_layout.addWidget(run_container_btn)
        # Removed "Show all containers" checkbox since we'll always show all containers
        
        containers_layout.addLayout(containers_actions_layout)
        
        # Containers table
        self.containers_table = QTableWidget(0, 6)
        self.containers_table.setHorizontalHeaderLabels(["ID", "Name", "Image", "Status", "Ports", "Actions"])
        self.containers_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.containers_table.setColumnWidth(5, 250)
        containers_layout.addWidget(self.containers_table)
        
        containers_tab.setLayout(containers_layout)
        resources_tabs.addTab(containers_tab, "Containers")
        
        docker_resources_layout.addWidget(resources_tabs)
        docker_resources_group.setLayout(docker_resources_layout)
        layout.addWidget(docker_resources_group)
        
        self.setLayout(layout)
        
        # Initial load
        self.refresh_images()
        self.refresh_containers()
    
    def refresh_images(self):
        """Refresh the list of Docker images"""
        success, message, images = self.docker_manager.list_images()
        
        self.images_table.setRowCount(0)
        
        if not success:
            QMessageBox.warning(self, "Error", message)
            return
        
        row = 0
        for image in images:
            self.images_table.insertRow(row)
            
            # Name:Tag
            self.images_table.setItem(row, 0, QTableWidgetItem(image['name_tag']))
            
            # ID
            self.images_table.setItem(row, 1, QTableWidgetItem(image['id']))
            
            # Size
            self.images_table.setItem(row, 2, QTableWidgetItem(image['size']))
            
            # Created
            self.images_table.setItem(row, 3, QTableWidgetItem(image['created_at']))
            
            # Actions
            actions_widget = QWidget()
            actions_layout = QHBoxLayout()
            actions_layout.setContentsMargins(0, 0, 0, 0)
            actions_layout.setSpacing(8)  # Add space between buttons
            
            button_style = """
                QPushButton {
                    background-color: #0078D7;
                    color: white;
                    font-weight: bold;
                    border: none;
                    padding: 5px 10px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #005A9E;
                }
                QPushButton:pressed {
                    background-color: #003E73;
                }
            """
            
            run_btn = QPushButton("Run")
            run_btn.setStyleSheet(button_style)
            run_btn.clicked.connect(lambda checked, img=image['name_tag']: self.run_container_from_image(img))
            
            delete_btn = QPushButton("Delete")
            delete_btn.setStyleSheet(button_style.replace("#0078D7", "#D83B01").replace("#005A9E", "#A42600").replace("#003E73", "#750B1C"))
            delete_btn.clicked.connect(lambda checked, img_id=image['id']: self.delete_image(img_id))
            
            actions_layout.addWidget(run_btn)
            actions_layout.addWidget(delete_btn)
            actions_widget.setLayout(actions_layout)
            
            self.images_table.setCellWidget(row, 4, actions_widget)
            
            row += 1
            
    def refresh_containers(self):

        """Refresh the list of Docker containers (always showing all containers)"""
        success, message, containers = self.docker_manager.list_containers(True)
        
        self.containers_table.setRowCount(0)
        print(f"Found {len(containers)} containers")
        
        if not success:
            QMessageBox.warning(self, "Error", message)
            return
        
        row = 0
        for container in containers:
            self.containers_table.insertRow(row)
            
            # ID
            self.containers_table.setItem(row, 0, QTableWidgetItem(container['id']))
            
            # Name
            self.containers_table.setItem(row, 1, QTableWidgetItem(container['name']))
            
            # Image
            self.containers_table.setItem(row, 2, QTableWidgetItem(container['image']))
            
            # Status with color indicator
            status_text = container['status']
            status_item = QTableWidgetItem(status_text)
            
            # Set color based on container status
            if "Up " in status_text:  # Running container
                status_item.setForeground(QColor("#00AA00"))  # Green for running
                status_item.setIcon(QIcon.fromTheme("media-playback-start", QIcon()))
            else:  # Stopped, exited, or other states
                status_item.setForeground(QColor("#D83B01"))  # Red/Orange for stopped
                status_item.setIcon(QIcon.fromTheme("media-playback-stop", QIcon()))
                
            self.containers_table.setItem(row, 3, status_item)
            
            # Ports
            self.containers_table.setItem(row, 4, QTableWidgetItem(container['ports']))
            
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
                    padding: 5px 10px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #005A9E;
                }
                QPushButton:pressed {
                    background-color: #003E73;
                }
            """
              # Add appropriate action buttons based on container status
            if "Up " in container['status']:  # Running container
                stop_btn = QPushButton("Stop")
                stop_btn.setStyleSheet(button_style.replace("#0078D7", "#D83B01").replace("#005A9E", "#A42600").replace("#003E73", "#750B1C"))
                stop_btn.clicked.connect(lambda checked, cont_id=container['id']: self.stop_container(cont_id))
                actions_layout.addWidget(stop_btn)
            else:  # Stopped container
                start_btn = QPushButton("Start")
                start_btn.setStyleSheet(button_style)  # Use blue color for start
                start_btn.clicked.connect(lambda checked, cont_id=container['id']: self.start_container(cont_id))
                actions_layout.addWidget(start_btn)
            
            # Add delete button for all containers
            delete_btn = QPushButton("Remove")
            delete_btn.setStyleSheet(button_style.replace("#0078D7", "#555555").replace("#005A9E", "#333333").replace("#003E73", "#111111"))
            delete_btn.clicked.connect(lambda checked, cont_id=container['id']: self.remove_container(cont_id))
            actions_layout.addWidget(delete_btn)
            
            actions_widget.setLayout(actions_layout)
            self.containers_table.setCellWidget(row, 5, actions_widget)
            
            row += 1
   
    def pull_image(self):
        """Pull a Docker image from a registry"""
        image_name, ok = QInputDialog.getText(
            self, "Pull Docker Image", 
            "Enter image name to pull (e.g., nginx:latest):"
        )
        
        if ok and image_name:
            # Disable UI during pull
            QApplication.setOverrideCursor(Qt.WaitCursor)
            
            # Pull the image
            success, message = self.docker_manager.pull_image(image_name)
            
            # Restore cursor
            QApplication.restoreOverrideCursor()
            
            if success:
                QMessageBox.information(self, "Success", message)
                self.refresh_images()
            else:
                QMessageBox.warning(self, "Error", message)
    
    def search_local_images(self):
        """Search for local Docker images"""
        search_term, ok = QInputDialog.getText(
            self, "Search Local Images", 
            "Enter image name or tag to search for:"
        )
        
        if ok and search_term:
            success, message, images = self.docker_manager.search_local_image(search_term)
            
            if success:
                # Display the search results
                self.images_table.setRowCount(0)
                
                row = 0
                for image in images:
                    self.images_table.insertRow(row)
                    
                    # Name:Tag
                    self.images_table.setItem(row, 0, QTableWidgetItem(image['name_tag']))
                    
                    # ID
                    self.images_table.setItem(row, 1, QTableWidgetItem(image['id']))
                    
                    # Size
                    self.images_table.setItem(row, 2, QTableWidgetItem(image['size']))
                    
                    # Created
                    self.images_table.setItem(row, 3, QTableWidgetItem(image['created_at']))
                    
                    # Actions (same as in refresh_images)
                    actions_widget = QWidget()
                    actions_layout = QHBoxLayout()
                    actions_layout.setContentsMargins(0, 0, 0, 0)
                    actions_layout.setSpacing(8)
                    
                    button_style = """
                        QPushButton {
                            background-color: #0078D7;
                            color: white;
                            font-weight: bold;
                            border: none;
                            padding: 5px 10px;
                            border-radius: 4px;
                        }
                        QPushButton:hover {
                            background-color: #005A9E;
                        }
                        QPushButton:pressed {
                            background-color: #003E73;
                        }
                    """
                    
                    run_btn = QPushButton("Run")
                    run_btn.setStyleSheet(button_style)
                    run_btn.clicked.connect(lambda checked, img=image['name_tag']: self.run_container_from_image(img))
                    
                    delete_btn = QPushButton("Delete")
                    delete_btn.setStyleSheet(button_style.replace("#0078D7", "#D83B01").replace("#005A9E", "#A42600").replace("#003E73", "#750B1C"))
                    delete_btn.clicked.connect(lambda checked, img_id=image['id']: self.delete_image(img_id))
                    
                    actions_layout.addWidget(run_btn)
                    actions_layout.addWidget(delete_btn)
                    actions_widget.setLayout(actions_layout)
                    
                    self.images_table.setCellWidget(row, 4, actions_widget)
                    
                    row += 1
                
                QMessageBox.information(self, "Search Results", message)
            else:
                QMessageBox.warning(self, "Error", message)
    
    def search_dockerhub(self):
        """Search for Docker images on DockerHub"""
        search_term, ok = QInputDialog.getText(
            self, "Search DockerHub", 
            "Enter image name to search for on DockerHub:"
        )
        
        if ok and search_term:
            # Disable UI during search
            QApplication.setOverrideCursor(Qt.WaitCursor)
            
            # Search DockerHub
            success, message, results = self.docker_manager.search_dockerhub(search_term)
            
            # Restore cursor
            QApplication.restoreOverrideCursor()
            
            if success:
                # Create a dialog to display the results
                dialog = QDialog(self)
                dialog.setWindowTitle(f"DockerHub Results: {search_term}")
                dialog.setGeometry(100, 100, 800, 500)
                
                dialog_layout = QVBoxLayout()
                
                result_table = QTableWidget(0, 5)
                result_table.setHorizontalHeaderLabels(["Name", "Description", "Stars", "Official", "Actions"])
                result_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
                
                row = 0
                for result in results:
                    result_table.insertRow(row)
                    
                    # Name
                    result_table.setItem(row, 0, QTableWidgetItem(result['name']))
                    
                    # Description
                    result_table.setItem(row, 1, QTableWidgetItem(result['description']))
                    
                    # Stars
                    result_table.setItem(row, 2, QTableWidgetItem(result['stars']))
                    
                    # Official
                    result_table.setItem(row, 3, QTableWidgetItem("Yes" if result['official'] else "No"))
                    
                    # Pull button
                    actions_widget = QWidget()
                    actions_layout = QHBoxLayout()
                    actions_layout.setContentsMargins(0, 0, 0, 0)
                    
                    pull_btn = QPushButton("Pull Image")
                    pull_btn.clicked.connect(lambda checked, img=result['name']: self.pull_hub_image(img, dialog))
                    actions_layout.addWidget(pull_btn)
                    
                    actions_widget.setLayout(actions_layout)
                    result_table.setCellWidget(row, 4, actions_widget)
                    
                    row += 1
                
                dialog_layout.addWidget(result_table)
                
                close_btn = QPushButton("Close")
                close_btn.clicked.connect(dialog.accept)
                dialog_layout.addWidget(close_btn)
                
                dialog.setLayout(dialog_layout)
                dialog.exec_()
            else:
                QMessageBox.warning(self, "Error", message)
    
    def pull_hub_image(self, image_name, dialog=None):
        """Pull an image from DockerHub (from the search results dialog)"""
        if dialog:
            dialog.accept()  # Close the dialog
        
        # Disable UI during pull
        QApplication.setOverrideCursor(Qt.WaitCursor)
        
        # Pull the image
        success, message = self.docker_manager.pull_image(image_name)
        
        # Restore cursor
        QApplication.restoreOverrideCursor()
        
        if success:
            QMessageBox.information(self, "Success", message)
            self.refresh_images()        
        else:
            QMessageBox.warning(self, "Error", message)
    
    def stop_container(self, container_id):
        """Stop a running Docker container"""
        reply = QMessageBox.question(
            self, 'Stop Container',
            f"Are you sure you want to stop container {container_id}?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            success, message = self.docker_manager.stop_container(container_id)
            
            if success:                
                QMessageBox.information(self, "Success", message)
                self.refresh_containers()
            else:
                QMessageBox.warning(self, "Error", message)
    
    def delete_image(self, image_id):
        """Delete a Docker image"""
        # This would require implementing the delete_image method in DockerManager
        QMessageBox.warning(self, "Not Implemented", "Image deletion not implemented yet")
    
    def run_container_from_image(self, image_name):
        """Run a container from the selected image"""
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Run Container: {image_name}")
        dialog.setGeometry(100, 100, 500, 300)
        
        layout = QVBoxLayout()
        
        # Container name
        name_layout = QHBoxLayout()
        name_label = QLabel("Container Name:")
        name_label.setFixedWidth(120)
        name_input = QLineEdit()
        name_input.setPlaceholderText("Leave empty for auto-generated name")
        name_layout.addWidget(name_label)
        name_layout.addWidget(name_input)
        layout.addLayout(name_layout)
        
        # Port mappings
        port_layout = QHBoxLayout()
        port_label = QLabel("Port Mappings:")
        port_label.setFixedWidth(120)
        port_input = QLineEdit()
        port_input.setPlaceholderText("host:container (e.g., 8080:80)")
        port_layout.addWidget(port_label)
        port_layout.addWidget(port_input)
        layout.addLayout(port_layout)
        
        # Run in background option
        detach_checkbox = QCheckBox("Run in background")
        detach_checkbox.setChecked(True)
        layout.addWidget(detach_checkbox)
        
        # Buttons
        buttons_layout = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        run_btn = QPushButton("Run Container")
        
        def on_run():
            container_name = name_input.text().strip() or None
            ports = [port_input.text().strip()] if port_input.text().strip() else None
            detach = detach_checkbox.isChecked()
            
            dialog.accept()
            
            # Run the container
            success, message, container_id = self.docker_manager.run_container(
                image_name=image_name,
                container_name=container_name,
                ports=ports,
                detach=detach
            )
            
            if success:
                QMessageBox.information(self, "Success", message)
                self.refresh_containers()
            else:
                QMessageBox.warning(self, "Error", message)
        
        run_btn.clicked.connect(on_run)
        buttons_layout.addWidget(cancel_btn)
        buttons_layout.addWidget(run_btn)
        layout.addLayout(buttons_layout)
        
        dialog.setLayout(layout)
        dialog.exec_()
    
    def run_container(self):
        """Run a new container from available images"""
        success, message, images = self.docker_manager.list_images()
        
        if not success or not images:
            QMessageBox.warning(self, "Error", "No Docker images available. Please pull or build an image first.")
            return
        
        # Create image selection dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Run Container")
        dialog.setGeometry(100, 100, 500, 400)
        
        layout = QVBoxLayout()
        
        # Image selection
        image_layout = QHBoxLayout()
        image_label = QLabel("Select Image:")
        image_combo = QComboBox()
        
        for image in images:
            image_combo.addItem(image['name_tag'])
        
        image_layout.addWidget(image_label)
        image_layout.addWidget(image_combo)
        layout.addLayout(image_layout)
        
        # Container name
        name_layout = QHBoxLayout()
        name_label = QLabel("Container Name:")
        name_input = QLineEdit()
        name_input.setPlaceholderText("Leave empty for auto-generated name")
        name_layout.addWidget(name_label)
        name_layout.addWidget(name_input)
        layout.addLayout(name_layout)
        
        # Port mappings
        port_layout = QHBoxLayout()
        port_label = QLabel("Port Mappings:")
        port_input = QLineEdit()
        port_input.setPlaceholderText("host:container (e.g., 8080:80)")
        port_layout.addWidget(port_label)
        port_layout.addWidget(port_input)
        layout.addLayout(port_layout)
        
        # Run in background option
        detach_checkbox = QCheckBox("Run in background")
        detach_checkbox.setChecked(True)
        layout.addWidget(detach_checkbox)
        
        # Buttons
        buttons_layout = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        run_btn = QPushButton("Run Container")
        
        def on_run():
            selected_image = image_combo.currentText()
            container_name = name_input.text().strip() or None
            ports = [port_input.text().strip()] if port_input.text().strip() else None
            detach = detach_checkbox.isChecked()
            
            dialog.accept()
            
            # Run the container
            success, message, container_id = self.docker_manager.run_container(
                image_name=selected_image,
                container_name=container_name,
                ports=ports,
                detach=detach
            )
            
            if success:
                QMessageBox.information(self, "Success", message)
                self.refresh_containers()
            else:
                QMessageBox.warning(self, "Error", message)
        
        run_btn.clicked.connect(on_run)
        buttons_layout.addWidget(cancel_btn)
        buttons_layout.addWidget(run_btn)
        layout.addLayout(buttons_layout)
        dialog.setLayout(layout)
        dialog.exec_()
        
    def start_container(self, container_id):
        """Start a stopped Docker container"""
        reply = QMessageBox.question(
            self, 'Start Container',
            f"Are you sure you want to start container {container_id}?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            success, message = self.docker_manager.start_container(container_id)
            
            if success:
                QMessageBox.information(self, "Success", message)
                self.refresh_containers()  # Will use show_all_containers class variable
            else:
                QMessageBox.warning(self, "Error", message)
    
    def remove_container(self, container_id):
        """Remove a Docker container"""
        reply = QMessageBox.question(
            self, 'Remove Container',
            f"Are you sure you want to remove container {container_id}?\nThis action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            success, message = self.docker_manager.remove_container(container_id)
            if success:
                QMessageBox.information(self, "Success", message)
                # Make sure we're showing all containers
                self.show_all_containers = True
                self.show_all_checkbox.setChecked(True)
                self.refresh_containers()  # Will use show_all_containers
            else:                QMessageBox.warning(self, "Error", message)

class MainWindow(QMainWindow):
    """Main application window"""
    def __init__(self):
        super().__init__()
        self.settings = QSettings("CloudVMManager", "CloudVM")
        self.disk_manager = DiskManager()
        self.vm_manager = VMManager()
        self.docker_manager = DockerManager()
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
        
        # Docker manager tab
        self.docker_tab = DockerManagerTab(self.docker_manager)
        self.tabs.addTab(self.docker_tab, QIcon(get_icon_path("docker.png")), "Docker Manager")
        
        self.docker_resources = DockerResourcesTab(self.docker_manager)
        self.tabs.addTab(self.docker_resources, QIcon(get_icon_path("docker.png")), "Docker Resources")

        # Connect the disks_changed signal to the VM tab's refresh_disks method
        self.disk_tab.disks_changed.connect(self.vm_tab.refresh_disks)
        # Also force the VM manager to reload its disk manager registry when disks change
        self.disk_tab.disks_changed.connect(lambda: self.vm_manager.disk_manager._load_registry())
        
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
        self.docker_tab.refresh_images()
        self.docker_tab.refresh_containers()
        self.statusBar.showMessage("Refreshed all data", 3000)
    
    def show_create_disk(self):
        """Switch to the disk tab and focus on the create disk form"""
        self.tabs.setCurrentIndex(0)  # Switch to disk tab
        self.disk_tab.disk_name_input.setFocus()
    
    def show_create_vm(self):
        """Switch to the VM tab and focus on the create VM form"""
        # Force refresh of the disk list before switching tabs
        self.vm_tab.refresh_disks()
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