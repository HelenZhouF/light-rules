import uuid
from typing import Any, List, Optional

from pydantic import BaseModel, Field


class OrderRequest(BaseModel):
    type: str = Field(..., description="Type of resource identifier, should be 'id'")
    template: str = Field(..., description="URL template for the resource")
    resources: List[str] = Field(..., description="List of rule IDs in the desired order")


class OrderResponse(BaseModel):
    type: str
    template: str
    resources: List[str]
    message: Optional[str] = None

    model_config = {
        "from_attributes": True,
    }
