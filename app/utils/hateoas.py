import uuid
from typing import Optional

from app.schemas.ruleset import Link, ResourceLinks, PaginationLinks


API_BASE = "/api/v1/rulesets"


def build_ruleset_links(
    ruleset_id: uuid.UUID,
    is_locked: bool,
) -> ResourceLinks:
    base_url = f"{API_BASE}/{ruleset_id}"
    
    links = ResourceLinks(
        self=Link(href=base_url, method="GET"),
        rules=Link(href=f"{base_url}/rules/", method="GET"),
        revisions=Link(href=f"{base_url}/revisions", method="GET"),
    )
    
    if not is_locked:
        links.addRules = Link(href=f"{base_url}/rules/", method="POST")
        links.update = Link(href=base_url, method="PUT")
        links.delete = Link(href=base_url, method="DELETE")
        links.createRevision = Link(href=f"{base_url}/revisions", method="POST")
        links.updateOrder = Link(href=f"{base_url}/order", method="PUT")
    
    return links


def build_rule_links(
    ruleset_id: uuid.UUID,
    rule_id: uuid.UUID,
    ruleset_is_locked: bool,
) -> ResourceLinks:
    base_url = f"{API_BASE}/{ruleset_id}/rules/{rule_id}"
    ruleset_url = f"{API_BASE}/{ruleset_id}"
    
    links = ResourceLinks(
        self=Link(href=base_url, method="GET"),
        up=Link(href=ruleset_url, method="GET"),
    )
    
    if not ruleset_is_locked:
        links.update = Link(href=base_url, method="PUT")
        links.delete = Link(href=base_url, method="DELETE")
    
    return links


def build_pagination_links(
    skip: int,
    limit: int,
    total: int,
) -> PaginationLinks:
    base_url = API_BASE
    
    def build_page_url(s: int) -> str:
        return f"{base_url}?skip={s}&limit={limit}"
    
    links = PaginationLinks(
        self=Link(href=build_page_url(skip), method="GET"),
        first=Link(href=build_page_url(0), method="GET"),
    )
    
    if skip + limit < total:
        links.next = Link(href=build_page_url(skip + limit), method="GET")
    
    if skip > 0:
        prev_skip = max(0, skip - limit)
        links.prev = Link(href=build_page_url(prev_skip), method="GET")
    
    return links


def build_rule_pagination_links(
    ruleset_id: uuid.UUID,
    skip: int,
    limit: int,
    total: int,
) -> PaginationLinks:
    base_url = f"{API_BASE}/{ruleset_id}/rules"
    
    def build_page_url(s: int) -> str:
        return f"{base_url}?skip={s}&limit={limit}"
    
    links = PaginationLinks(
        self=Link(href=build_page_url(skip), method="GET"),
        first=Link(href=build_page_url(0), method="GET"),
    )
    
    if skip + limit < total:
        links.next = Link(href=build_page_url(skip + limit), method="GET")
    
    if skip > 0:
        prev_skip = max(0, skip - limit)
        links.prev = Link(href=build_page_url(prev_skip), method="GET")
    
    return links


def build_revision_links(
    ruleset_id: uuid.UUID,
    revision_id: uuid.UUID,
    is_locked: bool,
) -> ResourceLinks:
    base_url = f"{API_BASE}/{ruleset_id}/revisions/{revision_id}"
    ruleset_url = f"{API_BASE}/{ruleset_id}"
    revisions_url = f"{API_BASE}/{ruleset_id}/revisions"
    
    links = ResourceLinks(
        self=Link(href=base_url, method="GET"),
        up=Link(href=revisions_url, method="GET"),
        ruleset=Link(href=ruleset_url, method="GET"),
    )
    
    if not is_locked:
        links.createRevision = Link(href=revisions_url, method="POST")
    
    return links


def build_revision_pagination_links(
    ruleset_id: uuid.UUID,
    skip: int,
    limit: int,
    total: int,
) -> PaginationLinks:
    base_url = f"{API_BASE}/{ruleset_id}/revisions"
    
    def build_page_url(s: int) -> str:
        return f"{base_url}?skip={s}&limit={limit}"
    
    links = PaginationLinks(
        self=Link(href=build_page_url(skip), method="GET"),
        first=Link(href=build_page_url(0), method="GET"),
    )
    
    if skip + limit < total:
        links.next = Link(href=build_page_url(skip + limit), method="GET")
    
    if skip > 0:
        prev_skip = max(0, skip - limit)
        links.prev = Link(href=build_page_url(prev_skip), method="GET")
    
    return links


DOMAIN_API_BASE = "/api/v1/domains"


def build_domain_links(
    domain_id: uuid.UUID,
) -> ResourceLinks:
    base_url = f"{DOMAIN_API_BASE}/{domain_id}"
    
    links = ResourceLinks(
        self=Link(href=base_url, method="GET"),
        entries=Link(href=f"{base_url}/entries", method="GET"),
    )
    
    links.update = Link(href=base_url, method="PUT")
    links.delete = Link(href=base_url, method="DELETE")
    links.addEntries = Link(href=f"{base_url}/entries", method="POST")
    links.patchEntries = Link(href=f"{base_url}/entries", method="PATCH")
    
    return links


def build_domain_pagination_links(
    skip: int,
    limit: int,
    total: int,
) -> PaginationLinks:
    base_url = DOMAIN_API_BASE
    
    def build_page_url(s: int) -> str:
        return f"{base_url}?skip={s}&limit={limit}"
    
    links = PaginationLinks(
        self=Link(href=build_page_url(skip), method="GET"),
        first=Link(href=build_page_url(0), method="GET"),
    )
    
    if skip + limit < total:
        links.next = Link(href=build_page_url(skip + limit), method="GET")
    
    if skip > 0:
        prev_skip = max(0, skip - limit)
        links.prev = Link(href=build_page_url(prev_skip), method="GET")
    
    return links
