import sys
import uuid
sys.path.insert(0, 'c:\\workspace\\ai\\light-rules')

from decimal import Decimal
from app.services.execution import (
    execute_ruleset_with_data,
    parse_comparison_expression,
    parse_value,
    compare_values,
    evaluate_condition,
    execute_action,
    build_signature_maps,
    validate_and_convert_input,
    ComparisonOperator,
    DataType,
)
from app.schemas.signature import SignatureTerm, Direction
from app.schemas.condition_action import (
    ConditionCreate,
    ActionCreate,
    TermRef,
    ConditionType,
    ActionType,
)
from app.schemas.rule import RuleCreate
from app.crud.rule import process_conditions_for_storage, process_actions_for_storage


def test_parse_comparison_expression():
    print("=== Testing parse_comparison_expression ===")
    
    test_cases = [
        ("> 10", ComparisonOperator.GT, "10"),
        (">= 100", ComparisonOperator.GE, "100"),
        ("< 5", ComparisonOperator.LT, "5"),
        ("<= 50", ComparisonOperator.LE, "50"),
        ("== 'test'", ComparisonOperator.EQ, "'test'"),
        ("!= 'other'", ComparisonOperator.NE, "'other'"),
        ("> 15000", ComparisonOperator.GT, "15000"),
    ]
    
    for expr, expected_op, expected_val in test_cases:
        op, val = parse_comparison_expression(expr)
        assert op == expected_op, f"Expected operator {expected_op}, got {op}"
        assert val == expected_val, f"Expected value '{expected_val}', got '{val}'"
        print(f"  [OK] {expr} -> op={op}, val='{val}'")
    
    print("[OK] parse_comparison_expression tests passed!\n")


def test_parse_value():
    print("=== Testing parse_value ===")
    
    test_cases = [
        ("'hello'", DataType.STRING, "hello"),
        ('"world"', DataType.STRING, "world"),
        ("plain", DataType.STRING, "plain"),
        ("123", DataType.DECIMAL, Decimal("123")),
        ("45.67", DataType.DECIMAL, Decimal("45.67")),
        ("true", DataType.BOOLEAN, True),
        ("false", DataType.BOOLEAN, False),
        ("'2024-01-15'", DataType.DATE, None),
    ]
    
    for val_str, data_type, expected in test_cases:
        result = parse_value(val_str, data_type)
        if expected is not None:
            assert result == expected, f"Expected {expected}, got {result}"
        print(f"  [OK] parse_value('{val_str}', {data_type}) = {result}")
    
    print("[OK] parse_value tests passed!\n")


def test_compare_values():
    print("=== Testing compare_values ===")
    
    test_cases = [
        (10, 5, ComparisonOperator.GT, DataType.DECIMAL, True),
        (5, 10, ComparisonOperator.GT, DataType.DECIMAL, False),
        (10, 10, ComparisonOperator.GE, DataType.DECIMAL, True),
        (5, 10, ComparisonOperator.LT, DataType.DECIMAL, True),
        ("abc", "abc", ComparisonOperator.EQ, DataType.STRING, True),
        ("abc", "def", ComparisonOperator.NE, DataType.STRING, True),
    ]
    
    for left, right, op, data_type, expected in test_cases:
        result = compare_values(left, right, op, data_type)
        assert result == expected, f"Expected {expected} for {left} {op} {right}, got {result}"
        print(f"  [OK] {left} {op} {right} = {result}")
    
    print("[OK] compare_values tests passed!\n")


def test_execute_ruleset_with_data():
    print("=== Testing execute_ruleset_with_data ===")
    
    signature = [
        {"id": str(uuid.uuid4()), "name": "vehicleCost", "dataType": "decimal", "direction": "input"},
        {"id": str(uuid.uuid4()), "name": "isHighCost", "dataType": "boolean", "direction": "output"},
        {"id": str(uuid.uuid4()), "name": "category", "dataType": "string", "direction": "output"},
    ]
    
    conditions = [
        {
            "id": str(uuid.uuid4()),
            "term": {"name": "vehicleCost", "termId": signature[0]["id"]},
            "expression": "> 15000",
            "type": "expression",
            "status": None,
            "statusMessage": None,
        }
    ]
    
    actions_high = [
        {
            "id": str(uuid.uuid4()),
            "term": {"name": "isHighCost", "termId": signature[1]["id"]},
            "expression": "true",
            "type": "assignment",
            "status": None,
            "statusMessage": None,
        },
        {
            "id": str(uuid.uuid4()),
            "term": {"name": "category", "termId": signature[2]["id"]},
            "expression": "'PREMIUM'",
            "type": "assignment",
            "status": None,
            "statusMessage": None,
        }
    ]
    
    actions_low = [
        {
            "id": str(uuid.uuid4()),
            "term": {"name": "isHighCost", "termId": signature[1]["id"]},
            "expression": "false",
            "type": "assignment",
            "status": None,
            "statusMessage": None,
        },
        {
            "id": str(uuid.uuid4()),
            "term": {"name": "category", "termId": signature[2]["id"]},
            "expression": "'STANDARD'",
            "type": "assignment",
            "status": None,
            "statusMessage": None,
        }
    ]
    
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
            name="High Cost Check",
            order_index=0,
            conditional="all",
            conditions=conditions,
            actions=actions_high,
        ),
        MockRule(
            name="Low Cost Check",
            order_index=1,
            conditional="all",
            conditions=[
                {
                    "id": str(uuid.uuid4()),
                    "term": {"name": "vehicleCost", "termId": signature[0]["id"]},
                    "expression": "<= 15000",
                    "type": "expression",
                    "status": None,
                    "statusMessage": None,
                }
            ],
            actions=actions_low,
        )
    ]
    
    print("Test 1: vehicleCost = 20000 (should be PREMIUM, isHighCost = true)")
    result = execute_ruleset_with_data(signature, rules, {"vehicleCost": 20000})
    print(f"  Success: {result.success}")
    print(f"  Output: {result.output}")
    print(f"  Error: {result.error}")
    assert result.success, f"Expected success, got error: {result.error}"
    assert result.output["isHighCost"] == True, f"Expected isHighCost=true, got {result.output['isHighCost']}"
    assert result.output["category"] == "PREMIUM", f"Expected category=PREMIUM, got {result.output['category']}"
    print("  [OK]\n")
    
    print("Test 2: vehicleCost = 10000 (should be STANDARD, isHighCost = false)")
    result = execute_ruleset_with_data(signature, rules, {"vehicleCost": 10000})
    print(f"  Success: {result.success}")
    print(f"  Output: {result.output}")
    print(f"  Error: {result.error}")
    assert result.success, f"Expected success, got error: {result.error}"
    assert result.output["isHighCost"] == False, f"Expected isHighCost=false, got {result.output['isHighCost']}"
    assert result.output["category"] == "STANDARD", f"Expected category=STANDARD, got {result.output['category']}"
    print("  [OK]\n")
    
    print("Test 3: Missing input (should fail)")
    result = execute_ruleset_with_data(signature, rules, {})
    print(f"  Success: {result.success}")
    print(f"  Error: {result.error}")
    assert not result.success, "Expected failure for missing input"
    print("  [OK]\n")
    
    print("[OK] execute_ruleset_with_data tests passed!\n")


def test_rule_execution_details():
    print("=== Testing rule execution details ===")
    
    signature = [
        {"id": str(uuid.uuid4()), "name": "age", "dataType": "decimal", "direction": "input"},
        {"id": str(uuid.uuid4()), "name": "isAdult", "dataType": "boolean", "direction": "output"},
    ]
    
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
            name="Adult Check",
            order_index=0,
            conditional="all",
            conditions=[
                {
                    "id": "cond-1",
                    "term": {"name": "age"},
                    "expression": ">= 18",
                    "type": "expression",
                    "status": None,
                    "statusMessage": None,
                }
            ],
            actions=[
                {
                    "id": "act-1",
                    "term": {"name": "isAdult"},
                    "expression": "true",
                    "type": "assignment",
                    "status": None,
                    "statusMessage": None,
                }
            ],
        )
    ]
    
    result = execute_ruleset_with_data(signature, rules, {"age": 25})
    assert result.success
    
    print(f"Number of rules executed: {len(result.rules)}")
    assert len(result.rules) == 1
    
    rule_result = result.rules[0]
    print(f"Rule name: {rule_result.rule_name}")
    print(f"Conditions passed: {rule_result.conditions_passed}")
    print(f"Number of conditions: {len(rule_result.conditions)}")
    print(f"Number of actions: {len(rule_result.actions)}")
    
    assert rule_result.conditions_passed == True
    assert len(rule_result.conditions) == 1
    assert len(rule_result.actions) == 1
    
    cond_result = rule_result.conditions[0]
    print(f"Condition - term: {cond_result.term_name}, expression: {cond_result.expression}, result: {cond_result.result}")
    assert cond_result.result == True
    
    action_result = rule_result.actions[0]
    print(f"Action - term: {action_result.term_name}, expression: {action_result.expression}, value: {action_result.value}")
    assert action_result.value == True
    
    print("\n[OK] rule execution details tests passed!\n")


def main():
    try:
        test_parse_comparison_expression()
        test_parse_value()
        test_compare_values()
        test_execute_ruleset_with_data()
        test_rule_execution_details()
        
        print("=== All tests passed! ===")
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
