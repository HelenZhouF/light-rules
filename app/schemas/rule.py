import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.schemas.base import Link, ResourceLinks, PaginationLinks


class RuleBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    conditional: Dict[str, Any]
    order_index: int = Field(..., ge=0)


class RuleCreate(RuleBase):
    pass


class RuleUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    conditional: Optional[Dict[str, Any]] = None
    order_index: Optional[int] = Field(None, ge=0)


class RuleResponseData(RuleBase):
    id: uuid.UUID
    rule_set_id: uuid.UUID
    created_by: Optional[str]
    created_datetime: datetime
    modified_by: Optional[str]
    modified_datetime: datetime

    class Config:
        from_attributes = True


class RuleResponse(RuleResponseData):
    links: ResourceLinks = Field(..., alias="_links")

    model_config = {
        "populate_by_name": True,
        "by_alias": True,
        "exclude_none": True,
    }


class RuleListResponse(BaseModel):
    items: List[RuleResponse]
    links: PaginationLinks = Field(..., alias="_links")
    total: int
    skip: int
    limit: int

    model_config = {
        "populate_by_name": True,
        "by_alias": True,
        "exclude_none": True,
    }
