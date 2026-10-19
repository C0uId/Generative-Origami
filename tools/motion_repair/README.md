# 教学折纸软件 — 可执行生成式 MVP

这是一个**可以直接运行**的端到端版本，重点是把产品链路和验证门禁先固定下来。

## 立即运行（无需安装第三方 Python 包）

要求：Python 3.10+

```bash
python run_demo.py
```

然后浏览器打开：

```text
http://127.0.0.1:8765
```

输入：
- 狐狸
- 长颈鹿
- 霸王龙
- 千纸鹤
- 玫瑰
- 咖啡杯
- 任意自定义文本

系统都会返回：
1. 语义分类；
2. 参数；
3. 生成的 `.fold` 候选；
4. 几何验证；
5. 教程 JSON；
6. SVG 折痕预览；
7. 网络教程兜底。

## CLI

Windows PowerShell：

```powershell
$env:PYTHONPATH="src"
python -m generative_origami.cli "狐狸" --out runtime_outputs
```

macOS/Linux：

```bash
PYTHONPATH=src python -m generative_origami.cli "狐狸" --out runtime_outputs
```

## 自动测试

```bash
python -m unittest discover -s tests/core -p "test_*.py" -v
```

## 重要：当前“生成”的真实含义

当前版本已经实现“任何搜索都能进入生成链路”，但只把结果认证到：

`LOCAL_SINGLE_VERTEX_RULES_PASS`

它不是“最终狐狸/霸王龙已被数学证明可以从一张纸刚性折出来”。

最高标准要求后续同时通过：
- 全局 flat fold / layer order；
- rigid path；
- loop closure；
- self-collision；
- human foldability；
- 真人拿纸验收；

才能升级为：

`VERIFIED_FINISHED_MODEL`

项目不会为了演示效果伪造这个状态。

## 项目目录

本轮基于原始 C2 ZIP 在独立目录继续研究，保留其中的演示、规划器和所有原实验。建议独立解压，不覆盖其他APP版本或原始ZIP。

## 刚性流形运动规划（研究功能）

安装研究依赖：

```bash
pip install -r requirements-research.txt
```

运行：

```bash
python plan_motion.py "狗" --mode layer-order --iterations 40
```

碰撞模式：
- `layer-order`：当前推荐。显式推断层序，Goal contact-mode prefix + 材料点级合法接触检查；Dog 当前生成约 163 个刚性关键帧。
- `strict`：把所有非相邻几何接触都当碰撞，主要用于诊断；flat-fold 合法层接触会被过度拒绝。
- `contact-aware`：C1 的旧研究模式，只做粗粒度 pair 豁免，不再作为推荐结果。
- `off`：只验证约束流形连通性。

`layer-order` 已明显强于旧 contact-aware，但最终最高认证仍需 POC01-007C3 的 continuous CCD。

## POC01-007C3-A 连续认证

在工程根目录执行：

```powershell
python -m pip install -r requirements-research.txt
python tools/certification/certify_motion.py --backend reference
python -m unittest discover -s tests/core -p "test_*.py" -v
```

默认输入为 C2 原始163帧。每个区间输出独立JSON，同时生成 `interval_certificates.json`、`report.json` 和 `INTERVAL_SUMMARY.md`。结果目录是 `work/repair_motion`。

退出码0表示全部区间认证通过；退出码2表示完整审计已运行但路径未获认证；退出码3表示输入或指定后端不可用。退出码2不能被CI或调用方当作认证成功。

真实区间曲线采用线性铰链角与 Rodrigues 刚体FK，保持面片刚性；没有把顶点线性插值当折纸运动。该曲线仍须通过连续闭环门禁。reference adapter 对线性弦仅作保守代理，用曲率余量包住真实曲线，并在不能证明时返回UNCERTAIN。

只有162个区间、所有面片对、连续闭环与M/V门禁全部PASS，状态才允许升级。未认证时保留C2历史等级，不改变原始关键帧或旧实验结论。当前结果见项目总控 CURRENT_STATUS 与本轮 report。

外部C++实现的替换契约见 `native_ccd/README.md`。本轮没有编译或使用原版Tight-Inclusion；Python数值界的保证范围和浮点误差余量明确记录在证书中，不能冒称第三方形式化保证。

## POC01-007C3-B：修复连续闭环桥

本版在独立目录继续研究，保留原C2和C3-A的输入及审计数据。新入口：

```powershell
python -m pip install -r requirements-research-lock.txt
python repair_motion.py --backend reference
python -m unittest discover -s tests/core -p "test_*.py" -v
```

解析球面3R单元需证明全区间定义域、连续角分支、非线性角范围、速度与加速度界；奇异或未解决单元使用明确的有限容差刚体折角子段。每个新子段重新进行全部面片对CCD，不能以闭环通过替代碰撞通过。

结果和复现说明见 `experiments/current/baseline_inputs/`；全部162个原区间的完整证书、共享节点修正和映射均保留。退出码2仍表示完成审计但未获完整连续碰撞认证。`--closure-only --out 独立目录`仅作闭环研究，该模式永远不能返回连续碰撞认证。


## POC01-007C3-C：Singular + Contact Exact Bridge

运行 `python singular_contact_motion.py --backend reference`。

本轮结果：PASS=71 / COLLISION=0 / UNCERTAIN=91；closure {'PASS': 162}；自动测试112项通过。

完整方法、逐区间证书、实验分组、未定根因与复现说明见 `experiments/current/POC01-007C3-C_SINGULAR_CONTACT_EXACT_BRIDGE/README.md`。