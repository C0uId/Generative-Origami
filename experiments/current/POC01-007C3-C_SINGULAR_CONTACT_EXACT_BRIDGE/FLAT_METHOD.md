# EXP-C3C-01 — Flat Singular / Local Chart Bridge

实现：`simulation/singular_bridge.py`；回归测试：`08_测试/test_singular_bridge.py`。

## 不变输入与运动定义

- 输入使用 C3-B 的 `repaired_source_knots.json`，只替换 source intervals 0–8 的构造。
- 共享端点不重新优化；构造末端与给定共享节点不一致超过 `2e-11` 时，返回无替换运动和明确失败原因。
- 9–69 不在本 builder 的合法 index 范围内。Dog、RRT、主路径和旧的 spherical/closure/CCD 模块不修改。
- 所有 panel/material point 都由 fold angles 经过原 rigid Rodrigues FK 求得。顶点弦仅作 CCD 误差界，不是实际运动。

## Flat 点的退奇异解析图

原三转轴因子分解令三个相邻 crease 的角度依赖其余自由角。自由角仍作为局部 chart 的坐标，来源于既有两个共享节点。固定轴位于参考平面，所以 flat 处的 acos argument 有结构恒等式

\[
x(0)=1,\qquad x'(0)=0,\qquad 1-x(t)=t^2 h(t).
\]

实现不在近 1 的两个浮点数之间相减来恢复 h。它先对自由转轴 exponential product 作阶数 18 的矩阵 Taylor 系数卷积，并对每个系数向外舍入；完整 analytic series 被每个阶次的显式 exponential remainder 包围。若自由角绝对变化之和为 F，则

\[
|x^{(k)}(t)|\le F^k/|A|,\qquad 0\le t\le1.
\]

这给出 h、h'、h'' 全区间尾界。整段证出 h>0 及 asin argument 的严格域后，使用

\[
\beta(t)=\operatorname{sign}(\beta)\,2\arcsin\!\left(t\sqrt{h(t)/2}\right)
\]

求依赖角。它在 t=0 具有有限一、二阶导数，没有原 acos 图的 `1/sin(beta)` 发散。alpha、gamma 使用同一 3R 因子分解的 atan2 图，并显式证明 projection 范数与 atan2 半径下界、排除分支切线。

数学运动定义是隐式的理想 analytic branch，h=(1-x)/t² 并在 flat 处解析延拓；不是 finite polynomial 定义的替代轨迹。运行中 `q()` 用有限 Taylor 系数中心近似 h，只承担具有显式误差界的数值 evaluator。它与理想 analytic h 的误差不会被隐藏：系数中心误差、Taylor 截断、Horner 舍入，经过 h→beta→alpha/gamma→rotation product 的导数界，加入整段 closure upper bound。故“理想解析恒等式”和“浮点实现误差”分开记录。低阶、大自由角测试专门验证 truncation 会阻止闭环通过。

所有使用 evaluator 端点/中点来收紧的 joint bounds 都加入完整 evaluation error；vertex bounds 同样加入完整材料点评估误差。供 CCD 使用的 chord error 不是仅有曲率项，而是 `acceleration*duration²/8 + endpoint_evaluation_error`，确保 ideal 曲线相对数值端点 chord 的偏差被包围。`exact_closing_hinge_certificate()` 只对 ideal factorization 的结构恒等式作声明，明确 finite Taylor evaluator 不是数学运动定义，且不由“小闭环残差”推导 exact seam。

本模块另限制完整材料点评估误差不超过 `1e-8`（现 conservative CCD 默认 transverse-witness guard）。超出时 closure 和 exact-seam gate 均返回 `EVALUATOR_ERROR_EXCEEDS_COLLISION_WITNESS_GUARD`。若调用方降低 CCD witness guard，必须同步降低 config 的 `max_point_evaluation_error`；不能泛称任意配置皆可通过。

## Null-space、弧长与高阶延拓

Flat 的 crease-axis Jacobian rank=2、nullity=6。构造记录来源方向在 null-space 上的 mode seed，并记录解析图在原点的实际 tangent、`J tangent` 误差和 arc length unit tangent。由 interval jet 的 q'、q'' 得到二阶 arc length predictor

\[
q_{ss}=(q''-T(T\cdot q''))/\|q'\|^2.
\]

实际连续运动采用高阶退奇异 analytic chart 参数 t；没有声称采用精确等弧长时间参数。每一 cell 的弧长上下界来自整段 q' interval 范数乘参数宽度，不来自离散 chord sum。Mode/tangent 的数值诊断也不构成认证。

Intervals 1–8 离开 flat 后使用 regular 3R local charts，以 interval automatic differentiation 同时包围每个角、速度和加速度。若整段图的域/分支/角域不能证明，则只细分 chart 的参数范围，不改变两个源端点，也不插入 q-linear rigid motion。

## 整段证据与 CCD protocol

每一保留的 cell 提供：

1. `continuous_closure()`：结构恒等式、显式有限 series 误差传播、rotation / seam gap 上界。
2. `joint_bounds()`：每角范围，导数单调性可把 flat 的数学端点 0 保留为精确单侧界，避免人为 epsilon 缺口。
3. 一、二阶 interval jets：角速度/加速度；panel point 的 `speed_bound()`、`acceleration_bound()`、chord error、vertex bounds。
4. 28 panel pairs 的全材料 z-gap 保守包围，明确标为 `BOUND_ONLY`。该粗界不单独证明接触合法，不授予面片豁免。
5. `exact_closing_hinge_certificate()`、`fixed_joint_values` 等旧 conservative CCD 所需 protocol。

证明图失败、角域失败、尾界过大、端点 join 失败均保留具体参数区间和原因。builder 不回退到 q-linear；由总控决定是否保留并明确标注 B 的有限容差 fallback。

## 数值范围与结果使用

本实现与旧 reference backend 的数值定位一致：nextafter 向外舍入 + 明确的 libm/FK floating reference guard。它不是经过验证的 directed-rounding transcendental 库，不能报告为机器形式化证明。整段界是解析/interval 构造；测试中的离散评价只用于回归检查。

修正完整 ideal/evaluator contract 后，独立重新认证 intervals 0–8 的 cell 数分别为 `[1,43,24,16,11,8,8,8,8]`，共 127 cells；9 个 source intervals 全部 conservative CCD PASS、COLLISION=0、UNCERTAIN=0，closure 9/9 PASS，最大 continuous closure upper bound 为 `9.533072279507542e-9`，全程共享节点 join 通过。结果在 `flat_recheck/interval_000.json` 至 `interval_008.json`，配置、输入及模块哈希在 `flat_recheck/metadata.json`，耗时 50.53 秒。该局部结果不替代总控对全部 162 区间的最终门禁。

新增测试 9 项覆盖：flat 奇异点有限导数、严格角域、闭环与材料刚性、导数/几何包围回归、禁止弦插值、mode/弧长诊断、深度耗尽 fail closed、Taylor 尾项阻止闭环认证、禁止覆盖失配源端点、保护 9–69 和无效输入。