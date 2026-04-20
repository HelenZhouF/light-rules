import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


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


class RuleSetResponse(RuleSetBase):
    id: uuid.UUID
    version: int
    is_locked: bool
    created_by: Optional[str]
    created_datetime: datetime
    modified_by: Optional[str]
    modified_datetime: datetime

    class Config:
        from_attributes = True
