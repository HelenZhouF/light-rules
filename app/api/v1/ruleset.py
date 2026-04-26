import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import PlainTextResponse
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
from app.schemas.revision import (
    RevisionType,
    RevisionResponse,
    RevisionResponseData,
    RevisionListResponse,
)
from app.schemas.execution import (
    ExecutionRequest,
    ExecutionResponse,
    RuleExecutionResult,
    ConditionExecutionResult,
    ActionExecutionResult,
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
from app.crud.ruleset import (
    get_revisions,
    get_revision_by_id,
    count_revisions,
    create_revision,
)
from app.crud.rule import (
    get_ruleset_with_rules,
    get_rules_order,
    update_rules_order,
)
from app.crud.lookup import get_lookup_with_entries

from app.schemas.order import OrderRequest, OrderResponse
from app.services.execution import execute_ruleset as execute_ruleset_service
from app.services.code_generator import generate_ruleset_function, generate_ruleset_metadata
from app.utils.hateoas import (
    build_ruleset_links,
    build_pagination_links,
    build_rule_links,
    build_revision_links,
    build_revision_pagination_links,
)

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
        rules=[],
        _links=links,
    )
    result = response.model_dump(by_alias=True, exclude_none=True)
    result["rules"] = rules_responses
    return result


def revision_to_response(ruleset_id: uuid.UUID, revision) -> dict:
    data = RevisionResponseData.model_validate(revision)
    links = build_revision_links(ruleset_id, revision.id, revision.is_locked)
    response = RevisionResponse(**data.model_dump(), _links=links)
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


@router.get("/{ruleset_id}/revisions", response_model=dict, status_code=status.HTTP_200_OK)
async def read_revisions(
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
    
    total = await count_revisions(db, ruleset_id=ruleset_id)
    revisions = await get_revisions(db, ruleset_id=ruleset_id, skip=skip, limit=limit)
    
    items = [revision_to_response(ruleset_id, r) for r in revisions]
    pagination_links = build_revision_pagination_links(ruleset_id, skip, limit, total)
    
    response = RevisionListResponse(
        items=[],
        _links=pagination_links,
        total=total,
        skip=skip,
        limit=limit,
    )
    result = response.model_dump(by_alias=True, exclude_none=True)
    result["items"] = items
    return result


@router.get("/{ruleset_id}/revisions/{revision_id}", response_model=dict, status_code=status.HTTP_200_OK)
async def read_revision(
    ruleset_id: uuid.UUID,
    revision_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_session),
):
    ruleset = await get_ruleset_by_id(db, ruleset_id=ruleset_id)
    if ruleset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="RuleSet not found",
        )
    
    revision = await get_revision_by_id(db, ruleset_id=ruleset_id, revision_id=revision_id)
    if revision is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Revision not found",
        )
    
    return revision_to_response(ruleset_id, revision)


@router.post("/{ruleset_id}/revisions", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_new_revision(
    ruleset_id: uuid.UUID,
    revisionType: RevisionType = Query(default=RevisionType.minor, description="Version type: major or minor"),
    ruleset_update: Optional[RuleSetUpdate] = None,
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
            detail="RuleSet is locked and cannot be versioned",
        )
    
    if ruleset_update and ruleset_update.name and ruleset_update.name != ruleset.name:
        existing_ruleset = await get_ruleset_by_name(db, name=ruleset_update.name)
        if existing_ruleset:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="RuleSet with this name already exists",
            )
    
    revision = await create_revision(
        db=db,
        ruleset_id=ruleset_id,
        revision_type=revisionType,
        ruleset_update=ruleset_update,
    )
    return revision_to_response(ruleset_id, revision)


def execution_result_to_response(result) -> dict:
    rule_results = []
    for rule_result in result.rules:
        condition_results = []
        for cond_result in rule_result.conditions:
            condition_results.append(ConditionExecutionResult(
                id=cond_result.condition_id,
                termName=cond_result.term_name,
                expression=cond_result.expression,
                result=cond_result.result,
                error=cond_result.error,
            ))
        
        action_results = []
        for action_result in rule_result.actions:
            action_results.append(ActionExecutionResult(
                id=action_result.action_id,
                termName=action_result.term_name,
                expression=action_result.expression,
                value=action_result.value,
                error=action_result.error,
            ))
        
        rule_results.append(RuleExecutionResult(
            id=rule_result.rule_id,
            name=rule_result.rule_name,
            orderIndex=rule_result.order_index,
            conditional=rule_result.conditional,
            conditionsPassed=rule_result.conditions_passed,
            conditions=condition_results,
            actions=action_results,
            error=rule_result.error,
        ))
    
    response = ExecutionResponse(
        success=result.success,
        output=result.output,
        rules=rule_results,
        error=result.error,
    )
    return response.model_dump(by_alias=True, exclude_none=True)


@router.post("/{ruleset_id}/execute", response_model=dict, status_code=status.HTTP_200_OK)
async def execute_ruleset_endpoint(
    ruleset_id: uuid.UUID,
    request: ExecutionRequest,
    db: AsyncSession = Depends(get_async_session),
):
    ruleset = await get_ruleset_by_id(db, ruleset_id=ruleset_id)
    if ruleset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="RuleSet not found",
        )
    
    result = await execute_ruleset_service(
        db=db,
        ruleset_id=ruleset_id,
        input_data=request.input,
    )
    
    if not result.success and result.error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.error,
        )
    
    return execution_result_to_response(result)


@router.post("/{ruleset_id}/revisions/{revision_id}/execute", response_model=dict, status_code=status.HTTP_200_OK)
async def execute_revision_endpoint(
    ruleset_id: uuid.UUID,
    revision_id: uuid.UUID,
    request: ExecutionRequest,
    db: AsyncSession = Depends(get_async_session),
):
    ruleset = await get_ruleset_by_id(db, ruleset_id=ruleset_id)
    if ruleset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="RuleSet not found",
        )
    
    revision = await get_revision_by_id(db, ruleset_id=ruleset_id, revision_id=revision_id)
    if revision is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Revision not found",
        )
    
    result = await execute_ruleset_service(
        db=db,
        ruleset_id=ruleset_id,
        input_data=request.input,
        revision_id=revision_id,
    )
    
    if not result.success and result.error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.error,
        )
    
    return execution_result_to_response(result)


@router.get("/{ruleset_id}/order", response_model=dict, status_code=status.HTTP_200_OK)
async def get_ruleset_order(
    ruleset_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_session),
):
    ruleset = await get_ruleset_by_id(db, ruleset_id=ruleset_id)
    if ruleset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="RuleSet not found",
        )
    
    rule_ids = await get_rules_order(db, rule_set_id=ruleset_id)
    
    response = OrderResponse(
        type="id",
        template=f"/ruleSets/{ruleset_id}/rules/{{id}}",
        resources=rule_ids,
    )
    return response.model_dump(by_alias=True, exclude_none=True)


@router.put("/{ruleset_id}/order", response_model=dict, status_code=status.HTTP_200_OK)
async def update_ruleset_order(
    ruleset_id: uuid.UUID,
    order_request: OrderRequest,
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
    
    if order_request.type != "id":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only 'id' type is supported",
        )
    
    success = await update_rules_order(
        db,
        rule_set_id=ruleset_id,
        rule_ids=order_request.resources,
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update order. Please check that all rule IDs are valid.",
        )
    
    response = OrderResponse(
        type="id",
        template=f"/ruleSets/{ruleset_id}/rules/{{id}}",
        resources=order_request.resources,
        message="Order updated successfully",
    )
    return response.model_dump(by_alias=True, exclude_none=True)


@router.get("/{ruleset_id}/code", response_class=PlainTextResponse, status_code=status.HTTP_200_OK)
async def get_ruleset_code(
    ruleset_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_session),
):
    ruleset = await get_ruleset_with_rules(db, ruleset_id=ruleset_id)
    if ruleset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="RuleSet not found",
        )
    
    signature = ruleset.signature or []
    rules = ruleset.rules or []
    
    lookup_ids: set = set()
    for rule in rules:
        conditions = rule.conditions if hasattr(rule, 'conditions') else rule.get('conditions', [])
        for cond in conditions or []:
            if isinstance(cond, dict):
                lookup_id = cond.get('lookup_id')
                if lookup_id:
                    lookup_ids.add(str(lookup_id))
        
        actions = rule.actions if hasattr(rule, 'actions') else rule.get('actions', [])
        for action in actions or []:
            if isinstance(action, dict):
                lookup_id = action.get('lookup_id')
                if lookup_id:
                    lookup_ids.add(str(lookup_id))
    
    lookup_data: dict = {}
    for lookup_id_str in lookup_ids:
        try:
            lookup_id_uuid = uuid.UUID(lookup_id_str)
            lookup = await get_lookup_with_entries(db, lookup_id_uuid)
            if lookup and lookup.entries:
                lookup_data[lookup_id_str] = {
                    entry.key: entry.value for entry in lookup.entries
                }
        except (ValueError, TypeError):
            continue
    
    code = generate_ruleset_function(
        ruleset_name=ruleset.name,
        signature=signature,
        rules=rules,
        lookup_data=lookup_data,
    )
    
    return code


@router.get("/{ruleset_id}/metadata", response_model=dict, status_code=status.HTTP_200_OK)
async def get_ruleset_metadata(
    ruleset_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_session),
):
    ruleset = await get_ruleset_by_id(db, ruleset_id=ruleset_id)
    if ruleset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="RuleSet not found",
        )
    
    signature = ruleset.signature or []
    
    metadata = generate_ruleset_metadata(
        ruleset_name=ruleset.name,
        ruleset_description=ruleset.description,
        major=ruleset.major,
        minor=ruleset.minor,
        signature=signature,
    )
    
    return metadata
