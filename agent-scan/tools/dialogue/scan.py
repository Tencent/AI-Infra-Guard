"""
Scan tool for collecting agent configuration information via API endpoints.

This tool automatically discovers and scans configuration endpoints based on
the provider type defined in providers.yaml - configuration driven approach.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from tools.registry import register_tool
from core.agent_adapter.adapter import AIProviderClient, ProviderOptions, ProviderConfig, ProviderConfigLoader
from utils.tool_context import ToolContext
from utils.loging import logger

class EndpointScanResult(BaseModel):
    """Result from scanning a single endpoint."""
    endpoint: str
    success: bool
    status_code: Optional[int] = None
    response: Optional[Any] = None
    error: Optional[str] = None
    sensitive_findings: Optional[List[str]] = None


class ScanResult(BaseModel):
    """Complete scan result for an agent."""
    provider_type: str
    base_url: str
    total_endpoints: int
    successful_scans: int
    failed_scans: int
    endpoint_results: List[EndpointScanResult] = Field(default_factory=list)
    summary: Optional[str] = None


class AgentScanner:
    """
    Scanner for collecting agent configuration information.
    
    This scanner automatically detects the provider type and scans
    all configured endpoints defined in providers.yaml.
    
    The scan endpoints are configuration-driven, not hardcoded.
    """
    
    # Sensitive patterns to detect in responses
    SENSITIVE_PATTERNS = [
        ("api_key", "API Key Exposure"),
        ("api_secret", "API Secret Exposure"),
        ("password", "Password Exposure"),
        ("token", "Token Exposure"),
        ("secret", "Secret Exposure"),
        ("private_key", "Private Key Exposure"),
        ("credential", "Credential Exposure"),
        ("database", "Database Configuration"),
        ("connection_string", "Connection String"),
        ("internal_", "Internal Configuration"),
        ("debug", "Debug Information"),
    ]
    
    def __init__(self, timeout: int = 30):
        self.client = AIProviderClient(timeout=timeout)
        self.config_loader = ProviderConfigLoader()
    
    def scan_agent(self, provider: ProviderOptions, endpoints: Optional[List[str]] = None) -> ScanResult:
        """
        Scan an agent's configuration endpoints.
        
        Args:
            provider: Provider configuration
            endpoints: Optional list of specific endpoints to scan.
                      If None, uses endpoints from providers.yaml based on provider type.
        
        Returns:
            ScanResult with all endpoint scan results
        """
        provider_id = (provider.id or "").lower()
        provider_type = self._extract_provider_type(provider_id)
        
        # Get base URL
        base_url = self._get_base_url(provider)
        
        # Get scan endpoints from providers.yaml configuration (configuration-driven)
        if endpoints is None:
            endpoints = self._get_scan_endpoints_from_config(provider_type, provider)
        
        if not endpoints:
            return ScanResult(
                provider_type=provider_type,
                base_url=base_url,
                total_endpoints=0,
                successful_scans=0,
                failed_scans=0,
                summary=f"No scan_endpoints configured in providers.yaml for provider type: {provider_type}"
            )
        
        # Scan all endpoints
        endpoint_results = []
        successful = 0
        failed = 0
        
        for endpoint in endpoints:
            result = self._scan_endpoint(provider, base_url, endpoint)
            endpoint_results.append(result)
            if result.success:
                successful += 1
            else:
                failed += 1
        
        return ScanResult(
            provider_type=provider_type,
            base_url=base_url,
            total_endpoints=len(endpoints),
            successful_scans=successful,
            failed_scans=failed,
            endpoint_results=endpoint_results,
            summary=f"Scanned {len(endpoints)} endpoints: {successful} successful, {failed} failed"
        )
    
    def _extract_provider_type(self, provider_id: str) -> str:
        """Extract provider type from provider ID."""
        if ":" in provider_id:
            return provider_id.split(":")[0]
        return provider_id
    
    def _get_base_url(self, provider: ProviderOptions) -> str:
        """Get base URL from provider configuration."""
        if provider.config and provider.config.apiBaseUrl:
            return provider.config.apiBaseUrl.rstrip("/")
        if provider.config and provider.config.url:
            return provider.config.url.rstrip("/")
        return ""
    
    def _get_scan_endpoints_from_config(self, provider_type: str, provider: ProviderOptions) -> List[str]:
        """
        Get scan endpoints from providers.yaml configuration.
        
        This is the core configuration-driven approach - endpoints are defined
        in providers.yaml under each provider's 'scan_endpoints' field.
        """
        provider_conf = self.config_loader.get_provider_config(provider_type)
        if not provider_conf:
            return []
        
        # Get scan_endpoints from provider configuration
        endpoints = provider_conf.get("scan_endpoints", [])
        
        # Resolve placeholders in endpoints (e.g., {{bot_id}})
        resolved_endpoints = []
        for endpoint in endpoints:
            resolved = self._resolve_endpoint_placeholders(endpoint, provider)
            if resolved:
                resolved_endpoints.append(resolved)
        
        return resolved_endpoints
    
    def _resolve_endpoint_placeholders(self, endpoint: str, provider: ProviderOptions) -> Optional[str]:
        """Resolve placeholders like {{bot_id}} in endpoint paths."""
        if "{{bot_id}}" in endpoint:
            bot_id = self._extract_bot_id(provider)
            if not bot_id:
                return None
            endpoint = endpoint.replace("{{bot_id}}", bot_id)
        return endpoint
    
    def _extract_bot_id(self, provider: ProviderOptions) -> Optional[str]:
        """Extract bot_id from provider configuration."""
        provider_id = (provider.id or "").lower()
        
        # Try to extract from provider_id (e.g., "coze:bot_123")
        if ":" in provider_id:
            parts = provider_id.split(":", 1)
            if len(parts) > 1 and parts[1]:
                return parts[1]
        
        # Try to extract from config.extra
        if provider.config and hasattr(provider.config, 'extra'):
            extra = getattr(provider.config, 'extra', {}) or {}
            if 'bot_id' in extra:
                return extra['bot_id']
        
        return None
    
    def _scan_endpoint(
        self, 
        provider: ProviderOptions, 
        base_url: str, 
        endpoint: str
    ) -> EndpointScanResult:
        """Scan a single endpoint and return the result."""
        url = f"{base_url}{endpoint}"
        
        # Create HTTP provider config for this endpoint scan
        scan_provider = ProviderOptions(
            id="http",
            config=ProviderConfig(
                url=url,
                method="GET",
                headers=self._build_auth_headers(provider),
                body={},
                transform_response="json"
            )
        )
        
        # Make the request
        result = self.client.call_provider(scan_provider, "scan")
        
        # Build endpoint result
        endpoint_result = EndpointScanResult(
            endpoint=endpoint,
            success=result.success,
        )
        
        if result.provider_response:
            metadata = result.provider_response.metadata or {}
            endpoint_result.status_code = metadata.get("status_code")
            endpoint_result.response = result.provider_response.raw
            endpoint_result.error = result.provider_response.error
            
            # Check for sensitive information
            if result.success and result.provider_response.raw:
                findings = self._detect_sensitive_info(result.provider_response.raw)
                if findings:
                    endpoint_result.sensitive_findings = findings
        
        return endpoint_result
    
    def _build_auth_headers(self, provider: ProviderOptions) -> Dict[str, str]:
        """Build authentication headers based on provider configuration."""
        headers = {
            "Content-Type": "application/json"
        }
        
        if provider.config and provider.config.apiKey:
            headers["Authorization"] = f"Bearer {provider.config.apiKey}"
        
        # Merge any additional headers from config
        if provider.config and provider.config.headers:
            headers.update(dict(provider.config.headers))
        
        return headers
    
    def _detect_sensitive_info(self, response: Any) -> List[str]:
        """Detect sensitive information in response data."""
        findings = []
        response_str = str(response).lower()
        
        for pattern, finding_type in self.SENSITIVE_PATTERNS:
            if pattern in response_str:
                findings.append(finding_type)
        
        return list(set(findings))  # Remove duplicates


@register_tool
def scan(endpoints: str = None, context: ToolContext = None) -> str:
    """
    Scan an agent's configuration endpoints to collect information.
    
    This tool automatically detects the provider type from the config file
    and retrieves scan endpoints from providers.yaml configuration.
    
    The scan endpoints are CONFIGURATION-DRIVEN:
    - Dify: scan_endpoints defined in providers.yaml -> ["/info", "/parameters", "/meta", "/site"]
    - Coze: scan_endpoints defined in providers.yaml -> ["/v1/bots/{{bot_id}}"]
    - Custom: Add scan_endpoints to your provider in providers.yaml
    
    Args:
        provider: Provider configuration
        endpoints: Optional comma-separated list of specific endpoints to scan.
                  If not provided, uses endpoints from providers.yaml.
    
    Returns:
        Json string containing scan results with endpoint responses and findings
    """
    scanner = AgentScanner()
    
    # Parse endpoints if provided (override configuration)
    endpoint_list = None
    if endpoints:
        endpoint_list = [e.strip() for e in endpoints.split(",") if e.strip()]
    
    result: ScanResult = scanner.scan_agent(context.agent_provider, endpoint_list)
    logger.info(f"Agent configuration: {result}")
    return result.model_dump_json()