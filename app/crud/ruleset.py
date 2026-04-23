import uuid
from typing import Any, Dict, List, Optional, Sequence, Tuple

from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.ruleset import RuleSet
from app.models.rule import Rule
from app.schemas.ruleset import RuleSetCreate, RuleSetUpdate


def build_term_comparison_key(term: Dict[str, Any]) -> Tuple:
    key_parts = []
    for key in sorted(term.keys()):
        if key != "name" and key != "id":
            value = term[key]
            if isinstance(value, list):
                value = tuple(build_term_comparison_key(t) if isinstance(t, dict) else t for t in value)
            elif isinstance(value, dict):
                value = build_term_comparison_key(value)
            key_parts.append((key, value))
    return tuple(key_parts)


def detect_term_renames(
    old_signature: Optional[List[Dict[str, Any]]],
    new_signature: Optional[List[Dict[str, Any]]],
) -> Dict[str, str]:
    if not old_signature or not new_signature:
        return {}
    
    old_terms_by_key: Dict[Tuple, str] = {}
    for term in old_signature:
        if isinstance(term, dict) and "name" in term:
            key = build_term_comparison_key(term)
            old_terms_by_key[key] = term["name"]
    
    name_mapping: Dict[str, str] = {}
    for term in new_signature:
        if isinstance(term, dict) and "name" in term:
            key = build_term_comparison_key(term)
            if key in old_terms_by_key:
                old_name = old_terms_by_key[key]
                new_name = term["name"]
                if old_name != new_name:
                    name_mapping[old_name] = new_name
    
    return name_mapping


def update_term_in_list(
    items: Optional[List[Dict[str, Any]]],
    name_mapping: Dict[str, str],
) -> Optional[List[Dict[str, Any]]]:
    if not items or not name_mapping:
        return items
    
    updated = []
    for item in items:
        if isinstance(item, dict):
            item_copy = dict(item)
            term = item_copy.get("term")
            if isinstance(term, dict) and "name" in term:
                old_name = term["name"]
                if old_name in name_mapping:
                    new_name = name_mapping[old_name]
                    item_copy["term"] = {"name": new_name}
            updated.append(item_copy)
        else:
            updated.append(item)
    
    return updated


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


async def count_rulesets(db: AsyncSession) -> int:
    result = await db.execute(select(func.count(RuleSet.id)))
    return result.scalar_one()


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

    old_signature = ruleset.signature
    new_signature = update_data.get("signature")
    
    if new_signature is not None:
        name_mapping = detect_term_renames(old_signature, new_signature)
        
        if name_mapping:
            ruleset_with_rules = await db.execute(
                select(RuleSet)
                .options(selectinload(RuleSet.rules))
                .where(RuleSet.id == ruleset_id)
            )
            ruleset_obj = ruleset_with_rules.scalar_one_or_none()
            
            if ruleset_obj and ruleset_obj.rules:
                for rule in ruleset_obj.rules:
                    if rule.conditions:
                        rule.conditions = update_term_in_list(rule.conditions, name_mapping)
                    if rule.actions:
                        rule.actions = update_term_in_list(rule.actions, name_mapping)

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
