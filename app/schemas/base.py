from typing import Optional

from pydantic import BaseModel, Field


class Link(BaseModel):
    href: str
    method: str = "GET"


class ResourceLinks(BaseModel):
    self: Link
    addRules: Optional[Link] = None
    update: Optional[Link] = None
    delete: Optional[Link] = None

    model_config = {
        "exclude_none": True,
    }


class PaginationLinks(BaseModel):
    self: Link
    next: Optional[Link] = None
    prev: Optional[Link] = None
    first: Link

    model_config = {
        "exclude_none": True,
    }
