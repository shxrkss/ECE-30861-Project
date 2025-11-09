from pydantic import BaseModel
from typing import Optional

class ModelMetadata(BaseModel):
    name: str
    key: str
    size: int
    last_modified: str
    version: Optional[str] = "v1.0.0"