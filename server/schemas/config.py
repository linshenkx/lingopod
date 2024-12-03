from pydantic import BaseModel
from typing import Any, Dict, Optional

class ConfigBase(BaseModel):
    value: Any
    type: str
    description: Optional[str] = None

class ConfigUpdate(ConfigBase):
    pass

class ConfigResponse(ConfigBase):
    key: str

    class Config:
        from_attributes = True

class ConfigListResponse(BaseModel):
    configs: Dict[str, ConfigResponse] 