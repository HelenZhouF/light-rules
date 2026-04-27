from app.services.code_generator import generate_ruleset_function

class MockRule:
    def __init__(self, order_index, conditional, conditions, actions):
        self.id = f"rule-{order_index}"
        self.name = f"Rule {order_index}"
        self.order_index = order_index
        self.conditional = conditional
        self.conditions = conditions
        self.actions = actions
    
    def get(self, key, default=None):
        return getattr(self, key, default)

rule1 = MockRule(
    order_index=0,
    conditional='all',
    conditions=[{
        'term': {'name': 'ning'},
        'expression': '==1',
        'type': 'expression'
    }],
    actions=[{
        'term': {'name': 'out'},
        'expression': "'ning=1'",
        'type': 'assignment'
    }]
)

rule2 = MockRule(
    order_index=1,
    conditional='all',
    conditions=[{
        'term': {'name': 'ning'},
        'expression': '==0',
        'type': 'expression'
    }],
    actions=[]
)

signature = [
    {'name': 'ning', 'dataType': 'decimal', 'direction': 'input'},
    {'name': 'out', 'dataType': 'string', 'direction': 'output'}
]

code = generate_ruleset_function(
    ruleset_name='test_ruleset',
    signature=signature,
    rules=[rule1, rule2],
    lookup_data={}
)

print('生成的代码：')
print(code)
print('---')

try:
    exec(code)
    print('代码编译成功！')
    
    result = execute_test_ruleset({'ning': 1})
    print(f'执行结果(ning=1): {result}')
    
    result2 = execute_test_ruleset({'ning': 0})
    print(f'执行结果(ning=0): {result2}')
    
except Exception as e:
    import traceback
    traceback.print_exc()
    print(f'代码编译失败: {type(e).__name__}: {e}')
