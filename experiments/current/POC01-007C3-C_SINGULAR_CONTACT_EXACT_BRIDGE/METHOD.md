# C3-C 方法与证据范围

本轮从经 SHA256 与630文件清单复核的 C3-B 完整包继续，在独立目录实现。原始163帧、C3-A/C3-B证据和旧规划器均保留。未重新运行Dog生成或RRT，也未启动Sequence Planner。

## 固定中段

使用B的共享修正节点与完整plan重建9–69原曲线，包括球面3R dependent顺序、父曲线端点和每个时间限制区间。节点9..70逐值冻结，全部61个plan的canonical JSON SHA256必须相同。重建后逐区间重新调用同一保守CCD，不直接沿用旧PASS标签。

## Flat与Goal

- [Flat奇异消元、null-space与高阶局部图](FLAT_METHOD.md)。解析图的理想闭环身份与实际有限Taylor求值误差分开记录，尾界和角误差传播必须落入声明的reference容差。
- [Goal接触active-set、共享节点修复与局部图](CONTACT_METHOD.md)。FREE/CONTACT/RELEASE、材料映射、层序、signed gap、事件时间包络和切换后切空间记录在plan和whole_interval_bounds中。

接触端仅允许统一修正71..161的共享节点，每个修正记录原值、新值、delta、采用坐标图和切空间。禁止在相邻区间私自使用不同端点。节点162保持Goal。

## 全量连续认证

每个显式运动单元以刚性Rodrigues FK求值，不对世界顶点线性插值。每个单元分别通过整段角域、连续闭环、速度/加速度包络与28个panel pairs的保守认证。原有certifier使用swept AABB、曲线运动包络、cone separation、vertex-face/edge-edge CCD及有限材料patch证明。

导数证据分两层：`whole_interval_bounds`记录8片面板所有材料点的速度/加速度上界；`plan.cells[*].regularity`记录折角导数。Flat含每关节interval jets；正则3R图的dependent speed L2 / acceleration L1上界也分别约束每个dependent分量，自由角为明确的线性图坐标。导数时间单位为归一化cell或记录的父图参数；源区间换算按cell参数宽度及其平方进行。

线性顶点弦只作为带曲率膨胀余量的保守检测代理，不能作为真实运动。曲线刚体轨迹与保守线性CCD代理的区别见[原始Rigid-IPC研究](https://ipc-sim.github.io/rigid-ipc/)。

全部162源区间必须连续覆盖，每个局部图拼接通过，所有原始gate通过，两端exact构造通过且每个Goal单元的active-set材料signed-gap审计通过，才能升级。`raw_ccd_counts`只记录原CCD的结果；`counts`还包含C3-C的exact构造/接触证明门禁。两者不能互相替代。

无法构造精确桥时，仍对显式标记的有限容差刚体FK诊断运动进行CCD，以保留失败panel pair、子区间和深度。该区间额外记录`EXACT_ENDPOINT_BRIDGE_NOT_PROVEN`；其有限容差闭环通过不能继承精确接缝身份。

## 文件与复现

- `interval_certificates.json`与`certificates/interval_000.json`至`interval_161.json`：源区间、图、接触状态、全时间包络与28pair证据。
- `remaining_failures.json`：未定/碰撞的具体源区间、局部时间、源时间、panel pair、叶节点原因、feature原因与深度。
- `endpoint_knot_repairs.json`和`middle_integrity.json`：允许范围内的修正与保护中段的完整性。
- `EXP-C3C-01_FLAT_SINGULAR`、`EXP-C3C-02_GOAL_CONTACT`、`EXP-C3C-03_CERTIFICATION_RERUN`：分实验结果。
- `test_output.txt`与`console_output.txt`：实测日志。

数值保证范围为带显式guard的条件float64/reference界；不是对平台libm实现完成形式化证明的任意精度区间算术，也未运行原生Tight-Inclusion。无限小mode、离散continuation节点和自动测试均不能单独构成整段认证。

独立审查与文献见[design_audit.md](design_audit.md)。最终实测结论以[report.json](report.json)与[162区间表](INTERVAL_SUMMARY.md)为准。