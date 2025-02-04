import docker
from pathlib import Path
import logging
import os
from typing import Dict, Any
from docker.errors import DockerException

logger = logging.getLogger(__name__)

class ContainerManager:
    def __init__(self):
        """Initialize Docker client with explicit connection settings"""
        try:
            # Create client with explicit Unix socket configuration
            self.client = docker.DockerClient(
                base_url='unix://var/run/docker.sock',
                version='auto',
                timeout=30
            )
            
            # Test connection
            version = self.client.version()
            logger.info(f"Connected to Docker daemon (version: {version.get('Version', 'unknown')})")
            
            # Setup paths and configuration
            self.dev_container_path = Path("docker/dev_container")
            self.port_start = int(os.getenv('SSH_PORT_RANGE_START', 15000))
            self.port_end = int(os.getenv('SSH_PORT_RANGE_END', 15100))
            
        except Exception as e:
            logger.error(f"Docker connection failed: {str(e)}")
            raise DockerException(f"Failed to connect to Docker daemon: {str(e)}")

    def _get_next_available_port(self) -> int:
        """Find next available port in the configured range"""
        used_ports = set()
        try:
            containers = self.client.containers.list(all=True)
            for container in containers:
                ports = container.ports.get('22/tcp', [])
                if ports:
                    used_ports.add(int(ports[0]['HostPort']))
        except Exception as e:
            logger.warning(f"Error checking existing ports: {str(e)}")
            
        for port in range(self.port_start, self.port_end + 1):
            if port not in used_ports:
                return port
        raise Exception("No available ports in the configured range")

    def create_container(self) -> str:
        """Create a new development container"""
        try:
            # Build container image
            logger.info("Building container image...")
            image, _ = self.client.images.build(
                path=str(self.dev_container_path),
                tag="dev-container:latest",
                forcerm=True
            )

            # Get next available port
            port = self._get_next_available_port()
            logger.info(f"Using port {port} for new container")

            # Create and start container
            container = self.client.containers.run(
                image="dev-container:latest",
                detach=True,
                ports={'22/tcp': port},
                volumes={
                    '/workspace': {'bind': '/workspace', 'mode': 'rw'}
                },
                environment={
                    'CONTAINER_SSH_PORT': str(port)
                },
                restart_policy={"Name": "unless-stopped"}
            )

            logger.info(f"Container created with ID: {container.id}")
            return container.id

        except Exception as e:
            logger.error(f"Failed to create container: {str(e)}")
            raise

    def remove_container(self, container_id: str) -> None:
        """Remove a container by ID"""
        try:
            container = self.client.containers.get(container_id)
            container.stop()
            container.remove(force=True)
            logger.info(f"Container {container_id} removed")
        except Exception as e:
            logger.error(f"Failed to remove container: {str(e)}")
            raise

    def get_container_info(self, container_id: str) -> Dict[str, Any]:
        """Get container information"""
        try:
            container = self.client.containers.get(container_id)
            ports = container.ports.get('22/tcp', [])
            ssh_port = int(ports[0]['HostPort']) if ports else None
            
            return {
                "id": container.id,
                "status": container.status,
                "ssh_port": ssh_port,
                "created": container.attrs['Created'],
                "name": container.name
            }
        except Exception as e:
            logger.error(f"Failed to get container info: {str(e)}")
            raise