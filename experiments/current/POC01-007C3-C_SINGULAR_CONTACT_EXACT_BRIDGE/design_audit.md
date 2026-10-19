# C3-C 独立设计审计

审计日期：2026-10-18（Asia/Shanghai）。审计对象是 `singular_contact_motion.py`、`simulation/singular_bridge.py`、`simulation/contact_bridge.py`、原有 conservative CCD 及升级门禁。本文件记录独立代码审查和局部回归验证；最终区间结果以同目录 `report.json`、`interval_certificates.json`、`remaining_failures.json` 为准。

## 已核实的基线与保护范围

- C3-B 报告为 162 个 source intervals：PASS=61、COLLISION=0、UNCERTAIN=101，continuous closure=162/162 PASS；源 keyframes SHA256 为 `c25ac604c1f4c90f0d44734370313967f2e333309c6bffcc3c52d6e37199be1d`。
- 9–69 的完整 B plan 使用 canonical JSON SHA256 比较；重放采用原 parent endpoints、dependent chart 和 cell time restrictions。节点 9–70 逐值保持，包含受保护区域两端的连接节点。
- 保护依据是运动定义和端点一致性，不能只比较 PASS 数量。中间 61 个 plan 的重放回归独立通过。
- C3-B `MaterialContactValidator.patches` 实际包含全部 28 个 panel pairs；20 对的列表属于 `LayerContactModel.samples_by_pair` / 非邻接 final-contact list。C3-C 新材料 patch 模块构造全部 28 对，不应把这个区别描述为旧 CCD 漏查了 8 对。

## Flat bridge 的证明链、审计修复与最终语义

`LocalChartMotion` 的数学运动定义为理想隐式 analytic 3R 曲线：`h(t)=(1-x(t))/t²` 在 t=0 连续解析延拓，`1-x(t)=t² h(t)` 消去 flat endpoint 的 acos 一阶分母奇异性。h、h′、h″ 由高阶系数区间与解析指数尾界包络；interval jets 生成理想 joint angle、velocity、acceleration 及 rigid-FK point bounds。null-space seed、单位弧长 tangent、二阶 predictor 是构造诊断，不是连续认证。实际构造使用高阶局部 chart，并未宣称已经以弧长变量执行完整数值 continuation。

审计提出的第一项问题是有限 Taylor 系数中心求值的误差未显式传播。修复后的 `_flat_evaluation_error` 包含系数中心误差、Taylor 尾项、Horner 舍入，再经 beta 对 h 的导数界、alpha projection norm、gamma atan2 radius 传播为三个角及 cyclic rotation-product 的误差界。

审计进一步区分了有限多项式实际曲线与理想解析曲线：小但非零的 finite-polynomial closure residual 不能建立 shared-hinge 恒等式，不能据此沿用 exact seam 身份。最终补丁选择明确的 ideal/evaluator 契约，`q()` / `triangle()` 只是理想曲线的有界数值求值器，有限 Taylor 不是另一条数学运动。为使所有证明路径一致，最终代码已同时修复：

1. `joint_bounds` 以完整 evaluator error 保护中点/端点数值收紧，替代仅固定 `16e-12` 的余量。
2. Flat 专用 `chord_error_bound` 在 ideal acceleration 曲率项之外加入完整 point evaluator error；现有 feature CCD 将两面板的该余量相加，因此 numerical endpoint chords 也包住 ideal 轨迹。
3. `vertex_bounds` 的完整 evaluator guard 保留；其余量与新增 chord 余量部分重叠只会增加保守性。`exact_closing_hinge_certificate` 明确依据理想 analytic dependent-product 恒等式，并分列求值误差；不依据 finite-polynomial residual 小而授予拓扑身份。

最终补丁只在 `singular_bridge.py` 的专用 motion override 中改变行为，不改变受保护中段或 Goal 的既有基类计算。因此完整 162 区间初次认证后，`tools/recertify_c3c_flat.py` 必须以最终代码重新运行所有 0–8 区间，替换完整 certificates 并重新聚合最终报告；9–161 的完整 certificate JSON 通过前后 hash 比较保持不变。是否完成该复算及实际计数以 `flat_bound_audit_repair.json` 为准，不能使用旧 Flat PASS。

这些包络沿用项目的 reference arithmetic 范围：基本区间运算采用 outward nextafter，并对 host libm / rigid FK 使用声明的浮点 guard。它们不是任意精度、形式化验证的 directed interval libm 证明。无法建立正 h、反三角分支、strict M/V sector、finite derivative bounds、受支持的 evaluator error 或端点连接时，builder 返回明确失败，不输出新的 q-linear 替代曲线。
## Goal contact 的安全性审查

- 每个有限 goal-overlap polygon 的顶点保存两片材料上的 barycentric coordinates，signed gap 是该有限材料 patch 上的仿射函数，因此顶点区间界可覆盖 patch。
- `contact_pair_certificate` 只接受严格固定的 generating joint subchain，逐值等于 goal；公共左旋转乘积消去后，相对 Rodrigues product 恒定。这证明有限材料接触的对应关系和零间隙，不是依据 pair 名单或近零采样 gap 豁免整片面板。
- FREE/CONTACT/RELEASE 事件隔离目前覆盖 linear free chart coordinates 的 crease-boundary 根；persistent boundary contact 使用恒定坐标恒等式。nonlinear dependent boundary event 没有由端点相等推断为已隔离，不能证明时拒绝该 chart。此实现不宣称完成任意非邻接材料 gap 的通用根隔离器。
- active set 更新后记录重新计算的约束 Jacobian/null-space tangent 与 local chart；这些局部诊断仍不能替代 whole-interval contact 和 CCD。
- signed gap 的失败独立保留。即使 raw conservative CCD 全部 PASS，Goal cell 的 active-set material-gap/event audit 未通过也不得升级，根因记录为 `ACTIVE_SET_SIGNED_GAP_OR_EVENT_NOT_PROVEN`。

## CCD 与最终升级条件

真实几何始终由 hinge angles 和 Rodrigues FK 计算。线性 vertex chords 只作为带 rigid curvature inflation 的 CCD surrogate；它们不是 rigid motion 本身。所有 28 对面板的 pair status 均需通过，shared origin 仅按同一精确材料点处理，不允许有限半径的任意穿透豁免。

最终门禁重新聚合底层 cell evidence，要求同时满足：162 个连续、唯一且完整的 source intervals；全部 cells/pairs/strict sectors/continuous closure/coverage/joins PASS；closure upper bound 不超过 4e-6；8 片面板均有 finite nonnegative speed 和 acceleration bounds；exact closing-seam evidence PASS；端部 exact-bridge construction 通过；Goal active-set signed-gap/event evidence PASS；受保护中段不变。任一个 UNCERTAIN、遗漏证据或有限容差 fallback 均阻止升级。

若 exact candidate 构造失败，runner 可以保留并重新认证早先明确声明的 finite-tolerance rigid-FK motion，以便如实记录失败区间；该保留动作不会让 fallback 继承 exact 身份，也不会因为离散帧或 closure 容差通过而升级。未满足全门禁时不得启动 Sequence Planner。

## 独立验证

- `test_singular_contact_integration.py`：独立运行 9/9 PASS，覆盖保护区域重放、缺失/重复 source interval、隐藏的 unknown pair、closure 未证、finite-tolerance endpoint、断连接、缺失/非有限导数、缺失 exact seam、vertex interpolation 和未证明的材料 gap 阻止升级。
- `test_singular_bridge.py`：理想曲线/evaluator 三项补丁后独立再次运行最终 9/9 PASS，覆盖 flat endpoint、解析/数值闭环与材料距离、全区间 angle/derivative/vertex bounds 的回归、无 epsilon hole、端点 mismatch、拒绝 q-linear replacement，以及低阶大自由角的 Taylor 尾界显著超过算术 guard 时阻止闭环通过。采样仅用于回归发现错误，不构成上述连续证明。
- 全部 162 区间的本次执行结果与完整自动测试汇总须结合最终报告读取；单元测试成功本身不等于连续路径已经认证。

## 适用方法的原始资料

1. Dickson, Kelley, Ipsen, Kevrekidis, *Condition Estimates for Pseudo-Arclength Continuation* (2007)：增广 Jacobian 的非奇异结论需 regular points / simple folds 等假设，不能直接套用于 flat 多维分叉。[作者提供的论文](https://ipsen.math.ncsu.edu/ps/sinum65438.pdf)
2. He and Guest, *On rigid origami III: local rigidity analysis*：first-order flex 与高阶兼容/实际 rigid foldability 需要区别，null-space 方向本身不足以证明有限连续运动。[原文全文](https://pmc.ncbi.nlm.nih.gov/articles/PMC8826367/)
3. Ferguson et al., *Intersection-free Rigid Body Dynamics* (2021)：curved rigid trajectories 的保守窄相位可归约为带 minimum-separation 的 linear CCD queries；这支持项目的 curvature-inflated surrogate 使用范围。[作者项目页与论文](https://ipc-sim.github.io/rigid-ipc/)

