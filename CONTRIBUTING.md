# 贡献指南 / Contributing

欢迎改进信号处理、测试、安全规则、文档和可复现实验。

1. 从独立分支开发，并保持修改范围清晰；
2. 不提交真实个人信息、健康数据、密钥、原始审计日志或无再分发权的数据；
3. 新模型必须按受试者划分数据，并提交完整基准结果；
4. 性能回退或未通过发布门禁的候选必须明确标注；
5. 运行 `python -m unittest discover -s tests -v`；
6. 提交说明包含目的、方法、验证结果和已知限制。

Contributions to signal processing, tests, safety controls, documentation, and reproducible evaluation
are welcome. Never commit personal health information, credentials, raw audit logs, or restricted data.
Evaluate models with subject-isolated splits, disclose regressions, run the full test suite, and preserve
the non-diagnostic, fail-closed behavior.

The ReHealth name and official logo are brand assets. The Apache-2.0 code license does not grant
trademark rights or permission to imply endorsement.
