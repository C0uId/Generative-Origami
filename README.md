# Generative Origami / 教学折纸

生成式折纸与交互教学项目的当前权威仓库。

## 当前研发主线

1. Q4-B01 真实四足 Base；
2. Parameter-to-Geometry 真正进入纸面几何；
3. 真实 CP、材料区域、稳定 ID 与独立复折证据；
4. 将真实 Base 接回 L1/L2/C3 连续验证；
5. 连续路径门禁通过后再启动 Sequence Planner；
6. APP / 播放器 / 后端属于后续产品层。

当前 Q4 状态：`TREE_LAYOUT_SCREENED_ONLY`。
当前 C3 状态：`CONTINUOUS_RIGID_PATH_NOT_CERTIFIED`，71 PASS / 0 COLLISION / 91 UNCERTAIN，continuous closure 162/162 PASS。

## 当前唯一 C3 版本

仓库只保留 `POC01-007C3-C` 作为 C3 当前版本。C1、C2、C3-A、C3-B 不再作为独立版本保留；C3-C 运行仍需要的少量输入已整理到 `experiments/current/baseline_inputs/`。

## 目录

- `src/`：正式 Python 引擎
- `research/q4_b01/`：Q4-B01 当前研究实现
- `tests/`：核心和 Q4 回归测试
- `experiments/current/`：当前 C3-C 及其最小基线输入
- `experiments/q4_b01/`：当前 Q4 实验
- `assets/`：Base、FOLD、SVG 和目标数据
- `tools/`：认证、C3、运动修复和演示工具
- `docs/reference/`：最终完整实现方案
- `docs/engineering/`：当前工程定义、优先级和测试结论
- `governance/`：项目基线、任务、风险、验收和 Agent 审计协议

## 回归

```bash
PYTHONPATH=src:. python -m unittest discover -s tests/core -v
PYTHONPATH=src:research/q4_b01:. python -m unittest discover -s tests/q4_b01 -v
```

当前整理版本验证：核心 112/112 PASS；Q4 28/28 PASS。

## 文档原则

仓库只保留当前有执行价值的文档。聊天记录、重复建议、旧 ROADMAP/DECISIONS、已被后续方案覆盖的版本和运行垃圾均不进入当前项目树。