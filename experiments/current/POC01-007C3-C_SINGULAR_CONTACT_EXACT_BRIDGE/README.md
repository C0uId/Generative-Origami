# POC01-007C3-C — Singular + Contact Exact Bridge

实测：**PASS=71 / COLLISION=0 / UNCERTAIN=91**；continuous closure {'PASS': 162}。状态 `CONTINUOUS_RIGID_PATH_NOT_CERTIFIED`。

9–69 原曲线及节点9..70完整保留；全部162个区间重新运行保守CCD。每个运动单元输出closure、angle、point velocity/acceleration、材料contact界；无法证明时保持UNCERTAIN。

自动测试：112/112 PASS。全路径精确流形声明：False。

复现（工程根目录）：

```powershell
python -m pip install -r requirements-research-lock.txt
python singular_contact_motion.py --backend reference
python -m unittest discover -s 08_测试 -p "test_*.py" -v
python tools/update_c3c_ledger.py
```

退出码0=全部连续门禁通过；2=审计完整运行但未认证；3=输入/构造/指定后端不可用。保留既有证据时使用 `--out 新目录`。

[162区间表](INTERVAL_SUMMARY.md)、[完整证书](interval_certificates.json)、[剩余失败与根因](remaining_failures.json)、[中段完整性](middle_integrity.json)、[节点修正](endpoint_knot_repairs.json)、[方法](METHOD.md)、[独立审计](design_audit.md)。

EXACT_ENDPOINT_BRIDGE_NOT_PROVEN 表示新精确构造未获接受；该区间重审的旧式运动明确为有限容差刚体FK，不是精确桥的成功结果。接触状态记录也不能替代连续非穿透证明。

本轮补充：[接触证明适用范围修正](CONTACT_MODE_SCOPE.md)、[实际状态对照](contact_mode_gate_correction.json)、[独立接触复核](independent_contact_review.md)、[固定Goal精确审计](independent_goal_halfturn_audit.json)、[端点复核](independent_endpoint_review.md)、[执行源码与配置](run_provenance.json)、[最终门禁复核](post_run_gate_audit.json)。

当前坐标和全π Goal 的精确半转乘积不是单位阵；这与4e-6容差闭环通过并不矛盾。本轮没有修改原几何或终态，不能把容差通过升级为严格端点身份。

[最终完整证据审计](final_contact_schema_audit.md) 已核验全部574个运动单元与16,072对证书。本轮较C3-B新增10个通过区间：展开端0–8，以及接触状态修正后通过的70。剩余71–161仍未认证。