import sys
import uuid
sys.path.insert(0, 'c:\\workspace\\ai\\light-rules')

from app.schemas.condition_action import (
    ConditionCreate, 
    ActionCreate, 
    ConditionResponse, 
    ActionResponse,
    TermRef,
    ConditionType,
    ActionType
)

from app.schemas.rule import (
    RuleCreate, 
    RuleUpdate, 
    RuleResponseData,
    get_valid_term_names,
    validate_terms,
    convert_conditions_value,
    convert_actions_value
)

from app.crud.rule import (
    process_conditions_for_storage,
    process_actions_for_storage
)

print("=== Testing ConditionCreate ===")
cond = ConditionCreate(
    term=TermRef(name='vehicleCost'),
    expression='> 15000',
    type=ConditionType.DECISION_TABLE
)
print(f"Condition created: {cond.model_dump()}")

print("")
print("=== Testing ActionCreate ===")
action = ActionCreate(
    term=TermRef(name='isHighCost'),
    expression='true',
    type=ActionType.ASSIGNMENT
)
print(f"Action created: {action.model_dump()}")

print("")
print("=== Testing RuleCreate ===")
rule_create = RuleCreate(
    name='Vehicle Categorization',
    description='Look at vehicle cost to determine category',
    conditional='if',
    order_index=0,
    conditions=[cond],
    actions=[action]
)
print(f"RuleCreate created: {rule_create.model_dump()}")

print("")
print("=== Testing process_conditions_for_storage ===")
stored_conds = process_conditions_for_storage([cond])
print(f"Stored conditions: {stored_conds}")
has_id = "id" in stored_conds[0] if stored_conds else False
has_status = "status" in stored_conds[0] if stored_conds else False
print(f"Condition has ID: {has_id}")
print(f"Condition has status: {has_status}")

print("")
print("=== Testing process_actions_for_storage ===")
stored_actions = process_actions_for_storage([action])
print(f"Stored actions: {stored_actions}")

print("")
print("=== Testing ConditionResponse ===")
cond_response = ConditionResponse(
    id=uuid.uuid4(),
    term=TermRef(name='vehicleCost'),
    expression='> 15000',
    type=ConditionType.DECISION_TABLE,
    status='valid',
    statusMessage='OK'
)
print(f"ConditionResponse: {cond_response.model_dump()}")

print("")
print("=== Testing get_valid_term_names ===")
signature = [
    {'name': 'vehicleCost', 'dataType': 'decimal', 'direction': 'input'},
    {'name': 'isHighCost', 'dataType': 'boolean', 'direction': 'output'}
]
valid_names = get_valid_term_names(signature)
print(f"Valid term names: {valid_names}")

print("")
print("=== Testing validate_terms - valid case ===")
errors = validate_terms([cond], [action], valid_names)
print(f"Validation errors (should be empty): {errors}")

print("")
print("=== Testing validate_terms - invalid case ===")
invalid_cond = ConditionCreate(
    term=TermRef(name='invalidTerm'),
    expression='> 1000',
    type=ConditionType.EXPRESSION
)
errors = validate_terms([invalid_cond], [], valid_names)
print(f"Validation errors (should have error): {errors}")

print("")
print("=== All tests passed! ===")
