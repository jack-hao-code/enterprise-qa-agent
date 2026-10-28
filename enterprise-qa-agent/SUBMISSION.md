# 第3题提交说明

本地项目代码与离线验收材料已经准备，远程仓库为 [jack-hao-code/enterprise-qa-agent](https://github.com/jack-hao-code/enterprise-qa-agent)。**当前尚未生成真实模型执行证据。仓库上传不等于已完成线上交卷。**

## 提交前必须核实

1. 阅读并理解代码，按实际情况补充个人贡献和用时，不把 AI 工作写成本人独立完成。
2. 配置真实模型，运行 `python3 scripts/evaluate.py --backend live`，复核并保留实际结果。至少正常与冲突/补查两条真实模型路径，不可使用 Mock 冒充。
3. 更新 docs/03-evaluation.md 的实际模型结果、失败和限制；重新执行单元测试。
4. 核对 GitHub 仓库中已上传本项目；确保没有 `.env`、密钥或真实隐私资料。私有仓库按考试要求给指定评审账号读取权限。
5. 在最终变更后提交并推送，使用 `git rev-parse HEAD` 获取最终完整 commit SHA，再提交题号、真实 GitHub URL 和该 SHA。

如果本目录还没有初始化 Git，可在完成真实验证后执行：

```bash
git init -b main
git add .
git commit -m "Implement enterprise knowledge QA agent"
git remote add origin 你已创建的GitHub仓库地址
git push -u origin main
git rev-parse HEAD
```

若已经初始化，不要重复设置 origin。本项目远程 URL 为 `https://github.com/jack-hao-code/enterprise-qa-agent.git`；最终 SHA 通过实际提交后的 `git rev-parse HEAD` 获取。

## 可用于答题框的说明底稿

选择第3题：企业知识问答 Agent。

项目提供 Python CLI、带 ID/日期的合成制度资料、文档检索和原文读取工具。真实模式由模型选择检索、读取、补查、追问或结束，工具观察会回传模型，执行器设置调用上限并校验引用。正常答案以经过逐字校验的原文展示；已识别的制度冲突列出双方规定并请求确认，不按版本日期擅自决定适用制度。资料不足、工具失败及执行超限均有明确状态。

当前已提供可执行测试和覆盖明确答案、制度冲突、资料外问题、同义改写、上下文追问、工具失败等场景的离线实际输入、输出及 Trace。Mock 仅验证控制流，不证明真实模型效果。真实模型入口已实现，实际模型验证情况、GitHub URL、最终 commit SHA 及个人投入请在确实完成后据实补充。

详细运行步骤、验证证据、AI 辅助范围及限制见仓库 README 和 docs/01-05。
