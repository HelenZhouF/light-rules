import sys
sys.path.insert(0, 'c:\\workspace\\ai\\light-rules')

from app.services.import_service import (
    process_csv_import,
    generate_signature_from_terms,
    group_rows_by_ruleset,
    validate_all_rows,
    parse_csv_content,
    ParsedRuleSet,
)
from app.schemas.signature import SignatureTerm, DataType, Direction


def test_generate_signature_from_terms_with_direction():
    """Test generate_signature_from_terms with direction logic"""
    print("=== Test generate_signature_from_terms with direction ===\n")
    
    term_names = {"ninq", "onlyInput", "onlyOutput"}
    term_datatypes = {
        "ninq": "decimal",
        "onlyInput": "string",
        "onlyOutput": "string",
    }
    
    condition_term_names = {"ninq", "onlyInput"}
    action_term_names = {"ninq", "onlyOutput"}
    
    signature = generate_signature_from_terms(
        term_names,
        term_datatypes,
        condition_term_names,
        action_term_names,
        default_length=100,
    )
    
    print(f"Generated signature with {len(signature)} terms:")
    for term in signature:
        print(f"  {term.name}: direction={term.direction}, dataType={term.dataType}")
    
    # Check each term
    for term in signature:
        if term.name == "ninq":
            # ninq is in both condition and action -> should be inout
            assert term.direction == Direction.INOUT, f"ninq should be inout, got {term.direction}"
            print(f"\n  [OK] 'ninq' has direction='inout' (in both condition and action)")
        elif term.name == "onlyInput":
            # onlyInput is only in condition -> should be input
            assert term.direction == Direction.INPUT, f"onlyInput should be input, got {term.direction}"
            print(f"  [OK] 'onlyInput' has direction='input' (only in condition)")
        elif term.name == "onlyOutput":
            # onlyOutput is only in action -> should be output
            assert term.direction == Direction.OUTPUT, f"onlyOutput should be output, got {term.direction}"
            print(f"  [OK] 'onlyOutput' has direction='output' (only in action)")
    
    print("\n  [OK] All direction tests passed!\n")


def test_user_csv_scenario():
    """Test the exact scenario described by user"""
    print("=== Test user's CSV scenario ===\n")
    
    # User's CSV data (simplified)
    csv_content = """ruleset_id,ruleset_nm,ruleset_desc,rule_id,rule_nm,rule_desc,rule_seq_no,conditional,datatype,lhs_term,expression,expression_type,expression_order
fc96e3b2-0003-4ebb-bf3b-5409a2183da6,hmeq_ninq,,,,8eccd5bb-a1f5-4084-8669-e80dd594b881,Default_rule_1,,1,if,decimal,ninq,1,CONDITION,1
fc96e3b2-0003-4ebb-bf3b-5409a2183da6,hmeq_ninq,,,,8eccd5bb-a1f5-4084-8669-e80dd594b881,Default_rule_1,,1,if,decimal,ninq,2,ACTION,1
fc96e3b2-0003-4ebb-bf3b-5409a2183da6,hmeq_ninq,,,,15780b99-88ae-4076-8bd5-0fcd7b9ea8af,Default_rule_2,,2,if,decimal,ninq,0,CONDITION,1
"""
    
    print("CSV Content:")
    print(csv_content)
    
    # Parse CSV
    rows, parse_error = parse_csv_content(csv_content)
    if parse_error:
        print(f"Parse error: {parse_error}")
        return
    
    print(f"Parsed {len(rows)} rows")
    
    # Validate
    accepted, rejected = validate_all_rows(rows)
    print(f"Accepted: {len(accepted)}, Rejected: {len(rejected)}")
    
    # Group by ruleset
    rulesets = group_rows_by_ruleset(accepted)
    print(f"Parsed {len(rulesets)} ruleset(s)")
    
    for ruleset_id, parsed_ruleset in rulesets.items():
        print(f"\nRuleset: {parsed_ruleset.ruleset_nm}")
        print(f"  All term names: {parsed_ruleset.all_term_names}")
        print(f"  Term datatypes: {parsed_ruleset.term_datatypes}")
        
        # Collect condition and action terms
        condition_term_names = set()
        action_term_names = set()
        
        for rule_id, parsed_rule in parsed_ruleset.rules.items():
            print(f"\n  Rule: {parsed_rule.rule_nm}")
            print(f"    Conditions: {[c.term_name for c in parsed_rule.conditions]}")
            print(f"    Actions: {[a.term_name for a in parsed_rule.actions]}")
            
            for condition in parsed_rule.conditions:
                condition_term_names.add(condition.term_name)
            for action in parsed_rule.actions:
                action_term_names.add(action.term_name)
        
        print(f"\n  Condition terms: {condition_term_names}")
        print(f"  Action terms: {action_term_names}")
        print(f"  Inout terms (intersection): {condition_term_names & action_term_names}")
        
        # Generate signature
        signature = generate_signature_from_terms(
            parsed_ruleset.all_term_names,
            parsed_ruleset.term_datatypes,
            condition_term_names,
            action_term_names,
            default_length=100,
        )
        
        print(f"\n  Generated signature:")
        for term in signature:
            print(f"    {term.name}: direction={term.direction}, dataType={term.dataType}")
        
        # Check 'ninq' term
        for term in signature:
            if term.name == "ninq":
                print(f"\n  Checking 'ninq' term:")
                print(f"    direction: {term.direction}")
                print(f"    direction.value: {term.direction.value if term.direction else None}")
                
                if term.direction == Direction.INOUT:
                    print(f"  [OK] 'ninq' has direction='inout'!")
                else:
                    print(f"  [FAIL] 'ninq' should have direction='inout', got {term.direction}")
                    
                # Test model_dump with exclude_none=True
                term_dict = term.model_dump(exclude_none=True)
                print(f"\n    model_dump(exclude_none=True):")
                print(f"      {term_dict}")
                
                if "direction" in term_dict:
                    print(f"  [OK] 'direction' field is present in model_dump output")
                    print(f"      direction value: {term_dict['direction']}")
                else:
                    print(f"  [FAIL] 'direction' field is NOT present in model_dump output")
                    print(f"      This means direction was None and excluded by exclude_none=True")


def main():
    try:
        test_generate_signature_from_terms_with_direction()
        test_user_csv_scenario()
        
        print("\n=== All tests completed ===")
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
