import sys
import uuid
sys.path.insert(0, 'c:\\workspace\\ai\\light-rules')

from app.services.execution import (
    execute_ruleset_with_data,
    evaluate_condition,
    execute_action,
    build_signature_maps,
    _strip_quotes,
)
from app.schemas.condition_action import (
    ConditionType,
    ActionType,
)


def test_strip_quotes():
    """Test _strip_quotes function"""
    print("=== Testing _strip_quotes ===")
    
    test_cases = [
        ("'aaa'", "aaa"),
        ('"aaa"', "aaa"),
        ("'DEFAULT'", "DEFAULT"),
        ('"B"', "B"),
        ("  'aaa'  ", "aaa"),
        ("aaa", "aaa"),
        ("'aaa", "'aaa"),
        ("aaa'", "aaa'"),
    ]
    
    for input_val, expected in test_cases:
        result = _strip_quotes(input_val)
        print(f"  _strip_quotes('{input_val}') = '{result}' (expected: '{expected}')")
        assert result == expected, f"Expected '{expected}', got '{result}'"
    
    print("[OK] _strip_quotes tests passed!\n")


def test_lookup_value_action_with_uuid_lookup_id():
    """Test action type = lookupValue with UUID type lookup_id"""
    print("=== Testing action type = lookupValue with UUID type lookup_id ===")
    
    signature = [
        {"id": str(uuid.uuid4()), "name": "statusCode", "dataType": "string", "direction": "input"},
        {"id": str(uuid.uuid4()), "name": "statusName", "dataType": "string", "direction": "output"},
    ]
    
    lookup_id_uuid = uuid.UUID("3fa85f64-5717-4562-b3fc-2c963f66afa6")
    lookup_id_str = str(lookup_id_uuid)
    
    lookup_data = {
        lookup_id_str: {
            "A": "Active",
            "B": "Blocked",
            "C": "Cancelled",
        }
    }
    
    terms_by_name, input_terms, output_terms = build_signature_maps(signature)
    
    action = {
        "term": {"name": "statusName"},
        "type": ActionType.LOOKUP_VALUE,
        "lookup_id": lookup_id_uuid,
        "expression": "statusCode",
    }
    
    print("Test 1: lookup_id is UUID type, expression is term name 'statusCode'")
    print(f"  lookup_id type: {type(action['lookup_id'])}")
    print(f"  lookup_data keys: {list(lookup_data.keys())}")
    print(f"  lookup_data keys types: {[type(k) for k in lookup_data.keys()]}")
    
    variables = {"statusCode": "A", "statusName": None}
    term_name, value = execute_action(action, variables, terms_by_name, lookup_data)
    print(f"  Term: {term_name}, Value: {value}")
    assert term_name == "statusName"
    assert value == "Active", f"Expected 'Active', got {value}"
    print("  [OK]\n")
    
    action2 = {
        "term": {"name": "statusName"},
        "type": ActionType.LOOKUP_VALUE,
        "lookup_id": lookup_id_uuid,
        "expression": "'B'",
    }
    
    print("Test 2: lookup_id is UUID type, expression is direct value \"'B'\"")
    variables = {"statusCode": "A", "statusName": None}
    term_name, value = execute_action(action2, variables, terms_by_name, lookup_data)
    print(f"  Term: {term_name}, Value: {value}")
    assert term_name == "statusName"
    assert value == "Blocked", f"Expected 'Blocked', got {value}"
    print("  [OK]\n")
    
    action3 = {
        "term": {"name": "statusName"},
        "type": ActionType.LOOKUP_VALUE,
        "lookup_id": lookup_id_str,
        "expression": "'C'",
    }
    
    print("Test 3: lookup_id is string type, expression is direct value \"'C'\"")
    print(f"  lookup_id type: {type(action3['lookup_id'])}")
    variables = {"statusCode": "A", "statusName": None}
    term_name, value = execute_action(action3, variables, terms_by_name, lookup_data)
    print(f"  Term: {term_name}, Value: {value}")
    assert term_name == "statusName"
    assert value == "Cancelled", f"Expected 'Cancelled', got {value}"
    print("  [OK]\n")
    
    print("[OK] lookupValue action with UUID type lookup_id tests passed!\n")


def test_lookup_value_action_with_term_name_vs_direct_value():
    """Test the difference between term name and direct value"""
    print("=== Testing term name vs direct value ===")
    
    signature = [
        {"id": str(uuid.uuid4()), "name": "code", "dataType": "string", "direction": "input"},
        {"id": str(uuid.uuid4()), "name": "AAA", "dataType": "string", "direction": "input"},
        {"id": str(uuid.uuid4()), "name": "result", "dataType": "string", "direction": "output"},
    ]
    
    lookup_id = "3fa85f64-5717-4562-b3fc-2c963f66afa6"
    lookup_data = {
        lookup_id: {
            "A": "Active",
            "B": "Blocked",
            "AAA": "Triple A",
            "BBB": "Triple B",
        }
    }
    
    terms_by_name, input_terms, output_terms = build_signature_maps(signature)
    print(f"  signature_terms keys: {list(terms_by_name.keys())}")
    
    action1 = {
        "term": {"name": "result"},
        "type": ActionType.LOOKUP_VALUE,
        "lookup_id": lookup_id,
        "expression": "AAA",
    }
    
    print("Test 1: expression = 'AAA' (AAA is a term name in signature)")
    variables = {"code": "X", "AAA": "A", "result": None}
    print(f"  Variables: {variables}")
    term_name, value = execute_action(action1, variables, terms_by_name, lookup_data)
    print(f"  Term: {term_name}, Value: {value}")
    assert term_name == "result"
    assert value == "Active", f"Expected 'Active' (using AAA term's value 'A' as key), got {value}"
    print("  [OK]\n")
    
    action2 = {
        "term": {"name": "result"},
        "type": ActionType.LOOKUP_VALUE,
        "lookup_id": lookup_id,
        "expression": "'AAA'",
    }
    
    print("Test 2: expression = \"'AAA'\" (with quotes, should be direct value)")
    variables = {"code": "X", "AAA": "A", "result": None}
    print(f"  Variables: {variables}")
    term_name, value = execute_action(action2, variables, terms_by_name, lookup_data)
    print(f"  Term: {term_name}, Value: {value}")
    assert term_name == "result"
    assert value == "Triple A", f"Expected 'Triple A' (using 'AAA' as direct key), got {value}"
    print("  [OK]\n")
    
    action3 = {
        "term": {"name": "result"},
        "type": ActionType.LOOKUP_VALUE,
        "lookup_id": lookup_id,
        "expression": "BBB",
    }
    
    print("Test 3: expression = 'BBB' (BBB is NOT a term name, should be direct value)")
    variables = {"code": "X", "AAA": "A", "result": None}
    print(f"  Variables: {variables}")
    term_name, value = execute_action(action3, variables, terms_by_name, lookup_data)
    print(f"  Term: {term_name}, Value: {value}")
    assert term_name == "result"
    assert value == "Triple B", f"Expected 'Triple B' (using 'BBB' as direct key), got {value}"
    print("  [OK]\n")
    
    print("[OK] term name vs direct value tests passed!\n")


def main():
    try:
        test_strip_quotes()
        test_lookup_value_action_with_uuid_lookup_id()
        test_lookup_value_action_with_term_name_vs_direct_value()
        
        print("=== All detailed lookup tests passed! ===")
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
