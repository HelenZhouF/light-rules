import uuid
from datetime import datetime
from enum import Enum
from typing import Any, List, Optional

from pydantic import BaseModel, Field

from app.schemas.base import Link, ResourceLinks, PaginationLinks
from app.schemas.signature import SignatureTerm


class RevisionType(str, Enum):
    major = "major"
    minor = "minor"


class RevisionCreate(BaseModel):
    revisionType: RevisionType = Field(default=RevisionType.minor)


class RevisionBase(BaseModel):
    name: str
    ruleSetType: str
    description: Optional[str] = None
    signature: Optional[List[SignatureTerm]] = None
    major: int
    minor: int


class RevisionResponseData(RevisionBase):
    id: uuid.UUID
    rule_set_id: uuid.UUID
    is_locked: bool
    created_by: Optional[str]
    created_datetime: datetime
    modified_by: Optional[str]
    modified_datetime: datetime

    model_config = {
        "from_attributes": True,
    }


class RevisionResponse(RevisionResponseData):
    links: ResourceLinks = Field(..., alias="_links")

    model_config = {
        "populate_by_name": True,
        "by_alias": True,
        "exclude_none": True,
    }


class RevisionListResponse(BaseModel):
    items: List[RevisionResponse]
    links: PaginationLinks = Field(..., alias="_links")
    total: int
    skip: int
    limit: int

    model_config = {
        "populate_by_name": True,
        "by_alias": True,
        "exclude_none": True,
    }
