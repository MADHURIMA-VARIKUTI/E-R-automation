#  EMBEDDER & RERANKER

## Introduction

NVIDIA NIM (NVIDIA Inference Microservices) provides high-performance AI inference capabilities for text embedding and reranking tasks through containerized microservices. This documentation covers performance benchmarking methodologies and results for two key NIM services:

### Text Embedding NIM
The **NV-EmbedQA-E5-v5** model provides state-of-the-art text embedding capabilities, converting textual input into high-dimensional vector representations. This service supports both:
- **Query embeddings**: Short text queries (typically ~20 tokens) for search and retrieval tasks
- **Passage embeddings**: Longer text passages (300-512 tokens) for document indexing and semantic search

### Text Reranking NIM  
The **Llama-3.2-NV-RerankQA-1B-v2** model enhances search relevance by reordering candidate documents based on their semantic similarity to a given query. This service processes query-passage pairs to provide refined ranking scores for improved retrieval accuracy.

## Performance Benchmarking Overview

Both NIM services can be benchmarked using the **genai-perf** tool, which comes pre-installed in the Triton Server SDK container. This tool enables comprehensive performance evaluation under simulated production loads by measuring:

- **Latency metrics**: P50, P90, P95, and P99 percentiles
- **Throughput**: Requests per second (infer/sec)
- **Concurrency handling**: Performance under various concurrent load levels
- **Batch processing**: Efficiency with different batch sizes

## Kubernetes Deployment Process

### Prerequisites

Before deploying NVIDIA NIM services on Kubernetes, ensure you have the following components installed and configured:

### HELM Installation

Install Helm 3.x using the official installation script:

```bash
# Download and install Helm
curl -fsSL -o get_helm.sh https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3
chmod 700 get_helm.sh
./get_helm.sh

# Add Helm to PATH
echo 'export PATH=$PATH:/usr/local/bin' >> ~/.bashrc
source ~/.bashrc

# Verify Helm installation
helm version
# Expected output: version.BuildInfo{Version:"v3.18.4", GitCommit:"d80839cf37d860c8aa9a0503fe463278f26cd5e2", GitTreeState:"clean", GoVersion:"go1.24.4"}
```

### Environment Setup

Configure your NGC (NVIDIA GPU Cloud) API key for accessing NVIDIA's container registry:

```bash
# Set your NGC API Key (obtain from NGC User Guide - NVIDIA Docs)
export NGC_API_KEY="<YOUR_NGC_API_KEY>"
```

**Note**: To obtain your NGC API Key, follow the [NGC User Guide - NVIDIA Docs](https://docs.nvidia.com/ngc/ngc-user-guide/index.html).


### Namespace Creation

Create dedicated Kubernetes namespaces for your NIM deployments:

```bash
# Create namespace for embedding service
kubectl create namespace <embedding-namespace>

```

```bash
# Create namespace for genai-perf 
kubectl create namespace <genai-namespace>

```

```bash
# Create namespace for reranker service
kubectl create namespace <reranker-namespace>

```


### Secrets Creation [ do for both embedding-namespace and reranker-namespace ]

Configure the necessary secrets for NGC registry access and API authentication:

```bash
# Apply image pull secret for NGC registry access
kubectl apply -n <embedding-namespace> -f imagepull.yaml

# Create NGC API key secret
kubectl create -n <embedding-namespace> secret generic ngc-api \
  --from-literal=NGC_API_KEY=${NGC_API_KEY}

# Verify secrets creation
kubectl get secrets -n <embedding-namespace>
```
**Expected output:**
```
NAME                          TYPE                             DATA   AGE
ngc-api                       Opaque                           1      13s
ngc-secret                    kubernetes.io/dockerconfigjson   1      25s
```
### Fetching the Helm Chart

Download the official NVIDIA NIM Helm charts from NGC:

```bash
# Fetch the text embedding NIM Helm chart
helm fetch https://helm.ngc.nvidia.com/nim/nvidia/charts/text-embedding-nim-1.5.0.tgz \
  --username='$oauthtoken' \
  --password=$NGC_API_KEY

# Extract the Helm chart
tar -xvf text-embedding-nim-1.5.0.tgz
```

Note: change version if required like 1.5.0/ 1.2.0
### Configuration Considerations

### values.yaml Modifications

Before deploying, you may need to modify the `values.yaml` file to customize your deployment:

#### Model Selection

To select the appropriate model image and tag, you have two options:

**Option 1: Internal Registry (ezfab)**
```bash
# Login to ezfab and navigate to the registry path
# Go to: /opt/ezfab/registry/docker/registry/v2/repositories/ezmeral-common/nvcr.io/nim/nvidia/
# select any model like llama-3.1-8b-instruct-pb24h2/_manifests/tagsSelect the desired tag from available versions
```

**Option 2: NGC Catalog**
- Visit the [NGC Catalog](https://catalog.ngc.nvidia.com/orgs/nim/teams/nvidia/helm-charts/)
- Browse available models and their versions
- Select the appropriate model for your use case

#### Configuration Example

```yaml
# Image configuration
image:
  repository: nvcr.io/nim/nvidia/nv-embedqa-e5-v5  # The container (nv-embedqa-e5) to deploy
  pullPolicy: IfNotPresent
  tag: "1.5.0"                                     # The version of that container

# Image pull secrets for NGC registry access
imagePullSecrets:
  - name: ngc-secret    # change this to whatever your image pull secret should be

# Environment variables with proxy configuration
envVars:
  http_proxy: <add>
  https_proxy: <add>
  no_proxy: <add>

# Storage options (based on environment and cluster in use)
persistence:
  enabled: true

# Resource requirements
resources:
  limits:
    nvidia.com/gpu: 1    # change these based on your requirements
    memory: 32Gi
    cpu: 8
  requests:
    nvidia.com/gpu: 1
    memory: 16Gi
    cpu: 4

```

#### Key Configuration Parameters

- **image.repository**: Specifies the container image to deploy (e.g., nvcr.io/nim/nvidia/nv-embedqa-e5-v5, nvcr.io/nim/nvidia/llama-3.2-nv-rerankqa-1b-v2)
- **image.tag**: Defines the version of the container (e.g., 1.5.0, 1.3.0)
- **Storage options**: Configure based on your environment and cluster requirements
- **resources**: Adjust when a model requires more than the default of one GPU
- **env**: Array of environment variables for advanced container configuration


### Helm Deployment

After modifying the `values.yaml` file, deploy the NIM service using Helm:

```bash
# Navigate outside of the extracted chart directory
cd ..

# Install the Helm chart with your custom configuration
helm install <any_name> text-embedding-nim/ -n <embedding-namespace>
```

**Parameters:**
- `<any_name>`: Choose any name for your Helm release (e.g., my-embedding-nim, embedder-service)
- `<extracted_folder>`: The name of the extracted chart directory (e.g., text-embedding-nim / text-reranking-nim)
- `<namespace>`: The namespace where you want to deploy (e.g., embedding-nim1 / reranking-nim1)


## Troubleshooting

### Common Deployment Issues

If you encounter errors during Helm deployment or service startup, try the following troubleshooting steps:

#### _config.tpl File Replacement

If there are configuration-related errors, you may need to replace the default `_config.tpl` file:

```bash
# Navigate to the extracted Helm chart directory
cd <extracted_folder>

# Replace the _config.tpl file in the nim-library templates
# Copy your custom _config.tpl file to the correct location:
cp /path/to/your/_config.tpl charts/nim-library/templates/_config.tpl

# Example:
cp _config.tpl charts/nim-library/templates/_config.tpl

# Verify the file has been replaced
ls -la charts/nim-library/templates/_config.tpl
```

**When to use this fix:**
- Deployment fails with configuration errors, Environment variables are not being set correctly
- Proxy settings are not being applied

**After replacing the file:**
```bash
# Re-install or upgrade the Helm chart
helm upgrade <release-name> <extracted_folder> -n <embedding-namespace>

# Or uninstall and reinstall:
helm uninstall <release-name> -n <embedding-namespace>
helm install <release-name> <extracted_folder> -n <embedding-namespace>
```

#### Other Common Issues

1. **Image Pull Errors**: Verify NGC secrets are correctly configured
2. **Resource Issues**: Check if sufficient GPU resources are available
3. **Network Issues**: Verify proxy settings and network policies
4. **Permission Issues**: Ensure proper RBAC permissions for the namespace

```bash
# Verify the deployment
kubectl get pods -n <embedding-namespace>
kubectl get services -n <embedding-namespace>

# Get all resources in the namespace
kubectl get all -n <embedding-namespace>
```

**Expected output after successful deployment:**
```bash
$ kubectl get all -n embedding-nim1
NAME                           READY   STATUS    RESTARTS   AGE
pod/app-text-embedding-nim-0   1/1     Running   0          112s

NAME                                 TYPE        CLUSTER-IP    EXTERNAL-IP   PORT(S)    AGE
service/app-text-embedding-nim       ClusterIP   10.x.x.x      <none>        8000/TCP   112s
service/app-text-embedding-nim-sts   ClusterIP   None          <none>        8000/TCP   112s
```

**Service Verification:**
- **Pod Status**: Should show `1/1 Running` indicating the container is healthy
- **Services**: Two services are created:
  - `app-text-embedding-nim`: Main service with ClusterIP for external access
  - `app-text-embedding-nim-sts`: StatefulSet service for internal communication

**Deployment Verification:**
```bash
# Check deployment status
helm status <any_name> -n <embedding-namespace>

# Monitor pod logs
kubectl logs -f deployment/<deployment-name> -n <embedding-namespace>
```

### GenAI Performance Testing Setup

After deploying the NIM service, set up the performance testing environment using GenAI-Perf:

#### PVC Configuration (genai-pvc.yaml)

Create or modify the `genai-pvc.yaml` file with the following content:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: genaistore    # change metadata name as required
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
```

#### Deployment Configuration (genai-deployment.yaml)

Create or modify the `genai-deployment.yaml` file:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: genai-perf-deployment
spec:
  replicas: 1
  selector:
    matchLabels:
      app: genai-perf
  template:
    metadata:
      labels:
        app: genai-perf
    spec:
      containers:
      - name: genai-perf
        image: nvcr.io/nvidia/tritonserver:25.01-py3-sdk  # select image as required
        command: ["/bin/bash"]
        args: ["-c", "sleep infinity"]
        volumeMounts:
        - name: genaistore
          mountPath: /workspace
      volumes:
      - name: genaistore
        persistentVolumeClaim:
          claimName: genaistore
```

#### Deploy GenAI Components

```bash
# Create the PVC in the GenAI namespace
kubectl create -f genai-pvc.yaml -n <genai-namespace>

# Create the deployment in the GenAI namespace
kubectl create -f genai-deployment.yaml -n <genai-namespace>

# Verify PVC and Pods
kubectl get pvc -n <genai-namespace>
kubectl get pods -n <genai-namespace>
```

**Expected output after successful GenAI setup:**
```bash
$ kubectl get pvc -n genai-perf
NAME         STATUS   VOLUME         CAPACITY   ACCESS MODES   STORAGECLASS   AGE
genaistore   Bound    pvc-xxx        10Gi       RWO            default        45s

$ kubectl get pods -n genai-perf
NAME                                   READY   STATUS    RESTARTS   AGE
genai-perf-deployment-7d8b9c5f6-xyz12   1/1     Running   0          50s
```

**GenAI Environment Verification:**
- **PVC Status**: Should show `Bound` status with allocated volume
- **Pod Status**: Should show `1/1 Running` indicating the container is ready
- **Image**: Uses Triton Server SDK with GenAI-Perf pre-installed

### Service Testing

After both the NIM embedding service and GenAI environment are deployed, test the embedding service endpoint:

#### Get Service Information

```bash
# Get the ClusterIP of the embedding service
kubectl get services -n <embedding-namespace>

# Example output:
# NAME                                 TYPE        CLUSTER-IP    EXTERNAL-IP   PORT(S)    AGE
# service/app-text-embedding-nim       ClusterIP   10.x.x.x     <none>        8000/TCP   112s
```

#### Test the Embedding Service

```bash
# Test the embedding endpoint with curl
curl -X 'POST' \
  'http://<service-cluster-ip>:8000/v1/embeddings' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
    "input": "hello world",
    "model": "<model-name>",
    "input_type": "passage"
  }'

```

**Parameters to customize:**
- `<service-cluster-ip>`: Replace with the actual ClusterIP from kubectl get services
- `<model-name>`: Replace with your deployed model name (e.g., nvidia/nv-embedqa-e5-v5)


### Performance Benchmarking Execution

After verifying the service works, run comprehensive performance tests using the GenAI-Perf pod:

#### Access the GenAI Performance Pod

```bash
# Get the GenAI pod name
kubectl get pods -n <genai-namespace>

# Example output:
# NAME                                   READY   STATUS    RESTARTS   AGE
# genai-perf-deployment-7d8b9c5f6-xyz12   1/1     Running   0          50s

# Access the pod interactively
kubectl exec -it <pod_name> -n <genai-namespace> -- bash

# Example:
kubectl exec -it genai-perf-deployment-7d8b9c5f6-xyz12 -n genai-perf -- bash
```

#### Copy and Configure Performance Script

```bash
# Inside the pod, you'll be in /workspace directory
# Copy the run_genaiperf_embedder.py script to this location

# From your local machine, copy the script to the pod:
kubectl cp run_genaiperf_embedder.py <genai-namespace>/<pod_name>:/workspace/

```

#### Configure the Performance Script

Edit the `run_genaiperf_embedder.py` script inside the pod to update:

```python
# Update these variables in run_genaiperf_embedder.py
model = "nvidia/nv-embedqa-e5-v5"  # Change to your deployed model
url = "http://<service-cluster-ip>:8000"  # Change to actual ClusterIP

# Example:
model = "nvidia/nv-embedqa-e5-v5"
url = "http://10.x.x.x:8000"
```

#### Execute Performance Tests

```bash
# Inside the GenAI pod, run the performance benchmark
python3 run_genaiperf_embedder.py
```

**Test Configurations:**
- **Query embeddings**: 20 tokens, batch size 1, concurrency 1-15
- **Passage embeddings**: 300/512 tokens, batch size 64, concurrency 1-5

**Expected execution flow:**
```bash
▶ Running: input_type=passage, tokens=300, batch=64, concurrency=1
▶ Running: input_type=passage, tokens=300, batch=64, concurrency=3
▶ Running: input_type=passage, tokens=300, batch=64, concurrency=5
▶ Running: input_type=query, tokens=20, batch=1, concurrency=1
▶ Running: input_type=query, tokens=20, batch=1, concurrency=3
...
```

Each test will generate detailed performance metrics including latency percentiles and throughput measurements.

## Text Reranking NIM Deployment

The text reranking deployment follows a similar process to the embedding service, with specific configurations for the reranking model. This section provides detailed steps for deploying and testing the reranking service.

### Reranking Namespace Setup

Create a dedicated namespace for the reranking service:

```bash
# Create namespace for reranker service
kubectl create namespace <reranker-namespace>

# Example:
kubectl create namespace reranking-nim1
```

### Reranking Secrets Configuration

Configure the necessary secrets for NGC registry access and API authentication in the reranking namespace:

```bash
# Apply image pull secret for NGC registry access
kubectl apply -n <reranker-namespace> -f imagepull.yaml

# Create NGC API key secret
kubectl create -n <reranker-namespace> secret generic ngc-api \
  --from-literal=NGC_API_KEY=${NGC_API_KEY}

# Verify secrets creation
kubectl get secrets -n <reranker-namespace>
```

**Expected output:**
```
NAME                          TYPE                             DATA   AGE
ngc-api                       Opaque                           1      13s
ngc-secret                    kubernetes.io/dockerconfigjson   1      25s
```

### Fetch Reranking Helm Chart

Download the official NVIDIA text reranking NIM Helm chart from NGC:

```bash
# Fetch the text reranking NIM Helm chart
helm fetch https://helm.ngc.nvidia.com/nim/nvidia/charts/text-reranking-nim-1.3.0.tgz \
  --username='$oauthtoken' \
  --password=$NGC_API_KEY

# Extract the Helm chart
tar -xvf text-reranking-nim-1.3.0.tgz

# Verify extraction
ls -la text-reranking-nim/
```

### Reranking Configuration

#### Reranking values.yaml Configuration

Modify the `values.yaml` file in the extracted chart directory for reranking-specific settings:

```yaml
# Image configuration for reranking
image:
  repository: nvcr.io/nim/nvidia/llama-3.2-nv-rerankqa-1b-v2  # Reranking model container
  pullPolicy: IfNotPresent
  tag: "1.3.0"                                                # Reranking model version

# Image pull secrets for NGC registry access
imagePullSecrets:
  - name: ngc-secret    # Must match your image pull secret name

# Environment variables with proxy configuration
envVars:
  http_proxy: <add>
  https_proxy: <add>
  no_proxy: <add>

# Storage options (based on environment and cluster requirements)
persistence:
  enabled: true

# Resource requirements for reranking model
resources:
  limits:
    nvidia.com/gpu: 1    # Adjust based on model requirements
    memory: 32Gi
    cpu: 8
  requests:
    nvidia.com/gpu: 1
    memory: 16Gi
    cpu: 4
```

#### Replace _config.tpl (if needed)

If you encounter configuration issues, replace the default `_config.tpl` file:

```bash
# Navigate to the extracted chart directory
cd text-reranking-nim

# Replace the _config.tpl file in the nim-library templates
cp _config.tpl charts/nim-library/templates/_config.tpl

# Verify the file replacement
ls -la charts/nim-library/templates/_config.tpl
```

### Deploy Reranking Service

Install the reranking service using Helm:

```bash
# Navigate outside of the extracted chart directory (if inside it)
cd ..

# Install the reranking Helm chart
helm install <reranking-release-name> text-reranking-nim/ -n <reranker-namespace>

# Example:
helm install my-reranker text-reranking-nim/ -n reranking-nim1
```

**Parameters:**
- `<reranking-release-name>`: Choose a name for your reranking Helm release (e.g., my-reranker, reranking-service)
- `<reranker-namespace>`: The namespace for reranking deployment (e.g., reranking-nim1)

### Verify Reranking Deployment

Check the deployment status and ensure all components are running:

```bash
# Verify the reranking deployment
kubectl get pods -n <reranker-namespace>
kubectl get services -n <reranker-namespace>

# Get all resources in the reranking namespace
kubectl get all -n <reranker-namespace>
```

**Expected output after successful reranking deployment:**
```bash
$ kubectl get all -n reranking-nim1
NAME                           READY   STATUS    RESTARTS   AGE
pod/app-text-reranking-nim-0   1/1     Running   0          95s

NAME                                 TYPE        CLUSTER-IP    EXTERNAL-IP   PORT(S)    AGE
service/app-text-reranking-nim       ClusterIP   10.x.x.x      <none>        8000/TCP   95s
service/app-text-reranking-nim-sts   ClusterIP   None          <none>        8000/TCP   95s
```

### Test Reranking Service

Test the reranking service endpoint to ensure it's working correctly:

```bash
# Get the ClusterIP of the reranking service
kubectl get services -n <reranker-namespace>

# Test the reranking endpoint with curl
curl -X "POST" \
  "http://<ip>:31084/v1/ranking" \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "model": "<model>",
  "query": {"text": "which way did the traveler go?"},
  "passages": [
    {"text": "two roads diverged in a yellow wood, and sorry i could not travel both and be one traveler, long i stood and looked down one as far as i could to where it bent in the undergrowth;"},
    {"text": "then took the other, as just as fair, and having perhaps the better claim because it was grassy and wanted wear, though as for that the passing there had worn them really about the same,"},
    {"text": "and both that morning equally lay in leaves no step had trodden black. oh, i marked the first for another day! yet knowing how way leads on to way i doubted if i should ever come back."},
    {"text": "i shall be telling this with a sigh somewhere ages and ages hence: two roads diverged in a wood, and i, i took the one less traveled by, and that has made all the difference."}
  ],
  "truncate": "END"
}'
```

**Parameters to customize:**
- `<reranking-service-cluster-ip>`: Replace with the actual ClusterIP from kubectl get services
- `<reranking-model-name>`: Replace with your deployed reranking model name (e.g., nvidia/llama-3.2-nv-rerankqa-1b-v2)

### Reranking Performance Testing

#### Configure Reranking Performance Script

Access the GenAI-Perf pod and configure the reranking performance script:

```bash
# Get the GenAI pod name (same pod used for embedding tests)
kubectl get pods -n <genai-namespace>

# Access the pod interactively
kubectl exec -it <genai-pod-name> -n <genai-namespace> -- bash

# Copy the reranking performance script to the pod
# (Run this from outside the pod first)
kubectl cp run_genaiperf_reranker.py <genai-namespace>/<genai-pod-name>:/workspace/
```

#### Update Reranking Script Configuration

Inside the GenAI pod, edit the `run_genaiperf_reranker.py` script:

```python
# Update these variables in run_genaiperf_reranker.py
model = "nvidia/llama-3.2-nv-rerankqa-1b-v2"  # Change to your deployed reranking model
url = "http://<reranking-service-cluster-ip>:8000"  # Change to actual reranking ClusterIP

# Example:
model = "nvidia/llama-3.2-nv-rerankqa-1b-v2"
url = "http://10.x.x.x:8000"
```

#### Execute Reranking Performance Tests

```bash
# Inside the GenAI pod, run the reranking performance benchmark
python3 run_genaiperf_reranker.py
```

**Test Configurations:**
- **Input tokens**: 512
- **Batch sizes**: 10, 20, 40
- **Concurrency levels**: 1, 3, 5

**Expected reranking execution flow:**
```bash
▶ Running reranking test: passages=5, batch=1, concurrency=1
▶ Running reranking test: passages=5, batch=1, concurrency=3
▶ Running reranking test: passages=10, batch=1, concurrency=1
▶ Running reranking test: passages=10, batch=1, concurrency=3
...
```

Each reranking test will generate detailed performance metrics including latency percentiles and throughput measurements specific to reranking operations.


## Documentation Sources:
- [NVIDIA NIM Text Embedding Performance](https://docs.nvidia.com/nim/nemo-retriever/text-embedding/1.2.0/performance.html)
- [NVIDIA NIM Text Reranking Performance](https://docs.nvidia.com/nim/nemo-retriever/text-reranking/latest/performance.html)
