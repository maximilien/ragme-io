"""
Unit tests for deployment configuration validation
"""

import pytest
import yaml
import os
from pathlib import Path


class TestDeploymentConfig:
    """Test deployment configuration validation"""
    
    def test_config_example_has_deployment_section(self):
        """Test that config.yaml.example contains the deployment section"""
        config_path = Path(__file__).parent.parent.parent.parent / "config.yaml.example"
        
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        assert 'deployment' in config
        assert 'mode' in config['deployment']
        assert 'containers' in config['deployment']
        assert 'kubernetes' in config['deployment']
    
    def test_deployment_mode_options(self):
        """Test that deployment mode has valid options"""
        config_path = Path(__file__).parent.parent.parent.parent / "config.yaml.example"
        
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        mode = config['deployment']['mode']
        assert mode in ['local', 'docker', 'kubernetes']
    
    def test_container_registry_configuration(self):
        """Test container registry configuration"""
        config_path = Path(__file__).parent.parent.parent.parent / "config.yaml.example"
        
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        containers = config['deployment']['containers']
        assert 'registry' in containers
        assert 'repository' in containers
        assert 'tag' in containers
        assert 'pull_policy' in containers
    
    def test_kubernetes_replicas_configuration(self):
        """Test Kubernetes replicas configuration"""
        config_path = Path(__file__).parent.parent.parent.parent / "config.yaml.example"
        
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        replicas = config['deployment']['kubernetes']['replicas']
        assert replicas['api'] >= 1
        assert replicas['mcp'] >= 1
        assert replicas['agent'] == 1  # Must be exactly 1
        assert replicas['frontend'] >= 1
    
    def test_kubernetes_resources_configuration(self):
        """Test Kubernetes resource configuration"""
        config_path = Path(__file__).parent.parent.parent.parent / "config.yaml.example"
        
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        resources = config['deployment']['kubernetes']['resources']
        services = ['api', 'mcp', 'agent', 'frontend', 'minio', 'weaviate']
        
        for service in services:
            assert service in resources
            assert 'requests' in resources[service]
            assert 'limits' in resources[service]
            assert 'memory' in resources[service]['requests']
            assert 'cpu' in resources[service]['requests']
    
    def test_environment_variables_in_example(self):
        """Test that env.example contains deployment environment variables"""
        env_path = Path(__file__).parent.parent.parent.parent / "env.example"
        
        with open(env_path, 'r') as f:
            content = f.read()
        
        required_vars = [
            'CONTAINER_REGISTRY',
            'CONTAINER_TAG',
            'K8S_CLUSTER_NAME',
            'K8S_NAMESPACE',
            'K8S_STORAGE_CLASS',
            'K8S_ACCESS_TYPE',
            'K8S_INGRESS_HOST',
            'K8S_OPERATOR_NAMESPACE',
            'RAGME_OPERATOR_IMAGE'
        ]
        
        for var in required_vars:
            assert var in content, f"Environment variable {var} not found in env.example"


class TestDockerfiles:
    """Test Dockerfile validation"""
    
    def test_dockerfiles_exist(self):
        """Test that all required Dockerfiles exist"""
        deployment_path = Path(__file__).parent.parent.parent
        dockerfiles = [
            'containers/Dockerfile.api',
            'containers/Dockerfile.mcp',
            'containers/Dockerfile.agent',
            'containers/Dockerfile.frontend'
        ]
        
        for dockerfile in dockerfiles:
            assert (deployment_path / dockerfile).exists(), f"Dockerfile {dockerfile} not found"
    
    def test_dockerfile_has_required_instructions(self):
        """Test that Dockerfiles have required instructions"""
        deployment_path = Path(__file__).parent.parent.parent
        dockerfiles = [
            'containers/Dockerfile.api',
            'containers/Dockerfile.mcp',
            'containers/Dockerfile.agent',
            'containers/Dockerfile.frontend'
        ]
        
        for dockerfile_path in dockerfiles:
            with open(deployment_path / dockerfile_path, 'r') as f:
                content = f.read()
            
            # Check for required instructions
            assert 'FROM' in content
            assert 'WORKDIR' in content
            assert 'COPY' in content
            assert 'EXPOSE' in content or 'agent' in dockerfile_path  # Agent doesn't expose ports
            assert 'CMD' in content
    
    def test_dockerfile_health_checks(self):
        """Test that service Dockerfiles have health checks"""
        deployment_path = Path(__file__).parent.parent.parent
        dockerfiles_with_health = [
            'containers/Dockerfile.api',
            'containers/Dockerfile.mcp',
            'containers/Dockerfile.frontend'
        ]
        
        for dockerfile_path in dockerfiles_with_health:
            with open(deployment_path / dockerfile_path, 'r') as f:
                content = f.read()
            
            assert 'HEALTHCHECK' in content, f"Health check missing in {dockerfile_path}"


class TestKubernetesManifests:
    """Test Kubernetes manifest validation"""
    
    def test_kubernetes_manifests_exist(self):
        """Test that all required Kubernetes manifests exist"""
        deployment_path = Path(__file__).parent.parent.parent
        
        # Check kind deployment manifests
        kind_k8s_path = deployment_path / "kind" / "k8s"
        kind_manifests = [
            'namespace.yaml',
            'configmap-kind.yaml',
            'shared-storage-kind.yaml',
            'minio-deployment.yaml',
            'weaviate-deployment.yaml',
            'api-deployment.yaml',
            'mcp-deployment.yaml',
            'agent-deployment.yaml',
            'frontend-deployment.yaml',
            'kustomization.yaml'
        ]
        
        for manifest in kind_manifests:
            assert (kind_k8s_path / manifest).exists(), f"Kind Kubernetes manifest {manifest} not found"
        
        # Check GKE deployment manifests
        gke_k8s_path = deployment_path / "gke" / "k8s"
        gke_manifests = [
            'namespace.yaml',
            'configmap-gke.yaml',
            'shared-storage-gke.yaml',
            'minio-deployment.yaml',
            'weaviate-deployment.yaml',
            'api-deployment-gke.yaml',
            'mcp-deployment-gke.yaml',
            'agent-deployment-gke.yaml',
            'frontend-deployment-gke.yaml',
            'kustomization-gke.yaml'
        ]
        
        for manifest in gke_manifests:
            assert (gke_k8s_path / manifest).exists(), f"GKE Kubernetes manifest {manifest} not found"
    
    def test_kustomization_yaml_valid(self):
        """Test that kustomization.yaml files are valid"""
        deployment_path = Path(__file__).parent.parent.parent
        
        # Test kind kustomization
        kind_kustomization_path = deployment_path / "kind" / "k8s" / "kustomization.yaml"
        with open(kind_kustomization_path, 'r') as f:
            kind_kustomization = yaml.safe_load(f)
        
        assert 'apiVersion' in kind_kustomization
        assert 'kind' in kind_kustomization
        assert kind_kustomization['kind'] == 'Kustomization'
        assert 'namespace' in kind_kustomization
        assert 'resources' in kind_kustomization
        
        # Test GKE kustomization
        gke_kustomization_path = deployment_path / "gke" / "k8s" / "kustomization-gke.yaml"
        with open(gke_kustomization_path, 'r') as f:
            gke_kustomization = yaml.safe_load(f)
        
        assert 'apiVersion' in gke_kustomization
        assert 'kind' in gke_kustomization
        assert gke_kustomization['kind'] == 'Kustomization'
        assert 'namespace' in gke_kustomization
        assert 'resources' in gke_kustomization
        
        # Check that all referenced resources exist for kind
        kind_k8s_path = deployment_path / "kind" / "k8s"
        for resource in kind_kustomization['resources']:
            assert (kind_k8s_path / resource).exists(), f"Kind referenced resource {resource} not found"
        
        # Check that all referenced resources exist for GKE
        gke_k8s_path = deployment_path / "gke" / "k8s"
        for resource in gke_kustomization['resources']:
            assert (gke_k8s_path / resource).exists(), f"GKE referenced resource {resource} not found"


class TestDeploymentScripts:
    """Test deployment scripts"""
    
    def test_deployment_scripts_exist(self):
        """Test that deployment scripts exist and are executable"""
        deployment_path = Path(__file__).parent.parent.parent
        scripts = [
            'deploy.sh',
            'scripts/build-containers.sh',
            'scripts/push-containers.sh'
        ]
        
        for script in scripts:
            script_path = deployment_path / script
            assert script_path.exists(), f"Script {script} not found"
            assert os.access(script_path, os.X_OK), f"Script {script} is not executable"
    
    def test_docker_compose_file_exists(self):
        """Test that docker-compose.yml exists for local testing"""
        compose_path = Path(__file__).parent.parent.parent / "containers" / "docker-compose.yml"
        assert compose_path.exists(), "docker-compose.yml not found"
        
        with open(compose_path, 'r') as f:
            compose = yaml.safe_load(f)
        
        assert 'services' in compose
        expected_services = ['minio', 'ragme-api', 'ragme-mcp', 'ragme-agent', 'ragme-frontend']
        
        for service in expected_services:
            assert service in compose['services'], f"Service {service} not found in docker-compose.yml"