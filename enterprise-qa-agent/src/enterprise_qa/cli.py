"""Reproducible CLI. No implicit credential loading or live-to-mock fallback."""
import argparse
import json
import sys
import tempfile
from pathlib import Path

from .agent import Agent
from .backends import LiveBackend, MockBackend
from .documents import DocumentStore

ROOT = Path(__file__).resolve().parents[2]


def save_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                         prefix='.' + path.name + '.', suffix='.tmp', delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
        temporary.replace(path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def main(argv=None):
    parser = argparse.ArgumentParser(description='企业知识问答 Agent：仅使用合成文档')
    parser.add_argument('--backend', choices=['mock', 'live'], default='mock', help='mock 只验证流程；live 连接真实模型')
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--question', help='单轮问题')
    source.add_argument('--input', type=Path, help='包含 question 与可选 history 的 JSON 文件')
    parser.add_argument('--data', type=Path, default=ROOT / 'data/documents.json')
    parser.add_argument('--output', type=Path, default=ROOT / 'runs/latest.json')
    parser.add_argument('--max-steps', type=int, default=10)
    parser.add_argument('--fail-tool', choices=['search_documents', 'read_document'])
    parser.add_argument('--failure-count', type=int, default=1)
    parser.add_argument('--timeout', type=float, default=45, help='每次真实模型 HTTP 请求超时秒数，最多120')
    args = parser.parse_args(argv)
    try:
        if args.failure_count < 0:
            raise ValueError('failure-count 不得小于零')
        request = json.loads(args.input.read_text(encoding='utf-8')) if args.input else {'question': args.question}
        store = DocumentStore(args.data)
        backend = LiveBackend(timeout=args.timeout) if args.backend == 'live' else MockBackend()
        fail_tools = {args.fail_tool: args.failure_count} if args.fail_tool else {}
        result = Agent(backend, store, args.max_steps, fail_tools).run(request)
        save_json(args.output, result)
    except (ValueError, OSError) as exc:
        print('输入、配置或文件错误：' + str(exc), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result['status'] in ('tool_error', 'incomplete') else 0
