import unittest
import os
import json
import shutil
from unittest.mock import patch, MagicMock
from services.docker_manager import DockerManager

class TestDockerManager(unittest.TestCase):
    """Unit tests for the DockerManager class"""
    
    def setUp(self):
        """Set up test environment before each test"""
        # Create test directories
        self.test_dockerfiles_dir = os.path.join('test_data', 'dockerfiles')
        self.test_docker_data_dir = os.path.join('test_data', 'docker')
        
        # Clean up and recreate test directories
        for dir_path in [self.test_dockerfiles_dir, self.test_docker_data_dir]:
            if os.path.exists(dir_path):
                shutil.rmtree(dir_path)
            os.makedirs(dir_path, exist_ok=True)
        
        # Create a DockerManager with test directories
        self.docker_manager = DockerManager(
            dockerfiles_dir=self.test_dockerfiles_dir,
            docker_data_dir=self.test_docker_data_dir
        )
    
    def tearDown(self):
        """Clean up after each test"""
        if os.path.exists('test_data'):
            shutil.rmtree('test_data')
    
    def test_create_dockerfile_project(self):
        """Test creating a Docker project with Dockerfile and other files"""
        project_name = "test_project"
        dockerfile_content = "FROM python:3.9-slim\nWORKDIR /app"
        requirements_content = "flask==2.0.1\nnumpy>=1.20.0"
        entrypoint_content = "from flask import Flask\n\napp = Flask(__name__)"
        entrypoint_file = "app.py"
        
        success, message, project_path = self.docker_manager.create_dockerfile_project(
            project_name, dockerfile_content, requirements_content,
            entrypoint_content, entrypoint_file
        )
        
        # Verify the project was created successfully
        self.assertTrue(success)
        self.assertIn("Docker project created successfully", message)
        self.assertEqual(project_path, os.path.join(self.test_dockerfiles_dir, project_name))
        
        # Verify the project files were created correctly
        dockerfile_path = os.path.join(project_path, "Dockerfile")
        requirements_path = os.path.join(project_path, "requirements.txt")
        entrypoint_path = os.path.join(project_path, entrypoint_file)
        
        self.assertTrue(os.path.exists(dockerfile_path))
        self.assertTrue(os.path.exists(requirements_path))
        self.assertTrue(os.path.exists(entrypoint_path))
        
        # Verify file contents
        with open(dockerfile_path, 'r') as f:
            self.assertEqual(f.read(), dockerfile_content)
        
        with open(requirements_path, 'r') as f:
            self.assertEqual(f.read(), requirements_content)
        
        with open(entrypoint_path, 'r') as f:
            self.assertEqual(f.read(), entrypoint_content)
    
    def test_create_dockerfile_project_minimal(self):
        """Test creating a Docker project with only a Dockerfile"""
        project_name = "minimal_project"
        dockerfile_content = "FROM nginx:latest"
        
        success, message, project_path = self.docker_manager.create_dockerfile_project(
            project_name, dockerfile_content
        )
        
        # Verify the project was created successfully
        self.assertTrue(success)
        self.assertIn("Docker project created successfully", message)
        
        # Verify only the Dockerfile was created
        dockerfile_path = os.path.join(project_path, "Dockerfile")
        requirements_path = os.path.join(project_path, "requirements.txt")
        
        self.assertTrue(os.path.exists(dockerfile_path))
        self.assertFalse(os.path.exists(requirements_path))
        
        # Verify Dockerfile content
        with open(dockerfile_path, 'r') as f:
            self.assertEqual(f.read(), dockerfile_content)
    
    def test_create_dockerfile(self):
        """Test creating a standalone Dockerfile"""
        dockerfile_path = os.path.join(self.test_dockerfiles_dir, "TestDockerfile")
        dockerfile_content = "FROM ubuntu:20.04\nRUN apt-get update"
        
        success, message, path = self.docker_manager.create_dockerfile(
            dockerfile_path, dockerfile_content
        )
        
        # Verify the Dockerfile was created successfully
        self.assertTrue(success)
        self.assertIn("Dockerfile created successfully", message)
        self.assertEqual(path, dockerfile_path)
        
        # Verify the file exists and has the correct content
        self.assertTrue(os.path.exists(dockerfile_path))
        with open(dockerfile_path, 'r') as f:
            self.assertEqual(f.read(), dockerfile_content)
    
    @patch('subprocess.run')
    def test_build_image(self, mock_run):
        """Test building a Docker image from a Dockerfile"""
        # Create a test Dockerfile
        project_name = "build_test"
        project_path = os.path.join(self.test_dockerfiles_dir, project_name)
        dockerfile_path = os.path.join(project_path, "Dockerfile")
        
        os.makedirs(project_path, exist_ok=True)
        with open(dockerfile_path, 'w') as f:
            f.write("FROM python:3.9-slim")
        
        # Mock the subprocess.run call
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = "Successfully built 123456"
        mock_run.return_value = mock_process
        
        # Build the image
        success, message = self.docker_manager.build_image(
            dockerfile_path=dockerfile_path,
            image_name="test-image:latest"
        )
        
        # Verify the image was built successfully
        self.assertTrue(success)
        self.assertIn("Successfully built Docker image", message)
        
        # Verify subprocess.run was called with the correct command
        mock_run.assert_called()
    
    @patch('subprocess.run')
    def test_list_images(self, mock_run):
        """Test listing Docker images"""
        # Mock the subprocess.run call
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = "python:3.9\t123456\t100MB\t2 days ago\nnginx:latest\t789012\t20MB\t3 days ago"
        mock_run.return_value = mock_process
        
        # List the images
        success, message, images = self.docker_manager.list_images()
        
        # Verify the images were listed successfully
        self.assertTrue(success)
        self.assertEqual(len(images), 2)
        self.assertEqual(images[0]['name_tag'], "python:3.9")
        self.assertEqual(images[0]['id'], "123456")
        self.assertEqual(images[1]['name_tag'], "nginx:latest")
        self.assertEqual(images[1]['id'], "789012")
        
        # Verify subprocess.run was called with the correct command
        mock_run.assert_called_with(
            ["docker", "images", "--format", "{{.Repository}}:{{.Tag}}\t{{.ID}}\t{{.Size}}\t{{.CreatedAt}}"],
            capture_output=True, text=True
        )
    
    @patch('subprocess.run')
    def test_list_containers(self, mock_run):
        """Test listing Docker containers"""
        # Mock the subprocess.run call
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = "123456\tpython:3.9\tUp 2 hours\ttest-container\t80/tcp, 443/tcp"
        mock_run.return_value = mock_process
        
        # List the containers
        success, message, containers = self.docker_manager.list_containers()
        
        # Verify the containers were listed successfully
        self.assertTrue(success)
        self.assertEqual(len(containers), 1)
        self.assertEqual(containers[0]['id'], "123456")
        self.assertEqual(containers[0]['image'], "python:3.9")
        self.assertEqual(containers[0]['name'], "test-container")
        
        # Verify subprocess.run was called with the correct command
        mock_run.assert_called()
    
    @patch('subprocess.run')
    def test_start_container(self, mock_run):
        """Test starting a Docker container"""
        # Mock the subprocess.run call
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = "Container started"
        mock_run.return_value = mock_process
        
        # Start the container
        container_id = "123456"
        success, message = self.docker_manager.start_container(container_id)
        
        # Verify the container was started successfully
        self.assertTrue(success)
        self.assertIn(f"Successfully started container: {container_id}", message)
        
        # Verify subprocess.run was called with the correct command
        mock_run.assert_called_with(
            ["docker", "start", container_id],
            capture_output=True, text=True
        )
    
    @patch('subprocess.run')
    def test_stop_container(self, mock_run):
        """Test stopping a Docker container"""
        # Mock the subprocess.run call
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = "Container stopped"
        mock_run.return_value = mock_process
        
        # Stop the container
        container_id = "123456"
        success, message = self.docker_manager.stop_container(container_id)
        
        # Verify the container was stopped successfully
        self.assertTrue(success)
        self.assertIn(f"Successfully stopped container: {container_id}", message)
        
        # Verify subprocess.run was called with the correct command
        mock_run.assert_called_with(
            ["docker", "stop", container_id],
            capture_output=True, text=True
        )
    
    @patch('subprocess.run')
    def test_remove_container(self, mock_run):
        """Test removing a Docker container"""
        # Mock the subprocess.run call
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = "Container removed"
        mock_run.return_value = mock_process
        
        # Remove the container
        container_id = "123456"
        success, message = self.docker_manager.remove_container(container_id)
        
        # Verify the container was removed successfully
        self.assertTrue(success)
        self.assertIn(f"Successfully removed container: {container_id}", message)
        
        # Verify subprocess.run was called with the correct command
        mock_run.assert_called_with(
            ["docker", "rm", container_id],
            capture_output=True, text=True
        )
    
    @patch('subprocess.run')
    def test_run_container(self, mock_run):
        """Test running a Docker container"""
        # Mock the subprocess.run call
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = "123456789abcdef"
        mock_run.return_value = mock_process
        
        # Run the container
        image_name = "python:3.9"
        container_name = "test-container"
        ports = ["8080:80"]
        
        success, message, container_id = self.docker_manager.run_container(
            image_name=image_name,
            container_name=container_name,
            ports=ports,
            detach=True
        )
        
        # Verify the container was run successfully
        self.assertTrue(success)
        self.assertIn(f"Successfully started container: {container_id}", message)
        self.assertEqual(container_id, "123456789abcdef")
        
        # Verify subprocess.run was called with the correct command
        mock_run.assert_called()
        cmd = mock_run.call_args[0][0]
        self.assertEqual(cmd[0], "docker")
        self.assertEqual(cmd[1], "run")
        self.assertIn("-d", cmd)  # Detached mode
        self.assertIn("--name", cmd)
        self.assertIn(container_name, cmd)
        self.assertIn("-p", cmd)
        self.assertIn("8080:80", cmd)
        self.assertIn(image_name, cmd)
    
    @patch('subprocess.run')
    def test_search_local_image(self, mock_run):
        """Test searching for a local Docker image"""
        # Mock the subprocess.run call
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = "python:3.9\t123456\t100MB\t2 days ago"
        mock_run.return_value = mock_process
        
        # Search for the image
        search_term = "python"
        success, message, images = self.docker_manager.search_local_image(search_term)
        
        # Verify the search was successful
        self.assertTrue(success)
        self.assertEqual(len(images), 1)
        self.assertEqual(images[0]['name_tag'], "python:3.9")
        
        # Verify subprocess.run was called with the correct command
        mock_run.assert_called()
    
    @patch('subprocess.run')
    def test_search_dockerhub(self, mock_run):
        """Test searching for a Docker image on DockerHub"""
        # Mock the subprocess.run call
        mock_process = MagicMock()
        mock_process.returncode = 0
        # Return JSON data for each result instead of table format
        mock_process.stdout = '{"Name":"python","Description":"Python is a programming language","StarCount":8112,"IsOfficial":"[OK]","IsAutomated":""}\n{"Name":"python/someimage","Description":"A Python image with additional tools","StarCount":123,"IsOfficial":"","IsAutomated":"[OK]"}'
        mock_run.return_value = mock_process
        
        # Search for the image
        search_term = "python"
        success, message, results = self.docker_manager.search_dockerhub(search_term)
        
        # Verify the search was successful
        self.assertTrue(success)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]['name'], "python")
        self.assertTrue(results[0]['official'])
        self.assertEqual(results[0]['stars'], "8112")
        self.assertEqual(results[1]['name'], "python/someimage")
        self.assertFalse(results[1]['official'])
        
        # Verify subprocess.run was called with the correct command
        mock_run.assert_called_with(
            ["docker", "search", "--format", "{{json .}}", search_term],
            capture_output=True, text=True
        )

if __name__ == '__main__':
    unittest.main() 