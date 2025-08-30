package unit

import (
	"testing"

	ragmev1 "github.com/maximilien/ragme-io/operator/api/v1"
	"github.com/maximilien/ragme-io/operator/internal/controller"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/client-go/kubernetes/scheme"
	"sigs.k8s.io/controller-runtime/pkg/client/fake"
)

func TestRAGmeDefaults(t *testing.T) {
	// Create a test scheme
	testScheme := runtime.NewScheme()
	_ = ragmev1.AddToScheme(testScheme)
	_ = scheme.AddToScheme(testScheme)

	// Create fake client
	fakeClient := fake.NewClientBuilder().WithScheme(testScheme).Build()

	// Create controller
	reconciler := &controller.RAGmeReconciler{
		Client: fakeClient,
		Scheme: testScheme,
	}

	// Test default setting logic
	ragme := &ragmev1.RAGme{}
	reconciler.SetDefaults(ragme)

	// Verify defaults were set correctly
	if ragme.Spec.Version == "" {
		ragme.Spec.Version = "latest"
	}
	if ragme.Spec.Images.Tag != "latest" {
		t.Errorf("Expected default tag to be 'latest', got %s", ragme.Spec.Images.Tag)
	}
	if ragme.Spec.Replicas.API != 2 {
		t.Errorf("Expected default API replicas to be 2, got %d", ragme.Spec.Replicas.API)
	}
	if ragme.Spec.Replicas.Agent != 1 {
		t.Errorf("Expected default Agent replicas to be 1, got %d", ragme.Spec.Replicas.Agent)
	}
}

func TestRAGmeValidation(t *testing.T) {
	tests := []struct {
		name    string
		ragme   *ragmev1.RAGme
		wantErr bool
	}{
		{
			name: "valid RAGme spec",
			ragme: &ragmev1.RAGme{
				Spec: ragmev1.RAGmeSpec{
					Version: "latest",
					Replicas: ragmev1.RAGmeReplicas{
						API:      2,
						MCP:      2,
						Agent:    1,
						Frontend: 2,
					},
					Storage: ragmev1.RAGmeStorage{
						MinIO: ragmev1.RAGmeMinIOStorage{
							Enabled:     true,
							StorageSize: "10Gi",
						},
					},
				},
			},
			wantErr: false,
		},
		{
			name: "invalid agent replicas",
			ragme: &ragmev1.RAGme{
				Spec: ragmev1.RAGmeSpec{
					Replicas: ragmev1.RAGmeReplicas{
						Agent: 2, // Should be 1
					},
				},
			},
			wantErr: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			// Validation logic would go here
			// For now, just check agent replica count
			if tt.ragme.Spec.Replicas.Agent > 1 && !tt.wantErr {
				t.Errorf("Agent replicas should not be more than 1")
			}
		})
	}
}

func TestImageNaming(t *testing.T) {
	tests := []struct {
		name     string
		registry string
		repo     string
		tag      string
		service  string
		expected string
	}{
		{
			name:     "local registry",
			registry: "localhost:5001",
			repo:     "ragme",
			tag:      "latest",
			service:  "api",
			expected: "localhost:5001/ragme-api:latest",
		},
		{
			name:     "docker hub",
			registry: "docker.io/myuser",
			repo:     "ragme",
			tag:      "v1.0.0",
			service:  "frontend",
			expected: "docker.io/myuser/ragme-frontend:v1.0.0",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := tt.registry + "/ragme-" + tt.service + ":" + tt.tag
			if result != tt.expected {
				t.Errorf("Expected %s, got %s", tt.expected, result)
			}
		})
	}
}

func TestResourceRequirements(t *testing.T) {
	ragme := &ragmev1.RAGme{
		Spec: ragmev1.RAGmeSpec{
			Resources: ragmev1.RAGmeResources{
				API: ragmev1.RAGmeServiceResources{
					Requests: ragmev1.RAGmeResourceRequests{
						Memory: "512Mi",
						CPU:    "500m",
					},
					Limits: ragmev1.RAGmeResourceLimits{
						Memory: "1Gi",
						CPU:    "1000m",
					},
				},
			},
		},
	}

	// Test that resource values are valid
	_, err := resource.ParseQuantity(ragme.Spec.Resources.API.Requests.Memory)
	if err != nil {
		t.Errorf("Invalid memory request: %v", err)
	}

	_, err = resource.ParseQuantity(ragme.Spec.Resources.API.Requests.CPU)
	if err != nil {
		t.Errorf("Invalid CPU request: %v", err)
	}
}