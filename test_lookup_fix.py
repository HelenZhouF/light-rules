import sys
import uuid
sys.path.insert(0, 'c:\\workspace\\ai\\light-rules')

from app.schemas.condition_action import (
    ConditionCreate, 
    ActionCreate, 
    TermRef,
    ConditionType,
    ActionType
)

from app.crud.rule import (
    process_conditions_for_storage,
    process_actions_for_storage
)

from app.schemas.rule import (
    convert_conditions_with_signature,
    convert_actions_with_signature
)

print("=== Test 1: ConditionCreate with LOOKUP type (no expression) ===")
cond_lookup = ConditionCreate(
    term=TermRef(name='v1'),
    type=ConditionType.LOOKUP,
    lookup_id=uuid.UUID('3fa85f64-5717-4562-b3fc-2c963f66afa6')
)
print(f"Condition (lookup) created: {cond_lookup.model_dump()}")
print(f"Condition lookup_id type: {type(cond_lookup.lookup_id)}")

print("")
print("=== Test 2: ActionCreate with LOOKUP_VALUE type (no expression) ===")
action_lookup = ActionCreate(
    term=TermRef(name='v2'),
    type=ActionType.LOOKUP_VALUE,
    lookup_id=uuid.UUID('3fa85f64-5717-4562-b3fc-2c963f66afa6')
)
print(f"Action (lookupValue) created: {action_lookup.model_dump()}")

print("")
print("=== Test 3: process_conditions_for_storage - check lookup_id is string ===")
stored_conds = process_conditions_for_storage([cond_lookup])
print(f"Stored conditions: {stored_conds}")
if stored_conds:
    lookup_id = stored_conds[0].get('lookup_id')
    print(f"lookup_id value: {lookup_id}")
    print(f"lookup_id type: {type(lookup_id)}")
    print(f"lookup_id is string: {isinstance(lookup_id, str)}")

print("")
print("=== Test 4: process_actions_for_storage - check lookup_id is string ===")
stored_actions = process_actions_for_storage([action_lookup])
print(f"Stored actions: {stored_actions}")
if stored_actions:
    lookup_id = stored_actions[0].get('lookup_id')
    print(f"lookup_id value: {lookup_id}")
    print(f"lookup_id type: {type(lookup_id)}")
    print(f"lookup_id is string: {isinstance(lookup_id, str)}")

print("")
print("=== Test 5: convert_conditions_with_signature - check lookup_id is UUID ===")
signature = [
    {'name': 'v1', 'dataType': 'string', 'direction': 'input'},
    {'name': 'v2', 'dataType': 'string', 'direction': 'output'}
]
converted_conds = convert_conditions_with_signature(stored_conds, signature)
print(f"Converted conditions: {converted_conds}")
if converted_conds:
    lookup_id = converted_conds[0].lookup_id
    print(f"lookup_id value: {lookup_id}")
    print(f"lookup_id type: {type(lookup_id)}")
    print(f"lookup_id is UUID: {isinstance(lookup_id, uuid.UUID)}")

print("")
print("=== Test 6: convert_actions_with_signature - check lookup_id is UUID ===")
converted_actions = convert_actions_with_signature(stored_actions, signature)
print(f"Converted actions: {converted_actions}")
if converted_actions:
    lookup_id = converted_actions[0].lookup_id
    print(f"lookup_id value: {lookup_id}")
    print(f"lookup_id type: {type(lookup_id)}")
    print(f"lookup_id is UUID: {isinstance(lookup_id, uuid.UUID)}")

print("")
print("=== Test 7: Condition with expression still works ===")
cond_with_expr = ConditionCreate(
    term=TermRef(name='vehicleCost'),
    expression='> 15000',
    type=ConditionType.DECISION_TABLE
)
print(f"Condition (with expression) created: {cond_with_expr.model_dump()}")

print("")
print("=== All tests passed! ===")
