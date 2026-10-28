# 实际批量运行结果

- backend: mock
- model: offline-rule-mock-v1
- evidence_level: offline_flow_only
- Python: 3.9.6
- 通过: 10/10
- 真实模型效果：本报告未验证

| 场景 | 预期 | 实际 | 检查 | 实际动作 |
|---|---|---|---|---|
| [normal](normal.json) | answered | answered | PASS | search_documents → read_document → finish |
| [conflict](conflict.json) | needs_clarification | needs_clarification | PASS | search_documents → read_document → read_document → finish |
| [out_of_scope](out_of_scope.json) | no_answer | no_answer | PASS | search_documents → search_documents → finish |
| [paraphrase](paraphrase.json) | answered | answered | PASS | search_documents → search_documents → read_document → finish |
| [followup](followup.json) | answered | answered | PASS | search_documents → read_document → finish |
| [tool_failure](tool_failure.json) | tool_error | tool_error | PASS | search_documents → read_document → read_document → finish |
| [transient_recovery](transient_recovery.json) | answered | answered | PASS | search_documents → read_document → read_document → finish |
| [missing_question](missing_question.json) | needs_clarification | needs_clarification | PASS |  |
| [step_limit](step_limit.json) | incomplete | incomplete | PASS | search_documents |
| [changed_source](changed_source.json) | answered | answered | PASS | search_documents → read_document → finish |
