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
from app.utils.hateoas import build_ruleset_links, build_pagination_links

router = APIRouter(prefix="/rulesets", tags=["rulesets"])


def ruleset_to_response(ruleset) -> RuleSetResponse:
    data = RuleSetResponseData.model_validate(ruleset)
    links = build_ruleset_links(ruleset.id, ruleset.is_locked)
    return RuleSetResponse(**data.model_dump(), _links=links)


@router.get("/", response_model=RuleSetListResponse, status_code=status.HTTP_200_OK)
async def read_rulesets(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_async_session),
):
    total = await count_rulesets(db)
    rulesets = await get_rulesets(db, skip=skip, limit=limit)
    
    items = [ruleset_to_response(r) for r in rulesets]
    pagination_links = build_pagination_links(skip, limit, total)
    
    return RuleSetListResponse(
        items=items,
        _links=pagination_links,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{ruleset_id}", response_model=RuleSetResponse, status_code=status.HTTP_200_OK)
async def read_ruleset(
    ruleset_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_session),
):
    ruleset = await get_ruleset_by_id(db, ruleset_id=ruleset_id)
    if ruleset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="RuleSet not found",
        )
    return ruleset_to_response(ruleset)


@router.post("/", response_model=RuleSetResponse, status_code=status.HTTP_201_CREATED)
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


@router.put("/{ruleset_id}", response_model=RuleSetResponse, status_code=status.HTTP_200_OK)
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
