import json
import sys

from app.schemas.signature import SignatureTerm, DataType, Direction


def test_basic_signature_term():
    """Test basic SignatureTerm"""
    term = SignatureTerm(
        name="isHighCost",
        dataType=DataType.BOOLEAN,
        direction=Direction.OUTPUT
    )
    assert term.name == "isHighCost"
    assert term.dataType == DataType.BOOLEAN
    assert term.direction == Direction.OUTPUT
    print("[OK] Basic SignatureTerm test passed")


def test_string_with_length():
    """Test string type must have length"""
    try:
        SignatureTerm(
            name="accidentType",
            dataType=DataType.STRING,
        )
        assert False, "Should raise validation error"
    except ValueError as e:
        assert "length is required" in str(e)
        print("[OK] String type requires length validation passed")

    term = SignatureTerm(
        name="accidentType",
        dataType=DataType.STRING,
        length=100
    )
    assert term.length == 100
    print("[OK] String type with length test passed")


def test_decimal_type():
    """Test decimal type"""
    term = SignatureTerm(
        name="repairCost",
        dataType=DataType.DECIMAL,
        length=18
    )
    assert term.dataType == DataType.DECIMAL
    assert term.length == 18
    print("[OK] Decimal type test passed")


def test_data_grid_with_extension():
    """Test dataGrid type with nested extension"""
    term = SignatureTerm(
        name="accidents",
        dataType=DataType.DATAGRID,
        direction=Direction.INPUT,
        dataGridExtension=[
            SignatureTerm(
                name="accidentType",
                dataType=DataType.STRING,
                length=100
            ),
            SignatureTerm(
                name="repairCost",
                dataType=DataType.DECIMAL
            )
        ]
    )
    assert term.dataType == DataType.DATAGRID
    assert term.direction == Direction.INPUT
    assert len(term.dataGridExtension) == 2
    assert term.dataGridExtension[0].name == "accidentType"
    assert term.dataGridExtension[1].name == "repairCost"
    print("[OK] dataGrid type with nested extension test passed")


def test_data_grid_must_have_extension():
    """Test dataGrid type must have dataGridExtension"""
    try:
        SignatureTerm(
            name="accidents",
            dataType=DataType.DATAGRID,
            direction=Direction.INPUT
        )
        assert False, "Should raise validation error"
    except ValueError as e:
        assert "dataGridExtension is required" in str(e)
        print("[OK] dataGrid requires dataGridExtension validation passed")

    try:
        SignatureTerm(
            name="accidents",
            dataType=DataType.DATAGRID,
            direction=Direction.INPUT,
            dataGridExtension=[]
        )
        assert False, "Should raise validation error"
    except ValueError as e:
        assert "dataGridExtension cannot be empty" in str(e)
        print("[OK] dataGridExtension cannot be empty validation passed")


def test_non_data_grid_cannot_have_extension():
    """Test non-dataGrid type cannot have dataGridExtension"""
    try:
        SignatureTerm(
            name="test",
            dataType=DataType.STRING,
            length=100,
            dataGridExtension=[]
        )
        assert False, "Should raise validation error"
    except ValueError as e:
        assert "dataGridExtension should only be set" in str(e)
        print("[OK] Non-dataGrid cannot have dataGridExtension validation passed")


def test_length_only_for_string_and_decimal():
    """Test length can only be used for string and decimal types"""
    try:
        SignatureTerm(
            name="test",
            dataType=DataType.BOOLEAN,
            length=10
        )
        assert False, "Should raise validation error"
    except ValueError as e:
        assert "length can only be set" in str(e)
        print("[OK] Length only for string/decimal validation passed")


def test_serialization():
    """Test serialization and deserialization"""
    term = SignatureTerm(
        name="accidents",
        dataType=DataType.DATAGRID,
        direction=Direction.INPUT,
        dataGridExtension=[
            SignatureTerm(
                name="accidentType",
                dataType=DataType.STRING,
                length=100
            ),
            SignatureTerm(
                name="repairCost",
                dataType=DataType.DECIMAL
            )
        ]
    )

    data = term.model_dump()
    json_str = json.dumps(data, default=str)
    print(f"[OK] Serialization test passed: {json_str}")


def test_full_example():
    """Test the complete example provided by user"""
    from app.schemas.ruleset import RuleSetCreate

    ruleset = RuleSetCreate(
        name="TestRuleSet",
        ruleSetType="decision",
        description="Test ruleset with signature",
        signature=[
            SignatureTerm(
                name="accidents",
                dataType=DataType.DATAGRID,
                direction=Direction.INPUT,
                dataGridExtension=[
                    SignatureTerm(
                        name="accidentType",
                        dataType=DataType.STRING,
                        length=100
                    ),
                    SignatureTerm(
                        name="repairCost",
                        dataType=DataType.DECIMAL
                    )
                ]
            ),
            SignatureTerm(
                name="isHighCost",
                dataType=DataType.BOOLEAN,
                direction=Direction.OUTPUT
            )
        ]
    )

    data = ruleset.model_dump()
    assert data["name"] == "TestRuleSet"
    assert len(data["signature"]) == 2
    assert data["signature"][0]["name"] == "accidents"
    assert data["signature"][0]["dataType"] == "dataGrid"
    assert data["signature"][1]["name"] == "isHighCost"
    assert data["signature"][1]["dataType"] == "boolean"

    json_str = json.dumps(data, default=str, indent=2)
    print(f"[OK] Full example test passed:\n{json_str}")


def test_backward_compatibility_dict_signature():
    """Test backward compatibility with old dict format signature"""
    from app.schemas.ruleset import RuleSetResponseData
    import uuid
    from datetime import datetime

    data = {
        "id": uuid.uuid4(),
        "name": "TestRuleSet",
        "ruleSetType": "decision",
        "description": "Test",
        "signature": {"additionalProp1": {}},
        "version": 1,
        "is_locked": False,
        "created_by": "test",
        "created_datetime": datetime.now(),
        "modified_by": "test",
        "modified_datetime": datetime.now(),
    }

    result = RuleSetResponseData.model_validate(data)
    assert result.signature == []
    print("[OK] Backward compatibility: dict signature converted to empty list")


def test_backward_compatibility_with_orm_object():
    """Test backward compatibility with ORM object (simulating SQLAlchemy model)"""
    from app.schemas.ruleset import RuleSetResponseData, validate_signature_field
    import uuid
    from datetime import datetime

    class MockORMObject:
        def __init__(self):
            self._signature = {"additionalProp1": {}}
            self.id = uuid.uuid4()
            self.name = "TestRuleSet"
            self.ruleSetType = "decision"
            self.description = "Test"
            self.version = 1
            self.is_locked = False
            self.created_by = "test"
            self.created_datetime = datetime.now()
            self.modified_by = "test"
            self.modified_datetime = datetime.now()
        
        @property
        def signature(self):
            return self._signature

    mock_obj = MockORMObject()
    
    result = validate_signature_field(mock_obj.signature)
    assert result == []
    print("[OK] Backward compatibility: ORM object signature dict converted to empty list")


def test_backward_compatibility_empty_dict():
    """Test backward compatibility with empty dict signature"""
    from app.schemas.ruleset import RuleSetResponseData
    import uuid
    from datetime import datetime

    data = {
        "id": uuid.uuid4(),
        "name": "TestRuleSet",
        "ruleSetType": "decision",
        "description": "Test",
        "signature": {},
        "version": 1,
        "is_locked": False,
        "created_by": "test",
        "created_datetime": datetime.now(),
        "modified_by": "test",
        "modified_datetime": datetime.now(),
    }

    result = RuleSetResponseData.model_validate(data)
    assert result.signature == []
    print("[OK] Backward compatibility: empty dict converted to empty list")


def test_backward_compatibility_none_signature():
    """Test backward compatibility with None signature"""
    from app.schemas.ruleset import RuleSetResponseData
    import uuid
    from datetime import datetime

    data = {
        "id": uuid.uuid4(),
        "name": "TestRuleSet",
        "ruleSetType": "decision",
        "description": "Test",
        "signature": None,
        "version": 1,
        "is_locked": False,
        "created_by": "test",
        "created_datetime": datetime.now(),
        "modified_by": "test",
        "modified_datetime": datetime.now(),
    }

    result = RuleSetResponseData.model_validate(data)
    assert result.signature is None
    print("[OK] Backward compatibility: None signature remains None")


def test_backward_compatibility_list_signature():
    """Test that new list format works correctly"""
    from app.schemas.ruleset import RuleSetResponseData
    import uuid
    from datetime import datetime

    data = {
        "id": uuid.uuid4(),
        "name": "TestRuleSet",
        "ruleSetType": "decision",
        "description": "Test",
        "signature": [
            {
                "name": "isHighCost",
                "dataType": "boolean",
                "direction": "output"
            }
        ],
        "version": 1,
        "is_locked": False,
        "created_by": "test",
        "created_datetime": datetime.now(),
        "modified_by": "test",
        "modified_datetime": datetime.now(),
    }

    result = RuleSetResponseData.model_validate(data)
    assert len(result.signature) == 1
    assert result.signature[0].name == "isHighCost"
    assert result.signature[0].dataType.value == "boolean"
    print("[OK] Backward compatibility: list format works correctly")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8')
    print("Starting Signature model tests...\n")

    test_basic_signature_term()
    test_string_with_length()
    test_decimal_type()
    test_data_grid_with_extension()
    test_data_grid_must_have_extension()
    test_non_data_grid_cannot_have_extension()
    test_length_only_for_string_and_decimal()
    test_serialization()
    test_full_example()
    test_backward_compatibility_dict_signature()
    test_backward_compatibility_with_orm_object()
    test_backward_compatibility_empty_dict()
    test_backward_compatibility_none_signature()
    test_backward_compatibility_list_signature()

    print("\n[OK] All tests passed!")
