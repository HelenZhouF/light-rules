import sys
import uuid
import asyncio
sys.path.insert(0, 'c:\\workspace\\ai\\light-rules')

from sqlalchemy import text
from app.core.database import engine, async_session_maker
from app.crud.ruleset import (
    detect_term_renames,
    update_term_in_list,
    build_term_comparison_key,
    get_ruleset_by_id,
    update_ruleset
)
from app.crud.rule import (
    create_rule,
    get_rules_by_ruleset_id
)
from app.schemas.rule import RuleCreate
from app.schemas.ruleset import RuleSetUpdate
from app.schemas.condition_action import (
    ConditionCreate,
    ActionCreate,
    TermRef,
    ConditionType,
    ActionType
)


async def test_detect_renames():
    print("=== Testing detect_term_renames ===")
    
    old_signature = [
        {"name": "vehicleCost", "dataType": "decimal", "direction": "input"},
        {"name": "model", "dataType": "string", "direction": "input", "length": 100}
    ]
    
    new_signature = [
        {"name": "vehiclePrice", "dataType": "decimal", "direction": "input"},
        {"name": "model", "dataType": "string", "direction": "input", "length": 100}
    ]
    
    name_mapping = detect_term_renames(old_signature, new_signature)
    print(f"Old signature: {old_signature}")
    print(f"New signature: {new_signature}")
    print(f"Detected renames: {name_mapping}")
    assert name_mapping == {"vehicleCost": "vehiclePrice"}, f"Expected {{'vehicleCost': 'vehiclePrice'}}, got {name_mapping}"
    print("OK: detect_term_renames test passed!")


async def test_update_term_in_list():
    print("\n=== Testing update_term_in_list ===")
    
    conditions = [
        {
            "term": {"name": "vehicleCost"},
            "expression": "> 10",
            "type": "expression",
            "id": "test-1"
        }
    ]
    
    name_mapping = {"vehicleCost": "vehiclePrice"}
    
    updated = update_term_in_list(conditions, name_mapping)
    print(f"Original conditions: {conditions}")
    print(f"Updated conditions: {updated}")
    assert updated[0]["term"]["name"] == "vehiclePrice", f"Expected 'vehiclePrice', got {updated[0]['term']['name']}"
    print("OK: update_term_in_list test passed!")


async def test_full_cascade_update():
    print("\n=== Testing full cascade update ===")
    
    ruleset_id = uuid.UUID("b2e2512c-debf-41b2-99b3-cb8b3b0ac29f")
    
    async with async_session_maker() as db:
        ruleset = await get_ruleset_by_id(db, ruleset_id)
        if not ruleset:
            print("ERROR: Could not find rs2_with_sig ruleset")
            return
        
        print(f"Found ruleset: {ruleset.name}")
        print(f"Original signature: {ruleset.signature}")
        
        original_signature = ruleset.signature
        
        new_signature = []
        for term in original_signature:
            if term.get("name") == "vehicleCost":
                new_term = dict(term)
                new_term["name"] = "vehiclePrice"
                new_signature.append(new_term)
            else:
                new_signature.append(term)
        
        print(f"New signature: {new_signature}")
        
        ruleset_update = RuleSetUpdate(
            signature=new_signature
        )
        
        updated_ruleset = await update_ruleset(
            db=db,
            ruleset_id=ruleset_id,
            ruleset_in=ruleset_update
        )
        
        print(f"Updated ruleset signature: {updated_ruleset.signature}")
        
        rules = await get_rules_by_ruleset_id(db, rule_set_id=ruleset_id)
        print(f"\nFound {len(rules)} rules in this ruleset")
        
        for rule in rules:
            print(f"\nRule: {rule.name}")
            if rule.conditions:
                for cond in rule.conditions:
                    term_name = cond.get("term", {}).get("name", "N/A")
                    print(f"  Condition term: {term_name}")
            if rule.actions:
                for action in rule.actions:
                    term_name = action.get("term", {}).get("name", "N/A")
                    print(f"  Action term: {term_name}")
        
        revert_update = RuleSetUpdate(
            signature=original_signature
        )
        await update_ruleset(
            db=db,
            ruleset_id=ruleset_id,
            ruleset_in=revert_update
        )
        print("\nOK: Reverted signature back to original")


async def main():
    try:
        await test_detect_renames()
        await test_update_term_in_list()
        await test_full_cascade_update()
        print("\n=== All tests passed! ===")
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
