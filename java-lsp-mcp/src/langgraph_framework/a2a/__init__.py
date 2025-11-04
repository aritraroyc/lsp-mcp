"""
Agent-to-Agent (A2A) Service Deployment

Enables A2A communication for subgraphs using HTTP/gRPC protocols
with service discovery support.
"""

from typing import Any, Dict, Optional, Set, List, TYPE_CHECKING, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import asyncio
import logging
import json

try:
    import aiohttp
    from aiohttp import web
    AIOHTTP_AVAILABLE = True
except ImportError:
    aiohttp = None
    web = None
    AIOHTTP_AVAILABLE = False

if TYPE_CHECKING:
    # Only import for type checking, not at runtime
    if not AIOHTTP_AVAILABLE:
        from typing import Any as WebRequest
        from typing import Any as WebResponse
    else:
        from aiohttp.web import Request as WebRequest
        from aiohttp.web import Response as WebResponse

from ..registry import SubgraphMetadata, SubgraphCapability, get_global_registry
from ..subgraphs import SubgraphState, SubgraphStatus

logger = logging.getLogger(__name__)


class ServiceProtocol(Enum):
    """Supported communication protocols."""
    HTTP = "http"
    GRPC = "grpc"
    WEBSOCKET = "websocket"


@dataclass
class ServiceEndpoint:
    """
    Service endpoint information.
    
    Attributes:
        service_name: Name of the service
        protocol: Communication protocol
        host: Host address
        port: Port number
        path: URL path (for HTTP)
        metadata: Additional endpoint metadata
        health_check_url: Optional health check endpoint
        registered_at: Registration timestamp
    """
    service_name: str
    protocol: ServiceProtocol
    host: str
    port: int
    path: str = "/"
    metadata: Dict[str, Any] = field(default_factory=dict)
    health_check_url: Optional[str] = None
    registered_at: datetime = field(default_factory=datetime.now)
    
    def get_url(self) -> str:
        """Get full service URL."""
        if self.protocol == ServiceProtocol.HTTP:
            return f"http://{self.host}:{self.port}{self.path}"
        elif self.protocol == ServiceProtocol.WEBSOCKET:
            return f"ws://{self.host}:{self.port}{self.path}"
        return f"{self.protocol.value}://{self.host}:{self.port}"


class ServiceDiscovery:
    """
    Service discovery registry for A2A communication.
    
    Maintains registry of available service endpoints and supports
    health checking and automatic deregistration.
    """
    
    def __init__(self, health_check_interval: int = 60):
        """
        Initialize service discovery.
        
        Args:
            health_check_interval: Interval in seconds for health checks
        """
        self._services: Dict[str, ServiceEndpoint] = {}
        self._capabilities_index: Dict[SubgraphCapability, Set[str]] = {}
        self.health_check_interval = health_check_interval
        self._health_check_task: Optional[asyncio.Task] = None
        logger.info("ServiceDiscovery initialized")
    
    def register_service(self, endpoint: ServiceEndpoint) -> None:
        """
        Register a service endpoint.
        
        Args:
            endpoint: Service endpoint to register
        """
        self._services[endpoint.service_name] = endpoint
        logger.info(f"Registered service '{endpoint.service_name}' at {endpoint.get_url()}")
    
    def deregister_service(self, service_name: str) -> bool:
        """
        Deregister a service endpoint.
        
        Args:
            service_name: Name of service to deregister
            
        Returns:
            True if deregistered, False if not found
        """
        if service_name in self._services:
            del self._services[service_name]
            logger.info(f"Deregistered service '{service_name}'")
            return True
        return False
    
    def get_service(self, service_name: str) -> Optional[ServiceEndpoint]:
        """
        Get service endpoint by name.
        
        Args:
            service_name: Service name
            
        Returns:
            ServiceEndpoint if found, None otherwise
        """
        return self._services.get(service_name)
    
    def list_services(self, protocol: Optional[ServiceProtocol] = None) -> List[ServiceEndpoint]:
        """
        List all registered services.
        
        Args:
            protocol: Optional filter by protocol
            
        Returns:
            List of service endpoints
        """
        services = list(self._services.values())
        
        if protocol:
            services = [s for s in services if s.protocol == protocol]
        
        return services
    
    async def check_health(self, service_name: str) -> bool:
        """
        Check health of a service.
        
        Args:
            service_name: Service name to check
            
        Returns:
            True if healthy, False otherwise
        """
        endpoint = self.get_service(service_name)
        if not endpoint or not endpoint.health_check_url:
            return False
        
        if aiohttp is None:
            logger.warning("aiohttp not available for health checks")
            return True  # Assume healthy if can't check
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(endpoint.health_check_url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    return resp.status == 200
        except Exception as e:
            logger.warning(f"Health check failed for '{service_name}': {e}")
            return False
    
    async def start_health_checks(self) -> None:
        """Start background health checking."""
        if self._health_check_task:
            return
        
        async def health_check_loop():
            while True:
                await asyncio.sleep(self.health_check_interval)
                for service_name in list(self._services.keys()):
                    healthy = await self.check_health(service_name)
                    if not healthy:
                        logger.warning(f"Service '{service_name}' failed health check")
        
        self._health_check_task = asyncio.create_task(health_check_loop())
        logger.info("Started health check background task")
    
    def stop_health_checks(self) -> None:
        """Stop background health checking."""
        if self._health_check_task:
            self._health_check_task.cancel()
            self._health_check_task = None
            logger.info("Stopped health check background task")


class A2AHttpServer:
    """
    HTTP server for A2A subgraph communication.
    
    Exposes subgraph execution via HTTP API.
    """
    
    def __init__(self, 
                 host: str = "0.0.0.0",
                 port: int = 8080,
                 service_name: str = "a2a-service"):
        """
        Initialize A2A HTTP server.
        
        Args:
            host: Host to bind to
            port: Port to bind to
            service_name: Service name for discovery
        """
        if web is None:
            raise ImportError("aiohttp is required for A2AHttpServer. Install with: pip install aiohttp")
        
        self.host = host
        self.port = port
        self.service_name = service_name
        self.registry = get_global_registry()
        self.app = web.Application()
        self._setup_routes()
        logger.info(f"A2AHttpServer initialized on {host}:{port}")
    
    def _setup_routes(self) -> None:
        """Setup HTTP routes."""
        self.app.router.add_get("/health", self._health_handler)
        self.app.router.add_get("/subgraphs", self._list_subgraphs_handler)
        self.app.router.add_post("/execute/{subgraph_name}", self._execute_handler)
        self.app.router.add_get("/stats", self._stats_handler)
    
    async def _health_handler(self, request) -> Any:
        """Health check endpoint."""
        return web.json_response({
            "status": "healthy",
            "service": self.service_name,
            "timestamp": datetime.now().isoformat()
        })
    
    async def _list_subgraphs_handler(self, request) -> Any:
        """List available subgraphs."""
        subgraphs = self.registry.list_all()
        
        subgraph_list = [
            {
                "name": reg.metadata.name,
                "description": reg.metadata.description,
                "capabilities": [cap.value for cap in reg.metadata.capabilities],
                "tags": list(reg.metadata.tags),
                "priority": reg.metadata.priority,
                "can_execute": reg.can_execute()
            }
            for reg in subgraphs
        ]
        
        return web.json_response({
            "subgraphs": subgraph_list,
            "total": len(subgraph_list)
        })
    
    async def _execute_handler(self, request) -> Any:
        """Execute a subgraph."""
        subgraph_name = request.match_info['subgraph_name']
        
        # Get request body
        try:
            body = await request.json()
        except Exception as e:
            return web.json_response({
                "status": "error",
                "message": f"Invalid JSON: {str(e)}"
            }, status=400)
        
        # Get subgraph
        registration = self.registry.get(subgraph_name)
        if not registration:
            return web.json_response({
                "status": "error",
                "message": f"Subgraph '{subgraph_name}' not found"
            }, status=404)
        
        # Check if can execute
        if not registration.can_execute():
            return web.json_response({
                "status": "error",
                "message": f"Subgraph '{subgraph_name}' is at capacity"
            }, status=503)
        
        # Increment active counter
        self.registry.increment_active(subgraph_name)
        
        try:
            # Prepare input state
            input_state = SubgraphState(
                subgraph_name=subgraph_name,
                input_data=body.get("input", {})
            )
            
            # Execute subgraph
            start_time = datetime.now()
            graph = registration.graph_builder()
            result_state = await graph.ainvoke(input_state)
            end_time = datetime.now()
            
            execution_time = (end_time - start_time).total_seconds()
            
            # Return result
            return web.json_response({
                "status": "success",
                "subgraph": subgraph_name,
                "execution_time": execution_time,
                "result": {
                    "output_data": result_state.output_data,
                    "status": result_state.status.value,
                    "error": result_state.error
                }
            })
            
        except Exception as e:
            logger.error(f"Subgraph execution failed: {e}")
            return web.json_response({
                "status": "error",
                "message": str(e)
            }, status=500)
            
        finally:
            # Decrement active counter
            self.registry.decrement_active(subgraph_name)
    
    async def _stats_handler(self, request) -> Any:
        """Get server statistics."""
        stats = self.registry.get_stats()
        return web.json_response(stats)
    
    async def start(self) -> None:
        """Start the HTTP server."""
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        logger.info(f"A2A HTTP Server started on http://{self.host}:{self.port}")
    
    def run(self) -> None:
        """Run the server (blocking)."""
        web.run_app(self.app, host=self.host, port=self.port)


class A2AHttpClient:
    """
    HTTP client for invoking remote A2A subgraphs.
    """
    
    def __init__(self, service_discovery: Optional[ServiceDiscovery] = None):
        """
        Initialize A2A HTTP client.
        
        Args:
            service_discovery: Optional service discovery instance
        """
        if aiohttp is None:
            raise ImportError("aiohttp is required for A2AHttpClient. Install with: pip install aiohttp")
        
        self.service_discovery = service_discovery
        logger.info("A2AHttpClient initialized")
    
    async def execute_remote_subgraph(self,
                                     service_url: str,
                                     subgraph_name: str,
                                     input_data: Dict[str, Any],
                                     timeout: int = 300) -> Dict[str, Any]:
        """
        Execute a remote subgraph via HTTP.
        
        Args:
            service_url: Base URL of the A2A service
            subgraph_name: Name of subgraph to execute
            input_data: Input data for the subgraph
            timeout: Request timeout in seconds
            
        Returns:
            Execution result dictionary
        """
        url = f"{service_url}/execute/{subgraph_name}"
        
        payload = {
            "input": input_data
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        logger.info(f"Remote execution successful: {subgraph_name}")
                        return result
                    else:
                        error_text = await resp.text()
                        raise Exception(f"Remote execution failed ({resp.status}): {error_text}")
        
        except Exception as e:
            logger.error(f"Remote execution error: {e}")
            raise
    
    async def list_remote_subgraphs(self, service_url: str) -> List[Dict[str, Any]]:
        """
        List subgraphs available on a remote service.
        
        Args:
            service_url: Base URL of the A2A service
            
        Returns:
            List of subgraph information dictionaries
        """
        url = f"{service_url}/subgraphs"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        return result.get("subgraphs", [])
                    else:
                        raise Exception(f"Failed to list subgraphs ({resp.status})")
        
        except Exception as e:
            logger.error(f"List subgraphs error: {e}")
            raise
    
    async def check_service_health(self, service_url: str) -> bool:
        """
        Check health of a remote service.
        
        Args:
            service_url: Base URL of the A2A service
            
        Returns:
            True if healthy, False otherwise
        """
        url = f"{service_url}/health"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    return resp.status == 200
        except Exception:
            return False


def create_a2a_service(host: str = "0.0.0.0",
                      port: int = 8080,
                      service_name: str = "a2a-service",
                      register_discovery: bool = True) -> Tuple[A2AHttpServer, Optional[ServiceEndpoint]]:
    """
    Factory function to create an A2A HTTP service.
    
    Args:
        host: Host to bind to
        port: Port to bind to
        service_name: Service name
        register_discovery: Whether to create service endpoint info
        
    Returns:
        Tuple of (A2AHttpServer, ServiceEndpoint)
    """
    server = A2AHttpServer(host, port, service_name)
    
    endpoint = None
    if register_discovery:
        endpoint = ServiceEndpoint(
            service_name=service_name,
            protocol=ServiceProtocol.HTTP,
            host=host,
            port=port,
            path="/",
            health_check_url=f"http://{host}:{port}/health"
        )
    
    return server, endpoint
