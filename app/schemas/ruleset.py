import uuid
from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, Field, field_validator

from app.schemas.base import Link, ResourceLinks, PaginationLinks
from app.schemas.rule import RuleResponse
from app.schemas.signature import SignatureTerm


class RuleSetBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    ruleSetType: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = Field(None, max_length=1000)
    signature: Optional[List[SignatureTerm]] = None


class RuleSetCreate(RuleSetBase):
    pass


class RuleSetUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    ruleSetType: Optional[str] = Field(None, min_length=1, max_length=50)
    description: Optional[str] = Field(None, max_length=1000)
    signature: Optional[List[SignatureTerm]] = None
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


class RuleSetDetailResponse(RuleSetResponseData):
    rules: List[RuleResponse]
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
