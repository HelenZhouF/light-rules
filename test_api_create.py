import sys
import uuid
import asyncio
sys.path.insert(0, 'c:\\workspace\\ai\\light-rules')

from sqlalchemy import text
from app.core.database import engine

async def get_ruleset_id():
    async with engine.begin() as conn:
        result = await conn.execute(text("SELECT id, name FROM rulesets WHERE name = 'rs2_with_sig'"))
        row = result.fetchone()
        if row:
            return row[0]
    return None

async def test_create_rule():
    ruleset_id = await get_ruleset_id()
    if not ruleset_id:
        print("Error: Could not find rs2_with_sig ruleset")
        return
    
    # 转换为标准 UUID 格式（如果需要）
    try:
        # 尝试解析为 UUID
        if len(ruleset_id) == 32:
            # 没有连字符的格式
            ruleset_uuid = uuid.UUID(ruleset_id)
        else:
            ruleset_uuid = uuid.UUID(ruleset_id)
        print(f"Using ruleset ID: {ruleset_uuid}")
    except Exception as e:
        print(f"Error parsing ruleset ID: {e}")
        return

    # 测试 payload
    payload = {
        "name": "r3_test",
        "description": "r3 desc",
        "conditional": "decisionTable",
        "order_index": 10,
        "conditions": [
            {
                "term": {
                    "name": "vehicleCost"
                },
                "expression": "> 10",
                "type": "expression"
            }
        ],
        "actions": [
            {
                "term": {
                    "name": "model"
                },
                "expression": "SUB",
                "type": "assignment"
            }
        ]
    }

    print(f"Payload: {payload}")
    
    # 尝试直接调用 API 层的代码，不通过 HTTP
    from fastapi import Depends
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.core.database import get_async_session
    from app.schemas.rule import RuleCreate
    from app.crud import get_ruleset_by_id
    from app.crud.rule import create_rule, get_rule_by_name_and_ruleset, get_rule_by_order_index_and_ruleset
    
    try:
        # 解析 payload
        rule_in = RuleCreate(**payload)
        print(f"Parsed RuleCreate: {rule_in.model_dump()}")
        
        # 创建数据库会话
        from app.core.database import async_session_maker
        
        async with async_session_maker() as db:
            # 检查 ruleset
            ruleset = await get_ruleset_by_id(db, ruleset_id=ruleset_uuid)
            if ruleset is None:
                print("Error: RuleSet not found")
                return
            
            print(f"Found ruleset: {ruleset.name}")
            print(f"Ruleset signature: {ruleset.signature}")
            
            # 验证 term
            from app.schemas.rule import get_valid_term_names, validate_terms
            valid_term_names = get_valid_term_names(ruleset.signature)
            print(f"Valid term names: {valid_term_names}")
            
            validation_errors = validate_terms(rule_in.conditions, rule_in.actions, valid_term_names)
            if validation_errors:
                print(f"Validation errors: {validation_errors}")
                return
            
            print("Validation passed!")
            
            # 检查是否存在同名 rule
            existing_rule_by_name = await get_rule_by_name_and_ruleset(
                db, name=rule_in.name, rule_set_id=ruleset_uuid
            )
            if existing_rule_by_name:
                print(f"Error: Rule with name '{rule_in.name}' already exists")
                return
            
            # 检查 order_index
            existing_rule_by_order = await get_rule_by_order_index_and_ruleset(
                db, order_index=rule_in.order_index, rule_set_id=ruleset_uuid
            )
            if existing_rule_by_order:
                print(f"Error: Rule with order_index {rule_in.order_index} already exists")
                return
            
            # 创建 rule
            rule = await create_rule(db=db, rule_in=rule_in, rule_set_id=ruleset_uuid)
            print(f"Rule created successfully!")
            print(f"Rule ID: {rule.id}")
            print(f"Rule conditions: {rule.conditions}")
            print(f"Rule actions: {rule.actions}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_create_rule())
