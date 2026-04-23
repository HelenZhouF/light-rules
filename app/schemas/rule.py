import uuid
from datetime import datetime
from typing import Any, List, Optional, Set

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.base import Link, ResourceLinks, PaginationLinks
from app.schemas.condition_action import (
    ConditionCreate,
    ConditionResponse,
    ActionCreate,
    ActionResponse,
    TermRef,
)


def convert_conditions_value(
    value: Optional[List[Any]]
) -> Optional[List[ConditionCreate]]:
    if value is None:
        return None
    if isinstance(value, list):
        return [ConditionCreate(**item) if isinstance(item, dict) else item for item in value]
    return None


def convert_actions_value(
    value: Optional[List[Any]]
) -> Optional[List[ActionCreate]]:
    if value is None:
        return None
    if isinstance(value, list):
        return [ActionCreate(**item) if isinstance(item, dict) else item for item in value]
    return None


def convert_conditions_response(
    value: Optional[List[Any]]
) -> Optional[List[ConditionResponse]]:
    if value is None:
        return None
    if isinstance(value, list):
        result = []
        for item in value:
            if isinstance(item, dict):
                result.append(ConditionResponse(**item))
            elif isinstance(item, ConditionResponse):
                result.append(item)
        return result
    return None


def convert_actions_response(
    value: Optional[List[Any]]
) -> Optional[List[ActionResponse]]:
    if value is None:
        return None
    if isinstance(value, list):
        result = []
        for item in value:
            if isinstance(item, dict):
                result.append(ActionResponse(**item))
            elif isinstance(item, ActionResponse):
                result.append(item)
        return result
    return None


def get_valid_term_names(signature: Optional[List[Any]]) -> Set[str]:
    valid_names = set()
    if signature:
        for term in signature:
            if isinstance(term, dict) and "name" in term:
                valid_names.add(term["name"])
    return valid_names


def validate_terms(
    conditions: Optional[List[ConditionCreate]],
    actions: Optional[List[ActionCreate]],
    valid_term_names: Set[str],
) -> List[str]:
    errors = []
    
    if conditions:
        for i, cond in enumerate(conditions):
            if cond.term and cond.term.name not in valid_term_names:
                errors.append(f"Condition[{i}]: term '{cond.term.name}' not found in ruleset signature")
    
    if actions:
        for i, action in enumerate(actions):
            if action.term and action.term.name not in valid_term_names:
                errors.append(f"Action[{i}]: term '{action.term.name}' not found in ruleset signature")
    
    return errors


class RuleBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    conditional: str
    order_index: int = Field(..., ge=0)


class RuleCreate(RuleBase):
    conditions: Optional[List[ConditionCreate]] = None
    actions: Optional[List[ActionCreate]] = None

    @field_validator("conditions", mode="before")
    @classmethod
    def validate_conditions(cls, value: Any) -> Any:
        return convert_conditions_value(value)

    @field_validator("actions", mode="before")
    @classmethod
    def validate_actions(cls, value: Any) -> Any:
        return convert_actions_value(value)


class RuleUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    conditional: Optional[str] = None
    order_index: Optional[int] = Field(None, ge=0)
    conditions: Optional[List[ConditionCreate]] = None
    actions: Optional[List[ActionCreate]] = None

    @field_validator("conditions", mode="before")
    @classmethod
    def validate_conditions(cls, value: Any) -> Any:
        return convert_conditions_value(value)

    @field_validator("actions", mode="before")
    @classmethod
    def validate_actions(cls, value: Any) -> Any:
        return convert_actions_value(value)


class RuleResponseData(BaseModel):
    name: str
    description: Optional[str]
    conditional: str
    order_index: int
    id: uuid.UUID
    rule_set_id: uuid.UUID
    conditions: Optional[List[ConditionResponse]] = None
    actions: Optional[List[ActionResponse]] = None
    created_by: Optional[str]
    created_datetime: datetime
    modified_by: Optional[str]
    modified_datetime: datetime

    @field_validator("conditions", mode="before")
    @classmethod
    def validate_conditions_response(cls, value: Any) -> Any:
        return convert_conditions_response(value)

    @field_validator("actions", mode="before")
    @classmethod
    def validate_actions_response(cls, value: Any) -> Any:
        return convert_actions_response(value)

    model_config = {
        "from_attributes": True,
    }


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
