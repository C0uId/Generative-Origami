# C3-C 独立接触证明复核

日期：2026-10-18。范围为新增 `contact_separation.py`、`contact_gate.py`、continuous CCD 的 contact provider hook、总控中的模式合并和最终证据门禁。未修改本轮正在执行的 driver、运动定义或几何模块。

## Forward induced hinge

对 i<j 的 forward 相对乘积，令 `R_i^T R_j = B R_u(q) A`，其中 B、A 均由逐值固定在 Goal 的原始转轴半转组成；所有轴仍各自保留。把 anchor 与 target 的材料点变换到实际单变量轴的坐标系，分别为 `x=B^T x_i`、`y=A y_j`，与代码 row-vector 形式一致。固定半转只反射平面并翻转法向，不引入另一条近似轴。

整段 `0<|q|<=pi` 的角界排除 unfolded coplanar 状态。中间角时两平面的交线只有实际轴 u；这条轴上的材料点在 q 和 Goal 半转下都保持不动，因此实际允许的有限交线材料点也在 Goal 相对位姿重合。pi 端点允许的面积重叠必须对应明确的有限 Goal patch。此规则不能推广到多个可变 joint，也不能借 candidate 的 exact cyclic closure 推定输入 Goal 也精确闭合；实现正确地保持 forward-only。

仅有轴材料对应并不足以排除沿轴的横穿。实现另证整个 anchor 或 target containing triangle 的线性 signed-gap 系数非负且至少一个非原点系数严格正。有限 Goal overlap patch 是该三角形的子集，所以同一不等式覆盖整个材料 patch；对所有中间角，整个 containing triangle 位于另一平面的同一侧，也排除了跨轴横穿。

独立推导两种系数得到同一符号：target 使用 `-rank_sign*(-1)^i*sign(q)*(B*(u cross y))_z`；anchor 使用正号及 x。这与 `_induced_layer_halfplane` 一致。`(-1)^i` 是 Goal anchor 法向在其材料坐标中的精确半转奇偶性。此处为随材料坐标运输的层序，不是任意时刻的世界 z 排序。

结构零仅授予精确 origin，以及通过原始 crease index 确认的实际轴端点：anchor 还要求变量 joint 是链首，target 要求其为链末。其余即使数值上近零，也必须减去完整 guard 后非负。当前三个有效 forward pairs `(1,3)`、`(2,4)`、`(5,7)` 均满足该证明；反转 layer ranks、取消固定 joint、加入 unfolded endpoint、把近轴当同轴的负例均被拒绝。

## Relative frame cone 与 scope correction

公共左 FK 乘积先按代数消去，再用每个 joint 的全区间角界构造 interval Rodrigues matrix product，包围 target 在 anchor 材料坐标中的全部顶点。LP 只提出一个 plane normal；PASS 来自静态 anchor 两条非中心射线的严格正下界与 target 两条射线的整段严格负上界。原点是精确共同材料点，没有删除任何有限半径球。若走 complementary chain，必须先有本运动的 exact cyclic identity；此 FREE 证明不需要输入 Goal 的 cyclic identity。

模式合并仅移除了已由整段证明分离的 facets 上错误施加的世界 z Goal 对应点排序。FREE 需被识别的完整连续分离证明；结构 hinge 需正确 joint、角域和必要的 exact seam；pi 端点和 persistent area contact 仍需有限材料 patch 和 layer ranks。Induced material hinge 同时需要上述 unilateral layer 与有限材料映射。未知 proof reason、未覆盖的时间子区间、未知 pair、仅有轴身份、实际 persistent CONTACT 与 FREE 冲突均保持 UNCERTAIN。没有用旧 material audit 的 PASS 挽救 unknown CCD。

本模块是受信任几何 producer 的证据 schema gate，不是可对任意伪造字段独立重做几何的验证器。Producer 的 M/V layer-order admissibility、motion 的完整 joint bounds、固定 joint 恒等式和 reference 浮点 guard 仍是声明的前提。

## 最终门禁加固

复核发现原 `final_gate` 对已存 active audit 仅检查顶层 PASS，无法拒绝残缺的缓存模式证据。新增独立 `simulation/certification_evidence.py`：从 cell 的完整连续 pair proofs 与保留的 `original_material_audit` 重新执行 `merge_contact_modes`，要求 fresh PASS、唯一完整 pair coverage，并要求已存 active audit 与 fresh merge 的完整规范结构一致。拒绝仅 PASS 标签、缺失原始 audit、少 pair、重复 pair、未知 leaf、被编辑的 mode segment 和非有限数据。没有为本轮计算引入新的几何判据。

独立 helper 与测试已完成；root 在完整数值 run 结束后接入 driver 并对现有证书重聚合，以保持该 run 的模块 snapshot 不变。最终交付应保留数值 run provenance 与门禁校验补丁的独立记录，不能把新 schema gate 冒充数值轨迹重算。

## 独立验证与结论

- `test_contact_separation.py`：8/8 PASS（0.651 秒）。
- `test_contact_gate.py`：11/11 PASS（0.317 秒）。
- `test_certification_evidence.py`：6/6 PASS（0.010 秒）。
- 更新有效 schema fixture 后，`test_singular_contact_integration.py`：9/9 PASS（4.746 秒）。

代码审查与上述回归未发现当前实际输入、默认配置下新增几何 false-PASS 路径。结论仍限于项目声明的 conditional float64 reference arithmetic：outward rounding 加明确 libm/FK guards，不是形式化 interval libm 或原生 Tight-Inclusion 证明。最终路径仍以全部 162 区间和精确端点等全部门禁为准；本独立复核不授予路径认证。