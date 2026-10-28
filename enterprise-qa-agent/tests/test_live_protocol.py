"""Transport-double tests verify serialization/parser, NOT a real model."""
import io
import json
import unittest
import urllib.error
from unittest.mock import patch

from enterprise_qa.backends import LiveBackend


class Transport:
    def __init__(self, result):
        self.result = result
        self.request = None

    def open(self, request, timeout):
        self.request, self.timeout = request, timeout
        return io.BytesIO(json.dumps(self.result).encode('utf-8'))


def response(calls=None):
    return {'choices': [{'message': {'tool_calls': calls if calls is not None else [{
        'id': 'provider_call_1', 'type': 'function', 'function': {
            'name': 'search_documents', 'arguments': json.dumps({'query': '报销', 'limit': 10, 'reason': '定位制度'}),
        },
    }]}}]}


class LiveProtocolTests(unittest.TestCase):
    def backend(self):
        return LiveBackend('https://model.example.invalid/v1', 'test-not-a-real-key', 'test-model')

    def test_request_and_tool_response_serialization(self):
        transport = Transport(response())
        with patch('enterprise_qa.backends.urllib.request.build_opener', return_value=transport):
            action = self.backend().decide([{'role': 'user', 'content': '报销'}])
        payload = json.loads(transport.request.data)
        self.assertEqual(transport.request.full_url, 'https://model.example.invalid/v1/chat/completions')
        self.assertEqual(payload['tool_choice'], 'required')
        self.assertFalse(payload['parallel_tool_calls'])
        self.assertEqual({item['function']['name'] for item in payload['tools']}, {'search_documents', 'read_document', 'finish'})
        self.assertEqual(action.name, 'search_documents')
        self.assertEqual(action.arguments['query'], '报销')
        self.assertEqual(action.call_id, 'provider_call_1')

    def test_missing_or_parallel_calls_are_rejected(self):
        single = response()['choices'][0]['message']['tool_calls']
        for calls in ([], single + single):
            with patch('enterprise_qa.backends.urllib.request.build_opener', return_value=Transport(response(calls))):
                with self.assertRaises(RuntimeError):
                    self.backend().decide([])

    def test_http_error_does_not_expose_provider_body(self):
        error = urllib.error.HTTPError('https://model.example.invalid', 401, 'bad', {}, io.BytesIO(b'secret-token'))
        with patch('enterprise_qa.backends.urllib.request.build_opener') as create:
            create.return_value.open.side_effect = error
            with self.assertRaises(RuntimeError) as caught:
                self.backend().decide([])
        self.assertIn('401', str(caught.exception))
        self.assertNotIn('secret-token', str(caught.exception))

    def test_external_plain_http_is_rejected(self):
        with self.assertRaises(ValueError):
            LiveBackend('http://model.example.invalid/v1', 'fake', 'test')

    def test_local_model_can_use_http_without_api_key(self):
        self.assertEqual(LiveBackend('http://localhost:11434/v1', '', 'local-model').model, 'local-model')


if __name__ == '__main__':
    unittest.main()
