package v1

import (
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
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

// DeepCopyInto copies the receiver into the given *RAGmeSpec
func (r *RAGmeSpec) DeepCopyInto(out *RAGmeSpec) {
	*out = *r
	r.Images.DeepCopyInto(&out.Images)
	r.Replicas.DeepCopyInto(&out.Replicas)
	r.Storage.DeepCopyInto(&out.Storage)
	r.VectorDB.DeepCopyInto(&out.VectorDB)
	r.Resources.DeepCopyInto(&out.Resources)
	r.ExternalAccess.DeepCopyInto(&out.ExternalAccess)
}

// DeepCopy returns a deep copy of RAGmeSpec
func (r *RAGmeSpec) DeepCopy() *RAGmeSpec {
	if r == nil {
		return nil
	}
	out := new(RAGmeSpec)
	r.DeepCopyInto(out)
	return out
}

// RAGmeImages defines container images for each service
type RAGmeImages struct {
	Registry   string `json:"registry,omitempty"`
	Repository string `json:"repository,omitempty"`
	Tag        string `json:"tag,omitempty"`
	PullPolicy string `json:"pullPolicy,omitempty"`
}

// DeepCopyInto copies the receiver into the given *RAGmeImages
func (r *RAGmeImages) DeepCopyInto(out *RAGmeImages) {
	*out = *r
}

// DeepCopy returns a deep copy of RAGmeImages
func (r *RAGmeImages) DeepCopy() *RAGmeImages {
	if r == nil {
		return nil
	}
	out := new(RAGmeImages)
	r.DeepCopyInto(out)
	return out
}

// RAGmeReplicas defines replica counts for each service
type RAGmeReplicas struct {
	API      int32 `json:"api,omitempty"`
	MCP      int32 `json:"mcp,omitempty"`
	Agent    int32 `json:"agent,omitempty"`
	Frontend int32 `json:"frontend,omitempty"`
}

// DeepCopyInto copies the receiver into the given *RAGmeReplicas
func (r *RAGmeReplicas) DeepCopyInto(out *RAGmeReplicas) {
	*out = *r
}

// DeepCopy returns a deep copy of RAGmeReplicas
func (r *RAGmeReplicas) DeepCopy() *RAGmeReplicas {
	if r == nil {
		return nil
	}
	out := new(RAGmeReplicas)
	r.DeepCopyInto(out)
	return out
}

// RAGmeStorage defines storage configuration
type RAGmeStorage struct {
	// MinIO configuration
	MinIO RAGmeMinIOStorage `json:"minio,omitempty"`

	// Shared storage for watch directory
	SharedVolume RAGmeSharedVolume `json:"sharedVolume,omitempty"`
}

// DeepCopyInto copies the receiver into the given *RAGmeStorage
func (r *RAGmeStorage) DeepCopyInto(out *RAGmeStorage) {
	*out = *r
	r.MinIO.DeepCopyInto(&out.MinIO)
	r.SharedVolume.DeepCopyInto(&out.SharedVolume)
}

// DeepCopy returns a deep copy of RAGmeStorage
func (r *RAGmeStorage) DeepCopy() *RAGmeStorage {
	if r == nil {
		return nil
	}
	out := new(RAGmeStorage)
	r.DeepCopyInto(out)
	return out
}

// RAGmeMinIOStorage defines MinIO storage settings
type RAGmeMinIOStorage struct {
	Enabled     bool   `json:"enabled,omitempty"`
	StorageSize string `json:"storageSize,omitempty"`
	AccessKey   string `json:"accessKey,omitempty"`
	SecretKey   string `json:"secretKey,omitempty"`
}

// DeepCopyInto copies the receiver into the given *RAGmeMinIOStorage
func (r *RAGmeMinIOStorage) DeepCopyInto(out *RAGmeMinIOStorage) {
	*out = *r
}

// DeepCopy returns a deep copy of RAGmeMinIOStorage
func (r *RAGmeMinIOStorage) DeepCopy() *RAGmeMinIOStorage {
	if r == nil {
		return nil
	}
	out := new(RAGmeMinIOStorage)
	r.DeepCopyInto(out)
	return out
}

// RAGmeSharedVolume defines shared volume settings
type RAGmeSharedVolume struct {
	Size         string `json:"size,omitempty"`
	StorageClass string `json:"storageClass,omitempty"`
}

// DeepCopyInto copies the receiver into the given *RAGmeSharedVolume
func (r *RAGmeSharedVolume) DeepCopyInto(out *RAGmeSharedVolume) {
	*out = *r
}

// DeepCopy returns a deep copy of RAGmeSharedVolume
func (r *RAGmeSharedVolume) DeepCopy() *RAGmeSharedVolume {
	if r == nil {
		return nil
	}
	out := new(RAGmeSharedVolume)
	r.DeepCopyInto(out)
	return out
}

// RAGmeVectorDB defines vector database configuration
type RAGmeVectorDB struct {
	Type     string          `json:"type,omitempty"`
	Weaviate RAGmeWeaviateDB `json:"weaviate,omitempty"`
	Milvus   RAGmeMilvusDB   `json:"milvus,omitempty"`
}

// DeepCopyInto copies the receiver into the given *RAGmeVectorDB
func (r *RAGmeVectorDB) DeepCopyInto(out *RAGmeVectorDB) {
	*out = *r
	r.Weaviate.DeepCopyInto(&out.Weaviate)
	r.Milvus.DeepCopyInto(&out.Milvus)
}

// DeepCopy returns a deep copy of RAGmeVectorDB
func (r *RAGmeVectorDB) DeepCopy() *RAGmeVectorDB {
	if r == nil {
		return nil
	}
	out := new(RAGmeVectorDB)
	r.DeepCopyInto(out)
	return out
}

// RAGmeWeaviateDB defines Weaviate configuration
type RAGmeWeaviateDB struct {
	Enabled     bool   `json:"enabled,omitempty"`
	StorageSize string `json:"storageSize,omitempty"`
}

// DeepCopyInto copies the receiver into the given *RAGmeWeaviateDB
func (r *RAGmeWeaviateDB) DeepCopyInto(out *RAGmeWeaviateDB) {
	*out = *r
}

// DeepCopy returns a deep copy of RAGmeWeaviateDB
func (r *RAGmeWeaviateDB) DeepCopy() *RAGmeWeaviateDB {
	if r == nil {
		return nil
	}
	out := new(RAGmeWeaviateDB)
	r.DeepCopyInto(out)
	return out
}

// RAGmeMilvusDB defines Milvus configuration
type RAGmeMilvusDB struct {
	Enabled bool   `json:"enabled,omitempty"`
	URI     string `json:"uri,omitempty"`
	Token   string `json:"token,omitempty"`
}

// DeepCopyInto copies the receiver into the given *RAGmeMilvusDB
func (r *RAGmeMilvusDB) DeepCopyInto(out *RAGmeMilvusDB) {
	*out = *r
}

// DeepCopy returns a deep copy of RAGmeMilvusDB
func (r *RAGmeMilvusDB) DeepCopy() *RAGmeMilvusDB {
	if r == nil {
		return nil
	}
	out := new(RAGmeMilvusDB)
	r.DeepCopyInto(out)
	return out
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

// DeepCopyInto copies the receiver into the given *RAGmeResources
func (r *RAGmeResources) DeepCopyInto(out *RAGmeResources) {
	*out = *r
	r.API.DeepCopyInto(&out.API)
	r.MCP.DeepCopyInto(&out.MCP)
	r.Agent.DeepCopyInto(&out.Agent)
	r.Frontend.DeepCopyInto(&out.Frontend)
	r.MinIO.DeepCopyInto(&out.MinIO)
	r.Weaviate.DeepCopyInto(&out.Weaviate)
}

// DeepCopy returns a deep copy of RAGmeResources
func (r *RAGmeResources) DeepCopy() *RAGmeResources {
	if r == nil {
		return nil
	}
	out := new(RAGmeResources)
	r.DeepCopyInto(out)
	return out
}

// RAGmeServiceResources defines resource requirements for a service
type RAGmeServiceResources struct {
	Requests RAGmeResourceRequests `json:"requests,omitempty"`
	Limits   RAGmeResourceLimits   `json:"limits,omitempty"`
}

// DeepCopyInto copies the receiver into the given *RAGmeServiceResources
func (r *RAGmeServiceResources) DeepCopyInto(out *RAGmeServiceResources) {
	*out = *r
	r.Requests.DeepCopyInto(&out.Requests)
	r.Limits.DeepCopyInto(&out.Limits)
}

// DeepCopy returns a deep copy of RAGmeServiceResources
func (r *RAGmeServiceResources) DeepCopy() *RAGmeServiceResources {
	if r == nil {
		return nil
	}
	out := new(RAGmeServiceResources)
	r.DeepCopyInto(out)
	return out
}

// RAGmeResourceRequests defines resource requests
type RAGmeResourceRequests struct {
	Memory string `json:"memory,omitempty"`
	CPU    string `json:"cpu,omitempty"`
}

// DeepCopyInto copies the receiver into the given *RAGmeResourceRequests
func (r *RAGmeResourceRequests) DeepCopyInto(out *RAGmeResourceRequests) {
	*out = *r
}

// DeepCopy returns a deep copy of RAGmeResourceRequests
func (r *RAGmeResourceRequests) DeepCopy() *RAGmeResourceRequests {
	if r == nil {
		return nil
	}
	out := new(RAGmeResourceRequests)
	r.DeepCopyInto(out)
	return out
}

// RAGmeResourceLimits defines resource limits
type RAGmeResourceLimits struct {
	Memory string `json:"memory,omitempty"`
	CPU    string `json:"cpu,omitempty"`
}

// DeepCopyInto copies the receiver into the given *RAGmeResourceLimits
func (r *RAGmeResourceLimits) DeepCopyInto(out *RAGmeResourceLimits) {
	*out = *r
}

// DeepCopy returns a deep copy of RAGmeResourceLimits
func (r *RAGmeResourceLimits) DeepCopy() *RAGmeResourceLimits {
	if r == nil {
		return nil
	}
	out := new(RAGmeResourceLimits)
	r.DeepCopyInto(out)
	return out
}

// RAGmeExternalAccess defines external access configuration
type RAGmeExternalAccess struct {
	Type    string             `json:"type,omitempty"` // NodePort, LoadBalancer, Ingress
	Ingress RAGmeIngressConfig `json:"ingress,omitempty"`
}

// DeepCopyInto copies the receiver into the given *RAGmeExternalAccess
func (r *RAGmeExternalAccess) DeepCopyInto(out *RAGmeExternalAccess) {
	*out = *r
	r.Ingress.DeepCopyInto(&out.Ingress)
}

// DeepCopy returns a deep copy of RAGmeExternalAccess
func (r *RAGmeExternalAccess) DeepCopy() *RAGmeExternalAccess {
	if r == nil {
		return nil
	}
	out := new(RAGmeExternalAccess)
	r.DeepCopyInto(out)
	return out
}

// RAGmeIngressConfig defines ingress configuration
type RAGmeIngressConfig struct {
	Enabled     bool              `json:"enabled,omitempty"`
	Host        string            `json:"host,omitempty"`
	TLSEnabled  bool              `json:"tlsEnabled,omitempty"`
	Annotations map[string]string `json:"annotations,omitempty"`
}

// DeepCopyInto copies the receiver into the given *RAGmeIngressConfig
func (r *RAGmeIngressConfig) DeepCopyInto(out *RAGmeIngressConfig) {
	*out = *r
	if r.Annotations != nil {
		out.Annotations = make(map[string]string)
		for k, v := range r.Annotations {
			out.Annotations[k] = v
		}
	}
}

// DeepCopy returns a deep copy of RAGmeIngressConfig
func (r *RAGmeIngressConfig) DeepCopy() *RAGmeIngressConfig {
	if r == nil {
		return nil
	}
	out := new(RAGmeIngressConfig)
	r.DeepCopyInto(out)
	return out
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

// DeepCopyInto copies the receiver into the given *RAGmeStatus
func (r *RAGmeStatus) DeepCopyInto(out *RAGmeStatus) {
	*out = *r
	r.Conditions = make([]metav1.Condition, len(r.Conditions))
	for i := range r.Conditions {
		r.Conditions[i].DeepCopyInto(&out.Conditions[i])
	}
	r.Services.DeepCopyInto(&out.Services)
}

// DeepCopy returns a deep copy of RAGmeStatus
func (r *RAGmeStatus) DeepCopy() *RAGmeStatus {
	if r == nil {
		return nil
	}
	out := new(RAGmeStatus)
	r.DeepCopyInto(out)
	return out
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

// DeepCopyInto copies the receiver into the given *RAGmeServiceStatus
func (r *RAGmeServiceStatus) DeepCopyInto(out *RAGmeServiceStatus) {
	*out = *r
	r.API.DeepCopyInto(&out.API)
	r.MCP.DeepCopyInto(&out.MCP)
	r.Agent.DeepCopyInto(&out.Agent)
	r.Frontend.DeepCopyInto(&out.Frontend)
	r.MinIO.DeepCopyInto(&out.MinIO)
	r.Weaviate.DeepCopyInto(&out.Weaviate)
}

// DeepCopy returns a deep copy of RAGmeServiceStatus
func (r *RAGmeServiceStatus) DeepCopy() *RAGmeServiceStatus {
	if r == nil {
		return nil
	}
	out := new(RAGmeServiceStatus)
	r.DeepCopyInto(out)
	return out
}

// ServiceComponentStatus defines status for a single service component
type ServiceComponentStatus struct {
	Ready    bool   `json:"ready,omitempty"`
	Replicas int32  `json:"replicas,omitempty"`
	URL      string `json:"url,omitempty"`
}

// DeepCopyInto copies the receiver into the given *ServiceComponentStatus
func (r *ServiceComponentStatus) DeepCopyInto(out *ServiceComponentStatus) {
	*out = *r
}

// DeepCopy returns a deep copy of ServiceComponentStatus
func (r *ServiceComponentStatus) DeepCopy() *ServiceComponentStatus {
	if r == nil {
		return nil
	}
	out := new(ServiceComponentStatus)
	r.DeepCopyInto(out)
	return out
}

// +kubebuilder:object:root=true
// +kubebuilder:subresource:status
// +kubebuilder:resource:scope=Namespaced

// RAGme is the Schema for the ragmes API
type RAGme struct {
	metav1.TypeMeta   `json:",inline"`
	metav1.ObjectMeta `json:"metadata,omitempty"`

	Spec   RAGmeSpec   `json:"spec,omitempty"`
	Status RAGmeStatus `json:"status,omitempty"`
}

// DeepCopyObject implements runtime.Object
func (r *RAGme) DeepCopyObject() runtime.Object {
	if c := r.DeepCopy(); c != nil {
		return c
	}
	return nil
}

// DeepCopy implements runtime.Object
func (r *RAGme) DeepCopy() *RAGme {
	if r == nil {
		return nil
	}
	out := new(RAGme)
	r.DeepCopyInto(out)
	return out
}

// DeepCopyInto implements runtime.Object
func (r *RAGme) DeepCopyInto(out *RAGme) {
	*out = *r
	out.TypeMeta = r.TypeMeta
	r.ObjectMeta.DeepCopyInto(&out.ObjectMeta)
	r.Spec.DeepCopyInto(&out.Spec)
	r.Status.DeepCopyInto(&out.Status)
}

// +kubebuilder:object:root=true

// RAGmeList contains a list of RAGme
type RAGmeList struct {
	metav1.TypeMeta `json:",inline"`
	metav1.ListMeta `json:"metadata,omitempty"`
	Items           []RAGme `json:"items"`
}

// DeepCopyObject implements runtime.Object
func (r *RAGmeList) DeepCopyObject() runtime.Object {
	if c := r.DeepCopy(); c != nil {
		return c
	}
	return nil
}

// DeepCopy implements runtime.Object
func (r *RAGmeList) DeepCopy() *RAGmeList {
	if r == nil {
		return nil
	}
	out := new(RAGmeList)
	r.DeepCopyInto(out)
	return out
}

// DeepCopyInto implements runtime.Object
func (r *RAGmeList) DeepCopyInto(out *RAGmeList) {
	*out = *r
	out.TypeMeta = r.TypeMeta
	r.ListMeta.DeepCopyInto(&out.ListMeta)
	if r.Items != nil {
		in, out := &r.Items, &out.Items
		*out = make([]RAGme, len(*in))
		for i := range *in {
			(*in)[i].DeepCopyInto(&(*out)[i])
		}
	}
}

func init() {
	SchemeBuilder.Register(&RAGme{}, &RAGmeList{})
}
