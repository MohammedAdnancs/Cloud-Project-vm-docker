import os
import subprocess
import sys
import platform
import logging


def check_qemu_installation():
    """Check if QEMU is installed and available on PATH"""
    try:
        # Try to run qemu-img version
        result = subprocess.run(['qemu-img', '--version'], 
                                capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ QEMU is installed: {result.stdout.strip()}")
            return True
        else:
            print("❌ QEMU seems to be installed but returned an error.")
            return False
    except FileNotFoundError:
        print("❌ QEMU is not installed or not found in PATH.")
        return False


def install_qemu_instructions():
    """Print instructions for installing QEMU"""
    print("\n=== QEMU Installation Instructions ===\n")
    
    if platform.system() == "Windows":
        print("1. Download QEMU for Windows from: https://www.qemu.org/download/#windows")
        print("2. Run the installer and follow the installation steps.")
        print("3. Make sure to check the option to add QEMU to your PATH.")
        print("4. Restart your computer after installation.")
        print("\nAlternatively, you can install QEMU using Chocolatey:")
        print("   choco install qemu")
        
    elif platform.system() == "Darwin":  # macOS
        print("Install QEMU using Homebrew:")
        print("1. If you don't have Homebrew: /bin/bash -c \"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\"")
        print("2. Install QEMU: brew install qemu")
        
    elif platform.system() == "Linux":
        print("For Ubuntu/Debian:")
        print("   sudo apt update && sudo apt install qemu-kvm qemu-system qemu-utils")
        print("\nFor Fedora:")
        print("   sudo dnf install qemu-kvm qemu-system qemu-utils")
        print("\nFor Arch:")
        print("   sudo pacman -S qemu")
    
    print("\nAfter installation, please restart this program.")


def check_environment():
    """Check environment and create necessary directories"""
    print("=== Environment Check ===")
    
    # Check if data directories exist and create if necessary
    print("Checking directories...")
    for dir_path in ['data', 'data/disks', 'data/vms', 'data/isos']:
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
            print(f"Created directory: {dir_path}")
        else:
            print(f"✅ Directory exists: {dir_path}")


def setup_logging():
    """Configure logging for the application"""
    os.makedirs('data', exist_ok=True)
    
    # Configure basic logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('data/cloud_vm_manager.log'),
            logging.StreamHandler()
        ]
    )
    print("✅ Logging configured")

def main():
    print("=== Cloud VM Manager Setup ===")
    
    qemu_installed = check_qemu_installation()
    if not qemu_installed:
        install_qemu_instructions()
        input("\nPress Enter to exit...")
        sys.exit(1)
    
    check_environment()
    setup_logging()
    
    print("\n✅ Setup complete! You can now run main.py to start the application.")
    print("   Command: python main.py")


if __name__ == "__main__":
    main()
