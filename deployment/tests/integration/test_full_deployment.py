"""
Integration tests for full RAGme deployment on Kubernetes
"""

import pytest
import subprocess
import time
import requests
import yaml
from pathlib import Path


class TestFullDeployment:
    """Integration tests for complete RAGme deployment"""
    
    cluster_name = "ragme-integration-test"
    namespace = "ragme-integration"
    timeout = 300  # 5 minutes timeout for deployments
    
    @classmethod
    def setup_class(cls):
        """Set up integration test environment"""
        cls.deployment_path = Path(__file__).parent.parent.parent
        cls.project_root = cls.deployment_path.parent
        
        # Skip if required tools are not available
        cls._check_prerequisites()
    
    @classmethod
    def _check_prerequisites(cls):
        """Check if required tools are available"""
        required_tools = ['kind', 'kubectl', 'podman']
        
        for tool in required_tools:
            try:
                subprocess.run([tool, "--version"], 
                             capture_output=True, check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                pytest.skip(f"Required tool {tool} not available")
    
    def test_01_create_test_cluster(self):
        """Test creating a test kind cluster"""
        try:
            # Delete cluster if it exists
            subprocess.run([
                "kind", "delete", "cluster", "--name", self.cluster_name
            ], capture_output=True)
            
            # Create new cluster
            subprocess.run([
                "kind", "create", "cluster", "--name", self.cluster_name
            ], check=True, capture_output=True)
            
            # Verify cluster is ready
            subprocess.run([
                "kubectl", "cluster-info", "--context", f"kind-{self.cluster_name}"
            ], check=True, capture_output=True)
            
        except subprocess.CalledProcessError as e:
            pytest.fail(f"Failed to create test cluster: {e}")
    
    def test_02_build_container_images(self):
        """Test building container images"""
        try:
            # Run build script
            result = subprocess.run([
                str(self.deployment_path / "scripts" / "build-containers.sh")
            ], check=True, capture_output=True, text=True, cwd=str(self.project_root))
            
            # Verify images were built
            result = subprocess.run([
                "podman", "images", "ragme-api"
            ], check=True, capture_output=True, text=True)
            assert "ragme-api" in result.stdout
            
        except subprocess.CalledProcessError as e:
            pytest.fail(f"Failed to build container images: {e}")
    
    def test_03_load_images_to_kind(self):
        """Test loading images into kind cluster"""
        try:
            images = ["ragme-api:latest", "ragme-mcp:latest", "ragme-agent:latest", "ragme-frontend:latest"]
            
            for image in images:
                subprocess.run([
                    "kind", "load", "docker-image", image, "--name", self.cluster_name
                ], check=True, capture_output=True)
                
        except subprocess.CalledProcessError as e:
            pytest.fail(f"Failed to load images to kind: {e}")
    
    def test_04_apply_kubernetes_manifests(self):
        """Test applying Kubernetes manifests"""
        try:
            k8s_path = self.deployment_path / "k8s"
            
            # Apply with modified namespace
            subprocess.run([
                "kubectl", "kustomize", str(k8s_path)
            ], check=True, capture_output=True)
            
            # Create test namespace
            subprocess.run([
                "kubectl", "create", "namespace", self.namespace,
                "--context", f"kind-{self.cluster_name}"
            ], check=True, capture_output=True)
            
            # Apply manifests (dry-run first)
            subprocess.run([
                "kubectl", "apply", "-k", str(k8s_path),
                "--context", f"kind-{self.cluster_name}",
                "--namespace", self.namespace,
                "--dry-run=client"
            ], check=True, capture_output=True)
            
        except subprocess.CalledProcessError as e:
            pytest.fail(f"Failed to apply Kubernetes manifests: {e}")
    
    def test_05_operator_installation(self):
        """Test operator installation"""
        try:
            operator_path = self.deployment_path / "operator"
            
            # Install CRDs
            subprocess.run([
                "kubectl", "apply", "-f", str(operator_path / "config" / "crd"),
                "--context", f"kind-{self.cluster_name}"
            ], check=True, capture_output=True)
            
            # Apply RBAC
            subprocess.run([
                "kubectl", "apply", "-f", str(operator_path / "config" / "rbac"),
                "--context", f"kind-{self.cluster_name}"
            ], check=True, capture_output=True)
            
        except subprocess.CalledProcessError as e:
            pytest.fail(f"Failed to install operator: {e}")
    
    def test_06_ragme_custom_resource(self):
        """Test creating RAGme custom resource"""
        try:
            operator_path = self.deployment_path / "operator"
            sample_path = operator_path / "config" / "samples" / "ragme_v1_ragme.yaml"
            
            # Validate sample CR
            with open(sample_path, 'r') as f:
                cr = yaml.safe_load(f)
            
            assert cr['apiVersion'] == 'ragme.io/v1'
            assert cr['kind'] == 'RAGme'
            
            # Apply with dry-run
            subprocess.run([
                "kubectl", "apply", "-f", str(sample_path),
                "--context", f"kind-{self.cluster_name}",
                "--namespace", self.namespace,
                "--dry-run=client"
            ], check=True, capture_output=True)
            
        except subprocess.CalledProcessError as e:
            pytest.fail(f"Failed to validate RAGme custom resource: {e}")
    
    @classmethod
    def teardown_class(cls):
        """Clean up integration test environment"""
        try:
            # Delete test cluster
            subprocess.run([
                "kind", "delete", "cluster", "--name", cls.cluster_name
            ], capture_output=True)
        except subprocess.CalledProcessError:
            pass  # Ignore cleanup errors


class TestLocalContainerDeployment:
    """Test local container deployment with docker-compose"""
    
    def test_docker_compose_validation(self):
        """Test that docker-compose file is valid"""
        compose_path = Path(__file__).parent.parent.parent / "containers" / "docker-compose.yml"
        
        try:
            # Validate docker-compose file
            result = subprocess.run([
                "docker-compose", "-f", str(compose_path), "config"
            ], capture_output=True, text=True)
            
            # If docker-compose is not available, try podman-compose
            if result.returncode != 0:
                result = subprocess.run([
                    "podman-compose", "-f", str(compose_path), "config"
                ], capture_output=True, text=True)
            
            if result.returncode != 0:
                pytest.skip("Neither docker-compose nor podman-compose available")
                
        except FileNotFoundError:
            pytest.skip("Docker-compose or podman-compose not available")
    
    def test_container_service_definitions(self):
        """Test that all required services are defined in docker-compose"""
        compose_path = Path(__file__).parent.parent.parent / "containers" / "docker-compose.yml"
        
        with open(compose_path, 'r') as f:
            compose = yaml.safe_load(f)
        
        required_services = ['minio', 'ragme-api', 'ragme-mcp', 'ragme-agent', 'ragme-frontend']
        
        for service in required_services:
            assert service in compose['services'], f"Service {service} not found"
            
            service_def = compose['services'][service]
            
            # Check basic service configuration
            if service == 'minio':
                assert 'image' in service_def
                assert 'minio/minio' in service_def['image']
            else:
                assert 'build' in service_def
                assert 'dockerfile' in service_def['build']
    
    def test_container_environment_variables(self):
        """Test that containers have required environment variables"""
        compose_path = Path(__file__).parent.parent.parent / "containers" / "docker-compose.yml"
        
        with open(compose_path, 'r') as f:
            compose = yaml.safe_load(f)
        
        # Check API service environment
        api_env = compose['services']['ragme-api']['environment']
        assert any('RAGME_API_PORT' in str(env) for env in api_env)
        assert any('RAGME_MCP_URL' in str(env) for env in api_env)
        
        # Check MCP service environment
        mcp_env = compose['services']['ragme-mcp']['environment']
        assert any('RAGME_MCP_PORT' in str(env) for env in mcp_env)
        
        # Check Frontend service environment
        frontend_env = compose['services']['ragme-frontend']['environment']
        assert any('RAGME_API_URL' in str(env) for env in frontend_env)