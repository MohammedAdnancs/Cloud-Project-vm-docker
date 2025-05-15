# Cloud VM Manager

A graphical tool for managing and running virtual machines with QEMU.

## Features

- **Create Virtual Disks**:
  - Choose from multiple formats: qcow2, raw, vmdk, vdi, vhd
  - Specify disk size
  - Manage disk storage

- **Create and Launch Virtual Machines**:
  - Specify VM name, memory, and CPU count
  - Select from existing disks
  - Boot from ISO or existing disk
  - Start/stop VM operations

- **User-friendly GUI**:
  - Easy-to-use interface for creating and managing VMs
  - Organized disk and VM management tabs
  - Progress indicators for operations

## Setup and Installation

### Prerequisites

- Python 3.8 or higher
- QEMU (for VM management)
- Docker (optional, for container management)

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/cloud-vm-manager.git
   cd cloud-vm-manager
   ```

2. Install required Python packages:
   ```
   pip install -r requirements.txt
   ```

3. Run the application:
   ```
   python main.py
   ```

### Directory Structure

The application will create several directories when first run:

- `data/disks/` - Storage for virtual disk images
- `data/vms/` - Configuration files for virtual machines
- `data/isos/` - Storage for ISO images
- `data/docker/` - Docker-related files and metadata
- `data/dockerfiles/` - Dockerfile projects

These directories are excluded from version control in the `.gitignore` file but will be created automatically when the application runs.

## Requirements

- Python 3.6+
- QEMU (latest version recommended)
- PyQt5

## Installation

1. Install QEMU:
   - **Windows**: Download from [QEMU website](https://www.qemu.org/download/#windows) or use Chocolatey: `choco install qemu`
   - **macOS**: Use Homebrew: `brew install qemu`
   - **Linux**: Use your package manager (e.g., `apt install qemu-kvm qemu-system qemu-utils`)

2. Install Python dependencies:
   ```
   pip install PyQt5
   ```

3. Run the setup script to verify your environment:
   ```
   python setup.py
   ```

## Usage

1. Run the application:
   ```
   python main.py
   ```

2. Creating a Disk:
   - Go to the "Virtual Disks" tab
   - Enter a name, size, and format
   - Click "Create Disk"

3. Creating a VM:
   - Go to the "Virtual Machines" tab
   - Fill in the VM details (name, memory, CPU)
   - Select a previously created disk
   - Optionally select a boot ISO
   - Click "Create VM"

4. Starting a VM:
   - In the VM list, click "Start" next to the VM you want to run

## Directory Structure

- `data/disks/`: Storage for virtual disk files
- `data/vms/`: VM configuration files
- `data/isos/`: ISO image files for OS installation

## Files

- `main.py`: Main application with GUI
- `disk_manager.py`: Core functionality for disk management
- `vm_manager.py`: Core functionality for VM management
- `setup.py`: Environment setup and verification

## Troubleshooting

- **"QEMU not found"**: Ensure QEMU is installed and in your system PATH
- **VM fails to start**: Check if the disk and ISO paths are valid
- **Disk creation fails**: Verify you have permissions to write to the data directory

## License

This project is open source, free to use and modify.

## Contributions

Contributions, bug reports, and feature requests are welcome!
