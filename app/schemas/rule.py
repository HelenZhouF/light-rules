import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.base import Link, ResourceLinks, PaginationLinks
from app.schemas.condition_action import (
    ConditionCreate,
    ConditionResponse,
    ActionCreate,
    ActionResponse,
    TermRef,
    TermRefResponse,
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


def _term_to_dict(term: Any) -> Optional[Dict[str, Any]]:
    if isinstance(term, dict):
        return term
    if isinstance(term, BaseModel):
        return term.model_dump()
    return None


def get_valid_term_names(signature: Optional[List[Any]]) -> Set[str]:
    valid_names = set()
    if signature:
        for term in signature:
            term_dict = _term_to_dict(term)
            if term_dict and "name" in term_dict:
                valid_names.add(term_dict["name"])
    return valid_names


def build_signature_term_maps(
    signature: Optional[List[Any]]
) -> Tuple[Dict[uuid.UUID, Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    terms_by_id: Dict[uuid.UUID, Dict[str, Any]] = {}
    terms_by_name: Dict[str, Dict[str, Any]] = {}
    
    if signature:
        for term in signature:
            term_dict = _term_to_dict(term)
            if term_dict:
                if "id" in term_dict:
                    try:
                        term_id = uuid.UUID(str(term_dict["id"]))
                        terms_by_id[term_id] = term_dict
                    except (ValueError, TypeError):
                        pass
                if "name" in term_dict:
                    terms_by_name[term_dict["name"]] = term_dict
    
    return terms_by_id, terms_by_name


def find_term_in_signature(
    term_ref: TermRef,
    terms_by_id: Dict[uuid.UUID, Dict[str, Any]],
    terms_by_name: Dict[str, Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    if term_ref.termId and term_ref.termId in terms_by_id:
        return terms_by_id[term_ref.termId]
    if term_ref.name and term_ref.name in terms_by_name:
        return terms_by_name[term_ref.name]
    return None


def get_term_identifier(term_ref: TermRef) -> str:
    if term_ref.termId:
        return str(term_ref.termId)
    if term_ref.name:
        return term_ref.name
    return "unknown"


def validate_terms(
    conditions: Optional[List[ConditionCreate]],
    actions: Optional[List[ActionCreate]],
    signature_or_valid_names: Any,
) -> List[str]:
    errors = []
    
    if isinstance(signature_or_valid_names, set):
        valid_names = signature_or_valid_names
        if conditions:
            for i, cond in enumerate(conditions):
                if cond.term and cond.term.name and cond.term.name not in valid_names:
                    errors.append(f"Condition[{i}]: term '{cond.term.name}' not found in ruleset signature")
        
        if actions:
            for i, action in enumerate(actions):
                if action.term and action.term.name and action.term.name not in valid_names:
                    errors.append(f"Action[{i}]: term '{action.term.name}' not found in ruleset signature")
    else:
        signature = signature_or_valid_names
        terms_by_id, terms_by_name = build_signature_term_maps(signature)
        
        if conditions:
            for i, cond in enumerate(conditions):
                if cond.term:
                    term = find_term_in_signature(cond.term, terms_by_id, terms_by_name)
                    if term is None:
                        identifier = get_term_identifier(cond.term)
                        errors.append(f"Condition[{i}]: term '{identifier}' not found in ruleset signature")
        
        if actions:
            for i, action in enumerate(actions):
                if action.term:
                    term = find_term_in_signature(action.term, terms_by_id, terms_by_name)
                    if term is None:
                        identifier = get_term_identifier(action.term)
                        errors.append(f"Action[{i}]: term '{identifier}' not found in ruleset signature")
    
    return errors


def resolve_term_for_storage(
    term_ref: TermRef,
    terms_by_id: Dict[uuid.UUID, Dict[str, Any]],
    terms_by_name: Dict[str, Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    term = find_term_in_signature(term_ref, terms_by_id, terms_by_name)
    if term is None:
        return None
    
    term_id = term.get("id")
    if term_id:
        return {"termId": str(term_id)}
    return {"name": term.get("name")}


def build_term_ref_response(
    term_ref_data: Dict[str, Any],
    terms_by_id: Dict[uuid.UUID, Dict[str, Any]],
    terms_by_name: Dict[str, Dict[str, Any]],
) -> TermRefResponse:
    term_ref = TermRef(
        termId=term_ref_data.get("termId"),
        name=term_ref_data.get("name"),
    )
    term = find_term_in_signature(term_ref, terms_by_id, terms_by_name)
    if term:
        return TermRefResponse(**term)
    
    term_id = term_ref_data.get("termId")
    if term_id:
        try:
            term_id = uuid.UUID(str(term_id))
        except (ValueError, TypeError):
            term_id = None
    
    return TermRefResponse(
        id=term_id,
        name=term_ref_data.get("name"),
    )


def convert_conditions_with_signature(
    conditions: Optional[List[Any]],
    signature: Optional[List[Any]],
) -> Optional[List[ConditionResponse]]:
    if conditions is None:
        return None
    if not isinstance(conditions, list):
        return None
    
    terms_by_id, terms_by_name = build_signature_term_maps(signature)
    result = []
    
    for item in conditions:
        if not isinstance(item, dict):
            continue
        
        item_copy = dict(item)
        term_ref_data = item_copy.get("term")
        
        if isinstance(term_ref_data, dict):
            item_copy["term"] = build_term_ref_response(
                term_ref_data, terms_by_id, terms_by_name
            )
        
        result.append(ConditionResponse(**item_copy))
    
    return result


def convert_actions_with_signature(
    actions: Optional[List[Any]],
    signature: Optional[List[Any]],
) -> Optional[List[ActionResponse]]:
    if actions is None:
        return None
    if not isinstance(actions, list):
        return None
    
    terms_by_id, terms_by_name = build_signature_term_maps(signature)
    result = []
    
    for item in actions:
        if not isinstance(item, dict):
            continue
        
        item_copy = dict(item)
        term_ref_data = item_copy.get("term")
        
        if isinstance(term_ref_data, dict):
            item_copy["term"] = build_term_ref_response(
                term_ref_data, terms_by_id, terms_by_name
            )
        
        result.append(ActionResponse(**item_copy))
    
    return result


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
