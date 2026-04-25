import uuid
from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.rule import Rule
from app.models.ruleset import RuleSet
from app.schemas.rule import (
    RuleCreate,
    RuleUpdate,
    build_signature_term_maps,
    resolve_term_for_storage,
)
from app.schemas.condition_action import ConditionCreate, ActionCreate, TermRef


def process_term_ref_for_storage(
    term: Any,
    terms_by_id: Dict[uuid.UUID, Dict[str, Any]],
    terms_by_name: Dict[str, Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    if isinstance(term, TermRef):
        return resolve_term_for_storage(term, terms_by_id, terms_by_name)
    elif isinstance(term, dict):
        term_ref = TermRef(
            termId=term.get("termId"),
            name=term.get("name"),
        )
        return resolve_term_for_storage(term_ref, terms_by_id, terms_by_name)
    return None


def process_conditions_for_storage(
    conditions: Optional[List[ConditionCreate]],
    signature: Optional[List[Any]] = None,
    existing_conditions: Optional[List[Dict[str, Any]]] = None,
) -> Optional[List[Dict[str, Any]]]:
    if conditions is None:
        return existing_conditions
    
    if not conditions:
        return []
    
    terms_by_id, terms_by_name = build_signature_term_maps(signature)
    
    result = []
    for cond in conditions:
        cond_dict = cond.model_dump()
        cond_dict["id"] = str(uuid.uuid4())
        cond_dict["status"] = None
        cond_dict["statusMessage"] = None
        
        if "lookup_id" in cond_dict and cond_dict["lookup_id"] is not None:
            cond_dict["lookup_id"] = str(cond_dict["lookup_id"])
        
        if "term" in cond_dict:
            processed_term = process_term_ref_for_storage(
                cond.term, terms_by_id, terms_by_name
            )
            if processed_term:
                cond_dict["term"] = processed_term
        
        result.append(cond_dict)
    
    return result


def process_actions_for_storage(
    actions: Optional[List[ActionCreate]],
    signature: Optional[List[Any]] = None,
    existing_actions: Optional[List[Dict[str, Any]]] = None,
) -> Optional[List[Dict[str, Any]]]:
    if actions is None:
        return existing_actions
    
    if not actions:
        return []
    
    terms_by_id, terms_by_name = build_signature_term_maps(signature)
    
    result = []
    for action in actions:
        action_dict = action.model_dump()
        action_dict["id"] = str(uuid.uuid4())
        action_dict["status"] = None
        action_dict["statusMessage"] = None
        
        if "lookup_id" in action_dict and action_dict["lookup_id"] is not None:
            action_dict["lookup_id"] = str(action_dict["lookup_id"])
        
        if "term" in action_dict:
            processed_term = process_term_ref_for_storage(
                action.term, terms_by_id, terms_by_name
            )
            if processed_term:
                action_dict["term"] = processed_term
        
        result.append(action_dict)
    
    return result


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


async def get_next_order_index(db: AsyncSession, rule_set_id: uuid.UUID) -> int:
    result = await db.execute(
        select(func.max(Rule.order_index)).where(Rule.rule_set_id == rule_set_id)
    )
    max_order = result.scalar_one_or_none()
    return max_order + 1 if max_order is not None else 0


async def get_max_order_index(db: AsyncSession, rule_set_id: uuid.UUID) -> int:
    result = await db.execute(
        select(func.max(Rule.order_index)).where(Rule.rule_set_id == rule_set_id)
    )
    max_order = result.scalar_one_or_none()
    return max_order if max_order is not None else -1


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
    signature: Optional[List[Any]] = None,
    created_by: Optional[str] = None,
) -> Rule:
    rule_data = rule_in.model_dump(exclude={"conditions", "actions"})
    rule_data["rule_set_id"] = rule_set_id
    rule_data["created_by"] = created_by
    rule_data["modified_by"] = created_by
    
    if rule_data.get("order_index") is None:
        rule_data["order_index"] = await get_next_order_index(db, rule_set_id)
    
    rule_data["conditions"] = process_conditions_for_storage(rule_in.conditions, signature)
    rule_data["actions"] = process_actions_for_storage(rule_in.actions, signature)

    rule = Rule(**rule_data)
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule


async def update_rule(
    db: AsyncSession,
    rule_id: uuid.UUID,
    rule_in: RuleUpdate,
    signature: Optional[List[Any]] = None,
    modified_by: Optional[str] = None,
) -> Optional[Rule]:
    rule = await get_rule_by_id(db, rule_id)
    if not rule:
        return None

    update_data = rule_in.model_dump(exclude_unset=True, exclude={"conditions", "actions"})
    
    if rule_in.conditions is not None:
        update_data["conditions"] = process_conditions_for_storage(
            rule_in.conditions,
            signature,
            rule.conditions
        )
    
    if rule_in.actions is not None:
        update_data["actions"] = process_actions_for_storage(
            rule_in.actions,
            signature,
            rule.actions
        )
    
    if not update_data and rule_in.conditions is None and rule_in.actions is None:
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


async def get_rules_order(
    db: AsyncSession,
    rule_set_id: uuid.UUID,
) -> List[str]:
    rules = await get_rules_by_ruleset_id(db, rule_set_id=rule_set_id)
    return [str(rule.id) for rule in rules]


async def update_rules_order(
    db: AsyncSession,
    rule_set_id: uuid.UUID,
    rule_ids: List[str],
) -> bool:
    existing_rules = await get_rules_by_ruleset_id(db, rule_set_id=rule_set_id)
    existing_rule_ids = set(str(rule.id) for rule in existing_rules)
    
    for rule_id in rule_ids:
        if rule_id not in existing_rule_ids:
            return False
    
    rule_id_to_rule = {str(rule.id): rule for rule in existing_rules}
    
    max_order = await get_max_order_index(db, rule_set_id)
    temp_offset = max_order + 1000
    
    for i, rule_id in enumerate(rule_ids):
        rule = rule_id_to_rule.get(rule_id)
        if rule:
            rule.order_index = temp_offset + i
    
    await db.flush()
    
    for index, rule_id in enumerate(rule_ids):
        rule = rule_id_to_rule.get(rule_id)
        if rule:
            rule.order_index = index
    
    await db.commit()
    return True
