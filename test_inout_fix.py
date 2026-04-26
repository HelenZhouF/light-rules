import sys
sys.path.insert(0, 'c:\\workspace\\ai\\light-rules')

from app.schemas.signature import SignatureTerm, DataType, Direction
from app.services.execution import build_signature_maps


def test_direction_inout_enum():
    """Test that Direction.INOUT enum exists"""
    print("=== Testing Direction.INOUT enum ===")
    
    assert Direction.INOUT.value == "inout"
    print(f"  Direction.INOUT = '{Direction.INOUT.value}'")
    
    assert "inout" in [d.value for d in Direction]
    print("  [OK] Direction.INOUT enum exists\n")


def test_build_signature_maps_inout():
    """Test that build_signature_maps correctly handles 'inout' direction"""
    print("=== Testing build_signature_maps with inout direction ===")
    
    signature = [
        {"id": "1", "name": "term1", "dataType": "string", "direction": "input"},
        {"id": "2", "name": "term2", "dataType": "string", "direction": "output"},
        {"id": "3", "name": "term3", "dataType": "string", "direction": "inout"},
        {"id": "4", "name": "term4", "dataType": "string"},
    ]
    
    terms_by_name, input_terms, output_terms = build_signature_maps(signature)
    
    print(f"  All terms: {list(terms_by_name.keys())}")
    print(f"  Input terms: {list(input_terms.keys())}")
    print(f"  Output terms: {list(output_terms.keys())}")
    
    assert "term1" in input_terms
    assert "term1" not in output_terms
    print("  [OK] term1 is input only")
    
    assert "term2" not in input_terms
    assert "term2" in output_terms
    print("  [OK] term2 is output only")
    
    assert "term3" in input_terms
    assert "term3" in output_terms
    print("  [OK] term3 (inout) is in both input and output")
    
    assert "term4" in input_terms
    assert "term4" in output_terms
    print("  [OK] term4 (no direction) is in both input and output")
    
    print("  [OK] All build_signature_maps tests passed!\n")


def test_signature_term_inout():
    """Test SignatureTerm with direction=inout"""
    print("=== Testing SignatureTerm with direction=inout ===")
    
    term = SignatureTerm(
        name="testTerm",
        dataType=DataType.STRING,
        length=100,
        direction=Direction.INOUT
    )
    
    assert term.direction == Direction.INOUT
    assert term.direction.value == "inout"
    print(f"  Term direction: {term.direction.value}")
    
    data = term.model_dump()
    assert data["direction"] == "inout"
    print(f"  Serialized direction: {data['direction']}")
    
    print("  [OK] SignatureTerm with inout direction works!\n")


def test_extract_term_names():
    """Test extracting term names from conditions and actions"""
    print("=== Testing extract term names from conditions/actions ===")
    
    from app.crud.rule import (
        extract_term_names_from_conditions,
        extract_term_names_from_actions,
    )
    from app.schemas.condition_action import (
        ConditionCreate,
        ActionCreate,
        TermRef,
        ConditionType,
        ActionType,
    )
    
    conditions = [
        ConditionCreate(
            term=TermRef(name="inputTerm1"),
            type=ConditionType.EXPRESSION,
            expression="> 10"
        ),
        ConditionCreate(
            term=TermRef(name="sharedTerm"),
            type=ConditionType.EXPRESSION,
            expression="== 'test'"
        ),
    ]
    
    actions = [
        ActionCreate(
            term=TermRef(name="outputTerm1"),
            type=ActionType.ASSIGNMENT,
            expression="true"
        ),
        ActionCreate(
            term=TermRef(name="sharedTerm"),
            type=ActionType.ASSIGNMENT,
            expression="'updated'"
        ),
    ]
    
    condition_terms = extract_term_names_from_conditions(conditions)
    action_terms = extract_term_names_from_actions(actions)
    
    print(f"  Condition terms: {condition_terms}")
    print(f"  Action terms: {action_terms}")
    
    assert "inputTerm1" in condition_terms
    assert "sharedTerm" in condition_terms
    print("  [OK] Condition terms extracted correctly")
    
    assert "outputTerm1" in action_terms
    assert "sharedTerm" in action_terms
    print("  [OK] Action terms extracted correctly")
    
    inout_terms = condition_terms & action_terms
    assert "sharedTerm" in inout_terms
    assert "inputTerm1" not in inout_terms
    assert "outputTerm1" not in inout_terms
    print(f"  Inout terms (intersection): {inout_terms}")
    print("  [OK] Inout terms detected correctly!\n")


def test_update_signature_direction():
    """Test updating signature direction for inout terms"""
    print("=== Testing update_signature_direction_for_inout_terms ===")
    
    from app.crud.rule import update_signature_direction_for_inout_terms
    
    signature = [
        {"id": "1", "name": "inputOnly", "dataType": "string", "direction": "input"},
        {"id": "2", "name": "outputOnly", "dataType": "string", "direction": "output"},
        {"id": "3", "name": "sharedTerm", "dataType": "string", "direction": "input"},
        {"id": "4", "name": "alreadyInout", "dataType": "string", "direction": "inout"},
    ]
    
    condition_terms = {"inputOnly", "sharedTerm"}
    action_terms = {"outputOnly", "sharedTerm", "alreadyInout"}
    terms_by_name = {
        "inputOnly": {"name": "inputOnly"},
        "outputOnly": {"name": "outputOnly"},
        "sharedTerm": {"name": "sharedTerm"},
        "alreadyInout": {"name": "alreadyInout"},
    }
    
    updated_signature, was_updated = update_signature_direction_for_inout_terms(
        signature,
        condition_terms,
        action_terms,
        terms_by_name
    )
    
    print(f"  Was updated: {was_updated}")
    
    assert was_updated == True
    print("  [OK] Signature was updated")
    
    for term in updated_signature:
        if term["name"] == "inputOnly":
            assert term["direction"] == "input", f"inputOnly should be input, got {term['direction']}"
            print(f"  inputOnly: {term['direction']} (correct)")
        elif term["name"] == "outputOnly":
            assert term["direction"] == "output", f"outputOnly should be output, got {term['direction']}"
            print(f"  outputOnly: {term['direction']} (correct)")
        elif term["name"] == "sharedTerm":
            assert term["direction"] == "inout", f"sharedTerm should be inout, got {term['direction']}"
            print(f"  sharedTerm: {term['direction']} (correct - updated to inout)")
        elif term["name"] == "alreadyInout":
            assert term["direction"] == "inout", f"alreadyInout should be inout, got {term['direction']}"
            print(f"  alreadyInout: {term['direction']} (correct - already inout)")
    
    print("  [OK] All signature direction updates correct!\n")


def main():
    try:
        test_direction_inout_enum()
        test_build_signature_maps_inout()
        test_signature_term_inout()
        test_extract_term_names()
        test_update_signature_direction()
        
        print("=== All tests passed! ===")
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
