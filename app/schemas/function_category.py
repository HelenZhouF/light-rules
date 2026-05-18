import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.base import Link, ResourceLinks, PaginationLinks


class FunctionCategoryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    hidden: Optional[bool] = False


class FunctionCategoryCreate(FunctionCategoryBase):
    pass


class FunctionCategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    hidden: Optional[bool] = None


class FunctionCategoryResponseData(FunctionCategoryBase):
    id: uuid.UUID
    version: int
    created_by: Optional[str]
    creationTimeStamp: datetime = Field(..., validation_alias="created_datetime")
    modified_by: Optional[str]
    modifiedTimeStamp: datetime = Field(..., validation_alias="modified_datetime")

    model_config = {
        "from_attributes": True,
    }


class FunctionCategoryResponse(FunctionCategoryResponseData):
    links: ResourceLinks = Field(..., alias="_links")

    model_config = {
        "populate_by_name": True,
        "by_alias": True,
        "exclude_none": True,
    }


class FunctionCategoryListResponse(BaseModel):
    items: list[FunctionCategoryResponse]
    links: PaginationLinks = Field(..., alias="_links")
    total: int
    skip: int
    limit: int

    model_config = {
        "populate_by_name": True,
        "by_alias": True,
        "exclude_none": True,
    }
