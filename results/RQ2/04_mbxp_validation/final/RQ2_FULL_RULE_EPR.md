# RQ2 全量规则攻击 EPR 验证

EPR 在 baseline 测试通过、攻击实际改变且语法有效的样本上计算：`post_pass / syntax_valid_changed`。三个可执行基准的全部样本均参与测试，四个攻击通道分别运行，seed 固定为 42。

| 数据集 | 语言 | 通道 | 总样本 | baseline pass | changed | syntax-valid changed | post-pass | EPR |
|---|---|---|---:|---:|---:|---:|---:|---:|
| MBCPP | C++ | id | 764 | 763 | 763 | 763 | 756 | 99.08% |
| MBCPP | C++ | expr | 764 | 763 | 763 | 763 | 763 | 100.00% |
| MBCPP | C++ | block | 764 | 763 | 763 | 763 | 754 | 98.82% |
| MBCPP | C++ | all | 764 | 763 | 763 | 763 | 748 | 98.03% |
| MBJP | Java | id | 842 | 842 | 842 | 842 | 834 | 99.05% |
| MBJP | Java | expr | 842 | 842 | 842 | 842 | 842 | 100.00% |
| MBJP | Java | block | 842 | 842 | 842 | 842 | 835 | 99.17% |
| MBJP | Java | all | 842 | 842 | 842 | 842 | 829 | 98.46% |
| MBJSP | JavaScript | id | 797 | 795 | 788 | 788 | 761 | 96.57% |
| MBJSP | JavaScript | expr | 797 | 795 | 788 | 788 | 781 | 99.11% |
| MBJSP | JavaScript | block | 797 | 795 | 788 | 788 | 781 | 99.11% |
| MBJSP | JavaScript | all | 797 | 795 | 788 | 788 | 760 | 96.45% |

跨 12 个实验单元的加权 EPR 为 **98.66%**（9444/9572）。逐样本输出、失败阶段、运行环境和 SHA-256 校验值见 `rq2_full_rule_epr.json`。

主实验数据集按语言使用执行有效性证据：GitHub-C→MBCPP，GitHub-Java/CSN-Java→MBJP，CSN-JavaScript→MBJSP。GitHub/CSN 本身没有可执行测试套件，因此不将 Tree-sitter 语法有效性表述为逐条功能正确性。
