import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.schemas.function_category import (
    FunctionCategoryCreate,
    FunctionCategoryUpdate,
    FunctionCategoryResponse,
    FunctionCategoryResponseData,
    FunctionCategoryListResponse,
)
from app.crud import (
    get_function_category_by_id,
    get_function_category_by_name,
    get_function_categories,
    count_function_categories,
    create_function_category,
    update_function_category,
    delete_function_category,
)
from app.utils.hateoas import (
    build_function_category_links,
    build_function_category_pagination_links,
    FUNCTION_CATEGORY_API_BASE,
    FUNCTION_CATEGORY_MEDIA_TYPE,
)

router = APIRouter(prefix="/function-categories", tags=["function-categories"])


def function_category_to_response(category) -> dict:
    data = FunctionCategoryResponseData.model_validate(category)
    links = build_function_category_links(category.id)
    data_dict = data.model_dump()
    response = FunctionCategoryResponse(**data_dict, _links=links)
    result = response.model_dump(by_alias=True, exclude_none=True)
    return result


@router.get("/", response_model=dict, status_code=status.HTTP_200_OK)
async def read_function_categories(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    include_hidden: bool = Query(False, description="Include hidden categories"),
    db: AsyncSession = Depends(get_async_session),
):
    total = await count_function_categories(db, include_hidden=include_hidden)
    categories = await get_function_categories(
        db, skip=skip, limit=limit, include_hidden=include_hidden
    )

    items = [function_category_to_response(c) for c in categories]
    pagination_links = build_function_category_pagination_links(skip, limit, total)

    response = FunctionCategoryListResponse(
        items=[],
        _links=pagination_links,
        total=total,
        skip=skip,
        limit=limit,
    )
    result = response.model_dump(by_alias=True, exclude_none=True)
    result["items"] = items
    result["_links"]["createFunctionCategory"] = {
        "href": FUNCTION_CATEGORY_API_BASE,
        "method": "POST",
        "uri": FUNCTION_CATEGORY_API_BASE,
        "type": FUNCTION_CATEGORY_MEDIA_TYPE
    }
    return result


@router.get("/{category_id}", response_model=dict, status_code=status.HTTP_200_OK)
async def read_function_category(
    category_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_session),
):
    category = await get_function_category_by_id(db, category_id=category_id)
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="FunctionCategory not found",
        )
    return function_category_to_response(category)


@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_new_function_category(
    category_in: FunctionCategoryCreate,
    db: AsyncSession = Depends(get_async_session),
):
    existing_category = await get_function_category_by_name(db, name=category_in.name)
    if existing_category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="FunctionCategory with this name already exists",
        )

    category = await create_function_category(db=db, category_in=category_in)
    return function_category_to_response(category)


@router.put("/{category_id}", response_model=dict, status_code=status.HTTP_200_OK)
async def update_existing_function_category(
    category_id: uuid.UUID,
    category_in: FunctionCategoryUpdate,
    db: AsyncSession = Depends(get_async_session),
):
    category = await get_function_category_by_id(db, category_id=category_id)
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="FunctionCategory not found",
        )

    if category_in.name and category_in.name != category.name:
        existing_category = await get_function_category_by_name(db, name=category_in.name)
        if existing_category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="FunctionCategory with this name already exists",
            )

    updated_category = await update_function_category(
        db=db,
        category_id=category_id,
        category_in=category_in,
    )
    return function_category_to_response(updated_category)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_existing_function_category(
    category_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_session),
):
    category = await get_function_category_by_id(db, category_id=category_id)
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="FunctionCategory not found",
        )

    await delete_function_category(db=db, category_id=category_id)
    return None
