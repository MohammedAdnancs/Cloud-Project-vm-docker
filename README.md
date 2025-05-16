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

## Running Tests

The application includes a comprehensive test suite that covers all major components:

### Test Structure

- **Unit Tests**: Tests for individual components
  - `test_disk_manager.py`: Tests disk creation, listing, and deletion
  - `test_vm_manager.py`: Tests VM creation, configuration, and control
  - `test_docker_manager.py`: Tests Docker operations and integration

- **Integration Tests**:
  - `test_integration.py`: Tests interactions between components

### Running the Tests

To run the complete test suite:

```bash
python run_tests.py
```

This will:
1. Execute all unit and integration tests
2. Generate a detailed test report in the `test_reports` directory
3. Display a summary of the results in the terminal

For more focused testing, you can run individual test modules:

```bash
python -m unittest test_disk_manager.py
```

### Test Reports

Test reports are saved in the `test_reports` directory with timestamps in their filenames. These reports include:
- Test results for each test case
- Error details for failed tests
- A summary section with overall statistics

### Interpreting Results

The test summary provides:
- Total number of tests executed
- Number of passed tests
- Number of failed tests
- Number of errors encountered

Note: Some tests may fail if dependencies like QEMU or Docker are not installed or accessible. The test output will indicate these cases.

## License

This project is open source, free to use and modify.

## Contributions

Contributions, bug reports, and feature requests are welcome!
