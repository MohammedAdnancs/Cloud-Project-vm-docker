import os
import sys
import subprocess
import platform
import shutil
import logging
import winreg as reg

# Setup logging
os.makedirs('data', exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data/cloud_vm_launcher.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('cloud_vm_launcher')

def create_desktop_shortcut():
    """Create a desktop shortcut for the application on Windows"""
    try:
        # Get the path to the current script
        script_path = os.path.abspath(__file__)
        app_dir = os.path.dirname(script_path)
        main_script = os.path.join(app_dir, 'main.py')
        
        # Path to Python executable
        python_path = sys.executable
        
        # Desktop path
        desktop_path = os.path.join(os.path.expanduser('~'), 'Desktop')
        shortcut_path = os.path.join(desktop_path, 'Cloud VM Manager.lnk')
        
        if os.path.exists(shortcut_path):
            logger.info(f"Shortcut already exists at {shortcut_path}")
            return True
        
        # Create shortcut using PowerShell
        ps_script = f"""
        $WshShell = New-Object -ComObject WScript.Shell
        $Shortcut = $WshShell.CreateShortcut("{shortcut_path}")
        $Shortcut.TargetPath = "{python_path}"
        $Shortcut.Arguments = "{main_script}"
        $Shortcut.WorkingDirectory = "{app_dir}"
        $Shortcut.Description = "Cloud VM Manager"
        $Shortcut.IconLocation = "{python_path},0"
        $Shortcut.Save()
        """
        
        # Execute PowerShell script
        cmd = ['powershell.exe', '-Command', ps_script]
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        
        logger.info(f"Created desktop shortcut at {shortcut_path}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to create desktop shortcut: {str(e)}")
        return False

def register_file_associations():
    """Register the application as a handler for .qcow2, .vmdk files etc."""
    try:
        # Get the path to the current script
        script_path = os.path.abspath(__file__)
        app_dir = os.path.dirname(script_path)
        main_script = os.path.join(app_dir, 'main.py')
        
        # Path to Python executable
        python_path = sys.executable
        
        # Command to execute
        cmd = f'"{python_path}" "{main_script}" "%1"'
        
        # File types to associate with
        file_types = [
            ('.qcow2', 'QEMU Disk Image'),
            ('.raw', 'Raw Disk Image'),
            ('.vmdk', 'VMware Disk Image'),
            ('.vdi', 'VirtualBox Disk Image'),
            ('.vhd', 'Hyper-V Disk Image'),
        ]
        
        # Register each file type
        for ext, desc in file_types:
            logger.info(f"Registering file association for {ext}")
            
            # Create file type entry
            key_path = f'Software\\Classes\\{ext}'
            try:
                key = reg.CreateKey(reg.HKEY_CURRENT_USER, key_path)
                reg.SetValue(key, '', reg.REG_SZ, f'CloudVMManager{ext}')
                reg.CloseKey(key)
                
                # Create file type descriptor
                key_path = f'Software\\Classes\\CloudVMManager{ext}'
                key = reg.CreateKey(reg.HKEY_CURRENT_USER, key_path)
                reg.SetValue(key, '', reg.REG_SZ, desc)
                reg.CloseKey(key)
                
                # Set default icon
                key_path = f'Software\\Classes\\CloudVMManager{ext}\\DefaultIcon'
                key = reg.CreateKey(reg.HKEY_CURRENT_USER, key_path)
                reg.SetValue(key, '', reg.REG_SZ, f'{python_path},0')
                reg.CloseKey(key)
                
                # Set open command
                key_path = f'Software\\Classes\\CloudVMManager{ext}\\shell\\open\\command'
                key = reg.CreateKey(reg.HKEY_CURRENT_USER, key_path)
                reg.SetValue(key, '', reg.REG_SZ, cmd)
                reg.CloseKey(key)
                
            except Exception as e:
                logger.error(f"Failed to register {ext}: {str(e)}")
                continue
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to register file associations: {str(e)}")
        return False

def main():
    print("=== Cloud VM Manager Launcher ===")
    
    # Run the setup script first
    print("Running setup checks...")
    setup_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'setup.py')
    result = subprocess.run([sys.executable, setup_script], capture_output=True, text=True)
    
    if result.returncode != 0:
        print("Setup check failed. Please fix the issues and try again.")
        print(result.stdout)
        print(result.stderr)
        input("\nPress Enter to exit...")
        sys.exit(1)
    
    # Create desktop shortcut
    print("Creating desktop shortcut...")
    shortcut_result = create_desktop_shortcut()
    
    # Register file associations
    print("Registering file associations...")
    register_result = register_file_associations()
    
    print("\n✅ Launcher setup complete!")
    
    # Launch the application
    print("Starting Cloud VM Manager...")
    main_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'main.py')
    subprocess.Popen([sys.executable, main_script])


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.exception("Launcher failed with unhandled exception")
        print(f"Error: {str(e)}")
        input("\nPress Enter to exit...")
