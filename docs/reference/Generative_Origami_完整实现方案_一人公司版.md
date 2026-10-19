Generative Origami
生成式折纸系统完整实现方案

一人公司版

方案版本 1.0    制定日期 2026 年 10 月 17 日

适用对象  创始人  总控 AI  开发与测试 AI

实施方式  一人公司加多 AI 虚拟团队

先验证可折和可教的最小闭环，再扩大自动生成范围。

本方案将产品边界、研究依据、完整技术链、生成器、数据与 API、纸层与路径验证、教学动画、AI 协作、许可成本和 90 天计划落实为任务、测试与阶段门。首要决定是以 PoC-01 四足动物生成器检验投入价值。

执行结论为有条件 Go。任意物体的通用逆向折纸保留为长期研究目标；近期交付依靠受支持的基础模型、参数域、宏动作和真人证据。

目录

1 执行结论与实施边界	6

1.1 项目结论	6

1.2 产品目标与不变量	6

1.3 首版用户流程	7

1.4 90 天交付口径	7

2 研究基础与可行性判断	7

2.1 可复用能力及其边界	7

2.2 四种问题必须分开验收	8

2.3 对原路线的工程修正	8

2.4 可行性分层	8

3 系统总架构与完整技术链	9

3.1 端到端流程	9

3.2 每个模块的输入输出	9

3.3 初始部署形态	10

3.4 不可变资产与版本联动	10

4 目标表示与策略路由	11

4.1 TargetSpec 设计	11

4.2 路由规则	11

4.3 质量选择	12

5 参数化生成器体系	12

5.1 统一生成器接口	12

5.2 五类生成器规格	12

5.3 参数约束与认证方法	13

5.4 候选生成和成本控制	13

6 FOLD 中间格式与扩展协议	13

6.1 标准字段与坐标约定	13

6.2 合法的最小 FOLD 示例	14

6.3 扩展字段与旁车文件	14

6.4 协议升级	15

7 几何验证 碰撞 层序与仿真	15

7.1 四级验证与状态	15

7.2 L1 拓扑和度量检查	15

7.3 L2 层序和接触	16

7.4 L3 碰撞检测和连续路径	16

7.5 数值仿真策略	16

7.6 全局可折性处理原则	16

8 Sequence Planner 与教学生成	17

8.1 首版使用模板化序列	17

8.2 动作 JSON 示例	17

8.3 后续自动规划路线	18

8.4 教学语言与可视化	18

9 真人可折性评分与实验数据集	18

9.1 启发评分	18

9.2 数据集结构	19

9.3 实验设计	19

9.4 评分迭代与防泄漏	20

10 Animation Engine 与 Flutter APP	20

10.1 技术选型	20

10.2 Three.js 播放方式	21

10.3 Flutter 与 WebView 的边界	21

10.4 APP 页面和异常状态	21

10.5 性能预算	22

11 数据库与资产设计	22

11.1 核心关系	22

11.2 数据字典	22

11.3 PostgreSQL 核心建表示例	23

11.4 事务 队列与恢复	24

11.5 权限 备份与保留	24

12 API 合同与错误处理	25

12.1 最小 API 集	25

12.2 请求与异步响应示例	25

12.3 统一错误格式	26

13 分阶段产品和技术路线	27

13.1 版本定义与阶段门	27

13.2 工作量与依赖	27

13.3 各阶段暂不投入的项目	27

14 PoC 01 四足动物生成器详细实现	28

14.1 唯一验证问题	28

14.2 基础资产交付包	28

14.3 参数合同和有限配置	28

14.4 工程目录与模块	29

14.5 候选处理算法	30

14.6 Python 可运行预检原型	30

14.7 后端接入和本地运行	32

14.8 PoC 任务分解	32

15 一人公司与多 AI 虚拟团队	33

15.1 责任与并行控制	33

15.2 docs 项目事实源	33

15.3 可复制任务模板	34

15.4 PR CI 和 QA	34

15.5 日常节奏	35

16 许可 商业化与成本	35

16.1 软件许可矩阵	35

16.2 内容 设计和数据的权利	36

16.3 商业验证路线	36

16.4 90 天预算和单位经济	36

17 30 60 90 天执行计划	37

17.1 产能安排	37

17.2 前 30 天	37

17.3 Day 31 至 60	38

17.4 Day 61 至 90	38

17.5 下一个工作日即可启动的清单	39

18 测试体系与验收指标	39

18.1 关键测试用例	39

18.2 不变量与性质测试	40

18.3 分阶段验收表	40

18.4 发布验收模板	41

19 风险矩阵 退出条件与决策标准	41

19.1 风险矩阵	41

19.2 单次任务退出条件	42

19.3 项目 Go Conditional Go No Go	42

20 最终可行性分析与启动决定	43

21 研究与官方资料	44

# 1 执行结论与实施边界

## 1.1 项目结论

Generative Origami 的近期可行产品是“受支持类别内的参数化折纸设计与交互教学系统”。用户用自然语言描述目标，系统在有来源、有可执行步骤、有实折证据的生成器范围内产生候选，验证并解释方案，再由 APP 分步播放。立项建议为有条件 Go：先投入 30 天完成 PoC-01，以真实纸张和未参与设计的用户验证核心闭环，再决定后续投入。

“任意物体、任意精度、一张纸、自动设计、自动规划、普通人都能完成”的组合仍属于研究目标，不能作为 V1.0 的交付承诺。文本理解、图形展示和 APP 工程可使用成熟组件；折纸构造、可执行路径、纸层接触和真人可操作性需要专门开发与实验，AI 不能代替这些证据。

本方案面向一名创始人和按任务启动的 AI 虚拟团队。创始人保留产品取舍、实物验收、授权确认、main 合并和生产发布权。总控 AI 维护依赖与验收，专业 AI 在独立分支交付可审查的变更。前 90 天优先证明一个可靠生成器，然后扩展类别；不同时建设社区、任意 3D 逆向设计和通用物理求解器。

## 1.2 产品目标与不变量

## 1.3 首版用户流程

用户输入“小狐狸，适合初学者”，选择纸张尺寸，系统显示支持能力及预计难度；生成任务异步运行，返回至多三个通过门槛的候选。作品页展示实物参考、步骤数、预计用时、纸张要求和验证状态。进入播放器后可暂停、慢放、切换视角、查看当前移动纸层、重播或退回检查点，并保存进度。

如果没有可靠候选，页面提供“换成更简单的相近造型”“改用已验证教程”“提交想折的目标”。相近造型要明确名称及省略特征，例如“简化四足动物，未包含长鼻”。外部教程保留来源和跳转信息，不计为生成成功，不自动下载为训练集。

## 1.4 90 天交付口径

90 天目标是可邀请测试的 V0.5：PoC-01 达标，形成一个可靠的四足生成器；五类生成器均有独立规格，争取五类各有一个经过实折的基础实现；若资源不足，宁可只上线一至三类。所谓“50 至 100 个目标名称”仅是别名与语义覆盖试验，不等于 50 至 100 种独立、验证过的折纸结构。

所有工期和性能数字均为工程目标或预算假设，须用实验替换。V1.0 及以后按阶段门推进，不把研究结果写成确定发布日期。验收数据中同时保留失败、超时、未支持与用户退出，防止只展示成功样本。

# 2 研究基础与可行性判断

## 2.1 可复用能力及其边界

Tree Method 的“目标树”是设计约束，不是最终纸面拓扑。相同四足语义可能需要不同 flap 分配；长颈鹿、大象、鹿角动物不能仅靠把同一组浮点数改大就保证可实现。五类生成器应各自拥有合法 base、动作库、参数依赖和认证域。[R1]

Origamizer 提供多面体表面逆向折纸的研究基础，但复杂折痕、低纸张效率、藏纸和装配路径会影响教学价值。论文思想、作者软件、输出模型以及第三方内容的权利需要分别审查。[R2]

## 2.2 四种问题必须分开验收

第一，语义相似度回答“成品是否让人认出目标”。第二，几何状态有效性回答“面片尺寸、连接和层序是否一致”。第三，路径有效性回答“是否存在本系统能验证的从展开纸到目标的操作序列”。第四，真人可操作性回答“目标用户是否能按教程完成”。这四项相互关联，不能互相替代。

局部平折条件只在适用顶点和模型假设下使用。对内部单顶点的理想平折，Kawasaki 检查交替扇区角和，Maekawa 检查山谷数量差；边界、未使用折痕、非平折目标及面片弯曲动作必须另处理。局部条件通过不推出全局层序一致、连续刚性路径存在或厚纸可操作。[R6]

## 2.3 对原路线的工程修正

将“最终两帧网格插值”改为“回放已验证的折痕角路径或仿真轨迹”。逐顶点线性插值会缩短边、弯曲面并穿过纸层，只能用于明确标注的示意过渡，不能作为折叠教学证据。

将“任意参数变形”改为“生成器约束域内的可验证变体”。不能简单拉伸已折叠成品来获得新折法；如果改变 crease pattern，必须重新编译所有状态和动作、重新检查纸张度量与碰撞，并重新确定实折覆盖。

将“仿真器判断可折”改为“仿真输出有假设、有容差、有失败状态的证据”。不收敛通常表示当前求解方式未找到解，不直接判定数学上不可折；收敛到终态也不证明找到人类能执行的过程。

## 2.4 可行性分层

# 3 系统总架构与完整技术链

## 3.1 端到端流程

Text 用户目标与纸张约束

→ Target Representation 语义部件图及约束

→ Strategy Router 支持矩阵和许可策略

→ Parametric Generator 合法 base 与参数域

→ Candidate Generator 多候选与动作草案

→ Geometry Validator 拓扑度量与局部筛查

→ Fold Simulator 依照动作草案生成轨迹

→ Human Foldability Score 初步难度和操作风险

→ Sequence Planner 展开模板并细化可执行路径

→ Tutorial Generator 确定动作到教学语言

→ Animation Engine 已验证轨迹与教学标注

→ Flutter APP 候选选择与分步学习

路径细化 → 重新仿真 → 重新评分 → 发布门槛

任一失败 → 有限重试或可靠回退 → 需求池

流程中的顺序表示职责交接，不是每个模块只执行一次。初版候选已携带 sequence template，仿真才能知道“怎么动”；Sequence Planner 在后段进行模板展开、依赖排序和细节补全。最终轨迹改变后必须重新验证并计算真人评分，不能只评估成品。

## 3.2 每个模块的输入输出

## 3.3 初始部署形态

采用模块化单体 API 加独立计算 worker，不拆成十几个微服务。Python 核心包不依赖 FastAPI，命令行、测试和 worker 调用同一组纯函数。API 处理鉴权、配额和任务状态，worker 处理生成、几何与轨迹。编辑器和 APP 不直接修改核心几何数据。

Flutter APP ← HTTPS → FastAPI API

↓                      ↓

本地 Three.js WebView    PostgreSQL 事实数据与 outbox

↓                      ↓

已下载动画资产           Redis 队列通知及短期缓存

↓

Python 计算 worker

↓

资产存储及不可变 manifest

Web 编辑器 → 同一 API → 审核与发布流程

PoC 用本地目录存资产；邀请测试再迁移至对象存储和签名 URL。PostgreSQL 保存权威状态，Redis 可重建。API 只发任务 ID，不把大网格、全部轨迹或长计算放入请求线程。官方 FastAPI 文档也建议重计算考虑独立任务工具。[R7]

## 3.4 不可变资产与版本联动

每个 DesignVersion 固定 generator_version、base_hash、参数、seed、protocol_version、solver_version、material_profile、validation_policy、sequence_hash 和内容哈希。发布后不能原地改数组或替换同 URL 文件。修复创建新版本，旧学习进度仍绑定旧教程。

CandidateBundle 至少包含 source.fold、sequence.json、trajectory、validation.json、tutorial.json、license_manifest.json 和 manifest.json。每个文件在 manifest 中记录 SHA-256、字节数、媒体类型及 schema 版本；下载后校验哈希。涉及真实用户的隐私信息放数据库，不写入公开资产。

# 4 目标表示与策略路由

## 4.1 TargetSpec 设计

语义长度是相对视觉比例，不是承诺可实现的 flap 长度。参数映射层负责把目标比例投影至生成器能力域，并返回实际实现的差异。LLM 只能生成 schema 允许的目标表示，不允许输出可执行代码、任意插件名、数据库查询或发布标记。

{

"schema_version": "target-1.0",

"canonical_target": "fox",

"family": "QUADRUPED",

"required_features": ["four_legs", "pointed_ears"],

"optional_features": ["long_tail"],

"visual_ratios": {"tail_to_body": 0.65},

"constraints": {

"paper_shape": "square", "paper_side_mm": 200,

"cutting": false, "glue": false,

"max_steps": 35, "skill": "beginner"

},

"language": "zh-CN",

"confidence": 0.91

}

confidence 是解析模型自报值，不能当成正确率；低置信阈值初设 0.75，并用人工标注的解析测试集校准。有限别名词典先行；已知目标无需每次调用 LLM。未知目标先给出结构约束，再决定是否存在生成器。

## 4.2 路由规则

路由同时检查 license_allowed_for_commercial、材料、动作集和设备能力。设置每请求最多 20 个候选、2 次参数修正、总计算 60 秒的初始预算；超限返回明确状态，不能让 Agent 无限制循环搜索。

## 4.3 质量选择

先执行硬门槛，再按 Pareto 前沿选候选。硬门槛包括协议、几何、完整序列、路径验证、许可和发布证据。初始排序建议 Q = 0.35S + 0.40H + 0.15T + 0.10E，四项均归一至 0 至 100；S 为人工标注轮廓相似度，H 为真人可折启发分，T 为教学完整度，E 为纸张与计算效率。权重是产品假设，需实验校准。

最多展示三个有意义的候选；若只有一个通过，则只显示一个。没有训练数据前，不向用户展示“84% 相似”这种伪精度，使用“轮廓简化”“步骤较少”“保留长尾”等可解释描述。

# 5 参数化生成器体系

## 5.1 统一生成器接口

GeneratorSpec 描述可用拓扑、纸张范围、动作集合、参数依赖、验证域、来源和版本。generate 不直接返回一个漂亮网格，而是返回可编译的 DesignProgram：base 引用、折痕构造或选择、flap 对应、宏动作、参数及验证前置条件。

describe() → GeneratorManifest

map_target(TargetSpec) → Params 与 approximation_notes

propose(Params, seed, budget) → DesignProgram[]

compile(DesignProgram) → CP 与 states 与 sequence

validate(Bundle, Material, Policy) → ValidationReport

一个 generator family 可以包含多个 base，不能把所有四足动物强塞进同一拓扑。continuous_domain 表示允许尝试的范围；certified_samples 表示已有证据的离散样本，两者不能混为一谈。

## 5.2 五类生成器规格

Flower 不默认覆盖玫瑰、百合、莲花全部结构。Box 的比例变更会改变折痕与序列，必须由解析构造和回归测试控制。Bird、Fish 不直接等于所有鸟类和海洋动物；语义覆盖需要逐目标辨识实验。

## 5.3 参数约束与认证方法

每个参数记录类型、单位、下限、上限、默认值、依赖与证据。姿态角用度，内部求解统一弧度；纸面坐标无量纲，材料尺寸用毫米。离散 base 不能通过连续插值跨越。相邻参数组合仍可能碰撞，逐项合法不能替代联合验证。

首次实现采用有限网格：每个自由度三档，先只开放两个真正可控自由度，形成最多九个组合。其余目标特征由已验证预设决定。后续用拉丁超立方采样发现边界，再以区间细分、约束优化和实折样本扩展；在未证明连续域安全前，用户输入吸附至已认证预设，并展示实际参数。

## 5.4 候选生成和成本控制

先使用固定 seed 的预设邻域采样，快速筛除显然越界或结构不完整的候选，再对少量候选做动态验证。缓存键包括 TargetSpec 规范化值、generator/base 版本、参数、材料、策略和 solver 版本；不要仅按“狐狸”缓存。不同用户的私人设计不得因共享缓存泄露。

给每个候选保留 rejection_code，例如 OUT_OF_DOMAIN、FLAP_BUDGET、LAYER_CYCLE、PATH_COLLISION、SIMULATION_TIMEOUT、HUMAN_REVIEW_REQUIRED。失败分布比候选总数更能指导下一周开发。

# 6 FOLD 中间格式与扩展协议

## 6.1 标准字段与坐标约定

FOLD 是 JSON 交换格式。固定文件规范版本和自有 schema 版本；标准字段保持规范语义，不把私有时间轴塞进 edges_foldAngle。初始按官方 FOLD 1.2 规范建立兼容性测试，发行时将实际仓库 commit 和 schema 哈希写入锁定文件。[R3]

内部材料坐标使用原点在左下的 [0,1] 正方形，+z 指向初始正面；Three.js 显示转换集中在 adapter 中。山谷符号依 FOLD 定义，客户端不得按屏幕上下重新解释。初始正面、面环方向和法线必须在 golden fixture 中共同验证。

## 6.2 合法的最小 FOLD 示例

下例只是一张已三角化、尚未折叠的正方形，用于协议互通；它不是四足动物折痕。对角线是平面边 F，角度为 0。示例把自有元数据放在自有前缀字段中；外部工具忽略扩展仍能读取基本几何。

{

"file_spec": 1.2,

"file_creator": "GenerativeOrigami",

"file_classes": ["singleModel"],

"frame_classes": ["creasePattern"],

"frame_attributes": ["2D"],

"vertices_coords": [[0,0],[1,0],[1,1],[0,1]],

"edges_vertices": [[0,1],[1,2],[2,3],[3,0],[0,2]],

"edges_assignment": ["B","B","B","B","F"],

"edges_foldAngle": [0,0,0,0,0],

"faces_vertices": [[0,1,2],[0,2,3]],

"go:schema_version": "go-1.0",

"go:design_id": "demo-square-001"

}

## 6.3 扩展字段与旁车文件

FOLD 数组索引只在该几何版本内有效。编辑导致拓扑改变时生成新 topology_hash，迁移稳定 ID 或明确失效，不能让旧步骤继续移动错误纸层。轨迹可采用压缩二进制存储，FOLD 保留语义几何；不要把每一渲染帧的大量重复坐标都写入数据库 JSONB。

CP 的山谷分配表示该 CP/目标帧约定；过程帧保存当时的实际折角及对应赋值。预折、展开或反向折叠可能让同一材料折线经过零角或改变角度符号，不能拿最终静态分配强行检查全部过程帧。所有自定义属性均采用含冒号的命名空间键，例如 go:sequence_ref；标准字段不改名。[R3]

## 6.4 协议升级

采用主版本拒绝、次版本忽略可选字段的兼容策略。升级要提供旧 fixture 的读取、写入、往返和迁移测试。关键字段缺失、NaN、过大数组、错误下标、层序环或哈希不匹配时阻止加载；播放器显示友好错误和可恢复入口。

# 7 几何验证 碰撞 层序与仿真

## 7.1 四级验证与状态

每项返回 pass、fail、unknown 或 not_applicable，附原因和模型假设。L1/L2 初期可自动执行，L3 对支持动作和已认证轨迹执行；L4 是发布证据。非适用条件不能标为 pass。任何必要检查 unknown 的候选不得进入“已验证生成”产品通道。

## 7.2 L1 拓扑和度量检查

检查闭合纸张边界、无意外孔洞、顶点和边索引、面自交、重复边、近零面积面、共享边连接，以及 CP 中交叉折线的正确分割。将最终 CP 统一细分，使整个轨迹使用同一材料网格；未激活折痕保留零角度。欧拉关系仅按实际连通分量和孔洞条件辅助检查，不能机械套用一个常数。

按适用顶点计算扇区角、Kawasaki 残差和 Maekawa 数量差，未分配或不用的折痕单独记录。刚性面片检查每条材料边的长度与面内距离，防止把目标网格拉伸当折纸。容差与纸张尺度和浮点精度绑定，禁止通过无限放宽容差获取通过。

数据中区分真实折痕、材料离散网格边、临时弯曲自由度和渲染三角化边。柔性宏必须给出柔性区域、材料模型或经实折校准的专用过渡模型；该区域不使用刚性面内角度不变假设，但仍检查材料度量与形变限值。当前模型不支持的过渡返回 unknown。

## 7.3 L2 层序和接触

先求非相邻三角面相交；相邻面只排除它们共享的合法边或顶点接触，不能排除整对面片。对近共面区域投影并切分重叠单元，在每个重叠单元建立局部上下关系及接触约束，检查矛盾、穿插和循环。faceOrders 是输入或输出约束，不是自动可折证明。

全模型一个简单面序 DAG 不能覆盖所有折叠层序问题，因为同一对面在不同空间区域的关系和纸层连接可能更复杂。PoC 限定已知层序模板和有限接触事件，局部未知关系返回 unknown；后续再引入约束求解，不以“图无环”宣称通用全局可折。

## 7.4 L3 碰撞检测和连续路径

采用 BVH 或 AABB 宽相位，三角形间距离、相交及扫掠检测做窄相位。每个宏动作记录允许接触的面片对、接触区域、时间区间、接触类型和层序事件，同时记录共享铰链、运动侧和握持区域；允许局部接触不能跳过整对面片检查。普通离散采样可能跨过薄纸碰撞；先用自适应时间细分和速度上界，生产支持动作优先加入连续碰撞检测。只有采样通过时，报告应写“在给定步长下未检出穿透”，证据等级低于连续验证。

厚纸通过实测 thickness_mm 和接触间隙建模。对近零厚度拓扑验证与有限厚度可操作性分开报告；合法面片接触、贴合和纸层轻微弯曲不应全部当成碰撞。压折、翻折和塞入可能需要面内新折痕、临时弯曲或多指操作，不能用一个刚体转动代替。

## 7.5 数值仿真策略

PoC 首选经过人工确认的宏动作及其轨迹：简单铰链动作采用刚性面片树与闭环约束，复杂宏使用离线求解并经实折校对的轨迹。一般 CP 的动态松弛作为研究预览工具。Origami Simulator 的交互能力可用于参考或合规集成，但其演示结果不作为完整路径认证。[R4]

残差包括相对边长误差、铰链闭合误差、目标角误差、最小非接触间隙和最大穿透。PoC 初始建议：边长相对误差 ≤ 1e-4；铰链闭合误差 ≤ 纸边长的 1e-4；角残差 ≤ 1°。禁止未解释的穿层或穿透；落在数值不确定区的接触返回 unknown，不能用一个大于纸厚的误差阈值放行。数值容差、材料厚度和设计留隙分别配置。上述初值必须校准并保存原始指标。

## 7.6 全局可折性处理原则

不开发一个名为 is_foldable 且只返回布尔值的万能函数。将“我们已有一条通过验证的路径”“数值求解未找到路径”“已证伪某项必要条件”分别编码。一般全局问题的困难性意味着有限时间搜索存在未决结果；产品应通过限制 base、动作和材料范围获得可靠性，而不是假装消除研究难点。[R6]

新参数导致路径失效时，依次吸附至邻近认证参数、切换同族 base、返回已验证近似方案；全部失败则停止生成。未经验证的研究候选可以在内部编辑器显示，不能被普通用户误认成可教学方案。

# 8 Sequence Planner 与教学生成

## 8.1 首版使用模板化序列

V0.1 把人工验证过的动作程序参数化，而不是从任意 CP 自动找教程。每个宏动作定义前置条件、移动面组、固定面、参考边、纸层、可达区域、角度轨迹、接触切换、终止条件和逆向调试程序。模板展开后形成步骤依赖 DAG；只有允许交换的独立步骤才能重排。

ROTATE_VIEW 是摄像机动作；ROTATE_PAPER 和 FLIP_PAPER 是用户对整张纸的操作。它们要分开编码，避免教程说“翻面”而播放器只是绕摄像机。UNFOLD 也不是删除历史状态：预折痕仍存在，并会影响后续材料和参考线。

## 8.2 动作 JSON 示例

下例仅说明协议结构。face 和 edge ID 必须来自对应实际模型；不能把示例 ID 当作现成折法。

{

"schema_version": "sequence-1.0",

"step_id": "s007",

"macro_id": "inside_reverse_q4_head_v1",

"pre_state": "state006", "post_state": "state007",

"moving_faces": ["f12", "f13"],

"fixed_faces": ["f08"],

"reference_edges": ["e42"],

"trajectory_ref": "traj007",

"requires": ["crease_e42_prepared"],

"ensures": ["head_shape_ready"],

"contact_policy_ref": "contact007",

"flexible_transition": true,

"flexible_region_faces": ["f12", "f13"],

"transition_model_ref": "q4-head-flex-v1",

"checkpoint": true,

"duration_ms": 2400

}

## 8.3 后续自动规划路线

V1.0 在有限模板图上自动选择、展开和局部重排；“自动 Sequence”指结构化编译和已知宏组合，不宣称从任意 CP 发现折叠顺序。V2.0 才在受限状态空间使用 beam search 或 A*，状态包含当前几何、折痕激活、局部层序、握持和宏动作可用性。启发函数可综合目标差异、剩余动作成本和操作难度；找不到解应保留 unknown。

LLM 可以提出 schema 内动作候选，验证器决定是否执行；限制候选宽度、深度与仿真调用数。对柔性过渡和闭合链，必须使用适配的动作模型。Learn2Fold 的 proposal、verify、lookahead 思路可作参考；其评估含已有 CP 与目标信息，不能据此推出任意文本已能从零生成任意折纸。[R5]

## 8.4 教学语言与可视化

先用确定性句式生成“移动对象、参考位置、折叠方向、完成检查”，再允许 LLM 在不改变 ID、角度、前后状态的前提下改写。文案校验器把数字、指代和方向映射回动作；模型输出缺参考线或新增动作则拒绝并使用模板文案。

每步包括动作前示意、当前移动纸层高亮、山谷线型、运动箭头、慢放、完成后检查及常见错误。复杂步骤可提供经授权实拍短片；它必须与该设计版本一致，并在编辑器标记为“实拍辅助”。图文降级可用于已经实折过的步骤，不能掩盖缺失的几何路径。

# 9 真人可折性评分与实验数据集

## 9.1 启发评分

先建立可解释风险分，不在缺数据时训练一个“成功率模型”。令每个风险 r 在 0 至 1，H = 100 × [1 − (0.15r_steps + 0.20r_size + 0.20r_layers + 0.15r_precision + 0.15r_access + 0.15r_complex)]，最终限制在 0 至 100。分数只用于候选比较，不能替代硬约束或声称为成功概率。

clip 表示截断到 [0,1]；初值需校准。例如最小操作宽度应测“手要夹持或压折的有效区域”，不只是网格最短边。未知层数、容许误差或触达性不能填 0，应产生 missing_features 并要求人工评估。材料换批、纸张尺寸变化后重新计算。

## 9.2 数据集结构

成功定义：在指定时间上限内，未由研究人员代折，四腿、头尾等必需部件完整，且最终结构通过预定义检查。口头提示另记 assistance_count；“完成但得到帮助”与独立完成分开。主动退出进入分母，设备故障保留并单列，不事后随意排除。

## 9.3 实验设计

PoC：三个相近 preset 各两次设计者或专家复折；12 名未参与制作的目标用户，每人一次主要测试，按 4/4/4 分配 preset，尽量平衡经验。另做盲评辨识实验，先不展示目标名称，让受试者选择或自由命名；区分“四足动物”识别和“狐狸”物种识别。

V0.5：累计至少 30 名独立用户、60 次试折，分层报告生成器、材料和经验；同一人多次记录不是独立用户。V1.0 正式验收使用冻结方案的新增用户，关键主要指标按参与者首次任务计算；多次任务模型要处理参与者相关性。

PoC 完成率门槛为至少 9/12 独立完成，单个 preset 不低于 2/4。9/12 的 95% Wilson 区间约为 47% 至 91%，仅能支持继续探索，不能宣传“保证 75% 用户完成”。后续扩大样本并报告分母、置信区间和分组差异。

预注册每次独立试折上限 45 分钟；研究人员代折、逐动作口头引导或替用户修复关键结构均计独立完成失败。一般性设备操作帮助单列。盲评先用 20 名未见教程者、每人一张随机成品照片，至少 14/20 正确识别预定义类别；物种命名另报，不将已告知名称后的“觉得像”当作盲评。

project_go_gate 只决定是否继续研发。preset_release_gate 独立决定每个配置是否可供用户使用：权利、自动必需项和专家复折必须完整；对新配置至少有 10 名独立目标用户测试且至少 8 人独立完成，保留区间及范围声明。PoC 的 2/4 配置不得直接公开发布，需修改和补测；未通过此门的版本只用于明确同意的实验。

## 9.4 评分迭代与防泄漏

先检验 H 分与完成率、耗时、求助数的相关性，再决定是否用逻辑回归或梯度提升模型。训练、验证、测试按 base family 划分，不能把同一模型的轻微参数变化同时放进训练和测试来夸大泛化。另保留完全未见过的 base 外测集。

不得将用户上传照片和视频默认用于模型训练。分别取得服务处理、实验研究、公开展示和训练的用途同意；媒体默认私有、可撤回，并通过资产引用追踪派生用途。早期仅招募成年人可降低实验组织复杂度。

# 10 Animation Engine 与 Flutter APP

## 10.1 技术选型

版本策略：使用官方仍支持的稳定分支，在 Day 1 把实际版本、依赖哈希、许可证和目标设备写入 docs/11_DEPENDENCIES.md；不以“始终用最新版”替代复现。首轮建议 Python 3.12 兼容环境、Pydantic v2、SQLAlchemy 2 风格接口；具体补丁版由 CI 验证后锁定。

## 10.2 Three.js 播放方式

播放器加载固定版本的 mesh、稳定 ID 映射、关节角曲线和标注；每个 t 通过同一 kinematic adapter 计算位置，或读取经验证的仿真样本。角度插值用于已验证的运动参数，刚体方向使用合适的旋转插值；临近接触处禁止用不受约束的样条产生超调。

样本间的插值函数及参数本身属于 trajectory 资产，必须一起通过 L3 检查；关键帧检查通过不能授权任意逐顶点补间。客户端在随机 t、动作边界和接触切换附近与服务端运行 golden 对照，核对几何残差和状态 ID。仅有示意帧而无有效插值时，采用停帧教学，不宣称真实折叠动画。

步骤进度与物理时间分开：拖动进度可以跳到已存检查点再回放；“上一步”是教学回看，不要求用户把实物自动展开。渲染三角化不改变真实折痕和面 ID。纸正反面颜色、半透明、透视和剖层视图帮助辨认纸层，默认视图避免遮住关键区域。

## 10.3 Flutter 与 WebView 的边界

Flutter 负责登录、目标输入、候选选择、下载、收藏、进度和无障碍控制。Three.js 页面作为受信任本地资源打包，bridge 只接受白名单 JSON 消息：loadBundle、seek、play、pause、setCamera 和事件 ready、stepChanged、error。消息包含 protocol_version、request_id、design_version；主端检查顺序和长度。[R8]

当前 Three.js WebGLRenderer 需要 WebGL2，必须探测该能力。官方 webview_flutter 支持平台以锁定版为准，移动端优先 Android/iOS；Flutter Web 若以后支持，另用 HtmlElementView 或官方 Web 内容嵌入机制，不把移动插件当作全平台兼容保证。[R20][R21]

bridge 不传任意脚本，不将远程用户文字直接拼成 JavaScript；不向 WebView 注入账户 token 或服务器密钥。禁止非白名单导航和不必要文件访问，下载通过 API 获取短时签名 URL。网页外链交给系统浏览器。Android 和 iOS 的 WebView 分别做 WebGL 功能探测与实机测试，不能据桌面浏览器效果承诺全部移动设备性能。

## 10.4 APP 页面和异常状态

WebGL 不支持时使用已经验证的图文关键帧教程；没有图文包则说明设备能力并返回作品页，不展示空白画布。离线包保留 manifest 和版本，APP 重启恢复到上次完成的检查点。用户误连点、快速跳步、屏幕旋转、后台恢复都要保持同一状态机。

## 10.5 性能预算

初始单模型预算为不超过 10,000 个渲染三角面、压缩教学包不超过 10 MB、按需加载轨迹。选择一台中端 Android 和一台受支持 iPhone 作为基线，记录机型、系统、WebView、网络和包版本。目标为步骤交互 p95 ≤ 100 ms，基线设备播放 ≥ 30 fps，100 次加载无不可恢复崩溃；实际测量不达标先简化资产和缓存，不直接重写原生 3D 引擎。

# 11 数据库与资产设计

## 11.1 核心关系

User 1 → N GenerationJob 1 → N Candidate

Generator 1 → N GeneratorVersion → BaseAssetVersion

Candidate N → 1 DesignVersion 1 → N ValidationRun

DesignVersion 1 → N TutorialVersion 1 → N TutorialStep

TutorialVersion 1 → N FoldTrial 1 → N StepAttempt

DesignVersion 1 → N Artifact → RightsRecord

User N ↔ N Design 收藏

User + TutorialVersion → LearningProgress

作品语义实体 Design 和具体 DesignVersion 分离；同一“狐狸”可以有多个 base 和多套教程。验证报告绑定精确设计版本、序列哈希与材料。旧 L0 至 L4 是内容表现等级，新 L1 至 L4 是验证阶段，数据库必须分别命名 content_level 和 validation_stage，避免混淆。

## 11.2 数据字典

JSONB 适合版本化 TargetSpec、参数和报告摘要；经常筛选的状态、版本、用户、时间和权限使用显式列。完整轨迹和媒体放资产存储。不要把用户表、验证日志与大几何 JSON 混成一张文档表。

## 11.3 PostgreSQL 核心建表示例

以下 DDL 为核心切片，其余表按数据字典实现；所有变更通过 Alembic 迁移。ID 由应用生成 UUID，避免示例依赖额外扩展。

CREATE TABLE generation_jobs (

id uuid PRIMARY KEY,

user_id uuid NOT NULL REFERENCES users(id),

idempotency_key varchar(100) NOT NULL,

request_hash char(64) NOT NULL,

request jsonb NOT NULL,

status varchar(24) NOT NULL CHECK (status IN

('queued','running','succeeded','failed','cancelled')),

stage varchar(40),

lease_until timestamptz,

attempt_count integer NOT NULL DEFAULT 0,

created_at timestamptz NOT NULL DEFAULT now(),

updated_at timestamptz NOT NULL DEFAULT now(),

UNIQUE (user_id, idempotency_key)

);

CREATE INDEX jobs_pending ON generation_jobs(created_at)

WHERE status = 'queued';

CREATE TABLE design_versions (

id uuid PRIMARY KEY,

design_id uuid NOT NULL REFERENCES designs(id),

version integer NOT NULL CHECK (version > 0),

generator_version_id uuid NOT NULL

REFERENCES generator_versions(id),

base_asset_version_id uuid NOT NULL

REFERENCES base_asset_versions(id),

params jsonb NOT NULL,

seed bigint NOT NULL,

source_hash char(64) NOT NULL,

manifest_artifact_id uuid REFERENCES artifacts(id),

status varchar(24) NOT NULL DEFAULT 'draft',

created_at timestamptz NOT NULL DEFAULT now(),

UNIQUE (design_id, version)

);

## 11.4 事务 队列与恢复

创建 job 与 outbox event 放同一 PostgreSQL 事务；dispatcher 向 Redis 投递通知后标记投递。通知可重复，worker 用数据库原子状态转换和 lease 抢占，输出先写临时资产、校验哈希，再提交 manifest 和结果引用。任务执行按至少一次处理设计，不能假定“消息只来一次”。

worker 崩溃后 lease 到期可重试；幂等产物键确保不重复计费和发布。每个阶段记录 stage_started_at、attempt、heartbeat 和 error_code；可重试网络错误最多三次并退避，几何失败不盲目重试。Redis 丢失时扫描未完成任务和 outbox 恢复，已完成事实仍在 PostgreSQL。若使用 Celery，应按其任务确认语义配置，并保留应用层幂等。[R22]

## 11.5 权限 备份与保留

API 每次读取 job、design、trial 和进度均核对 owner 或公开发布权限；数据库可增加行级安全作为纵深措施。使用 RLS 时必须测试应用数据库角色、表所有者和 BYPASSRLS 行为，不能假定开启即全面生效。[R9]

初始每日备份数据库和不可变资产清单，异地加密副本保留 30 天；每月实际恢复到隔离环境并校验随机 manifest。邀请测试阶段目标 RPO ≤ 24 小时、RTO ≤ 4 小时。搜索原文和实验媒体设独立保留策略；删除请求触发引用审计，依法或依约保留的记录采用去标识摘要。

# 12 API 合同与错误处理

## 12.1 最小 API 集

接口以 OpenAPI 和 JSON Schema 为合同；Flutter 和编辑器从固定版本生成类型。分页采用 opaque cursor，默认 20 条、最大 100；枚举新增需兼容旧客户端。非必要不暴露精确内部异常或堆栈。

## 12.2 请求与异步响应示例

POST /v1/generations

Authorization: Bearer <用户短期令牌>

Idempotency-Key: client-generated-uuid

Content-Type: application/json

{

"protocol_version": "go-1.0",

"text": "适合初学者的小狐狸",

"paper": {"profile_id": "paper-200-01"},

"preferences": {"max_steps": 35, "skill": "beginner"},

"locale": "zh-CN"

}

{

"job_id": "bca811bd-138b-40ab-b1c8-4d1cb3738e9b",

"status": "queued",

"poll_after_ms": 1500,

"capability_version": "cap-0.1.0",

"request_id": "req-001"

}

成功任务返回 candidates、actual_parameters、approximation_notes、verification_scope 和不可变 design_version。幂等键相同且 request_hash 不同返回 409；相同输入返回原任务，不再扣额度。GET job 可返回 Retry-After；早期采用轮询，只有必要时再加 SSE。

## 12.3 统一错误格式

{

"error": {

"code": "UNSUPPORTED_PARAMETER_DOMAIN",

"message": "当前基础模型不能实现所需长颈结构",

"retryable": false,

"details": {"supported_family": "short_neck_quadruped"}

},

"request_id": "req-001"

}

NO_VERIFIED_CANDIDATE 可作为已完成 job 的 outcome，而不是将所有正常无解场景都伪装成服务器错误。HTTP 提交成功不等于生成成功；监控分别统计提交、处理、通过验证和真人完成。

# 13 分阶段产品和技术路线

## 13.1 版本定义与阶段门

V0.1 的“五类”是目标清单，不是可以跳过证据的发布条件。五类未全部达标时，用能力清单公布真实覆盖，不把半成品标为已支持。V1.0 的自动序列是有限域内编译，不把通用状态空间规划提前承诺给用户。

## 13.2 工作量与依赖

PoC-01 预留 3 至 5 周；V0.1 在 PoC 达标后再预留 4 至 8 周；V0.5 需要额外 4 至 6 周的数据和用户测试。V1.0 预留 2 至 4 个月，V2.0 和 V3.0 各用独立研究周期评估。各阶段可以复用基础设施，但不能把 AI 并行数直接当成人类研发人数来压缩时间。

30/60/90 天计划是有阶段门的执行安排：30 天争取完成 PoC，60 天扩展可靠类别，90 天争取 V0.5 邀请测试。若第一个 base 需额外设计或几何求解未达标，后续里程碑顺延并主动缩范围；不靠降低验收门槛追赶日期。

## 13.3 各阶段暂不投入的项目

前 90 天不建设社区投稿、大规模爬取、排行榜、社交关系、拍照自动纠错、任意 Text-to-3D 及常驻 GPU 集群。旧方案的官方教程、外部索引和需求池保留为轻量回退；内容 L0 至 L4 字段可保留，不为其单独再建一个平台。

V2.0 开始探索自动规划前，应先证明新增已知 base 的作者成本下降、同一宏能被多个模型复用、碰撞反例不会漏检。V3.0 研究预算与生产预算分账，模型输出未经教学验证不能直接进入 APP。

# 14 PoC 01 四足动物生成器详细实现

## 14.1 唯一验证问题

PoC-01 验证“一个可实折且具有合法权利的四足基础模型，能否在可控范围内产生多个可辨识变体，并用同一套结构化程序教用户完成”。首轮选择短颈、小头、四腿、尾部可修形的简化模型。Q4-B01 是拟建资产编号，当前计划不假定它已经存在。

若创始人无法设计并稳定复折该模型，应采购折纸设计或教学协作服务，书面明确商业、改编、动画、数据分发和实验用途。AI 可以辅助 CP 整理和编码，但不能虚构一张“四足正确折痕图”来代替实物设计。

## 14.2 基础资产交付包

缺少基础纸样、授权、宏程序或复折证据时，生成 API 返回 unverified_asset，只允许内部协议演示。Day 10 仍未获得可重复基准时停止扩大工程投入，优先换 base 或调整为教程作者工具。

## 14.3 参数合同和有限配置

首轮 A/B/C 的角度和尺寸由真实纸样确定后填写到 preset manifest，文档不预先编造可行区间。第一轮只开放离散配置；第二轮至多两个姿态自由度的三档组合仍需逐组合验证。长颈鹿、象鼻、鹿角等进入其他 base 需求池。

## 14.4 工程目录与模块

repo/

docs/                    产品与技术事实源

packages/

origami_core/

target.py            TargetSpec 与单位

routing.py           支持范围与许可筛选

generators/q4.py     四足候选与参数映射

compiler.py          宏程序到 CP 状态 序列

geometry.py          拓扑与度量检查

contact.py           碰撞和局部层序

simulation.py        运动与轨迹生成

scoring.py           真人风险特征

tutorial.py          文案及标注编译

packaging.py         manifest 与哈希

player/                Three.js TypeScript

apps/api/                FastAPI 与 worker

apps/mobile/             Flutter

apps/editor/             最小作者编辑器

assets/bases/q4_b01/      权利受控的基础资产

schemas/                 FOLD profile 与旁车协议

tests/fixtures/          正例 反例和冻结数据

experiments/             配置 记录和分析

infra/                   容器 CI 迁移和恢复

编译入口 compile_program(base, preset, policy) 先校验权利、版本和文件哈希，展开宏动作，统一细分材料网格，生成稳定 ID 映射、CP、状态与序列。所有输出携带 source_program_hash；文字和动画从同一结果派生，禁止各 AI 分别猜一套几何。

## 14.5 候选处理算法

1. 规范化输入并判断目标必需部件。四腿、头尾需求可以进入 Q4；额外长鼻或鹿角无法满足则先拒绝或提出近似选择。

2. 从已授权、材料匹配、版本固定的 A/B/C 中取比例最接近的配置。PoC 上限 12 个候选，通常只需三个；全系统上限 20 个。

3. 读取并校验 base 与宏程序哈希，编译所有表示。禁止先生成好看的网格再补故事式步骤。

4. 执行 L1/L2，失败立即记录；对支持宏运行 L3 轨迹验证，unknown 不进入公开候选。

5. 抽取风险特征和近似差异，硬门槛通过后排序，输出最多三个不同候选。

6. 生成确定性教学文案、箭头和摄像机，打包并核对源哈希。只有专家及用户证据匹配的配置才标为可发布。

7. 冷生成尚未实折的新参数进入 ready_for_review；在线用户优先使用已认证配置，后续再扩大自动生成范围。

## 14.6 Python 可运行预检原型

下面的标准库脚本可直接复制为 preflight.py。它实现严格目录准入、比例匹配、哈希验证及明确失败，不包含尚待开发的折纸求解器。空目录返回 NO_VERIFIED_CANDIDATE 是正确行为；它不能产出一个假四足模型。

catalogue.json 的根为数组；每项必须有 id、base_version、paper_profile、family、ratios、source_path、sha256、rights_cleared、expert_trials、required_checks 和 user_trial_gate。required_checks 必含 schema、geometry、terminal、path 四项且值为 pass。只有 actual ratios 和真实证据完备的配置可入选。

from pathlib import Path

import hashlib

import json

import math

import sys

REQUIRED = {"schema", "geometry", "terminal", "path"}

def require(condition):

if not condition:

raise ValueError("ineligible preset")

def choose(target, catalogue, asset_root, paper, limit=3):

root = Path(asset_root).resolve()

if not isinstance(catalogue, list):

raise ValueError("catalogue must be a list")

if not isinstance(target, dict) or not target:

raise ValueError("target ratios required")

if not all(isinstance(v, (int, float))

and not isinstance(v, bool)

and math.isfinite(v) and v > 0

for v in target.values()):

raise ValueError("invalid target ratio")

ranked, rejected = [], []

for p in catalogue:

if not isinstance(p, dict):

rejected.append("malformed-entry")

continue

pid = p.get("id", "unknown")

try:

require(p["family"] == "QUADRUPED")

require(p["paper_profile"] == paper)

require(p["rights_cleared"] is True)

require(bool(p["base_version"]))

require(len(p["expert_trials"]) >= 2)

require(p["user_trial_gate"] is True)

checks = p["required_checks"]

require(REQUIRED.issubset(checks))

require(all(checks[k] == "pass" for k in REQUIRED))

ratios = p["ratios"]

require(all(k in ratios for k in target))

require(all(isinstance(ratios[k], (int, float))

and not isinstance(ratios[k], bool)

and math.isfinite(ratios[k])

and ratios[k] > 0 for k in target))

source = (root / p["source_path"]).resolve()

require(source.is_relative_to(root))