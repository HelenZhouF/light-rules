import uuid
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, Request, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.services.import_service import (
    process_csv_import,
    generate_accept_csv,
    generate_reject_csv,
    generate_signature_from_terms,
    parsed_condition_to_condition_create,
    parsed_action_to_action_create,
    ParsedRuleSet,
    ImportResult,
)
from app.crud.ruleset import create_ruleset_with_rules_transaction
from app.schemas.condition_action import ConditionCreate, ActionCreate

router = APIRouter(tags=["batch-import"])


MULTIPART_BOUNDARY = "batch_import_boundary"


def build_multipart_response(
    global_error: Optional[str],
    accept_csv: str,
    reject_csv: str,
    created_rulesets: List[Dict[str, Any]],
) -> StreamingResponse:
    boundary = MULTIPART_BOUNDARY
    lines = []
    
    if global_error:
        lines.append(f"--{boundary}")
        lines.append("Content-Type: application/json")
        lines.append("")
        lines.append('{"error": ' + f'"{escape_for_json(global_error)}"' + "}")
        lines.append("")
    
    if accept_csv:
        lines.append(f"--{boundary}")
        lines.append("Content-Type: text/csv; charset=utf-8")
        lines.append('Content-Disposition: attachment; filename="accepted.csv"')
        lines.append("")
        lines.append(accept_csv)
        lines.append("")
    
    if reject_csv:
        lines.append(f"--{boundary}")
        lines.append("Content-Type: text/csv; charset=utf-8")
        lines.append('Content-Disposition: attachment; filename="rejected.csv"')
        lines.append("")
        lines.append(reject_csv)
        lines.append("")
    
    if created_rulesets:
        lines.append(f"--{boundary}")
        lines.append("Content-Type: application/json")
        lines.append("")
        import json
        lines.append(json.dumps({"created_rulesets": created_rulesets}, default=str))
        lines.append("")
    
    lines.append(f"--{boundary}--")
    lines.append("")
    
    content = "\r\n".join(lines)
    
    return StreamingResponse(
        iter([content.encode("utf-8")]),
        media_type=f"multipart/mixed; boundary={boundary}",
    )


def escape_for_json(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "\\r")


def parsed_ruleset_to_db_format(
    parsed_ruleset: ParsedRuleSet,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]], List[Any]]:
    signature = generate_signature_from_terms(
        parsed_ruleset.all_term_names,
        parsed_ruleset.term_datatypes,
        default_length=100,
    )
    
    ruleset_data = {
        "id": parsed_ruleset.ruleset_id,
        "name": parsed_ruleset.ruleset_nm,
        "ruleSetType": "decision",
        "description": parsed_ruleset.ruleset_desc or None,
    }
    
    rules_data = []
    for rule_id, parsed_rule in parsed_ruleset.rules.items():
        conditions = [
            _condition_to_dict(parsed_condition_to_condition_create(c))
            for c in parsed_rule.conditions
        ]
        actions = [
            _action_to_dict(parsed_action_to_action_create(a))
            for a in parsed_rule.actions
        ]
        
        rule_data = {
            "id": rule_id,
            "name": parsed_rule.rule_nm,
            "description": parsed_rule.rule_desc or None,
            "conditional": parsed_rule.conditional,
            "order_index": parsed_rule.rule_seq_no,
            "conditions": conditions,
            "actions": actions,
        }
        rules_data.append(rule_data)
    
    return ruleset_data, rules_data, signature


def _condition_to_dict(cond: ConditionCreate) -> Dict[str, Any]:
    return {
        "term": {"name": cond.term.name, "termId": str(cond.term.termId) if cond.term.termId else None},
        "expression": cond.expression,
        "type": cond.type.value if cond.type else "expression",
        "lookup_id": str(cond.lookup_id) if cond.lookup_id else None,
    }


def _action_to_dict(action: ActionCreate) -> Dict[str, Any]:
    return {
        "term": {"name": action.term.name, "termId": str(action.term.termId) if action.term.termId else None},
        "expression": action.expression,
        "type": action.type.value if action.type else "assignment",
        "lookup_id": str(action.lookup_id) if action.lookup_id else None,
    }


def ruleset_to_response_dict(ruleset: Any) -> Dict[str, Any]:
    return {
        "id": str(ruleset.id),
        "name": ruleset.name,
        "ruleSetType": ruleset.ruleSetType,
        "description": ruleset.description,
        "version": ruleset.version,
        "major": ruleset.major,
        "minor": ruleset.minor,
        "is_locked": ruleset.is_locked,
        "created_by": ruleset.created_by,
        "created_datetime": ruleset.created_datetime.isoformat() if ruleset.created_datetime else None,
        "modified_by": ruleset.modified_by,
        "modified_datetime": ruleset.modified_datetime.isoformat() if ruleset.modified_datetime else None,
    }


@router.post("/rules")
async def batch_import_rules(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
):
    content_type = request.headers.get("content-type", "")
    if "text/csv" not in content_type:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Content-Type must be text/csv",
        )
    
    body = await request.body()
    try:
        csv_content = body.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CSV content must be UTF-8 encoded",
        )
    
    import_result = process_csv_import(csv_content)
    
    accept_csv = ""
    reject_csv = ""
    created_rulesets = []
    
    if import_result.accepted_rows:
        accept_csv = generate_accept_csv(import_result.accepted_rows)
    
    if import_result.rejected_rows:
        reject_csv = generate_reject_csv(import_result.rejected_rows)
    
    if import_result.global_error:
        return build_multipart_response(
            global_error=import_result.global_error,
            accept_csv=accept_csv,
            reject_csv=reject_csv,
            created_rulesets=[],
        )
    
    for ruleset_id, parsed_ruleset in import_result.parsed_rulesets.items():
        ruleset_data, rules_data, signature = parsed_ruleset_to_db_format(parsed_ruleset)
        
        ruleset, error = await create_ruleset_with_rules_transaction(
            db=db,
            ruleset_data=ruleset_data,
            rules_data=rules_data,
            signature=signature,
        )
        
        if ruleset:
            created_rulesets.append(ruleset_to_response_dict(ruleset))
        else:
            if import_result.global_error is None:
                import_result.global_error = f"Failed to create ruleset '{parsed_ruleset.ruleset_nm}': {error}"
            else:
                import_result.global_error += f"; Failed to create ruleset '{parsed_ruleset.ruleset_nm}': {error}"
    
    return build_multipart_response(
        global_error=import_result.global_error,
        accept_csv=accept_csv,
        reject_csv=reject_csv,
        created_rulesets=created_rulesets,
    )
