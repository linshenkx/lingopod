from pydantic import BaseModel, ConfigDict
from typing import Any, Dict, Optional

class ConfigBase(BaseModel):
    value: Any
    type: str
    description: Optional[str] = None

class ConfigUpdate(ConfigBase):
    pass

class ConfigResponse(ConfigBase):
    key: str
    model_config = ConfigDict(from_attributes=True)

class ConfigListResponse(BaseModel):
    configs: Dict[str, ConfigResponse]