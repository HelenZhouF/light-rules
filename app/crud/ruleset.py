import uuid
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.ruleset import RuleSet
from app.models.rule import Rule
from app.models.revision import Revision
from app.schemas.ruleset import RuleSetCreate, RuleSetUpdate
from app.schemas.revision import RevisionType


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


def reconcile_signature_ids(
    old_signature: Optional[List[Dict[str, Any]]],
    new_signature: Optional[List[Dict[str, Any]]],
) -> Optional[List[Dict[str, Any]]]:
    """
    智能复用旧 signature 的 id：
    1. 对于新 signature 中的 term，如果 name 在旧 signature 中存在，复用旧 id（即使新 term 有自动生成的 id）
    2. 尝试检测"重命名"场景：旧 name 不在新 signature 中，新 name 不在旧 signature 中，且位置相同
    3. 如果 name 相同但 id 不同，认为是更新，保持旧 id
    """
    if new_signature is None:
        return None
    
    if old_signature is None:
        return new_signature
    
    old_name_to_term: Dict[str, Dict[str, Any]] = {}
    old_index_to_term: Dict[int, Dict[str, Any]] = {}
    for i, term in enumerate(old_signature):
        term_dict = _term_to_dict(term)
        if term_dict and "name" in term_dict:
            old_name_to_term[term_dict["name"]] = term_dict
        old_index_to_term[i] = term_dict
    
    new_names: Set[str] = set()
    for term in new_signature:
        term_dict = _term_to_dict(term)
        if term_dict and "name" in term_dict:
            new_names.add(term_dict["name"])
    
    old_names: Set[str] = set(old_name_to_term.keys())
    
    removed_names = old_names - new_names
    added_names = new_names - old_names
    
    result = []
    for i, new_term in enumerate(new_signature):
        new_term_dict = _term_to_dict(new_term)
        if new_term_dict is None:
            result.append(new_term)
            continue
        
        new_term_id = new_term_dict.get("id")
        new_term_name = new_term_dict.get("name")
        
        if new_term_name:
            if new_term_name in old_name_to_term:
                old_term = old_name_to_term[new_term_name]
                old_id = old_term.get("id")
                if old_id:
                    if new_term_id:
                        if str(old_id) != str(new_term_id):
                            new_term_dict["id"] = str(old_id) if isinstance(old_id, str) else old_id
                    else:
                        new_term_dict["id"] = old_id
            elif len(removed_names) == 1 and len(added_names) == 1:
                removed_name = next(iter(removed_names))
                if new_term_name in added_names:
                    old_term = old_name_to_term.get(removed_name)
                    if old_term:
                        old_id = old_term.get("id")
                        if old_id:
                            new_term_dict["id"] = old_id
            elif i < len(old_signature):
                old_term = old_index_to_term.get(i)
                if old_term:
                    old_name = old_term.get("name")
                    if old_name in removed_names:
                        old_id = old_term.get("id")
                        if old_id:
                            new_term_dict["id"] = old_id
        
        result.append(new_term_dict)
    
    return result


def update_term_refs_in_list(
    items: Optional[List[Dict[str, Any]]],
    name_mapping: Dict[str, str],
    new_signature: Optional[List[Dict[str, Any]]],
) -> Optional[List[Dict[str, Any]]]:
    if not items or (not name_mapping and not new_signature):
        return items
    
    new_name_to_id = build_term_maps_by_name(new_signature)
    new_id_to_term = build_term_maps_by_id(new_signature)
    
    updated = []
    for item in items:
        if isinstance(item, dict):
            item_copy = dict(item)
            term = item_copy.get("term")
            if isinstance(term, dict):
                term_id = term.get("termId")
                term_name = term.get("name")
                
                term_id_valid = False
                if term_id:
                    try:
                        term_uuid = uuid.UUID(str(term_id))
                        if term_uuid in new_id_to_term:
                            term_id_valid = True
                    except (ValueError, TypeError):
                        pass
                
                if term_id_valid:
                    new_term = new_id_to_term.get(uuid.UUID(str(term_id)))
                    if new_term:
                        new_term_name = new_term.get("name")
                        if term_name and term_name != new_term_name:
                            item_copy["term"] = {
                                "termId": term_id,
                                "name": new_term_name
                            }
                        elif not term_name and new_term_name:
                            item_copy["term"] = {
                                "termId": term_id,
                                "name": new_term_name
                            }
                else:
                    if term_name:
                        if term_name in name_mapping:
                            new_name = name_mapping[term_name]
                            if new_name in new_name_to_id:
                                item_copy["term"] = {
                                    "termId": str(new_name_to_id[new_name]),
                                    "name": new_name
                                }
                            else:
                                item_copy["term"] = {"name": new_name}
                        elif term_name in new_name_to_id:
                            item_copy["term"] = {
                                "termId": str(new_name_to_id[term_name]),
                                "name": term_name
                            }
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
    await db.flush()
    
    revision_data = {
        "rule_set_id": ruleset.id,
        "name": ruleset.name,
        "ruleSetType": ruleset.ruleSetType,
        "description": ruleset.description,
        "signature": ruleset.signature,
        "major": ruleset.major,
        "minor": ruleset.minor,
        "is_locked": False,
        "created_by": created_by,
        "modified_by": created_by,
    }
    revision = Revision(**revision_data)
    db.add(revision)
    
    await db.commit()
    await db.refresh(ruleset)
    return ruleset


def _signature_terms_to_dicts(
    signature: Optional[List[Any]]
) -> Optional[List[Dict[str, Any]]]:
    """
    将 signature 中的 SignatureTerm 转换为 dict，确保 id 被包含。
    解决 model_dump(exclude_unset=True) 排除自动生成 id 的问题。
    """
    if signature is None:
        return None
    
    result = []
    for term in signature:
        if isinstance(term, BaseModel):
            term_dict = term.model_dump()
            if "id" in term_dict and isinstance(term_dict["id"], uuid.UUID):
                term_dict["id"] = str(term_dict["id"])
            result.append(term_dict)
        elif isinstance(term, dict):
            term_dict = dict(term)
            if "id" in term_dict and isinstance(term_dict["id"], uuid.UUID):
                term_dict["id"] = str(term_dict["id"])
            result.append(term_dict)
    
    return result if result else None


async def get_unlocked_revision(
    db: AsyncSession,
    ruleset_id: uuid.UUID,
) -> Optional[Revision]:
    result = await db.execute(
        select(Revision).where(
            Revision.rule_set_id == ruleset_id,
            Revision.is_locked == False,
        )
    )
    return result.scalar_one_or_none()


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
    
    new_signature_input = None
    if ruleset_in.signature is not None:
        new_signature_input = _signature_terms_to_dicts(ruleset_in.signature)
    
    if new_signature_input is not None:
        update_data["signature"] = new_signature_input
    
    new_signature = update_data.get("signature")
    
    if new_signature is not None:
        reconciled_signature = reconcile_signature_ids(old_signature, new_signature)
        if reconciled_signature is not None:
            new_signature = reconciled_signature
            update_data["signature"] = new_signature
        
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

    unlocked_revision = await get_unlocked_revision(db, ruleset_id)
    if unlocked_revision:
        revision_update_fields = ["name", "ruleSetType", "description", "signature", "modified_by"]
        for key, value in update_data.items():
            if key in revision_update_fields:
                setattr(unlocked_revision, key, value)

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


async def get_revisions(
    db: AsyncSession,
    ruleset_id: uuid.UUID,
    skip: int = 0,
    limit: int = 100,
) -> Sequence[Revision]:
    result = await db.execute(
        select(Revision)
        .where(Revision.rule_set_id == ruleset_id)
        .order_by(Revision.major.desc(), Revision.minor.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


async def get_revision_by_id(
    db: AsyncSession,
    ruleset_id: uuid.UUID,
    revision_id: uuid.UUID,
) -> Optional[Revision]:
    result = await db.execute(
        select(Revision).where(
            Revision.rule_set_id == ruleset_id,
            Revision.id == revision_id,
        )
    )
    return result.scalar_one_or_none()


async def count_revisions(
    db: AsyncSession,
    ruleset_id: uuid.UUID,
) -> int:
    result = await db.execute(
        select(func.count(Revision.id)).where(Revision.rule_set_id == ruleset_id)
    )
    return result.scalar_one()


async def lock_all_revisions(
    db: AsyncSession,
    ruleset_id: uuid.UUID,
) -> None:
    from sqlalchemy import update
    await db.execute(
        update(Revision)
        .where(Revision.rule_set_id == ruleset_id)
        .values(is_locked=True)
    )


async def create_revision(
    db: AsyncSession,
    ruleset_id: uuid.UUID,
    revision_type: RevisionType = RevisionType.minor,
    ruleset_update: Optional[RuleSetUpdate] = None,
    created_by: Optional[str] = None,
) -> Optional[Revision]:
    ruleset = await get_ruleset_by_id(db, ruleset_id)
    if not ruleset:
        return None

    if ruleset_update:
        update_data = ruleset_update.model_dump(exclude_unset=True)
        if update_data:
            update_data["modified_by"] = created_by

            old_signature = ruleset.signature
            
            new_signature_input = None
            if ruleset_update.signature is not None:
                new_signature_input = _signature_terms_to_dicts(ruleset_update.signature)
            
            if new_signature_input is not None:
                update_data["signature"] = new_signature_input
            
            new_signature = update_data.get("signature")
            
            if new_signature is not None:
                reconciled_signature = reconcile_signature_ids(old_signature, new_signature)
                if reconciled_signature is not None:
                    new_signature = reconciled_signature
                    update_data["signature"] = new_signature
                
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

    if revision_type == RevisionType.major:
        ruleset.major += 1
        ruleset.minor = 0
    else:
        ruleset.minor += 1

    ruleset.version += 1
    ruleset.modified_by = created_by

    await lock_all_revisions(db, ruleset_id)

    revision_data = {
        "rule_set_id": ruleset.id,
        "name": ruleset.name,
        "ruleSetType": ruleset.ruleSetType,
        "description": ruleset.description,
        "signature": ruleset.signature,
        "major": ruleset.major,
        "minor": ruleset.minor,
        "is_locked": False,
        "created_by": created_by,
        "modified_by": created_by,
    }

    revision = Revision(**revision_data)
    db.add(revision)

    await db.commit()
    await db.refresh(revision)
    return revision
