import os
import subprocess
import json
import logging
import time

from rich import _console
from services.disk_manager import DiskManager

# Setup logging
os.makedirs('data', exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
# Create file handler
file_handler = logging.FileHandler('data/vm_manager.log')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

# Get logger
logger = logging.getLogger('vm_manager')
logger.addHandler(file_handler)

class VMManager:
    def __init__(self, vms_dir='data/vms', isos_dir='data/isos'):
        self.vms_dir = vms_dir
        self.isos_dir = isos_dir
        self.registry_file = os.path.join('data', 'vm_registry.json')
        self.disk_manager = DiskManager()
        self._ensure_directories()
        self._load_registry()
    
    def _ensure_directories(self):
        """Ensure all necessary directories exist"""
        os.makedirs(self.vms_dir, exist_ok=True)
        os.makedirs(self.isos_dir, exist_ok=True)
    
    def _load_registry(self):
        """Load the VM registry from the JSON file"""
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
        # Remove entries for VMs whose config files no longer exist
        for vm_name in list(self.registry.keys()):
            config_path = self.registry[vm_name]['config_path']
            if not os.path.exists(config_path):
                logger.warning(f"VM config for {vm_name} no longer exists at {config_path}. Removing from registry.")
                del self.registry[vm_name]
        
        # Add entries for VM configs that exist but are not in the registry
        for filename in os.listdir(self.vms_dir):
            if filename.endswith('.json'):
                config_path = os.path.join(self.vms_dir, filename)
                vm_name = os.path.splitext(filename)[0]
                if vm_name not in self.registry:
                    try:
                        with open(config_path, 'r') as f:
                            config = json.load(f)
                        self.registry[vm_name] = {
                            'config_path': config_path,
                            'disk': config.get('disk', ''),
                            'memory': config.get('memory', 512),
                            'cpus': config.get('cpus', 1),
                            'iso': config.get('iso', ''),
                            'created_time': os.path.getctime(config_path)
                        }
                        logger.info(f"Added existing VM {vm_name} to registry")
                    except (json.JSONDecodeError, IOError) as e:
                        logger.warning(f"Could not load config for VM {vm_name}: {str(e)}. Skipping.")
        
        # Save changes
        self._save_registry()
    
    def _save_registry(self):
        """Save the current registry to the JSON file"""
        try:
            with open(self.registry_file, 'w') as f:
                json.dump(self.registry, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save registry: {str(e)}")
    
    def list_vms(self):
        """Return a list of all registered VMs"""
        return self.registry
    
    def list_isos(self):
        """List all ISO files in the ISOs directory"""
        isos = []
        if os.path.exists(self.isos_dir):
            for file in os.listdir(self.isos_dir):
                if file.lower().endswith('.iso'):
                    isos.append(os.path.join(self.isos_dir, file))
        return isos
    
    def create_vm(self, vm_name, memory, cpus, disk_name, iso_path=None):
        """Create a new VM configuration"""
        if vm_name in self.registry:
            logger.error(f"VM {vm_name} already exists")
            return False, f"VM {vm_name} already exists"
        

        # Validate disk exists
        disk_path = self.disk_manager.get_disk_path(disk_name)
        if not disk_path:
            logger.error(f"Disk {disk_name} not found {disk_path}")
            return False, f"Disk {disk_name} not found"
        
        # Validate ISO if provided
        if iso_path and not os.path.exists(iso_path):
            logger.error(f"ISO file {iso_path} not found")
            return False, f"ISO file {iso_path} not found"
        
        # Create VM config
        config = {
            'name': vm_name,
            'memory': memory,
            'cpus': cpus,
            'disk': disk_path,
            'iso': iso_path if iso_path else '',
            'first_boot': True if iso_path else False
        }
        
        config_path = os.path.join(self.vms_dir, f"{vm_name}.json")
        try:
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
            
            # Add to registry
            self.registry[vm_name] = {
                'config_path': config_path,
                'disk': disk_path,
                'memory': memory,
                'cpus': cpus,
                'iso': iso_path if iso_path else '',
                'created_time': os.path.getctime(config_path)
            }
            self._save_registry()
            
            logger.info(f"Successfully created VM {vm_name}")
            return True, f"Successfully created VM {vm_name}"
            
        except Exception as e:
            logger.error(f"Error creating VM config: {str(e)}")
            return False, f"Error creating VM config: {str(e)}"
    
    def start_vm(self, vm_name):
        """Start a virtual machine"""
        if vm_name not in self.registry:
            logger.error(f"VM {vm_name} not found")
            return False, f"VM {vm_name} not found"
        
        config_path = self.registry[vm_name]['config_path']
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load VM config: {str(e)}")
            return False, f"Failed to load VM config: {str(e)}"
        
        # Build the QEMU command
        cmd = ['qemu-system-x86_64']
        
        # Add memory
        cmd.extend(['-m', str(config['memory'])])
        
        # Add CPUs
        cmd.extend(['-smp', str(config['cpus'])])
          # Add disk
        if not os.path.exists(config['disk']):
            logger.error(f"Disk {config['disk']} not found")
            return False, f"Disk {config['disk']} not found"
        
        # Get the disk name from path to look up format in disk manager
        disk_name = os.path.splitext(os.path.basename(config['disk']))[0]
        disk_format = 'raw'  # Default to raw
        
        # Try to get the actual format from disk manager
        disk_info = self.disk_manager.list_disks().get(disk_name, {})
        if disk_info and 'format' in disk_info:
            disk_format = disk_info['format']
        
        print(f"Disk format for {disk_name} is {disk_format}")

        logger.info(f"Using disk {config['disk']} with format {disk_format}")
        cmd.extend(['-drive', f'file={config["disk"]},format={disk_format}'])
        
        # Add ISO if first boot or if specified
        if config.get('first_boot', False) and config.get('iso'):
            if not os.path.exists(config['iso']):
                logger.error(f"ISO file {config['iso']} not found")
                return False, f"ISO file {config['iso']} not found"
            
            cmd.extend(['-cdrom', config['iso']])
            cmd.extend(['-boot', 'order=dc'])
            
            # Update config to indicate first boot is done
            config['first_boot'] = False
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
        
        # Add display and other options
        cmd.extend(['-display', 'gtk'])
        
        # Execute the command
        try:
            logger.info(f"Starting VM {vm_name} with command: {' '.join(cmd)}")
            
            # Use Popen to run the VM in the background
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            
            # Give it a moment to start and check if it's running
            time.sleep(2)
            if process.poll() is not None:
                # Process exited quickly, which likely means an error
                stdout, stderr = process.communicate()
                logger.error(f"VM process exited immediately with return code {process.returncode}")
                logger.error(f"STDOUT: {stdout}")
                logger.error(f"STDERR: {stderr}")
                return False, f"Failed to start VM: {stderr}"
            
            return True, f"Successfully started VM {vm_name}"
            
        except subprocess.SubprocessError as e:
            error_msg = f"Failed to start VM: {e.stderr if hasattr(e, 'stderr') else str(e)}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            logger.error(f"Error starting VM: {str(e)}")
            return False, f"Error starting VM: {str(e)}"
    
    def delete_vm(self, vm_name):
        """Delete a VM configuration (does not delete the disk)"""
        if vm_name not in self.registry:
            logger.error(f"VM {vm_name} not found")
            return False, f"VM {vm_name} not found"
        
        config_path = self.registry[vm_name]['config_path']
        
        try:
            os.remove(config_path)
            del self.registry[vm_name]
            self._save_registry()
            logger.info(f"Successfully deleted VM {vm_name}")
            return True, f"Successfully deleted VM {vm_name}"
        except Exception as e:
            logger.error(f"Failed to delete VM {vm_name}: {str(e)}")
            return False, f"Failed to delete VM {vm_name}: {str(e)}"
