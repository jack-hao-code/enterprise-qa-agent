# 效果验证、失败与限制

## 当前结论及证据边界

本版本已实际运行单元/集成测试和10组离线场景。全部离线场景通过检查，报告和每组输入、输出、Trace 位于 [examples/mock/](../examples/mock/report.md)。这些证据只覆盖控制流、工具、运行时限制和规则 Mock，**不证明真实模型决策达到题目要求**。

`tests/test_live_protocol.py` 使用传输测试替身检查请求序列化、工具参数解析和异常处理；没有访问真实模型。它不能作为真实模型调用成功的证据。

真实模型没有运行，原因是本交付未配置用户选择的模型服务与凭据。没有填入假的模型效果、费用、响应时间或通过率，也没有使用离线输出冒充模型输出。

## 可复现命令与实际记录

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 scripts/evaluate.py --backend mock
```

测试命令的实际输出见 [test-results.txt](../examples/mock/test-results.txt)。批量运行时间、Python 版本、用例预期、实际状态、错误列表和实际动作见 [report.json](../examples/mock/report.json)。自动测试总数以测试日志为准。

## 六项必验与附加实验

| 场景 | 预期 | 当前离线结果与文件 |
|---|---|---|
| 明确答案 | D01原文支持30天 | answered，[normal.json](../examples/mock/normal.json) |
| 制度冲突 | 读双方、列冲突、追问，不按日期决胜 | needs_clarification，[conflict.json](../examples/mock/conflict.json) |
| 资料外问题 | 补查后缺口明确，无伪造引用 | no_answer，[out_of_scope.json](../examples/mock/out_of_scope.json) |
| 同义改写 | 首轮无结果后改写为报销期限 | answered，[paraphrase.json](../examples/mock/paraphrase.json) |
| 上下文追问 | 依据历史识别报销话题并重新读原文 | answered，[followup.json](../examples/mock/followup.json) |
| 工具持续失败 | 保留失败观察并停止 | tool_error，[tool_failure.json](../examples/mock/tool_failure.json) |
| 工具暂时失败 | 观察失败后再读，成功后引用 | answered，[transient_recovery.json](../examples/mock/transient_recovery.json) |
| 缺少问题 | 追问，不调用模型 | needs_clarification，[missing_question.json](../examples/mock/missing_question.json) |
| 步数限制 | 1步耗尽后不能假报完成 | incomplete，[step_limit.json](../examples/mock/step_limit.json) |
| 修改资料 | 改成45天后引用与答案同步变化 | answered，[changed_source.json](../examples/mock/changed_source.json) |

`cases.json` 的自动断言检查状态、关键文本、文档 ID、必要动作和错误观察，不使用另一个模型自动打分；它不能完全判定语义相关性与答案完整性。

## 开发中发现的实际问题

1. **资料外问题误命中。** 首次检索无结果后，Mock 原先附加“制度、说明”这类泛词，导致火星问题命中报销和产品文档。通过实际 Trace 定位后，改为保留主题的查询归一化；回归测试要求此问题最终 no_answer。未通过时没有改写预期来掩盖失败。
2. **历史中的泛词污染召回。** 将完整历史直接拼成查询时，“员工、规定”等词召回了无关的远程办公资料。Mock 现在对该离线报销追问做明确的话题提取；测试要求只引用 D01。此规则改进仅属于离线替身，不代表通用上下文理解已解决。
3. **冲突引用可能没有展示具体分歧。** 仅检查文档和片段 ID 时，双方都引用“员工”也能通过。新增测试后加强门禁：已检测到的冲突中，每一方引用必须含自己的规定值。
4. **引用截断可能改变含义。** 独立审查复现了把“30天”中的“0天”作为引文的漏洞。现要求 quote 等于完整原文片段，不接受任意子串，保留数值及限定条件。
5. **历史检索截断可能被漏掉。** 只看最新查询的截断标记时，一次无关的空检索会掩盖早先漏读的冲突。现为每条历史查询保留未消除的截断，只有同一查询以更大 limit 返回完整结果才消除；已添加拒绝绕过与正常扩大查询的回归测试。
6. **非回答状态仍可能输出编造正文。** 现对 no_answer、tool_error、incomplete、一般追问的主回答使用运行时状态说明；冲突正文只显示完整原文。测试中模型试图在 no_answer 写入“15天”时，该断言不会成为主回答。
7. **畸形动作名可能造成异常退出。** 模型返回数组作为工具名时，原来会触发未捕获的类型错误。现在先检查工具名为字符串，再查白名单；拒绝动作仍有结构化记录并受步数限制。

## 尚未覆盖或无法保证的部分

- 真实模型补查、冲突查证和失败调整的实际质量尚未验证。
- 关键词检索召回有限，尤其是复杂同义表达、跨语言和长文档。
- 事实标注需人工维护；无标注、错误标注、跨范围隐含冲突不由结构化门禁全面识别。
- 引用逐字匹配不等于语义上足够支持所有结论；抽取式回答也可能选错相关片段，需要人工复核。
- 示例数据很小，未做并发、性能、访问权限、生产日志与隐私合规系统测试。
- 不实现自动制度优先级推断或跨次会话持久记忆；每次都需提供历史并重新核对来源。
- 步数是模型决策次数上限，不是整体墙钟时间上限；Live 总时间还受单次超时和网络影响。

## 提交前真实模型验证

先按 README 配置模型，再运行 `python3 scripts/evaluate.py --backend live`。审阅 `examples/live/report.md` 和每组 JSON，特别核对：模型是否因工具观察而更换动作、是否完整引用冲突双方、是否在资料外问题停止、错误之后是否保留成功记录。失败场景要如实保留；修正后重新运行，不能编辑历史 Trace 来制造通过。

至少保留正常路径与冲突/补查路径两条真实模型记录。随后在本文补充实际模型名、运行时间、通过与失败结果，并更新 AI 使用说明与个人实际用时。
