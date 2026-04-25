import sys
import uuid
from app.services.import_service import (
    process_csv_import,
    generate_accept_csv,
    generate_reject_csv,
    generate_signature_from_terms,
    unescape_csv_expression,
    parse_csv_content,
    validate_row,
    validate_all_rows,
    group_rows_by_ruleset,
    CSVRow,
)


SAMPLE_CSV = (
    "ruleset_id,ruleset_nm,ruleset_desc,rule_id,rule_nm,rule_desc,rule_seq_no,conditional,datatype,lhs_term,expression,expression_type,expression_order\n"
    "fc96e3b2-0003-4ebb-bf3b-5409a2183da6,hmeq_ninq,,8eccd5bb-a1f5-4084-8669-e80dd594b881,Default_rule_1,,1,if,decimal,ninq,1,CONDITION,1\n"
    'fc96e3b2-0003-4ebb-bf3b-5409a2183da6,hmeq_ninq,,8eccd5bb-a1f5-4084-8669-e80dd594b881,Default_rule_1,,1,if,string,out,"\'ninq is 1\'",ACTION,1\n'
    "fc96e3b2-0003-4ebb-bf3b-5409a2183da6,hmeq_ninq,,15780b99-88ae-4076-8bd5-0fcd7b9ea8af,Default_rule_2,,2,if,decimal,ninq,0,CONDITION,1\n"
)


def test_unescape_csv_expression():
    assert unescape_csv_expression("'ninq is 1'") == "ninq is 1"
    assert unescape_csv_expression("'''ninq is 1'''") == "'ninq is 1'"
    assert unescape_csv_expression("1") == "1"
    assert unescape_csv_expression("") == ""
    assert unescape_csv_expression(None) is None
    print("[OK] test_unescape_csv_expression passed")


def test_parse_csv_content():
    rows, error = parse_csv_content(SAMPLE_CSV)
    assert error is None, f"Parse error: {error}"
    assert len(rows) == 3
    
    assert rows[0].ruleset_id == "fc96e3b2-0003-4ebb-bf3b-5409a2183da6"
    assert rows[0].ruleset_nm == "hmeq_ninq"
    assert rows[0].rule_nm == "Default_rule_1"
    assert rows[0].expression_type == "CONDITION"
    
    assert rows[1].expression_type == "ACTION"
    assert rows[1].expression == "'ninq is 1'"
    
    assert rows[2].rule_nm == "Default_rule_2"
    
    print("[OK] test_parse_csv_content passed")


def test_validate_row():
    valid_row = CSVRow(
        line_number=2,
        ruleset_id="fc96e3b2-0003-4ebb-bf3b-5409a2183da6",
        ruleset_nm="hmeq_ninq",
        ruleset_desc="",
        rule_id="8eccd5bb-a1f5-4084-8669-e80dd594b881",
        rule_nm="Default_rule_1",
        rule_desc="",
        rule_seq_no="1",
        conditional="if",
        datatype="decimal",
        lhs_term="ninq",
        expression="1",
        expression_type="CONDITION",
        expression_order="1",
        raw={},
    )
    
    validated = validate_row(valid_row)
    assert validated.is_valid, f"Errors: {validated.errors}"
    print("[OK] test_validate_row with valid row passed")
    
    invalid_row = CSVRow(
        line_number=2,
        ruleset_id="invalid-uuid",
        ruleset_nm="",
        ruleset_desc="",
        rule_id="invalid-rule-uuid",
        rule_nm="",
        rule_desc="",
        rule_seq_no="not-a-number",
        conditional="",
        datatype="invalid-type",
        lhs_term="",
        expression="1",
        expression_type="INVALID_TYPE",
        expression_order="-5",
        raw={},
    )
    
    validated = validate_row(invalid_row)
    assert not validated.is_valid
    assert len(validated.errors) > 0
    print(f"[OK] test_validate_row with invalid row passed, errors: {validated.errors}")


def test_validate_all_rows():
    rows, error = parse_csv_content(SAMPLE_CSV)
    assert error is None
    
    accepted, rejected = validate_all_rows(rows)
    assert len(accepted) == 3
    assert len(rejected) == 0
    print("[OK] test_validate_all_rows passed")


def test_group_rows_by_ruleset():
    rows, error = parse_csv_content(SAMPLE_CSV)
    assert error is None
    
    accepted, rejected = validate_all_rows(rows)
    assert len(rejected) == 0
    
    rulesets = group_rows_by_ruleset(accepted)
    assert len(rulesets) == 1
    
    ruleset_id = uuid.UUID("fc96e3b2-0003-4ebb-bf3b-5409a2183da6")
    assert ruleset_id in rulesets
    
    ruleset = rulesets[ruleset_id]
    assert ruleset.ruleset_nm == "hmeq_ninq"
    
    assert len(ruleset.rules) == 2
    
    rule1_id = uuid.UUID("8eccd5bb-a1f5-4084-8669-e80dd594b881")
    rule2_id = uuid.UUID("15780b99-88ae-4076-8bd5-0fcd7b9ea8af")
    
    assert rule1_id in ruleset.rules
    assert rule2_id in ruleset.rules
    
    rule1 = ruleset.rules[rule1_id]
    assert rule1.rule_nm == "Default_rule_1"
    assert len(rule1.conditions) == 1
    assert len(rule1.actions) == 1
    assert rule1.conditions[0].term_name == "ninq"
    assert rule1.actions[0].term_name == "out"
    assert rule1.actions[0].expression == "ninq is 1"
    
    rule2 = ruleset.rules[rule2_id]
    assert rule2.rule_nm == "Default_rule_2"
    assert len(rule2.conditions) == 1
    assert len(rule2.actions) == 0
    
    assert "ninq" in ruleset.all_term_names
    assert "out" in ruleset.all_term_names
    
    print("[OK] test_group_rows_by_ruleset passed")


def test_generate_signature_from_terms():
    term_names = {"ninq", "out", "is_valid"}
    term_datatypes = {
        "ninq": "decimal",
        "out": "string",
        "is_valid": "boolean",
    }
    
    signature = generate_signature_from_terms(term_names, term_datatypes, default_length=100)
    
    assert len(signature) == 3
    
    term_dict = {t.name: t for t in signature}
    
    assert "ninq" in term_dict
    assert term_dict["ninq"].dataType.value == "decimal"
    assert term_dict["ninq"].length == 100
    
    assert "out" in term_dict
    assert term_dict["out"].dataType.value == "string"
    assert term_dict["out"].length == 100
    
    assert "is_valid" in term_dict
    assert term_dict["is_valid"].dataType.value == "boolean"
    assert term_dict["is_valid"].length is None
    
    print("[OK] test_generate_signature_from_terms passed")


def test_process_csv_import():
    result = process_csv_import(SAMPLE_CSV)
    
    assert result.global_error is None, f"Global error: {result.global_error}"
    assert len(result.accepted_rows) == 3
    assert len(result.rejected_rows) == 0
    assert len(result.parsed_rulesets) == 1
    
    print("[OK] test_process_csv_import passed")


def test_generate_csv_outputs():
    result = process_csv_import(SAMPLE_CSV)
    
    accept_csv = generate_accept_csv(result.accepted_rows)
    assert "ruleset_id" in accept_csv
    assert "hmeq_ninq" in accept_csv
    assert "Default_rule_1" in accept_csv
    
    print(f"[OK] test_generate_csv_outputs passed, accept_csv:\n{accept_csv}")
    
    invalid_csv = """ruleset_id,ruleset_nm,ruleset_desc,rule_id,rule_nm,rule_desc,rule_seq_no,conditional,datatype,lhs_term,expression,expression_type,expression_order
invalid-uuid,hmeq_ninq,,invalid-rule,Default_rule_1,,1,if,decimal,ninq,1,CONDITION,1
"""
    result2 = process_csv_import(invalid_csv)
    assert len(result2.rejected_rows) == 1
    
    reject_csv = generate_reject_csv(result2.rejected_rows)
    assert "errors" in reject_csv
    assert "invalid" in reject_csv.lower()
    
    print(f"[OK] test_generate_csv_outputs with reject_csv passed:\n{reject_csv}")


def test_invalid_csv():
    missing_columns_csv = """ruleset_id,ruleset_nm
fc96e3b2-0003-4ebb-bf3b-5409a2183da6,hmeq_ninq
"""
    result = process_csv_import(missing_columns_csv)
    assert result.global_error is not None
    assert "Missing" in result.global_error or "columns" in result.global_error.lower()
    print(f"[OK] test_invalid_csv passed, global_error: {result.global_error}")


def test_empty_csv():
    empty_csv = """ruleset_id,ruleset_nm,ruleset_desc,rule_id,rule_nm,rule_desc,rule_seq_no,conditional,datatype,lhs_term,expression,expression_type,expression_order
"""
    result = process_csv_import(empty_csv)
    assert result.global_error is not None
    print(f"[OK] test_empty_csv passed, global_error: {result.global_error}")


def test_uuid_preserved_in_parsed_ruleset():
    result = process_csv_import(SAMPLE_CSV)
    assert result.global_error is None
    
    expected_ruleset_id = uuid.UUID("fc96e3b2-0003-4ebb-bf3b-5409a2183da6")
    expected_rule1_id = uuid.UUID("8eccd5bb-a1f5-4084-8669-e80dd594b881")
    expected_rule2_id = uuid.UUID("15780b99-88ae-4076-8bd5-0fcd7b9ea8af")
    
    assert expected_ruleset_id in result.parsed_rulesets
    
    parsed_ruleset = result.parsed_rulesets[expected_ruleset_id]
    assert parsed_ruleset.ruleset_id == expected_ruleset_id
    
    assert expected_rule1_id in parsed_ruleset.rules
    assert expected_rule2_id in parsed_ruleset.rules
    
    rule1 = parsed_ruleset.rules[expected_rule1_id]
    assert rule1.rule_id == expected_rule1_id
    
    rule2 = parsed_ruleset.rules[expected_rule2_id]
    assert rule2.rule_id == expected_rule2_id
    
    print("[OK] test_uuid_preserved_in_parsed_ruleset passed")


def test_parsed_ruleset_to_db_format_includes_id():
    from app.api.v1.batch_import import parsed_ruleset_to_db_format
    
    result = process_csv_import(SAMPLE_CSV)
    assert result.global_error is None
    
    expected_ruleset_id = uuid.UUID("fc96e3b2-0003-4ebb-bf3b-5409a2183da6")
    expected_rule1_id = uuid.UUID("8eccd5bb-a1f5-4084-8669-e80dd594b881")
    expected_rule2_id = uuid.UUID("15780b99-88ae-4076-8bd5-0fcd7b9ea8af")
    
    parsed_ruleset = result.parsed_rulesets[expected_ruleset_id]
    ruleset_data, rules_data, signature = parsed_ruleset_to_db_format(parsed_ruleset)
    
    assert "id" in ruleset_data
    assert ruleset_data["id"] == expected_ruleset_id
    
    assert len(rules_data) == 2
    
    rule_ids = {rule["id"] for rule in rules_data}
    assert expected_rule1_id in rule_ids
    assert expected_rule2_id in rule_ids
    
    print("[OK] test_parsed_ruleset_to_db_format_includes_id passed")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8')
    print("Starting batch import service tests...\n")
    
    test_unescape_csv_expression()
    test_parse_csv_content()
    test_validate_row()
    test_validate_all_rows()
    test_group_rows_by_ruleset()
    test_generate_signature_from_terms()
    test_process_csv_import()
    test_generate_csv_outputs()
    test_invalid_csv()
    test_empty_csv()
    test_uuid_preserved_in_parsed_ruleset()
    test_parsed_ruleset_to_db_format_includes_id()
    
    print("\n[OK] All tests passed!")
