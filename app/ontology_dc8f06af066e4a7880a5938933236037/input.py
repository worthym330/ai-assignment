from decimal import *
from datetime import *
from typing import *

from dataclasses import dataclass
from marshmallow import Schema, fields, post_load
from openfabric_pysdk.utility import SchemaUtil

@dataclass
class InputClass:
    prompt: str = None
    attachments: List[str] = None
    model: str = None
    temperature: float = 0.7
    max_tokens: int = 512
    stream: bool = False

class InputClassSchema(Schema):
    prompt = fields.String(required=True)
    attachments = fields.List(fields.String(), allow_none=True)
    model = fields.String(allow_none=True, missing=None)
    temperature = fields.Float(allow_none=True, missing=0.7)
    max_tokens = fields.Integer(allow_none=True, missing=512)
    stream = fields.Boolean(allow_none=True, missing=False)

    @post_load
    def create(self, data, **kwargs):
        return SchemaUtil.create(InputClass(), data)