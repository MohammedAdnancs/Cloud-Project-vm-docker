import unittest
import os
import json
import shutil
from unittest.mock import patch, MagicMock
from services.vm_manager import VMManager
from services.disk_manager import DiskManager

class TestVMManager(unittest.TestCase):
    """Unit tests for the VMManager class"""
    
    def setUp(self):
        """Set up test environment before each test"""
        # Create test directories
        self.test_vms_dir = os.path.join('test_data', 'vms')
        self.test_isos_dir = os.path.join('test_data', 'isos')
        self.test_disks_dir = os.path.join('test_data', 'disks')
        
        # Clean up and recreate test directories
        for dir_path in [self.test_vms_dir, self.test_isos_dir, self.test_disks_dir]:
            if os.path.exists(dir_path):
                shutil.rmtree(dir_path)
            os.makedirs(dir_path, exist_ok=True)
        
        # Registry files paths
        self.vm_registry_file = os.path.join('test_data', 'vm_registry.json')
        self.disk_registry_file = os.path.join('test_data', 'disk_registry.json')
        
        # Create parent directory for registry files
        os.makedirs(os.path.dirname(self.vm_registry_file), exist_ok=True)
        
        # Create a disk manager with test directories
        self.disk_manager = DiskManager(disks_dir=self.test_disks_dir)
        self.disk_manager.registry_file = self.disk_registry_file
        
        # Create a test disk for VM tests
        self.test_disk_name = "test_disk"
        self.test_disk_path = os.path.join(self.test_disks_dir, f"{self.test_disk_name}.qcow2")
        
        # Create an empty disk file
        with open(self.test_disk_path, 'w') as f:
            f.write('')
        
        # Add the test disk to disk manager registry
        self.disk_manager.registry = {
            self.test_disk_name: {
                'path': self.test_disk_path,
                'format': 'qcow2',
                'size': 10737418240,
                'created_time': 1621234567.0
            }
        }
        self.disk_manager._save_registry()
        
        # Create a VM manager with test directories
        self.vm_manager = VMManager(vms_dir=self.test_vms_dir, isos_dir=self.test_isos_dir)
        self.vm_manager.registry_file = self.vm_registry_file
        
        # Replace the disk_manager with our test instance
        self.vm_manager.disk_manager = self.disk_manager
        
        # Create a test ISO file
        self.test_iso_path = os.path.join(self.test_isos_dir, "test.iso")
        with open(self.test_iso_path, 'w') as f:
            f.write('')
    
    def tearDown(self):
        """Clean up after each test"""
        if os.path.exists('test_data'):
            shutil.rmtree('test_data')
    
    def test_create_vm_success(self):
        """Test creating a VM with valid parameters"""
        # Create a VM
        vm_name = "test_vm"
        memory = 1024
        cpus = 2
        
        success, message = self.vm_manager.create_vm(vm_name, memory, cpus, self.test_disk_name)
        
        # Verify VM was created successfully
        self.assertTrue(success)
        self.assertEqual(message, f"Successfully created VM {vm_name}")
        
        # Verify the VM is in the registry
        self.assertIn(vm_name, self.vm_manager.registry)
        self.assertEqual(self.vm_manager.registry[vm_name]['memory'], memory)
        self.assertEqual(self.vm_manager.registry[vm_name]['cpus'], cpus)
        self.assertEqual(self.vm_manager.registry[vm_name]['disk'], self.test_disk_path)
        
        # Verify the config file was created
        config_path = os.path.join(self.test_vms_dir, f"{vm_name}.json")
        self.assertTrue(os.path.exists(config_path))
        
        # Verify config file contents
        with open(config_path, 'r') as f:
            config = json.load(f)
        self.assertEqual(config['name'], vm_name)
        self.assertEqual(config['memory'], memory)
        self.assertEqual(config['cpus'], cpus)
        self.assertEqual(config['disk'], self.test_disk_path)
    
    def test_create_vm_with_iso(self):
        """Test creating a VM with an ISO file"""
        vm_name = "test_vm_with_iso"
        memory = 1024
        cpus = 1
        
        success, message = self.vm_manager.create_vm(vm_name, memory, cpus, self.test_disk_name, self.test_iso_path)
        
        # Verify VM was created successfully
        self.assertTrue(success)
        self.assertEqual(message, f"Successfully created VM {vm_name}")
        
        # Verify the VM is in the registry with ISO
        self.assertIn(vm_name, self.vm_manager.registry)
        self.assertEqual(self.vm_manager.registry[vm_name]['iso'], self.test_iso_path)
        
        # Verify config file contents includes ISO and first_boot flag
        config_path = os.path.join(self.test_vms_dir, f"{vm_name}.json")
        with open(config_path, 'r') as f:
            config = json.load(f)
        self.assertEqual(config['iso'], self.test_iso_path)
        self.assertTrue(config['first_boot'])
    
    def test_create_vm_invalid_name(self):
        """Test creating a VM with invalid name"""
        # Test empty name
        success, message = self.vm_manager.create_vm("", 1024, 1, self.test_disk_name)
        self.assertFalse(success)
        self.assertEqual(message, "VM name cannot be empty")
        
        # Test invalid characters in name
        success, message = self.vm_manager.create_vm("invalid/name", 1024, 1, self.test_disk_name)
        self.assertFalse(success)
        self.assertEqual(message, "VM name can only contain letters, numbers, underscores, hyphens, and periods")
    
    def test_create_vm_invalid_memory(self):
        """Test creating a VM with invalid memory settings"""
        # Test negative memory
        success, message = self.vm_manager.create_vm("test_vm", -1024, 1, self.test_disk_name)
        self.assertFalse(success)
        self.assertEqual(message, "Memory must be greater than zero")
        
        # Test memory too low
        success, message = self.vm_manager.create_vm("test_vm", 100, 1, self.test_disk_name)
        self.assertFalse(success)
        self.assertEqual(message, "Memory must be at least 128 MB")
        
        # Test memory too high
        success, message = self.vm_manager.create_vm("test_vm", 1000000, 1, self.test_disk_name)
        self.assertFalse(success)
        self.assertEqual(message, "Memory exceeds maximum allowed (32 GB)")
    
    def test_create_vm_invalid_cpus(self):
        """Test creating a VM with invalid CPU settings"""
        # Test negative CPUs
        success, message = self.vm_manager.create_vm("test_vm", 1024, -1, self.test_disk_name)
        self.assertFalse(success)
        self.assertEqual(message, "CPU count must be greater than zero")
        
        # Test too many CPUs
        success, message = self.vm_manager.create_vm("test_vm", 1024, 32, self.test_disk_name)
        self.assertFalse(success)
        self.assertEqual(message, "CPU count exceeds maximum allowed (16)")
    
    def test_create_vm_nonexistent_disk(self):
        """Test creating a VM with a disk that doesn't exist"""
        success, message = self.vm_manager.create_vm("test_vm", 1024, 1, "nonexistent_disk")
        self.assertFalse(success)
        self.assertEqual(message, "Disk nonexistent_disk not found")
    
    def test_create_vm_duplicate_name(self):
        """Test creating a VM with a name that already exists"""
        # Create a VM first
        self.vm_manager.create_vm("test_vm", 1024, 1, self.test_disk_name)
        
        # Try to create another VM with the same name
        success, message = self.vm_manager.create_vm("test_vm", 2048, 2, self.test_disk_name)
        self.assertFalse(success)
        self.assertEqual(message, "VM test_vm already exists")
    
    def test_list_vms(self):
        """Test listing available VMs"""
        # Create a test VM
        self.vm_manager.create_vm("test_vm", 1024, 1, self.test_disk_name)
        
        # Get the list of VMs
        vms = self.vm_manager.list_vms()
        
        # Verify the test VM is in the list
        self.assertIn("test_vm", vms)
        self.assertEqual(vms["test_vm"]["memory"], 1024)
        self.assertEqual(vms["test_vm"]["cpus"], 1)
    
    def test_list_isos(self):
        """Test listing available ISO files"""
        # Get the list of ISOs
        isos = self.vm_manager.list_isos()
        
        # Verify the test ISO is in the list
        self.assertIn(self.test_iso_path, isos)
    
    @patch('subprocess.Popen')
    @patch('subprocess.run')
    def test_start_vm(self, mock_run, mock_popen):
        """Test starting a VM"""
        # Configure the mock process
        mock_process = MagicMock()
        mock_process.poll.return_value = None  # Process is still running
        mock_popen.return_value = mock_process
        
        # Configure the run mock for qemu-img info
        mock_run_result = MagicMock()
        mock_run_result.stdout = '{"format": "qcow2"}'
        mock_run_result.returncode = 0
        mock_run.return_value = mock_run_result
        
        # Create a test VM
        vm_name = "test_vm"
        self.vm_manager.create_vm(vm_name, 1024, 1, self.test_disk_name)
        
        # Start the VM
        success, message = self.vm_manager.start_vm(vm_name)
        
        # Verify the VM was started successfully
        self.assertTrue(success)
        self.assertEqual(message, f"Successfully started VM {vm_name}")
        
        # Verify subprocess.Popen was called with the correct command
        mock_popen.assert_called()
        # Extract the first argument (the command) from the call
        cmd = mock_popen.call_args[0][0]
        self.assertEqual(cmd[0], "qemu-system-x86_64")
        self.assertIn("-m", cmd)
        self.assertIn("1024", cmd)
        self.assertIn("-smp", cmd)
        self.assertIn("1", cmd)
    
    def test_start_nonexistent_vm(self):
        """Test starting a VM that doesn't exist"""
        success, message = self.vm_manager.start_vm("nonexistent_vm")
        self.assertFalse(success)
        self.assertEqual(message, "VM nonexistent_vm not found")
    
    def test_delete_vm(self):
        """Test deleting a VM"""
        # Create a test VM
        vm_name = "test_vm"
        self.vm_manager.create_vm(vm_name, 1024, 1, self.test_disk_name)
        
        # Delete the VM
        success, message = self.vm_manager.delete_vm(vm_name)
        
        # Verify the VM was deleted successfully
        self.assertTrue(success)
        self.assertEqual(message, f"Successfully deleted VM {vm_name}")
        
        # Verify the VM is no longer in the registry
        self.assertNotIn(vm_name, self.vm_manager.registry)
        
        # Verify the config file was deleted
        config_path = os.path.join(self.test_vms_dir, f"{vm_name}.json")
        self.assertFalse(os.path.exists(config_path))
    
    def test_delete_nonexistent_vm(self):
        """Test deleting a VM that doesn't exist"""
        success, message = self.vm_manager.delete_vm("nonexistent_vm")
        self.assertFalse(success)
        self.assertEqual(message, "VM nonexistent_vm not found")
    
    def test_validate_registry(self):
        """Test VM registry validation"""
        # Create a registry with a VM that doesn't exist
        self.vm_manager.registry = {
            "nonexistent_vm": {
                "config_path": os.path.join(self.test_vms_dir, "nonexistent_vm.json"),
                "disk": self.test_disk_path,
                "memory": 1024,
                "cpus": 1,
                "iso": "",
                "created_time": 1621234567.0
            }
        }
        
        # Create a VM config file that isn't in the registry
        vm_name = "unlisted_vm"
        config_path = os.path.join(self.test_vms_dir, f"{vm_name}.json")
        config = {
            "name": vm_name,
            "memory": 2048,
            "cpus": 2,
            "disk": self.test_disk_path,
            "iso": "",
            "first_boot": False
        }
        
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, 'w') as f:
            json.dump(config, f)
        
        # Run the validation
        self.vm_manager._validate_registry()
        
        # Verify the nonexistent VM was removed from registry
        self.assertNotIn("nonexistent_vm", self.vm_manager.registry)
        
        # Verify the unlisted VM was added to registry
        self.assertIn(vm_name, self.vm_manager.registry)
        self.assertEqual(self.vm_manager.registry[vm_name]["memory"], 2048)
        self.assertEqual(self.vm_manager.registry[vm_name]["cpus"], 2)

if __name__ == '__main__':
    unittest.main() 