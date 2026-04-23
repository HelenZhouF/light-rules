import uuid
from typing import Any, Dict, List, Optional, Sequence, Tuple

from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.ruleset import RuleSet
from app.models.rule import Rule
from app.schemas.ruleset import RuleSetCreate, RuleSetUpdate


def _term_to_dict(term: Any) -> Optional[Dict[str, Any]]:
    if isinstance(term, dict):
        return term
    if isinstance(term, BaseModel):
        return term.model_dump()
    return None


def build_term_maps_by_id(
    signature: Optional[List[Any]]
) -> Dict[uuid.UUID, Dict[str, Any]]:
    terms_by_id: Dict[uuid.UUID, Dict[str, Any]] = {}
    if signature:
        for term in signature:
            term_dict = _term_to_dict(term)
            if term_dict and "id" in term_dict:
                try:
                    term_id = uuid.UUID(str(term_dict["id"]))
                    terms_by_id[term_id] = term_dict
                except (ValueError, TypeError):
                    pass
    return terms_by_id


def build_term_maps_by_name(
    signature: Optional[List[Any]]
) -> Dict[str, uuid.UUID]:
    name_to_id: Dict[str, uuid.UUID] = {}
    if signature:
        for term in signature:
            term_dict = _term_to_dict(term)
            if term_dict and "id" in term_dict and "name" in term_dict:
                try:
                    term_id = uuid.UUID(str(term_dict["id"]))
                    name_to_id[term_dict["name"]] = term_id
                except (ValueError, TypeError):
                    pass
    return name_to_id


def detect_term_renames_by_id(
    old_signature: Optional[List[Dict[str, Any]]],
    new_signature: Optional[List[Dict[str, Any]]],
) -> Dict[str, str]:
    if not old_signature or not new_signature:
        return {}
    
    old_terms_by_id = build_term_maps_by_id(old_signature)
    new_terms_by_id = build_term_maps_by_id(new_signature)
    
    name_mapping: Dict[str, str] = {}
    for term_id, old_term in old_terms_by_id.items():
        if term_id in new_terms_by_id:
            old_name = old_term.get("name")
            new_name = new_terms_by_id[term_id].get("name")
            if old_name and new_name and old_name != new_name:
                name_mapping[old_name] = new_name
    
    return name_mapping


def update_term_refs_in_list(
    items: Optional[List[Dict[str, Any]]],
    name_mapping: Dict[str, str],
    new_signature: Optional[List[Dict[str, Any]]],
) -> Optional[List[Dict[str, Any]]]:
    if not items or (not name_mapping and not new_signature):
        return items
    
    new_name_to_id = build_term_maps_by_name(new_signature)
    
    updated = []
    for item in items:
        if isinstance(item, dict):
            item_copy = dict(item)
            term = item_copy.get("term")
            if isinstance(term, dict):
                if "termId" in term and term["termId"]:
                    pass
                elif "name" in term:
                    old_name = term["name"]
                    if old_name in name_mapping:
                        new_name = name_mapping[old_name]
                        if new_name in new_name_to_id:
                            item_copy["term"] = {"termId": str(new_name_to_id[new_name])}
                        else:
                            item_copy["term"] = {"name": new_name}
                    elif old_name in new_name_to_id:
                        item_copy["term"] = {"termId": str(new_name_to_id[old_name])}
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
        name_mapping = detect_term_renames_by_id(old_signature, new_signature)
        
        if name_mapping or new_signature:
            ruleset_with_rules = await db.execute(
                select(RuleSet)
                .options(selectinload(RuleSet.rules))
                .where(RuleSet.id == ruleset_id)
            )
            ruleset_obj = ruleset_with_rules.scalar_one_or_none()
            
            if ruleset_obj and ruleset_obj.rules:
                for rule in ruleset_obj.rules:
                    if rule.conditions:
                        rule.conditions = update_term_refs_in_list(
                            rule.conditions, name_mapping, new_signature
                        )
                    if rule.actions:
                        rule.actions = update_term_refs_in_list(
                            rule.actions, name_mapping, new_signature
                        )

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
