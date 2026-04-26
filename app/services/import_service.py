import csv
import io
import re
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from app.schemas.signature import SignatureTerm, DataType, Direction
from app.schemas.condition_action import (
    ConditionCreate,
    ActionCreate,
    TermRef,
    ConditionType,
    ActionType,
)


CSV_COLUMNS = [
    "ruleset_id",
    "ruleset_nm",
    "ruleset_desc",
    "rule_id",
    "rule_nm",
    "rule_desc",
    "rule_seq_no",
    "conditional",
    "datatype",
    "lhs_term",
    "expression",
    "expression_type",
    "expression_order",
]


@dataclass
class CSVRow:
    line_number: int
    ruleset_id: str
    ruleset_nm: str
    ruleset_desc: str
    rule_id: str
    rule_nm: str
    rule_desc: str
    rule_seq_no: str
    conditional: str
    datatype: str
    lhs_term: str
    expression: str
    expression_type: str
    expression_order: str
    raw: Dict[str, str]


@dataclass
class ValidatedRow:
    row: CSVRow
    errors: List[str] = field(default_factory=list)
    
    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0


@dataclass
class ParsedCondition:
    term_name: str
    expression: str
    order: int
    datatype: str


@dataclass
class ParsedAction:
    term_name: str
    expression: str
    order: int
    datatype: str


@dataclass
class ParsedRule:
    rule_id: uuid.UUID
    rule_nm: str
    rule_desc: str
    rule_seq_no: int
    conditional: str
    conditions: List[ParsedCondition] = field(default_factory=list)
    actions: List[ParsedAction] = field(default_factory=list)
    term_names: Set[str] = field(default_factory=set)


@dataclass
class ParsedRuleSet:
    ruleset_id: uuid.UUID
    ruleset_nm: str
    ruleset_desc: str
    rules: Dict[uuid.UUID, ParsedRule] = field(default_factory=dict)
    all_term_names: Set[str] = field(default_factory=set)
    term_datatypes: Dict[str, str] = field(default_factory=dict)


@dataclass
class ImportResult:
    accepted_rows: List[ValidatedRow] = field(default_factory=list)
    rejected_rows: List[ValidatedRow] = field(default_factory=list)
    parsed_rulesets: Dict[uuid.UUID, ParsedRuleSet] = field(default_factory=dict)
    global_error: Optional[str] = None


def unescape_csv_expression(expr: str) -> str:
    if not expr:
        return expr
    
    if expr.startswith("'") and expr.endswith("'"):
        inner = expr[1:-1]
        inner = inner.replace("''", "'")
        return inner
    
    if expr.startswith('"') and expr.endswith('"'):
        inner = expr[1:-1]
        inner = inner.replace('""', '"')
        return inner
    
    return expr


def parse_csv_content(content: str) -> Tuple[List[CSVRow], Optional[str]]:
    rows = []
    
    try:
        content_io = io.StringIO(content)
        reader = csv.DictReader(content_io)
        
        actual_columns = reader.fieldnames if reader.fieldnames else []
        actual_lower = [col.lower().strip() for col in actual_columns]
        expected_lower = [col.lower() for col in CSV_COLUMNS]
        
        if len(actual_lower) < len(expected_lower):
            missing = set(expected_lower) - set(actual_lower)
            return [], f"Missing required columns: {', '.join(missing)}"
        
        column_mapping = {}
        for expected in CSV_COLUMNS:
            expected_lower = expected.lower()
            for i, actual in enumerate(actual_columns):
                if actual.lower().strip() == expected_lower:
                    column_mapping[expected] = actual
                    break
        
        for line_number, row_dict in enumerate(reader, start=2):
            row = CSVRow(
                line_number=line_number,
                ruleset_id=row_dict.get(column_mapping.get("ruleset_id", "ruleset_id"), "").strip(),
                ruleset_nm=row_dict.get(column_mapping.get("ruleset_nm", "ruleset_nm"), "").strip(),
                ruleset_desc=row_dict.get(column_mapping.get("ruleset_desc", "ruleset_desc"), "").strip(),
                rule_id=row_dict.get(column_mapping.get("rule_id", "rule_id"), "").strip(),
                rule_nm=row_dict.get(column_mapping.get("rule_nm", "rule_nm"), "").strip(),
                rule_desc=row_dict.get(column_mapping.get("rule_desc", "rule_desc"), "").strip(),
                rule_seq_no=row_dict.get(column_mapping.get("rule_seq_no", "rule_seq_no"), "").strip(),
                conditional=row_dict.get(column_mapping.get("conditional", "conditional"), "").strip(),
                datatype=row_dict.get(column_mapping.get("datatype", "datatype"), "").strip(),
                lhs_term=row_dict.get(column_mapping.get("lhs_term", "lhs_term"), "").strip(),
                expression=row_dict.get(column_mapping.get("expression", "expression"), "").strip(),
                expression_type=row_dict.get(column_mapping.get("expression_type", "expression_type"), "").strip(),
                expression_order=row_dict.get(column_mapping.get("expression_order", "expression_order"), "").strip(),
                raw=row_dict,
            )
            rows.append(row)
        
        return rows, None
        
    except csv.Error as e:
        return [], f"CSV parsing error: {str(e)}"
    except Exception as e:
        return [], f"Error parsing CSV: {str(e)}"


def validate_row(row: CSVRow) -> ValidatedRow:
    errors = []
    
    if not row.ruleset_id:
        errors.append("ruleset_id is required")
    else:
        try:
            uuid.UUID(row.ruleset_id)
        except ValueError:
            errors.append(f"ruleset_id '{row.ruleset_id}' is not a valid UUID")
    
    if not row.ruleset_nm:
        errors.append("ruleset_nm is required")
    elif len(row.ruleset_nm) > 255:
        errors.append("ruleset_nm exceeds maximum length of 255")
    
    if row.ruleset_desc and len(row.ruleset_desc) > 1000:
        errors.append("ruleset_desc exceeds maximum length of 1000")
    
    if not row.rule_id:
        errors.append("rule_id is required")
    else:
        try:
            uuid.UUID(row.rule_id)
        except ValueError:
            errors.append(f"rule_id '{row.rule_id}' is not a valid UUID")
    
    if not row.rule_nm:
        errors.append("rule_nm is required")
    elif len(row.rule_nm) > 255:
        errors.append("rule_nm exceeds maximum length of 255")
    
    if row.rule_desc and len(row.rule_desc) > 1000:
        errors.append("rule_desc exceeds maximum length of 1000")
    
    if not row.rule_seq_no:
        errors.append("rule_seq_no is required")
    else:
        try:
            seq = int(row.rule_seq_no)
            if seq < 0:
                errors.append("rule_seq_no must be a non-negative integer")
        except ValueError:
            errors.append(f"rule_seq_no '{row.rule_seq_no}' is not a valid integer")
    
    if not row.conditional:
        errors.append("conditional is required")
    
    if not row.datatype:
        errors.append("datatype is required")
    else:
        valid_datatypes = [dt.value for dt in DataType]
        if row.datatype.lower() not in [dt.lower() for dt in valid_datatypes]:
            errors.append(f"datatype '{row.datatype}' is not valid. Valid types: {', '.join(valid_datatypes)}")
    
    if not row.lhs_term:
        errors.append("lhs_term is required")
    elif len(row.lhs_term) > 255:
        errors.append("lhs_term exceeds maximum length of 255")
    
    if not row.expression_type:
        errors.append("expression_type is required")
    else:
        valid_types = ["CONDITION", "ACTION"]
        if row.expression_type.upper() not in valid_types:
            errors.append(f"expression_type '{row.expression_type}' is not valid. Valid types: {', '.join(valid_types)}")
    
    if not row.expression_order:
        errors.append("expression_order is required")
    else:
        try:
            order = int(row.expression_order)
            if order < 1:
                errors.append("expression_order must be a positive integer")
        except ValueError:
            errors.append(f"expression_order '{row.expression_order}' is not a valid integer")
    
    return ValidatedRow(row=row, errors=errors)


def validate_all_rows(rows: List[CSVRow]) -> Tuple[List[ValidatedRow], List[ValidatedRow]]:
    validated = [validate_row(row) for row in rows]
    accepted = [v for v in validated if v.is_valid]
    rejected = [v for v in validated if not v.is_valid]
    return accepted, rejected


def group_rows_by_ruleset(validated_rows: List[ValidatedRow]) -> Dict[uuid.UUID, ParsedRuleSet]:
    rulesets: Dict[uuid.UUID, ParsedRuleSet] = {}
    
    for validated in validated_rows:
        row = validated.row
        
        ruleset_id = uuid.UUID(row.ruleset_id)
        rule_id = uuid.UUID(row.rule_id)
        
        if ruleset_id not in rulesets:
            rulesets[ruleset_id] = ParsedRuleSet(
                ruleset_id=ruleset_id,
                ruleset_nm=row.ruleset_nm,
                ruleset_desc=row.ruleset_desc,
            )
        
        ruleset = rulesets[ruleset_id]
        
        if row.lhs_term:
            ruleset.all_term_names.add(row.lhs_term)
            ruleset.term_datatypes[row.lhs_term] = row.datatype
        
        if rule_id not in ruleset.rules:
            try:
                rule_seq_no = int(row.rule_seq_no)
            except ValueError:
                rule_seq_no = 0
            
            ruleset.rules[rule_id] = ParsedRule(
                rule_id=rule_id,
                rule_nm=row.rule_nm,
                rule_desc=row.rule_desc,
                rule_seq_no=rule_seq_no,
                conditional=row.conditional,
            )
        
        rule = ruleset.rules[rule_id]
        rule.term_names.add(row.lhs_term)
        
        unescaped_expression = unescape_csv_expression(row.expression)
        
        try:
            expression_order = int(row.expression_order)
        except ValueError:
            expression_order = 1
        
        if row.expression_type.upper() == "CONDITION":
            parsed_condition = ParsedCondition(
                term_name=row.lhs_term,
                expression=unescaped_expression,
                order=expression_order,
                datatype=row.datatype,
            )
            rule.conditions.append(parsed_condition)
        elif row.expression_type.upper() == "ACTION":
            parsed_action = ParsedAction(
                term_name=row.lhs_term,
                expression=unescaped_expression,
                order=expression_order,
                datatype=row.datatype,
            )
            rule.actions.append(parsed_action)
    
    for ruleset in rulesets.values():
        for rule in ruleset.rules.values():
            rule.conditions.sort(key=lambda c: c.order)
            rule.actions.sort(key=lambda a: a.order)
    
    return rulesets


def generate_signature_from_terms(
    term_names: Set[str],
    term_datatypes: Dict[str, str],
    default_length: int = 100,
) -> List[SignatureTerm]:
    signature = []
    
    for term_name in term_names:
        datatype_str = term_datatypes.get(term_name, "string").lower()
        
        try:
            data_type = DataType(datatype_str)
        except ValueError:
            data_type = DataType.STRING
        
        term_kwargs = {
            "name": term_name,
            "dataType": data_type,
        }
        
        if data_type == DataType.STRING:
            term_kwargs["length"] = default_length
        elif data_type == DataType.DECIMAL:
            term_kwargs["length"] = default_length
        
        signature.append(SignatureTerm(**term_kwargs))
    
    return signature


def parsed_condition_to_condition_create(
    condition: ParsedCondition,
) -> ConditionCreate:
    return ConditionCreate(
        term=TermRef(name=condition.term_name),
        expression=condition.expression,
        type=ConditionType.EXPRESSION,
    )


def parsed_action_to_action_create(
    action: ParsedAction,
) -> ActionCreate:
    return ActionCreate(
        term=TermRef(name=action.term_name),
        expression=action.expression,
        type=ActionType.ASSIGNMENT,
    )


def process_csv_import(content: str) -> ImportResult:
    rows, parse_error = parse_csv_content(content)
    
    if parse_error:
        return ImportResult(global_error=parse_error)
    
    if not rows:
        return ImportResult(global_error="CSV file is empty or contains no data rows")
    
    accepted, rejected = validate_all_rows(rows)
    
    if not accepted:
        return ImportResult(
            accepted_rows=[],
            rejected_rows=rejected,
            global_error="All rows were rejected during validation" if rejected else None,
        )
    
    rulesets = group_rows_by_ruleset(accepted)
    
    return ImportResult(
        accepted_rows=accepted,
        rejected_rows=rejected,
        parsed_rulesets=rulesets,
    )


def generate_accept_csv(accepted_rows: List[ValidatedRow]) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow(CSV_COLUMNS)
    
    for validated in accepted_rows:
        row = validated.row
        writer.writerow([
            row.ruleset_id,
            row.ruleset_nm,
            row.ruleset_desc,
            row.rule_id,
            row.rule_nm,
            row.rule_desc,
            row.rule_seq_no,
            row.conditional,
            row.datatype,
            row.lhs_term,
            row.expression,
            row.expression_type,
            row.expression_order,
        ])
    
    return output.getvalue()


def generate_reject_csv(rejected_rows: List[ValidatedRow]) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    
    header = CSV_COLUMNS + ["errors"]
    writer.writerow(header)
    
    for validated in rejected_rows:
        row = validated.row
        errors_str = "; ".join(validated.errors)
        writer.writerow([
            row.ruleset_id,
            row.ruleset_nm,
            row.ruleset_desc,
            row.rule_id,
            row.rule_nm,
            row.rule_desc,
            row.rule_seq_no,
            row.conditional,
            row.datatype,
            row.lhs_term,
            row.expression,
            row.expression_type,
            row.expression_order,
            errors_str,
        ])
    
    return output.getvalue()


def filter_rows_by_ruleset(
    rows: List[ValidatedRow],
    ruleset_ids: Set[uuid.UUID],
) -> List[ValidatedRow]:
    return [
        row for row in rows 
        if uuid.UUID(row.row.ruleset_id) in ruleset_ids
    ]


def add_error_to_rows(
    rows: List[ValidatedRow],
    error_message: str,
) -> List[ValidatedRow]:
    result = []
    for validated in rows:
        new_errors = list(validated.errors)
        new_errors.append(error_message)
        result.append(ValidatedRow(row=validated.row, errors=new_errors))
    return result


def separate_accept_reject_by_creation_result(
    accepted_rows: List[ValidatedRow],
    rejected_rows: List[ValidatedRow],
    created_ruleset_ids: Set[uuid.UUID],
    failed_rulesets: Dict[uuid.UUID, str],
) -> Tuple[List[ValidatedRow], List[ValidatedRow]]:
    final_accepted = []
    final_rejected = list(rejected_rows)
    
    for validated in accepted_rows:
        ruleset_id = uuid.UUID(validated.row.ruleset_id)
        
        if ruleset_id in created_ruleset_ids:
            final_accepted.append(validated)
        elif ruleset_id in failed_rulesets:
            error_msg = failed_rulesets[ruleset_id]
            new_errors = list(validated.errors)
            new_errors.append(f"Import failed: {error_msg}")
            final_rejected.append(ValidatedRow(row=validated.row, errors=new_errors))
        else:
            final_accepted.append(validated)
    
    return final_accepted, final_rejected
