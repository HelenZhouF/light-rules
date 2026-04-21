import uuid
from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.rule import Rule
from app.models.ruleset import RuleSet
from app.schemas.rule import RuleCreate, RuleUpdate


async def get_rule_by_id(db: AsyncSession, rule_id: uuid.UUID) -> Optional[Rule]:
    result = await db.execute(select(Rule).where(Rule.id == rule_id))
    return result.scalar_one_or_none()


async def get_rule_by_id_with_ruleset(
    db: AsyncSession, rule_id: uuid.UUID
) -> Optional[Rule]:
    result = await db.execute(
        select(Rule)
        .options(selectinload(Rule.ruleset))
        .where(Rule.id == rule_id)
    )
    return result.scalar_one_or_none()


async def get_rule_by_name_and_ruleset(
    db: AsyncSession, name: str, rule_set_id: uuid.UUID
) -> Optional[Rule]:
    result = await db.execute(
        select(Rule).where(Rule.name == name, Rule.rule_set_id == rule_set_id)
    )
    return result.scalar_one_or_none()


async def get_rule_by_order_index_and_ruleset(
    db: AsyncSession, order_index: int, rule_set_id: uuid.UUID
) -> Optional[Rule]:
    result = await db.execute(
        select(Rule).where(
            Rule.order_index == order_index, Rule.rule_set_id == rule_set_id
        )
    )
    return result.scalar_one_or_none()


async def get_rules_by_ruleset_id(
    db: AsyncSession,
    rule_set_id: uuid.UUID,
    skip: int = 0,
    limit: int = 100,
) -> Sequence[Rule]:
    result = await db.execute(
        select(Rule)
        .where(Rule.rule_set_id == rule_set_id)
        .order_by(Rule.order_index)
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


async def count_rules_by_ruleset(db: AsyncSession, rule_set_id: uuid.UUID) -> int:
    result = await db.execute(
        select(func.count(Rule.id)).where(Rule.rule_set_id == rule_set_id)
    )
    return result.scalar_one()


async def get_ruleset_with_rules(
    db: AsyncSession, ruleset_id: uuid.UUID
) -> Optional[RuleSet]:
    result = await db.execute(
        select(RuleSet)
        .options(selectinload(RuleSet.rules))
        .where(RuleSet.id == ruleset_id)
    )
    return result.scalar_one_or_none()


async def create_rule(
    db: AsyncSession,
    rule_in: RuleCreate,
    rule_set_id: uuid.UUID,
    created_by: Optional[str] = None,
) -> Rule:
    rule_data = rule_in.model_dump()
    rule_data["rule_set_id"] = rule_set_id
    rule_data["created_by"] = created_by
    rule_data["modified_by"] = created_by

    rule = Rule(**rule_data)
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule


async def update_rule(
    db: AsyncSession,
    rule_id: uuid.UUID,
    rule_in: RuleUpdate,
    modified_by: Optional[str] = None,
) -> Optional[Rule]:
    rule = await get_rule_by_id(db, rule_id)
    if not rule:
        return None

    update_data = rule_in.model_dump(exclude_unset=True)
    if not update_data:
        return rule

    update_data["modified_by"] = modified_by

    for key, value in update_data.items():
        setattr(rule, key, value)

    await db.commit()
    await db.refresh(rule)
    return rule


async def delete_rule(
    db: AsyncSession,
    rule_id: uuid.UUID,
) -> bool:
    rule = await get_rule_by_id(db, rule_id)
    if not rule:
        return False

    await db.delete(rule)
    await db.commit()
    return True
