from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from app.schemas.signature import DataType, Direction
from app.schemas.condition_action import ConditionType, ActionType


COMPARISON_OPERATORS = [
    (">=", ">="),
    ("<=", "<="),
    ("==", "=="),
    ("!=", "!="),
    (">", ">"),
    ("<", "<"),
    ("=", "=="),
]


def _strip_quotes(value_str: str) -> str:
    value_str = value_str.strip()
    if (value_str.startswith("'") and value_str.endswith("'")) or \
       (value_str.startswith('"') and value_str.endswith('"')):
        return value_str[1:-1].strip()
    return value_str


def parse_comparison_expression(expression: str) -> Tuple[str, str]:
    expression = expression.strip()
    
    for op_str, normalized_op in COMPARISON_OPERATORS:
        if expression.startswith(op_str):
            value = expression[len(op_str):].strip()
            return normalized_op, value
    
    return "==", expression


def parse_value_to_python(value_str: str, data_type: str) -> str:
    value_str = value_str.strip()
    
    if data_type == DataType.STRING.value:
        quoted = _strip_quotes(value_str)
        return repr(quoted)
    
    if data_type == DataType.BOOLEAN.value:
        lower_val = _strip_quotes(value_str).lower()
        if lower_val in ("true", "1", "yes"):
            return "True"
        if lower_val in ("false", "0", "no"):
            return "False"
        return "bool(" + repr(value_str) + ")"
    
    if data_type == DataType.DECIMAL.value:
        return "Decimal(" + repr(_strip_quotes(value_str)) + ")"
    
    if data_type == DataType.DATE.value:
        return "date.fromisoformat(" + repr(_strip_quotes(value_str)) + ")"
    
    if data_type == DataType.DATETIME.value:
        return "datetime.fromisoformat(" + repr(_strip_quotes(value_str)) + ")"
    
    return repr(value_str)


def generate_condition_code(
    condition: Dict[str, Any],
    signature_terms: Dict[str, Dict[str, Any]],
    indent: str = "    "
) -> List[str]:
    lines: List[str] = []
    
    term_ref = condition.get("term", {})
    term_name = term_ref.get("name")
    expression = condition.get("expression", "")
    cond_type = condition.get("type", ConditionType.DECISION_TABLE.value)
    
    if not term_name:
        return lines
    
    if term_name not in signature_terms:
        return lines
    
    term_info = signature_terms[term_name]
    data_type = term_info.get("dataType", DataType.STRING.value)
    var_name = f"variables[{repr(term_name)}]"
    
    if cond_type == ConditionType.EXPRESSION.value:
        if not expression:
            return lines
        
        operator, value_str = parse_comparison_expression(expression)
        compare_value = parse_value_to_python(value_str, data_type)
        
        if data_type == DataType.DECIMAL.value:
            lines.append(f"{indent}left = Decimal(str({var_name})) if not isinstance({var_name}, Decimal) else {var_name}")
            lines.append(f"{indent}right = {compare_value}")
            lines.append(f"{indent}cond_result = left {operator} right")
        elif data_type in [DataType.DATE.value, DataType.DATETIME.value]:
            lines.append(f"{indent}left = {var_name}")
            lines.append(f"{indent}right = {compare_value}")
            lines.append(f"{indent}cond_result = left {operator} right")
        else:
            lines.append(f"{indent}cond_result = {var_name} {operator} {compare_value}")
    
    elif cond_type == ConditionType.DECISION_TABLE.value:
        lines.append(f"{indent}cond_result = bool({repr(expression)})")
    
    elif cond_type == ConditionType.LOOKUP.value:
        lookup_id = condition.get("lookup_id")
        lines.append(f"{indent}lookup_id = {repr(str(lookup_id)) if lookup_id else None}")
        lines.append(f"{indent}cond_result = False")
        lines.append(f"{indent}if lookup_id and lookup_id in lookup_data:")
        lines.append(f"{indent}    lookup_table = lookup_data[lookup_id]")
        lines.append(f"{indent}    current_value_str = str({var_name}) if {var_name} is not None else ''")
        lines.append(f"{indent}    cond_result = current_value_str in lookup_table")
    
    elif cond_type == ConditionType.COMPLEX.value:
        if not expression:
            return lines
        lines.append(f"{indent}cond_result = bool({repr(expression)})")
    
    return lines


def generate_action_code(
    action: Dict[str, Any],
    signature_terms: Dict[str, Dict[str, Any]],
    indent: str = "    "
) -> List[str]:
    lines: List[str] = []
    
    term_ref = action.get("term", {})
    term_name = term_ref.get("name")
    expression = action.get("expression", "")
    action_type = action.get("type", ActionType.ASSIGNMENT.value)
    
    if not term_name:
        return lines
    
    if term_name not in signature_terms:
        return lines
    
    term_info = signature_terms[term_name]
    data_type = term_info.get("dataType", DataType.STRING.value)
    var_name = f"variables[{repr(term_name)}]"
    
    if action_type == ActionType.ASSIGNMENT.value:
        if not expression:
            return lines
        new_value = parse_value_to_python(expression, data_type)
        lines.append(f"{indent}{var_name} = {new_value}")
        lines.append(f"{indent}action_value = {new_value}")
    
    elif action_type == ActionType.LOOKUP_VALUE.value:
        lookup_id = action.get("lookup_id")
        lines.append(f"{indent}lookup_id = {repr(str(lookup_id)) if lookup_id else None}")
        lines.append(f"{indent}{var_name} = None")
        lines.append(f"{indent}action_value = None")
        lines.append(f"{indent}if lookup_id and lookup_id in lookup_data:")
        lines.append(f"{indent}    lookup_table = lookup_data[lookup_id]")
        if expression:
            expr_stripped = expression.strip()
            lines.append(f"{indent}    expr_stripped = {repr(expr_stripped)}")
            lines.append(f"{indent}    if expr_stripped in variables:")
            lines.append(f"{indent}        lookup_key = str(variables[expr_stripped])")
            lines.append(f"{indent}    else:")
            lines.append(f"{indent}        lookup_key = {repr(_strip_quotes(expr_stripped))}")
        else:
            lines.append(f"{indent}    lookup_key = ''")
        lines.append(f"{indent}    if lookup_key in lookup_table:")
        lines.append(f"{indent}        lookup_result = lookup_table[lookup_key]")
        lines.append(f"{indent}        # Note: lookup value parsing depends on data type")
        lines.append(f"{indent}        {var_name} = lookup_result")
        lines.append(f"{indent}        action_value = lookup_result")
    
    elif action_type == ActionType.COMPLEX.value:
        if not expression:
            return lines
        new_value = parse_value_to_python(expression, data_type)
        lines.append(f"{indent}{var_name} = {new_value}")
        lines.append(f"{indent}action_value = {new_value}")
    
    elif action_type == ActionType.RETURN.value:
        if expression:
            return_value = parse_value_to_python(expression, data_type)
            lines.append(f"{indent}{var_name} = {return_value}")
            lines.append(f"{indent}action_value = {return_value}")
        else:
            lines.append(f"{indent}action_value = {var_name}")
    
    return lines


def generate_ruleset_function(
    ruleset_name: str,
    signature: List[Dict[str, Any]],
    rules: List[Any],
) -> str:
    lines: List[str] = []
    
    lines.append("from datetime import date, datetime")
    lines.append("from decimal import Decimal")
    lines.append("from typing import Any, Dict, List, Optional")
    lines.append("")
    lines.append("")
    
    function_name = f"execute_{ruleset_name.lower().replace('-', '_')}"
    
    lines.append(f"def {function_name}(")
    lines.append("    input_data: Dict[str, Any],")
    lines.append("    lookup_data: Optional[Dict[str, Dict[str, str]]] = None")
    lines.append(") -> Dict[str, Any]:")
    lines.append("    \"\"\"")
    lines.append(f"    Executes the '{ruleset_name}' ruleset.")
    lines.append("    \"\"\"")
    lines.append("    variables: Dict[str, Any] = {}")
    lines.append("    output: Dict[str, Any] = {}")
    lines.append("")
    lines.append("    if lookup_data is None:")
    lines.append("        lookup_data = {}")
    lines.append("")
    
    terms_by_name: Dict[str, Dict[str, Any]] = {}
    input_terms: Dict[str, Dict[str, Any]] = {}
    output_terms: Dict[str, Dict[str, Any]] = {}
    
    for term in signature:
        if isinstance(term, dict):
            name = term.get("name")
            if name:
                terms_by_name[name] = term
                direction = term.get("direction")
                if direction == Direction.INPUT.value:
                    input_terms[name] = term
                elif direction == Direction.OUTPUT.value:
                    output_terms[name] = term
                elif direction == Direction.INOUT.value:
                    input_terms[name] = term
                    output_terms[name] = term
                else:
                    input_terms[name] = term
                    output_terms[name] = term
    
    lines.append("    # Validate and convert input")
    for name, term_info in input_terms.items():
        data_type = term_info.get("dataType", DataType.STRING.value)
        default_value = term_info.get("defaultValue")
        var_name = f"variables[{repr(name)}]"
        
        lines.append(f"    # Input term: {name} ({data_type})")
        
        if default_value is not None:
            default_py = parse_value_to_python(str(default_value), data_type)
            if data_type == DataType.STRING.value:
                lines.append(f"    if {repr(name)} in input_data and input_data[{repr(name)}] is not None:")
            else:
                lines.append(f"    if {repr(name)} in input_data and input_data[{repr(name)}] is not None:")
            
            if data_type == DataType.DECIMAL.value:
                lines.append(f"        val = input_data[{repr(name)}]")
                lines.append(f"        if isinstance(val, Decimal):")
                lines.append(f"            {var_name} = val")
                lines.append(f"        elif isinstance(val, (int, float)):")
                lines.append(f"            {var_name} = Decimal(str(val))")
                lines.append(f"        elif isinstance(val, str):")
                lines.append(f"            {var_name} = Decimal(val)")
                lines.append(f"        else:")
                lines.append(f"            {var_name} = {default_py}")
            elif data_type in [DataType.DATE.value, DataType.DATETIME.value]:
                lines.append(f"        val = input_data[{repr(name)}]")
                lines.append(f"        if isinstance(val, {'date' if data_type == DataType.DATE.value else 'datetime'}):")
                lines.append(f"            {var_name} = val")
                lines.append(f"        elif isinstance(val, str):")
                lines.append(f"            {var_name} = {'date' if data_type == DataType.DATE.value else 'datetime'}.fromisoformat(val)")
                lines.append(f"        else:")
                lines.append(f"            {var_name} = {default_py}")
            elif data_type == DataType.BOOLEAN.value:
                lines.append(f"        val = input_data[{repr(name)}]")
                lines.append(f"        if isinstance(val, bool):")
                lines.append(f"            {var_name} = val")
                lines.append(f"        elif isinstance(val, str):")
                lines.append(f"            lower_val = val.lower()")
                lines.append(f"            if lower_val in ('true', '1', 'yes'):")
                lines.append(f"                {var_name} = True")
                lines.append(f"            elif lower_val in ('false', '0', 'no'):")
                lines.append(f"                {var_name} = False")
                lines.append(f"            else:")
                lines.append(f"                {var_name} = bool(val)")
                lines.append(f"        else:")
                lines.append(f"            {var_name} = {default_py}")
            else:
                lines.append(f"        {var_name} = str(input_data[{repr(name)}])")
            lines.append(f"    else:")
            lines.append(f"        {var_name} = {default_py}")
        else:
            if data_type == DataType.DECIMAL.value:
                lines.append(f"    val = input_data[{repr(name)}]")
                lines.append(f"    if isinstance(val, Decimal):")
                lines.append(f"        {var_name} = val")
                lines.append(f"    elif isinstance(val, (int, float)):")
                lines.append(f"        {var_name} = Decimal(str(val))")
                lines.append(f"    elif isinstance(val, str):")
                lines.append(f"        {var_name} = Decimal(val)")
                lines.append(f"    else:")
                lines.append(f"        raise ValueError(f'Cannot convert {{type(val)}} to decimal for {name}')")
            elif data_type in [DataType.DATE.value, DataType.DATETIME.value]:
                lines.append(f"    val = input_data[{repr(name)}]")
                lines.append(f"    if isinstance(val, {'date' if data_type == DataType.DATE.value else 'datetime'}):")
                lines.append(f"        {var_name} = val")
                lines.append(f"    elif isinstance(val, str):")
                lines.append(f"        {var_name} = {'date' if data_type == DataType.DATE.value else 'datetime'}.fromisoformat(val)")
                lines.append(f"    else:")
                lines.append(f"        raise ValueError(f'Cannot convert {{type(val)}} to {data_type} for {name}')")
            elif data_type == DataType.BOOLEAN.value:
                lines.append(f"    val = input_data[{repr(name)}]")
                lines.append(f"    if isinstance(val, bool):")
                lines.append(f"        {var_name} = val")
                lines.append(f"    elif isinstance(val, str):")
                lines.append(f"        lower_val = val.lower()")
                lines.append(f"        if lower_val in ('true', '1', 'yes'):")
                lines.append(f"            {var_name} = True")
                lines.append(f"        elif lower_val in ('false', '0', 'no'):")
                lines.append(f"            {var_name} = False")
                lines.append(f"        else:")
                lines.append(f"            {var_name} = bool(val)")
                lines.append(f"    else:")
                lines.append(f"        {var_name} = bool(val)")
            else:
                lines.append(f"    {var_name} = str(input_data[{repr(name)}])")
    
    lines.append("")
    lines.append("    # Initialize output variables")
    for name, term_info in output_terms.items():
        var_name = f"variables[{repr(name)}]"
        default_value = term_info.get("defaultValue")
        data_type = term_info.get("dataType", DataType.STRING.value)
        
        if default_value is not None:
            default_py = parse_value_to_python(str(default_value), data_type)
            lines.append(f"    if {repr(name)} not in variables:")
            lines.append(f"        {var_name} = {default_py}")
        else:
            lines.append(f"    if {repr(name)} not in variables:")
            lines.append(f"        {var_name} = None")
    
    lines.append("")
    lines.append("    # Execute rules")
    lines.append("")
    
    sorted_rules = sorted(rules, key=lambda r: r.order_index if hasattr(r, 'order_index') else r.get('order_index', 0))
    
    for rule in sorted_rules:
        rule_id = str(rule.id) if hasattr(rule, 'id') else str(rule.get('id', ''))
        rule_name = rule.name if hasattr(rule, 'name') else rule.get('name', '')
        order_index = rule.order_index if hasattr(rule, 'order_index') else rule.get('order_index', 0)
        conditional = rule.conditional if hasattr(rule, 'conditional') else rule.get('conditional', 'all')
        conditions_data = rule.conditions if hasattr(rule, 'conditions') else rule.get('conditions', [])
        actions_data = rule.actions if hasattr(rule, 'actions') else rule.get('actions', [])
        
        lines.append(f"    # Rule: {rule_name} (order: {order_index})")
        lines.append(f"    rule_{order_index}_conditions_passed: List[bool] = []")
        lines.append("")
        
        for i, cond in enumerate(conditions_data or []):
            lines.append(f"    # Condition {i+1}")
            cond_lines = generate_condition_code(cond, terms_by_name, "    ")
            lines.extend(cond_lines)
            lines.append(f"    rule_{order_index}_conditions_passed.append(cond_result)")
            lines.append("")
        
        conditional_lower = conditional.lower()
        if conditional_lower in ("all", "and", "if"):
            lines.append(f"    rule_{order_index}_passed = all(rule_{order_index}_conditions_passed) if rule_{order_index}_conditions_passed else True")
        elif conditional_lower in ("any", "or"):
            lines.append(f"    rule_{order_index}_passed = any(rule_{order_index}_conditions_passed) if rule_{order_index}_conditions_passed else True")
        elif conditional_lower == "decisiontable":
            lines.append(f"    rule_{order_index}_passed = all(rule_{order_index}_conditions_passed) if rule_{order_index}_conditions_passed else True")
        else:
            lines.append(f"    rule_{order_index}_passed = all(rule_{order_index}_conditions_passed) if rule_{order_index}_conditions_passed else True")
        
        lines.append("")
        lines.append(f"    if rule_{order_index}_passed:")
        
        for i, action in enumerate(actions_data or []):
            lines.append(f"        # Action {i+1}")
            action_lines = generate_action_code(action, terms_by_name, "        ")
            lines.extend(action_lines)
        
        lines.append("")
    
    lines.append("    # Collect output")
    for name in output_terms.keys():
        var_name = f"variables[{repr(name)}]"
        lines.append(f"    output[{repr(name)}] = {var_name}")
    
    lines.append("")
    lines.append("    return output")
    lines.append("")
    
    return "\n".join(lines)


def generate_ruleset_metadata(
    ruleset_name: str,
    ruleset_description: Optional[str],
    major: int,
    minor: int,
    signature: List[Dict[str, Any]],
) -> Dict[str, Any]:
    input_terms: List[Dict[str, Any]] = []
    output_terms: List[Dict[str, Any]] = []
    
    for term in signature:
        if isinstance(term, dict):
            name = term.get("name")
            if not name:
                continue
            
            direction = term.get("direction")
            data_type = term.get("dataType", DataType.STRING.value)
            default_value = term.get("defaultValue")
            length = term.get("length")
            
            term_info: Dict[str, Any] = {
                "name": name,
                "dataType": data_type,
            }
            if default_value is not None:
                term_info["defaultValue"] = default_value
            if length is not None:
                term_info["length"] = length
            
            if direction == Direction.INPUT.value:
                input_terms.append(term_info)
            elif direction == Direction.OUTPUT.value:
                output_terms.append(term_info)
            elif direction == Direction.INOUT.value:
                input_terms.append(dict(term_info, direction="inout"))
                output_terms.append(dict(term_info, direction="inout"))
            else:
                input_terms.append(term_info)
                output_terms.append(term_info)
    
    return {
        "name": ruleset_name,
        "description": ruleset_description,
        "version": {
            "major": major,
            "minor": minor,
            "full": f"{major}.{minor}",
        },
        "input": input_terms,
        "output": output_terms,
    }
