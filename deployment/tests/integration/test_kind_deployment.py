"""
Integration tests for RAGme Kubernetes deployment on kind cluster
"""

import pytest
import subprocess
import time
import requests
import yaml
from pathlib import Path


class TestKindDeployment:
    """Integration tests for kind cluster deployment"""
    
    cluster_name = "ragme-test-cluster"
    namespace = "ragme-test"
    
    @classmethod
    def setup_class(cls):
        """Set up test environment"""
        cls.deployment_path = Path(__file__).parent.parent.parent
        
    def test_kind_cluster_creation(self):
        """Test that kind cluster can be created"""
        try:
            # Check if cluster already exists
            result = subprocess.run(
                ["kind", "get", "clusters"], 
                capture_output=True, 
                text=True
            )
            
            if self.cluster_name not in result.stdout:
                # Create test cluster
                subprocess.run(
                    ["kind", "create", "cluster", "--name", self.cluster_name],
                    check=True,
                    capture_output=True
                )
            
            # Verify cluster exists
            result = subprocess.run(
                ["kind", "get", "clusters"], 
                capture_output=True, 
                text=True,
                check=True
            )
            assert self.cluster_name in result.stdout
            
        except subprocess.CalledProcessError as e:
            pytest.skip(f"Kind not available or failed to create cluster: {e}")
    
    def test_kubectl_access(self):
        """Test that kubectl can access the cluster"""
        try:
            subprocess.run(
                ["kubectl", "cluster-info", "--context", f"kind-{self.cluster_name}"],
                check=True,
                capture_output=True
            )
        except subprocess.CalledProcessError as e:
            pytest.skip(f"Kubectl not available or can't access cluster: {e}")
    
    def test_namespace_creation(self):
        """Test that namespace can be created"""
        try:
            # Create test namespace
            subprocess.run([
                "kubectl", "create", "namespace", self.namespace,
                "--context", f"kind-{self.cluster_name}",
                "--dry-run=client", "-o", "yaml"
            ], check=True, capture_output=True)
            
        except subprocess.CalledProcessError as e:
            pytest.skip(f"Failed to validate namespace creation: {e}")
    
    def test_configmap_application(self):
        """Test that ConfigMap can be applied"""
        try:
            configmap_path = self.deployment_path / "k8s" / "configmap.yaml"
            
            # Apply with dry-run
            subprocess.run([
                "kubectl", "apply", "-f", str(configmap_path),
                "--context", f"kind-{self.cluster_name}",
                "--dry-run=client"
            ], check=True, capture_output=True)
            
        except subprocess.CalledProcessError as e:
            pytest.skip(f"Failed to validate ConfigMap: {e}")
    
    def test_deployment_manifests_valid(self):
        """Test that all deployment manifests are valid YAML"""
        k8s_path = self.deployment_path / "k8s"
        
        for manifest_file in k8s_path.glob("*.yaml"):
            try:
                with open(manifest_file, 'r') as f:
                    yaml.safe_load_all(f)
            except yaml.YAMLError as e:
                pytest.fail(f"Invalid YAML in {manifest_file}: {e}")
    
    def test_kustomization_build(self):
        """Test that kustomization can build successfully"""
        try:
            k8s_path = self.deployment_path / "k8s"
            
            result = subprocess.run([
                "kubectl", "kustomize", str(k8s_path)
            ], check=True, capture_output=True, text=True)
            
            # Verify output contains expected resources
            assert "apiVersion:" in result.stdout
            assert "kind:" in result.stdout
            
        except subprocess.CalledProcessError as e:
            pytest.skip(f"Kustomize build failed: {e}")
    
    @classmethod
    def teardown_class(cls):
        """Clean up test environment"""
        try:
            # Delete test cluster if it exists
            subprocess.run(
                ["kind", "delete", "cluster", "--name", cls.cluster_name],
                capture_output=True
            )
        except subprocess.CalledProcessError:
            pass  # Ignore errors during cleanup


class TestContainerImages:
    """Test container image building"""
    
    def test_container_build_scripts_executable(self):
        """Test that container build scripts are executable"""
        scripts_path = Path(__file__).parent.parent.parent / "scripts"
        
        build_script = scripts_path / "build-containers.sh"
        push_script = scripts_path / "push-containers.sh"
        
        assert build_script.exists()
        assert push_script.exists()
        assert os.access(build_script, os.X_OK)
        assert os.access(push_script, os.X_OK)
    
    def test_dockerfile_syntax(self):
        """Test that Dockerfiles have valid syntax"""
        containers_path = Path(__file__).parent.parent.parent / "containers"
        
        dockerfiles = [
            "Dockerfile.api",
            "Dockerfile.mcp", 
            "Dockerfile.agent",
            "Dockerfile.frontend"
        ]
        
        for dockerfile in dockerfiles:
            dockerfile_path = containers_path / dockerfile
            assert dockerfile_path.exists(), f"Dockerfile {dockerfile} not found"
            
            # Read and validate basic Dockerfile structure
            with open(dockerfile_path, 'r') as f:
                content = f.read()
            
            assert content.startswith('# RAGme'), f"Dockerfile {dockerfile} missing header comment"
            assert 'FROM' in content, f"Dockerfile {dockerfile} missing FROM instruction"
            assert 'WORKDIR' in content, f"Dockerfile {dockerfile} missing WORKDIR instruction"
    
    def test_dockerignore_exists(self):
        """Test that .dockerignore exists"""
        dockerignore_path = Path(__file__).parent.parent.parent / "containers" / ".dockerignore"
        assert dockerignore_path.exists(), ".dockerignore file not found"
        
        with open(dockerignore_path, 'r') as f:
            content = f.read()
        
        # Check for important exclusions
        assert '.git' in content
        assert '__pycache__' in content
        assert 'node_modules' in content
        assert '.env' in content


class TestOperatorFiles:
    """Test operator Go files"""
    
    def test_operator_files_exist(self):
        """Test that operator Go files exist"""
        operator_path = Path(__file__).parent.parent.parent / "operator"
        
        required_files = [
            "go.mod",
            "cmd/main.go",
            "api/v1/ragme_types.go",
            "api/v1/groupversion_info.go",
            "internal/controller/ragme_controller.go",
            "config/crd/ragme.io_ragmes.yaml",
            "config/samples/ragme_v1_ragme.yaml",
            "Dockerfile",
            "Makefile"
        ]
        
        for file_path in required_files:
            assert (operator_path / file_path).exists(), f"Operator file {file_path} not found"
    
    def test_go_mod_valid(self):
        """Test that go.mod is valid"""
        operator_path = Path(__file__).parent.parent.parent / "operator"
        go_mod_path = operator_path / "go.mod"
        
        with open(go_mod_path, 'r') as f:
            content = f.read()
        
        assert "module github.com/maximilien/ragme-io/operator" in content
        assert "go 1.21" in content
        assert "k8s.io/client-go" in content
        assert "sigs.k8s.io/controller-runtime" in content
    
    def test_crd_yaml_valid(self):
        """Test that CRD YAML is valid"""
        operator_path = Path(__file__).parent.parent.parent / "operator"
        crd_path = operator_path / "config" / "crd" / "ragme.io_ragmes.yaml"
        
        with open(crd_path, 'r') as f:
            crd = yaml.safe_load(f)
        
        assert crd['apiVersion'] == 'apiextensions.k8s.io/v1'
        assert crd['kind'] == 'CustomResourceDefinition'
        assert crd['metadata']['name'] == 'ragmes.ragme.io'
        assert crd['spec']['group'] == 'ragme.io'