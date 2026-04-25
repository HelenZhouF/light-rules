import csv
import io

test_csv = (
    "ruleset_id,ruleset_nm,ruleset_desc,rule_id,rule_nm,rule_desc,rule_seq_no,conditional,datatype,lhs_term,expression,expression_type,expression_order\n"
    "fc96e3b2-0003-4ebb-bf3b-5409a2183da6,hmeq_ninq,,8eccd5bb-a1f5-4084-8669-e80dd594b881,Default_rule_1,,1,if,decimal,ninq,1,CONDITION,1\n"
    'fc96e3b2-0003-4ebb-bf3b-5409a2183da6,hmeq_ninq,,8eccd5bb-a1f5-4084-8669-e80dd594b881,Default_rule_1,,1,if,string,out,"\'ninq is 1\'",ACTION,1\n'
    "fc96e3b2-0003-4ebb-bf3b-5409a2183da6,hmeq_ninq,,15780b99-88ae-4076-8bd5-0fcd7b9ea8af,Default_rule_2,,2,if,decimal,ninq,0,CONDITION,1\n"
)

print("Test CSV:")
print(repr(test_csv))
print()

reader = csv.DictReader(io.StringIO(test_csv))
for i, row in enumerate(reader):
    print(f"Row {i+1}:")
    for key, value in row.items():
        print(f"  {key} = {repr(value)}")
    print()

print("\n=== Testing single quote escaping ===")

test_cases = [
    '"\'ninq is 1\'"',
    "'''ninq is 1'''",
    "'\\''ninq is 1'\\''",
]

for tc in test_cases:
    print(f"\nInput: {repr(tc)}")
    try:
        reader = csv.reader(io.StringIO(f"col1\n{tc}"))
        for row in reader:
            if row:
                print(f"  Parsed: {repr(row[0])}")
    except Exception as e:
        print(f"  Error: {e}")
