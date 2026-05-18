import uuid
from datetime import datetime
from typing import Optional, List, Any

from pydantic import BaseModel, Field, field_validator
from pydantic_core import PydanticCustomError

from app.schemas.base import Link, ResourceLinks, PaginationLinks


class FunctionParameter(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    type: str = Field(..., min_length=1, max_length=50)
    inOut: Optional[bool] = False


def convert_signature_value(
    value: Optional[List[Any]]
) -> Optional[List[FunctionParameter]]:
    if value is None:
        return None
    if isinstance(value, list):
        return [FunctionParameter(**item) if isinstance(item, dict) else item for item in value]
    return None


def validate_signature_field(
    value: Optional[List[Any]]
) -> Optional[List[FunctionParameter]]:
    if value is None:
        return None
    if isinstance(value, list):
        return [FunctionParameter(**item) if isinstance(item, dict) else item for item in value]
    raise PydanticCustomError(
        "list_type",
        "Input should be a valid list",
        {"input": value}
    )


class FunctionBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    code: str = Field(..., min_length=1)
    returnType: str = Field(..., min_length=1, max_length=50)
    signature: Optional[List[FunctionParameter]] = None
    hidden: Optional[bool] = False

    @field_validator("signature", mode="before")
    @classmethod
    def validate_signature(cls, value: Any) -> Any:
        return validate_signature_field(value)


class FunctionCreate(FunctionBase):
    pass


class FunctionUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    code: Optional[str] = Field(None, min_length=1)
    returnType: Optional[str] = Field(None, min_length=1, max_length=50)
    signature: Optional[List[FunctionParameter]] = None
    hidden: Optional[bool] = None

    @field_validator("signature", mode="before")
    @classmethod
    def validate_signature(cls, value: Any) -> Any:
        return validate_signature_field(value)


class FunctionResponseData(FunctionBase):
    id: uuid.UUID
    categoryId: uuid.UUID = Field(..., validation_alias="category_id")
    version: int
    created_by: Optional[str]
    creationTimeStamp: datetime = Field(..., validation_alias="created_datetime")
    modified_by: Optional[str]
    modifiedTimeStamp: datetime = Field(..., validation_alias="modified_datetime")

    model_config = {
        "from_attributes": True,
    }


class FunctionResponse(FunctionResponseData):
    links: ResourceLinks = Field(..., alias="_links")

    model_config = {
        "populate_by_name": True,
        "by_alias": True,
        "exclude_none": True,
    }


class FunctionListResponse(BaseModel):
    items: list[FunctionResponse]
    links: PaginationLinks = Field(..., alias="_links")
    total: int
    skip: int
    limit: int

    model_config = {
        "populate_by_name": True,
        "by_alias": True,
        "exclude_none": True,
    }
