# RQ2 真实 LLM 重述 pilot

100 次实验请求由初始长度受限阶段 15 次和 `reasoning_effort=minimal` 阶段 85 次组成。初始阶段有 14 次因推理耗尽 1,100-token 上限而未返回代码；发现后立即停止。minimal 阶段 85/85 均返回可解析代码，reasoning tokens 总数为 0。

## 功能正确性

| 语言 | changed | syntax-valid changed | post-pass | EPR |
|---|---:|---:|---:|---:|
| cpp | 15 | 15 | 15 | 100.00% |
| java | 15 | 15 | 15 | 100.00% |
| javascript | 15 | 15 | 15 | 100.00% |

三语言合计 45/45 执行通过。主实验 pilot 共 40 条，其中攻击前语法有效 34 条，这 34 条攻击后全部语法有效；正式 cohort 已增加双方法 baseline 语法资格审查。

## 水印链路 smoke 结果

| 方法 | 数据集 | paired n | clean BAR | attack BAR | DeltaBAR | attack MAR |
|---|---|---:|---:|---:|---:|---:|
| codemark | csn_java | 3 | 0.9167 | 0.6667 | 0.2500 | 0.3333 |
| codemark | csn_js | 5 | 1.0000 | 0.9500 | 0.0500 | 0.8000 |
| codemark | github_c_funcs | 5 | 0.9500 | 0.7000 | 0.2500 | 0.4000 |
| codemark | github_java_funcs | 4 | 1.0000 | 0.6875 | 0.3125 | 0.5000 |
| srcmarker | csn_java | 3 | 0.9167 | 0.4167 | 0.5000 | 0.0000 |
| srcmarker | csn_js | 5 | 1.0000 | 0.7000 | 0.3000 | 0.2000 |
| srcmarker | github_c_funcs | 5 | 1.0000 | 0.8500 | 0.1500 | 0.6000 |
| srcmarker | github_java_funcs | 5 | 1.0000 | 0.8500 | 0.1500 | 0.6000 |

上述每格仅 3–5 条，是端到端集成检查，不作为论文效应量结论。

## 费用与全量投影

- minimal 阶段精确 usage：输入 92,195，输出 21,140 tokens。
- 已记录 usage 的费用加初始 14 次缺失 usage 的保守上界：不超过 **¥3.67**。
- baseline 语法过滤后的全量计划：LLM-EPR 2,400 次，主实验 5,748 次，共 8,148 次。
- 按 minimal pilot 实测均值投影：约 **¥219.18**；增加 10% 重试储备后约 **¥241.10**。

完整逐样本结果、usage、状态、置信区间和 SHA-256 见 `rq2_llm_pilot.json`。
