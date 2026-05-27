import uuid
from typing import Optional

from app.schemas.ruleset import Link, ResourceLinks, PaginationLinks


API_BASE = "/api/v1/rulesets"
RULESET_MEDIA_TYPE = "application/vnd.sas.business.rule.ruleset"
RULESET_LIST_MEDIA_TYPE = "application/vnd.sas.business.rule.ruleset.list"
RULE_MEDIA_TYPE = "application/vnd.sas.business.rule"
REVISION_MEDIA_TYPE = "application/vnd.sas.business.rule.revision"
DOMAIN_MEDIA_TYPE = "application/vnd.sas.business.rule.domain"
DOMAIN_LIST_MEDIA_TYPE = "application/vnd.sas.business.rule.domain.list"


def build_ruleset_links(
    ruleset_id: uuid.UUID,
    is_locked: bool,
) -> ResourceLinks:
    base_url = f"{API_BASE}/{ruleset_id}"

    links = ResourceLinks(
        self=Link(href=base_url, method="GET", uri=base_url, type=RULESET_MEDIA_TYPE),
        rules=Link(href=f"{base_url}/rules/", method="GET", uri=f"{base_url}/rules/", type=RULE_MEDIA_TYPE),
        revisions=Link(href=f"{base_url}/revisions", method="GET", uri=f"{base_url}/revisions", type=REVISION_MEDIA_TYPE),
    )

    if not is_locked:
        links.addRules = Link(href=f"{base_url}/rules/", method="POST", uri=f"{base_url}/rules/", type=RULE_MEDIA_TYPE)
        links.update = Link(href=base_url, method="PUT", uri=base_url, type=RULESET_MEDIA_TYPE)
        links.delete = Link(href=base_url, method="DELETE", uri=base_url, type=RULESET_MEDIA_TYPE)
        links.createRevision = Link(href=f"{base_url}/revisions", method="POST", uri=f"{base_url}/revisions", type=REVISION_MEDIA_TYPE)
        links.updateOrder = Link(href=f"{base_url}/order", method="PUT", uri=f"{base_url}/order", type=RULESET_MEDIA_TYPE)

    return links


def build_rule_links(
    ruleset_id: uuid.UUID,
    rule_id: uuid.UUID,
    ruleset_is_locked: bool,
) -> ResourceLinks:
    base_url = f"{API_BASE}/{ruleset_id}/rules/{rule_id}"
    ruleset_url = f"{API_BASE}/{ruleset_id}"

    links = ResourceLinks(
        self=Link(href=base_url, method="GET", uri=base_url, type=RULE_MEDIA_TYPE),
        up=Link(href=ruleset_url, method="GET", uri=ruleset_url, type=RULESET_MEDIA_TYPE),
    )

    if not ruleset_is_locked:
        links.update = Link(href=base_url, method="PUT", uri=base_url, type=RULE_MEDIA_TYPE)
        links.delete = Link(href=base_url, method="DELETE", uri=base_url, type=RULE_MEDIA_TYPE)

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
        self=Link(href=build_page_url(skip), method="GET", uri=build_page_url(skip), type=RULESET_LIST_MEDIA_TYPE),
        first=Link(href=build_page_url(0), method="GET", uri=build_page_url(0), type=RULESET_LIST_MEDIA_TYPE),
    )

    if skip + limit < total:
        links.next = Link(href=build_page_url(skip + limit), method="GET", uri=build_page_url(skip + limit), type=RULESET_LIST_MEDIA_TYPE)

    if skip > 0:
        prev_skip = max(0, skip - limit)
        links.prev = Link(href=build_page_url(prev_skip), method="GET", uri=build_page_url(prev_skip), type=RULESET_LIST_MEDIA_TYPE)

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
        self=Link(href=build_page_url(skip), method="GET", uri=build_page_url(skip), type=RULE_MEDIA_TYPE),
        first=Link(href=build_page_url(0), method="GET", uri=build_page_url(0), type=RULE_MEDIA_TYPE),
    )

    if skip + limit < total:
        links.next = Link(href=build_page_url(skip + limit), method="GET", uri=build_page_url(skip + limit), type=RULE_MEDIA_TYPE)

    if skip > 0:
        prev_skip = max(0, skip - limit)
        links.prev = Link(href=build_page_url(prev_skip), method="GET", uri=build_page_url(prev_skip), type=RULE_MEDIA_TYPE)

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
        self=Link(href=base_url, method="GET", uri=base_url, type=REVISION_MEDIA_TYPE),
        up=Link(href=revisions_url, method="GET", uri=revisions_url, type=REVISION_MEDIA_TYPE),
        ruleset=Link(href=ruleset_url, method="GET", uri=ruleset_url, type=RULESET_MEDIA_TYPE),
    )

    if not is_locked:
        links.createRevision = Link(href=revisions_url, method="POST", uri=revisions_url, type=REVISION_MEDIA_TYPE)

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
        self=Link(href=build_page_url(skip), method="GET", uri=build_page_url(skip), type=REVISION_MEDIA_TYPE),
        first=Link(href=build_page_url(0), method="GET", uri=build_page_url(0), type=REVISION_MEDIA_TYPE),
    )

    if skip + limit < total:
        links.next = Link(href=build_page_url(skip + limit), method="GET", uri=build_page_url(skip + limit), type=REVISION_MEDIA_TYPE)

    if skip > 0:
        prev_skip = max(0, skip - limit)
        links.prev = Link(href=build_page_url(prev_skip), method="GET", uri=build_page_url(prev_skip), type=REVISION_MEDIA_TYPE)

    return links


DOMAIN_API_BASE = "/api/v1/domains"


def build_domain_links(
    domain_id: uuid.UUID,
) -> ResourceLinks:
    base_url = f"{DOMAIN_API_BASE}/{domain_id}"

    links = ResourceLinks(
        self=Link(href=base_url, method="GET", uri=base_url, type=DOMAIN_MEDIA_TYPE),
        entries=Link(href=f"{base_url}/entries", method="GET", uri=f"{base_url}/entries", type=DOMAIN_MEDIA_TYPE),
    )

    links.update = Link(href=base_url, method="PUT", uri=base_url, type=DOMAIN_MEDIA_TYPE)
    links.delete = Link(href=base_url, method="DELETE", uri=base_url, type=DOMAIN_MEDIA_TYPE)
    links.addEntries = Link(href=f"{base_url}/entries", method="POST", uri=f"{base_url}/entries", type=DOMAIN_MEDIA_TYPE)
    links.patchEntries = Link(href=f"{base_url}/entries", method="PATCH", uri=f"{base_url}/entries", type=DOMAIN_MEDIA_TYPE)

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
        self=Link(href=build_page_url(skip), method="GET", uri=build_page_url(skip), type=DOMAIN_LIST_MEDIA_TYPE),
        first=Link(href=build_page_url(0), method="GET", uri=build_page_url(0), type=DOMAIN_LIST_MEDIA_TYPE),
    )

    if skip + limit < total:
        links.next = Link(href=build_page_url(skip + limit), method="GET", uri=build_page_url(skip + limit), type=DOMAIN_LIST_MEDIA_TYPE)

    if skip > 0:
        prev_skip = max(0, skip - limit)
        links.prev = Link(href=build_page_url(prev_skip), method="GET", uri=build_page_url(prev_skip), type=DOMAIN_LIST_MEDIA_TYPE)

    return links


FUNCTION_CATEGORY_API_BASE = "/api/v1/function-categories"
FUNCTION_CATEGORY_MEDIA_TYPE = "application/vnd.sas.business.rule.function.category"
FUNCTION_CATEGORY_LIST_MEDIA_TYPE = "application/vnd.sas.business.rule.function.category.list"

FUNCTION_API_BASE = "/api/v1/functions"
FUNCTION_MEDIA_TYPE = "application/vnd.sas.business.rule.function"
FUNCTION_LIST_MEDIA_TYPE = "application/vnd.sas.business.rule.function.list"
FUNCTION_VALIDATION_MEDIA_TYPE = "application/vnd.sas.business.rule.function+json"


def build_function_category_links(
    category_id: uuid.UUID,
) -> ResourceLinks:
    base_url = f"{FUNCTION_CATEGORY_API_BASE}/{category_id}"
    
    links = ResourceLinks(
        self=Link(href=base_url, method="GET", uri=base_url, type=FUNCTION_CATEGORY_MEDIA_TYPE),
        update=Link(href=base_url, method="PUT", uri=base_url, type=FUNCTION_CATEGORY_MEDIA_TYPE),
        delete=Link(href=base_url, method="DELETE", uri=base_url, type=FUNCTION_CATEGORY_MEDIA_TYPE),
        functions=Link(
            href=f"{base_url}/functions",
            method="GET",
            uri=f"{base_url}/functions",
            type=FUNCTION_CATEGORY_MEDIA_TYPE
        ),
    )
    
    return links


def build_function_category_pagination_links(
    skip: int,
    limit: int,
    total: int,
) -> PaginationLinks:
    base_url = FUNCTION_CATEGORY_API_BASE
    
    def build_page_url(s: int) -> str:
        return f"{base_url}?skip={s}&limit={limit}"
    
    links = PaginationLinks(
        self=Link(
            href=build_page_url(skip),
            method="GET",
            uri=build_page_url(skip),
            type=FUNCTION_CATEGORY_LIST_MEDIA_TYPE
        ),
        first=Link(
            href=build_page_url(0),
            method="GET",
            uri=build_page_url(0),
            type=FUNCTION_CATEGORY_LIST_MEDIA_TYPE
        ),
    )
    
    if skip + limit < total:
        next_url = build_page_url(skip + limit)
        links.next = Link(
            href=next_url,
            method="GET",
            uri=next_url,
            type=FUNCTION_CATEGORY_LIST_MEDIA_TYPE
        )
    
    if skip > 0:
        prev_skip = max(0, skip - limit)
        prev_url = build_page_url(prev_skip)
        links.prev = Link(
            href=prev_url,
            method="GET",
            uri=prev_url,
            type=FUNCTION_CATEGORY_LIST_MEDIA_TYPE
        )
    
    return links


def build_function_links(
    function_id: uuid.UUID,
    category_id: uuid.UUID,
) -> ResourceLinks:
    base_url = f"{FUNCTION_CATEGORY_API_BASE}/{category_id}/functions/{function_id}"
    category_url = f"{FUNCTION_CATEGORY_API_BASE}/{category_id}"
    
    links = ResourceLinks(
        self=Link(href=base_url, method="GET", uri=base_url, type=FUNCTION_MEDIA_TYPE),
        update=Link(href=base_url, method="PUT", uri=base_url, type=FUNCTION_MEDIA_TYPE),
        delete=Link(href=base_url, method="DELETE", uri=base_url, type=FUNCTION_MEDIA_TYPE),
        category=Link(href=category_url, method="GET", uri=category_url, type=FUNCTION_CATEGORY_MEDIA_TYPE),
    )
    
    return links


def build_function_pagination_links(
    category_id: uuid.UUID,
    skip: int,
    limit: int,
    total: int,
) -> PaginationLinks:
    base_url = f"{FUNCTION_CATEGORY_API_BASE}/{category_id}/functions"
    
    def build_page_url(s: int) -> str:
        return f"{base_url}?skip={s}&limit={limit}"
    
    links = PaginationLinks(
        self=Link(
            href=build_page_url(skip),
            method="GET",
            uri=build_page_url(skip),
            type=FUNCTION_LIST_MEDIA_TYPE
        ),
        first=Link(
            href=build_page_url(0),
            method="GET",
            uri=build_page_url(0),
            type=FUNCTION_LIST_MEDIA_TYPE
        ),
    )
    
    if skip + limit < total:
        next_url = build_page_url(skip + limit)
        links.next = Link(
            href=next_url,
            method="GET",
            uri=next_url,
            type=FUNCTION_LIST_MEDIA_TYPE
        )
    
    if skip > 0:
        prev_skip = max(0, skip - limit)
        prev_url = build_page_url(prev_skip)
        links.prev = Link(
            href=prev_url,
            method="GET",
            uri=prev_url,
            type=FUNCTION_LIST_MEDIA_TYPE
        )
    
    return links
