import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CliTests(unittest.TestCase):
    def run_cli(self, *arguments):
        env = dict(os.environ, PYTHONPATH=str(ROOT / 'src'), LLM_API_KEY='', LLM_BASE_URL='', LLM_MODEL='')
        return subprocess.run([sys.executable, '-m', 'enterprise_qa', *arguments], cwd=ROOT,
                              env=env, capture_output=True, text=True, timeout=15)

    def test_json_output_and_saved_file_agree(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'run.json'
            process = self.run_cli('--backend', 'mock', '--question', '报销期限多久？', '--output', str(output))
            self.assertEqual(process.returncode, 0, process.stderr)
            result = json.loads(process.stdout)
            self.assertEqual(result, json.loads(output.read_text(encoding='utf-8')))
            self.assertEqual(result['status'], 'answered')

    def test_persistent_failure_exits_one_and_saves_result(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'run.json'
            process = self.run_cli('--question', '报销期限', '--fail-tool', 'read_document',
                                   '--failure-count', '99', '--output', str(output))
            self.assertEqual(process.returncode, 1)
            self.assertEqual(json.loads(output.read_text())['status'], 'tool_error')

    def test_missing_live_configuration_exits_two(self):
        process = self.run_cli('--backend', 'live', '--question', '报销期限')
        self.assertEqual(process.returncode, 2)
        self.assertNotIn('Traceback', process.stderr)

    def test_invalid_json_exits_two(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'bad.json'
            path.write_text('{', encoding='utf-8')
            process = self.run_cli('--input', str(path))
            self.assertEqual(process.returncode, 2)
            self.assertNotIn('Traceback', process.stderr)


if __name__ == '__main__':
    unittest.main()
