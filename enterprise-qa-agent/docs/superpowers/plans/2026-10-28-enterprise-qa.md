# 企业知识问答 Agent Implementation Plan

> 执行方式：本会话顺序实现与检查，保持用户已授权的完整交付范围。

**Goal:** 构建第三题的可复现 CLI 项目与诚实的评估包。

**Architecture:** 两个只读业务工具、模型选择动作的有界循环、独立引用与冲突检查。HTTP 后端与离线规则后端共用协议；真实模型不可用明确失败。

**Tech Stack:** Python >=3.9 标准库，unittest，JSON，无第三方运行依赖。

## Global Constraints

- 只使用合成资料；不提交密钥或真实个人数据。
- 至少六项验收全部覆盖；Mock 不代表真实模型决策证据。
- 默认最多 10 次模型决策；超限返回 incomplete。
- 引用必须本次读取、逐字匹配；冲突禁止擅自定结论。

## 执行清单

- [x] 1. 先编写 tests/test_agent.py 的行为测试并运行，确认缺少实现而失败。接口 `DocumentStore(path).search(query, limit)` / `.read(document_id)`；`Agent(backend, store, max_steps=10, fail_tools=None).run(request)` 返回 JSON 可序列化字典。
- [x] 2. 实现 data/*.json、documents.py；运行检索与数据校验测试。所有文档含 id/title/version_date/chunks，各片段含 id/text/claim_key/claim_value/scope。
- [x] 3. 实现 protocol.py、agent.py、backends.py；运行模型脚本注入的循环、引用、冲突、失败与超限测试。HTTP 模式使用 function tools 和 tool_call_id；公开简要依据为 reason 参数。
- [x] 4. 实现 cli.py、__main__.py、scripts/evaluate.py；子进程验证退出码及 JSON 产物。命令 `PYTHONPATH=src python3 -m enterprise_qa --backend mock --question '报销期限多久？'`。
- [x] 5. 生成 examples/mock/* 六项验收和恢复/超限/改资料用例；`PYTHONPATH=src python3 scripts/evaluate.py --backend mock` 检查预期状态、引用、关键数值和动作路径。
- [x] 6. 完成 README、docs/01-05、.env.example、requirements.txt、SUBMISSION.md；说明真实模型尚未运行、个人贡献由用户自行核实。
- [x] 7. 执行 `PYTHONPATH=src python3 -m unittest discover -s tests -v` 与批量评估，记录实际输出；检查归档中无缓存、密钥与 .git。提供 ZIP 与粘贴说明。
