import uuid
from typing import Optional, Sequence

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.function import Function
from app.schemas.function import FunctionCreate, FunctionUpdate


async def get_function_by_id(
    db: AsyncSession,
    function_id: uuid.UUID,
) -> Optional[Function]:
    result = await db.execute(select(Function).where(Function.id == function_id))
    return result.scalar_one_or_none()


async def get_function_by_name_and_category(
    db: AsyncSession,
    name: str,
    category_id: uuid.UUID,
) -> Optional[Function]:
    result = await db.execute(
        select(Function).where(Function.name == name, Function.category_id == category_id)
    )
    return result.scalar_one_or_none()


async def get_functions_by_category_id(
    db: AsyncSession,
    category_id: uuid.UUID,
    skip: int = 0,
    limit: int = 100,
    include_hidden: bool = False,
) -> Sequence[Function]:
    query = select(Function).where(Function.category_id == category_id)
    if not include_hidden:
        query = query.where(Function.hidden == False)
    result = await db.execute(query.offset(skip).limit(limit))
    return result.scalars().all()


async def count_functions_by_category(
    db: AsyncSession,
    category_id: uuid.UUID,
    include_hidden: bool = False,
) -> int:
    query = select(func.count(Function.id)).where(Function.category_id == category_id)
    if not include_hidden:
        query = query.where(Function.hidden == False)
    result = await db.execute(query)
    return result.scalar_one()


async def create_function(
    db: AsyncSession,
    function_in: FunctionCreate,
    category_id: uuid.UUID,
    created_by: Optional[str] = None,
) -> Function:
    function_data = function_in.model_dump()
    function_data["category_id"] = category_id
    function_data["created_by"] = created_by
    function_data["modified_by"] = created_by

    function = Function(**function_data)
    db.add(function)
    await db.commit()
    await db.refresh(function)
    return function


async def update_function(
    db: AsyncSession,
    function_id: uuid.UUID,
    function_in: FunctionUpdate,
    modified_by: Optional[str] = None,
) -> Optional[Function]:
    function = await get_function_by_id(db, function_id)
    if not function:
        return None

    update_data = function_in.model_dump(exclude_unset=True)
    if not update_data:
        return function

    update_data["modified_by"] = modified_by
    update_data["version"] = function.version + 1

    for key, value in update_data.items():
        setattr(function, key, value)

    await db.commit()
    await db.refresh(function)
    return function


async def delete_function(
    db: AsyncSession,
    function_id: uuid.UUID,
) -> bool:
    function = await get_function_by_id(db, function_id)
    if not function:
        return False

    await db.delete(function)
    await db.commit()
    return True
