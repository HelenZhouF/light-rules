import uuid
from typing import Optional, Sequence

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.function_category import FunctionCategory
from app.schemas.function_category import FunctionCategoryCreate, FunctionCategoryUpdate


async def get_function_category_by_id(
    db: AsyncSession,
    category_id: uuid.UUID,
) -> Optional[FunctionCategory]:
    result = await db.execute(select(FunctionCategory).where(FunctionCategory.id == category_id))
    return result.scalar_one_or_none()


async def get_function_category_by_name(
    db: AsyncSession,
    name: str,
) -> Optional[FunctionCategory]:
    result = await db.execute(select(FunctionCategory).where(FunctionCategory.name == name))
    return result.scalar_one_or_none()


async def get_function_categories(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    include_hidden: bool = False,
) -> Sequence[FunctionCategory]:
    query = select(FunctionCategory)
    if not include_hidden:
        query = query.where(FunctionCategory.hidden == False)
    result = await db.execute(query.offset(skip).limit(limit))
    return result.scalars().all()


async def count_function_categories(
    db: AsyncSession,
    include_hidden: bool = False,
) -> int:
    query = select(func.count(FunctionCategory.id))
    if not include_hidden:
        query = query.where(FunctionCategory.hidden == False)
    result = await db.execute(query)
    return result.scalar_one()


async def create_function_category(
    db: AsyncSession,
    category_in: FunctionCategoryCreate,
    created_by: Optional[str] = None,
) -> FunctionCategory:
    category_data = category_in.model_dump()
    category_data["created_by"] = created_by
    category_data["modified_by"] = created_by

    category = FunctionCategory(**category_data)
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category


async def update_function_category(
    db: AsyncSession,
    category_id: uuid.UUID,
    category_in: FunctionCategoryUpdate,
    modified_by: Optional[str] = None,
) -> Optional[FunctionCategory]:
    category = await get_function_category_by_id(db, category_id)
    if not category:
        return None

    update_data = category_in.model_dump(exclude_unset=True)
    if not update_data:
        return category

    update_data["modified_by"] = modified_by
    update_data["version"] = category.version + 1

    for key, value in update_data.items():
        setattr(category, key, value)

    await db.commit()
    await db.refresh(category)
    return category


async def delete_function_category(
    db: AsyncSession,
    category_id: uuid.UUID,
) -> bool:
    category = await get_function_category_by_id(db, category_id)
    if not category:
        return False

    await db.delete(category)
    await db.commit()
    return True
