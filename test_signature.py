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

    print("\n[OK] All tests passed!")
