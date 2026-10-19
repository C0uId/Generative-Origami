# C3-C 最终接触证据结构独立复核

复核日期：2026-10-18。范围为本轮 fresh run 的全部 162 个独立区间证书，包含 160、161；不沿用上轮未完成输出的统计。本复核只读取证书、源文件和运行快照，重新验算证据结构及接触模式合并，不重新运行几何求解，也不使用离散采样判断连续安全。

## 实际覆盖与结论

| 项目 | 独立复核结果 |
| --- | --- |
| 源区间 | 162 个，连续编号 0–161 |
| 区间状态 | 71 PASS、0 COLLISION、91 UNCERTAIN |
| 显式运动单元 | 574 个：257 PASS、317 UNCERTAIN |
| 成对证书 | 16,072 个；每个运动单元恰有 28 个不同 panel pair |
| 成对树节点 | 50,830 个；完整时间覆盖、子树接续及 PASS 下层状态检查均无错误 |
| 连续闭环 | 所有单元的已保存连续上界有限、非负且不超过原容差 `4e-6` |
| 顶点运动 | 所有单元均明确 `uses_vertex_linear_interpolation_as_motion=false` |
| 保护中段 | 9–69 共 61 个完整 plan 的 canonical JSON SHA256 与 C3-B 逐一相同 |

本轮仍未取得整体连续认证；没有用材料审计的 PASS 或闭环 PASS 覆盖未定的成对 CCD。区间 161 保留有限容差诊断运动与 exact endpoint bridge 未证明标记。

0–8 的 Flat 区间全部由本轮修复后的代码 fresh 重算：已核对哈希绑定的实际运行 driver，它对每个区间调用新的 `FlatSingularBridgeBuilder.build_interval`，并对发出的全部 127 个单元重新调用连续检查器。没有读取 `flat_recheck` 或其他 prepared PASS 证书替代此次计算。9 个区间均为 exact bridge PASS、整体区间 PASS。

## 材料模式合并与世界 z 诊断

共有 318 个 Goal chart 单元保存接触模式合并。对每个单元，使用其底层完整成对连续证据和保存的 `original_material_audit` 重新调用当前 `merge_contact_modes`，全部 318 个返回值与存储值的 canonical JSON 完全相等。

- 原始世界 z 材料审计全部保留，318 个原始审计均为 UNCERTAIN，其中保存了 8,076 对负下界诊断；没有删除不利数据。
- 每个合并结果均包含明确的 `scope_correction`，并记录 `world_z_goal_order_used_as_gate=false`。对已经严格分离的 FREE 状态，不错误要求最终材料对应点在世界 z 中排序。
- 合并结果包含 3,834 对 FREE、1,916 对真实 TOPOLOGICAL_HINGE、628 对持续 CONTACT、942 对 MATERIAL_HINGE，以及 1,584 对 UNKNOWN。以上为各运动单元内的 pair 计数，同一 pair 会在不同单元重复出现。
- 只有第 70 区间的两个 Goal 单元获得完整合并 PASS；其余 316 个 Goal 单元仍 UNCERTAIN。两个 PASS 单元均通过新 `audit_goal_contact_evidence` 的独立 fresh merge 和完整字段一致性检查。
- 所有接受的 induced material hinge 都由已知证明结构约束：前向相对链、唯一可变真实关节、严格角域、有限材料 barycentric patch、映射误差界、层序 ranks、包含整个 patch 的三角形上非负仿射系数，以及基于原点/同一折痕索引的结构零。单纯材料轴线身份不能跳过单侧层序证据。
- 未知 PASS 原因、未知/未定下层状态、缺失材料或层序证据、缺失时间覆盖均维持拒绝。缓存的顶层 PASS 不是单独的证明依据。

256 个单元没有 Goal mode audit，其中包括非 Goal 阶段及 161 的未认证诊断 fallback；没有因此将 Goal fallback 授予 PASS。

## 源码与运行证据一致性

`run_provenance.json` 标记计算完成。实际生成成对证明和接触模式的五个模块，以及纯查询缓存模块，其当前 SHA256 均与运行记录一致：`continuous_ccd.py`、`singular_bridge.py`、`contact_bridge.py`、`contact_separation.py`、`contact_gate.py`、`motion_cache.py`。

当前 driver 与保存的 `run_driver_snapshot.py.txt` 有已核对的差异：增加 `certification_evidence` 导入，把最终 Goal 门禁从读取合并 PASS 标签加强为重新验证底层完整证据，并在后续运行的 provenance 中跟踪该验证模块。该差异没有修改本轮运动构造、几何计算或成对证书生成逻辑。运行时 driver 快照和原 SHA256 均保留，没有回写冒充本轮已运行代码。

`post_run_gate_audit.json` 中的原始 driver、当前 driver 和新 validator 哈希均与文件一致，记录的全部 162 个区间文件 SHA256 也逐一一致；门禁加强后没有替换任何区间证据。最终自动测试日志为 112 项通过。

逐项数据、61 个中段 plan 哈希、模块哈希和完整计数保存在同目录 `final_contact_schema_audit.json`。本次复核未发现结构或统计错误；其保证限于证据结构与已有 reference 证明的使用一致性，不等同于形式化任意精度几何证明或原生 Tight-Inclusion 实测。