import os
import json
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QCheckBox, QPushButton, QComboBox,
    QMessageBox, QGroupBox, QTabWidget, QWidget
)
from PyQt5.QtCore import QSettings

class SettingsDialog(QDialog):
    """Dialog for configuring QEMU and application settings"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = QSettings("CloudVMManager", "CloudVM")
        self.init_ui()
        self.load_settings()
    
    def init_ui(self):
        self.setWindowTitle("Settings")
        self.setMinimumWidth(500)
        
        layout = QVBoxLayout()
        
        # Create tabs
        tabs = QTabWidget()
        
        # QEMU Tab
        qemu_tab = QWidget()
        qemu_layout = QVBoxLayout()
        
        # QEMU paths group
        paths_group = QGroupBox("QEMU Paths")
        paths_layout = QFormLayout()
        
        self.qemu_img_path = QLineEdit()
        paths_layout.addRow("QEMU-IMG Path:", self.qemu_img_path)
        
        self.qemu_system_path = QLineEdit()
        paths_layout.addRow("QEMU-System Path:", self.qemu_system_path)
        
        auto_detect_btn = QPushButton("Auto-Detect")
        auto_detect_btn.clicked.connect(self.auto_detect_paths)
        paths_layout.addRow("", auto_detect_btn)
        
        paths_group.setLayout(paths_layout)
        qemu_layout.addWidget(paths_group)
        
        # VM Options
        vm_options_group = QGroupBox("Default VM Options")
        vm_options_layout = QFormLayout()
        
        self.default_display = QComboBox()
        self.default_display.addItems(["gtk", "sdl", "vnc", "spice"])
        vm_options_layout.addRow("Display:", self.default_display)
        
        self.enable_kvm = QCheckBox("Enable KVM acceleration when available")
        vm_options_layout.addRow("", self.enable_kvm)
        
        self.enable_audio = QCheckBox("Enable audio")
        vm_options_layout.addRow("", self.enable_audio)
        
        vm_options_group.setLayout(vm_options_layout)
        qemu_layout.addWidget(vm_options_group)
        
        # Additional command line options
        additional_options_group = QGroupBox("Additional Options")
        additional_options_layout = QFormLayout()
        
        self.additional_vm_options = QLineEdit()
        additional_options_layout.addRow("Additional VM Options:", self.additional_vm_options)
        
        additional_options_group.setLayout(additional_options_layout)
        qemu_layout.addWidget(additional_options_group)
        
        qemu_tab.setLayout(qemu_layout)
        tabs.addTab(qemu_tab, "QEMU Settings")
        
        # Interface Tab
        interface_tab = QWidget()
        interface_layout = QVBoxLayout()
        
        # UI Options
        ui_options_group = QGroupBox("UI Options")
        ui_options_layout = QFormLayout()
        
        self.confirm_vm_start = QCheckBox("Confirm VM start")
        self.confirm_vm_start.setChecked(True)
        ui_options_layout.addRow("", self.confirm_vm_start)
        
        self.confirm_deletion = QCheckBox("Confirm deletions")
        self.confirm_deletion.setChecked(True)
        ui_options_layout.addRow("", self.confirm_deletion)
        
        self.show_tooltips = QCheckBox("Show tooltips")
        self.show_tooltips.setChecked(True)
        ui_options_layout.addRow("", self.show_tooltips)
        
        ui_options_group.setLayout(ui_options_layout)
        interface_layout.addWidget(ui_options_group)
        
        # Data paths
        data_paths_group = QGroupBox("Data Paths")
        data_paths_layout = QFormLayout()
        
        self.disks_path = QLineEdit()
        self.disks_path.setReadOnly(True)  # Make this read-only for now
        data_paths_layout.addRow("Disks Directory:", self.disks_path)
        
        self.vms_path = QLineEdit()
        self.vms_path.setReadOnly(True)  # Make this read-only for now
        data_paths_layout.addRow("VMs Directory:", self.vms_path)
        
        self.isos_path = QLineEdit()
        self.isos_path.setReadOnly(True)  # Make this read-only for now
        data_paths_layout.addRow("ISOs Directory:", self.isos_path)
        
        data_paths_group.setLayout(data_paths_layout)
        interface_layout.addWidget(data_paths_group)
        
        interface_tab.setLayout(interface_layout)
        tabs.addTab(interface_tab, "Interface Settings")
        
        layout.addWidget(tabs)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        restore_defaults_btn = QPushButton("Restore Defaults")
        restore_defaults_btn.clicked.connect(self.restore_defaults)
        button_layout.addWidget(restore_defaults_btn)
        
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_settings)
        button_layout.addWidget(save_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def load_settings(self):
        """Load settings from QSettings"""
        # QEMU paths
        self.qemu_img_path.setText(self.settings.value("qemu/img_path", "qemu-img", str))
        self.qemu_system_path.setText(self.settings.value("qemu/system_path", "qemu-system-x86_64", str))
        
        # VM options
        self.default_display.setCurrentText(self.settings.value("qemu/default_display", "gtk", str))
        self.enable_kvm.setChecked(self.settings.value("qemu/enable_kvm", True, bool))
        self.enable_audio.setChecked(self.settings.value("qemu/enable_audio", True, bool))
        self.additional_vm_options.setText(self.settings.value("qemu/additional_options", "", str))
        
        # UI options
        self.confirm_vm_start.setChecked(self.settings.value("ui/confirm_vm_start", True, bool))
        self.confirm_deletion.setChecked(self.settings.value("ui/confirm_deletion", True, bool))
        self.show_tooltips.setChecked(self.settings.value("ui/show_tooltips", True, bool))
        
        # Data paths
        self.disks_path.setText(self.settings.value("paths/disks", os.path.abspath("data/disks"), str))
        self.vms_path.setText(self.settings.value("paths/vms", os.path.abspath("data/vms"), str))
        self.isos_path.setText(self.settings.value("paths/isos", os.path.abspath("data/isos"), str))
    
    def auto_detect_paths(self):
        """Try to auto-detect QEMU paths"""
        import shutil
        
        qemu_img_path = shutil.which("qemu-img")
        qemu_system_path = shutil.which("qemu-system-x86_64")
        
        if qemu_img_path:
            self.qemu_img_path.setText(qemu_img_path)
        
        if qemu_system_path:
            self.qemu_system_path.setText(qemu_system_path)
        
        if not qemu_img_path and not qemu_system_path:
            QMessageBox.warning(
                self, 
                "QEMU Not Found", 
                "Could not auto-detect QEMU paths. Make sure QEMU is installed and in your PATH."
            )
    
    def restore_defaults(self):
        """Restore default settings"""
        # QEMU paths
        self.qemu_img_path.setText("qemu-img")
        self.qemu_system_path.setText("qemu-system-x86_64")
        
        # VM options
        self.default_display.setCurrentText("gtk")
        self.enable_kvm.setChecked(True)
        self.enable_audio.setChecked(True)
        self.additional_vm_options.clear()
        
        # UI options
        self.confirm_vm_start.setChecked(True)
        self.confirm_deletion.setChecked(True)
        self.show_tooltips.setChecked(True)
    
    def save_settings(self):
        """Save settings to QSettings"""
        # QEMU paths
        self.settings.setValue("qemu/img_path", self.qemu_img_path.text())
        self.settings.setValue("qemu/system_path", self.qemu_system_path.text())
        
        # VM options
        self.settings.setValue("qemu/default_display", self.default_display.currentText())
        self.settings.setValue("qemu/enable_kvm", self.enable_kvm.isChecked())
        self.settings.setValue("qemu/enable_audio", self.enable_audio.isChecked())
        self.settings.setValue("qemu/additional_options", self.additional_vm_options.text())
        
        # UI options
        self.settings.setValue("ui/confirm_vm_start", self.confirm_vm_start.isChecked())
        self.settings.setValue("ui/confirm_deletion", self.confirm_deletion.isChecked())
        self.settings.setValue("ui/show_tooltips", self.show_tooltips.isChecked())
        
        # Data paths - these are currently read-only, but keep them in settings
        self.settings.setValue("paths/disks", self.disks_path.text())
        self.settings.setValue("paths/vms", self.vms_path.text())
        self.settings.setValue("paths/isos", self.isos_path.text())
        
        self.settings.sync()
        
        QMessageBox.information(self, "Settings Saved", "Settings have been saved successfully.")
        self.accept()
