import os
import toml
import subprocess
import json
import base64
import yaml

# Load the TOML file
toml_file_path = "user_input.toml"
config = toml.load(toml_file_path)

# Extract the NGC_API_KEY from the [env] section
ngc_api_key = config["env"]["NGC_API_KEY"]

# Export the NGC_API_KEY as an environment variable
os.environ["NGC_API_KEY"] = ngc_api_key

print(f"NGC_API_KEY has been set to: {os.environ['NGC_API_KEY']}")

# Extract embedding namespace from the TOML file
e_namespace = config["Constants"]["embedding_namespace"]
r_namespace = config["Constants"]["reranking_namespace"]
namespace = config["Constants"]["namespace"]

# Function to create a namespace
def create_namespace(ns):
    try:
        subprocess.run(["kubectl", "create", "namespace", ns], check=True)
        print(f"Namespace '{ns}' created successfully.")
    except subprocess.CalledProcessError:
        print(f"Namespace '{ns}' already exists or could not be created.")

# Create all required namespaces
for ns in [e_namespace, r_namespace, namespace]:
    create_namespace(ns)

# Extract pvc_name and namespace from TOML
pvc_name = config["Constants"]["pvc_name"]
namespace = config["Constants"]["namespace"]

# Update genai-pvc.yaml with the correct PVC name
pvc_yaml_path = os.path.join(os.getcwd(), "genai-pvc.yaml")
try:
    with open(pvc_yaml_path, "r") as file:
        pvc_lines = file.readlines()

    updated_pvc_lines = []
    for line in pvc_lines:
        if line.strip().startswith("name:"):
            updated_pvc_lines.append(f"  name: {pvc_name}\n")
        else:
            updated_pvc_lines.append(line)

    with open(pvc_yaml_path, "w") as file:
        file.writelines(updated_pvc_lines)

    print(f"genai-pvc.yaml updated with pvc_name '{pvc_name}'.")
except Exception as e:
    print(f"Error updating genai-pvc.yaml: {e}")
    exit(1)

# Create the PVC in the specified namespace
try:
    subprocess.run(
        ["kubectl", "create", "-f", pvc_yaml_path, "-n", namespace],
        check=True
    )
    print(f"PVC '{pvc_name}' created successfully in namespace '{namespace}'.")
except subprocess.CalledProcessError as e:
    print(f"Error creating PVC: {e}")
    exit(1)

image = config["Constants"]["image"]

# Update genai-deployment.yaml
deployment_yaml_path = os.path.join(os.getcwd(), "genai-deployment.yaml")
try:
    with open(deployment_yaml_path, "r") as f:
        deployment = yaml.safe_load(f)

    # Update image
    deployment['spec']['template']['spec']['containers'][0]['image'] = image

    # Update PVC name in volumes
    for vol in deployment['spec']['template']['spec']['volumes']:
        if 'persistentVolumeClaim' in vol:
            vol['name'] = pvc_name
            vol['persistentVolumeClaim']['claimName'] = pvc_name

    # Write back the updated YAML
    with open(deployment_yaml_path, "w") as f:
        yaml.dump(deployment, f, default_flow_style=False)

    print(f"genai-deployment.yaml updated with pvc_name '{pvc_name}' and image '{image}'.")
except Exception as e:
    print(f"Error updating genai-deployment.yaml: {e}")
    exit(1)

# Create the deployment in the specified namespace
try:
    subprocess.run(
        ["kubectl", "create", "-f", deployment_yaml_path, "-n", namespace],
        check=True
    )
    print(f"Deployment created successfully in namespace '{namespace}'.")
except subprocess.CalledProcessError as e:
    print(f"Error creating deployment: {e}")
    exit(1)

# Extract Helm chart details from the [helm] section
helm_chart_url = config["helm"]["helm_chart_url"]
helm_chart_file = config["helm"]["helm_chart_file"]

# Fetch the Helm chart
try:
    subprocess.run(
        [
            "helm", "fetch", helm_chart_url,
            "--username=$oauthtoken",
            f"--password={ngc_api_key}"
        ],
        check=True
    )
    print("Helm chart fetched successfully.")
except subprocess.CalledProcessError as e:
    print(f"Error fetching Helm chart: {e}")
    exit(1)

# Extract the Helm chart
try:
    subprocess.run(["tar", "-xvf", helm_chart_file], check=True)
    print("Helm chart extracted successfully.")
except subprocess.CalledProcessError as e:
    print(f"Error extracting Helm chart: {e}")
    exit(1)


docker_config = {
    "auths": {
        "nvcr.io": {
            "username": "$oauthtoken",
            "password": ngc_api_key
        }
    }
}

# Convert the DOCKER_CONFIG to a JSON string
docker_config_json = json.dumps(docker_config)

# Encode the JSON string in base64
docker_config_base64 = base64.b64encode(docker_config_json.encode()).decode()

# Export the base64-encoded DOCKER_CONFIG as NGC_REGISTRY_PASSWORD
os.environ["NGC_REGISTRY_PASSWORD"] = docker_config_base64

print(f"NGC_REGISTRY_PASSWORD has been set to: {os.environ['NGC_REGISTRY_PASSWORD']}")


# Define the target directory
target_directory = os.path.join(os.getcwd(), "Embedding-Reranker")

# Ensure the directory exists
os.makedirs(target_directory, exist_ok=True)


# Extract the secret name from the TOML file
secret_name = config["Constants"]["secret-name"]
# Ensure the secret name is not empty
if not secret_name:
    print("Error: Secret name is empty in the TOML file.")
    exit(1)

# Create the image_pull.yaml file content
imagepull_yaml_content = f"""apiVersion: v1
kind: Secret
metadata:
  name: {secret_name}
type: kubernetes.io/dockerconfigjson
data:
  .dockerconfigjson: {docker_config_base64}
"""

# Write the content to imagepull.yaml inside the target directory
imagepull_file_path = os.path.join(target_directory, "image_pull.yaml")
with open(imagepull_file_path, "w") as yaml_file:
    yaml_file.write(imagepull_yaml_content)

print(f"image_pull.yaml file has been created successfully in {target_directory}.")

# Apply the image pull secret
try:
    subprocess.run(
        ["kubectl", "apply", "-f", imagepull_file_path, "-n", e_namespace],
        check=True
    )
    print(f"Image pull secret '{secret_name}' applied successfully in namespace '{e_namespace}'.")
except subprocess.CalledProcessError as e:
    print(f"Error applying image pull secret '{secret_name}': {e}")
    exit(1)
   
# Create a Kubernetes secret for the NGC_API_KEY
try:
    subprocess.run(
        [
            "kubectl", "create", "-n", e_namespace, "secret", "generic", "ngc-api",
            f"--from-literal=NGC_API_KEY={ngc_api_key}"
        ],
        check=True
    )
    print(f"Kubernetes secret 'ngc-api' created successfully in namespace '{e_namespace}'.")
except subprocess.CalledProcessError as e:
    print(f"Error creating Kubernetes secret 'ngc-api': {e}")
    exit(1)

#list the secrets in the namespace
try:
    subprocess.run(
        ["kubectl", "get", "secrets", "-n", e_namespace],
        check=True
    )
    print(f"Listed secrets in namespace '{e_namespace}' successfully.")
except subprocess.CalledProcessError as e:
    print(f"Error listing secrets in namespace '{e_namespace}': {e}")
    exit(1)


# Extract values from the TOML file
gpu_limit = config["Constants"]["gpu_limit"]
node_value = config["Constants"]["node_value"]
image_repository = config["Constants"]["image_repository"]
image_tag = config["Constants"]["image_tag"]    
helm_release_name = config["Constants"]["helm_release_name"]

# Define the path to the values.yaml file
values_file_path = os.path.join(os.getcwd(), "Embedding-Reranker", "embedding", "values.yaml")


# Update the values.yaml file
try:
    with open(values_file_path, "r") as file:
        values_content = file.readlines()

    # Modify the relevant sections in values.yaml
    updated_values = []
    for line in values_content:
        if "values:" in line:  # Update node value
            updated_values.append(f"          - {node_value}\n")
        elif "repository:" in line:  # Update image repository
            updated_values.append(f"  repository: {image_repository}\n")
        elif "tag:" in line:  # Update image tag
            updated_values.append(f"  tag: \"{image_tag}\"\n")
        elif "nvidia.com/gpu:" in line:  # Update GPU limit
            updated_values.append(f"    nvidia.com/gpu: {gpu_limit}\n")
        else:
            updated_values.append(line)

    # Write the updated content back to values.yaml
    with open(values_file_path, "w") as file:
        file.writelines(updated_values)

    print(f"values.yaml file has been updated successfully at {values_file_path}.")
except FileNotFoundError:
    print(f"Error: The file {values_file_path} does not exist.")
    exit(1)
except Exception as e:
    print(f"Error updating values.yaml: {e}")
    exit(1)

os.chdir("..")
print(f"Changed directory to: {os.getcwd()}")

# Execute the Helm install command
try:
    subprocess.run(
        ["helm", "install", helm_release_name, "embedding/", "-n", e_namespace],
        check=True
    )
    print(f"Helm chart installed successfully with release name '{helm_release_name}' in namespace '{e_namespace}'.")
except subprocess.CalledProcessError as e:
    print(f"Error installing Helm chart: {e}")
    exit(1)


# List the pods in the namespace
try:
    subprocess.run(
        ["kubectl", "get", "pods", "-n", e_namespace],
        check=True
    )
    print(f"Listed pods in namespace '{e_namespace}' successfully.")
except subprocess.CalledProcessError as e:
    print(f"Error listing pods in namespace '{e_namespace}': {e}")
    exit(1)


# Get events for the specific object in the namespace
try:
    subprocess.run(
        [
            "kubectl", "get", "events",
            "--field-selector", "involvedObject.name=text-embedding-nim",
            "-n", e_namespace
        ],
        check=True
    )
    print(f"Events for 'text-embedding-nim' in namespace '{e_namespace}' listed successfully.")
except subprocess.CalledProcessError as e:
    print(f"Error listing events for 'text-embedding-nim' in namespace '{e_namespace}': {e}")
    exit(1)

model = config["Constants"]["model"]

# Get the service IP from Kubernetes
try:
    result = subprocess.run(
        ["kubectl", "get", "svc", "-n", e_namespace, "-o", "json"],
        capture_output=True,
        text=True,
        check=True
    )
    services = json.loads(result.stdout)
    # Assuming the service you need is the first one in the list
    service_ip = services["items"][0]["status"]["loadBalancer"]["ingress"][0]["ip"]
    print(f"Service IP: {service_ip}")
except subprocess.CalledProcessError as e:
    print(f"Error fetching service IP: {e}")
    exit(1)
except KeyError:
    print("Error: Could not find the service IP in the response.")
    exit(1)

# Define the service URL
service_url = f"http://{service_ip}:8000/v1/embeddings"

# Define the payload
payload = {
    "input": "hello world",
    "model": model,
    "input_type": "passage"
}

# Execute the curl command
try:
    subprocess.run(
        [
            "curl", "-X", "POST",
            service_url,
            "-H", "application/json",
            "-H", "Content-Type: application/json",
            "-d", json.dumps(payload)  # Convert payload to JSON format
        ],
        check=True
    )
    print(f"Request sent successfully to {service_url}.")
except subprocess.CalledProcessError as e:
    print(f"Error sending request to {service_url}: {e}")
    exit(1)    


import subprocess

namespace = config["Constants"]["namespace"]

# 1. Get the genaiperf pod name
try:
    result = subprocess.run(
        ["kubectl", "get", "pods", "-n", namespace, "-o", "jsonpath={.items[?(@.metadata.labels.app=='genai-deployment-madhu')].metadata.name}"],
        capture_output=True, text=True, check=True
    )
    pod_name = result.stdout.strip()
    print(f"Found pod: {pod_name}")
except subprocess.CalledProcessError as e:
    print(f"Error getting pod name: {e}")
    exit(1)

# 2. Copy files into the pod
files_to_copy = [
    "Embedding-Reranker/run_genaiperf_embedder.py",
    "Embedding-Reranker/run_genaiperf_reranking.py"
]
for file_path in files_to_copy:
    try:
        subprocess.run(
            ["kubectl", "cp", file_path, f"{namespace}/{pod_name}:/workspace/{file_path.split('/')[-1]}"],
            check=True
        )
        print(f"Copied {file_path} to pod {pod_name}")
    except subprocess.CalledProcessError as e:
        print(f"Error copying {file_path}: {e}")
        exit(1)


# 3. Get the cluster IP of the text-embedding-nim service
try:
    result = subprocess.run(
        ["kubectl", "get", "svc", "-n", e_namespace, "-o", "jsonpath={.items[?(@.metadata.name=='text-embedding-nim')].spec.clusterIP}"],
        capture_output=True, text=True, check=True
    )
    cluster_ip = result.stdout.strip()
    print(f"Cluster IP: {cluster_ip}")
    # Update the run_genaiperf_embedder.py file with the cluster IP
    embedder_file_path = "/workspace/run_genaiperf_embedder.py"
    with open(embedder_file_path, "r") as file:
        embedder_content = file.readlines()
    updated_embedder_content = []
    for line in embedder_content:   
        if "url = " in line:
            updated_embedder_content.append(f'url = "http://{cluster_ip}:8000"\n')
        elif "model = " in line:
            updated_embedder_content.append(f'model = "{model}"\n')
        else:
            updated_embedder_content.append(line)
    with open(embedder_file_path, "w") as file:
        file.writelines(updated_embedder_content)       
    print(f"Updated {embedder_file_path} with cluster IP '{cluster_ip}' and model '{model}'.")
except subprocess.CalledProcessError as e:
    print(f"Error getting cluster IP: {e}")
    exit(1)
   


# 4. Run the Python scripts inside the pod
try:            
    subprocess.run(
        ["kubectl", "exec", pod_name, "-n", namespace, "--", "python3", "/workspace/run_genaiperf_embedder.py"],
        check=True
    )
    print("run_genaiperf_embedder.py executed successfully.")   
except subprocess.CalledProcessError as e:
    print(f"Error executing run_genaiperf_embedder.py: {e}")
    exit(1)     

#main function to run the automation script
if __name__ == "__main__":  
    print("Automation script executed successfully.")    