import logging
from dataclasses import dataclass
from typing import List, Optional
from marshmallow import Schema, fields, post_load
from openfabric_pysdk.utility import SchemaUtil

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ConfigClass:
    app_ids: Optional[List[str]] = None
    llm_endpoint: str = "http://localhost:11434/api/generate"  # Default value
    default_model: str = "llama3"  # Default value
    max_response_tokens: int = 1024  # Default value
    timeout: float = 30.0  # Default value

class ConfigClassSchema(Schema):
    app_ids = fields.List(fields.String(), allow_none=True)
    llm_endpoint = fields.String(required=False, missing="http://localhost:11434/api/generate")
    default_model = fields.String(required=False, missing="llama3")
    max_response_tokens = fields.Integer(required=False, missing=1024)
    timeout = fields.Float(required=False, missing=30.0)

    @post_load
    def create(self, data, **kwargs):
        """Post-load method to convert schema data into a ConfigClass object."""
        logger.info(f"Processing data for ConfigClass creation: {data}")
        config_instance = SchemaUtil.create(ConfigClass(), data)
        logger.info(f"Created ConfigClass instance: {config_instance}")
        return config_instance
