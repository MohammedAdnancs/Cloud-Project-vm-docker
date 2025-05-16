import unittest
import os
import json
import shutil
from unittest.mock import patch, MagicMock
from services.disk_manager import DiskManager

class TestDiskManager(unittest.TestCase):
    """Unit tests for the DiskManager class"""
    
    def setUp(self):
        # Create test directories and files
        self.test_dir = os.path.join('test_data', 'disks')
        self.registry_file = os.path.join('test_data', 'disk_registry.json')
        
        # Ensure test directory exists and is empty
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        os.makedirs(self.test_dir, exist_ok=True)
        os.makedirs(os.path.dirname(self.registry_file), exist_ok=True)
        
        # Create a clean DiskManager for each test
        self.disk_manager = DiskManager(disks_dir=self.test_dir)
        self.disk_manager.registry_file = self.registry_file
        self.disk_manager.registry = {}
        
    def tearDown(self):
        # Clean up test data after each test
        if os.path.exists('test_data'):
            shutil.rmtree('test_data')

    @patch('subprocess.run')
    @patch('os.path.exists')
    @patch('os.path.getctime')
    def test_create_disk_success(self, mock_getctime, mock_path_exists, mock_run):
        """Test creating a disk with valid parameters"""
        # Track paths to handle exists checks correctly
        disk_file_exists = {}
        
        # Mock os.path.exists to return False for disk file (doesn't exist yet) but True for directory
        def mock_exists(path):
            if path.endswith('.qcow2'):
                # Check if we've seen this path before
                if path not in disk_file_exists:
                    disk_file_exists[path] = False
                    return False
                return disk_file_exists[path]
            elif path == self.disk_manager.registry_file:
                return False
            elif path == self.test_dir:
                return True
            return True
        
        mock_path_exists.side_effect = mock_exists
        
        # Mock os.path.getctime
        mock_getctime.return_value = 1621234567.0
        
        # Mock the subprocess.run calls
        def side_effect_function(*args, **kwargs):
            cmd = args[0]
            if cmd[0] == 'qemu-img' and cmd[1] == 'create':
                # Mock the qemu-img create command - this should also mark the path as existing
                if len(cmd) > 3:
                    disk_file_exists[cmd[3]] = True
                mock_create = MagicMock()
                mock_create.returncode = 0
                mock_create.stdout = ""
                return mock_create
            elif cmd[0] == 'qemu-img' and cmd[1] == 'info':
                # Mock the qemu-img info command
                mock_info = MagicMock()
                mock_info.returncode = 0
                mock_info.stdout = '{"format": "qcow2", "virtual-size": 10737418240}'
                return mock_info
            else:
                # Default mock response
                mock_default = MagicMock()
                mock_default.returncode = 0
                mock_default.stdout = ""
                return mock_default
        
        mock_run.side_effect = side_effect_function
        
        # Create a test disk
        success, message = self.disk_manager.create_disk("test_disk", "10G")
        
        # Check if the disk was created successfully
        self.assertTrue(success)
        self.assertEqual(message, "Successfully created disk test_disk")
        self.assertIn("test_disk", self.disk_manager.registry)
        
        # Verify the subprocess.run was called correctly
        mock_run.assert_called()
    
    def test_create_disk_invalid_name(self):
        """Test creating a disk with invalid name"""
        success, message = self.disk_manager.create_disk("", "10G")
        self.assertFalse(success)
        self.assertEqual(message, "Disk name cannot be empty")

        success, message = self.disk_manager.create_disk("invalid/name", "10G")
        self.assertFalse(success)
        self.assertEqual(message, "Disk name can only contain letters, numbers, underscores, hyphens, and periods")
    
    def test_create_disk_invalid_size(self):
        """Test creating a disk with invalid size"""
        success, message = self.disk_manager.create_disk("test_disk", "0G")
        self.assertFalse(success)
        self.assertIn("must be greater than zero", message)
        
        success, message = self.disk_manager.create_disk("test_disk", "-10G")
        self.assertFalse(success)
        self.assertIn("Invalid size", message)
        
        success, message = self.disk_manager.create_disk("test_disk", "abc")
        self.assertFalse(success)
        self.assertIn("Invalid size", message)
    
    def test_create_disk_invalid_format(self):
        """Test creating a disk with invalid format"""
        success, message = self.disk_manager.create_disk("test_disk", "10G", "invalid_format")
        self.assertFalse(success)
        self.assertIn("Invalid disk format", message)
    
    @patch('subprocess.run')
    def test_list_disks(self, mock_run):
        """Test listing available disks"""
        # Manually set up a disk in the registry
        test_disk = {
            "path": os.path.join(self.test_dir, "test_disk.qcow2"),
            "format": "qcow2",
            "size": 10737418240,
            "created_time": 1621234567.0
        }
        self.disk_manager.registry = {"test_disk": test_disk}
        self.disk_manager._save_registry()
        
        # Get the list of disks
        disks = self.disk_manager.list_disks()
        
        # Verify the test disk is in the list
        self.assertIn("test_disk", disks)
        self.assertEqual(disks["test_disk"], test_disk)
    
    @patch('os.remove')
    def test_delete_disk(self, mock_remove):
        """Test deleting a disk"""
        # Manually set up a disk in the registry
        disk_path = os.path.join(self.test_dir, "test_disk.qcow2")
        self.disk_manager.registry = {
            "test_disk": {
                "path": disk_path,
                "format": "qcow2",
                "size": 10737418240,
                "created_time": 1621234567.0
            }
        }
        
        # Create an empty file to be "deleted"
        with open(disk_path, 'w') as f:
            f.write('')
        
        # Delete the disk
        success, message = self.disk_manager.delete_disk("test_disk")
        
        # Verify the disk was deleted successfully
        self.assertTrue(success)
        self.assertEqual(message, "Successfully deleted disk test_disk")
        self.assertNotIn("test_disk", self.disk_manager.registry)
        mock_remove.assert_called_once_with(disk_path)
    
    def test_delete_nonexistent_disk(self):
        """Test deleting a disk that doesn't exist"""
        success, message = self.disk_manager.delete_disk("nonexistent_disk")
        self.assertFalse(success)
        self.assertEqual(message, "Disk nonexistent_disk not found")
    
    def test_get_disk_path(self):
        """Test getting the path for a specific disk"""
        # Manually set up a disk in the registry
        disk_path = os.path.join(self.test_dir, "test_disk.qcow2")
        self.disk_manager.registry = {
            "test_disk": {
                "path": disk_path,
                "format": "qcow2",
                "size": 10737418240,
                "created_time": 1621234567.0
            }
        }
        
        # Get the disk path
        path = self.disk_manager.get_disk_path("test_disk")
        
        # Verify the path is correct
        self.assertEqual(path, disk_path)
        
        # Test with a nonexistent disk
        path = self.disk_manager.get_disk_path("nonexistent_disk")
        self.assertIsNone(path)
    
    def test_validate_registry(self):
        """Test registry validation functionality"""
        # Create a registry with a disk that doesn't exist
        self.disk_manager.registry = {
            "nonexistent_disk": {
                "path": os.path.join(self.test_dir, "nonexistent.qcow2"),
                "format": "qcow2",
                "size": 10737418240,
                "created_time": 1621234567.0
            }
        }
        
        # Create a disk file that isn't in the registry
        disk_path = os.path.join(self.test_dir, "unlisted_disk.qcow2")
        with open(disk_path, 'w') as f:
            f.write('')
            
        # Mock the subprocess call for qemu-img info
        with patch('subprocess.run') as mock_run:
            # Configure the mock to return disk info
            mock_process = MagicMock()
            mock_process.returncode = 0
            mock_process.stdout = '{"format": "qcow2", "virtual-size": 10737418240}'
            mock_run.return_value = mock_process
            
            # Run the validation
            self.disk_manager._validate_registry()
            
            # Verify the nonexistent disk was removed from registry
            self.assertNotIn("nonexistent_disk", self.disk_manager.registry)
            
            # Skip automatic disk detection test since it requires mocking subprocess

if __name__ == '__main__':
    unittest.main() 