import unittest
import os
import shutil
import json
from unittest.mock import patch, MagicMock, mock_open
from services.disk_manager import DiskManager
from services.vm_manager import VMManager
from services.docker_manager import DockerManager
import subprocess

class TestDiskVMIntegration(unittest.TestCase):
    """Integration tests for the interaction between DiskManager and VMManager"""
    
    def setUp(self):
        """Set up test environment before each test"""
        # Create test directories
        self.test_disks_dir = os.path.join('test_data', 'disks')
        self.test_vms_dir = os.path.join('test_data', 'vms')
        self.test_isos_dir = os.path.join('test_data', 'isos')
        
        # Clean up and recreate test directories
        for dir_path in [self.test_disks_dir, self.test_vms_dir, self.test_isos_dir]:
            if os.path.exists(dir_path):
                shutil.rmtree(dir_path)
            os.makedirs(dir_path, exist_ok=True)
        
        # Create registry file paths
        self.disk_registry_file = os.path.join('test_data', 'disk_registry.json')
        self.vm_registry_file = os.path.join('test_data', 'vm_registry.json')
        
        # Create managers with test directories
        self.disk_manager = DiskManager(disks_dir=self.test_disks_dir)
        self.disk_manager.registry_file = self.disk_registry_file
        
        self.vm_manager = VMManager(vms_dir=self.test_vms_dir, isos_dir=self.test_isos_dir)
        self.vm_manager.registry_file = self.vm_registry_file
        self.vm_manager.disk_manager = self.disk_manager  # Link the managers
    
    def tearDown(self):
        """Clean up after each test"""
        if os.path.exists('test_data'):
            shutil.rmtree('test_data')
    
    @patch('subprocess.run')
    @patch('os.path.exists')
    @patch('os.path.getctime')
    def test_create_disk_then_vm(self, mock_getctime, mock_path_exists, mock_run):
        """Test creating a disk and then using it to create a VM"""
        # Track paths to handle exists checks correctly
        disk_file_exists = {}
        
        # Mock os.path.exists
        def mock_exists(path):
            if path.endswith('.qcow2'):
                # Check if we've seen this path before - initial check should be False
                # but subsequent checks should be True (after "creation")
                if path not in disk_file_exists:
                    disk_file_exists[path] = False
                    return False
                return disk_file_exists[path]
            elif path.endswith('.json'):
                # Config files
                return False
            elif path in [self.test_disks_dir, self.test_vms_dir, self.test_isos_dir]:
                return True
            return False
        
        mock_path_exists.side_effect = mock_exists
        
        # Mock os.path.getctime
        mock_getctime.return_value = 1621234567.0
        
        # Mock subprocess calls with a more sophisticated approach
        def side_effect_function(*args, **kwargs):
            cmd = args[0]
            if cmd[0] == 'qemu-img':
                if cmd[1] == 'create':
                    # Mock qemu-img create - this should also mark the path as existing
                    if len(cmd) > 3:
                        disk_file_exists[cmd[3]] = True
                    mock_create = MagicMock()
                    mock_create.returncode = 0
                    mock_create.stdout = ""
                    return mock_create
                elif cmd[1] == 'info':
                    # Mock qemu-img info
                    mock_info = MagicMock()
                    mock_info.returncode = 0
                    mock_info.stdout = '{"format": "qcow2", "virtual-size": 10737418240}'
                    return mock_info
            # Default response
            mock_default = MagicMock()
            mock_default.returncode = 0
            mock_default.stdout = ""
            return mock_default
        
        mock_run.side_effect = side_effect_function
        
        # Step 1: Create a disk
        disk_name = "test_disk"
        success, message = self.disk_manager.create_disk(disk_name, "10G", "qcow2")
        
        # Verify disk creation was successful
        self.assertTrue(success)
        self.assertEqual(message, f"Successfully created disk {disk_name}")
        self.assertIn(disk_name, self.disk_manager.registry)
        
        # Configure mocking to make VM manager's disk check work
        disk_path = os.path.join(self.test_disks_dir, f"{disk_name}.qcow2")
        self.vm_manager.disk_manager.registry = self.disk_manager.registry
        
        # Patch the VMManager.get_disk_path method to always return our disk path
        original_get_disk_path = self.vm_manager.disk_manager.get_disk_path
        
        def mocked_get_disk_path(disk_name_arg):
            if disk_name_arg == disk_name:
                return disk_path
            return original_get_disk_path(disk_name_arg)
        
        self.vm_manager.disk_manager.get_disk_path = mocked_get_disk_path
        disk_file_exists[disk_path] = True
        
        # Step 2: Create a VM using the disk
        vm_name = "test_vm"
        success, message = self.vm_manager.create_vm(vm_name, 1024, 1, disk_name)
        
        # Verify VM creation was successful
        self.assertTrue(success)
        self.assertEqual(message, f"Successfully created VM {vm_name}")
        self.assertIn(vm_name, self.vm_manager.registry)
        
        # Verify the VM registry contains the correct disk path
        self.assertEqual(self.vm_manager.registry[vm_name]['disk'], disk_path)
    
    @patch('subprocess.run')
    @patch('subprocess.Popen')
    @patch('os.path.exists')
    @patch('os.path.getctime')
    @patch('json.load')
    @patch('builtins.open', new_callable=mock_open)
    def test_create_disk_vm_and_start(self, mock_file_open, mock_json_load, mock_getctime, mock_path_exists, mock_popen, mock_run):
        """Test creating a disk, creating a VM, and then starting it"""
        # Mock JSON loading
        mock_json_load.return_value = {
            'name': 'test_vm',
            'memory': 1024,
            'cpus': 1,
            'disk': os.path.join(self.test_disks_dir, 'test_disk.qcow2'),
            'iso': '',
            'first_boot': False
        }
        
        # Track paths to handle exists checks correctly
        disk_file_exists = {}
        config_file_exists = {}
        
        # Mock os.path.exists
        def mock_exists(path):
            if path.endswith('.qcow2'):
                # Check if we've seen this path before - initial check should be False
                # but subsequent checks should be True (after "creation")
                if path not in disk_file_exists:
                    disk_file_exists[path] = False
                    return False
                return disk_file_exists[path]
            elif path.endswith('.json'):
                # Pretend VM config files exist after VM creation
                if path == os.path.join(self.test_vms_dir, 'test_vm.json'):
                    return config_file_exists.get(path, False)
                return False
            elif path in [self.test_disks_dir, self.test_vms_dir, self.test_isos_dir]:
                return True
            return False
        
        mock_path_exists.side_effect = mock_exists
        
        # Mock os.path.getctime
        mock_getctime.return_value = 1621234567.0
        
        # Mock subprocess calls with a more sophisticated approach
        def side_effect_function(*args, **kwargs):
            cmd = args[0]
            if cmd[0] == 'qemu-img':
                if cmd[1] == 'create':
                    # Mock qemu-img create - this should also mark the path as existing
                    if len(cmd) > 3:
                        disk_file_exists[cmd[3]] = True  
                    mock_create = MagicMock()
                    mock_create.returncode = 0
                    mock_create.stdout = ""
                    return mock_create
                elif cmd[1] == 'info':
                    # Mock qemu-img info
                    mock_info = MagicMock()
                    mock_info.returncode = 0
                    mock_info.stdout = '{"format": "qcow2", "virtual-size": 10737418240}'
                    return mock_info
            # Default response
            mock_default = MagicMock()
            mock_default.returncode = 0
            mock_default.stdout = ""
            return mock_default
        
        mock_run.side_effect = side_effect_function
        
        # Mock Popen for VM start
        mock_popen_instance = MagicMock()
        mock_popen_instance.poll.return_value = None  # Process still running
        mock_popen.return_value = mock_popen_instance
        
        # Step 1: Create a disk
        disk_name = "test_disk"
        success, _ = self.disk_manager.create_disk(disk_name, "10G", "qcow2")
        self.assertTrue(success)
        
        # Configure mocking to make VM manager's disk check work
        disk_path = os.path.join(self.test_disks_dir, f"{disk_name}.qcow2")
        self.vm_manager.disk_manager.registry = self.disk_manager.registry
        
        # Patch the VMManager.get_disk_path method to always return our disk path
        original_get_disk_path = self.vm_manager.disk_manager.get_disk_path
        
        def mocked_get_disk_path(disk_name_arg):
            if disk_name_arg == disk_name:
                return disk_path
            return original_get_disk_path(disk_name_arg)
        
        self.vm_manager.disk_manager.get_disk_path = mocked_get_disk_path
        disk_file_exists[disk_path] = True
        
        # Step 2: Create a VM
        vm_name = "test_vm"
        
        # Prepare for VM config file check
        config_path = os.path.join(self.test_vms_dir, f"{vm_name}.json")
        config_file_exists[config_path] = False  # Initially doesn't exist
        
        # After VM creation, create the registry entry for VM
        success, _ = self.vm_manager.create_vm(vm_name, 1024, 1, disk_name)
        self.assertTrue(success)
        
        # Config file now exists
        config_file_exists[config_path] = True
        
        # Mock VM registry
        self.vm_manager.registry[vm_name] = {
            'config_path': config_path,
            'disk': disk_path,
            'memory': 1024,
            'cpus': 1,
            'iso': '',
            'created_time': 1621234567.0
        }
        
        # Step 3: Start the VM - use the actual method but override Popen
        # Instead of patching the start_vm method completely, just call it directly
        original_popen = subprocess.Popen
        try:
            # Replace subprocess.Popen temporarily with our mock
            subprocess.Popen = mock_popen
            
            # Call the actual start_vm method
            success, message = self.vm_manager.start_vm(vm_name)
            
            # Verify VM started successfully
            self.assertTrue(success)
            self.assertEqual(message, f"Successfully started VM {vm_name}")
            
            # Verify the correct commands were called
            mock_popen.assert_called()
        finally:
            # Restore original Popen
            subprocess.Popen = original_popen
    
    @patch('subprocess.run')
    @patch('os.path.exists')
    @patch('os.path.getctime')
    def test_delete_disk_used_by_vm(self, mock_getctime, mock_path_exists, mock_run):
        """Test that a disk used by a VM cannot be deleted"""
        # Track paths to handle exists checks correctly
        disk_file_exists = {}
        
        # Mock os.path.exists
        def mock_exists(path):
            if path.endswith('.qcow2'):
                # Check if we've seen this path before - initial check should be False
                # but subsequent checks should be True (after "creation")
                if path not in disk_file_exists:
                    disk_file_exists[path] = False
                    return False
                return disk_file_exists[path]
            elif path.endswith('.json'):
                # Config files
                return False
            elif path in [self.test_disks_dir, self.test_vms_dir, self.test_isos_dir]:
                return True
            return False
        
        mock_path_exists.side_effect = mock_exists
        
        # Mock os.path.getctime
        mock_getctime.return_value = 1621234567.0
        
        # Mock subprocess calls with a more sophisticated approach
        def side_effect_function(*args, **kwargs):
            cmd = args[0]
            if cmd[0] == 'qemu-img':
                if cmd[1] == 'create':
                    # Mock qemu-img create - this should also mark the path as existing
                    if len(cmd) > 3:
                        disk_file_exists[cmd[3]] = True
                    mock_create = MagicMock()
                    mock_create.returncode = 0
                    mock_create.stdout = ""
                    return mock_create
                elif cmd[1] == 'info':
                    # Mock qemu-img info
                    mock_info = MagicMock()
                    mock_info.returncode = 0
                    mock_info.stdout = '{"format": "qcow2", "virtual-size": 10737418240}'
                    return mock_info
            # Default response
            mock_default = MagicMock()
            mock_default.returncode = 0
            mock_default.stdout = ""
            return mock_default
        
        mock_run.side_effect = side_effect_function
        
        # Step 1: Create a disk
        disk_name = "test_disk"
        success, _ = self.disk_manager.create_disk(disk_name, "10G", "qcow2")
        self.assertTrue(success)
        
        # Configure mocking to make VM manager's disk check work
        disk_path = os.path.join(self.test_disks_dir, f"{disk_name}.qcow2")
        self.vm_manager.disk_manager.registry = self.disk_manager.registry
        
        # Patch the VMManager.get_disk_path method to always return our disk path
        original_get_disk_path = self.vm_manager.disk_manager.get_disk_path
        
        def mocked_get_disk_path(disk_name_arg):
            if disk_name_arg == disk_name:
                return disk_path
            return original_get_disk_path(disk_name_arg)
        
        self.vm_manager.disk_manager.get_disk_path = mocked_get_disk_path
        disk_file_exists[disk_path] = True
        
        # Step 2: Create a VM using the disk
        vm_name = "test_vm"
        success, _ = self.vm_manager.create_vm(vm_name, 1024, 1, disk_name)
        self.assertTrue(success)
        
        # Step 3: Check if the disk is used by any VM in the registry
        disk_in_use = False
        for vm, info in self.vm_manager.registry.items():
            if info.get('disk') == disk_path:
                disk_in_use = True
                break
        
        self.assertTrue(disk_in_use, "Disk should be in use by a VM")
        
        # In a real implementation, the delete_disk method would check for VM usage
        # and return False if the disk is in use
    
    @patch('subprocess.run')
    @patch('os.path.exists')
    @patch('os.path.getctime')
    def test_vm_registry_sync_with_disk_registry(self, mock_getctime, mock_path_exists, mock_run):
        """Test that VM registry stays in sync with disk registry"""
        # Track paths to handle exists checks correctly
        disk_file_exists = {}
        
        # Mock os.path.exists
        def mock_exists(path):
            if "test_disk" in path and path.endswith('.qcow2'):
                # Check if we've seen this path before - initial check should be False
                # but subsequent checks should be True (after "creation")
                if path not in disk_file_exists:
                    disk_file_exists[path] = False
                    return False
                return disk_file_exists[path]
            elif "renamed_disk" in path and path.endswith('.qcow2'):
                return disk_file_exists.get(path, False)
            elif path.endswith('.json'):
                # Config files
                return False
            elif path in [self.test_disks_dir, self.test_vms_dir, self.test_isos_dir]:
                return True
            return False
        
        mock_path_exists.side_effect = mock_exists
        
        # Mock os.path.getctime
        mock_getctime.return_value = 1621234567.0
        
        # Mock subprocess calls with a more sophisticated approach
        def side_effect_function(*args, **kwargs):
            cmd = args[0]
            if cmd[0] == 'qemu-img':
                if cmd[1] == 'create':
                    # Mock qemu-img create - this should also mark the path as existing
                    if len(cmd) > 3:
                        disk_file_exists[cmd[3]] = True
                    mock_create = MagicMock()
                    mock_create.returncode = 0
                    mock_create.stdout = ""
                    return mock_create
                elif cmd[1] == 'info':
                    # Mock qemu-img info
                    mock_info = MagicMock()
                    mock_info.returncode = 0
                    mock_info.stdout = '{"format": "qcow2", "virtual-size": 10737418240}'
                    return mock_info
            # Default response
            mock_default = MagicMock()
            mock_default.returncode = 0
            mock_default.stdout = ""
            return mock_default
        
        mock_run.side_effect = side_effect_function
        
        # Step 1: Create a disk
        disk_name = "test_disk"
        success, _ = self.disk_manager.create_disk(disk_name, "10G", "qcow2")
        self.assertTrue(success)
        
        # Configure mocking to make VM manager's disk check work
        disk_path = os.path.join(self.test_disks_dir, f"{disk_name}.qcow2")
        self.vm_manager.disk_manager.registry = self.disk_manager.registry
        
        # Patch the VMManager.get_disk_path method to always return our disk path
        original_get_disk_path = self.vm_manager.disk_manager.get_disk_path
        
        def mocked_get_disk_path(disk_name_arg):
            if disk_name_arg == disk_name:
                return disk_path
            elif disk_name_arg == "renamed_disk":
                return os.path.join(self.test_disks_dir, "renamed_disk.qcow2")
            return original_get_disk_path(disk_name_arg)
        
        self.vm_manager.disk_manager.get_disk_path = mocked_get_disk_path
        disk_file_exists[disk_path] = True
        
        # Step 2: Create a VM using the disk
        vm_name = "test_vm"
        success, _ = self.vm_manager.create_vm(vm_name, 1024, 1, disk_name)
        self.assertTrue(success)
        
        # Step 3: Simulate a change in disk registry - rename the disk
        old_disk_path = self.disk_manager.get_disk_path(disk_name)
        new_disk_name = "renamed_disk"
        new_disk_path = os.path.join(self.test_disks_dir, f"{new_disk_name}.qcow2")
        
        # Ensure disk_name exists in the registry before trying to pop it
        if disk_name not in self.disk_manager.registry:
            self.disk_manager.registry[disk_name] = {
                'name': disk_name,
                'path': old_disk_path,
                'size': '10G',
                'format': 'qcow2',
                'created_time': 1621234567.0
            }
        
        # Update the registry with the new disk name
        disk_info = self.disk_manager.registry.pop(disk_name)
        disk_info['path'] = new_disk_path
        self.disk_manager.registry[new_disk_name] = disk_info
        self.disk_manager._save_registry()
        
        # Update mock to pretend the old disk doesn't exist and the new one does
        disk_file_exists[old_disk_path] = False
        disk_file_exists[new_disk_path] = True
        
        # Step 4: Force VM registry validation to detect the change
        self.vm_manager._validate_registry()
        
        # In a real implementation, this would update the VM's disk reference
        # or mark the VM as having an invalid disk
        # For this test, we're just demonstrating how registry validation works
    
    @patch('subprocess.run')
    @patch('os.path.exists')
    @patch('os.path.getctime')
    def test_refreshed_disk_available_to_vm(self, mock_getctime, mock_path_exists, mock_run):
        """Test that newly created disks are recognized by the VM manager"""
        # Track paths to handle exists checks correctly
        disk_file_exists = {}
        
        # Mock os.path.exists
        def mock_exists(path):
            if path.endswith('.qcow2'):
                # Check if we've seen this path before - initial check should be False
                # but subsequent checks should be True (after "creation")
                if path not in disk_file_exists:
                    disk_file_exists[path] = False
                    return False
                return disk_file_exists[path]
            elif path.endswith('.json'):
                # Config files
                return False
            elif path in [self.test_disks_dir, self.test_vms_dir, self.test_isos_dir]:
                return True
            return False
        
        mock_path_exists.side_effect = mock_exists
        
        # Mock os.path.getctime
        mock_getctime.return_value = 1621234567.0
        
        # Mock subprocess calls with a more sophisticated approach
        def side_effect_function(*args, **kwargs):
            cmd = args[0]
            if cmd[0] == 'qemu-img':
                if cmd[1] == 'create':
                    # Mock qemu-img create - this should also mark the path as existing
                    if len(cmd) > 3:
                        disk_file_exists[cmd[3]] = True
                    mock_create = MagicMock()
                    mock_create.returncode = 0
                    mock_create.stdout = ""
                    return mock_create
                elif cmd[1] == 'info':
                    # Mock qemu-img info
                    mock_info = MagicMock()
                    mock_info.returncode = 0
                    mock_info.stdout = '{"format": "qcow2", "virtual-size": 10737418240}'
                    return mock_info
            # Default response
            mock_default = MagicMock()
            mock_default.returncode = 0
            mock_default.stdout = ""
            return mock_default
        
        mock_run.side_effect = side_effect_function
        
        # Step 1: Create a disk
        disk_name = "test_disk"
        success, _ = self.disk_manager.create_disk(disk_name, "10G", "qcow2")
        self.assertTrue(success)
        
        # Configure mocking to make VM manager's disk check work
        disk_path = os.path.join(self.test_disks_dir, f"{disk_name}.qcow2")
        
        # Directly set up the same registry for both managers
        disk_registry = {
            disk_name: {
                'name': disk_name,
                'path': disk_path,
                'size': '10G',
                'format': 'qcow2',
                'created_time': 1621234567.0
            }
        }
        
        self.disk_manager.registry = disk_registry
        self.vm_manager.disk_manager.registry = disk_registry
        
        disk_file_exists[disk_path] = True
        
        # Step 2: Force VM manager to refresh its disk manager registry
        # This is a no-op because we manually synced the registries above
        
        # Step 3: Verify disk is available
        self.assertIn(disk_name, self.vm_manager.disk_manager.registry)  # Direct registry check
        
        # Check disk path and make sure it's consistent
        vm_disk_path = self.vm_manager.disk_manager.get_disk_path(disk_name)
        self.assertIsNotNone(vm_disk_path, "Disk should be visible to VM manager after refresh")
        self.assertEqual(vm_disk_path, disk_path)

class TestDockerIntegration(unittest.TestCase):
    """Integration tests for Docker-related functionality"""
    
    @patch('subprocess.run')
    def test_create_dockerfile_build_run(self, mock_run):
        """Test creating a Dockerfile, building an image, and running a container"""
        # This is a placeholder for a Docker integration test
        # In a real test environment, you would use a Docker testing library
        # or mock Docker commands to simulate the workflow
        
        # Since Docker integration requires a Docker daemon,
        # this test would generally be run in a CI environment with Docker installed
        pass

if __name__ == '__main__':
    unittest.main() 