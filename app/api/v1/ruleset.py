import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.schemas.ruleset import (
    RuleSetCreate,
    RuleSetUpdate,
    RuleSetResponse,
    RuleSetResponseData,
    RuleSetListResponse,
    RuleSetDetailResponse,
)
from app.schemas.rule import (
    RuleResponse,
    RuleResponseData,
    convert_conditions_with_signature,
    convert_actions_with_signature,
)
from app.crud import (
    get_ruleset_by_id,
    get_ruleset_by_name,
    get_rulesets,
    count_rulesets,
    create_ruleset,
    update_ruleset,
    delete_ruleset,
)
from app.crud.rule import get_ruleset_with_rules
from app.utils.hateoas import build_ruleset_links, build_pagination_links, build_rule_links

router = APIRouter(prefix="/rulesets", tags=["rulesets"])


def ruleset_to_response(ruleset) -> dict:
    data = RuleSetResponseData.model_validate(ruleset)
    links = build_ruleset_links(ruleset.id, ruleset.is_locked)
    response = RuleSetResponse(**data.model_dump(), _links=links)
    return response.model_dump(by_alias=True, exclude_none=True)


def rule_to_response_with_signature(rule, signature, ruleset_id, ruleset_is_locked: bool) -> dict:
    conditions = convert_conditions_with_signature(rule.conditions, signature)
    actions = convert_actions_with_signature(rule.actions, signature)
    
    data_dict = {
        "name": rule.name,
        "description": rule.description,
        "conditional": rule.conditional,
        "order_index": rule.order_index,
        "id": rule.id,
        "rule_set_id": rule.rule_set_id,
        "conditions": conditions,
        "actions": actions,
        "created_by": rule.created_by,
        "created_datetime": rule.created_datetime,
        "modified_by": rule.modified_by,
        "modified_datetime": rule.modified_datetime,
    }
    
    data = RuleResponseData(**data_dict)
    links = build_rule_links(ruleset_id, rule.id, ruleset_is_locked)
    response = RuleResponse(**data.model_dump(), _links=links)
    return response.model_dump(by_alias=True, exclude_none=True)


def ruleset_to_detail_response(ruleset) -> dict:
    data = RuleSetResponseData.model_validate(ruleset)
    links = build_ruleset_links(ruleset.id, ruleset.is_locked)
    
    rules_responses = []
    for rule in ruleset.rules:
        rule_response = rule_to_response_with_signature(
            rule, 
            ruleset.signature, 
            ruleset.id, 
            ruleset.is_locked
        )
        rules_responses.append(rule_response)
    
    response = RuleSetDetailResponse(
        **data.model_dump(),
        rules=rules_responses,
        _links=links,
    )
    return response.model_dump(by_alias=True, exclude_none=True)


@router.get("/", response_model=dict, status_code=status.HTTP_200_OK)
async def read_rulesets(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_async_session),
):
    total = await count_rulesets(db)
    rulesets = await get_rulesets(db, skip=skip, limit=limit)
    
    items = [ruleset_to_response(r) for r in rulesets]
    pagination_links = build_pagination_links(skip, limit, total)
    
    response = RuleSetListResponse(
        items=[],
        _links=pagination_links,
        total=total,
        skip=skip,
        limit=limit,
    )
    result = response.model_dump(by_alias=True, exclude_none=True)
    result["items"] = items
    return result


@router.get("/{ruleset_id}", response_model=dict, status_code=status.HTTP_200_OK)
async def read_ruleset(
    ruleset_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_session),
):
    ruleset = await get_ruleset_with_rules(db, ruleset_id=ruleset_id)
    if ruleset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="RuleSet not found",
        )
    return ruleset_to_detail_response(ruleset)


@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_new_ruleset(
    ruleset_in: RuleSetCreate,
    db: AsyncSession = Depends(get_async_session),
):
    existing_ruleset = await get_ruleset_by_name(db, name=ruleset_in.name)
    if existing_ruleset:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="RuleSet with this name already exists",
        )
    
    ruleset = await create_ruleset(db=db, ruleset_in=ruleset_in)
    return ruleset_to_response(ruleset)


@router.put("/{ruleset_id}", response_model=dict, status_code=status.HTTP_200_OK)
async def update_existing_ruleset(
    ruleset_id: uuid.UUID,
    ruleset_in: RuleSetUpdate,
    db: AsyncSession = Depends(get_async_session),
):
    ruleset = await get_ruleset_by_id(db, ruleset_id=ruleset_id)
    if ruleset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="RuleSet not found",
        )
    
    if ruleset.is_locked:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="RuleSet is locked and cannot be modified",
        )
    
    if ruleset_in.name and ruleset_in.name != ruleset.name:
        existing_ruleset = await get_ruleset_by_name(db, name=ruleset_in.name)
        if existing_ruleset:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="RuleSet with this name already exists",
            )
    
    updated_ruleset = await update_ruleset(
        db=db,
        ruleset_id=ruleset_id,
        ruleset_in=ruleset_in,
    )
    return ruleset_to_response(updated_ruleset)


@router.delete("/{ruleset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_existing_ruleset(
    ruleset_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_session),
):
    ruleset = await get_ruleset_by_id(db, ruleset_id=ruleset_id)
    if ruleset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="RuleSet not found",
        )
    
    if ruleset.is_locked:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="RuleSet is locked and cannot be deleted",
        )
    
    await delete_ruleset(db=db, ruleset_id=ruleset_id)
    return None
