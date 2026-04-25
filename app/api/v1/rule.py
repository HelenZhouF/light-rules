import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.schemas.rule import (
    RuleCreate,
    RuleUpdate,
    RuleResponse,
    RuleResponseData,
    RuleListResponse,
    validate_terms,
    convert_conditions_with_signature,
    convert_actions_with_signature,
)
from app.crud import (
    get_ruleset_by_id,
)
from app.crud.rule import (
    get_rule_by_id,
    get_rule_by_id_with_ruleset,
    get_rule_by_name_and_ruleset,
    get_rule_by_order_index_and_ruleset,
    get_rules_by_ruleset_id,
    count_rules_by_ruleset,
    create_rule,
    update_rule,
    delete_rule,
    process_conditions_for_storage,
    process_actions_for_storage,
)
from app.utils.hateoas import build_rule_links, build_rule_pagination_links

router = APIRouter(prefix="/rulesets/{ruleset_id}/rules", tags=["rules"])


def rule_to_response(rule, signature: Optional[List[Any]], ruleset_is_locked: bool) -> dict:
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
    links = build_rule_links(rule.rule_set_id, rule.id, ruleset_is_locked)
    response = RuleResponse(**data.model_dump(), _links=links)
    return response.model_dump(by_alias=True, exclude_none=True)


@router.get("/", response_model=dict, status_code=status.HTTP_200_OK)
async def read_rules(
    ruleset_id: uuid.UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_async_session),
):
    ruleset = await get_ruleset_by_id(db, ruleset_id=ruleset_id)
    if ruleset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="RuleSet not found",
        )
    
    total = await count_rules_by_ruleset(db, rule_set_id=ruleset_id)
    rules = await get_rules_by_ruleset_id(db, rule_set_id=ruleset_id, skip=skip, limit=limit)
    
    items = [rule_to_response(r, ruleset.signature, ruleset.is_locked) for r in rules]
    pagination_links = build_rule_pagination_links(ruleset_id, skip, limit, total)
    
    response = RuleListResponse(
        items=[],
        _links=pagination_links,
        total=total,
        skip=skip,
        limit=limit,
    )
    result = response.model_dump(by_alias=True, exclude_none=True)
    result["items"] = items
    return result


@router.get("/{rule_id}", response_model=dict, status_code=status.HTTP_200_OK)
async def read_rule(
    ruleset_id: uuid.UUID,
    rule_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_session),
):
    rule = await get_rule_by_id_with_ruleset(db, rule_id=rule_id)
    if rule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rule not found",
        )
    
    if rule.rule_set_id != ruleset_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rule not found in this RuleSet",
        )
    
    return rule_to_response(rule, rule.ruleset.signature, rule.ruleset.is_locked)


@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_new_rule(
    ruleset_id: uuid.UUID,
    rule_in: RuleCreate,
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
    
    validation_errors = validate_terms(rule_in.conditions, rule_in.actions, ruleset.signature)
    if validation_errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="; ".join(validation_errors),
        )
    
    existing_rule_by_name = await get_rule_by_name_and_ruleset(
        db, name=rule_in.name, rule_set_id=ruleset_id
    )
    if existing_rule_by_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rule with this name already exists in this RuleSet",
        )
    
    if rule_in.order_index is not None:
        existing_rule_by_order = await get_rule_by_order_index_and_ruleset(
            db, order_index=rule_in.order_index, rule_set_id=ruleset_id
        )
        if existing_rule_by_order:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Rule with this order_index already exists in this RuleSet",
            )
    
    rule = await create_rule(
        db=db, 
        rule_in=rule_in, 
        rule_set_id=ruleset_id,
        signature=ruleset.signature,
    )
    return rule_to_response(rule, ruleset.signature, ruleset.is_locked)


@router.put("/{rule_id}", response_model=dict, status_code=status.HTTP_200_OK)
async def update_existing_rule(
    ruleset_id: uuid.UUID,
    rule_id: uuid.UUID,
    rule_in: RuleUpdate,
    db: AsyncSession = Depends(get_async_session),
):
    rule = await get_rule_by_id_with_ruleset(db, rule_id=rule_id)
    if rule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rule not found",
        )
    
    if rule.rule_set_id != ruleset_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rule not found in this RuleSet",
        )
    
    if rule.ruleset.is_locked:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="RuleSet is locked and cannot be modified",
        )
    
    if rule_in.conditions is not None or rule_in.actions is not None:
        validation_errors = validate_terms(rule_in.conditions, rule_in.actions, rule.ruleset.signature)
        if validation_errors:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="; ".join(validation_errors),
            )
    
    if rule_in.name and rule_in.name != rule.name:
        existing_rule_by_name = await get_rule_by_name_and_ruleset(
            db, name=rule_in.name, rule_set_id=ruleset_id
        )
        if existing_rule_by_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Rule with this name already exists in this RuleSet",
            )
    
    if rule_in.order_index is not None and rule_in.order_index != rule.order_index:
        existing_rule_by_order = await get_rule_by_order_index_and_ruleset(
            db, order_index=rule_in.order_index, rule_set_id=ruleset_id
        )
        if existing_rule_by_order:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Rule with this order_index already exists in this RuleSet",
            )
    
    updated_rule = await update_rule(
        db=db,
        rule_id=rule_id,
        rule_in=rule_in,
        signature=rule.ruleset.signature,
    )
    return rule_to_response(updated_rule, rule.ruleset.signature, rule.ruleset.is_locked)


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_existing_rule(
    ruleset_id: uuid.UUID,
    rule_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_session),
):
    rule = await get_rule_by_id_with_ruleset(db, rule_id=rule_id)
    if rule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rule not found",
        )
    
    if rule.rule_set_id != ruleset_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rule not found in this RuleSet",
        )
    
    if rule.ruleset.is_locked:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="RuleSet is locked and cannot be modified",
        )
    
    await delete_rule(db=db, rule_id=rule_id)
    return None
