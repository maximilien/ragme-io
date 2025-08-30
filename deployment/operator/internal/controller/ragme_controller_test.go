package controller

import (
	"context"
	"testing"
	"time"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
	appsv1 "k8s.io/api/apps/v1"
	corev1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/api/resource"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/types"
	"sigs.k8s.io/controller-runtime/pkg/client"
	"sigs.k8s.io/controller-runtime/pkg/envtest"
	logf "sigs.k8s.io/controller-runtime/pkg/log"
	"sigs.k8s.io/controller-runtime/pkg/log/zap"
	"sigs.k8s.io/controller-runtime/pkg/manager"

	ragmev1 "github.com/maximilien/ragme-io/operator/api/v1"
)

var (
	k8sClient client.Client
	testEnv   *envtest.Environment
	ctx       context.Context
	cancel    context.CancelFunc
)

func TestRAGmeController(t *testing.T) {
	RegisterFailHandler(Fail)
	RunSpecs(t, "RAGme Controller Suite")
}

var _ = BeforeSuite(func() {
	logf.SetLogger(zap.New(zap.WriteTo(GinkgoWriter), zap.UseDevMode(true)))

	ctx, cancel = context.WithCancel(context.TODO())

	By("bootstrapping test environment")
	testEnv = &envtest.Environment{
		CRDDirectoryPaths:     []string{"../../../config/crd"},
		ErrorIfCRDPathMissing: true,
	}

	cfg, err := testEnv.Start()
	Expect(err).NotTo(HaveOccurred())
	Expect(cfg).NotTo(BeNil())

	err = ragmev1.AddToScheme(scheme)
	Expect(err).NotTo(HaveOccurred())

	k8sClient, err = client.New(cfg, client.Options{Scheme: scheme})
	Expect(err).NotTo(HaveOccurred())
	Expect(k8sClient).NotTo(BeNil())

	k8sManager, err := manager.New(cfg, manager.Options{
		Scheme: scheme,
	})
	Expect(err).ToNot(HaveOccurred())

	err = (&RAGmeReconciler{
		Client: k8sManager.GetClient(),
		Scheme: k8sManager.GetScheme(),
	}).SetupWithManager(k8sManager)
	Expect(err).ToNot(HaveOccurred())

	go func() {
		defer GinkgoRecover()
		err = k8sManager.Start(ctx)
		Expect(err).ToNot(HaveOccurred(), "failed to run manager")
	}()
})

var _ = AfterSuite(func() {
	cancel()
	By("tearing down the test environment")
	err := testEnv.Stop()
	Expect(err).NotTo(HaveOccurred())
})

var _ = Describe("RAGme Controller", func() {
	Context("When creating a RAGme resource", func() {
		It("Should create the required Kubernetes resources", func() {
			By("Creating a RAGme instance")
			ragme := &ragmev1.RAGme{
				ObjectMeta: metav1.ObjectMeta{
					Name:      "test-ragme",
					Namespace: "default",
				},
				Spec: ragmev1.RAGmeSpec{
					Version: "latest",
					Images: ragmev1.RAGmeImages{
						Registry:   "localhost:5001",
						Repository: "ragme",
						Tag:        "latest",
						PullPolicy: "IfNotPresent",
					},
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
							AccessKey:   "minioadmin",
							SecretKey:   "minioadmin",
						},
						SharedVolume: ragmev1.RAGmeSharedVolume{
							Size: "5Gi",
						},
					},
					VectorDB: ragmev1.RAGmeVectorDB{
						Type: "weaviate",
						Weaviate: ragmev1.RAGmeWeaviateDB{
							Enabled:     true,
							StorageSize: "2Gi",
						},
					},
				},
			}

			Expect(k8sClient.Create(ctx, ragme)).Should(Succeed())

			ragmeKey := types.NamespacedName{Name: "test-ragme", Namespace: "default"}
			createdRAGme := &ragmev1.RAGme{}

			// Verify the RAGme resource was created
			Eventually(func() bool {
				err := k8sClient.Get(ctx, ragmeKey, createdRAGme)
				return err == nil
			}, time.Minute, time.Second).Should(BeTrue())

			By("Checking that persistent volume claims are created")
			Eventually(func() bool {
				sharedPVC := &corev1.PersistentVolumeClaim{}
				err := k8sClient.Get(ctx, types.NamespacedName{
					Name:      "test-ragme-shared-pvc",
					Namespace: "default",
				}, sharedPVC)
				return err == nil
			}, time.Minute, time.Second).Should(BeTrue())

			Eventually(func() bool {
				minioPVC := &corev1.PersistentVolumeClaim{}
				err := k8sClient.Get(ctx, types.NamespacedName{
					Name:      "test-ragme-minio-pvc",
					Namespace: "default",
				}, minioPVC)
				return err == nil
			}, time.Minute, time.Second).Should(BeTrue())

			By("Checking that deployments are created")
			services := []string{"minio", "weaviate", "api", "mcp", "agent", "frontend"}
			
			for _, service := range services {
				Eventually(func() bool {
					deployment := &appsv1.Deployment{}
					err := k8sClient.Get(ctx, types.NamespacedName{
						Name:      "test-ragme-" + service,
						Namespace: "default",
					}, deployment)
					return err == nil
				}, time.Minute, time.Second).Should(BeTrue(), "Deployment for service %s should be created", service)
			}

			By("Checking that services are created")
			servicesWithEndpoints := []string{"minio", "weaviate", "api", "mcp", "frontend"}
			
			for _, service := range servicesWithEndpoints {
				Eventually(func() bool {
					svc := &corev1.Service{}
					err := k8sClient.Get(ctx, types.NamespacedName{
						Name:      "test-ragme-" + service,
						Namespace: "default",
					}, svc)
					return err == nil
				}, time.Minute, time.Second).Should(BeTrue(), "Service for %s should be created", service)
			}

			By("Verifying resource specifications")
			deployment := &appsv1.Deployment{}
			err := k8sClient.Get(ctx, types.NamespacedName{
				Name:      "test-ragme-api",
				Namespace: "default",
			}, deployment)
			Expect(err).NotTo(HaveOccurred())
			Expect(*deployment.Spec.Replicas).To(Equal(int32(2)))

			By("Cleaning up test resources")
			Expect(k8sClient.Delete(ctx, ragme)).Should(Succeed())
		})
	})

	Context("When updating a RAGme resource", func() {
		It("Should update the deployments accordingly", func() {
			By("Creating a RAGme instance")
			ragme := &ragmev1.RAGme{
				ObjectMeta: metav1.ObjectMeta{
					Name:      "test-ragme-update",
					Namespace: "default",
				},
				Spec: ragmev1.RAGmeSpec{
					Replicas: ragmev1.RAGmeReplicas{
						API: 1,
					},
					Storage: ragmev1.RAGmeStorage{
						MinIO: ragmev1.RAGmeMinIOStorage{
							Enabled: true,
						},
					},
				},
			}

			Expect(k8sClient.Create(ctx, ragme)).Should(Succeed())

			ragmeKey := types.NamespacedName{Name: "test-ragme-update", Namespace: "default"}

			By("Updating replica count")
			Eventually(func() error {
				createdRAGme := &ragmev1.RAGme{}
				err := k8sClient.Get(ctx, ragmeKey, createdRAGme)
				if err != nil {
					return err
				}
				createdRAGme.Spec.Replicas.API = 3
				return k8sClient.Update(ctx, createdRAGme)
			}, time.Minute, time.Second).Should(Succeed())

			By("Verifying deployment was updated")
			Eventually(func() int32 {
				deployment := &appsv1.Deployment{}
				err := k8sClient.Get(ctx, types.NamespacedName{
					Name:      "test-ragme-update-api",
					Namespace: "default",
				}, deployment)
				if err != nil {
					return 0
				}
				return *deployment.Spec.Replicas
			}, time.Minute, time.Second).Should(Equal(int32(3)))

			By("Cleaning up test resources")
			Expect(k8sClient.Delete(ctx, ragme)).Should(Succeed())
		})
	})
})