# 企业知识问答 Agent

帮助员工查询合成制度和产品资料，输出可核对的原文引用；制度冲突时先查证并请求确认，资料不足或工具失败时明确说明。

**当前验证状态：代码、测试和离线流程示例已运行；尚未运行真实模型。仓库中的 Mock Trace 不代表真实模型决策效果，不能单凭本包声称已满足真实模型 ReAct 验收。** 真实接口入口已实现，使用者需要自行配置模型、实际运行并审阅结果。

## 评审入口

1. [需求与成功标准](docs/01-requirements.md)
2. [调用流程与设计取舍](docs/02-solution.md)
3. [实际评估与限制](docs/03-evaluation.md)
4. [离线评估汇总](examples/mock/report.md)，以及其中链接的每次实际输入、输出、Trace
5. [AI 使用说明](docs/04-ai-usage.md)、[复盘](docs/05-retrospective.md)

## 环境与运行

- Python >=3.9；本版本实际验证环境为 Python 3.9.6。
- 仅使用标准库，不需要安装第三方包、数据库或 Agent 框架。
- 从解压后的项目根目录执行命令；`requirements.txt` 已说明无第三方依赖。

```bash
python3 --version
python3 run.py --backend mock --question '报销期限多久？'
```

结果在终端以 JSON 输出，并保存到 `runs/latest.json`。`backend: mock` 和 `evidence_level: offline_flow_only` 会明确标记离线模式。`runs/` 为本地结果目录，已加入 Git 忽略规则。

批量运行并验证全部场景：

```bash
python3 scripts/evaluate.py --backend mock
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Windows PowerShell 可用以下测试命令：

```powershell
$env:PYTHONPATH = 'src'
python -m unittest discover -s tests -v
```

## 真实模型运行

需要一个支持 Chat Completions function tools 的模型接口；不强制使用某一厂商。配置 API 基地址、模型名和密钥，且不要提交实际密钥。程序**不自动读取 `.env` 文件**，`.env.example` 仅说明变量。设置环境变量后运行：

```bash
export LLM_BASE_URL='https://你的模型服务地址/v1'
export LLM_MODEL='你的工具调用模型名'
export LLM_API_KEY='在本机填写实际密钥'

python3 run.py --backend live \
  --input examples/inputs/normal.json \
  --output examples/live/normal.json

python3 run.py --backend live \
  --input examples/inputs/conflict.json --data data/conflict.json \
  --output examples/live/conflict.json

python3 scripts/evaluate.py --backend live
```

`LLM_BASE_URL` 应是 API 基地址，不能再包含 `/chat/completions`。例如基地址为 `https://某服务/v1` 时，程序请求 `https://某服务/v1/chat/completions`。外部接口要求 HTTPS，本地 `localhost` / `127.0.0.1` 模型允许 HTTP、可不设密钥。

模型需要支持 `tools`、`tool_choice=required`、单步一个 function call；本版本还发送 `parallel_tool_calls=false` 和严格工具 schema。不同兼容服务的支持程度可能不同，本项目没有验证所有厂商。接口错误会返回 `tool_error`，**不会自动切换到 Mock**。默认单次模型请求超时 45 秒，可用 `--timeout` 调整到最多 120 秒；没有后台无限重试。

真实模式会将问题、给定对话历史和本次读取的合成文档发送到你配置的模型服务。请只使用合成资料。程序只使用 `search_documents`、`read_document` 两个只读业务工具；`finish` 是结果提交协议，不执行企业写入或发布。

真实批量运行会产生 `examples/live/report.json`、`report.md` 及各场景完整 JSON。运行后必须人工复核引用与回答相关性、两条动态路径、失败后的实际动作，并在评估文档中如实补充模型名、结果和限制；不要把离线报告复制为真实报告。

## 场景复现

```bash
# 冲突：30天和15天并存，版本日期不能代替适用优先级
python3 run.py --backend mock --input examples/inputs/conflict.json \
  --data data/conflict.json --output runs/conflict.json

# 上下文追问
python3 run.py --backend mock --input examples/inputs/followup.json \
  --output runs/followup.json

# 首次读取失败，下一步由后端决定是否重试
python3 run.py --backend mock --question '报销期限多久？' \
  --fail-tool read_document --failure-count 1 --output runs/recovery.json

# 持续失败：返回 tool_error，进程退出码为1
python3 run.py --backend mock --question '报销期限多久？' \
  --fail-tool read_document --failure-count 99 --output runs/failure.json

# 执行上限：返回 incomplete，进程退出码为1
python3 run.py --backend mock --question '报销期限多久？' \
  --max-steps 1 --output runs/limit.json

# 替换制度内容：45天应替代原来30天
python3 run.py --backend mock --question '报销期限多久？' \
  --data data/changed.json --output runs/changed.json
```

`--fail-tool` 和 `--failure-count` 是可复现的故障注入配置，不是写死的决策日志。执行器只返回错误，后端必须观察后自行选择下一步；Mock 的选择来自明确的测试规则，Live 的选择来自下一次真实模型响应。

## 输入与输出

输入 JSON：

```json
{
  "question": "那最晚多久提交？",
  "history": [
    {"role": "user", "content": "我想了解员工报销规定。"},
    {"role": "assistant", "content": "你想了解哪一部分？"}
  ]
}
```

历史仅用于消解指代，不是证据。历史角色只允许 `user` 和 `assistant`；本次仍需检索并读取原文。

输出字段：

| 字段 | 说明 |
|---|---|
| `status` | answered / needs_clarification / no_answer / tool_error / incomplete |
| `answer` | 正常回答采用引用原文抽取式展示，避免生成额外制度事实 |
| `citations` | 文档 ID、片段 ID、逐字完整原文片段、版本日期、标题 |
| `gaps` | 资料缺口或未完成原因 |
| `clarification_question` | 需用户确认的问题 |
| `trace` | 实际步骤、动作参数、工具观察、公开依据、后续动作 |
| `backend` / `model` | 本次后端及模型标识 |
| `dataset_sha256` | 本次读取的资料文件摘要，可区分替换资料实验 |
| `steps` / `max_steps` | 已执行步数及上限 |

退出码：`0` 表示完成业务处理（包括明确追问与资料外拒答），`1` 表示工具失败或步数耗尽，`2` 表示输入、配置或文件错误。**退出码 0 不等于回答成功，业务结果必须看 `status`。**

## 目录

```text
README.md
run.py
requirements.txt
.env.example
src/enterprise_qa/
  agent.py           # 有界观察循环、原文引用和冲突检查
  backends.py        # 真实 HTTP 模型适配及明确标注的规则 Mock
  documents.py       # 合成资料校验、检索、片段读取
  protocol.py        # 工具 schema、动作参数校验
  cli.py             # 命令行与原子保存结果
tests/               # 核心行为、CLI、模型协议测试
data/                # 正常、冲突、内容替换实验的合成资料
examples/inputs/     # 实际运行输入
examples/cases.json  # 场景配置与预期
examples/mock/       # 已执行的离线结果、Trace 和测试日志
scripts/evaluate.py  # 一键运行并生成实际评估报告
docs/01-05           # 需求、方案、评估、AI 使用、复盘
SUBMISSION.md        # 提交前核对与 GitHub 提交步骤
```

## 主要限制

中文双字词检索并非语义检索；未命中的同义表达可能需要模型改写，仍无法保证全召回。抽取式引用保证完整片段的文本来源，但不自动证明选择的片段回答了用户的全部问题。结构化事实标注辅助冲突检查，不能代替通用自然语言矛盾识别；跨不同 scope 的适用冲突、隐含优先级以及标注错误仍需模型或人工确认。完整限制和实际失败修复见评估文档。

接口协议参考 [OpenAI 官方 Function calling 文档](https://developers.openai.com/api/docs/guides/function-calling)。项目直接通过标准库 HTTP 使用工具调用协议，没有引入 Agent 框架。
