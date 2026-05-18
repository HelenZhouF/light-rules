import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.schemas.function import (
    FunctionCreate,
    FunctionUpdate,
    FunctionResponse,
    FunctionResponseData,
    FunctionListResponse,
)
from app.crud import (
    get_function_category_by_id,
)
from app.crud.function import (
    get_function_by_id,
    get_function_by_name_and_category,
    get_functions_by_category_id,
    count_functions_by_category,
    create_function,
    update_function,
    delete_function,
)
from app.utils.hateoas import (
    build_function_links,
    build_function_pagination_links,
    FUNCTION_CATEGORY_API_BASE,
    FUNCTION_MEDIA_TYPE,
)

router = APIRouter(prefix="/function-categories/{category_id}/functions", tags=["functions"])


def function_to_response(function) -> dict:
    data = FunctionResponseData.model_validate(function)
    links = build_function_links(function.id, function.category_id)
    data_dict = data.model_dump()
    response = FunctionResponse(**data_dict, _links=links)
    result = response.model_dump(by_alias=True, exclude_none=True)
    return result


@router.get("/", response_model=dict, status_code=status.HTTP_200_OK)
async def read_functions(
    category_id: uuid.UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    include_hidden: bool = Query(False, description="Include hidden functions"),
    db: AsyncSession = Depends(get_async_session),
):
    category = await get_function_category_by_id(db, category_id=category_id)
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="FunctionCategory not found",
        )

    total = await count_functions_by_category(db, category_id=category_id, include_hidden=include_hidden)
    functions = await get_functions_by_category_id(
        db, category_id=category_id, skip=skip, limit=limit, include_hidden=include_hidden
    )

    items = [function_to_response(f) for f in functions]
    pagination_links = build_function_pagination_links(category_id, skip, limit, total)

    response = FunctionListResponse(
        items=[],
        _links=pagination_links,
        total=total,
        skip=skip,
        limit=limit,
    )
    result = response.model_dump(by_alias=True, exclude_none=True)
    result["items"] = items
    result["_links"]["createFunction"] = {
        "href": f"{FUNCTION_CATEGORY_API_BASE}/{category_id}/functions",
        "method": "POST",
        "uri": f"{FUNCTION_CATEGORY_API_BASE}/{category_id}/functions",
        "type": FUNCTION_MEDIA_TYPE
    }
    return result


@router.get("/{function_id}", response_model=dict, status_code=status.HTTP_200_OK)
async def read_function(
    category_id: uuid.UUID,
    function_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_session),
):
    category = await get_function_category_by_id(db, category_id=category_id)
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="FunctionCategory not found",
        )

    function = await get_function_by_id(db, function_id=function_id)
    if function is None or function.category_id != category_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Function not found",
        )
    return function_to_response(function)


@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_new_function(
    category_id: uuid.UUID,
    function_in: FunctionCreate,
    db: AsyncSession = Depends(get_async_session),
):
    category = await get_function_category_by_id(db, category_id=category_id)
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="FunctionCategory not found",
        )

    existing_function = await get_function_by_name_and_category(
        db, name=function_in.name, category_id=category_id
    )
    if existing_function:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Function with this name already exists in the category",
        )

    function = await create_function(db=db, function_in=function_in, category_id=category_id)
    return function_to_response(function)


@router.put("/{function_id}", response_model=dict, status_code=status.HTTP_200_OK)
async def update_existing_function(
    category_id: uuid.UUID,
    function_id: uuid.UUID,
    function_in: FunctionUpdate,
    db: AsyncSession = Depends(get_async_session),
):
    category = await get_function_category_by_id(db, category_id=category_id)
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="FunctionCategory not found",
        )

    function = await get_function_by_id(db, function_id=function_id)
    if function is None or function.category_id != category_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Function not found",
        )

    if function_in.name and function_in.name != function.name:
        existing_function = await get_function_by_name_and_category(
            db, name=function_in.name, category_id=category_id
        )
        if existing_function:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Function with this name already exists in the category",
            )

    updated_function = await update_function(
        db=db,
        function_id=function_id,
        function_in=function_in,
    )
    return function_to_response(updated_function)


@router.delete("/{function_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_existing_function(
    category_id: uuid.UUID,
    function_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_session),
):
    category = await get_function_category_by_id(db, category_id=category_id)
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="FunctionCategory not found",
        )

    function = await get_function_by_id(db, function_id=function_id)
    if function is None or function.category_id != category_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Function not found",
        )

    await delete_function(db=db, function_id=function_id)
    return None
