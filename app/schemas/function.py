import re
import uuid
from datetime import datetime
from typing import Optional, List, Any, Tuple

from pydantic import BaseModel, Field, field_validator
from pydantic_core import PydanticCustomError

from app.schemas.base import Link, ResourceLinks, PaginationLinks


class FunctionParameter(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    type: str = Field(..., min_length=1, max_length=50)
    inOut: Optional[bool] = False


def parse_ds2_signature(code: str) -> Tuple[Optional[List[FunctionParameter]], Optional[str]]:
    try:
        first_semicolon = code.find(';')
        if first_semicolon != -1:
            declaration = code[:first_semicolon]
        else:
            declaration = code
        
        method_match = re.search(
            r'method\s+(\w+)\s*\((.*?)\)\s*(?:returns\s+(\w+))?',
            declaration,
            re.IGNORECASE
        )
        if not method_match:
            return None, None
        
        params_str = method_match.group(2).strip()
        return_type = method_match.group(3)
        
        if not params_str:
            return [], return_type
        
        params = []
        for param_str in params_str.split(','):
            param_str = param_str.strip()
            if not param_str:
                continue
            
            is_inout = False
            param_lower = param_str.lower()
            if param_lower.startswith('inout '):
                is_inout = True
                param_str = param_str[6:].strip()
            elif param_lower.startswith('out '):
                is_inout = True
                param_str = param_str[4:].strip()
            
            parts = param_str.split()
            if len(parts) >= 2:
                param_type = parts[0]
                param_name = parts[1]
                params.append(FunctionParameter(name=param_name, type=param_type, inOut=is_inout))
        
        return params, return_type
    except Exception:
        return None, None


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
