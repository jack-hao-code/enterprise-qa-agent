"""Run actual executions and persist expectations, observations and full traces."""
import argparse
import json
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from enterprise_qa.agent import Agent
from enterprise_qa.backends import LiveBackend, MockBackend
from enterprise_qa.cli import save_json
from enterprise_qa.documents import DocumentStore


def check_case(case, result):
    errors = []
    if result['status'] != case['expected_status']:
        errors.append('status: expected ' + case['expected_status'] + ', actual ' + result['status'])
    for value in case.get('answer_contains', []):
        if value not in result['answer']:
            errors.append('answer missing: ' + value)
    for value in case.get('answer_excludes', []):
        if value in result['answer']:
            errors.append('answer unexpectedly contains: ' + value)
    expected_ids = set(case.get('citation_ids', []))
    if {c['document_id'] for c in result['citations']} != expected_ids:
        errors.append('citation document IDs differ from expectation')
    for action, key in [('read_document', 'min_reads'), ('search_documents', 'min_searches')]:
        if sum(t['action'] == action for t in result['trace']) < case.get(key, 0):
            errors.append('insufficient ' + action + ' observations')
    if case.get('must_observe_error') and not any(not t['observation'].get('ok') for t in result['trace']):
        errors.append('injected tool failure was not observed')
    if result['status'] == 'needs_clarification' and not result['clarification_question']:
        errors.append('missing clarification question')
    if result['status'] != 'answered' and not result['gaps']:
        errors.append('missing gap/failure explanation')
    if len(result['trace']) > result['max_steps']:
        errors.append('step limit violated')
    return errors


def main(argv=None):
    parser = argparse.ArgumentParser(description='批量评估；mock 与 live 分目录保存，绝不伪装真实模型运行')
    parser.add_argument('--backend', choices=['mock', 'live'], default='mock')
    parser.add_argument('--output-dir', type=Path)
    parser.add_argument('--timeout', type=float, default=45)
    args = parser.parse_args(argv)
    output = args.output_dir or ROOT / 'examples' / args.backend
    cases = json.loads((ROOT / 'examples/cases.json').read_text(encoding='utf-8'))
    try:
        backend = LiveBackend(timeout=args.timeout) if args.backend == 'live' else MockBackend()
    except ValueError as exc:
        print('模型配置错误：' + str(exc), file=sys.stderr)
        return 2
    started = time.monotonic()
    records = []
    for case in cases:
        request = json.loads((ROOT / 'examples/inputs' / (case['input'] + '.json')).read_text(encoding='utf-8'))
        store = DocumentStore(ROOT / 'data' / (case['data'] + '.json'))
        result = Agent(backend, store, case.get('max_steps', 10), case.get('fail_tools')).run(request)
        save_json(output / (case['id'] + '.json'), result)
        errors = check_case(case, result)
        records.append({'case_id': case['id'], 'passed': not errors, 'expected_status': case['expected_status'],
                        'actual_status': result['status'], 'errors': errors, 'steps': result['steps'],
                        'result_file': case['id'] + '.json',
                        'actions': [t['action'] for t in result['trace']]})
    passed = sum(record['passed'] for record in records)
    report = {'generated_at': datetime.now(timezone.utc).isoformat(), 'python': platform.python_version(),
              'backend': backend.mode, 'model': backend.model,
              'evidence_level': 'offline_flow_only' if args.backend == 'mock' else 'live_model_execution',
              'note': '通过表示满足本脚本的断言，不能证明所有问题均正确；mock 不验证真实模型决策。',
              'duration_seconds': round(time.monotonic() - started, 6),
              'passed': passed, 'total': len(cases), 'cases': records}
    save_json(output / 'report.json', report)
    lines = ['# 实际批量运行结果', '',
             '- backend: ' + backend.mode, '- model: ' + backend.model,
             '- evidence_level: ' + report['evidence_level'],
             '- Python: ' + report['python'], '- 通过: ' + str(passed) + '/' + str(len(cases)),
             '- 真实模型效果：' + ('本报告未验证' if args.backend == 'mock' else '仅限本次模型与本组用例'), '',
             '| 场景 | 预期 | 实际 | 检查 | 实际动作 |', '|---|---|---|---|---|']
    for record in records:
        lines.append('| [' + record['case_id'] + '](' + record['result_file'] + ') | ' + record['expected_status']
                     + ' | ' + record['actual_status'] + ' | ' + ('PASS' if record['passed'] else 'FAIL')
                     + ' | ' + ' → '.join(record['actions']) + ' |')
    output.mkdir(parents=True, exist_ok=True)
    (output / 'report.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(json.dumps({'backend': args.backend, 'passed': passed, 'total': len(cases),
                      'report': str(output / 'report.json')}, ensure_ascii=False))
    return 0 if passed == len(cases) else 1


if __name__ == '__main__':
    raise SystemExit(main())
