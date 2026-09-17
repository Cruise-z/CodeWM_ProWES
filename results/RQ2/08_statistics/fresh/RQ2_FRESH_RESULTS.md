# RQ2 fresh-checkpoint 实验结果

两种方法均以 seed 42 随机初始化，在四个数据集上独立训练 25 epochs；统一使用 4-bit、共享 GRU 编码器、batch size 64。规则攻击按 Id、Expr、Block、ALL 四个通道运行，鲁棒性置信区间使用 10,000 次样本级配对 bootstrap。

## 训练后 clean 结果

| 方法 | 数据集 | 最优 epoch | BAR | MAR | 样本数 |
|---|---|---:|---:|---:|---:|
| SrcMarker | GitHub-C | 14 | 0.9395 | 0.8192 | 459 |
| SrcMarker | GitHub-Java | 22 | 0.9378 | 0.8131 | 551 |
| SrcMarker | CSN-JavaScript | 15 | 0.9869 | 0.9663 | 3150 |
| SrcMarker | CSN-Java | 15 | 0.9732 | 0.9315 | 10535 |
| CodeMark | GitHub-C | 22 | 0.9602 | 0.8824 | 459 |
| CodeMark | GitHub-Java | 24 | 0.9528 | 0.8838 | 551 |
| CodeMark | CSN-JavaScript | 16 | 0.9810 | 0.9502 | 3150 |
| CodeMark | CSN-Java | 21 | 0.9798 | 0.9315 | 10535 |

## 规则攻击结果

| 方法 | 数据集 | 通道 | clean BAR | attack BAR | DeltaBAR | attack MAR | change rate | syntax-valid rate |
|---|---|---|---:|---:|---:|---:|---:|---:|
| SrcMarker | GitHub-C | id | 0.9381 | 0.5290 | 0.4090 | 0.1272 | 0.9760 | 0.9760 |
| SrcMarker | GitHub-C | expr | 0.9381 | 0.9308 | 0.0073 | 0.8036 | 0.9760 | 0.9760 |
| SrcMarker | GitHub-C | block | 0.9381 | 0.8092 | 0.1289 | 0.5625 | 0.9760 | 0.9760 |
| SrcMarker | GitHub-C | all | 0.9381 | 0.5340 | 0.4040 | 0.0915 | 0.9760 | 0.9760 |
| SrcMarker | GitHub-Java | id | 0.9389 | 0.4730 | 0.4659 | 0.0814 | 0.9583 | 0.9583 |
| SrcMarker | GitHub-Java | expr | 0.9389 | 0.9384 | 0.0005 | 0.8182 | 0.9583 | 0.9583 |
| SrcMarker | GitHub-Java | block | 0.9389 | 0.9285 | 0.0104 | 0.7992 | 0.9583 | 0.9583 |
| SrcMarker | GitHub-Java | all | 0.9389 | 0.4744 | 0.4645 | 0.0758 | 0.9583 | 0.9583 |
| SrcMarker | CSN-JavaScript | id | 0.9868 | 0.4671 | 0.5197 | 0.0534 | 0.9937 | 0.9937 |
| SrcMarker | CSN-JavaScript | expr | 0.9868 | 0.9875 | -0.0006 | 0.9674 | 0.9937 | 0.9937 |
| SrcMarker | CSN-JavaScript | block | 0.9868 | 0.9871 | -0.0003 | 0.9665 | 0.9937 | 0.9937 |
| SrcMarker | CSN-JavaScript | all | 0.9868 | 0.4658 | 0.5210 | 0.0508 | 0.9937 | 0.9937 |
| SrcMarker | CSN-Java | id | 0.9734 | 0.5276 | 0.4458 | 0.1013 | 0.9561 | 0.9561 |
| SrcMarker | CSN-Java | expr | 0.9734 | 0.9734 | 0.0000 | 0.9320 | 0.9561 | 0.9561 |
| SrcMarker | CSN-Java | block | 0.9734 | 0.9736 | -0.0002 | 0.9328 | 0.9561 | 0.9561 |
| SrcMarker | CSN-Java | all | 0.9734 | 0.5313 | 0.4421 | 0.1021 | 0.9561 | 0.9561 |
| CodeMark | GitHub-C | id | 0.9609 | 0.4508 | 0.5101 | 0.0403 | 0.9739 | 0.9739 |
| CodeMark | GitHub-C | expr | 0.9609 | 0.9592 | 0.0017 | 0.8792 | 0.9739 | 0.9739 |
| CodeMark | GitHub-C | block | 0.9609 | 0.9620 | -0.0011 | 0.8881 | 0.9739 | 0.9739 |
| CodeMark | GitHub-C | all | 0.9609 | 0.4485 | 0.5123 | 0.0380 | 0.9739 | 0.9739 |
| CodeMark | GitHub-Java | id | 0.9528 | 0.5168 | 0.4360 | 0.0710 | 0.9710 | 0.9710 |
| CodeMark | GitHub-Java | expr | 0.9528 | 0.9533 | -0.0005 | 0.8879 | 0.9710 | 0.9710 |
| CodeMark | GitHub-Java | block | 0.9528 | 0.9551 | -0.0023 | 0.8935 | 0.9710 | 0.9710 |
| CodeMark | GitHub-Java | all | 0.9528 | 0.5322 | 0.4206 | 0.0710 | 0.9710 | 0.9710 |
| CodeMark | CSN-JavaScript | id | 0.9808 | 0.5000 | 0.4808 | 0.0601 | 0.9937 | 0.9937 |
| CodeMark | CSN-JavaScript | expr | 0.9808 | 0.9808 | 0.0000 | 0.9502 | 0.9937 | 0.9937 |
| CodeMark | CSN-JavaScript | block | 0.9808 | 0.9804 | 0.0004 | 0.9486 | 0.9937 | 0.9937 |
| CodeMark | CSN-JavaScript | all | 0.9808 | 0.5009 | 0.4800 | 0.0645 | 0.9937 | 0.9937 |
| CodeMark | CSN-Java | id | 0.9801 | 0.5444 | 0.4358 | 0.1136 | 0.9559 | 0.9559 |
| CodeMark | CSN-Java | expr | 0.9801 | 0.9802 | -0.0000 | 0.9327 | 0.9559 | 0.9559 |
| CodeMark | CSN-Java | block | 0.9801 | 0.9798 | 0.0003 | 0.9322 | 0.9559 | 0.9559 |
| CodeMark | CSN-Java | all | 0.9801 | 0.5418 | 0.4384 | 0.1091 | 0.9559 | 0.9559 |

完整 checkpoint 哈希、训练记录、状态计数和 95% CI 见 `rq2_fresh_results.json`；扁平指标见 `rq2_fresh_rule_metrics.csv`。

## 尚未生成的数据

当前 workspace 未配置可用的真实 LLM provider/API 凭据，因此本报告不把 mock identity 输出作为 LLM 攻击性能数据。规则攻击和检测数据均为本次 fresh checkpoint 实际运行结果。
