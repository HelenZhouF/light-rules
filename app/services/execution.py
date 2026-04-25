import re
import uuid
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

from app.schemas.signature import DataType, Direction


class ExecutionError(Exception):
    pass


class InvalidInputError(ExecutionError):
    pass


class ExpressionEvaluationError(ExecutionError):
    pass


class TermNotFoundError(ExecutionError):
    pass


class ComparisonOperator(str, Enum):
    EQ = "=="
    NE = "!="
    GT = ">"
    LT = "<"
    GE = ">="
    LE = "<="


COMPARISON_OPERATORS = [
    (">=", ComparisonOperator.GE),
    ("<=", ComparisonOperator.LE),
    ("==", ComparisonOperator.EQ),
    ("!=", ComparisonOperator.NE),
    (">", ComparisonOperator.GT),
    ("<", ComparisonOperator.LT),
    ("=", ComparisonOperator.EQ),
]


def parse_comparison_expression(expression: str) -> Tuple[ComparisonOperator, str]:
    expression = expression.strip()
    
    for op_str, op in COMPARISON_OPERATORS:
        if expression.startswith(op_str):
            value = expression[len(op_str):].strip()
            return op, value
    
    return ComparisonOperator.EQ, expression


def _strip_quotes(value_str: str) -> str:
    value_str = value_str.strip()
    if (value_str.startswith("'") and value_str.endswith("'")) or \
       (value_str.startswith('"') and value_str.endswith('"')):
        return value_str[1:-1].strip()
    return value_str


def parse_value(value_str: str, data_type: DataType) -> Any:
    value_str = value_str.strip()
    
    if data_type == DataType.STRING:
        return _strip_quotes(value_str)
    
    if data_type == DataType.BOOLEAN:
        lower_val = _strip_quotes(value_str).lower()
        if lower_val in ("true", "1", "yes"):
            return True
        if lower_val in ("false", "0", "no"):
            return False
        return bool(value_str)
    
    if data_type == DataType.DECIMAL:
        try:
            return Decimal(_strip_quotes(value_str))
        except InvalidOperation:
            raise ExpressionEvaluationError(f"Invalid decimal value: {value_str}")
    
    if data_type == DataType.DATE:
        try:
            return date.fromisoformat(_strip_quotes(value_str))
        except ValueError:
            raise ExpressionEvaluationError(f"Invalid date value: {value_str} (expected YYYY-MM-DD)")
    
    if data_type == DataType.DATETIME:
        try:
            return datetime.fromisoformat(_strip_quotes(value_str))
        except ValueError:
            raise ExpressionEvaluationError(f"Invalid datetime value: {value_str} (expected ISO format)")
    
    return value_str


def convert_input_value(value: Any, data_type: DataType) -> Any:
    if value is None:
        return None
    
    if data_type == DataType.STRING:
        return str(value)
    
    if data_type == DataType.BOOLEAN:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            lower_val = value.lower()
            if lower_val in ("true", "1", "yes"):
                return True
            if lower_val in ("false", "0", "no"):
                return False
        return bool(value)
    
    if data_type == DataType.DECIMAL:
        if isinstance(value, Decimal):
            return value
        if isinstance(value, (int, float)):
            return Decimal(str(value))
        if isinstance(value, str):
            try:
                return Decimal(value)
            except InvalidOperation:
                raise InvalidInputError(f"Invalid decimal value: {value}")
        raise InvalidInputError(f"Cannot convert {type(value)} to decimal")
    
    if data_type == DataType.DATE:
        if isinstance(value, date):
            return value
        if isinstance(value, str):
            try:
                return date.fromisoformat(value)
            except ValueError:
                raise InvalidInputError(f"Invalid date value: {value} (expected YYYY-MM-DD)")
        raise InvalidInputError(f"Cannot convert {type(value)} to date")
    
    if data_type == DataType.DATETIME:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                raise InvalidInputError(f"Invalid datetime value: {value} (expected ISO format)")
        raise InvalidInputError(f"Cannot convert {type(value)} to datetime")
    
    return value


def compare_values(
    left: Any, 
    right: Any, 
    operator: ComparisonOperator,
    data_type: DataType
) -> bool:
    if data_type == DataType.DECIMAL:
        left = Decimal(str(left)) if not isinstance(left, Decimal) else left
        right = Decimal(str(right)) if not isinstance(right, Decimal) else right
    
    if operator == ComparisonOperator.EQ:
        return left == right
    if operator == ComparisonOperator.NE:
        return left != right
    if operator == ComparisonOperator.GT:
        return left > right
    if operator == ComparisonOperator.LT:
        return left < right
    if operator == ComparisonOperator.GE:
        return left >= right
    if operator == ComparisonOperator.LE:
        return left <= right
    
    raise ExpressionEvaluationError(f"Unsupported operator: {operator}")


def evaluate_condition(
    condition: Dict[str, Any],
    variables: Dict[str, Any],
    signature_terms: Dict[str, Dict[str, Any]],
    lookup_data: Optional[Dict[str, Dict[str, str]]] = None
) -> bool:
    term_ref = condition.get("term", {})
    term_name = term_ref.get("name")
    expression = condition.get("expression", "")
    cond_type = condition.get("type", "decisionTable")
    lookup_id = condition.get("lookup_id")
    
    if not term_name:
        raise TermNotFoundError("Condition term has no name")
    
    if term_name not in variables:
        raise TermNotFoundError(f"Term '{term_name}' not found in variables")
    
    if term_name not in signature_terms:
        raise TermNotFoundError(f"Term '{term_name}' not found in signature")
    
    term_info = signature_terms[term_name]
    data_type = DataType(term_info.get("dataType", "string"))
    current_value = variables[term_name]
    
    if cond_type == "expression":
        if not expression:
            raise ExpressionEvaluationError("Expression is required for condition type 'expression'")
        operator, value_str = parse_comparison_expression(expression)
        compare_value = parse_value(value_str, data_type)
        return compare_values(current_value, compare_value, operator, data_type)
    
    elif cond_type == "decisionTable":
        return evaluate_decision_table(expression, current_value, data_type)
    
    elif cond_type == "lookup":
        if not lookup_id:
            raise ExpressionEvaluationError("lookup_id is required for condition type 'lookup'")
        if lookup_data and lookup_id in lookup_data:
            lookup_table = lookup_data[lookup_id]
            current_value_str = str(current_value) if current_value is not None else ""
            return current_value_str in lookup_table
        return False
    
    elif cond_type == "complex":
        if not expression:
            raise ExpressionEvaluationError("Expression is required for condition type 'complex'")
        return bool(expression)
    
    raise ExpressionEvaluationError(f"Unsupported condition type: {cond_type}")


def evaluate_decision_table(expression: str, current_value: Any, data_type: DataType) -> bool:
    return bool(expression)


def evaluate_conditional(
    conditional: str,
    condition_results: List[bool]
) -> bool:
    if not condition_results:
        return True
    
    conditional_lower = conditional.lower()
    
    if conditional_lower in ("all", "and", "if"):
        return all(condition_results)
    
    if conditional_lower in ("any", "or"):
        return any(condition_results)
    
    if conditional_lower == "decisiontable":
        return all(condition_results)
    
    return all(condition_results)


def parse_assignment_expression(expression: str, data_type: DataType) -> Any:
    return parse_value(expression, data_type)


def execute_action(
    action: Dict[str, Any],
    variables: Dict[str, Any],
    signature_terms: Dict[str, Dict[str, Any]],
    lookup_data: Optional[Dict[str, Dict[str, str]]] = None
) -> Tuple[str, Any]:
    term_ref = action.get("term", {})
    term_name = term_ref.get("name")
    expression = action.get("expression", "")
    action_type = action.get("type", "assignment")
    lookup_id = action.get("lookup_id")
    
    if not term_name:
        raise TermNotFoundError("Action term has no name")
    
    if term_name not in signature_terms:
        raise TermNotFoundError(f"Term '{term_name}' not found in signature")
    
    term_info = signature_terms[term_name]
    data_type = DataType(term_info.get("dataType", "string"))
    
    if action_type == "assignment":
        if not expression:
            raise ExpressionEvaluationError("Expression is required for action type 'assignment'")
        new_value = parse_assignment_expression(expression, data_type)
        variables[term_name] = new_value
        return term_name, new_value
    
    elif action_type == "lookupValue":
        if not lookup_id:
            raise ExpressionEvaluationError("lookup_id is required for action type 'lookupValue'")
        
        input_term_name = None
        for name, var_value in variables.items():
            if name != term_name and name in signature_terms:
                term_dir = signature_terms[name].get("direction", "input")
                if term_dir == "input" or term_dir == "input/output":
                    input_term_name = name
                    break
        
        if input_term_name is None:
            raise ExpressionEvaluationError("No input term found for lookupValue action")
        
        lookup_key = str(variables.get(input_term_name, ""))
        
        if lookup_data and lookup_id in lookup_data:
            lookup_table = lookup_data[lookup_id]
            if lookup_key in lookup_table:
                new_value = parse_value(lookup_table[lookup_key], data_type)
                variables[term_name] = new_value
                return term_name, new_value
        
        variables[term_name] = None
        return term_name, None
    
    elif action_type == "complex":
        if not expression:
            raise ExpressionEvaluationError("Expression is required for action type 'complex'")
        new_value = parse_assignment_expression(expression, data_type)
        variables[term_name] = new_value
        return term_name, new_value
    
    elif action_type == "return":
        return_value = parse_assignment_expression(expression, data_type) if expression else variables.get(term_name)
        variables[term_name] = return_value
        return term_name, return_value
    
    raise ExpressionEvaluationError(f"Unsupported action type: {action_type}")


def build_signature_maps(
    signature: Optional[List[Any]]
) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    terms_by_name: Dict[str, Dict[str, Any]] = {}
    input_terms: Dict[str, Dict[str, Any]] = {}
    output_terms: Dict[str, Dict[str, Any]] = {}
    
    if signature:
        for term in signature:
            if isinstance(term, dict):
                name = term.get("name")
                if name:
                    terms_by_name[name] = term
                    direction = term.get("direction")
                    if direction == "input":
                        input_terms[name] = term
                    elif direction == "output":
                        output_terms[name] = term
                    else:
                        input_terms[name] = term
                        output_terms[name] = term
    
    return terms_by_name, input_terms, output_terms


def validate_and_convert_input(
    input_data: Dict[str, Any],
    input_terms: Dict[str, Dict[str, Any]]
) -> Dict[str, Any]:
    converted: Dict[str, Any] = {}
    
    for name, term_info in input_terms.items():
        data_type = DataType(term_info.get("dataType", "string"))
        default_value = term_info.get("defaultValue")
        
        if name in input_data:
            value = input_data[name]
            converted[name] = convert_input_value(value, data_type)
        elif default_value is not None:
            converted[name] = convert_input_value(default_value, data_type)
        else:
            raise InvalidInputError(f"Missing required input: '{name}'")
    
    return converted


def initialize_output_variables(
    output_terms: Dict[str, Dict[str, Any]],
    variables: Dict[str, Any]
) -> Dict[str, Any]:
    for name, term_info in output_terms.items():
        if name not in variables:
            default_value = term_info.get("defaultValue")
            data_type = DataType(term_info.get("dataType", "string"))
            if default_value is not None:
                variables[name] = convert_input_value(default_value, data_type)
            else:
                variables[name] = None
    return variables


class ConditionEvaluationResult:
    def __init__(
        self,
        condition_id: str,
        term_name: str,
        expression: str,
        result: bool,
        error: Optional[str] = None
    ):
        self.condition_id = condition_id
        self.term_name = term_name
        self.expression = expression
        self.result = result
        self.error = error
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.condition_id,
            "termName": self.term_name,
            "expression": self.expression,
            "result": self.result,
            "error": self.error,
        }


class ActionExecutionResult:
    def __init__(
        self,
        action_id: str,
        term_name: str,
        expression: str,
        value: Any,
        error: Optional[str] = None
    ):
        self.action_id = action_id
        self.term_name = term_name
        self.expression = expression
        self.value = value
        self.error = error
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.action_id,
            "termName": self.term_name,
            "expression": self.expression,
            "value": self._serialize_value(self.value),
            "error": self.error,
        }
    
    def _serialize_value(self, value: Any) -> Any:
        if isinstance(value, Decimal):
            return str(value)
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        return value


class RuleExecutionResult:
    def __init__(
        self,
        rule_id: str,
        rule_name: str,
        order_index: int,
        conditional: str,
        conditions_passed: bool,
        conditions: List[ConditionEvaluationResult],
        actions: List[ActionExecutionResult],
        error: Optional[str] = None
    ):
        self.rule_id = rule_id
        self.rule_name = rule_name
        self.order_index = order_index
        self.conditional = conditional
        self.conditions_passed = conditions_passed
        self.conditions = conditions
        self.actions = actions
        self.error = error
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.rule_id,
            "name": self.rule_name,
            "orderIndex": self.order_index,
            "conditional": self.conditional,
            "conditionsPassed": self.conditions_passed,
            "conditions": [c.to_dict() for c in self.conditions],
            "actions": [a.to_dict() for a in self.actions],
            "error": self.error,
        }


class ExecutionResult:
    def __init__(
        self,
        success: bool,
        output: Dict[str, Any],
        rules: List[RuleExecutionResult],
        error: Optional[str] = None
    ):
        self.success = success
        self.output = output
        self.rules = rules
        self.error = error
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "output": self._serialize_output(self.output),
            "rules": [r.to_dict() for r in self.rules],
            "error": self.error,
        }
    
    def _serialize_output(self, output: Dict[str, Any]) -> Dict[str, Any]:
        result = {}
        for key, value in output.items():
            if isinstance(value, Decimal):
                result[key] = str(value)
            elif isinstance(value, (date, datetime)):
                result[key] = value.isoformat()
            else:
                result[key] = value
        return result


def execute_ruleset_with_data(
    signature: List[Any],
    rules: List[Any],
    input_data: Dict[str, Any],
    lookup_data: Optional[Dict[str, Dict[str, str]]] = None
) -> ExecutionResult:
    rule_results: List[RuleExecutionResult] = []
    
    try:
        terms_by_name, input_terms, output_terms = build_signature_maps(signature)
        
        variables = validate_and_convert_input(input_data, input_terms)
        
        variables = initialize_output_variables(output_terms, variables)
        
        sorted_rules = sorted(rules, key=lambda r: r.order_index if hasattr(r, 'order_index') else r.get('order_index', 0))
        
        for rule in sorted_rules:
            rule_result = execute_single_rule(rule, variables, terms_by_name, lookup_data)
            rule_results.append(rule_result)
        
        output = {}
        for name in output_terms.keys():
            output[name] = variables.get(name)
        
        return ExecutionResult(
            success=True,
            output=output,
            rules=rule_results
        )
        
    except ExecutionError as e:
        return ExecutionResult(
            success=False,
            output={},
            rules=rule_results,
            error=str(e)
        )
    except Exception as e:
        return ExecutionResult(
            success=False,
            output={},
            rules=rule_results,
            error=f"Unexpected error: {str(e)}"
        )


def execute_single_rule(
    rule: Any,
    variables: Dict[str, Any],
    signature_terms: Dict[str, Dict[str, Any]],
    lookup_data: Optional[Dict[str, Dict[str, str]]] = None
) -> RuleExecutionResult:
    rule_id = str(rule.id) if hasattr(rule, 'id') else str(rule.get('id', ''))
    rule_name = rule.name if hasattr(rule, 'name') else rule.get('name', '')
    order_index = rule.order_index if hasattr(rule, 'order_index') else rule.get('order_index', 0)
    conditional = rule.conditional if hasattr(rule, 'conditional') else rule.get('conditional', 'all')
    conditions_data = rule.conditions if hasattr(rule, 'conditions') else rule.get('conditions', [])
    actions_data = rule.actions if hasattr(rule, 'actions') else rule.get('actions', [])
    
    condition_results: List[ConditionEvaluationResult] = []
    condition_booleans: List[bool] = []
    
    for cond in conditions_data or []:
        cond_id = cond.get('id', '')
        term_ref = cond.get('term', {})
        term_name = term_ref.get('name', '')
        expression = cond.get('expression', '')
        
        try:
            result = evaluate_condition(cond, variables, signature_terms, lookup_data)
            condition_booleans.append(result)
            condition_results.append(ConditionEvaluationResult(
                condition_id=cond_id,
                term_name=term_name,
                expression=expression,
                result=result
            ))
        except Exception as e:
            condition_booleans.append(False)
            condition_results.append(ConditionEvaluationResult(
                condition_id=cond_id,
                term_name=term_name,
                expression=expression,
                result=False,
                error=str(e)
            ))
    
    conditions_passed = evaluate_conditional(conditional, condition_booleans)
    
    action_results: List[ActionExecutionResult] = []
    
    if conditions_passed:
        for action in actions_data or []:
            action_id = action.get('id', '')
            term_ref = action.get('term', {})
            term_name = term_ref.get('name', '')
            expression = action.get('expression', '')
            
            try:
                assigned_name, assigned_value = execute_action(action, variables, signature_terms, lookup_data)
                action_results.append(ActionExecutionResult(
                    action_id=action_id,
                    term_name=assigned_name,
                    expression=expression,
                    value=assigned_value
                ))
            except Exception as e:
                action_results.append(ActionExecutionResult(
                    action_id=action_id,
                    term_name=term_name,
                    expression=expression,
                    value=None,
                    error=str(e)
                ))
    
    return RuleExecutionResult(
        rule_id=rule_id,
        rule_name=rule_name,
        order_index=order_index,
        conditional=conditional,
        conditions_passed=conditions_passed,
        conditions=condition_results,
        actions=action_results
    )


async def execute_ruleset(
    db,
    ruleset_id: uuid.UUID,
    input_data: Dict[str, Any],
    revision_id: Optional[uuid.UUID] = None
) -> ExecutionResult:
    from app.crud.rule import get_ruleset_with_rules
    from app.crud.ruleset import get_revision_by_id, get_ruleset_by_id
    from app.crud.lookup import get_lookup_with_entries
    
    if revision_id:
        revision = await get_revision_by_id(db, ruleset_id=ruleset_id, revision_id=revision_id)
        if not revision:
            return ExecutionResult(
                success=False,
                output={},
                rules=[],
                error=f"Revision {revision_id} not found"
            )
        signature = revision.signature or []
    else:
        ruleset = await get_ruleset_by_id(db, ruleset_id=ruleset_id)
        if not ruleset:
            return ExecutionResult(
                success=False,
                output={},
                rules=[],
                error=f"RuleSet {ruleset_id} not found"
            )
        signature = ruleset.signature or []
    
    ruleset_with_rules = await get_ruleset_with_rules(db, ruleset_id=ruleset_id)
    if not ruleset_with_rules:
        return ExecutionResult(
            success=False,
            output={},
            rules=[],
            error=f"RuleSet {ruleset_id} not found"
        )
    
    rules = ruleset_with_rules.rules or []
    
    lookup_ids = set()
    for rule in rules:
        conditions = rule.conditions if hasattr(rule, 'conditions') else rule.get('conditions', [])
        for cond in conditions or []:
            if isinstance(cond, dict):
                lookup_id = cond.get('lookup_id')
                if lookup_id:
                    lookup_ids.add(str(lookup_id))
        
        actions = rule.actions if hasattr(rule, 'actions') else rule.get('actions', [])
        for action in actions or []:
            if isinstance(action, dict):
                lookup_id = action.get('lookup_id')
                if lookup_id:
                    lookup_ids.add(str(lookup_id))
    
    lookup_data: Dict[str, Dict[str, str]] = {}
    for lookup_id_str in lookup_ids:
        try:
            lookup_id_uuid = uuid.UUID(lookup_id_str)
            lookup = await get_lookup_with_entries(db, lookup_id_uuid)
            if lookup and lookup.entries:
                lookup_data[lookup_id_str] = {
                    entry.key: entry.value for entry in lookup.entries
                }
        except (ValueError, TypeError):
            continue
    
    return execute_ruleset_with_data(signature, rules, input_data, lookup_data)
