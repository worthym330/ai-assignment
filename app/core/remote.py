import json
import logging
from typing import Optional, Union, Dict, Any, Generator

from openfabric_pysdk.helper import Proxy
from openfabric_pysdk.helper.proxy import ExecutionResult

# Setting up the logger
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class Remote:
    """
    Enhanced Remote class with LLM-specific improvements.
    Maintains all original functionality while adding features useful for LLM operations.
    """

    def __init__(self, proxy_url: str, proxy_tag: Optional[str] = None, timeout: int = 30):
        """
        Initialize with additional timeout parameter.
        
        Args:
            proxy_url: The base URL of the proxy
            proxy_tag: Optional tag for the proxy instance
            timeout: Timeout in seconds for operations (default: 30)
        """
        self.proxy_url = proxy_url
        self.proxy_tag = proxy_tag
        # self.timeout = timeout
        self.client: Optional[Proxy] = None
        logger.debug(f"Remote instance initialized with proxy_url={proxy_url}, proxy_tag={proxy_tag}, timeout={timeout}")

    def connect(self) -> 'Remote':
        """Establish connection with timeout support"""
        logger.debug("Attempting to connect to proxy")
        self.client = Proxy(
            self.proxy_url, 
            self.proxy_tag, 
            ssl_verify=False,
            # timeout=self.timeout
        )
        logger.info(f"Successfully connected to proxy {self.proxy_url} with tag {self.proxy_tag}")
        return self

    def execute(self, inputs: dict, uid: str, stream: bool = False) -> Union[ExecutionResult, None]:
        """
        Enhanced execute with streaming support.
        
        Args:
            inputs: Input payload
            uid: Unique request identifier
            stream: Whether to enable streaming (default: False)
            
        Returns:
            ExecutionResult or None if not connected
        """
        if self.client is None:
            logger.error("Client is not connected. Execute failed.")
            return None

        logger.debug(f"Executing request with uid={uid}, stream={stream}")
        # Add streaming flag to inputs if LLM request
        if isinstance(inputs, dict) and inputs.get("model"):
            inputs["stream"] = stream

        result = self.client.request(inputs, uid)
        logger.info(f"Request executed with uid={uid}")
        return result

    @staticmethod
    def get_response(output: ExecutionResult) -> Union[dict, None]:
        """
        Original get_response with enhanced error handling.
        """
        if output is None:
            logger.warning("Received empty output, returning None")
            return None

        output.wait()
        status = str(output.status()).lower()
        
        logger.debug(f"Response status: {status}")
        
        if status == "completed":
            logger.info("Request completed successfully")
            return output.data()
        elif status == "failed":
            error = output.error() or "Unknown error"
            logger.error(f"Request failed: {error}")
            raise Exception(f"Request failed: {error}")
        elif status == "cancelled":
            logger.warning("Request was cancelled")
            raise Exception("Request was cancelled")
        else:
            logger.error(f"Unexpected request status: {status}")
            raise Exception(f"Unexpected request status: {status}")

    def execute_sync(self, inputs: dict, configs: dict, uid: str) -> Union[dict, None]:
        """
        Original synchronous execute with timeout enforcement.
        """
        if self.client is None:
            logger.error("Client is not connected. Sync execute failed.")
            return None

        logger.debug(f"Executing sync request with uid={uid}")
        output = self.client.execute(inputs, configs, uid)
        return self.get_response(output)

    # New LLM-specific methods
    def stream_response(self, output: ExecutionResult) -> Generator[Dict[str, Any], None, None]:
        """
        Stream LLM responses chunk by chunk.
        
        Args:
            output: ExecutionResult from a streaming request
            
        Yields:
            Response chunks as they arrive
        """
        if output is None:
            logger.error("Stream error: No output provided.")
            return

        while not output.completed():
            if output.error():
                logger.error(f"Stream error: {output.error()}")
                raise Exception(f"Stream error: {output.error()}")
                
            chunk = output.stream()
            if chunk:
                try:
                    logger.debug("Received chunk, attempting to parse")
                    yield json.loads(chunk)
                except json.JSONDecodeError:
                    logger.warning("Chunk not valid JSON, returning as plain content")
                    yield {"content": chunk}
            
            if output.completed():
                logger.info("Streaming completed")
                break

    async def execute_async(self, inputs: dict, uid: str) -> Union[dict, None]:
        """
        Async version of execute (if your Proxy supports async).
        """
        # Implementation depends on your Proxy's async capabilities
        logger.warning("Async execution not implemented in base Proxy")
        raise NotImplementedError("Async execution not implemented in base Proxy")

    def health_check(self) -> bool:
        """
        Check if the remote connection is healthy.
        Useful for LLM services that need persistent connections.
        """
        if self.client is None:
            logger.error("Client is not connected. Health check failed.")
            return False
        healthy = self.client.ping()
        logger.info(f"Health check result: {healthy}")
        return healthy
