package controller

import (
	"context"
	"fmt"
	"time"

	appsv1 "k8s.io/api/apps/v1"
	corev1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/api/errors"
	"k8s.io/apimachinery/pkg/api/resource"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/types"
	"k8s.io/apimachinery/pkg/util/intstr"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/client"
	"sigs.k8s.io/controller-runtime/pkg/log"

	ragmev1 "github.com/maximilien/ragme-io/operator/api/v1"
)

// RAGmeReconciler reconciles a RAGme object
type RAGmeReconciler struct {
	client.Client
	Scheme *runtime.Scheme
}

// +kubebuilder:rbac:groups=ragme.io,resources=ragmes,verbs=get;list;watch;create;update;patch;delete
// +kubebuilder:rbac:groups=ragme.io,resources=ragmes/status,verbs=get;update;patch
// +kubebuilder:rbac:groups=ragme.io,resources=ragmes/finalizers,verbs=update
// +kubebuilder:rbac:groups=apps,resources=deployments,verbs=get;list;watch;create;update;patch;delete
// +kubebuilder:rbac:groups="",resources=services,verbs=get;list;watch;create;update;patch;delete
// +kubebuilder:rbac:groups="",resources=configmaps,verbs=get;list;watch;create;update;patch;delete
// +kubebuilder:rbac:groups="",resources=secrets,verbs=get;list;watch;create;update;patch;delete
// +kubebuilder:rbac:groups="",resources=persistentvolumeclaims,verbs=get;list;watch;create;update;patch;delete

// Reconcile is part of the main kubernetes reconciliation loop which aims to
// move the current state of the cluster closer to the desired state.
func (r *RAGmeReconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
	logger := log.FromContext(ctx)

	// Fetch the RAGme instance
	ragme := &ragmev1.RAGme{}
	err := r.Get(ctx, req.NamespacedName, ragme)
	if err != nil {
		if errors.IsNotFound(err) {
			logger.Info("RAGme resource not found. Ignoring since object must be deleted")
			return ctrl.Result{}, nil
		}
		logger.Error(err, "Failed to get RAGme")
		return ctrl.Result{}, err
	}

	logger.Info("Reconciling RAGme", "name", ragme.Name, "namespace", ragme.Namespace)

	// Set default values
	r.setDefaults(ragme)

	// Update status to indicate reconciliation has started
	ragme.Status.Phase = "Reconciling"
	if err := r.Status().Update(ctx, ragme); err != nil {
		logger.Error(err, "Failed to update RAGme status")
		return ctrl.Result{}, err
	}

	// Reconcile storage components
	if err := r.reconcileStorage(ctx, ragme); err != nil {
		logger.Error(err, "Failed to reconcile storage")
		return ctrl.Result{RequeueAfter: time.Minute}, err
	}

	// Reconcile MinIO
	if err := r.reconcileMinIO(ctx, ragme); err != nil {
		logger.Error(err, "Failed to reconcile MinIO")
		return ctrl.Result{RequeueAfter: time.Minute}, err
	}

	// Reconcile vector database
	if err := r.reconcileVectorDB(ctx, ragme); err != nil {
		logger.Error(err, "Failed to reconcile vector database")
		return ctrl.Result{RequeueAfter: time.Minute}, err
	}

	// Reconcile RAGme services
	if err := r.reconcileRAGmeServices(ctx, ragme); err != nil {
		logger.Error(err, "Failed to reconcile RAGme services")
		return ctrl.Result{RequeueAfter: time.Minute}, err
	}

	// Update final status
	ragme.Status.Phase = "Ready"
	if err := r.Status().Update(ctx, ragme); err != nil {
		logger.Error(err, "Failed to update final RAGme status")
		return ctrl.Result{}, err
	}

	logger.Info("Successfully reconciled RAGme", "name", ragme.Name)
	return ctrl.Result{RequeueAfter: time.Minute * 5}, nil
}

// setDefaults sets default values for RAGme spec
func (r *RAGmeReconciler) setDefaults(ragme *ragmev1.RAGme) {
	if ragme.Spec.Version == "" {
		ragme.Spec.Version = "latest"
	}

	if ragme.Spec.Images.Tag == "" {
		ragme.Spec.Images.Tag = "latest"
	}

	if ragme.Spec.Images.PullPolicy == "" {
		ragme.Spec.Images.PullPolicy = "IfNotPresent"
	}

	if ragme.Spec.Replicas.API == 0 {
		ragme.Spec.Replicas.API = 2
	}

	if ragme.Spec.Replicas.MCP == 0 {
		ragme.Spec.Replicas.MCP = 2
	}

	if ragme.Spec.Replicas.Agent == 0 {
		ragme.Spec.Replicas.Agent = 1
	}

	if ragme.Spec.Replicas.Frontend == 0 {
		ragme.Spec.Replicas.Frontend = 2
	}

	if ragme.Spec.Storage.MinIO.StorageSize == "" {
		ragme.Spec.Storage.MinIO.StorageSize = "10Gi"
	}

	if ragme.Spec.Storage.SharedVolume.Size == "" {
		ragme.Spec.Storage.SharedVolume.Size = "5Gi"
	}

	if ragme.Spec.VectorDB.Type == "" {
		ragme.Spec.VectorDB.Type = "milvus"
	}

	// Set default authentication values
	if ragme.Spec.Authentication.Session.SecretKey == "" {
		ragme.Spec.Authentication.Session.SecretKey = "ragme-shared-session-secret-key-2025"
	}
	if ragme.Spec.Authentication.Session.MaxAgeSeconds == 0 {
		ragme.Spec.Authentication.Session.MaxAgeSeconds = 86400 // 24 hours
	}
	if ragme.Spec.Authentication.Session.SameSite == "" {
		ragme.Spec.Authentication.Session.SameSite = "lax"
	}
}

// reconcileStorage reconciles shared storage components
func (r *RAGmeReconciler) reconcileStorage(ctx context.Context, ragme *ragmev1.RAGme) error {
	// Create shared PVC for watch directory
	pvc := &corev1.PersistentVolumeClaim{
		ObjectMeta: metav1.ObjectMeta{
			Name:      fmt.Sprintf("%s-shared-pvc", ragme.Name),
			Namespace: ragme.Namespace,
		},
		Spec: corev1.PersistentVolumeClaimSpec{
			AccessModes: []corev1.PersistentVolumeAccessMode{
				corev1.ReadWriteMany,
			},
			Resources: corev1.ResourceRequirements{
				Requests: corev1.ResourceList{
					corev1.ResourceStorage: resource.MustParse(ragme.Spec.Storage.SharedVolume.Size),
				},
			},
		},
	}

	if ragme.Spec.Storage.SharedVolume.StorageClass != "" {
		pvc.Spec.StorageClassName = &ragme.Spec.Storage.SharedVolume.StorageClass
	}

	if err := ctrl.SetControllerReference(ragme, pvc, r.Scheme); err != nil {
		return err
	}

	found := &corev1.PersistentVolumeClaim{}
	err := r.Get(ctx, types.NamespacedName{Name: pvc.Name, Namespace: pvc.Namespace}, found)
	if err != nil && errors.IsNotFound(err) {
		if err := r.Create(ctx, pvc); err != nil {
			return err
		}
	}

	return nil
}

// reconcileMinIO reconciles MinIO deployment and service
func (r *RAGmeReconciler) reconcileMinIO(ctx context.Context, ragme *ragmev1.RAGme) error {
	if !ragme.Spec.Storage.MinIO.Enabled {
		return nil
	}

	// Create MinIO PVC
	pvc := &corev1.PersistentVolumeClaim{
		ObjectMeta: metav1.ObjectMeta{
			Name:      fmt.Sprintf("%s-minio-pvc", ragme.Name),
			Namespace: ragme.Namespace,
		},
		Spec: corev1.PersistentVolumeClaimSpec{
			AccessModes: []corev1.PersistentVolumeAccessMode{
				corev1.ReadWriteOnce,
			},
			Resources: corev1.ResourceRequirements{
				Requests: corev1.ResourceList{
					corev1.ResourceStorage: resource.MustParse(ragme.Spec.Storage.MinIO.StorageSize),
				},
			},
		},
	}

	if err := ctrl.SetControllerReference(ragme, pvc, r.Scheme); err != nil {
		return err
	}

	found := &corev1.PersistentVolumeClaim{}
	err := r.Get(ctx, types.NamespacedName{Name: pvc.Name, Namespace: pvc.Namespace}, found)
	if err != nil && errors.IsNotFound(err) {
		if err := r.Create(ctx, pvc); err != nil {
			return err
		}
	}

	// Create MinIO deployment
	deployment := r.createMinIODeployment(ragme)
	if err := ctrl.SetControllerReference(ragme, deployment, r.Scheme); err != nil {
		return err
	}

	foundDeployment := &appsv1.Deployment{}
	err = r.Get(ctx, types.NamespacedName{Name: deployment.Name, Namespace: deployment.Namespace}, foundDeployment)
	if err != nil && errors.IsNotFound(err) {
		if err := r.Create(ctx, deployment); err != nil {
			return err
		}
	} else if err == nil {
		// Update existing deployment
		foundDeployment.Spec = deployment.Spec
		if err := r.Update(ctx, foundDeployment); err != nil {
			return err
		}
	}

	// Create MinIO service
	service := r.createMinIOService(ragme)
	if err := ctrl.SetControllerReference(ragme, service, r.Scheme); err != nil {
		return err
	}

	foundService := &corev1.Service{}
	err = r.Get(ctx, types.NamespacedName{Name: service.Name, Namespace: service.Namespace}, foundService)
	if err != nil && errors.IsNotFound(err) {
		if err := r.Create(ctx, service); err != nil {
			return err
		}
	}

	return nil
}

// reconcileVectorDB reconciles vector database deployment
func (r *RAGmeReconciler) reconcileVectorDB(ctx context.Context, ragme *ragmev1.RAGme) error {
	if ragme.Spec.VectorDB.Type == "weaviate" && ragme.Spec.VectorDB.Weaviate.Enabled {
		return r.reconcileWeaviate(ctx, ragme)
	}
	return nil
}

// reconcileWeaviate reconciles Weaviate deployment
func (r *RAGmeReconciler) reconcileWeaviate(ctx context.Context, ragme *ragmev1.RAGme) error {
	// Create Weaviate PVC
	pvc := &corev1.PersistentVolumeClaim{
		ObjectMeta: metav1.ObjectMeta{
			Name:      fmt.Sprintf("%s-weaviate-pvc", ragme.Name),
			Namespace: ragme.Namespace,
		},
		Spec: corev1.PersistentVolumeClaimSpec{
			AccessModes: []corev1.PersistentVolumeAccessMode{
				corev1.ReadWriteOnce,
			},
			Resources: corev1.ResourceRequirements{
				Requests: corev1.ResourceList{
					corev1.ResourceStorage: resource.MustParse(ragme.Spec.VectorDB.Weaviate.StorageSize),
				},
			},
		},
	}

	if err := ctrl.SetControllerReference(ragme, pvc, r.Scheme); err != nil {
		return err
	}

	found := &corev1.PersistentVolumeClaim{}
	err := r.Get(ctx, types.NamespacedName{Name: pvc.Name, Namespace: pvc.Namespace}, found)
	if err != nil && errors.IsNotFound(err) {
		if err := r.Create(ctx, pvc); err != nil {
			return err
		}
	}

	// Create Weaviate deployment and service similar to MinIO
	deployment := r.createWeaviateDeployment(ragme)
	if err := ctrl.SetControllerReference(ragme, deployment, r.Scheme); err != nil {
		return err
	}

	foundDeployment := &appsv1.Deployment{}
	err = r.Get(ctx, types.NamespacedName{Name: deployment.Name, Namespace: deployment.Namespace}, foundDeployment)
	if err != nil && errors.IsNotFound(err) {
		if err := r.Create(ctx, deployment); err != nil {
			return err
		}
	} else if err == nil {
		foundDeployment.Spec = deployment.Spec
		if err := r.Update(ctx, foundDeployment); err != nil {
			return err
		}
	}

	// Create Weaviate service
	service := r.createWeaviateService(ragme)
	if err := ctrl.SetControllerReference(ragme, service, r.Scheme); err != nil {
		return err
	}

	foundService := &corev1.Service{}
	err = r.Get(ctx, types.NamespacedName{Name: service.Name, Namespace: service.Namespace}, foundService)
	if err != nil && errors.IsNotFound(err) {
		if err := r.Create(ctx, service); err != nil {
			return err
		}
	}

	return nil
}

// reconcileRAGmeServices reconciles the main RAGme application services
func (r *RAGmeReconciler) reconcileRAGmeServices(ctx context.Context, ragme *ragmev1.RAGme) error {
	services := []string{"api", "mcp", "agent", "frontend"}

	for _, serviceName := range services {
		if err := r.reconcileRAGmeService(ctx, ragme, serviceName); err != nil {
			return fmt.Errorf("failed to reconcile %s service: %w", serviceName, err)
		}
	}

	return nil
}

// reconcileRAGmeService reconciles a single RAGme service
func (r *RAGmeReconciler) reconcileRAGmeService(ctx context.Context, ragme *ragmev1.RAGme, serviceName string) error {
	deployment := r.createRAGmeServiceDeployment(ragme, serviceName)
	if err := ctrl.SetControllerReference(ragme, deployment, r.Scheme); err != nil {
		return err
	}

	foundDeployment := &appsv1.Deployment{}
	err := r.Get(ctx, types.NamespacedName{Name: deployment.Name, Namespace: deployment.Namespace}, foundDeployment)
	if err != nil && errors.IsNotFound(err) {
		if err := r.Create(ctx, deployment); err != nil {
			return err
		}
	} else if err == nil {
		foundDeployment.Spec = deployment.Spec
		if err := r.Update(ctx, foundDeployment); err != nil {
			return err
		}
	}

	// Create service (except for agent which doesn't need a service)
	if serviceName != "agent" {
		service := r.createRAGmeService(ragme, serviceName)
		if err := ctrl.SetControllerReference(ragme, service, r.Scheme); err != nil {
			return err
		}

		foundService := &corev1.Service{}
		err = r.Get(ctx, types.NamespacedName{Name: service.Name, Namespace: service.Namespace}, foundService)
		if err != nil && errors.IsNotFound(err) {
			if err := r.Create(ctx, service); err != nil {
				return err
			}
		}
	}

	return nil
}

// Helper functions to create Kubernetes resources

func (r *RAGmeReconciler) createMinIODeployment(ragme *ragmev1.RAGme) *appsv1.Deployment {
	labels := map[string]string{
		"app":       "ragme",
		"component": "minio",
		"instance":  ragme.Name,
	}

	deployment := &appsv1.Deployment{
		ObjectMeta: metav1.ObjectMeta{
			Name:      fmt.Sprintf("%s-minio", ragme.Name),
			Namespace: ragme.Namespace,
			Labels:    labels,
		},
		Spec: appsv1.DeploymentSpec{
			Replicas: &[]int32{1}[0],
			Selector: &metav1.LabelSelector{
				MatchLabels: labels,
			},
			Template: corev1.PodTemplateSpec{
				ObjectMeta: metav1.ObjectMeta{
					Labels: labels,
				},
				Spec: corev1.PodSpec{
					Containers: []corev1.Container{
						{
							Name:  "minio",
							Image: "minio/minio:latest",
							Args:  []string{"server", "/data", "--console-address", ":9001"},
							Ports: []corev1.ContainerPort{
								{ContainerPort: 9000, Name: "api"},
								{ContainerPort: 9001, Name: "console"},
							},
							Env: []corev1.EnvVar{
								{Name: "MINIO_ROOT_USER", Value: ragme.Spec.Storage.MinIO.AccessKey},
								{Name: "MINIO_ROOT_PASSWORD", Value: ragme.Spec.Storage.MinIO.SecretKey},
							},
							VolumeMounts: []corev1.VolumeMount{
								{Name: "minio-data", MountPath: "/data"},
							},
							LivenessProbe: &corev1.Probe{
								ProbeHandler: corev1.ProbeHandler{
									HTTPGet: &corev1.HTTPGetAction{
										Path: "/minio/health/live",
										Port: intstr.FromInt(9000),
									},
								},
								InitialDelaySeconds: 30,
								PeriodSeconds:       20,
							},
							ReadinessProbe: &corev1.Probe{
								ProbeHandler: corev1.ProbeHandler{
									HTTPGet: &corev1.HTTPGetAction{
										Path: "/minio/health/ready",
										Port: intstr.FromInt(9000),
									},
								},
								InitialDelaySeconds: 5,
								PeriodSeconds:       5,
							},
						},
					},
					Volumes: []corev1.Volume{
						{
							Name: "minio-data",
							VolumeSource: corev1.VolumeSource{
								PersistentVolumeClaim: &corev1.PersistentVolumeClaimVolumeSource{
									ClaimName: fmt.Sprintf("%s-minio-pvc", ragme.Name),
								},
							},
						},
					},
				},
			},
		},
	}

	return deployment
}

func (r *RAGmeReconciler) createMinIOService(ragme *ragmev1.RAGme) *corev1.Service {
	labels := map[string]string{
		"app":       "ragme",
		"component": "minio",
		"instance":  ragme.Name,
	}

	return &corev1.Service{
		ObjectMeta: metav1.ObjectMeta{
			Name:      fmt.Sprintf("%s-minio", ragme.Name),
			Namespace: ragme.Namespace,
			Labels:    labels,
		},
		Spec: corev1.ServiceSpec{
			Selector: labels,
			Ports: []corev1.ServicePort{
				{Name: "api", Port: 9000, TargetPort: intstr.FromInt(9000)},
				{Name: "console", Port: 9001, TargetPort: intstr.FromInt(9001)},
			},
			Type: corev1.ServiceTypeClusterIP,
		},
	}
}

func (r *RAGmeReconciler) createWeaviateDeployment(ragme *ragmev1.RAGme) *appsv1.Deployment {
	labels := map[string]string{
		"app":       "ragme",
		"component": "weaviate",
		"instance":  ragme.Name,
	}

	deployment := &appsv1.Deployment{
		ObjectMeta: metav1.ObjectMeta{
			Name:      fmt.Sprintf("%s-weaviate", ragme.Name),
			Namespace: ragme.Namespace,
			Labels:    labels,
		},
		Spec: appsv1.DeploymentSpec{
			Replicas: &[]int32{1}[0],
			Selector: &metav1.LabelSelector{
				MatchLabels: labels,
			},
			Template: corev1.PodTemplateSpec{
				ObjectMeta: metav1.ObjectMeta{
					Labels: labels,
				},
				Spec: corev1.PodSpec{
					Containers: []corev1.Container{
						{
							Name:  "weaviate",
							Image: "cr.weaviate.io/semitechnologies/weaviate:1.25.0",
							Ports: []corev1.ContainerPort{
								{ContainerPort: 8080, Name: "http"},
							},
							Env: []corev1.EnvVar{
								{Name: "QUERY_DEFAULTS_LIMIT", Value: "25"},
								{Name: "AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED", Value: "true"},
								{Name: "PERSISTENCE_DATA_PATH", Value: "/var/lib/weaviate"},
								{Name: "DEFAULT_VECTORIZER_MODULE", Value: "none"},
								{Name: "ENABLE_MODULES", Value: "text2vec-openai,generative-openai"},
								{Name: "CLUSTER_HOSTNAME", Value: "node1"},
							},
							VolumeMounts: []corev1.VolumeMount{
								{Name: "weaviate-data", MountPath: "/var/lib/weaviate"},
							},
						},
					},
					Volumes: []corev1.Volume{
						{
							Name: "weaviate-data",
							VolumeSource: corev1.VolumeSource{
								PersistentVolumeClaim: &corev1.PersistentVolumeClaimVolumeSource{
									ClaimName: fmt.Sprintf("%s-weaviate-pvc", ragme.Name),
								},
							},
						},
					},
				},
			},
		},
	}

	return deployment
}

func (r *RAGmeReconciler) createWeaviateService(ragme *ragmev1.RAGme) *corev1.Service {
	labels := map[string]string{
		"app":       "ragme",
		"component": "weaviate",
		"instance":  ragme.Name,
	}

	return &corev1.Service{
		ObjectMeta: metav1.ObjectMeta{
			Name:      fmt.Sprintf("%s-weaviate", ragme.Name),
			Namespace: ragme.Namespace,
			Labels:    labels,
		},
		Spec: corev1.ServiceSpec{
			Selector: labels,
			Ports: []corev1.ServicePort{
				{Name: "http", Port: 8080, TargetPort: intstr.FromInt(8080)},
			},
			Type: corev1.ServiceTypeClusterIP,
		},
	}
}

func (r *RAGmeReconciler) createRAGmeServiceDeployment(ragme *ragmev1.RAGme, serviceName string) *appsv1.Deployment {
	labels := map[string]string{
		"app":       "ragme",
		"component": serviceName,
		"instance":  ragme.Name,
	}

	var replicas int32
	var port int32
	var image string

	switch serviceName {
	case "api":
		replicas = ragme.Spec.Replicas.API
		port = 8021
		image = fmt.Sprintf("%s/ragme-api:%s", ragme.Spec.Images.Registry, ragme.Spec.Images.Tag)
	case "mcp":
		replicas = ragme.Spec.Replicas.MCP
		port = 8022
		image = fmt.Sprintf("%s/ragme-mcp:%s", ragme.Spec.Images.Registry, ragme.Spec.Images.Tag)
	case "agent":
		replicas = ragme.Spec.Replicas.Agent
		port = 0 // No port for agent
		image = fmt.Sprintf("%s/ragme-agent:%s", ragme.Spec.Images.Registry, ragme.Spec.Images.Tag)
	case "frontend":
		replicas = ragme.Spec.Replicas.Frontend
		port = 8020
		image = fmt.Sprintf("%s/ragme-frontend:%s", ragme.Spec.Images.Registry, ragme.Spec.Images.Tag)
	}

	envVars := []corev1.EnvVar{
		{Name: "RAGME_API_URL", Value: fmt.Sprintf("http://%s-api:8021", ragme.Name)},
		{Name: "RAGME_MCP_URL", Value: fmt.Sprintf("http://%s-mcp:8022", ragme.Name)},
	}

	// Add OAuth environment variables if authentication is configured
	if ragme.Spec.Authentication.OAuth.Google.Enabled {
		envVars = append(envVars, []corev1.EnvVar{
			{Name: "GOOGLE_OAUTH_CLIENT_ID", Value: ragme.Spec.Authentication.OAuth.Google.ClientID},
			{Name: "GOOGLE_OAUTH_CLIENT_SECRET", Value: ragme.Spec.Authentication.OAuth.Google.ClientSecret},
			{Name: "GOOGLE_OAUTH_REDIRECT_URI", Value: ragme.Spec.Authentication.OAuth.Google.RedirectURI},
		}...)
	}

	if ragme.Spec.Authentication.OAuth.GitHub.Enabled {
		envVars = append(envVars, []corev1.EnvVar{
			{Name: "GITHUB_OAUTH_CLIENT_ID", Value: ragme.Spec.Authentication.OAuth.GitHub.ClientID},
			{Name: "GITHUB_OAUTH_CLIENT_SECRET", Value: ragme.Spec.Authentication.OAuth.GitHub.ClientSecret},
			{Name: "GITHUB_OAUTH_REDIRECT_URI", Value: ragme.Spec.Authentication.OAuth.GitHub.RedirectURI},
		}...)
	}

	if ragme.Spec.Authentication.OAuth.Apple.Enabled {
		envVars = append(envVars, []corev1.EnvVar{
			{Name: "APPLE_OAUTH_CLIENT_ID", Value: ragme.Spec.Authentication.OAuth.Apple.ClientID},
			{Name: "APPLE_OAUTH_CLIENT_SECRET", Value: ragme.Spec.Authentication.OAuth.Apple.ClientSecret},
			{Name: "APPLE_OAUTH_REDIRECT_URI", Value: ragme.Spec.Authentication.OAuth.Apple.RedirectURI},
		}...)
	}

	// Add session configuration
	if ragme.Spec.Authentication.Session.SecretKey != "" {
		envVars = append(envVars, corev1.EnvVar{
			Name: "SESSION_SECRET_KEY", Value: ragme.Spec.Authentication.Session.SecretKey,
		})
	}

	container := corev1.Container{
		Name:            serviceName,
		Image:           image,
		ImagePullPolicy: corev1.PullPolicy(ragme.Spec.Images.PullPolicy),
		Env:             envVars,
		VolumeMounts: []corev1.VolumeMount{
			{Name: "logs", MountPath: "/app/logs"},
			{Name: "watch-directory", MountPath: "/app/watch_directory"},
		},
	}

	if port > 0 {
		container.Ports = []corev1.ContainerPort{
			{ContainerPort: port, Name: "http"},
		}

		// Add health checks for services with HTTP endpoints
		container.LivenessProbe = &corev1.Probe{
			ProbeHandler: corev1.ProbeHandler{
				HTTPGet: &corev1.HTTPGetAction{
					Path: "/health",
					Port: intstr.FromInt(int(port)),
				},
			},
			InitialDelaySeconds: 30,
			PeriodSeconds:       20,
		}

		container.ReadinessProbe = &corev1.Probe{
			ProbeHandler: corev1.ProbeHandler{
				HTTPGet: &corev1.HTTPGetAction{
					Path: "/ready",
					Port: intstr.FromInt(int(port)),
				},
			},
			InitialDelaySeconds: 5,
			PeriodSeconds:       5,
		}
	}

	deployment := &appsv1.Deployment{
		ObjectMeta: metav1.ObjectMeta{
			Name:      fmt.Sprintf("%s-%s", ragme.Name, serviceName),
			Namespace: ragme.Namespace,
			Labels:    labels,
		},
		Spec: appsv1.DeploymentSpec{
			Replicas: &replicas,
			Selector: &metav1.LabelSelector{
				MatchLabels: labels,
			},
			Template: corev1.PodTemplateSpec{
				ObjectMeta: metav1.ObjectMeta{
					Labels: labels,
				},
				Spec: corev1.PodSpec{
					Containers: []corev1.Container{container},
					Volumes: []corev1.Volume{
						{
							Name: "logs",
							VolumeSource: corev1.VolumeSource{
								EmptyDir: &corev1.EmptyDirVolumeSource{},
							},
						},
						{
							Name: "watch-directory",
							VolumeSource: corev1.VolumeSource{
								PersistentVolumeClaim: &corev1.PersistentVolumeClaimVolumeSource{
									ClaimName: fmt.Sprintf("%s-shared-pvc", ragme.Name),
								},
							},
						},
					},
				},
			},
		},
	}

	return deployment
}

func (r *RAGmeReconciler) createRAGmeService(ragme *ragmev1.RAGme, serviceName string) *corev1.Service {
	labels := map[string]string{
		"app":       "ragme",
		"component": serviceName,
		"instance":  ragme.Name,
	}

	var port int32
	switch serviceName {
	case "api":
		port = 8021
	case "mcp":
		port = 8022
	case "frontend":
		port = 8020
	}

	return &corev1.Service{
		ObjectMeta: metav1.ObjectMeta{
			Name:      fmt.Sprintf("%s-%s", ragme.Name, serviceName),
			Namespace: ragme.Namespace,
			Labels:    labels,
		},
		Spec: corev1.ServiceSpec{
			Selector: labels,
			Ports: []corev1.ServicePort{
				{Name: "http", Port: port, TargetPort: intstr.FromInt(int(port))},
			},
			Type: corev1.ServiceTypeClusterIP,
		},
	}
}

// SetupWithManager sets up the controller with the Manager.
func (r *RAGmeReconciler) SetupWithManager(mgr ctrl.Manager) error {
	return ctrl.NewControllerManagedBy(mgr).
		For(&ragmev1.RAGme{}).
		Owns(&appsv1.Deployment{}).
		Owns(&corev1.Service{}).
		Owns(&corev1.ConfigMap{}).
		Owns(&corev1.PersistentVolumeClaim{}).
		Complete(r)
}
