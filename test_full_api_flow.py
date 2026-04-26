import sys
import uuid
import json
sys.path.insert(0, 'c:\\workspace\\ai\\light-rules')

from app.schemas.rule import RuleCreate, build_signature_term_maps
from app.schemas.condition_action import (
    ConditionCreate,
    ActionCreate,
    TermRef,
)
from app.schemas.ruleset import (
    RuleSetResponseData,
    RuleSetDetailResponse,
    validate_signature_field,
)
from app.schemas.signature import SignatureTerm, DataType, Direction
from app.crud.rule import (
    extract_term_names_from_conditions,
    extract_term_names_from_actions,
    update_signature_direction_for_inout_terms,
)
from app.crud.ruleset import _signature_terms_to_dicts


def test_full_flow_with_api_response():
    """Simulate full flow including API response serialization"""
    print("=== Test full flow with API response ===\n")
    
    # Step 1: Simulate ruleset.signature as stored in database
    # This is what gets stored after POST /rulesets
    db_signature = [
        {
            "id": str(uuid.uuid4()),
            "name": "ninq",
            "dataType": "decimal",
            "direction": None,  # No direction specified when creating ruleset
            "length": None,
            "defaultValue": None,
            "dataGridExtension": None
        },
        {
            "id": str(uuid.uuid4()),
            "name": "otherTerm",
            "dataType": "string",
            "direction": "input",
            "length": 100,
            "defaultValue": None,
            "dataGridExtension": None
        }
    ]
    
    print("Step 1: Ruleset signature in database (before creating rule)")
    for term in db_signature:
        print(f"  {term['name']}: direction={term.get('direction')}")
    
    # Step 2: User's payload for POST /rules
    payload = {
        "name": "Default_rule_1",
        "description": None,
        "conditional": "if",
        "order_index": 1,
        "conditions": [
            {
                "term": {
                    "name": "ninq"
                },
                "type": "expression",
                "expression": "1"
            }
        ],
        "actions": [
            {
                "term": {
                    "name": "ninq"
                },
                "type": "assignment",
                "expression": "2"
            }
        ]
    }
    
    # Step 3: Parse payload
    rule_in = RuleCreate(**payload)
    print(f"\nStep 3: Parsed rule payload")
    print(f"  Rule name: {rule_in.name}")
    
    # Step 4: Extract term names
    condition_term_names = extract_term_names_from_conditions(rule_in.conditions)
    action_term_names = extract_term_names_from_actions(rule_in.actions)
    
    print(f"\nStep 4: Extract term names")
    print(f"  Condition terms: {condition_term_names}")
    print(f"  Action terms: {action_term_names}")
    print(f"  Inout terms: {condition_term_names & action_term_names}")
    
    # Step 5: Build signature term maps
    terms_by_id, terms_by_name = build_signature_term_maps(db_signature)
    print(f"\nStep 5: Build signature term maps")
    print(f"  terms_by_name keys: {list(terms_by_name.keys())}")
    
    # Step 6: Update signature direction (this is what create_rule does)
    signature_dicts = _signature_terms_to_dicts(db_signature)
    updated_signature, signature_updated = update_signature_direction_for_inout_terms(
        signature_dicts,
        condition_term_names,
        action_term_names,
        terms_by_name
    )
    
    print(f"\nStep 6: Update signature direction")
    print(f"  signature_updated: {signature_updated}")
    print(f"\n  Updated signature:")
    for term in updated_signature:
        print(f"    {term['name']}: direction={term.get('direction')}")
    
    # Step 7: Simulate what happens when ruleset is saved to database
    # updated_signature should be stored back to database
    print(f"\nStep 7: Check if 'ninq' has direction='inout'")
    for term in updated_signature:
        if term['name'] == 'ninq':
            if term.get('direction') == 'inout':
                print(f"  [OK] 'ninq' has direction='inout'")
            else:
                print(f"  [FAIL] 'ninq' direction is: {term.get('direction')}")
    
    # Step 8: Simulate GET /rulesets/{id} response
    # This is what happens in ruleset_to_detail_response
    print(f"\nStep 8: Simulate API response (GET /rulesets/{{id}})")
    
    # First, simulate what RuleSetResponseData.model_validate does
    # It will call validate_signature_field on the signature
    validated_signature = validate_signature_field(updated_signature)
    print(f"\n  After validate_signature_field:")
    for term in validated_signature:
        if isinstance(term, dict):
            print(f"    {term['name']}: direction={term.get('direction')}")
        else:
            # SignatureTerm object
            print(f"    {term.name}: direction={term.direction}")
    
    # Now simulate model_dump with exclude_none=True
    print(f"\n  Simulate model_dump(exclude_none=True):")
    
    # Create a mock ruleset object that would be returned from database
    class MockRuleset:
        def __init__(self, signature):
            self.id = uuid.uuid4()
            self.name = "test_ruleset"
            self.ruleSetType = "decision"
            self.description = "test"
            self.signature = signature
            self.version = 1
            self.major = 1
            self.minor = 0
            self.is_locked = False
            self.created_by = "test"
            self.created_datetime = "2024-01-01T00:00:00"
            self.modified_by = "test"
            self.modified_datetime = "2024-01-01T00:00:00"
            self.rules = []
    
    mock_ruleset = MockRuleset(updated_signature)
    
    # This is what ruleset_to_response does:
    # data = RuleSetResponseData.model_validate(ruleset)
    # response = RuleSetResponse(**data.model_dump(), _links=links)
    # result = response.model_dump(by_alias=True, exclude_none=True)
    
    # Let's do this step by step
    data = RuleSetResponseData.model_validate(mock_ruleset)
    print(f"\n  After RuleSetResponseData.model_validate:")
    for term in data.signature:
        print(f"    {term.name}: direction={term.direction} (type: {type(term.direction)})")
    
    # Now model_dump with exclude_none=True
    data_dict = data.model_dump()
    print(f"\n  data.model_dump() (without exclude_none):")
    for term in data_dict['signature']:
        print(f"    {term['name']}: direction={term.get('direction')}")
    
    # The critical part: exclude_none=True
    data_dict_exclude_none = data.model_dump(exclude_none=True)
    print(f"\n  data.model_dump(exclude_none=True):")
    for term in data_dict_exclude_none['signature']:
        print(f"    {term['name']}: direction={term.get('direction', 'MISSING!')}")
    
    # Check if 'ninq' has direction in the final response
    print(f"\nStep 9: Final check")
    for term in data_dict_exclude_none['signature']:
        if term['name'] == 'ninq':
            if 'direction' in term and term['direction'] == 'inout':
                print(f"  [OK] 'ninq' has direction='inout' in final API response")
            elif 'direction' in term:
                print(f"  [FAIL] 'ninq' direction is '{term['direction']}' (expected 'inout')")
            else:
                print(f"  [FAIL] 'ninq' has no 'direction' field in final API response!")
                print(f"         This is the problem! exclude_none=True is removing it.")
    
    # Let's also check what happens when direction is None vs "inout"
    print(f"\nStep 10: Understand exclude_none behavior")
    test_term_with_direction = SignatureTerm(
        name="test1",
        dataType=DataType.STRING,
        length=100,
        direction=Direction.INOUT
    )
    
    test_term_without_direction = SignatureTerm(
        name="test2",
        dataType=DataType.STRING,
        length=100,
        direction=None  # Explicitly None
    )
    
    test_term_no_direction_field = SignatureTerm(
        name="test3",
        dataType=DataType.STRING,
        length=100
        # No direction specified, defaults to None
    )
    
    print(f"\n  test1 (direction=Direction.INOUT):")
    print(f"    model_dump(): {test_term_with_direction.model_dump()}")
    print(f"    model_dump(exclude_none=True): {test_term_with_direction.model_dump(exclude_none=True)}")
    
    print(f"\n  test2 (direction=None explicitly):")
    print(f"    model_dump(): {test_term_without_direction.model_dump()}")
    print(f"    model_dump(exclude_none=True): {test_term_without_direction.model_dump(exclude_none=True)}")
    
    print(f"\n  test3 (no direction field, defaults to None):")
    print(f"    model_dump(): {test_term_no_direction_field.model_dump()}")
    print(f"    model_dump(exclude_none=True): {test_term_no_direction_field.model_dump(exclude_none=True)}")


def main():
    try:
        test_full_flow_with_api_response()
        print("\n=== Test completed ===")
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
