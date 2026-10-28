"""Live HTTP tool calling and an explicitly non-LLM offline demonstration."""
import json
import os
import re
import socket
import urllib.error
import urllib.parse
import urllib.request

from .protocol import Action, TOOLS


class LiveBackend:
    mode = 'live'

    def __init__(self, base_url=None, api_key=None, model=None, timeout=45):
        self.base_url = (base_url or os.environ.get('LLM_BASE_URL', '')).rstrip('/')
        self.api_key = api_key if api_key is not None else os.environ.get('LLM_API_KEY', '')
        self.model = model or os.environ.get('LLM_MODEL', '')
        self.timeout = timeout
        parts = urllib.parse.urlsplit(self.base_url)
        loopback = parts.hostname in ('localhost', '127.0.0.1', '::1')
        if (parts.scheme not in ('http', 'https') or not parts.hostname or parts.username
                or parts.password or parts.query or parts.fragment):
            raise ValueError('LLM_BASE_URL 必须是无凭据、查询参数的 HTTP(S) API 基地址')
        if parts.scheme != 'https' and not loopback:
            raise ValueError('外部模型接口必须使用 HTTPS')
        if not self.model:
            raise ValueError('真实模式需要 LLM_MODEL')
        if not loopback and not self.api_key:
            raise ValueError('外部真实模式需要 LLM_API_KEY')
        if not isinstance(timeout, (float, int)) or not 0 < timeout <= 120:
            raise ValueError('模型超时必须在 0-120 秒之间')

    def decide(self, messages):
        payload = {'model': self.model, 'messages': messages, 'tools': TOOLS,
                   'tool_choice': 'required', 'parallel_tool_calls': False}
        headers = {'Content-Type': 'application/json'}
        if self.api_key:
            headers['Authorization'] = 'Bearer ' + self.api_key
        request = urllib.request.Request(self.base_url + '/chat/completions',
                                         data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
                                         headers=headers, method='POST')

        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, hdrs, newurl):
                return None

        try:
            with urllib.request.build_opener(NoRedirect()).open(request, timeout=self.timeout) as response:
                raw = response.read(2_000_001)
                if len(raw) > 2_000_000:
                    raise RuntimeError('模型返回超过 2MB 上限')
                result = json.loads(raw)
        except urllib.error.HTTPError as exc:
            # Do not echo body, request headers or credential-bearing provider errors.
            raise RuntimeError('模型 HTTP 错误，状态码 ' + str(exc.code)) from None
        except (urllib.error.URLError, socket.timeout, TimeoutError):
            raise RuntimeError('模型连接失败或超时') from None
        except (UnicodeError, json.JSONDecodeError):
            raise RuntimeError('模型返回不是有效 JSON') from None
        try:
            message = result['choices'][0]['message']
            calls = message.get('tool_calls', [])
            if len(calls) != 1:
                raise ValueError('每步必须返回恰好一个工具调用')
            call = calls[0]
            if call.get('type') != 'function' or not isinstance(call.get('id'), str) or not call['id']:
                raise ValueError('工具调用缺少有效 id/type')
            arguments = json.loads(call['function']['arguments'])
            return Action(call['function']['name'], arguments, call['id'])
        except (KeyError, IndexError, TypeError, AttributeError, ValueError):
            raise RuntimeError('模型工具调用协议无效：需要一个 function call 及 JSON 参数') from None


class MockBackend:
    """Rule-based test double. Its paths are NOT evidence of LLM reasoning."""
    mode = 'mock'
    model = 'offline-rule-mock-v1'

    def decide(self, messages):
        request = json.loads(messages[1]['content'])
        question = request['question']
        history = ' '.join(turn['content'] for turn in request.get('history', []))
        events = []
        calls = {}
        for message in messages:
            if message['role'] == 'assistant':
                for call in message.get('tool_calls', []):
                    calls[call['id']] = call['function']
            elif message['role'] == 'tool':
                call = calls[message['tool_call_id']]
                events.append((call['name'], json.loads(call['arguments']), json.loads(message['content'])))

        def act(name, reason, **kwargs):
            return Action(name, dict(kwargs, reason=reason))

        def done(status, answer, citations=None, gaps=None, clarification_question=''):
            return act('finish', '根据已观察到的原文或资料缺口提交结果', status=status,
                       answer=answer, citations=citations or [], gaps=gaps or [],
                       clarification_question=clarification_question)

        if not events:
            if '垫付' in question or '交单据' in question:
                query = '垫付 交单据'
            elif re.search(r'那|这个|上述', question) and history:
                # Offline fixture resolver: explicit topic extraction, not LLM inference.
                query = '报销 期限' if '报销' in history and re.search(r'最晚|多久|提交', question) else history + ' ' + question
            else:
                query = question
            return act('search_documents', '先定位问题对应的制度候选', query=query, limit=10)

        last_name, last_args, last_result = events[-1]
        if not last_result.get('ok'):
            failures = sum(name == last_name and not result.get('ok') for name, _, result in events)
            if last_result.get('error', {}).get('retryable') and failures < 2:
                retry_args = {key: value for key, value in last_args.items() if key != 'reason'}
                return act(last_name, '观察到暂时性工具错误，再尝试一次且保留此前成功结果', **retry_args)
            return done('tool_error', '工具未能完成，无法可靠回答。', gaps=['资料读取或检索失败，需恢复工具后重试。'])

        searches = [result for name, _, result in events if name == 'search_documents' and result.get('ok')]
        if not any(result['hits'] for result in searches):
            if len(searches) < 2:
                context = question + ' ' + history
                rewrite = '报销 期限' if any(word in context for word in ('垫付', '单据', '报销')) else context.replace('是什么', '').replace('？', ' ').strip()
                return act('search_documents', '首轮检索无结果，换一种表述补查', query=rewrite, limit=10)
            return done('no_answer', '当前资料中未找到支持此问题的制度或产品依据。', gaps=['需要补充相关制度或产品文档。'])

        candidates = list(dict.fromkeys(hit['document_id'] for result in searches for hit in result['hits']))
        read_docs = {result['document']['id']: result['document'] for name, _, result in events
                     if name == 'read_document' and result.get('ok')}
        for document_id in candidates:
            if document_id not in read_docs:
                return act('read_document', '读取候选原文以核对事实及潜在冲突', document_id=document_id)

        citations = []
        values = {}
        for doc in read_docs.values():
            for chunk in doc['chunks']:
                citations.append({'document_id': doc['id'], 'chunk_id': chunk['id'], 'quote': chunk['text']})
                if chunk.get('claim_key'):
                    values.setdefault((chunk['claim_key'], chunk.get('scope', '未知')), set()).add(chunk['claim_value'])
        if any(len(group) > 1 for group in values.values()):
            return done('needs_clarification', '已读取制度存在冲突，不能直接确定适用答案。', citations,
                        ['同一事项出现不同规定，资料未明确适用优先级。'], '请确认适用哪份制度，或提供明确的适用范围和优先级。')
        return done('answered', '根据原文回答。', citations)
