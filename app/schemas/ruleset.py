import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, model_validator

from app.schemas.base import Link, ResourceLinks, PaginationLinks
from app.schemas.rule import RuleResponse
from app.schemas.signature import SignatureTerm


def convert_signature_to_list(
    value: Optional[Union[List[Any], Dict[str, Any]]]
) -> Optional[List[SignatureTerm]]:
    if value is None:
        return None
    if isinstance(value, list):
        return [SignatureTerm(**item) if isinstance(item, dict) else item for item in value]
    if isinstance(value, dict):
        if len(value) == 0 or (len(value) == 1 and "additionalProp1" in value):
            return []
        return []
    return None


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

    model_config = {
        "from_attributes": True,
    }

    @model_validator(mode="before")
    @classmethod
    def convert_signature(cls, data: Any) -> Any:
        if isinstance(data, dict):
            signature = data.get("signature")
            if signature is not None and isinstance(signature, dict):
                data["signature"] = convert_signature_to_list(signature)
            return data
        elif hasattr(data, "signature"):
            signature = getattr(data, "signature", None)
            if signature is not None and isinstance(signature, dict):
                result = {}
                for key in ["id", "name", "ruleSetType", "description", "version", 
                           "is_locked", "created_by", "created_datetime", 
                           "modified_by", "modified_datetime", "rules"]:
                    if hasattr(data, key):
                        result[key] = getattr(data, key)
                result["signature"] = convert_signature_to_list(signature)
                return result
        return data


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
