import sys
import uuid
import json
sys.path.insert(0, 'c:\\workspace\\ai\\light-rules')

from app.schemas.signature import SignatureTerm, DataType, Direction
from app.crud.ruleset import _signature_terms_to_dicts, _convert_enum_to_value


def test_convert_enum_to_value():
    """Test that _convert_enum_to_value correctly converts enums and UUIDs"""
    print("=== Testing _convert_enum_to_value ===")
    
    test_uuid = uuid.uuid4()
    test_obj = {
        "id": test_uuid,
        "dataType": DataType.DECIMAL,
        "direction": Direction.INOUT,
        "nested": {
            "id": uuid.uuid4(),
            "dataType": DataType.STRING,
        },
        "list": [
            {"direction": Direction.INPUT},
            {"direction": Direction.OUTPUT},
        ]
    }
    
    converted = _convert_enum_to_value(test_obj)
    
    assert converted["id"] == str(test_uuid)
    print(f"  UUID converted: {converted['id']}")
    
    assert converted["dataType"] == "decimal"
    print(f"  DataType enum converted: {converted['dataType']}")
    
    assert converted["direction"] == "inout"
    print(f"  Direction enum converted: {converted['direction']}")
    
    assert converted["nested"]["dataType"] == "string"
    print(f"  Nested enum converted: {converted['nested']['dataType']}")
    
    assert converted["list"][0]["direction"] == "input"
    assert converted["list"][1]["direction"] == "output"
    print(f"  List enums converted: {converted['list']}")
    
    print("  [OK] All enum conversions passed!\n")


def test_signature_terms_to_dicts():
    """Test that _signature_terms_to_dicts correctly converts SignatureTerm objects"""
    print("=== Testing _signature_terms_to_dicts with SignatureTerm ===")
    
    signature = [
        SignatureTerm(
            name="inputTerm",
            dataType=DataType.STRING,
            length=100,
            direction=Direction.INPUT
        ),
        SignatureTerm(
            name="outputTerm",
            dataType=DataType.BOOLEAN,
            direction=Direction.OUTPUT
        ),
        SignatureTerm(
            name="inoutTerm",
            dataType=DataType.DECIMAL,
            direction=Direction.INOUT
        ),
        SignatureTerm(
            name="dataGridTerm",
            dataType=DataType.DATAGRID,
            direction=Direction.INPUT,
            dataGridExtension=[
                SignatureTerm(
                    name="nestedString",
                    dataType=DataType.STRING,
                    length=50
                ),
                SignatureTerm(
                    name="nestedDecimal",
                    dataType=DataType.DECIMAL
                ),
            ]
        ),
    ]
    
    converted = _signature_terms_to_dicts(signature)
    
    assert converted is not None
    assert len(converted) == 4
    
    for i, term in enumerate(converted):
        print(f"\n  Term[{i}]: {term['name']}")
        print(f"    id type: {type(term['id'])} (should be str)")
        print(f"    dataType: {term['dataType']} (should be str)")
        print(f"    direction: {term.get('direction')}")
        
        assert isinstance(term["id"], str), f"id should be str, got {type(term['id'])}"
        assert isinstance(term["dataType"], str), f"dataType should be str, got {type(term['dataType'])}"
        
        if term.get("dataGridExtension"):
            for j, nested in enumerate(term["dataGridExtension"]):
                print(f"      Nested[{j}]: {nested['name']}")
                print(f"        id type: {type(nested['id'])}")
                print(f"        dataType: {nested['dataType']}")
                assert isinstance(nested["id"], str)
                assert isinstance(nested["dataType"], str)
    
    print("\n  [OK] All SignatureTerm conversions passed!\n")


def test_json_serializable():
    """Test that converted signature is JSON serializable"""
    print("=== Testing JSON serializability ===")
    
    signature = [
        SignatureTerm(
            name="testTerm",
            dataType=DataType.STRING,
            length=100,
            direction=Direction.INOUT
        ),
    ]
    
    converted = _signature_terms_to_dicts(signature)
    
    try:
        json_str = json.dumps(converted)
        print(f"  JSON serialized successfully: {json_str}")
        
        parsed = json.loads(json_str)
        assert parsed[0]["name"] == "testTerm"
        assert parsed[0]["dataType"] == "string"
        assert parsed[0]["direction"] == "inout"
        
        print("  [OK] JSON serialization test passed!\n")
    except TypeError as e:
        print(f"  [FAIL] JSON serialization failed: {e}")
        raise


def main():
    try:
        test_convert_enum_to_value()
        test_signature_terms_to_dicts()
        test_json_serializable()
        
        print("=== All tests passed! ===")
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
