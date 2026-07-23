# A.I.G Case Studies

## Internal AI Infrastructure Vulnerability Scanning

A.I.G's `AI Infra Scan` feature supports the detection of CVE vulnerabilities in the web services of AI frameworks such as vLLM, ComfyUI, Ollama, Triton Inference Server, and Ray.


## More Recommended Integration Scenarios

A.I.G can be flexibly integrated into existing business pipelines to achieve automated security testing. Below are some common integration scenarios and tool types:

### CI/CD Pipelines:
A.I.G can serve as a security gate in a CI/CD pipeline, automatically triggering scans during code submission, build, or deployment phases to ensure that only applications that pass security checks can proceed to the next stage.
-   **Example Integration Point**: Call A.I.G's API for security detection after an MCP Server is built or before it is deployed.

### DevSecOps Platforms:
Integrate with DevSecOps platforms to aggregate all of A.I.G's risk scan results into a unified security dashboard, providing comprehensive security posture awareness.
-   **Example Integration Point**: Import A.I.G's scan reports into the DevSecOps platform via API or report export functionality.

### Git Code Security Review:
Integrate with code repositories to automatically trigger security scans during Pull Requests or Merge Requests, with results displayed directly in the code review interface. Common integration tools include:
-   **Example Integration Point**: Configure webhooks to trigger A.I.G scans on PR/MR events and send the status check results back to the code repository.
