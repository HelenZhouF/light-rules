import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.schemas.lookup import (
    LookupCreate,
    LookupUpdate,
    LookupResponse,
    LookupResponseData,
    LookupDetailResponse,
    LookupListResponse,
    LookupEntryCreate,
    LookupEntryResponse,
    LookupEntryResponseData,
    LookupEntryListResponse,
    JsonPatchOperation,
)
from app.crud.lookup import (
    get_lookup_by_id,
    get_lookup_with_entries,
    get_lookup_by_name,
    get_lookups,
    count_lookups,
    create_lookup,
    update_lookup,
    delete_lookup,
    get_entries_by_lookup_id,
    count_entries,
    create_entry,
    batch_create_entries,
    batch_upsert_entries,
    apply_json_patch,
)
from app.utils.hateoas import (
    build_domain_links,
    build_domain_pagination_links,
    build_entry_links,
    build_entry_pagination_links,
)

router = APIRouter(prefix="/domains", tags=["domains"])


def domain_to_response(lookup) -> dict:
    data = LookupResponseData.model_validate(lookup)
    links = build_domain_links(lookup.id)
    response = LookupResponse(**data.model_dump(), _links=links)
    return response.model_dump(by_alias=True, exclude_none=True)


def domain_to_detail_response(lookup) -> dict:
    data = LookupResponseData.model_validate(lookup)
    links = build_domain_links(lookup.id)

    entries_responses = []
    for entry in lookup.entries:
        entry_response = entry_to_response(lookup.id, entry)
        entries_responses.append(entry_response)

    response = LookupDetailResponse(
        **data.model_dump(),
        entries=[],
        _links=links,
    )
    result = response.model_dump(by_alias=True, exclude_none=True)
    result["entries"] = entries_responses
    return result


def entry_to_response(domain_id: uuid.UUID, entry) -> dict:
    data = LookupEntryResponseData.model_validate(entry)
    links = build_entry_links(domain_id, entry.key)
    response = LookupEntryResponse(**data.model_dump(), _links=links)
    return response.model_dump(by_alias=True, exclude_none=True)


@router.get("/", response_model=dict, status_code=status.HTTP_200_OK)
async def read_domains(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_async_session),
):
    total = await count_lookups(db)
    lookups = await get_lookups(db, skip=skip, limit=limit)

    items = [domain_to_response(l) for l in lookups]
    pagination_links = build_domain_pagination_links(skip, limit, total)

    response = LookupListResponse(
        items=[],
        _links=pagination_links,
        total=total,
        skip=skip,
        limit=limit,
    )
    result = response.model_dump(by_alias=True, exclude_none=True)
    result["items"] = items
    return result


@router.get("/{domain_id}", response_model=dict, status_code=status.HTTP_200_OK)
async def read_domain(
    domain_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_session),
):
    lookup = await get_lookup_with_entries(db, lookup_id=domain_id)
    if lookup is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Domain not found",
        )
    return domain_to_detail_response(lookup)


@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_new_domain(
    lookup_in: LookupCreate,
    db: AsyncSession = Depends(get_async_session),
):
    existing_lookup = await get_lookup_by_name(db, name=lookup_in.name)
    if existing_lookup:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Domain with this name already exists",
        )

    lookup = await create_lookup(db=db, lookup_in=lookup_in)
    return domain_to_response(lookup)


@router.put("/{domain_id}", response_model=dict, status_code=status.HTTP_200_OK)
async def update_existing_domain(
    domain_id: uuid.UUID,
    lookup_in: LookupUpdate,
    db: AsyncSession = Depends(get_async_session),
):
    lookup = await get_lookup_by_id(db, lookup_id=domain_id)
    if lookup is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Domain not found",
        )

    if lookup_in.name and lookup_in.name != lookup.name:
        existing_lookup = await get_lookup_by_name(db, name=lookup_in.name)
        if existing_lookup:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Domain with this name already exists",
            )

    updated_lookup = await update_lookup(
        db=db,
        lookup_id=domain_id,
        lookup_in=lookup_in,
    )
    return domain_to_response(updated_lookup)


@router.delete("/{domain_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_existing_domain(
    domain_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_session),
):
    lookup = await get_lookup_by_id(db, lookup_id=domain_id)
    if lookup is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Domain not found",
        )

    await delete_lookup(db=db, lookup_id=domain_id)
    return None


@router.get("/{domain_id}/entries", response_model=dict, status_code=status.HTTP_200_OK)
async def read_entries(
    domain_id: uuid.UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_async_session),
):
    lookup = await get_lookup_by_id(db, lookup_id=domain_id)
    if lookup is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Domain not found",
        )

    total = await count_entries(db, lookup_id=domain_id)
    entries = await get_entries_by_lookup_id(db, lookup_id=domain_id, skip=skip, limit=limit)

    items = [entry_to_response(domain_id, e) for e in entries]
    pagination_links = build_entry_pagination_links(domain_id, skip, limit, total)

    response = LookupEntryListResponse(
        items=[],
        _links=pagination_links,
        total=total,
        skip=skip,
        limit=limit,
    )
    result = response.model_dump(by_alias=True, exclude_none=True)
    result["items"] = items
    return result


@router.post("/{domain_id}/entries", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_entries_batch(
    domain_id: uuid.UUID,
    entries: List[LookupEntryCreate],
    db: AsyncSession = Depends(get_async_session),
):
    lookup = await get_lookup_by_id(db, lookup_id=domain_id)
    if lookup is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Domain not found",
        )

    created_entries = await batch_upsert_entries(
        db=db,
        lookup_id=domain_id,
        entries_in=entries,
    )

    items = [entry_to_response(domain_id, e) for e in created_entries]
    return {
        "success": True,
        "items": items,
        "_links": {
            "self": {"href": f"/api/v1/domains/{domain_id}/entries", "method": "POST"},
            "up": {"href": f"/api/v1/domains/{domain_id}", "method": "GET"},
        }
    }


@router.patch("/{domain_id}/entries", response_model=dict, status_code=status.HTTP_200_OK)
async def patch_entries(
    domain_id: uuid.UUID,
    operations: List[JsonPatchOperation],
    db: AsyncSession = Depends(get_async_session),
):
    lookup = await get_lookup_by_id(db, lookup_id=domain_id)
    if lookup is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Domain not found",
        )

    result = await apply_json_patch(
        db=db,
        lookup_id=domain_id,
        operations=operations,
    )

    if not result["success"] and result.get("errors"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["errors"],
        )

    updated_lookup = await get_lookup_with_entries(db, lookup_id=domain_id)
    return domain_to_detail_response(updated_lookup)
