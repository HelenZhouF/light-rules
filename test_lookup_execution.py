import sys
import uuid
sys.path.insert(0, 'c:\\workspace\\ai\\light-rules')

from app.services.execution import (
    execute_ruleset_with_data,
    evaluate_condition,
    execute_action,
    build_signature_maps,
)
from app.schemas.condition_action import (
    ConditionType,
    ActionType,
)


def test_lookup_condition():
    """Test condition type = lookup"""
    print("=== Testing condition type = lookup ===")
    
    signature = [
        {"id": str(uuid.uuid4()), "name": "statusCode", "dataType": "string", "direction": "input"},
        {"id": str(uuid.uuid4()), "name": "isValid", "dataType": "boolean", "direction": "output"},
    ]
    
    lookup_id = "3fa85f64-5717-4562-b3fc-2c963f66afa6"
    lookup_data = {
        lookup_id: {
            "A": "Active",
            "B": "Blocked",
            "C": "Cancelled",
        }
    }
    
    terms_by_name, input_terms, output_terms = build_signature_maps(signature)
    
    condition = {
        "term": {"name": "statusCode"},
        "type": ConditionType.LOOKUP,
        "lookup_id": lookup_id,
    }
    
    print("Test 1: statusCode = 'A' (should be in lookup keys)")
    variables = {"statusCode": "A", "isValid": None}
    result = evaluate_condition(condition, variables, terms_by_name, lookup_data)
    print(f"  Result: {result}")
    assert result == True, f"Expected True, got {result}"
    print("  [OK]\n")
    
    print("Test 2: statusCode = 'D' (should NOT be in lookup keys)")
    variables = {"statusCode": "D", "isValid": None}
    result = evaluate_condition(condition, variables, terms_by_name, lookup_data)
    print(f"  Result: {result}")
    assert result == False, f"Expected False, got {result}"
    print("  [OK]\n")
    
    print("Test 3: statusCode = None (should NOT be in lookup keys)")
    variables = {"statusCode": None, "isValid": None}
    result = evaluate_condition(condition, variables, terms_by_name, lookup_data)
    print(f"  Result: {result}")
    assert result == False, f"Expected False, got {result}"
    print("  [OK]\n")
    
    print("[OK] lookup condition tests passed!\n")


def test_lookup_value_action_with_term_name():
    """Test action type = lookupValue with expression as term name"""
    print("=== Testing action type = lookupValue with expression as term name ===")
    
    signature = [
        {"id": str(uuid.uuid4()), "name": "statusCode", "dataType": "string", "direction": "input"},
        {"id": str(uuid.uuid4()), "name": "statusName", "dataType": "string", "direction": "output"},
    ]
    
    lookup_id = "3fa85f64-5717-4562-b3fc-2c963f66afa6"
    lookup_data = {
        lookup_id: {
            "A": "Active",
            "B": "Blocked",
            "C": "Cancelled",
        }
    }
    
    terms_by_name, input_terms, output_terms = build_signature_maps(signature)
    
    action = {
        "term": {"name": "statusName"},
        "type": ActionType.LOOKUP_VALUE,
        "lookup_id": lookup_id,
        "expression": "statusCode",
    }
    
    print("Test 1: statusCode = 'A', expression = 'statusCode' (term name)")
    variables = {"statusCode": "A", "statusName": None}
    term_name, value = execute_action(action, variables, terms_by_name, lookup_data)
    print(f"  Term: {term_name}, Value: {value}")
    assert term_name == "statusName"
    assert value == "Active", f"Expected 'Active', got {value}"
    print("  [OK]\n")
    
    print("Test 2: statusCode = 'B', expression = 'statusCode' (term name)")
    variables = {"statusCode": "B", "statusName": None}
    term_name, value = execute_action(action, variables, terms_by_name, lookup_data)
    print(f"  Term: {term_name}, Value: {value}")
    assert term_name == "statusName"
    assert value == "Blocked", f"Expected 'Blocked', got {value}"
    print("  [OK]\n")
    
    print("Test 3: statusCode = 'D' (not in lookup), expression = 'statusCode'")
    variables = {"statusCode": "D", "statusName": None}
    term_name, value = execute_action(action, variables, terms_by_name, lookup_data)
    print(f"  Term: {term_name}, Value: {value}")
    assert term_name == "statusName"
    assert value is None, f"Expected None, got {value}"
    print("  [OK]\n")
    
    print("[OK] lookupValue action with term name tests passed!\n")


def test_lookup_value_action_with_direct_value():
    """Test action type = lookupValue with expression as direct value"""
    print("=== Testing action type = lookupValue with expression as direct value ===")
    
    signature = [
        {"id": str(uuid.uuid4()), "name": "statusCode", "dataType": "string", "direction": "input"},
        {"id": str(uuid.uuid4()), "name": "statusName", "dataType": "string", "direction": "output"},
    ]
    
    lookup_id = "3fa85f64-5717-4562-b3fc-2c963f66afa6"
    lookup_data = {
        lookup_id: {
            "A": "Active",
            "B": "Blocked",
            "C": "Cancelled",
            "DEFAULT": "Unknown",
        }
    }
    
    terms_by_name, input_terms, output_terms = build_signature_maps(signature)
    
    action = {
        "term": {"name": "statusName"},
        "type": ActionType.LOOKUP_VALUE,
        "lookup_id": lookup_id,
        "expression": "'DEFAULT'",
    }
    
    print("Test 1: expression = \"'DEFAULT'\" (with quotes, direct value)")
    variables = {"statusCode": "A", "statusName": None}
    term_name, value = execute_action(action, variables, terms_by_name, lookup_data)
    print(f"  Term: {term_name}, Value: {value}")
    assert term_name == "statusName"
    assert value == "Unknown", f"Expected 'Unknown', got {value}"
    print("  [OK]\n")
    
    action2 = {
        "term": {"name": "statusName"},
        "type": ActionType.LOOKUP_VALUE,
        "lookup_id": lookup_id,
        "expression": "DEFAULT",
    }
    
    print("Test 2: expression = 'DEFAULT' (without quotes, 'DEFAULT' is not a term name)")
    variables = {"statusCode": "A", "statusName": None}
    term_name, value = execute_action(action2, variables, terms_by_name, lookup_data)
    print(f"  Term: {term_name}, Value: {value}")
    assert term_name == "statusName"
    assert value == "Unknown", f"Expected 'Unknown', got {value}"
    print("  [OK]\n")
    
    action3 = {
        "term": {"name": "statusName"},
        "type": ActionType.LOOKUP_VALUE,
        "lookup_id": lookup_id,
        "expression": '"B"',
    }
    
    print("Test 3: expression = '\"B\"' (with double quotes)")
    variables = {"statusCode": "A", "statusName": None}
    term_name, value = execute_action(action3, variables, terms_by_name, lookup_data)
    print(f"  Term: {term_name}, Value: {value}")
    assert term_name == "statusName"
    assert value == "Blocked", f"Expected 'Blocked', got {value}"
    print("  [OK]\n")
    
    print("[OK] lookupValue action with direct value tests passed!\n")


def test_lookup_value_action_backward_compatibility():
    """Test action type = lookupValue backward compatibility (no expression)"""
    print("=== Testing action type = lookupValue backward compatibility (no expression) ===")
    
    signature = [
        {"id": str(uuid.uuid4()), "name": "statusCode", "dataType": "string", "direction": "input"},
        {"id": str(uuid.uuid4()), "name": "statusName", "dataType": "string", "direction": "output"},
    ]
    
    lookup_id = "3fa85f64-5717-4562-b3fc-2c963f66afa6"
    lookup_data = {
        lookup_id: {
            "A": "Active",
            "B": "Blocked",
            "C": "Cancelled",
        }
    }
    
    terms_by_name, input_terms, output_terms = build_signature_maps(signature)
    
    action = {
        "term": {"name": "statusName"},
        "type": ActionType.LOOKUP_VALUE,
        "lookup_id": lookup_id,
    }
    
    print("Test 1: No expression, should use first input term (statusCode)")
    variables = {"statusCode": "A", "statusName": None}
    term_name, value = execute_action(action, variables, terms_by_name, lookup_data)
    print(f"  Term: {term_name}, Value: {value}")
    assert term_name == "statusName"
    assert value == "Active", f"Expected 'Active', got {value}"
    print("  [OK]\n")
    
    print("Test 2: No expression, statusCode = 'B'")
    variables = {"statusCode": "B", "statusName": None}
    term_name, value = execute_action(action, variables, terms_by_name, lookup_data)
    print(f"  Term: {term_name}, Value: {value}")
    assert term_name == "statusName"
    assert value == "Blocked", f"Expected 'Blocked', got {value}"
    print("  [OK]\n")
    
    print("[OK] lookupValue action backward compatibility tests passed!\n")


def test_full_ruleset_with_lookup():
    """Test full ruleset execution with lookup condition and lookupValue action"""
    print("=== Testing full ruleset with lookup ===")
    
    signature = [
        {"id": str(uuid.uuid4()), "name": "statusCode", "dataType": "string", "direction": "input"},
        {"id": str(uuid.uuid4()), "name": "isValidStatus", "dataType": "boolean", "direction": "output"},
        {"id": str(uuid.uuid4()), "name": "statusName", "dataType": "string", "direction": "output"},
    ]
    
    lookup_id = "3fa85f64-5717-4562-b3fc-2c963f66afa6"
    lookup_data = {
        lookup_id: {
            "A": "Active",
            "B": "Blocked",
            "C": "Cancelled",
        }
    }
    
    class MockRule:
        def __init__(self, name, order_index, conditional, conditions, actions):
            self.id = uuid.uuid4()
            self.name = name
            self.order_index = order_index
            self.conditional = conditional
            self.conditions = conditions
            self.actions = actions
    
    rules = [
        MockRule(
            name="Check Valid Status",
            order_index=0,
            conditional="all",
            conditions=[
                {
                    "id": str(uuid.uuid4()),
                    "term": {"name": "statusCode"},
                    "type": "lookup",
                    "lookup_id": lookup_id,
                }
            ],
            actions=[
                {
                    "id": str(uuid.uuid4()),
                    "term": {"name": "isValidStatus"},
                    "type": "assignment",
                    "expression": "true",
                },
                {
                    "id": str(uuid.uuid4()),
                    "term": {"name": "statusName"},
                    "type": "lookupValue",
                    "lookup_id": lookup_id,
                    "expression": "statusCode",
                }
            ],
        )
    ]
    
    print("Test 1: statusCode = 'A' (valid status)")
    result = execute_ruleset_with_data(signature, rules, {"statusCode": "A"}, lookup_data)
    print(f"  Success: {result.success}")
    print(f"  Output: {result.output}")
    print(f"  Rules passed: {[r.conditions_passed for r in result.rules]}")
    assert result.success
    assert result.output["isValidStatus"] == True, f"Expected isValidStatus=True, got {result.output['isValidStatus']}"
    assert result.output["statusName"] == "Active", f"Expected statusName='Active', got {result.output['statusName']}"
    print("  [OK]\n")
    
    print("Test 2: statusCode = 'D' (invalid status)")
    result = execute_ruleset_with_data(signature, rules, {"statusCode": "D"}, lookup_data)
    print(f"  Success: {result.success}")
    print(f"  Output: {result.output}")
    print(f"  Rules passed: {[r.conditions_passed for r in result.rules]}")
    assert result.success
    assert result.output["isValidStatus"] is None, f"Expected isValidStatus=None, got {result.output['isValidStatus']}"
    assert result.output["statusName"] is None, f"Expected statusName=None, got {result.output['statusName']}"
    print("  [OK]\n")
    
    print("[OK] full ruleset with lookup tests passed!\n")


def main():
    try:
        test_lookup_condition()
        test_lookup_value_action_with_term_name()
        test_lookup_value_action_with_direct_value()
        test_lookup_value_action_backward_compatibility()
        test_full_ruleset_with_lookup()
        
        print("=== All lookup tests passed! ===")
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
