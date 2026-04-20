import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.schemas.ruleset import RuleSetCreate, RuleSetUpdate, RuleSetResponse
from app.crud import (
    get_ruleset_by_id,
    get_ruleset_by_name,
    get_rulesets,
    create_ruleset,
    update_ruleset,
    delete_ruleset,
)

router = APIRouter(prefix="/rulesets", tags=["rulesets"])


@router.get("/", response_model=List[RuleSetResponse], status_code=status.HTTP_200_OK)
async def read_rulesets(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_async_session),
):
    rulesets = await get_rulesets(db, skip=skip, limit=limit)
    return rulesets


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
    return ruleset


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
    return ruleset


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
    return updated_ruleset


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
