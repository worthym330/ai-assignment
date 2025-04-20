import logging
from dataclasses import dataclass
from typing import Optional
from marshmallow import Schema, fields, post_load
from openfabric_pysdk.utility import SchemaUtil

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class OutputClass:
    message: str = None
    model: Optional[str] = None
    tokens_used: Optional[int] = None
    generation_time: Optional[float] = None
    is_complete: bool = True

class OutputClassSchema(Schema):
    message = fields.String(allow_none=True, missing=None)
    model = fields.String(allow_none=True, missing=None)
    tokens_used = fields.Integer(allow_none=True)
    generation_time = fields.Float(allow_none=True)
    is_complete = fields.Boolean(allow_none=True)

    @post_load
    def create(self, data, **kwargs):
        """Post-load method to convert schema data into an OutputClass object."""
        logger.info(f"Processing data for OutputClass creation: {data}")
        output_instance = SchemaUtil.create(OutputClass(), data)
        logger.info(f"Created OutputClass instance: {output_instance}")
        return output_instance
