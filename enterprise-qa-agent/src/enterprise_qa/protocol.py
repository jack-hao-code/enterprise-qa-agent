"""Public action contract shared by model, offline double and executor."""
from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class Action:
    name: str
    arguments: Dict[str, Any]
    call_id: str = field(default='')


STATUSES = ['answered', 'needs_clarification', 'no_answer', 'tool_error', 'incomplete']


def obj(properties):
    return {'type': 'object', 'properties': properties,
            'required': list(properties), 'additionalProperties': False}


STRING = {'type': 'string'}
REASON = {'type': 'string', 'description': '公开的简要动作依据，一句话；不要输出内部思维过程。'}
CITATION = obj({'document_id': STRING, 'chunk_id': STRING, 'quote': STRING})
SCHEMAS = {
    'search_documents': obj({'query': STRING, 'limit': {'type': 'integer', 'minimum': 1, 'maximum': 20}, 'reason': REASON}),
    'read_document': obj({'document_id': STRING, 'reason': REASON}),
    'finish': obj({'status': {'type': 'string', 'enum': STATUSES}, 'answer': STRING,
                   'citations': {'type': 'array', 'items': CITATION},
                   'gaps': {'type': 'array', 'items': STRING},
                   'clarification_question': STRING, 'reason': REASON}),
}
TOOLS = [{'type': 'function', 'function': {
    'name': name, 'description': description, 'strict': True, 'parameters': SCHEMAS[name],
}} for name, description in [
    ('search_documents', '检索合成企业资料，返回候选元数据而非完整原文。可改写查询。'),
    ('read_document', '按文档 ID 读取带版本日期的原文片段及人工标注事实。'),
    ('finish', '在原文核对后提交结构化结果；冲突需列出双方引用并追问。'),
]]


def validate_value(value, schema):
    kind = schema['type']
    if kind == 'object':
        if not isinstance(value, dict) or set(value) != set(schema['properties']):
            raise ValueError('字段缺失或存在未声明字段')
        for key, child in schema['properties'].items():
            validate_value(value[key], child)
    elif kind == 'array':
        if not isinstance(value, list) or len(value) > 40:
            raise ValueError('数组无效或过长')
        for item in value:
            validate_value(item, schema['items'])
    elif kind == 'string':
        if not isinstance(value, str) or len(value) > 20000:
            raise ValueError('字符串无效或过长')
        if 'enum' in schema and value not in schema['enum']:
            raise ValueError('状态值无效')
    elif kind == 'integer':
        if type(value) is not int or not schema['minimum'] <= value <= schema['maximum']:
            raise ValueError('整数参数超出允许范围')


def validate_action(action):
    if not isinstance(action, Action) or not isinstance(action.name, str) or action.name not in SCHEMAS:
        raise ValueError('未知动作')
    validate_value(action.arguments, SCHEMAS[action.name])
    reason = action.arguments['reason']
    if not reason.strip() or len(reason) > 300:
        raise ValueError('动作依据需为 1-300 字符的公开摘要')
    for key in ('query', 'document_id'):
        if key in action.arguments and not action.arguments[key].strip():
            raise ValueError(key + ' 不得为空')


def failure(code, message, retryable=False):
    return {'ok': False, 'error': {'code': code, 'message': message, 'retryable': retryable}}
