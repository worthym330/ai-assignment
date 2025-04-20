import logging
import time
from typing import Dict, Optional

import requests
from ontology_dc8f06af066e4a7880a5938933236037.config import ConfigClass
from ontology_dc8f06af066e4a7880a5938933236037.input import InputClass
from ontology_dc8f06af066e4a7880a5938933236037.output import OutputClass
from openfabric_pysdk.context import AppModel, State
from core.stub import Stub

# Configurations for the app
configurations: Dict[str, ConfigClass] = {}

############################################################
# LLM Client Implementation
############################################################
class LLMClient:
    def __init__(self, config: ConfigClass):
        self.endpoint = config.llm_endpoint
        # self.timeout = config.timeout
        self.default_model = config.default_model
        self.max_tokens = config.max_response_tokens
        logging.info(f"LLMClient initialized with endpoint: {self.endpoint}")

    def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False
    ) -> Optional[Dict]:
        """Generate text from the LLM"""
        logging.info(f"Generating response for prompt: '{prompt[:50]}...'")  # Log first 50 characters of the prompt
        
        payload = {
            "model": model or self.default_model,
            "prompt": prompt,
            "stream": stream,
            "options": {
                "temperature": temperature or 0.7,
                "num_predict": max_tokens or self.max_tokens
            }
        }

        try:
            start_time = time.time()
            logging.info(f"Sending request to LLM API at {self.endpoint}")
            response = requests.post(
                self.endpoint,
                json=payload,
                headers={"Content-Type": "application/json"},
                # timeout=self.timeout
            )
            response.raise_for_status()

            data = response.json()
            generation_time = time.time() - start_time
            logging.info(f"LLM API response received in {generation_time:.2f} seconds")

            return {
                "response": data.get("response"),
                "model": data.get("model"),
                "tokens_used": len(data.get("response", "").split()),
                "generation_time": generation_time
            }
        except Exception as e:
            logging.error(f"LLM request failed: {e}")
            return None

############################################################
# Config callback function
############################################################
def config(configuration: Dict[str, ConfigClass], state: State) -> None:
    """Store user-specific configuration"""
    logging.info("Processing user-specific configurations.")
    for uid, conf in configuration.items():
        configurations[uid] = conf
        logging.info(f"Loaded config for user: {uid}")

############################################################
# Execution callback function
############################################################
def execute(model: AppModel) -> None:
    """Main execution entry point"""
    logging.info("Execution started.")

    # Get input and config
    request: InputClass = model.request
    logging.info(f"Received request with prompt: '{request.prompt[:50]}...'")  # Log first 50 characters of the prompt
    
    user_config: ConfigClass = configurations.get('super-user', ConfigClass())
    
    # Initialize components
    logging.info("Initializing Stub and LLMClient.")
    stub = Stub(user_config.app_ids)
    llm_client = LLMClient(user_config)
    
    # Generate LLM response
    llm_response = llm_client.generate(
        prompt=request.prompt,
        model=request.model,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
        stream=request.stream
    )
    
    # Prepare output
    response: OutputClass = model.response
    if llm_response:
        response.message = llm_response["response"]
        response.model = llm_response["model"]
        response.tokens_used = llm_response["tokens_used"]
        response.generation_time = llm_response["generation_time"]
        logging.info(f"LLM response generated successfully with {response.tokens_used} tokens used.")
    else:
        response.message = "Sorry, I couldn't process your request."
        logging.error("LLM response generation failed.")

    # Optional: Call other apps through stub if needed
    if user_config.app_ids:
        try:
            logging.info(f"Calling other apps through stub: {user_config.app_ids[0]}")
            stub_result = stub.call(user_config.app_ids[0], {"prompt": request.prompt})
            logging.info(f"Stub call result: {stub_result}")
        except Exception as e:
            logging.warning(f"Stub call failed: {e}")

    logging.info("Execution finished.")
