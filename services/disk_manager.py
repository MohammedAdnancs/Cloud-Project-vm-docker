import os
import subprocess
import json
import logging
import re

# Setup logging
os.makedirs('data', exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
# Create file handler
file_handler = logging.FileHandler('data/disk_manager.log')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

# Get logger
logger = logging.getLogger('disk_manager')
logger.addHandler(file_handler)

class DiskManager:
    def __init__(self, disks_dir='data/disks'):
        self.disks_dir = disks_dir
        self.registry_file = os.path.join('data', 'disk_registry.json')
        self.disk_formats = ['qcow2', 'raw', 'vmdk', 'vdi', 'vhd']
        self._ensure_directories()
        self._load_registry()
    
    def _ensure_directories(self):
        """Ensure all necessary directories exist"""
        os.makedirs(self.disks_dir, exist_ok=True)
    
    def _load_registry(self):
        """Load the disk registry from the JSON file"""
        if os.path.exists(self.registry_file):
            try:
                with open(self.registry_file, 'r') as f:
                    self.registry = json.load(f)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse {self.registry_file}. Creating a new registry.")
                self.registry = {}
        else:
            self.registry = {}
        
        # Validate the registry against actual files
        self._validate_registry()
    
    def _validate_registry(self):
        """Validate registry against actual files and vice versa"""
        # Remove entries for disks that no longer exist
        for disk_name in list(self.registry.keys()):
            disk_path = self.registry[disk_name]['path']
            if not os.path.exists(disk_path):
                logger.warning(f"Disk {disk_name} no longer exists at {disk_path}. Removing from registry.")
                del self.registry[disk_name]
        
        # Add entries for disks that exist but are not in the registry
        for filename in os.listdir(self.disks_dir):
            # Skip .gitkeep files and other hidden files
            if filename.startswith('.') or filename == '.gitkeep':
                continue
                
            disk_path = os.path.join(self.disks_dir, filename)
            if os.path.isfile(disk_path):
                disk_name = os.path.splitext(filename)[0]
                if disk_name not in self.registry:
                    # Try to get the format and size from qemu-img info
                    try:
                        result = subprocess.run(
                            ['qemu-img', 'info', '--output=json', disk_path],
                            capture_output=True, text=True, check=True
                        )
                        info = json.loads(result.stdout)
                        self.registry[disk_name] = {
                            'path': disk_path,
                            'format': info['format'],
                            'size': info['virtual-size'],
                            'created_time': os.path.getctime(disk_path)
                        }
                        logger.info(f"Added existing disk {disk_name} to registry")
                    except subprocess.SubprocessError:
                        logger.warning(f"Could not get info for disk {disk_name}. Skipping.")
                    except json.JSONDecodeError:
                        logger.warning(f"Could not parse qemu-img output for disk {disk_name}. Skipping.")
        
        # Remove any .gitkeep entries that might have been added previously
        if ".gitkeep" in self.registry:
            del self.registry[".gitkeep"]
        
        # Save changes
        self._save_registry()
    
    def _save_registry(self):
        """Save the current registry to the JSON file"""
        try:
            with open(self.registry_file, 'w') as f:
                json.dump(self.registry, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save registry: {str(e)}")
    
    def list_disks(self):
        """Return a list of all registered disks"""
        return self.registry
    
    def get_disk_path(self, disk_name):
        """Get the path for a specific disk"""
        if disk_name in self.registry:
            return self.registry[disk_name]['path']
        return None
    
    def create_disk(self, disk_name, size, disk_format='qcow2'):
        """Create a new virtual disk with enhanced validation"""
        # Validate disk name
        if not disk_name:
            logger.error("Disk name cannot be empty")
            return False, "Disk name cannot be empty"
            
        # Check for invalid characters in disk name
        if not re.match(r'^[a-zA-Z0-9_\-\.]+$', disk_name):
            logger.error(f"Disk name contains invalid characters: {disk_name}")
            return False, "Disk name can only contain letters, numbers, underscores, hyphens, and periods"
            
        # Check if disk name already exists
        if disk_name in self.registry:
            logger.error(f"Disk {disk_name} already exists")
            return False, f"Disk {disk_name} already exists"
        
        # Validate disk format
        if disk_format not in self.disk_formats:
            logger.error(f"Invalid disk format: {disk_format}")
            return False, f"Invalid disk format: {disk_format}. Supported formats: {', '.join(self.disk_formats)}"
        
        # Validate size string format and ensure positive value
        size_match = re.match(r'^(\d+)([KMGT])$', size)
        if not size_match:
            logger.error(f"Invalid size format: {size}")
            return False, f"Invalid size format: {size}. Examples: 10G, 500M, 2T"
            
        # Extract numeric part and unit
        size_value = int(size_match.group(1))
        size_unit = size_match.group(2)
        
        # Validate size is positive and reasonable
        if size_value <= 0:
            logger.error(f"Disk size must be positive: {size}")
            return False, "Disk size must be greater than zero"
            
        # Set reasonable upper limits based on unit
        max_sizes = {'K': 1024*1024, 'M': 1024*10, 'G': 1024, 'T': 64}
        if size_value > max_sizes[size_unit]:
            logger.warning(f"Unusually large disk size requested: {size}")
            return False, f"Size {size} exceeds reasonable limit. Maximum recommended: {max_sizes[size_unit]}{size_unit}"
        
        # Check available disk space
        try:
            import shutil
            free_space = shutil.disk_usage(self.disks_dir).free
            
            # Convert size to bytes for comparison
            unit_multipliers = {'K': 1024, 'M': 1024**2, 'G': 1024**3, 'T': 1024**4}
            requested_bytes = size_value * unit_multipliers[size_unit]
            
            # Check if we have enough space (with 10% buffer)
            if requested_bytes * 1.1 > free_space:
                logger.error(f"Not enough disk space. Requested: {size}, Available: {free_space/(1024**3):.2f}G")
                return False, f"Not enough disk space. Available: {free_space/(1024**3):.2f}G"
        except Exception as e:
            logger.warning(f"Could not check available disk space: {str(e)}")
        
        disk_path = os.path.join(self.disks_dir, f"{disk_name}.{disk_format}")
        
        # Check if the file already exists (even if not in registry)
        if os.path.exists(disk_path):
            logger.error(f"File already exists at path: {disk_path}")
            return False, f"A file already exists at {disk_path}"
        
        try:
            cmd = ['qemu-img', 'create', '-f', disk_format, disk_path, size]
            logger.info(f"Running command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            # Get actual size in bytes
            info = subprocess.run(
                ['qemu-img', 'info', '--output=json', disk_path],
                capture_output=True, text=True, check=True
            )
            disk_info = json.loads(info.stdout)
            
            # Add to registry
            self.registry[disk_name] = {
                'path': disk_path,
                'format': disk_format,
                'size': disk_info['virtual-size'],
                'created_time': os.path.getctime(disk_path)
            }
            self._save_registry()
            
            logger.info(f"Successfully created disk {disk_name} with size {size} and format {disk_format}")
            return True, f"Successfully created disk {disk_name}"
            
        except subprocess.SubprocessError as e:
            error_msg = f"Failed to create disk: {e.stderr if hasattr(e, 'stderr') else str(e)}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            logger.error(f"Error creating disk: {str(e)}")
            return False, f"Error creating disk: {str(e)}"
    
    def delete_disk(self, disk_name):
        """Delete a virtual disk"""
        if disk_name not in self.registry:
            logger.error(f"Disk {disk_name} not found")
            return False, f"Disk {disk_name} not found"
        
        disk_path = self.registry[disk_name]['path']
        
        try:
            os.remove(disk_path)
            del self.registry[disk_name]
            self._save_registry()
            logger.info(f"Successfully deleted disk {disk_name}")
            return True, f"Successfully deleted disk {disk_name}"
        except Exception as e:
            logger.error(f"Failed to delete disk {disk_name}: {str(e)}")
            return False, f"Failed to delete disk {disk_name}: {str(e)}"
