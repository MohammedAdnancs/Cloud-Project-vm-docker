#!/usr/bin/env python3
# filepath: c:\Users\medoa\Desktop\cloud\services\docker_manager.py

import os
import subprocess
import json
import logging
import shutil
from datetime import datetime

# Setup logging
os.makedirs('data', exist_ok=True)
os.makedirs('logs', exist_ok=True)  # Create logs directory if it doesn't exist
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
# Create file handler
file_handler = logging.FileHandler('logs/docker_manager.log')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

# Get logger
logger = logging.getLogger('docker_manager')
logger.addHandler(file_handler)

class DockerManager:
    def __init__(self, dockerfiles_dir='data/dockerfiles', docker_data_dir='data/docker'):
        """Initialize the Docker Manager with required directories"""
        self.dockerfiles_dir = dockerfiles_dir
        self.docker_data_dir = docker_data_dir
        self.metadata_dir = os.path.join(docker_data_dir, 'metadata')
        self._ensure_directories()
        self._check_docker_installed()
    
    def _ensure_directories(self):
        """Ensure all necessary directories exist"""
        os.makedirs(self.dockerfiles_dir, exist_ok=True)
        os.makedirs(self.docker_data_dir, exist_ok=True)
        os.makedirs(self.metadata_dir, exist_ok=True)
        logger.info(f"Ensured directories: {self.dockerfiles_dir}, {self.docker_data_dir}")
    
    def _check_docker_installed(self):
        """Check if Docker is installed and accessible"""
        try:
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                check=False  # Don't raise exception on non-zero exit
            )
            if result.returncode != 0:
                logger.error("Docker not installed or not accessible")
                print("WARNING: Docker not installed or not accessible. Please install Docker to use this feature.")
            else:
                logger.info(f"Docker detected: {result.stdout.strip()}")
        except FileNotFoundError:
            logger.error("Docker command not found")
            print("WARNING: Docker command not found. Please install Docker to use this feature.")
    
    def create_dockerfile_project(self, project_name, dockerfile_content, requirements_content=None, entrypoint_content=None, entrypoint_file=None):
        """
        Create a Docker project folder with Dockerfile, requirements.txt, and entry point file.
        
        Args:
            project_name (str): Name of the Docker project (folder will be created with this name)
            dockerfile_content (str): Content of the Dockerfile
            requirements_content (str, optional): Content of the requirements.txt file
            entrypoint_content (str, optional): Content of the entry point file
            entrypoint_file (str, optional): Name of the entry point file (e.g., app.py)
            
        Returns:
            tuple: (success (bool), message (str), project_path (str))
        """
        try:
            # Create the project directory
            project_path = os.path.join(self.dockerfiles_dir, project_name)
            os.makedirs(project_path, exist_ok=True)
            
            # Create Dockerfile
            dockerfile_path = os.path.join(project_path, "Dockerfile")
            with open(dockerfile_path, 'w') as f:
                f.write(dockerfile_content)
            
            # Create requirements.txt if provided
            if requirements_content:
                requirements_path = os.path.join(project_path, "requirements.txt")
                with open(requirements_path, 'w') as f:
                    f.write(requirements_content)
            
            # Create entry point file if provided
            if entrypoint_content and entrypoint_file:
                entrypoint_path = os.path.join(project_path, entrypoint_file)
                with open(entrypoint_path, 'w') as f:
                    f.write(entrypoint_content)
            
            logger.info(f"Created Docker project at {project_path}")
            return True, f"Docker project created successfully at {project_path}", project_path
        
        except Exception as e:
            logger.error(f"Error creating Docker project: {str(e)}")
            return False, f"Error creating Docker project: {str(e)}", None
            
    def create_dockerfile(self, path=None, content=None):
        """
        Create a Dockerfile at the specified location with the given content.
        
        Args:
            path (str, optional): Path to save the Dockerfile. Defaults to a timestamped file in dockerfiles_dir.
            content (str, optional): Content of the Dockerfile. If None, prompts user for input.
            
        Returns:
            tuple: (success (bool), message (str), dockerfile_path (str))
        """
        try:
            # Handle path
            if not path:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                path = os.path.join(self.dockerfiles_dir, f"Dockerfile_{timestamp}")
                print(f"No path specified. Using default: {path}")
            
            # If the path is a directory, append 'Dockerfile' to it
            if os.path.isdir(path):
                path = os.path.join(path, "Dockerfile")
            
            # Ensure the directory exists
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            
            # Handle content
            if content is None:
                print("Enter Dockerfile content (type 'EOF' on a new line to finish):")
                lines = []
                while True:
                    line = input()
                    if line == "EOF":
                        break
                    lines.append(line)
                content = "\n".join(lines)
            
            # Write the Dockerfile
            with open(path, 'w') as f:
                f.write(content)
            
            logger.info(f"Created Dockerfile at {path}")
            return True, f"Dockerfile created successfully at {path}", path
        
        except Exception as e:
            logger.error(f"Error creating Dockerfile: {str(e)}")
            return False, f"Error creating Dockerfile: {str(e)}", None
    
    def build_image(self, dockerfile_path=None, image_name=None):
        """
        Build a Docker image from a Dockerfile.
        
        Args:
            dockerfile_path (str, optional): Path to the Dockerfile. If None, prompts user.
            image_name (str, optional): Name and tag for the image (e.g., myapp:latest). If None, prompts user.
            
        Returns:
            tuple: (success (bool), message (str))
        """
        try:
            # Handle dockerfile_path
            if dockerfile_path is None:
                print(f"Default Dockerfiles location: {self.dockerfiles_dir}")
                dockerfile_path = input("Enter path to Dockerfile: ")
            
            if not os.path.exists(dockerfile_path):
                return False, f"Dockerfile not found at {dockerfile_path}"
            
            # Handle image_name
            if image_name is None:
                image_name = input("Enter image name and tag (e.g., myapp:latest): ")
            
            # Directory containing the Dockerfile
            docker_context = os.path.dirname(os.path.abspath(dockerfile_path))
            
            # Check if this is a Docker project structure from the dockerfiles directory
            is_project_structure = False
            if docker_context.startswith(self.dockerfiles_dir) and docker_context != self.dockerfiles_dir:
                # This is potentially a project structure
                project_name = os.path.basename(docker_context)
                requirements_path = os.path.join(docker_context, "requirements.txt")
                
                if os.path.exists(requirements_path):
                    is_project_structure = True
                    logger.info(f"Detected Docker project structure for {project_name}")
              # Build the Docker image
            # If this is a Docker project in the dockerfiles directory, use the project directory as context
            # This ensures that the Dockerfile can reference other files like requirements.txt and entry point
            if is_project_structure:
                # Use project directory as the context
                # This is equivalent to:
                # cd project_dir && docker build -t image_name .
                cmd = ["docker", "build", "-t", image_name, "."]
                logger.info(f"Building Docker image from project directory: {docker_context}")
                logger.info(f"Command (from {docker_context}): {' '.join(cmd)}")
                print(f"Building Docker image {image_name} from project directory...")
                
                # Run the command in the project directory
                process = subprocess.run(cmd, cwd=docker_context, capture_output=True, text=True)
            else:
                # Regular build with explicit Dockerfile path
                cmd = ["docker", "build", "-t", image_name, "-f", dockerfile_path, docker_context]
                logger.info(f"Building Docker image with command: {' '.join(cmd)}")
                print(f"Building Docker image {image_name}...")
                
                process = subprocess.run(cmd, capture_output=True, text=True)
            
            if process.returncode == 0:
                logger.info(f"Successfully built Docker image: {image_name}")
                
                # Store metadata about the built image
                metadata = {
                    "image_name": image_name,
                    "dockerfile_path": dockerfile_path,
                    "build_time": datetime.now().isoformat(),
                    "is_project_structure": is_project_structure,
                    "project_directory": docker_context if is_project_structure else None,
                    "build_output": process.stdout
                }
                
                # Save metadata
                image_name_safe = image_name.replace(":", "_").replace("/", "_")
                metadata_path = os.path.join(self.metadata_dir, f"{image_name_safe}_build_info.json")
                with open(metadata_path, 'w') as f:
                    json.dump(metadata, f, indent=2)
                
                return True, f"Successfully built Docker image: {image_name}"
            else:
                logger.error(f"Failed to build Docker image: {process.stderr}")
                return False, f"Failed to build Docker image: {process.stderr}"
                
        except Exception as e:
            logger.error(f"Error building Docker image: {str(e)}")
            return False, f"Error building Docker image: {str(e)}"
    
    def list_images(self):
        """
        List all locally available Docker images.
        
        Returns:
            tuple: (success (bool), message (str), images (list))
        """
        try:
            cmd = ["docker", "images", "--format", "{{.Repository}}:{{.Tag}}\t{{.ID}}\t{{.Size}}\t{{.CreatedAt}}"]
            logger.info("Listing Docker images")
            
            process = subprocess.run(cmd, capture_output=True, text=True)
            
            if process.returncode == 0:
                images = []
                for line in process.stdout.strip().split('\n'):
                    if line:  # Skip empty lines
                        parts = line.split('\t')
                        if len(parts) >= 4:
                            # Skip .gitkeep entries or entries with .gitkeep in the name
                            if '.gitkeep' in parts[0]:
                                continue
                                
                            image = {
                                "name_tag": parts[0],
                                "id": parts[1],
                                "size": parts[2],
                                "created_at": parts[3]
                            }
                            images.append(image)
                
                return True, f"Found {len(images)} Docker images", images
            else:
                logger.error(f"Failed to list Docker images: {process.stderr}")
                return False, f"Failed to list Docker images: {process.stderr}", []
                
        except Exception as e:
            logger.error(f"Error listing Docker images: {str(e)}")
            return False, f"Error listing Docker images: {str(e)}", []
    
    def list_containers(self, show_all=True):
        """
        List Docker containers.
        
        Args:
            show_all (bool): Ignored parameter - always shows all containers.
            
        Returns:
            tuple: (success (bool), message (str), containers (list))
        """
        try:
            # Make sure Docker is accessible
            check_cmd = ["docker", "info"]
            check_process = subprocess.run(check_cmd, capture_output=True, text=True)
            if check_process.returncode != 0:
                logger.error(f"Docker is not accessible: {check_process.stderr}")
                return False, f"Docker is not accessible: {check_process.stderr}", []
                  # Changed format to match Docker CLI output exactly
            cmd = ["docker", "ps", "-a", "--format", "{{.ID}}\t{{.Image}}\t{{.Status}}\t{{.Names}}\t{{.Ports}}"]
            
            logger.info(f"Listing all Docker containers with command: {' '.join(cmd)}")
            
            process = subprocess.run(cmd, capture_output=True, text=True)
            
            if process.returncode == 0:
                containers = []
                # Add debug output
                logger.info(f"Container output raw: {process.stdout}")
                
                for line in process.stdout.strip().split('\n'):
                    if line:  # Skip empty lines
                        logger.info(f"Processing container line: {line}")
                        parts = line.split('\t')
                        if len(parts) >= 5:
                            # Skip containers based on .gitkeep images
                            if '.gitkeep' in parts[1]:  # parts[1] is the image name
                                continue
                                
                            container = {
                                "id": parts[0],
                                "image": parts[1],
                                "status": parts[2],
                                "name": parts[3],
                                "ports": parts[4]
                            }
                            containers.append(container)
                
                return True, f"Found {len(containers)} containers", containers
            else:
                logger.error(f"Failed to list containers: {process.stderr}")
                return False, f"Failed to list containers: {process.stderr}", []
                
        except Exception as e:
            logger.error(f"Error listing containers: {str(e)}")
            return False, f"Error listing containers: {str(e)}", []
    
    def stop_container(self, container_id=None):
        """
        Stop a running Docker container.
        
        Args:
            container_id (str, optional): ID or name of the container to stop. If None, prompts user.
            
        Returns:
            tuple: (success (bool), message (str))
        """
        try:
            # Get container ID if not provided
            if container_id is None:
                success, message, containers = self.list_containers()
                if not success or not containers:
                    return False, "No running containers found"
                
                print("Running containers:")
                for i, container in enumerate(containers):
                    print(f"{i+1}. {container['name']} ({container['id']}) - {container['image']}")
                
                selection = input("\nEnter container number or ID/name to stop: ")
                try:
                    # Check if user entered a number
                    idx = int(selection) - 1
                    if 0 <= idx < len(containers):
                        container_id = containers[idx]["id"]
                    else:
                        container_id = selection
                except ValueError:
                    container_id = selection
            
            # Stop the container
            cmd = ["docker", "stop", container_id]
            logger.info(f"Stopping container: {container_id}")
            
            process = subprocess.run(cmd, capture_output=True, text=True)
            
            if process.returncode == 0:
                logger.info(f"Successfully stopped container: {container_id}")
                return True, f"Successfully stopped container: {container_id}"
            else:
                logger.error(f"Failed to stop container: {process.stderr}")
                return False, f"Failed to stop container: {process.stderr}"
                
        except Exception as e:
            logger.error(f"Error stopping container: {str(e)}")
            return False, f"Error stopping container: {str(e)}"
    
    def search_local_image(self, search_term=None):
        """
        Search for a Docker image locally.
        
        Args:
            search_term (str, optional): Partial image name or tag to search for. If None, prompts user.
            
        Returns:
            tuple: (success (bool), message (str), images (list))
        """
        try:
            # Get search term if not provided
            if search_term is None:
                search_term = input("Enter image name or tag to search for: ")
            
            # Get all images first
            success, message, images = self.list_images()
            if not success:
                return False, message, []
            
            # Filter images by search term
            filtered_images = [img for img in images if search_term.lower() in img["name_tag"].lower()]
            
            logger.info(f"Found {len(filtered_images)} images matching '{search_term}'")
            return True, f"Found {len(filtered_images)} images matching '{search_term}'", filtered_images
                
        except Exception as e:
            logger.error(f"Error searching for local images: {str(e)}")
            return False, f"Error searching for local images: {str(e)}", []
    
    def search_dockerhub(self, search_term=None):

        try:
            # Get search term if not provided
            if search_term is None:
                search_term = input("Enter image name to search for on DockerHub: ")
              # Search DockerHub
            # Use a simpler format without template parsing issues
            cmd = ["docker", "search", "--format", "{{json .}}", search_term]
            logger.info(f"Searching DockerHub for: {search_term}")
            
            process = subprocess.run(cmd, capture_output=True, text=True)
            if process.returncode == 0:
                results = []
                for line in process.stdout.strip().split('\n'):
                    if line:  # Skip empty lines
                        try:
                            # Parse JSON for each result
                            docker_result = json.loads(line)
                            result = {
                                "name": docker_result.get("Name", ""),
                                "description": docker_result.get("Description", ""),
                                "stars": str(docker_result.get("StarCount", 0)),  # Convert to string for consistency
                                "official": docker_result.get("IsOfficial", "") == "[OK]",
                                "automated": docker_result.get("IsAutomated", "") == "[OK]"
                            }
                            results.append(result)
                        except json.JSONDecodeError as e:
                            logger.error(f"Failed to parse Docker Hub search result: {e} - Line: {line}")
                
                logger.info(f"Found {len(results)} results on DockerHub for '{search_term}'")
                return True, f"Found {len(results)} results on DockerHub for '{search_term}'", results
            else:
                logger.error(f"Failed to search DockerHub: {process.stderr}")
                return False, f"Failed to search DockerHub: {process.stderr}", []
                
        except Exception as e:
            logger.error(f"Error searching DockerHub: {str(e)}")
            return False, f"Error searching DockerHub: {str(e)}", []
    
    def pull_image(self, image_name=None, progress_callback=None):
        """
        Pull a Docker image with progress reporting.
        
        Args:
            image_name (str, optional): Name of the image to pull. If None, prompts user.
            progress_callback (function, optional): Callback function to report progress.
                                                   Will be called with values from 0-100.
            
        Returns:
            tuple: (success (bool), message (str))
        """
        try:
            # Get image name if not provided
            if image_name is None:
                image_name = input("Enter image name to pull (e.g., nginx:latest): ")
            
            # Pull the image with progress reporting
            cmd = ["docker", "pull", image_name]
            logger.info(f"Pulling Docker image: {image_name}")
            print(f"Pulling image {image_name}...")
            
            # Use Popen instead of run to get real-time output
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1
            )
            
            # Variables to track progress
            layers = {}
            total_layers = 0
            layers_discovered = False
            layers_downloading = False
            layers_complete = 0
            overall_progress = 0
            last_reported_progress = -1  # To avoid repeated identical progress reports
            
            # Process the output line by line
            for line in iter(process.stdout.readline, ''):
                # Log each line for debugging
                logger.debug(f"Docker pull output: {line.strip()}")
                
                if not line.strip():
                    continue  # Skip empty lines
                
                if progress_callback:
                    # Check if this is the initial "Pulling from" line which marks the start
                    if ': Pulling from ' in line:
                        # Just starting, report minimal progress
                        progress_callback(1)
                    
                    # Check if the line contains layer count information
                    if not layers_discovered and "Pulling fs layer" in line:
                        total_layers += 1
                        layers_discovered = True
                        # Report initial progress as we're now discovering layers
                        progress_callback(2)
                    
                    # Track layer status
                    layer_id = None
                    
                    # Get layer ID from line
                    if ': ' in line:
                        layer_id = line.split(':', 1)[0].strip()
                    
                    # Process different status messages:
                    if ': Downloading' in line:
                        layers_downloading = True
                        
                        # Extract layer ID and progress
                        parts = line.split(': Downloading')
                        if parts and len(parts) >= 1:
                            layer_id = parts[0].strip()
                            
                            # Parse the progress indicator [=====>   ]
                            progress_text = parts[1] if len(parts) > 1 else ""
                            if '[' in progress_text and ']' in progress_text:
                                try:
                                    # Try to extract percentage directly from progress bar
                                    bar_parts = progress_text.split('[')[1].split(']')[0]
                                    filled_ratio = bar_parts.count('=') / (len(bar_parts) - 1)  # -1 for the '>' character
                                    layer_progress = filled_ratio * 100
                                    layers[layer_id] = layer_progress
                                except (ValueError, IndexError, ZeroDivisionError):
                                    # Fallback: extract numeric values (e.g., 100MB/200MB)
                                    try:
                                        size_parts = progress_text.split(']', 1)[1].strip().split('/')
                                        if len(size_parts) == 2:
                                            current = self._parse_size(size_parts[0].strip())
                                            total = self._parse_size(size_parts[1].strip())
                                            
                                            if total > 0:
                                                layer_progress = (current / total) * 100
                                                layers[layer_id] = layer_progress
                                    except (ValueError, IndexError):
                                        # If all parsing fails, just mark as in progress
                                        if layer_id and layer_id not in layers:
                                            layers[layer_id] = 10  # Default starting progress
                    
                    # Check for various layer status messages
                    elif ': Waiting' in line and layer_id:
                        # Layer is waiting to start
                        if layer_id not in layers:
                            layers[layer_id] = 0
                            
                    elif ': Verifying Checksum' in line and layer_id:
                        # Layer download complete, verifying
                        layers[layer_id] = 90
                        
                    elif ': Download complete' in line and layer_id:
                        # Layer downloaded completely
                        layers[layer_id] = 95
                    
                    elif ': Extracting' in line and layer_id:
                        # Layer being extracted
                        parts = line.split(': Extracting')
                        if parts and len(parts) >= 1:
                            layer_id = parts[0].strip()
                            
                            # Parse the progress indicator [=====>   ]
                            progress_text = parts[1] if len(parts) > 1 else ""
                            if '[' in progress_text and ']' in progress_text:
                                # Try to get percentage based on progress bar
                                try:
                                    bar_parts = progress_text.split('[')[1].split(']')[0]
                                    filled_ratio = bar_parts.count('=') / (len(bar_parts) - 1)  # -1 for the '>' character
                                    # Extracting is between 80-99%
                                    layer_progress = 80 + (filled_ratio * 19)
                                    layers[layer_id] = layer_progress
                                except (ValueError, IndexError, ZeroDivisionError):
                                    # Just set a default value
                                    layers[layer_id] = 85
                                        
                    elif ': Pull complete' in line and layer_id:
                        # Mark layer as complete
                        parts = line.split(': Pull complete')
                        if parts and len(parts) >= 1:
                            layer_id = parts[0].strip()
                            layers[layer_id] = 100
                            layers_complete += 1
                    
                    # Calculate overall progress
                    if layers:
                        # First pass: if we're discovering layers, base progress on discovery (0-10%)
                        if total_layers > 0 and not layers_downloading:
                            overall_progress = min(10, (len(layers) / total_layers) * 10)
                        # Second pass: If downloading has started, calculate based on layer completeness
                        else:
                            # Get average progress of known layers
                            layer_values = list(layers.values())
                            if layer_values:
                                layer_avg_progress = sum(layer_values) / len(layer_values)
                                
                                # If we know total layers, weight by completion percentage
                                if total_layers > 0:
                                    completion_weight = len(layers) / total_layers
                                    overall_progress = layer_avg_progress * completion_weight
                                else:
                                    overall_progress = layer_avg_progress
                            
                            # Boost progress if we have completed layers
                            if layers_complete > 0 and total_layers > 0:
                                complete_percentage = (layers_complete / total_layers) * 100
                                # Weight the completed percentage with the average progress
                                overall_progress = (complete_percentage * 0.7) + (overall_progress * 0.3)
                        
                        # Ensure progress stays within 0-100 range and increases monotonically
                        overall_progress = min(max(overall_progress, 0), 99)  # Cap at 99% until fully done
                        
                        # Only report progress if it has changed significantly (avoid progress bar flickering)
                        current_progress = int(overall_progress)
                        if current_progress > last_reported_progress:
                            last_reported_progress = current_progress
                            progress_callback(current_progress)
            
            # Wait for process to complete
            process.wait()
            
            if process.returncode == 0:
                # Ensure we show 100% at the end
                if progress_callback:
                    progress_callback(100)
                logger.info(f"Successfully pulled image: {image_name}")
                return True, f"Successfully pulled image: {image_name}"
            else:
                error = process.stderr.read()
                logger.error(f"Failed to pull image: {error}")
                return False, f"Failed to pull image: {error}"
                
        except Exception as e:
            logger.error(f"Error pulling image: {str(e)}")
            return False, f"Error pulling image: {str(e)}"
    
    def _parse_size(self, size_str):
        """Helper to parse size strings like 100MB, 1.2GB, etc."""
        try:
            if 'KB' in size_str:
                return float(size_str.replace('KB', '')) * 1024
            elif 'MB' in size_str:
                return float(size_str.replace('MB', '')) * 1024 * 1024
            elif 'GB' in size_str:
                return float(size_str.replace('GB', '')) * 1024 * 1024 * 1024
            else:
                return float(size_str)
        except ValueError:
            return 0

    def run_container(self, image_name=None, container_name=None, ports=None, volumes=None, environment=None, detach=True):
        """
        Run a Docker container.
        
        Args:
            image_name (str, optional): Name of the image to run. If None, prompts user.
            container_name (str, optional): Name for the container. If None, Docker assigns a random name.
            ports (list, optional): List of port mappings. Format: ["8080:80", "443:443"].
            volumes (list, optional): List of volume mappings. Format: ["/host/path:/container/path"].
            environment (list, optional): List of environment variables. Format: ["KEY=value"].
            detach (bool, optional): Run container in background if True.
            
        Returns:
            tuple: (success (bool), message (str), container_id (str))
        """
        try:
            # Get image name if not provided
            if image_name is None:
                success, message, images = self.list_images()
                if success and images:
                    print("Available images:")
                    for i, image in enumerate(images):
                        print(f"{i+1}. {image['name_tag']}")
                    
                    selection = input("\nEnter image number or name: ")
                    try:
                        idx = int(selection) - 1
                        if 0 <= idx < len(images):
                            image_name = images[idx]["name_tag"].split(':')[0]
                        else:
                            image_name = selection
                    except ValueError:
                        image_name = selection
                else:
                    image_name = input("Enter image name to run: ")
            
            # Build docker run command
            cmd = ["docker", "run"]
            
            if detach:
                cmd.append("-d")
            
            if container_name:
                cmd.extend(["--name", container_name])
            
            if ports:
                for port in ports:
                    cmd.extend(["-p", port])
            
            if volumes:
                for volume in volumes:
                    cmd.extend(["-v", volume])
            
            if environment:
                for env in environment:
                    cmd.extend(["-e", env])
            
            cmd.append(image_name)
            
            logger.info(f"Running container with command: {' '.join(cmd)}")
            print(f"Starting container from image {image_name}...")
            
            process = subprocess.run(cmd, capture_output=True, text=True)
            
            if process.returncode == 0:
                container_id = process.stdout.strip()
                logger.info(f"Successfully started container: {container_id}")
                return True, f"Successfully started container: {container_id}", container_id
            else:
                logger.error(f"Failed to run container: {process.stderr}")
                return False, f"Failed to run container: {process.stderr}", None
                
        except Exception as e:
            logger.error(f"Error running container: {str(e)}")
            return False, f"Error running container: {str(e)}", None

    def start_container(self, container_id=None):
        """
        Start a stopped Docker container.
        
        Args:
            container_id (str, optional): ID or name of the container to start.
            
        Returns:
            tuple: (success (bool), message (str))
        """
        try:
            if not container_id:
                # This code path should not be reached from the UI
                return False, "No container ID specified"
            
            # Start the container
            cmd = ["docker", "start", container_id]
            logger.info(f"Starting container: {container_id}")
            
            process = subprocess.run(cmd, capture_output=True, text=True)
            
            if process.returncode == 0:
                logger.info(f"Successfully started container: {container_id}")
                return True, f"Successfully started container: {container_id}"
            else:
                logger.error(f"Failed to start container: {process.stderr}")
                return False, f"Failed to start container: {process.stderr}"
                
        except Exception as e:
            logger.error(f"Error starting container: {str(e)}")
            return False, f"Error starting container: {str(e)}"
    
    def remove_container(self, container_id=None):
        """
        Remove a Docker container.
        
        Args:
            container_id (str, optional): ID or name of the container to remove.
            
        Returns:
            tuple: (success (bool), message (str))
        """
        try:
            if not container_id:
                # This code path should not be reached from the UI
                return False, "No container ID specified"
            
            # Remove the container
            cmd = ["docker", "rm", container_id]
            logger.info(f"Removing container: {container_id}")
            
            process = subprocess.run(cmd, capture_output=True, text=True)
            
            if process.returncode == 0:
                logger.info(f"Successfully removed container: {container_id}")
                return True, f"Successfully removed container: {container_id}"
            else:
                logger.error(f"Failed to remove container: {process.stderr}")
                return False, f"Failed to remove container: {process.stderr}"
                
        except Exception as e:
            logger.error(f"Error removing container: {str(e)}")
            return False, f"Error removing container: {str(e)}"

# Example usage if run as script
if __name__ == "__main__":
    print("Docker Manager")
    print("==============")
    docker_manager = DockerManager()
    
    # Example: List images
    success, message, images = docker_manager.list_images()
    if success and images:
        print("\nAvailable Docker images:")
        for image in images:
            print(f"{image['name_tag']} - {image['id']} - {image['size']}")
    else:
        print(message)
