import uuid
from datetime import datetime
from typing import Dict, List, Optional, Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.base import Link, ResourceLinks, PaginationLinks


class LookupBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


class LookupCreate(LookupBase):
    pass


class LookupUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)


class LookupEntryBase(BaseModel):
    key: str = Field(..., min_length=1, max_length=255)
    value: str = Field(..., min_length=1, max_length=1000)


class LookupEntryCreate(LookupEntryBase):
    pass


class LookupEntryUpdate(BaseModel):
    key: Optional[str] = Field(None, min_length=1, max_length=255)
    value: Optional[str] = Field(None, min_length=1, max_length=1000)


class LookupEntryResponse(LookupEntryBase):
    model_config = {
        "from_attributes": True,
    }


class LookupResponseData(LookupBase):
    id: uuid.UUID
    created_by: Optional[str]
    created_datetime: datetime
    modified_by: Optional[str]
    modified_datetime: datetime

    model_config = {
        "from_attributes": True,
    }


class LookupResponse(LookupResponseData):
    links: ResourceLinks = Field(..., alias="_links")

    model_config = {
        "populate_by_name": True,
        "by_alias": True,
        "exclude_none": True,
    }


class LookupDetailResponse(LookupResponseData):
    entries: List[LookupEntryResponse]
    links: ResourceLinks = Field(..., alias="_links")

    model_config = {
        "populate_by_name": True,
        "by_alias": True,
        "exclude_none": True,
    }


class LookupListResponse(BaseModel):
    items: List[LookupResponse]
    links: PaginationLinks = Field(..., alias="_links")
    total: int
    skip: int
    limit: int

    model_config = {
        "populate_by_name": True,
        "by_alias": True,
        "exclude_none": True,
    }


class JsonPatchOperation(BaseModel):
    op: Literal["add", "replace", "remove"]
    path: str = Field(..., min_length=1)
    value: Optional[str] = Field(None, max_length=1000)

    @field_validator("path")
    @classmethod
    def validate_path(cls, v: str) -> str:
        if not v.startswith("/"):
            raise ValueError("path must start with /")
        if len(v) < 2:
            raise ValueError("path must contain a key after /")
        return v

    @field_validator("value")
    @classmethod
    def validate_value_for_op(cls, v: Optional[str], info) -> Optional[str]:
        op = info.data.get("op")
        if op in ["add", "replace"] and v is None:
            raise ValueError(f"value is required for op: {op}")
        return v


class LookupEntryListResponse(BaseModel):
    items: List[LookupEntryResponse]
    links: PaginationLinks = Field(..., alias="_links")
    total: int
    skip: int
    limit: int

    model_config = {
        "populate_by_name": True,
        "by_alias": True,
        "exclude_none": True,
    }


class LookupEntriesBatchCreate(BaseModel):
    entries: List[LookupEntryCreate] = Field(..., min_length=1)


class LookupEntriesBatchUpdate(BaseModel):
    entries: List[LookupEntryCreate] = Field(..., min_length=1)
