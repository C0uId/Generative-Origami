# Goal contact active-set bridge：实现、证据范围与剩余限制

> 本文件保留初始 active-set 原型的方法记录。本轮最终验收采用 [CONTACT_MODE_SCOPE.md](CONTACT_MODE_SCOPE.md) 的状态适用范围：已证明分离的 FREE 面片不再额外要求世界 z 排序，实际材料接触仍需完整的材料和层序证明。原世界 z 审计保留为诊断，不能单独当作碰撞或安全证据。

本阶段只处理源区间 70–161。节点 0–70 和终点 162 逐值保留；节点 71–161 在统一共享节点阶段修复，不在每个区间中各自修改端点。原 9–69 已认证运动的定义不变。没有重新运行 Dog/RRT。

## 1. 有限解析 chart atlas

`GoalContactBridgeBuilder` 优先使用 dependent triple `(0,1,2)`，必要时尝试另外七个连续 cyclic triple。三条 dependent crease 用球面 3R 因式分解求解，其余 crease 是声明的局部自由坐标。每个时刻都经 Rodrigues 刚性正向运动学求 panel，而不是插值顶点。

节点修复先把距 goal 边界不超过 `2e-8` 的角度写为同一个声明的精确边界角；优先选择不包含这些 active 关节的 dependent triple，再求共享解析 knot。每次修正保留 original、delta、correction norm、dependent triple、active joint，以及重新计算的 tangent/null space。修正预算为 `1e-3`；实际测试所见最大修正约 `1.9915944e-8`。受保护节点 9–70 和终点 162 不吸附、不投影。

每个候选 cell 必须有 whole-interval acos domain、无 branch cut、非退化投影、inverse Jacobian、angle sector、closure，以及相邻端点 join 的证据。无法证明则细分；深度预算耗尽后记录精确源参数区间和原因。模块本身不创建 finite-tolerance/q-linear fallback。主运行器为完整审计而保留的 fallback 仍必须标为 exact bridge 未证明。

## 2. 全区间 bounds

父球面 chart 提供 closure identity 的误差上界、角度范围、角速度和角加速度上界。材料点速度和加速度分别由 panel 半径乘整体角速度和 `angular_speed² + angle_acceleration` 上界得到。局部 cell 的速度乘 source parameter 宽度，加速度乘其平方。顶点 enclosure 和曲率膨胀使用完整时间区间，离散测试点仅用于软件一致性检查，不参与 PASS 决策。

这些证明继承已有球面实现的 conditional float64 reference guard。它们不是经过形式化验证的 arbitrary precision interval arithmetic，也不代表原生 Tight-Inclusion 已运行。

## 3. 材料对应与层序

`GoalMaterialContact` 为全部 28 个 panel pair 构造有限 goal overlap polygon，包括 8 对邻接 panel。每个 polygon 顶点记录两侧材料 barycentric coordinates、材料重建误差、有限三角形内的权重诊断和 layer rank。固定 layer order 为 `[7,6,5,0,4,1,3,2]`，并验证它满足 M/V 邻接层序约束。

**更正审计时的初步判断：原 C3-B 的 `MaterialContactValidator.patches` 已经有全部 28 对。只有 `LayerContactModel.samples_by_pair` 是 20 个非邻接 pair。因此本阶段没有“修复旧 validator 漏掉 8 对”的改动。**

CONTACT 的充分条件是 `fixed_joint_values[i+1:j+1]` 与 goal 折角逐值相同。此时公共左侧刚体旋转消去，两 panel 的相对 Rodrigues 乘积在整个区间恒等于 goal 相对姿态；所有有限 overlap patch 的同一材料点在整个区间重合，signed gap 恒为零，且没有相对侧穿越。等端点、近似相等、goal pair membership、某个采样 gap 为零，都不能触发该规则。规则保留有限 patch 及材料坐标，不提供整个 panel pair 的任意接触豁免。

其他 pair 用全区间材料点位置 enclosure，按 layer rank 对 `z_i(material)-z_j(material)` 作 interval signed-gap 计算。只有下界 `>=0` 才证明该材料 patch 的非穿透；含负下界即 UNCERTAIN。shared origin 只允许同一个精确材料顶点，不扩成忽略半径。此处 goal material patch 的 signed gap 也是额外约束，不能代替其余非接触区域的 conservative CCD。

## 4. FREE / CONTACT / RELEASE 与事件范围

- CONTACT：上述恒定相对姿态的材料 patch 证据。
- FREE：完整材料 patch signed-gap 下界非负，且没有已证明持续 active contact。
- RELEASE：自由 chart 坐标离开声明的 goal crease 边界，并且完整材料 patch 的 signed-gap 条件同样通过。离开边界本身不能豁免 gap 检查。

自由 chart coordinate 是声明的线性函数，其到达或离开 goal crease 边界的根可以解析隔离。每个这样的 active-set 切换记录旧/新状态、源时间点和重新计算 tangent/local chart 的要求。持续 active crease、每个局部 chart cell 的 active set 和新的约束 null space 均保存到 plan。

**事件证明的边界必须明确：可解析隔离的是自由 crease 的 goal-boundary root，不是所有材料点接触事件。** 非线性 dependent crease 在边界端点出现时，模块拒绝把等端点当事件证明。材料 signed-gap enclosure 无法排除零时，只输出涵盖该 cell 的保守未隔离事件 bracket；没有使用离散帧声称找到了精确 contact time。若本次运行器在最后一次 JSON 审计字段补充前已载入模块，该范围也由本说明文件约束；运动、bounds、状态和门禁没有改变。

## 5. 终点奇异与最终门禁

源区间 161 含全折叠 goal。当前有限 3R atlas 在该终点发生 projection/domain singularity，构造返回 `NO_JOINED_REGULAR_CONTACT_CHART`，逐 chart 保存失败原因。没有把终点强行写回 analytic curve，也没有按小残差获得 exact seam 豁免。

70–160 的部分/多数候选可以获得 exact closure 和严格 join，但 signed-gap bounds 或材料接触事件仍可能未证明。主运行器必须把这些问题保留为 `ACTIVE_SET_SIGNED_GAP_OR_EVENT_NOT_PROVEN`；raw CCD PASS 不代表最终源区间 PASS。只有 162/162 全部 source intervals 的 continuous closure、pair CCD、angle sector、joins、endpoint exact construction、材料接触门禁均通过，才能升级状态。

独立 contact 回归测试共 8 项：受保护节点不可变、共享修正预算、全区间几何 enclosures、有限材料接触对应、等端点反例、signed-gap 未证明不会被 closure PASS 覆盖、解析自由边界/未隔离 nonlinear event、奇异终点无 fallback。