# RQ2 实验总报告：论文正文与附录输入

## 1. 实验完成范围

两种方法均从随机初始化独立训练，并在 GitHub-C、GitHub-Java、CSN-JavaScript 和 CSN-Java 上评估。训练统一使用 4-bit 水印、共享 GRU 编码器、batch size 64、25 epochs 和 seed 42。规则攻击覆盖 ID、Expr、Block 与组合 ALL 四个通道；真实 LLM-RAG 主实验使用平衡设计，每个方法×数据集单元 125 条，共 1,000 条。

### Clean 性能

| Method | Dataset | Best epoch | BAR | MAR | n |
|---|---|---|---|---|---|
| SrcMarker | GitHub-C | 14 | 0.9395 | 0.8192 | 459 |
| SrcMarker | GitHub-Java | 22 | 0.9378 | 0.8131 | 551 |
| SrcMarker | CSN-JavaScript | 15 | 0.9869 | 0.9663 | 3150 |
| SrcMarker | CSN-Java | 15 | 0.9732 | 0.9315 | 10535 |
| CodeMark | GitHub-C | 22 | 0.9602 | 0.8824 | 459 |
| CodeMark | GitHub-Java | 24 | 0.9528 | 0.8838 | 551 |
| CodeMark | CSN-JavaScript | 16 | 0.9810 | 0.9502 | 3150 |
| CodeMark | CSN-Java | 21 | 0.9798 | 0.9315 | 10535 |

### RQ2 主结果

| Method | Dataset | Rule-ALL BAR | Rule ΔBAR | Rule MAR | LLM BAR | LLM ΔBAR | LLM MAR | LLM n/cov. |
|---|---|---|---|---|---|---|---|---|
| SrcMarker | GitHub-C | 0.5340 | 0.4040 | 0.0915 | 0.7146 | 0.2208 | 0.3500 | 120/96.00% |
| SrcMarker | GitHub-Java | 0.4744 | 0.4645 | 0.0758 | 0.6963 | 0.2624 | 0.3223 | 121/96.80% |
| SrcMarker | CSN-JavaScript | 0.4658 | 0.5210 | 0.0508 | 0.7398 | 0.2602 | 0.3902 | 123/98.40% |
| SrcMarker | CSN-Java | 0.5313 | 0.4421 | 0.1021 | 0.7073 | 0.2642 | 0.3415 | 123/98.40% |
| CodeMark | GitHub-C | 0.4485 | 0.5123 | 0.0380 | 0.7394 | 0.2331 | 0.3983 | 118/94.40% |
| CodeMark | GitHub-Java | 0.5322 | 0.4206 | 0.0710 | 0.6613 | 0.3024 | 0.2742 | 124/99.20% |
| CodeMark | CSN-JavaScript | 0.5009 | 0.4800 | 0.0645 | 0.7521 | 0.2333 | 0.4000 | 120/96.00% |
| CodeMark | CSN-Java | 0.5418 | 0.4384 | 0.1091 | 0.7154 | 0.2663 | 0.3577 | 123/98.40% |

BAR 为逐比特准确率，MAR 为 4-bit 消息完全匹配率，ΔBAR = clean BAR − attacked BAR。LLM `n/cov.` 是成功进入成对水印评估的样本数及其相对 125 条尝试的覆盖率。每个单元的 10,000 次样本级配对 bootstrap 95% CI 位于 CSV/JSON 结果中。

### LLM 生成状态、token 与费用（逐格）

| Method | Dataset | n | Valid | Syntax invalid | No-op | Error | Prompt tok. | Completion tok. | Cost CNY |
|---|---|---|---|---|---|---|---|---|---|
| SrcMarker | GitHub-C | 125 | 120 | 2 | 3 | 0 | 140745 | 36459 | 3.7836 |
| SrcMarker | GitHub-Java | 125 | 121 | 1 | 3 | 0 | 136114 | 31752 | 3.4136 |
| SrcMarker | CSN-JavaScript | 125 | 123 | 0 | 2 | 0 | 148244 | 44789 | 4.4324 |
| SrcMarker | CSN-Java | 125 | 123 | 0 | 2 | 0 | 150180 | 46496 | 4.5688 |
| CodeMark | GitHub-C | 125 | 118 | 2 | 5 | 0 | 139958 | 35847 | 3.7339 |
| CodeMark | GitHub-Java | 125 | 124 | 0 | 1 | 0 | 135214 | 30246 | 3.3003 |
| CodeMark | CSN-JavaScript | 125 | 120 | 0 | 5 | 0 | 145923 | 43238 | 4.3035 |
| CodeMark | CSN-Java | 125 | 123 | 0 | 2 | 0 | 148422 | 44345 | 4.4028 |

### LLM 水印结果及置信区间（逐格）

| Method | Dataset | n | Clean BAR | Attack BAR [95% CI] | ΔBAR [95% CI] | Attack MAR [95% CI] | Coverage |
|---|---|---|---|---|---|---|---|
| SrcMarker | GitHub-C | 120 | 0.9354 | 0.7146 [0.6667, 0.7625] | 0.2208 [0.1750, 0.2687] | 0.3500 [0.2667, 0.4333] | 96.00% |
| SrcMarker | GitHub-Java | 121 | 0.9587 | 0.6963 [0.6467, 0.7459] | 0.2624 [0.2107, 0.3140] | 0.3223 [0.2397, 0.4050] | 96.80% |
| SrcMarker | CSN-JavaScript | 123 | 1.0000 | 0.7398 [0.6931, 0.7846] | 0.2602 [0.2154, 0.3069] | 0.3902 [0.3089, 0.4797] | 98.40% |
| SrcMarker | CSN-Java | 123 | 0.9715 | 0.7073 [0.6585, 0.7581] | 0.2642 [0.2154, 0.3130] | 0.3415 [0.2602, 0.4309] | 98.40% |
| CodeMark | GitHub-C | 118 | 0.9725 | 0.7394 [0.6886, 0.7860] | 0.2331 [0.1843, 0.2839] | 0.3983 [0.3136, 0.4831] | 94.40% |
| CodeMark | GitHub-Java | 124 | 0.9637 | 0.6613 [0.6109, 0.7117] | 0.3024 [0.2540, 0.3528] | 0.2742 [0.2016, 0.3548] | 99.20% |
| CodeMark | CSN-JavaScript | 120 | 0.9854 | 0.7521 [0.7063, 0.7958] | 0.2333 [0.1896, 0.2792] | 0.4000 [0.3167, 0.4917] | 96.00% |
| CodeMark | CSN-Java | 123 | 0.9817 | 0.7154 [0.6646, 0.7642] | 0.2663 [0.2175, 0.3171] | 0.3577 [0.2764, 0.4472] | 98.40% |

### 规则攻击完整 32 格结果及置信区间

| Method | Dataset | Channel | n | Attack BAR [95% CI] | ΔBAR [95% CI] | Attack MAR [95% CI] | Coverage |
|---|---|---|---|---|---|---|---|
| SrcMarker | GitHub-C | ID | 448 | 0.5290 [0.5033, 0.5547] | 0.4090 [0.3811, 0.4369] | 0.1272 [0.0982, 0.1585] | 97.60% |
| SrcMarker | GitHub-C | EXPR | 448 | 0.9308 [0.9157, 0.9448] | 0.0073 [0.0011, 0.0140] | 0.8036 [0.7656, 0.8393] | 97.60% |
| SrcMarker | GitHub-C | BLOCK | 448 | 0.8092 [0.7846, 0.8331] | 0.1289 [0.1071, 0.1512] | 0.5625 [0.5156, 0.6071] | 97.60% |
| SrcMarker | GitHub-C | ALL | 448 | 0.5340 [0.5100, 0.5580] | 0.4040 [0.3783, 0.4291] | 0.0915 [0.0670, 0.1183] | 97.60% |
| SrcMarker | GitHub-Java | ID | 528 | 0.4730 [0.4493, 0.4967] | 0.4659 [0.4403, 0.4920] | 0.0814 [0.0587, 0.1061] | 95.83% |
| SrcMarker | GitHub-Java | EXPR | 528 | 0.9384 [0.9257, 0.9503] | 0.0005 [0.0000, 0.0014] | 0.8182 [0.7860, 0.8504] | 95.83% |
| SrcMarker | GitHub-Java | BLOCK | 528 | 0.9285 [0.9148, 0.9418] | 0.0104 [0.0047, 0.0170] | 0.7992 [0.7652, 0.8314] | 95.83% |
| SrcMarker | GitHub-Java | ALL | 528 | 0.4744 [0.4508, 0.4976] | 0.4645 [0.4384, 0.4905] | 0.0758 [0.0530, 0.0985] | 95.83% |
| SrcMarker | CSN-JavaScript | ID | 3130 | 0.4671 [0.4578, 0.4764] | 0.5197 [0.5100, 0.5295] | 0.0534 [0.0457, 0.0613] | 99.37% |
| SrcMarker | CSN-JavaScript | EXPR | 3130 | 0.9875 [0.9847, 0.9900] | -0.0006 [-0.0014, -0.0001] | 0.9674 [0.9610, 0.9735] | 99.37% |
| SrcMarker | CSN-JavaScript | BLOCK | 3130 | 0.9871 [0.9843, 0.9898] | -0.0003 [-0.0011, 0.0005] | 0.9665 [0.9601, 0.9725] | 99.37% |
| SrcMarker | CSN-JavaScript | ALL | 3130 | 0.4658 [0.4569, 0.4748] | 0.5210 [0.5117, 0.5305] | 0.0508 [0.0435, 0.0588] | 99.37% |
| SrcMarker | CSN-Java | ID | 10072 | 0.5276 [0.5225, 0.5327] | 0.4458 [0.4405, 0.4512] | 0.1013 [0.0954, 0.1071] | 95.61% |
| SrcMarker | CSN-Java | EXPR | 10072 | 0.9734 [0.9712, 0.9756] | 0.0000 [-0.0001, 0.0002] | 0.9320 [0.9270, 0.9369] | 95.61% |
| SrcMarker | CSN-Java | BLOCK | 10072 | 0.9736 [0.9714, 0.9757] | -0.0002 [-0.0005, 0.0001] | 0.9328 [0.9278, 0.9376] | 95.61% |
| SrcMarker | CSN-Java | ALL | 10072 | 0.5313 [0.5263, 0.5364] | 0.4421 [0.4369, 0.4474] | 0.1021 [0.0961, 0.1079] | 95.61% |
| CodeMark | GitHub-C | ID | 447 | 0.4508 [0.4279, 0.4737] | 0.5101 [0.4849, 0.5352] | 0.0403 [0.0224, 0.0582] | 97.39% |
| CodeMark | GitHub-C | EXPR | 447 | 0.9592 [0.9474, 0.9698] | 0.0017 [-0.0011, 0.0050] | 0.8792 [0.8479, 0.9083] | 97.39% |
| CodeMark | GitHub-C | BLOCK | 447 | 0.9620 [0.9502, 0.9726] | -0.0011 [-0.0062, 0.0039] | 0.8881 [0.8568, 0.9172] | 97.39% |
| CodeMark | GitHub-C | ALL | 447 | 0.4485 [0.4262, 0.4709] | 0.5123 [0.4866, 0.5380] | 0.0380 [0.0224, 0.0559] | 97.39% |
| CodeMark | GitHub-Java | ID | 535 | 0.5168 [0.4958, 0.5374] | 0.4360 [0.4126, 0.4598] | 0.0710 [0.0505, 0.0935] | 97.10% |
| CodeMark | GitHub-Java | EXPR | 535 | 0.9533 [0.9402, 0.9654] | -0.0005 [-0.0014, 0.0000] | 0.8879 [0.8598, 0.9140] | 97.10% |
| CodeMark | GitHub-Java | BLOCK | 535 | 0.9551 [0.9425, 0.9673] | -0.0023 [-0.0047, -0.0005] | 0.8935 [0.8673, 0.9196] | 97.10% |
| CodeMark | GitHub-Java | ALL | 535 | 0.5322 [0.5117, 0.5528] | 0.4206 [0.3977, 0.4435] | 0.0710 [0.0505, 0.0935] | 97.10% |
| CodeMark | CSN-JavaScript | ID | 3130 | 0.5000 [0.4911, 0.5086] | 0.4808 [0.4716, 0.4904] | 0.0601 [0.0518, 0.0687] | 99.37% |
| CodeMark | CSN-JavaScript | EXPR | 3130 | 0.9808 [0.9775, 0.9840] | 0.0000 [-0.0004, 0.0004] | 0.9502 [0.9422, 0.9578] | 99.37% |
| CodeMark | CSN-JavaScript | BLOCK | 3130 | 0.9804 [0.9771, 0.9836] | 0.0004 [-0.0004, 0.0012] | 0.9486 [0.9406, 0.9562] | 99.37% |
| CodeMark | CSN-JavaScript | ALL | 3130 | 0.5009 [0.4920, 0.5097] | 0.4800 [0.4708, 0.4895] | 0.0645 [0.0562, 0.0735] | 99.37% |
| CodeMark | CSN-Java | ID | 10070 | 0.5444 [0.5392, 0.5495] | 0.4358 [0.4304, 0.4412] | 0.1136 [0.1074, 0.1198] | 95.59% |
| CodeMark | CSN-Java | EXPR | 10070 | 0.9802 [0.9786, 0.9817] | -0.0000 [-0.0002, 0.0002] | 0.9327 [0.9279, 0.9374] | 95.59% |
| CodeMark | CSN-Java | BLOCK | 10070 | 0.9798 [0.9782, 0.9814] | 0.0003 [-0.0001, 0.0008] | 0.9322 [0.9273, 0.9370] | 95.59% |
| CodeMark | CSN-Java | ALL | 10070 | 0.5418 [0.5365, 0.5468] | 0.4384 [0.4330, 0.4439] | 0.1091 [0.1031, 0.1152] | 95.59% |

## 2. 功能正确性与有效性

规则变换在全部 MBCPP、MBJP、MBJSP 上完成 9,612 个数据集×通道执行单元；9,572 个语法有效变换中 9,444 个通过测试，加权 EPR 为 **98.66%**。

| Dataset | ID | Expr | Block | ALL |
|---|---|---|---|---|
| MBCPP | 99.08% | 100.00% | 98.82% | 98.03% |
| MBJP | 99.05% | 100.00% | 99.17% | 98.46% |
| MBJSP | 96.57% | 99.11% | 99.11% | 96.45% |

在正式 LLM 主实验前，另以三个可执行 MBXP 数据集各 15 条完成 LLM-RAG 功能验证：总计 **45/45** 个语法有效改写通过测试（EPR 100.00%）。该 45 条结果用于攻击实现的执行正确性验证，不作为 1,000 条水印效应量的组成部分。

1,000 条正式 LLM 输出状态为：valid attack=972、syntax invalid=5、no-op=23、error=0；最终成对水印分析覆盖 972/1000（97.20%）。

## 3. 结果解读（供论文分析）

- 规则攻击中，SrcMarker 跨数据集平均 ΔBAR：ID=0.4601、Expr=0.0018、Block=0.0347、ALL=0.4579；CodeMark 对应为 ID=0.4657、Expr=0.0003、Block=-0.0007、ALL=0.4628。
- LLM-RAG 的有效样本加权结果：SrcMarker clean/attack BAR=0.9666/0.7146，ΔBAR=0.2521，attack MAR=0.3511；CodeMark clean/attack BAR=0.9758/0.7165，ΔBAR=0.2593，attack MAR=0.3567。
- 这些比较是描述性的；方法间显著性结论不应仅由重叠/不重叠置信区间推断。论文若需要正式的方法间假设检验，应在相同 UID 上预注册配对统计量。
- `rq2_llm_method_contrasts.csv` 另外提供相同 UID 且双方均为 valid attack 的交集配对比较及 10,000 次 bootstrap CI；它回答的是共同有效子集上的方法差异，不能替代包含无效攻击率在内的 coverage 比较。
- 4-bit MAR 的随机机会水平为 6.25%，BAR 的机会水平为 50%。

## 4. 可直接用于英文正文的实验设置

> We trained both watermarking methods from random initialization on GitHub-C, GitHub-Java, CodeSearchNet JavaScript, and CodeSearchNet Java using a four-bit payload, a shared GRU encoder, batch size 64, 25 epochs, and random seed 42. Robustness was evaluated under identifier-, expression-, block-, and jointly composed rule transformations. We additionally evaluated semantic restatement using an LLM augmented by deterministic BM25 retrieval over a frozen local rule knowledge base. We report clean and attacked bit accuracy (BAR), exact-message accuracy (MAR), and the paired degradation ΔBAR = BAR_clean − BAR_attack. Confidence intervals were computed by 10,000 sample-level paired bootstrap replicates.

> The LLM experiment used a balanced 2 × 4 design with 125 programs per method–dataset cell (1,000 generations total). The two methods shared the same underlying program cohort. Eligible samples had non-empty watermarked code of at most 1,400 characters and passed language-specific Tree-sitter parsing before attack. Generation used GPT-5 with temperature 0, reasoning effort “minimal,” a 1,100-token completion cap, retrieval top-k 6, and seed 42. Invalid or unchanged generations were retained in the audit trail and excluded from paired watermark-effect estimates through explicit status labels rather than silent deletion.

## 5. 可直接用于英文结果段落

> Across the complete executable MBXP validation matrix, 9,444 of 9,572 syntax-valid changed programs retained their original behavior, yielding a weighted execution-preservation rate of 98.66%. In the independent LLM implementation check, all 45 syntax-valid restatements passed their executable tests. The 1,000-generation main experiment produced 972 valid changed programs and 972 samples with complete clean/attacked watermark predictions. Under LLM restatement, the valid-sample weighted ΔBAR was 0.252 for SrcMarker and 0.259 for CodeMark; corresponding attacked MAR values were 0.351 and 0.357. Dataset-level estimates and paired-bootstrap confidence intervals are reported in the artifact tables.

## 6. 附录所需复现细节

- 数据集标签：GitHub-C、GitHub-Java、CSN-JavaScript、CSN-Java；功能验证集：MBCPP、MBJP、MBJSP。
- 训练：fresh random initialization；epochs=25；batch size=64；4-bit；GRU shared encoder；seed=42；`varmask_prob=0.5`；训练/验证/测试划分及词表大小保存在每个 `run_manifest.json`。
- 规则攻击：global seed=42；样本 seed 由 global seed、UID、channel 确定；语法检查使用 Tree-sitter；无可行变换、语法无效及执行失败均保留状态。
- LLM：provider=openai-compatible；base URL=`https://api.chatanywhere.tech/v1`；requested model=`gpt-5`；response model(s)=`gpt-5-2025-08-07`；temperature=0；reasoning effort=minimal；max completion tokens=1,100；top-k=6；每次最多一次请求；system/user prompt 与规则库逐字归档。
- Cohort：先按共享原始程序长度降序、输入索引升序确定；双方法均需非空、≤1,400 字符且 baseline 语法有效；每格取前 125 条。两方法同一数据集使用相同 UID。
- 检测：每个方法/数据集使用自身 fresh checkpoint；token 序列截断到 512；4-bit 阈值为 sigmoid>0.5。
- 统计：所有 BAR/MAR 差异以样本为重采样单位，10,000 次 paired bootstrap，seed=42；不把 4 个 bit 当作独立观测。
- 软件：Python 3.13.5；训练清单记录 PyTorch 2.6.0+cu124；EPR 环境使用 g++ 11.4、Java 21、Node 22；本机 GPU 为 NVIDIA A800 80GB。
- LLM usage：prompt=1,144,800 tokens，completion=313,172 tokens，reasoning=0 tokens；按归档单价记录费用 ¥31.94。
- 凭据不属于 artifact；复现者通过 `--env-file` 提供 mode 600 的本地文件。

### 6.1 训练数据划分、容量及 checkpoint 身份

| Method | Dataset | Train | Valid | Test | Vocab | Transform cap. | Checkpoint SHA-256 |
|---|---|---|---|---|---|---|---|
| SrcMarker | GitHub-C | 3661 | 457 | 459 | 10169 | 4096 | 9b6717e3d53ced224ac04625f108e4a1dca65cc97b9d10ed7a4650e047a2a815 |
| SrcMarker | GitHub-Java | 4400 | 550 | 551 | 10190 | 4096 | 875a0910c7a005a42b36f3344f5d851ba6ffddba2819119179fdd396daaf2531 |
| SrcMarker | CSN-JavaScript | 56393 | 3716 | 3150 | 134456 | 4096 | a0240b48e4cddecc89f0eea38687139bab7142c537c064f0568563db2dae4e19 |
| SrcMarker | CSN-Java | 157858 | 4940 | 10535 | 126187 | 4096 | fbb23c432234ba2fba5fdcc2eee3c395755c650559f9e387f16eb4035c2189f2 |
| CodeMark | GitHub-C | 3661 | 457 | 459 | 10169 | 4 | 1d837005d47fd28ce3999786cd0cc30c2d5d89fdb7d60a1736ae9fe4cd35eedd |
| CodeMark | GitHub-Java | 4400 | 550 | 551 | 10190 | 4 | 6cf99c34558456526ffc5e1528a350fccc8370f94e6c2757edc09f4fd571a022 |
| CodeMark | CSN-JavaScript | 56393 | 3716 | 3150 | 134456 | 4 | 03b413e5b93a825496006466f2c7ae4502c08dde6d74eb79cdf95605ba166ea0 |
| CodeMark | CSN-Java | 157858 | 4940 | 10535 | 126187 | 4 | f74f65f079d082da946dbb4c668b4067d4a7fd74fff15678e5c17f0032a9f060 |

表中 SHA-256 为实际用于最终检测的 `models_best.pt`。每次训练的完整参数、时间、Python/PyTorch 版本和数据规模也保存在对应 `run_manifest.json`；25 个 epoch 的逐轮指标保存在 `training_history.json`。

### 6.2 LLM cohort 的构造审计

| Dataset | Input | Shared eligible | Empty reject | Length reject | Syntax reject | Available selected |
|---|---|---|---|---|---|---|
| GitHub-C | 459 | 383 | 0 | 31 | 45 | 383 |
| GitHub-Java | 551 | 491 | 0 | 24 | 36 | 491 |
| CSN-JavaScript | 3150 | 2976 | 0 | 174 | 0 | 1000 |
| CSN-Java | 10535 | 9381 | 0 | 492 | 662 | 1000 |

正式 1,000 次实验从每个 available-selected cohort 的前 125 个稳定 UID 取样，形成 2 methods × 4 datasets × 125。排序键为共享原始程序字符长度降序，再按原始输入索引升序；这一步在调用 API 前完成，避免按生成结果或检测结果选择样本。

### 6.3 GPT-5 与 API 的精确配置

- API 类型：OpenAI-compatible Chat Completions；请求路径：`https://api.chatanywhere.tech/v1/chat/completions`。
- 请求模型别名：`gpt-5`；1000 次正式请求观察到的返回快照：`gpt-5-2025-08-07`。
- Payload 固定字段：`model`、两条 `messages`、`temperature=0`、逐样本 `seed`、`max_completion_tokens=1100`、`reasoning_effort=minimal`。
- Provider timeout：120 s；User-Agent：`RQ2-CodeWM-Experiment/1.0`；正式实验 `max_attempts=1`，因此没有隐藏重试。
- 逐样本 seed：取 `SHA256("42\0<sample_uid>\0llm-rag-all")` 的前 4 bytes，按 big-endian unsigned integer 解释。
- 输出契约：必须返回 `<applied_rules>...</applied_rules>` 和单个 fenced source block；缺失代码块即标为 error。未知/未检索的 reported rule ID 会被记录为 `unknown_reported_rule_ids`。
- 服务凭据仅从 mode-600 的外部 env 文件装载；报告、日志和 artifact 均不包含凭据。
- 定价审计采用运行时归档费率：输入 ¥0.00875/1K tokens，输出 ¥0.07/1K tokens。
- 价格来源（访问日期 2026-09-16）：`https://github.com/chatanywhere/GPT_API_free`；GPT-5 官方模型页：`https://developers.openai.com/api/docs/models/gpt-5`。实际账单由中转服务而非 OpenAI 官方美元价格决定。

### 6.4 RAG 检索实现

本地知识库共 12 张规则卡。检索器为依赖无关的确定性 BM25，参数 `k1=1.5`、`b=0.75`；查询文本为 `"<language> <channel> source-to-source watermark robustness " + source[:2500]`。先按语言与通道过滤；ALL 通道先从 ID、Expr、Block 各取最高分规则，再按分数与 Rule ID 稳定排序补足到 top-k=6。

| Rule ID | Channel | Languages | Title | Preconditions |
|---|---|---|---|---|
| id.rename_local | id | java/cpp/javascript | Local identifier renaming | rename only locally declared identifiers; avoid collisions and reserved keywords; update all bound uses consistently |
| id.naming_style | id | java/cpp/javascript | Identifier naming-style conversion | local identifiers only; avoid collisions; preserve binding |
| expr.update_ops | expr | java/cpp/javascript | Standalone update-form equivalence | the update value must not be consumed; operate only on standalone update statements in safe mode |
| expr.predicate_loop_literal | expr | cpp/javascript/java | Loop-condition representation | Java never uses integer 1 as a boolean condition; while-loop omission is not allowed; for-loop omission is allowed |
| expr.default_param_indexof | expr | java/javascript | Explicit default indexOf start position | receiver must be recognized as a built-in string/array value; do not rewrite unknown user-defined indexOf methods |
| expr.null_operand_swap | expr | java/cpp/javascript | Null-comparison operand swap | comparison operator must be equality or inequality; one operand must be null/nullptr/NULL |
| expr.empty_size | expr | java/cpp | Emptiness and size equivalence | receiver type must be a recognized standard container; unknown/custom types must be skipped |
| block.var_decl_reposition | block | java/cpp | Variable declaration repositioning | move only before first use; C++ safe mode restricts to scalar built-in types; JavaScript is skipped because TDZ/hoisting can change behavior |
| block.loop_stmt | block | java/cpp/javascript | for/while loop conversion | preserve update execution before same-loop continue; do not move updates across nested loop boundaries |
| block.if_flat_nest | block | java/cpp/javascript | Nested/compound if conversion | neither participating if may have an else branch |
| block.conditionals | block | java/cpp/javascript | Conditional structural rewriting | switch cases must not fall through; switch selector must be side-effect-free because an if-chain may reevaluate it; ternary rewrite is restricted to simple assignments |
| block.if_swap | block | java/cpp/javascript | Conditional branch swap | an else branch must exist; condition negation must preserve precedence |

模型报告的 applied-rule 总频数如下（一次生成可报告多个规则；逐方法×数据集的 retrieved/applied/valid-applied 频数见 `rq2_llm_rule_usage.csv`）：

| Reported applied rule | Count across 1,000 generations |
|---|---|
| id.rename_local | 908 |
| expr.null_operand_swap | 226 |
| expr.update_ops | 142 |
| block.var_decl_reposition | 84 |
| block.if_flat_nest | 83 |
| expr.default_param_indexof | 61 |
| expr.predicate_loop_literal | 59 |
| block.if_swap | 56 |
| block.conditionals | 51 |
| expr.empty_size | 39 |
| id.naming_style | 25 |
| block.loop_stmt | 9 |

规则知识库 SHA-256：`2466a9c0fd6de72cd7fb02fb9fae18aa3e1f6977a5d2983b3e2c641756619837`。

### 6.5 归档的 exact prompt

System prompt（SHA-256 `0ba49fe718fa9e6714c0af61ff1d428d7d693d2c023d968ad59995c6b752860c`）：

~~~~text
You are performing a source-to-source robustness transformation for a code-watermark experiment.

Your goal is to weaken source-level watermark carriers while preserving the program's externally observable behavior as much as possible.

STRICT REQUIREMENTS:
1. Preserve the function signature, return type, parameters, exceptions/throws contract, and externally visible API.
2. Do not delete required computation, add new I/O, add logging, add network/file access, or intentionally make the program fail.
3. Apply only transformations justified by the retrieved RULE CARDS below. If a rule's preconditions are not clearly satisfied, skip that rule.
4. Do not invent library methods, types, identifiers, imports, or APIs that are not already available in the source.
5. Preserve variable binding and scope. Avoid identifier collisions and reserved keywords.
6. Preserve evaluation order and side effects. In particular, do not duplicate or remove side-effecting expressions.
7. Keep the output in the same programming language as the input.
8. Prefer multiple safe rewrites within the requested channel when feasible, but semantic preservation has priority over attack strength.
9. Return no explanation outside the required output format.

OUTPUT FORMAT:
<applied_rules>comma-separated RULE_ID values actually used, or NONE</applied_rules>
```{language}
<transformed source code only>
```
~~~~

User prompt template（SHA-256 `7477cab12947469b091c5091d1b0e29ae09ec11af3d7fdb140166520b3fed07d`）：

~~~~text
REQUESTED_LANGUAGE: {language}
REQUESTED_CHANNEL: {channel}
RANDOMIZATION_SEED: {seed}

RETRIEVED RULE CARDS:
{rule_cards}

SOURCE CODE:
```{language}
{source_code}
```

Rewrite the source code using only safe, applicable retrieved rules from the requested channel. If no retrieved rule can be applied safely, return the original source unchanged and use <applied_rules>NONE</applied_rules>.
~~~~

每条实际 prompt 的 SHA-256、检索到的 Rule IDs、模型返回 ID、finish reason、token usage 与 sample seed 均写入对应 JSONL 的 `attack_meta`。

### 6.6 实现模块与数据流（给论文附录/Artifact 说明）

1. `training/SrcMarker_fresh/train_main.py`、`experiment_config.py` 与 `run_one_fresh_training.sh`：从随机初始化训练并写出 checkpoint、逐 epoch history 和 run manifest。
2. `training/SrcMarker_fresh/eval_main.py`：对 test split 生成带水印代码，并记录 `watermark`、clean `extract`、原始代码和水印后代码。
3. `project/srcMarker/SrcMarker/1_obfus.py` 与 `rq2_revision/rule_attack.py`：执行确定性规则攻击、语法检查与状态记录。
4. `prepare_fresh_llm_cohorts.py`：按共享原始程序建立双方法配对 cohort，并在 API 调用前完成长度/语法筛选。
5. `rq2_revision/rag.py`、`llm_rag.py`、`llm_provider.py` 与 `1_obfus_AI.py`：完成规则检索、prompt 组装、Chat Completions 调用、输出解析、语法验证与 resume 写盘。
6. `validate_mbxp_rq2.py`：在 MBCPP/MBJP/MBJSP 上进行 baseline qualification、攻击、编译/执行和测试比较，计算 EPR。
7. `run_watermark_detector_portable.py`：加载每格 checkpoint 的 extractor encoder/decoder；只对 `valid_attack` 产生 attacked prediction，显式保留 syntax-invalid/no-op/error 行。
8. `3_analysis.py`：计算 clean/attacked BAR、MAR、ΔBAR、coverage 与样本级 paired bootstrap CI。
9. `run_llm_full_1000.py`、`run_llm_full_detection.py`：固化 1,000 次生成和八格 checkpoint 检测协议；`build_rq2_deliverables.py` 与 `plot_rq2_results.py` 仅从归档结果构建报告、表格和图。

逐样本 LLM JSONL 的核心字段为 `_attack_uid`、`watermark`、`extract`、`after_watermark`、`after_obfus` 和 `attack_meta`。`attack_meta` 至少包含 attack family/channel/language、global/sample seed、source/prompt SHA-256、changed/syntax/status、retrieved/reported/unknown rule IDs、generation parameters、attempt count，以及 provider response ID/model/usage/finish reason。检测后增加 `obfus_extract` 与 `detector_status`。

## 7. 关键复现命令

```bash
PYTHONPATH=.deps pytest -q
PYTHONPATH=.deps python run_llm_full_1000.py \
  --env-file /secure/path/llm.env --workers 2
PYTHONPATH=.deps python run_llm_full_detection.py \
  --device cuda --gpus 0,1 --workers 2 --bootstrap 10000
PYTHONPATH=.deps python build_rq2_deliverables.py
PYTHONPATH=.deps python plot_rq2_results.py
```

训练命令由 `training/SrcMarker_fresh/run_fresh_training.sh` 和 `run_one_fresh_training.sh` 固化；规则攻击与完整 EPR 命令见 `README_REVISION.md` 及归档脚本。

## 8. 结果使用边界

LLM 主实验的“功能正确性”证据由独立可执行 MBXP pilot 提供；GitHub/CSN 主实验代码片段通常缺少独立测试夹具，因此主实验只对其进行 baseline/attack 语法筛选和水印检测。报告中应分别称为 execution preservation validation 与 main-task syntax/coverage accounting，避免将主实验语法有效率表述为执行语义正确率。
