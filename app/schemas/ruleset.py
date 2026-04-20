import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Link(BaseModel):
    href: str
    method: str = "GET"


class ResourceLinks(BaseModel):
    self: Link
    update: Optional[Link] = None
    delete: Optional[Link] = None

    model_config = {
        "exclude_none": True,
    }


class PaginationLinks(BaseModel):
    self: Link
    next: Optional[Link] = None
    prev: Optional[Link] = None
    first: Link

    model_config = {
        "exclude_none": True,
    }


class RuleSetBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    ruleSetType: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = Field(None, max_length=1000)
    signature: Optional[Dict[str, Any]] = None


class RuleSetCreate(RuleSetBase):
    pass


class RuleSetUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    ruleSetType: Optional[str] = Field(None, min_length=1, max_length=50)
    description: Optional[str] = Field(None, max_length=1000)
    signature: Optional[Dict[str, Any]] = None
    is_locked: Optional[bool] = None


class RuleSetResponseData(RuleSetBase):
    id: uuid.UUID
    version: int
    is_locked: bool
    created_by: Optional[str]
    created_datetime: datetime
    modified_by: Optional[str]
    modified_datetime: datetime

    class Config:
        from_attributes = True


class RuleSetResponse(RuleSetResponseData):
    links: ResourceLinks = Field(..., alias="_links")

    model_config = {
        "populate_by_name": True,
        "by_alias": True,
        "exclude_none": True,
    }


class RuleSetListResponse(BaseModel):
    items: List[RuleSetResponse]
    links: PaginationLinks = Field(..., alias="_links")
    total: int
    skip: int
    limit: int

    model_config = {
        "populate_by_name": True,
        "by_alias": True,
        "exclude_none": True,
    }
