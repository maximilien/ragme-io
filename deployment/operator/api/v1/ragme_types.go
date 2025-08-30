package v1

import (
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

// RAGmeSpec defines the desired state of RAGme
type RAGmeSpec struct {
	// Version specifies the RAGme version to deploy
	Version string `json:"version,omitempty"`

	// Image configuration
	Images RAGmeImages `json:"images,omitempty"`

	// Replicas configuration for each service
	Replicas RAGmeReplicas `json:"replicas,omitempty"`

	// Storage configuration
	Storage RAGmeStorage `json:"storage,omitempty"`

	// Vector database configuration
	VectorDB RAGmeVectorDB `json:"vectorDB,omitempty"`

	// Resource configuration
	Resources RAGmeResources `json:"resources,omitempty"`

	// External access configuration
	ExternalAccess RAGmeExternalAccess `json:"externalAccess,omitempty"`
}

// RAGmeImages defines container images for each service
type RAGmeImages struct {
	Registry   string `json:"registry,omitempty"`
	Repository string `json:"repository,omitempty"`
	Tag        string `json:"tag,omitempty"`
	PullPolicy string `json:"pullPolicy,omitempty"`
}

// RAGmeReplicas defines replica counts for each service
type RAGmeReplicas struct {
	API      int32 `json:"api,omitempty"`
	MCP      int32 `json:"mcp,omitempty"`
	Agent    int32 `json:"agent,omitempty"`
	Frontend int32 `json:"frontend,omitempty"`
}

// RAGmeStorage defines storage configuration
type RAGmeStorage struct {
	// MinIO configuration
	MinIO RAGmeMinIOStorage `json:"minio,omitempty"`
	
	// Shared storage for watch directory
	SharedVolume RAGmeSharedVolume `json:"sharedVolume,omitempty"`
}

// RAGmeMinIOStorage defines MinIO storage settings
type RAGmeMinIOStorage struct {
	Enabled     bool   `json:"enabled,omitempty"`
	StorageSize string `json:"storageSize,omitempty"`
	AccessKey   string `json:"accessKey,omitempty"`
	SecretKey   string `json:"secretKey,omitempty"`
}

// RAGmeSharedVolume defines shared volume settings
type RAGmeSharedVolume struct {
	Size         string `json:"size,omitempty"`
	StorageClass string `json:"storageClass,omitempty"`
}

// RAGmeVectorDB defines vector database configuration
type RAGmeVectorDB struct {
	Type     string            `json:"type,omitempty"`
	Weaviate RAGmeWeaviateDB   `json:"weaviate,omitempty"`
	Milvus   RAGmeMilvusDB     `json:"milvus,omitempty"`
}

// RAGmeWeaviateDB defines Weaviate configuration
type RAGmeWeaviateDB struct {
	Enabled     bool   `json:"enabled,omitempty"`
	StorageSize string `json:"storageSize,omitempty"`
}

// RAGmeMilvusDB defines Milvus configuration
type RAGmeMilvusDB struct {
	Enabled bool   `json:"enabled,omitempty"`
	URI     string `json:"uri,omitempty"`
	Token   string `json:"token,omitempty"`
}

// RAGmeResources defines resource requirements
type RAGmeResources struct {
	API      RAGmeServiceResources `json:"api,omitempty"`
	MCP      RAGmeServiceResources `json:"mcp,omitempty"`
	Agent    RAGmeServiceResources `json:"agent,omitempty"`
	Frontend RAGmeServiceResources `json:"frontend,omitempty"`
	MinIO    RAGmeServiceResources `json:"minio,omitempty"`
	Weaviate RAGmeServiceResources `json:"weaviate,omitempty"`
}

// RAGmeServiceResources defines resource requirements for a service
type RAGmeServiceResources struct {
	Requests RAGmeResourceRequests `json:"requests,omitempty"`
	Limits   RAGmeResourceLimits   `json:"limits,omitempty"`
}

// RAGmeResourceRequests defines resource requests
type RAGmeResourceRequests struct {
	Memory string `json:"memory,omitempty"`
	CPU    string `json:"cpu,omitempty"`
}

// RAGmeResourceLimits defines resource limits
type RAGmeResourceLimits struct {
	Memory string `json:"memory,omitempty"`
	CPU    string `json:"cpu,omitempty"`
}

// RAGmeExternalAccess defines external access configuration
type RAGmeExternalAccess struct {
	Type   string              `json:"type,omitempty"` // NodePort, LoadBalancer, Ingress
	Ingress RAGmeIngressConfig `json:"ingress,omitempty"`
}

// RAGmeIngressConfig defines ingress configuration
type RAGmeIngressConfig struct {
	Enabled     bool   `json:"enabled,omitempty"`
	Host        string `json:"host,omitempty"`
	TLSEnabled  bool   `json:"tlsEnabled,omitempty"`
	Annotations map[string]string `json:"annotations,omitempty"`
}

// RAGmeStatus defines the observed state of RAGme
type RAGmeStatus struct {
	// Phase represents the current deployment phase
	Phase string `json:"phase,omitempty"`

	// Conditions represent the latest available observations
	Conditions []metav1.Condition `json:"conditions,omitempty"`

	// Service status for each component
	Services RAGmeServiceStatus `json:"services,omitempty"`
}

// RAGmeServiceStatus defines status for all services
type RAGmeServiceStatus struct {
	API      ServiceComponentStatus `json:"api,omitempty"`
	MCP      ServiceComponentStatus `json:"mcp,omitempty"`
	Agent    ServiceComponentStatus `json:"agent,omitempty"`
	Frontend ServiceComponentStatus `json:"frontend,omitempty"`
	MinIO    ServiceComponentStatus `json:"minio,omitempty"`
	Weaviate ServiceComponentStatus `json:"weaviate,omitempty"`
}

// ServiceComponentStatus defines status for a single service component
type ServiceComponentStatus struct {
	Ready    bool   `json:"ready,omitempty"`
	Replicas int32  `json:"replicas,omitempty"`
	URL      string `json:"url,omitempty"`
}

//+kubebuilder:object:root=true
//+kubebuilder:subresource:status
//+kubebuilder:resource:scope=Namespaced

// RAGme is the Schema for the ragmes API
type RAGme struct {
	metav1.TypeMeta   `json:",inline"`
	metav1.ObjectMeta `json:"metadata,omitempty"`

	Spec   RAGmeSpec   `json:"spec,omitempty"`
	Status RAGmeStatus `json:"status,omitempty"`
}

//+kubebuilder:object:root=true

// RAGmeList contains a list of RAGme
type RAGmeList struct {
	metav1.TypeMeta `json:",inline"`
	metav1.ListMeta `json:"metadata,omitempty"`
	Items           []RAGme `json:"items"`
}

func init() {
	SchemeBuilder.Register(&RAGme{}, &RAGmeList{})
}