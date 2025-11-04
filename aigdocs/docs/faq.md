# Table of Contents

- [1. Installation](#1-installation)
  - [1.1 Port Conflict](#11-port-conflict)
  - [1.2 Permission Issues](#12-permission-issues)
  - [1.3 Service Startup Failure](#13-service-startup-failure)
  - [1.4 Stopping the Service](#14-stopping-the-service)
  - [1.5 Updating the Deployment](#15-updating-the-deployment)
- [2. Task Execution Errors and Troubleshooting](#2-task-execution-errors-and-troubleshooting)
- [3. Installation Without Internet Connection](#3-installation-without-internet-connection)
  - [3.1 Prepare Images on Internet-Connected Server](#31-prepare-images-on-internet-connected-server)
  - [3.2 Export Images to Tar Files](#32-export-images-to-tar-files)
  - [3.3 Copy Image Packages to Internal Network Server](#33-copy-image-packages-to-internal-network-server)
  - [3.4 Import Images on Internal Network Server](#34-import-images-on-internal-network-server)
  - [3.5 Start Containers](#35-start-containers)
- [4. Recommended Models](#4-recommended-models)
  - [4.1 Recommended Choices for MCP Scan](#41-recommended-choices-for-mcp-scan)
  - [4.2 Recommended Choices for Jailbreak Evaluation Models](#42-recommended-choices-for-jailbreak-evaluation-models)
- [5. Inaccurate Jailbreak Detection with Custom Evaluation Datasets](#5-inaccurate-jailbreak-detection-with-custom-evaluation-datasets)
- [6. Adding Model Failed](#6-adding-model-failed)

---

## 1.Installation
### 1.1 Port Conflict
   ```bash
   # Modify the webserver port mapping
   ports:
     - "8080:8088"  # Use port 8080
   ```

### 1.2 Permission Issues
   ```bash
   # Ensure the data directory has read/write permissions
   sudo chown -R $USER:$USER ./data
   ```

### 1.3 Service Startup Failure
   ```bash
   # View detailed logs
   docker-compose logs webserver
   docker-compose logs agent
   ```

### 1.4 Stopping the Service
   ```bash
   # Stop the service
   docker-compose down
   # Stop the service and remove data volumes (use with caution)
   docker-compose down -v
   ```

### 1.5 Updating the Deployment

To upgrade to the latest version and clean up obsolete resources:

```bash
# Rebuild container images and restart services
docker-compose -f docker-compose.images.yml up -d --build
# Prune dangling Docker images (optional cleanup)
docker image prune -f
```



## 2. Task Execution Errors and Troubleshooting

When encountering task execution errors or agent service problems, follow these troubleshooting steps:

```bash
# Log into the server where the Docker container is running
# Execute the following command to view agent logs
docker compose logs agent
```


## 3. Installation Without Internet Connection

You can prepare the required images and resources on a machine with internet access, then migrate them to the internal network server for deployment. Here's the specific approach:

### 3.1 Prepare Images on Internet-Connected Server

On a server with internet access, pull the required images:

```bash
# Pull the required A.I.G images
docker pull zhuquelab/aig-server:latest
docker pull zhuquelab/aig-agent:latest

# View local images
docker images
```

### 3.2 Export Images to Tar Files

Use the `docker save` command to save A.I.G images as tar packages:

```bash
# Export A.I.G images to tar files
docker save -o aig-server.tar zhuquelab/aig-server:latest
docker save -o aig-agent.tar zhuquelab/aig-agent:latest
```

### 3.3 Copy Image Packages to Internal Network Server

Transfer the tar files to your internal network server using your preferred method (USB drive, network transfer, etc.).

### 3.4 Import Images on Internal Network Server

Use the `docker load` command to import the tar packages into Docker:

```bash
# Import A.I.G images from tar files
docker load -i aig-server.tar
docker load -i aig-agent.tar
```

### 3.5 Start Containers

After importing the images, you can start the containers using the `docker-compose.images.yml` file (download from the GitHub repository root directory):

```bash
# Start containers with the images
docker-compose -f docker-compose.images.yml up -d
```

## 4. Recommended Models
### 4.1 Recommended Choices for MCP Scan
- GLM4.5
- DeepSeek-V3.1
- Kimi-K2-Instruct
- Qwen3-Coder-480B
- Hunyuan-Turbos

### 4.2 Recommended Choices for Jailbreak Evaluation Models

When working with a custom dataset, selecting an appropriate safety evaluation model can significantly improve the accuracy of automated assessments. You can balance model selection from two dimensions: **language** and **scenario**.

#### Language
- **Chinese Recommendation:**  
  - `qwen3-max` (best performance)  
  - `qwen3-235b-a22b-2507` (cost-effective choice)  
- **English Recommendation:**  
  - `claude-opus-4.1` (best performance)  
  - `claude-sonnet-4` (very good performance)  
  - `gemini-2.0-flash` (cost-effective choice)  

#### Scenario
- **Politically sensitive content testing:**  
  **Do not** choose Gemini models. Instead, prioritize domestic models such as `hunyuan-turbos` or `qwen3`. Cloud-based API calls yield better results.  
- **National, regional, or racial bias testing:**  
  Gemini models perform best.  
- **Dangerous weapons or high-risk behavior testing:**  
  Claude models perform best. For cost-effectiveness, Gemini models are also an option.  

## 5. Inaccurate Jailbreak Detection with Custom Evaluation Datasets

You can adjust the evaluation criteria based on the characteristics of your dataset. To modify the evaluation standards, please refer to the template file at: [https://github.com/Tencent/AI-Infra-Guard/blob/main/AIG-PromptSecurity/deepteam/metrics/harm/template.py](https://github.com/Tencent/AI-Infra-Guard/blob/main/AIG-PromptSecurity/deepteam/metrics/harm/template.py)

## 6. Adding Model Failed

A.I.G supports model interfaces in standard OpenAI format. If your model is not in OpenAI format, you can use a model API gateway to perform format conversion, such as [https://github.com/BerriAI/litellm](https://github.com/BerriAI/litellm).