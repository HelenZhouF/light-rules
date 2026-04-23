import sys
import uuid
import asyncio
sys.path.insert(0, 'c:\\workspace\\ai\\light-rules')

from sqlalchemy import text
from app.core.database import engine, async_session_maker
from app.crud.ruleset import (
    detect_term_renames_by_id,
    reconcile_signature_ids,
    update_term_refs_in_list,
    build_term_maps_by_id,
    build_term_maps_by_name,
    _term_to_dict,
    get_ruleset_by_id,
    update_ruleset,
    create_ruleset,
    delete_ruleset
)
from app.crud.rule import (
    create_rule,
    get_rules_by_ruleset_id,
    get_rule_by_id
)
from app.schemas.rule import RuleCreate
from app.schemas.ruleset import RuleSetCreate, RuleSetUpdate
from app.schemas.condition_action import (
    ConditionCreate,
    ActionCreate,
    TermRef,
    ConditionType,
    ActionType
)
from app.schemas.signature import SignatureTerm, DataType, Direction


def test_reconcile_signature_ids():
    print("=== Testing reconcile_signature_ids ===")
    
    old_signature = [
        {"id": uuid.UUID("11111111-1111-1111-1111-111111111111"), "name": "aaa", "dataType": "string", "length": 100},
        {"id": uuid.UUID("22222222-2222-2222-2222-222222222222"), "name": "bbb", "dataType": "string", "length": 100},
        {"id": uuid.UUID("33333333-3333-3333-3333-333333333333"), "name": "ccc", "dataType": "string", "length": 100},
    ]
    
    print(f"Old signature: {old_signature}")
    
    new_signature_without_id = [
        {"name": "aaa1", "dataType": "string", "length": 100},
        {"name": "bbb", "dataType": "string", "length": 100},
        {"name": "ccc", "dataType": "string", "length": 100},
    ]
    
    print(f"New signature (without id): {new_signature_without_id}")
    
    reconciled = reconcile_signature_ids(old_signature, new_signature_without_id)
    print(f"Reconciled signature: {reconciled}")
    
    assert reconciled is not None
    assert reconciled[0]["id"] == uuid.UUID("11111111-1111-1111-1111-111111111111")
    assert reconciled[0]["name"] == "aaa1"
    assert reconciled[1]["id"] == uuid.UUID("22222222-2222-2222-2222-222222222222")
    assert reconciled[1]["name"] == "bbb"
    assert reconciled[2]["id"] == uuid.UUID("33333333-3333-3333-3333-333333333333")
    assert reconciled[2]["name"] == "ccc"
    
    print("[OK] reconcile_signature_ids test passed!\n")


def test_detect_term_renames_by_id():
    print("=== Testing detect_term_renames_by_id ===")
    
    old_signature = [
        {"id": uuid.UUID("11111111-1111-1111-1111-111111111111"), "name": "aaa", "dataType": "string", "length": 100},
        {"id": uuid.UUID("22222222-2222-2222-2222-222222222222"), "name": "bbb", "dataType": "string", "length": 100},
    ]
    
    new_signature = [
        {"id": uuid.UUID("11111111-1111-1111-1111-111111111111"), "name": "aaa1", "dataType": "string", "length": 100},
        {"id": uuid.UUID("22222222-2222-2222-2222-222222222222"), "name": "bbb", "dataType": "string", "length": 100},
    ]
    
    name_mapping = detect_term_renames_by_id(old_signature, new_signature)
    print(f"Old signature: {old_signature}")
    print(f"New signature: {new_signature}")
    print(f"Detected renames: {name_mapping}")
    
    assert name_mapping == {"aaa": "aaa1"}, f"Expected {{'aaa': 'aaa1'}}, got {name_mapping}"
    
    print("[OK] detect_term_renames_by_id test passed!\n")


def test_update_term_refs_in_list():
    print("=== Testing update_term_refs_in_list ===")
    
    conditions = [
        {
            "id": "cond-1",
            "term": {"termId": "11111111-1111-1111-1111-111111111111", "name": "aaa"},
            "expression": "== 'test'",
            "type": "expression"
        },
        {
            "id": "cond-2",
            "term": {"termId": "22222222-2222-2222-2222-222222222222", "name": "bbb"},
            "expression": "> 0",
            "type": "expression"
        }
    ]
    
    name_mapping = {"aaa": "aaa1"}
    
    new_signature = [
        {"id": uuid.UUID("11111111-1111-1111-1111-111111111111"), "name": "aaa1", "dataType": "string", "length": 100},
        {"id": uuid.UUID("22222222-2222-2222-2222-222222222222"), "name": "bbb", "dataType": "string", "length": 100},
    ]
    
    print(f"Original conditions: {conditions}")
    print(f"Name mapping: {name_mapping}")
    print(f"New signature: {new_signature}")
    
    updated = update_term_refs_in_list(conditions, name_mapping, new_signature)
    print(f"Updated conditions: {updated}")
    
    assert updated is not None
    assert updated[0]["term"]["name"] == "aaa1", f"Expected 'aaa1', got {updated[0]['term']['name']}"
    assert updated[1]["term"]["name"] == "bbb", f"Expected 'bbb', got {updated[1]['term']['name']}"
    
    print("[OK] update_term_refs_in_list test passed!\n")


async def test_full_flow():
    print("=== Testing full flow (database) ===")
    
    async with async_session_maker() as db:
        print("\nStep 1: Create a new ruleset")
        ruleset_create = RuleSetCreate(
            name=f"Test_Ruleset_{uuid.uuid4()}",
            ruleSetType="decision",
            description="Test ruleset for term rename"
        )
        
        ruleset = await create_ruleset(db=db, ruleset_in=ruleset_create, created_by="test")
        ruleset_id = ruleset.id
        print(f"Created ruleset: {ruleset.name} (id: {ruleset_id})")
        print(f"Initial signature: {ruleset.signature}")
        
        print("\nStep 2: PUT /ruleset/{rs_id} - add signature: aaa, bbb, ccc")
        signature_with_aaa_bbb_ccc = [
            SignatureTerm(name="aaa", dataType=DataType.STRING, length=100, direction=Direction.INPUT),
            SignatureTerm(name="bbb", dataType=DataType.STRING, length=100, direction=Direction.INPUT),
            SignatureTerm(name="ccc", dataType=DataType.STRING, length=100, direction=Direction.OUTPUT),
        ]
        
        ruleset_update = RuleSetUpdate(
            signature=signature_with_aaa_bbb_ccc
        )
        
        updated_ruleset = await update_ruleset(
            db=db,
            ruleset_id=ruleset_id,
            ruleset_in=ruleset_update,
            modified_by="test"
        )
        
        print(f"Updated signature: {updated_ruleset.signature}")
        
        signature_terms = []
        for term in updated_ruleset.signature:
            term_dict = _term_to_dict(term)
            if term_dict:
                signature_terms.append(term_dict)
        
        print(f"Signature terms (dict): {signature_terms}")
        
        print("\nStep 3: Create a rule with condition.term.name = aaa, action.term.name = bbb")
        rule_create = RuleCreate(
            name="Test_Rule_1",
            description="Test rule",
            conditional="all",
            order_index=0,
            conditions=[
                ConditionCreate(
                    term=TermRef(name="aaa"),
                    expression="== 'test'",
                    type=ConditionType.EXPRESSION
                )
            ],
            actions=[
                ActionCreate(
                    term=TermRef(name="bbb"),
                    expression="'updated'",
                    type=ActionType.ASSIGNMENT
                )
            ]
        )
        
        rule = await create_rule(
            db=db,
            rule_in=rule_create,
            rule_set_id=ruleset_id,
            signature=signature_terms,
            created_by="test"
        )
        
        print(f"Created rule: {rule.name}")
        print(f"Rule conditions: {rule.conditions}")
        print(f"Rule actions: {rule.actions}")
        
        print("\nStep 4: PUT this ruleset - update signature aaa to aaa1")
        
        new_signature_aaa1 = [
            SignatureTerm(name="aaa1", dataType=DataType.STRING, length=100, direction=Direction.INPUT),
            SignatureTerm(name="bbb", dataType=DataType.STRING, length=100, direction=Direction.INPUT),
            SignatureTerm(name="ccc", dataType=DataType.STRING, length=100, direction=Direction.OUTPUT),
        ]
        
        ruleset_update_rename = RuleSetUpdate(
            signature=new_signature_aaa1
        )
        
        updated_ruleset_rename = await update_ruleset(
            db=db,
            ruleset_id=ruleset_id,
            ruleset_in=ruleset_update_rename,
            modified_by="test"
        )
        
        print(f"Updated signature (after rename): {updated_ruleset_rename.signature}")
        
        print("\nStep 5: Check rule's conditions and actions in database")
        rules = await get_rules_by_ruleset_id(db, rule_set_id=ruleset_id)
        
        for r in rules:
            print(f"\nRule: {r.name}")
            print(f"  Conditions: {r.conditions}")
            print(f"  Actions: {r.actions}")
            
            if r.conditions:
                for cond in r.conditions:
                    term_name = cond.get("term", {}).get("name", "N/A")
                    term_id = cond.get("term", {}).get("termId", "N/A")
                    print(f"  Condition term: name={term_name}, termId={term_id}")
            
            if r.actions:
                for action in r.actions:
                    term_name = action.get("term", {}).get("name", "N/A")
                    term_id = action.get("term", {}).get("termId", "N/A")
                    print(f"  Action term: name={term_name}, termId={term_id}")
        
        print("\nStep 6: Clean up - delete the ruleset")
        await delete_ruleset(db=db, ruleset_id=ruleset_id)
        print(f"Deleted ruleset: {ruleset_id}")
        
        print("\n[OK] Full flow test completed!\n")


async def main():
    try:
        test_reconcile_signature_ids()
        test_detect_term_renames_by_id()
        test_update_term_refs_in_list()
        
        await test_full_flow()
        
        print("\n=== All tests passed! ===")
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
