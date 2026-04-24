import uuid
from typing import List, Optional, Sequence, Dict

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.lookup import Lookup, LookupEntry
from app.schemas.lookup import (
    LookupCreate,
    LookupUpdate,
    LookupEntryCreate,
    JsonPatchOperation,
)


async def get_lookup_by_id(db: AsyncSession, lookup_id: uuid.UUID) -> Optional[Lookup]:
    result = await db.execute(select(Lookup).where(Lookup.id == lookup_id))
    return result.scalar_one_or_none()


async def get_lookup_with_entries(db: AsyncSession, lookup_id: uuid.UUID) -> Optional[Lookup]:
    result = await db.execute(
        select(Lookup)
        .options(selectinload(Lookup.entries))
        .where(Lookup.id == lookup_id)
    )
    return result.scalar_one_or_none()


async def get_lookup_by_name(db: AsyncSession, name: str) -> Optional[Lookup]:
    result = await db.execute(select(Lookup).where(Lookup.name == name))
    return result.scalar_one_or_none()


async def get_lookups(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
) -> Sequence[Lookup]:
    result = await db.execute(select(Lookup).offset(skip).limit(limit))
    return result.scalars().all()


async def count_lookups(db: AsyncSession) -> int:
    result = await db.execute(select(func.count(Lookup.id)))
    return result.scalar_one()


async def create_lookup(
    db: AsyncSession,
    lookup_in: LookupCreate,
    created_by: Optional[str] = None,
) -> Lookup:
    lookup_data = lookup_in.model_dump()
    lookup_data["created_by"] = created_by
    lookup_data["modified_by"] = created_by

    lookup = Lookup(**lookup_data)
    db.add(lookup)
    await db.commit()
    await db.refresh(lookup)
    return lookup


async def update_lookup(
    db: AsyncSession,
    lookup_id: uuid.UUID,
    lookup_in: LookupUpdate,
    modified_by: Optional[str] = None,
) -> Optional[Lookup]:
    lookup = await get_lookup_by_id(db, lookup_id)
    if not lookup:
        return None

    update_data = lookup_in.model_dump(exclude_unset=True)
    if not update_data:
        return lookup

    update_data["modified_by"] = modified_by

    for key, value in update_data.items():
        setattr(lookup, key, value)

    await db.commit()
    await db.refresh(lookup)
    return lookup


async def delete_lookup(
    db: AsyncSession,
    lookup_id: uuid.UUID,
) -> bool:
    lookup = await get_lookup_by_id(db, lookup_id)
    if not lookup:
        return False

    await db.delete(lookup)
    await db.commit()
    return True


async def get_entries_by_lookup_id(
    db: AsyncSession,
    lookup_id: uuid.UUID,
    skip: int = 0,
    limit: int = 100,
) -> Sequence[LookupEntry]:
    result = await db.execute(
        select(LookupEntry)
        .where(LookupEntry.lookup_id == lookup_id)
        .order_by(LookupEntry.key)
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


async def count_entries(db: AsyncSession, lookup_id: uuid.UUID) -> int:
    result = await db.execute(
        select(func.count(LookupEntry.id))
        .where(LookupEntry.lookup_id == lookup_id)
    )
    return result.scalar_one()


async def get_entry_by_lookup_and_key(
    db: AsyncSession,
    lookup_id: uuid.UUID,
    key: str,
) -> Optional[LookupEntry]:
    result = await db.execute(
        select(LookupEntry)
        .where(
            LookupEntry.lookup_id == lookup_id,
            LookupEntry.key == key,
        )
    )
    return result.scalar_one_or_none()


async def get_entry_by_id(
    db: AsyncSession,
    entry_id: uuid.UUID,
) -> Optional[LookupEntry]:
    result = await db.execute(
        select(LookupEntry).where(LookupEntry.id == entry_id)
    )
    return result.scalar_one_or_none()


async def create_entry(
    db: AsyncSession,
    lookup_id: uuid.UUID,
    entry_in: LookupEntryCreate,
    created_by: Optional[str] = None,
) -> Optional[LookupEntry]:
    lookup = await get_lookup_by_id(db, lookup_id)
    if not lookup:
        return None

    existing_entry = await get_entry_by_lookup_and_key(db, lookup_id, entry_in.key)
    if existing_entry:
        return None

    entry_data = entry_in.model_dump()
    entry_data["lookup_id"] = lookup_id
    entry_data["created_by"] = created_by
    entry_data["modified_by"] = created_by

    entry = LookupEntry(**entry_data)
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


async def update_entry(
    db: AsyncSession,
    lookup_id: uuid.UUID,
    key: str,
    value: str,
    modified_by: Optional[str] = None,
) -> Optional[LookupEntry]:
    entry = await get_entry_by_lookup_and_key(db, lookup_id, key)
    if not entry:
        return None

    entry.value = value
    entry.modified_by = modified_by

    await db.commit()
    await db.refresh(entry)
    return entry


async def delete_entry(
    db: AsyncSession,
    lookup_id: uuid.UUID,
    key: str,
) -> bool:
    entry = await get_entry_by_lookup_and_key(db, lookup_id, key)
    if not entry:
        return False

    await db.delete(entry)
    await db.commit()
    return True


async def batch_create_entries(
    db: AsyncSession,
    lookup_id: uuid.UUID,
    entries_in: List[LookupEntryCreate],
    created_by: Optional[str] = None,
) -> List[LookupEntry]:
    lookup = await get_lookup_by_id(db, lookup_id)
    if not lookup:
        return []

    existing_keys = set()
    result_entries = []

    for entry_in in entries_in:
        if entry_in.key in existing_keys:
            continue

        existing_entry = await get_entry_by_lookup_and_key(db, lookup_id, entry_in.key)
        if existing_entry:
            existing_keys.add(entry_in.key)
            continue

        entry_data = entry_in.model_dump()
        entry_data["lookup_id"] = lookup_id
        entry_data["created_by"] = created_by
        entry_data["modified_by"] = created_by

        entry = LookupEntry(**entry_data)
        db.add(entry)
        existing_keys.add(entry_in.key)
        result_entries.append(entry)

    if result_entries:
        await db.commit()
        for entry in result_entries:
            await db.refresh(entry)

    return result_entries


async def batch_upsert_entries(
    db: AsyncSession,
    lookup_id: uuid.UUID,
    entries_in: List[LookupEntryCreate],
    modified_by: Optional[str] = None,
) -> List[LookupEntry]:
    lookup = await get_lookup_by_id(db, lookup_id)
    if not lookup:
        return []

    result_entries = []
    keys_to_upsert = {entry_in.key: entry_in.value for entry_in in entries_in}

    existing_entries = await get_entries_by_lookup_id(db, lookup_id, limit=1000)
    existing_keys_map = {entry.key: entry for entry in existing_entries}

    for key, value in keys_to_upsert.items():
        if key in existing_keys_map:
            entry = existing_keys_map[key]
            entry.value = value
            entry.modified_by = modified_by
            result_entries.append(entry)
        else:
            entry_data = {
                "lookup_id": lookup_id,
                "key": key,
                "value": value,
                "created_by": modified_by,
                "modified_by": modified_by,
            }
            entry = LookupEntry(**entry_data)
            db.add(entry)
            result_entries.append(entry)

    await db.commit()
    for entry in result_entries:
        await db.refresh(entry)

    return result_entries


async def apply_json_patch(
    db: AsyncSession,
    lookup_id: uuid.UUID,
    operations: List[JsonPatchOperation],
    modified_by: Optional[str] = None,
) -> Dict[str, any]:
    lookup = await get_lookup_by_id(db, lookup_id)
    if not lookup:
        return {"success": False, "error": "Lookup not found"}

    added: List[str] = []
    replaced: List[str] = []
    removed: List[str] = []
    errors: List[str] = []

    for op in operations:
        key = op.path[1:]

        if op.op == "add":
            existing_entry = await get_entry_by_lookup_and_key(db, lookup_id, key)
            if existing_entry:
                errors.append(f"Key '{key}' already exists")
                continue

            if op.value is None:
                errors.append(f"Value is required for add operation on key '{key}'")
                continue

            entry_data = {
                "lookup_id": lookup_id,
                "key": key,
                "value": op.value,
                "created_by": modified_by,
                "modified_by": modified_by,
            }
            entry = LookupEntry(**entry_data)
            db.add(entry)
            added.append(key)

        elif op.op == "replace":
            existing_entry = await get_entry_by_lookup_and_key(db, lookup_id, key)
            if not existing_entry:
                errors.append(f"Key '{key}' not found")
                continue

            if op.value is None:
                errors.append(f"Value is required for replace operation on key '{key}'")
                continue

            existing_entry.value = op.value
            existing_entry.modified_by = modified_by
            replaced.append(key)

        elif op.op == "remove":
            deleted = await delete_entry(db, lookup_id, key)
            if deleted:
                removed.append(key)
            else:
                errors.append(f"Key '{key}' not found")

    lookup.modified_by = modified_by
    await db.commit()

    return {
        "success": len(errors) == 0,
        "added": added,
        "replaced": replaced,
        "removed": removed,
        "errors": errors if errors else None,
    }
