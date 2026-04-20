import uuid
from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ruleset import RuleSet
from app.schemas.ruleset import RuleSetCreate, RuleSetUpdate


async def get_ruleset_by_id(db: AsyncSession, ruleset_id: uuid.UUID) -> Optional[RuleSet]:
    result = await db.execute(select(RuleSet).where(RuleSet.id == ruleset_id))
    return result.scalar_one_or_none()


async def get_ruleset_by_name(db: AsyncSession, name: str) -> Optional[RuleSet]:
    result = await db.execute(select(RuleSet).where(RuleSet.name == name))
    return result.scalar_one_or_none()


async def get_rulesets(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
) -> Sequence[RuleSet]:
    result = await db.execute(select(RuleSet).offset(skip).limit(limit))
    return result.scalars().all()


async def create_ruleset(
    db: AsyncSession,
    ruleset_in: RuleSetCreate,
    created_by: Optional[str] = None,
) -> RuleSet:
    ruleset_data = ruleset_in.model_dump()
    ruleset_data["created_by"] = created_by
    ruleset_data["modified_by"] = created_by

    ruleset = RuleSet(**ruleset_data)
    db.add(ruleset)
    await db.commit()
    await db.refresh(ruleset)
    return ruleset


async def update_ruleset(
    db: AsyncSession,
    ruleset_id: uuid.UUID,
    ruleset_in: RuleSetUpdate,
    modified_by: Optional[str] = None,
) -> Optional[RuleSet]:
    ruleset = await get_ruleset_by_id(db, ruleset_id)
    if not ruleset:
        return None

    update_data = ruleset_in.model_dump(exclude_unset=True)
    if not update_data:
        return ruleset

    update_data["modified_by"] = modified_by

    for key, value in update_data.items():
        setattr(ruleset, key, value)

    await db.commit()
    await db.refresh(ruleset)
    return ruleset


async def delete_ruleset(
    db: AsyncSession,
    ruleset_id: uuid.UUID,
) -> bool:
    ruleset = await get_ruleset_by_id(db, ruleset_id)
    if not ruleset:
        return False

    await db.delete(ruleset)
    await db.commit()
    return True
