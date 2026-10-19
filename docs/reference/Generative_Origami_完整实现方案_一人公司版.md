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

require(source.is_file())

digest = hashlib.sha256(source.read_bytes()).hexdigest()

require(digest == p["sha256"])

loss = sum((target[k] - ratios[k]) ** 2

for k in target)

ranked.append((loss, pid, p))

except (KeyError, TypeError, ValueError, OSError):

rejected.append(pid)

ranked.sort(key=lambda row: (row[0], row[1]))

selected = [{"id": p["id"], "actual_ratios": p["ratios"],

"source_sha256": p["sha256"],

"status": "verified_catalogue_match"}

for _, _, p in ranked[:limit]]

return {"outcome": "ok" if selected

else "NO_VERIFIED_CANDIDATE",

"candidates": selected, "rejected_ids": rejected}

if __name__ == "__main__":

if len(sys.argv) != 4:

raise SystemExit("preflight.py catalogue.json target.json assets")

catalogue = json.loads(Path(sys.argv[1]).read_text("utf-8"))

target = json.loads(Path(sys.argv[2]).read_text("utf-8"))

result = choose(target["ratios"], catalogue, sys.argv[3],

target["paper_profile"])

print(json.dumps(result, ensure_ascii=False, indent=2))

运行环境为 Python 3.12；用空目录测试时，catalogue.json 内容为 []，target.json 如下。命令 python preflight.py catalogue.json target.json assets 会输出 NO_VERIFIED_CANDIDATE。开发者可使用临时测试文件构造正例，必须标注为测试替身，不作为可实折资产。

{

"paper_profile": "paper-200-01",

"ratios": {"body_to_leg": 1.3, "tail_to_body": 0.5}

}

原型目录只接受本地管理员整理的可信元数据，不能作为开放上传接口。正式实现增加 schema 类型、重复 ID、证据签名或审核权限检查，用验证服务计算 checks，并把 expert_trials 解析为对应版本的真实证据。文件读取还要设置大小限制。比例损失只适合同一 base 的归一化比例，不是完整视觉相似度。

## 14.7 后端接入和本地运行

第一次迭代先跑核心 CLI 和测试，再接 API；API 不得把本地原型当成长任务框架。开发环境准备 PostgreSQL、Redis 或许可确认后的替代、api 与单 worker，使用私有环境文件配置连接。执行迁移、导入已审核目录、启动 API，提交任务后应返回 202，worker 计算并写入固定版本结果，Flutter 用任务 ID 拉取。

python -m pytest tests/core tests/contracts

alembic upgrade head

uvicorn apps.api.main:app --host 127.0.0.1 --port 8000

python -m apps.api.worker

flutter analyze

flutter test

上述模块是仓库待建目标路径，按本章任务逐项实现后可执行；preflight.py 则是可直接运行的预检示例。README 必须记录实际启动方式、环境变量名、迁移、fixture 导入和一条端到端请求。不得将生产密钥写入示例或 APP。

## 14.8 PoC 任务分解

依赖为 P01→P02→P04→P05/P06→P07；P03 与 P01 可并行，P08 使用固定测试包并行；P09/P10 在 schema 冻结后推进。P11 不能提前用未经验证的演示动画替代教学包。

# 15 一人公司与多 AI 虚拟团队

## 15.1 责任与并行控制

采用五个常用角色，加按需专家能力。角色代表任务上下文和职责，不代表必须购买五个不同模型或长期同时运行。每日最多两个实现分支、一个独立审查任务；一项任务只有一个 owner，避免多个 AI 同时改协议或数据库。

几何验证、复杂动画或 DevOps 可临时拆为专家子任务，仍由一个 owner 整合。总控 AI 不同时大范围改代码；QA 不以阅读作者说明代替实际运行。任何 AI 的“看起来可行”都不覆盖真人试折。

## 15.2 docs 项目事实源

沿用旧方案的编号，增加折纸生成特有事实。聊天中的决定经确认后写入文件，代码、schema 和文档出现冲突时必须修正，不能让后续 AI 自行挑选有利版本。

/docs/01_PRODUCT.md          承诺 边界 用户和回退

/docs/02_ARCHITECTURE.md     模块依赖 部署和资产流

/docs/03_DATABASE.md         数据字典 迁移和权限

/docs/04_API.yaml            OpenAPI 合同与错误码

/docs/05_UI_STANDARD.md      页面和播放器交互

/docs/06_ORIGAMI_PROTOCOL.md FOLD profile 和 Sequence DSL

/docs/07_ROADMAP.md          版本 阶段门和预算

/docs/08_TASKS.md            任务状态及依赖

/docs/09_TEST_STANDARD.md    反例 容差和发布门槛

/docs/10_DECISIONS.md        ADR 索引及已作决定

/docs/11_DEPENDENCIES.md     版本 哈希 许可与支持平台

/docs/12_EXPERIMENTS.md      真人实验及数据集规则

/docs/13_LICENSE_REGISTER.md 代码 模型 媒体 授权凭证

/docs/adr/                  每项架构决定的理由

/docs/tasks/                单任务卡

/docs/qa/                   验收和回归报告

Agent 开工先读产品、架构、相关 schema、测试标准和当前任务；遇到字段或产品边界缺失，先在同一 PR 中提出具体修改，不凭聊天记忆造字段。重要假设标为 proposed，真人或被授权的总控确认后记为 accepted；被替代的决定保留原因和新索引。

## 15.3 可复制任务模板

TASK ID 及标题

目标行为  谁在何种条件下获得什么结果

输入事实源  文件及固定版本

范围  允许修改的模块

非范围  本次不解决的事项

交付物  代码 schema 文档 fixture 迁移

接口影响  字段 状态和兼容措施

验收  一条正例 两条反例 关键不变量

依赖  前置任务和阻塞项

预算  时间 计算和外部 API 上限

验证  命令 设备和实折要求

风险与回滚  触发条件和恢复方法

完成证据  提交哈希 测试报告和剩余限制

任务示例：P07 检测“首尾无碰撞但中间穿透”的两面运动。输入 contact-policy-v1 和冻结反例；只改 contact 模块。验收为反例被拒绝、合法铰链接触不误报、超时返回 unknown，提交失败时间区间及面 ID。只看两帧或放宽 epsilon 均不能通过。

## 15.4 PR CI 和 QA

任务卡及验收 → codex/任务分支 → 小范围实现

→ 自检及证据 → PR → 自动 CI

→ 独立 QA 反例 → 创始人验收与合并

→ 同一构建部署预发布 → 实机与实折抽验

→ 创始人发布 → 监控与回滚

PR 写明具体问题、行为变化、关联任务、接口迁移、测试结果、几何假设、许可证新增及回滚方式。生成器变化必须附固定参数和失败样本；数据库变化附迁移和旧数据兼容。CI 失败阻止合并，main 禁止 Agent 直接提交。按路径运行检查，避免每个文案变动都跑昂贵求解。

基础 CI 包含 Python 格式与类型、必要单元及性质测试、schema、固定 seed、API 鉴权和幂等、TypeScript 构建、Flutter analyze/test、密钥扫描及依赖许可清单。夜间或发布前再跑参数边界、碰撞反例、worker 中断、旧协议和实机回归。AI 评审只是补充，必需证据仍是执行结果和真人验收。

## 15.5 日常节奏

每日 15 分钟由总控整理“已完成、阻塞、今日唯一主目标”，创始人用 30 至 60 分钟审看关键差异和演示。每周安排一次完整纸张实验、一次版本演示、一次单位成本与失败原因回顾。以可发布教学包、未解决反例和用户完成率衡量进展，不以 AI 生成代码行数衡量产能。

生产密钥、应用商店账号、支付、许可签约和外部消息发送由创始人控制。默认 Agent 可在任务范围内读写、测试、建立分支和起草 PR；不可自行发布、购买服务、修改生产数据或对外承诺。权限应按实际工具设置落实，而不是只写在提示词中。

# 16 许可 商业化与成本

## 16.1 软件许可矩阵

以下为截至 2026 年 10 月 17 日的一手资料核查。实际发布须按锁定版本、依赖、修改、分发和服务方式复核；同一软件的算法论文、源码、二进制及示例内容并非同一授权对象。

TreeMaker 的 GPL 不是禁止收费；分发包含或修改其代码的组合程序可能涉及对应源代码及许可义务。仅加一个 HTTP 接口并不能自动给出豁免结论。首版优先独立实现受限模板，不复制后再让 AI 改变量名来掩盖来源。[R10][R19]

Tachi 软件不能因为可下载就默认为商业可用，内部用于生成付费产品资产也应先确认授权范围。论文可用于研究算法，但独立实现仍应记录来源、代码洁净边界以及专利等其他权利核查。[R2][R11]

Redis ≤7.2 使用 BSD-3-Clause；7.4 至 7.8 为 RSALv2 或 SSPLv1；8 及以后提供 RSALv2、SSPLv1 或 AGPLv3 的选择。许可后果取决于版本、所选条款和实际使用，不能把客户端 redis-py 的许可当成服务端许可。需要宽松许可时可评估 Valkey；不要仅为规避审查而长期停留在缺乏安全维护的版本。[R17][R18]

## 16.2 内容 设计和数据的权利

建立 rights_record：作者、原始来源、获取日期、许可原文及哈希、可商用、可改编、可分发图纸和动画、可用于训练、署名、地域期限、撤回与争议状态。折纸成品设计、图纸、摄影、视频、文字和角色品牌各自记录，不认为“折法公开”即可复制整套教程。

在线教程初期仅做合法索引和来源跳转；结构化改编需要明确权限。用户投稿与实验上传默认不赋予公开传播或训练权。商业角色和商标需求可用泛化造型替代，并在必要时取得授权。license manifest 未通过或授权到期的版本停止新下载，并保留已购用户处理和替代方案记录。

## 16.3 商业验证路线

首批定位为“能折完的个性化折纸教学”，测试用户是否愿意为可靠教程、难度选择、离线包及参数变体付费。先用访谈和小规模邀请验证，再决定订阅、单个模型包或教育机构授权；不在尚未稳定生成时出售“任意物体无限生成”。

建议首轮访谈 15 至 20 人，邀请测试至少 30 人；记录用户实际完成任务后的付费意愿，而非只问“觉得 AI 折纸有趣吗”。定价属于待验证变量，可用假设价测算毛利，不把文档中的数值当市场定价。用户留存与完成率低时先改善教学，不能用更复杂目标掩盖核心体验问题。

## 16.4 90 天预算和单位经济

预算按已有电脑、创始人每周约 25 小时、无常驻 GPU、月约 1,000 次受限任务的假设编制。下表是内部规划额度，不是云厂商或服务商报价；支付、应用商店、税费、法律服务及重大外包另计。

为以上支出另预留 30%，90 天运行预算约 4,300 至 17,200 元。基础折法设计和商用授权若需外购，单列内部暂定储备 2,000 至 10,000 元；该数值只用于预算情景，采购前取得实际报价和合同。创始人约 325 小时的时间成本必须计入商业分析，不能因没有工资支出就视为零成本。

C_job = C_parse + Σ(C_generate + C_validate + C_simulate) + C_package + C_storage；C_completed = 总服务成本 / 独立完成的用户任务数。看板同时记录 token、CPU 秒、候选数、缓存率、失败和完成。预算达到 80% 停止非必要研究，达到上限停止新增付费调用并保留已提交任务的可解释状态。

毛利测算还须扣除支付、分成、授权摊销、内容维护和客服。若连续两周每个独立完成任务的成本高于目标收入可承受范围，先缩候选、预计算和收窄类别；仍不改善则暂停自动生成商业承诺。

# 17 30 60 90 天执行计划

## 17.1 产能安排

Day 1 是实际启动日，不是文档日期。每周约 25 小时可用时间中，建议 8 小时用于纸张实验与用户观察、8 小时用于 AI 任务管理和集成、5 小时用于评审与回归、4 小时用于产品和来源。若只能投入每周 10 小时，按实际比例延长计划；不能把真人折叠和验收全部挤掉。

## 17.2 前 30 天

Day 30 不达标时最多安排一次两周的明确修复冲刺，写出唯一阻塞与验收。没有可验证改进路径就改为受控教程工具，不继续无期限增加 Agent 或模型调用。

## 17.3 Day 31 至 60

Day 60 目标：PoC 稳定，至少一至三类实际可用，五类规格完整；资源允许才完成五类基础实现。发布清单只列通过验证的类别。工程门槛是复用编译器、协议与播放器，不能每类都重新开发一套动画。

## 17.4 Day 61 至 90

Day 90 只允许三种结论：继续扩大已验证类别；保持现有范围改善教学和作者成本；停止生成路线投入并转为已验证教程与设计工具。不得以“未来 AI 会解决”作为继续投入的唯一理由。

## 17.5 下一个工作日即可启动的清单

建立私有仓库与 main 保护；写出 docs/01_PRODUCT.md 的支持与拒绝示例；选择一种 200 mm 正方形材料并登记；确定 Q4-B01 的合法来源；让核心 AI 建 schema 和空目录预检，让 QA AI 同时编写非法几何与穿透反例。创始人当日只需验收明确范围、首个纸样来源和未来三天的任务，不必先批准完整 APP 页面设计。

# 18 测试体系与验收指标

## 18.1 关键测试用例

T08 的具体反例应为同一重叠单元中 A>B、B>C、C>A。T10 若当前验证器仅支持离散采样，其验收必须使用足够细分能检出的已知反例，并在报告声明连续覆盖不足；不得声称通用连续碰撞保证。反例 fixture 与修复一起保留，防止后续回归。

## 18.2 不变量与性质测试

对有限合法参数随机采样，检查刚性区域度量守恒、对称约束、ID 引用完整、源哈希一致及动作前后状态连接。对支持的可逆宏做 round-trip 数值检查，但逆向可播放不代表真人能逆向恢复。把输入扰动、阈值边界和极小面片纳入测试；失败 seed 写入固定回归集。

协议做 Python→JSON→TypeScript→JSON 的往返测试，验证山谷符号、单位、面环方向和三角化映射。API 重点测鉴权、幂等、配额、取消和恢复。UI 重点测可学习流程，不以大量镜像实现的快照测试代替端到端。

## 18.3 分阶段验收表

表中 PoC 的 9/12 和单配置 2/4 是 project_go_gate，仅支持继续研发；对用户公开发布仍须分别满足第 9.3 节 preset_release_gate。预检 CLI 的缺字段错误接入 API 时需转为第 12 章统一错误，不能把原始堆栈返回用户。

p95 等性能目标需记录样本数、并发、网络、是否缓存及数据规模。超时任务必须进入失败或未决统计，不能从延迟分母删除。V0.5 完成率指标以至少 30 名独立用户首次任务为主，分层结果和置信区间必报，不以所有重复试折次数当独立样本。

## 18.4 发布验收模板

Release ID / commit / manifest hash

支持的 base preset 材料和协议

本次产品行为及限制

自动检查 通过 失败 unknown 及原因

专家与用户实折证据及适用范围

基线设备和性能样本

新引入依赖及权利检查

任务失败和已知缺陷

备份恢复与回滚演练

创始人决定  发布 仅邀请测试 或退回修复

模板中的 unknown 必须逐项说明是否为产品必需检查；必需项未决就不能公开标为已验证。允许降级的内容必须有独立、已经实折的替代教学包，不能以降级名义绕过正确性。

# 19 风险矩阵 退出条件与决策标准

## 19.1 风险矩阵

概率和影响使用 1 至 5 的工程初评，相乘用于排序，不代表统计概率。每周更新；实际故障发生后要用证据调整而非保持初值。

## 19.2 单次任务退出条件

达到候选数、时间、内存、迭代或 API 费用上限；发现硬几何错误、不可解层序、未覆盖的关键动作、授权缺失或证据哈希不匹配；用户取消；依赖服务超过重试预算。退出产物要保留阶段、已消耗预算和原因，不产生半个“成功教程”。

## 19.3 项目 Go Conditional Go No Go

项目退出不等于放弃全部资产：FOLD profile、播放器、作者工具和已授权教程仍可服务教学产品。必须停止的只是缺乏证据的自动生成承诺；研究沙箱可在独立预算下保留。

# 20 最终可行性分析与启动决定

技术上，限定拓扑和动作域的参数化设计、模板化序列、确定性几何检查以及交互播放器可以组成可执行方案；最先要解决的是基础模型资产和真人教学，而不是选择更大的语言模型。统一协议、不可变版本和分级验证能使各 AI 的工作互相接合，降低一人公司的集成成本。

研发上，通用全局可折判定、复杂接触和任意 CP 的人类序列仍是高风险问题。把这些问题约束在受支持的 base 和宏动作内，是近期可靠性的主要来源。V2.0/V3.0 以研究阶段门推进，不应成为首个付费版本的前置依赖。

商业上，可靠性、可完成率、内容授权、作者效率和用户愿付成本尚需实验。首期采用 30 天有条件投入，满足 PoC 门槛再扩大至 90 天；90 天决定继续、缩域或退出生成路线。主张为“有限范围内可解释、可验证、可学习的折纸生成”，每次扩域都补上与新增能力对应的证据。

启动顺序为：确认 Q4-B01 的合法纸样与材料；冻结 Target/FOLD/Sequence 合同；同源编译并实现几何与路径反例；跑通播放器和 APP；进行真人实验。只要第一道纸样门槛未过，就不把后续动画展示当成系统成功。

# 21 研究与官方资料

以下链接用于研究、能力和许可复核，访问核查日期为 2026 年 10 月 17 日。软件采用时仍需固定具体版本与 commit。本文的架构、阈值、预算和里程碑属于实施建议，外部研究并未替本项目验证这些工程假设。

[R1] Robert J. Lang  TreeMaker 官方介绍。https://langorigami.com/article/treemaker/

[R2] Tomohiro Tachi  Origamizing Polyhedral Surfaces  IEEE TVCG 16(2) 298–311 2010  DOI 10.1109/TVCG.2009.67。https://tsg.ne.jp/TT/cg/OrigamizingPolyhedralSurfaces_tachi_IEEETVCG.pdf

[R3] FOLD 官方规范 1.2  字段和 Custom Properties。https://github.com/edemaine/fold/blob/main/doc/spec.md

[R4] Amanda Ghassaei 等  Origami Simulator 作者仓库及方法说明。https://github.com/amandaghassaei/OrigamiSimulator

[R5] Yanjia Huang 等  Learn2Fold Structured Origami Generation with World Model Planning  arXiv:2603.29585v2  2026。https://arxiv.org/html/2603.29585v2

[R6] Erik Demaine  Origami Foldability  作者综述；Hugo A. Akitaya 等  Computing Flat Folded States  OSME 2024。https://erikdemaine.org/papers/OSME2001/paper.pdf ； https://erikdemaine.org/papers/FlatFolder_OSME2024/paper.pdf

[R7] FastAPI  Background Tasks  重计算与独立工具。https://fastapi.tiangolo.com/tutorial/background-tasks/

[R8] Flutter 官方维护  webview_flutter  支持平台 API 及许可。https://pub.dev/packages/webview_flutter

[R9] PostgreSQL  Row Security Policies。https://www.postgresql.org/docs/current/ddl-rowsecurity.html

[R10] TreeMaker 作者源码仓库  README  GPL version 2 or later。https://github.com/bugfolder/TreeMaker

[R11] Tomohiro Tachi  Software  官方使用条款和商业联系说明。https://www.tsg.ne.jp/TT/software/

[R12] FOLD  MIT License。https://github.com/edemaine/fold/blob/main/LICENSE

[R13] Origami Simulator  MIT License。https://github.com/amandaghassaei/OrigamiSimulator/blob/main/LICENSE

[R14] FastAPI  官方仓库及许可。https://github.com/FastAPI/FastAPI

[R15] Three.js  MIT License。https://github.com/mrdoob/three.js/blob/dev/LICENSE

[R16] PostgreSQL  官方许可证。https://www.postgresql.org/about/licence/

[R17] Redis  官方许可总览及版本区别。https://redis.io/legal/licenses/

[R18] Valkey  官方介绍及 BSD 许可。https://valkey.io/docs/topics/introduction/

[R19] GNU  GPL Frequently Asked Questions。https://www.gnu.org/licenses/gpl-faq.en.html

[R20] Three.js  WebGLRenderer  WebGL2 要求。https://threejs.org/docs/pages/WebGLRenderer

[R21] Flutter  在 Web 页面嵌入 Web 内容。https://docs.flutter.dev/platform-integration/web/web-content-in-flutter

[R22] Celery  Tasks  幂等与任务确认。https://docs.celeryq.dev/en/stable/userguide/tasks.html


<!-- Table 1 -->

| 项目 | 明确约定 | 对实现的约束 |

| --- | --- | --- |

| 核心价值 | 输入目标后获得可实际学习的折纸近似方案 | 搜索命中和生成成功分开统计 |

| 默认材料 | 单张正方形纸，不剪切、不粘贴 | 多纸、裁剪、湿折必须另列模式 |

| 初始用户 | 具有基础对折能力的成人或青少年自学者 | 不以低龄儿童数据替代早期验证 |

| 形似目标 | 优先突出轮廓和标志部件 | 不承诺照片级细节或商标复刻 |

| 正确性 | 硬校验优先于相似度和评分 | 不可行候选不得靠高分抵消 |

| 教学产物 | 结构、动作、状态、文字和动画版本一致 | 每一步均可回放和追溯 |

| 生成范围 | 当前 generator manifest 明示的拓扑和参数域 | 未支持目标必须回退或拒绝 |

| 发布条件 | 自动检查通过且具有对应实折证据 | 模拟通过不自动等于可发布 |


<!-- Table 2 -->

| 能力 | 一手研究或项目 | 可以借鉴 | 不能据此承诺 |

| --- | --- | --- | --- |

| 树状折纸设计 | Lang Tree Method 与 TreeMaker [R1] | 把附肢长度及连接关系转为 base 设计问题 | 一个四足骨架可任意长出耳、鼻、角 |

| 多面体逆向设计 | Tachi Origamizer [R2] | 从目标多面体设计单张纸折痕 | 自动得到初学者教程和短路径 |

| 通用数据交换 | FOLD 官方规范 [R3] | 折痕、面、角度、帧与层序交换 | 格式合法即物理可折 |

| 实时数值仿真 | Origami Simulator [R4] | GPU 迭代、折痕驱动、预览 | 无穿透路径证明或真人可折证明 |

| 神经符号序列 | Learn2Fold 预印本 [R5] | 候选程序、世界模型、前瞻搜索 | 任意物体到教学方案已成熟 |

| 全局折叠判定 | 计算折纸复杂性研究 [R6] | 使用限制问题、搜索预算和证据分级 | 存在覆盖所有模型的简单万能检查 |


<!-- Table 3 -->

| 层面 | 判断 | 立项条件 |

| --- | --- | --- |

| 产品闭环 | 条件可行 | 限定类别、可靠回退、可学习的动画 |

| 参数化工程 | 条件可行 | 先获得已验证 base 和动作资产 |

| 一人公司交付 | 可执行但产能受限 | 一条主线、最多两个实现任务并行 |

| 真人教学质量 | 必须实验 | 新手成功率和失败步骤可追溯 |

| 任意目标逆向生成 | 高不确定研究 | 独立预算，不能阻塞主营产品 |

| 商业成立 | 尚待验证 | 留存、付费意愿、生成成本与授权成本 |


<!-- Table 4 -->

| 模块 | 输入 | 输出 | 失败处理 |

| --- | --- | --- | --- |

| Text Parser | 文本、用户限制 | TargetSpec | 低置信时澄清或推荐相近目标 |

| Target Representation | 语义结果 | 部件图、必需和可省略特征 | 未知拓扑不自动编造 |

| Strategy Router | TargetSpec、能力清单 | RouteDecision | 返回 UNSUPPORTED_TARGET |

| Parametric Generator | base 版本、受限参数 | DesignProgram | 超域拒绝并说明限制 |

| Candidate Generator | 程序、seed、预算 | CandidateBundle 列表 | 保留失败原因与样本统计 |

| Geometry Validator | CP 和目标状态 | ValidationReport L1/L2 | fail 或 unknown |

| Fold Simulator | CP、动作草案、材料 | 轨迹、残差、接触事件 | 超时保留 unknown |

| Human Score | 轨迹、动作、纸张 | 风险项、H 分、证据等级 | 数据不足标待验证 |

| Sequence Planner | 动作模板、状态图 | CompiledSequence | 无路径则停止发布 |

| Tutorial Generator | 已确定动作、术语 | 逐步文案和标注 | 使用确定性模板兜底 |

| Animation Engine | 轨迹、摄像机、标注 | 播放资产包 | 失败显示验证过的图文 |

| Flutter APP | manifest 和资产 | 学习体验及事件 | 离线缓存、进度恢复 |


<!-- Table 5 -->

| 优先级 | 条件 | 路线 | 输出要求 |

| --- | --- | --- | --- |

| 1 | 精确命中已发布设计 | 检索已验证版本 | 明确“已验证方案” |

| 2 | 拓扑及参数处于认证域 | 参数化生成 | 重新编译和自动验证 |

| 3 | 需求可由相近基础模型表达 | 语义近似 | 列出省略特征供用户选择 |

| 4 | 需要新 flap 或新 base | 人工设计队列 | 不返回假生成结果 |

| 5 | Tree 或网格逆向实验 | 研究沙箱 | 禁止默认生产发布 |


<!-- Table 6 -->

| 生成器 | V0.1 基础模型 | 可调项目 | 必须锁定或约束的项目 |

| --- | --- | --- | --- |

| Quadruped | 原创或获授权的四腿带头尾模型 | 头颈姿态、尾角、已验证的局部修形 | flap 数、纸面度量、腿层分配 |

| Bird | 一个具有双翼和头尾的 base | 翼展开角、颈部姿态、尾部开合 | 不能凭角度产生新的翼尖或长颈 |

| Fish | 一个鱼身及尾鳍 base | 尾开角、体侧修形、头角 | 鲨鱼背鳍需对应真实 flap |

| Flower | 一个经过实折的放射花形 | 花瓣开合及允许的卷曲姿态 | 花瓣数量属于离散拓扑选择 |

| Box | 无剪切单纸开口盒 base | 合法折线位置及成品宽高 | 宽深高相互耦合，厚纸留隙 |


<!-- Table 7 -->

| 字段 | 使用约定 | 检查 |

| --- | --- | --- |

| file_spec 与 file_creator | 标准版本及生成工具 | 不冒充第三方工具 |

| vertices_coords | 同一帧二维或三维坐标 | 维度一致、数值有限 |

| edges_vertices | 两端顶点下标 | 范围合法、无零长边 |

| edges_assignment | B/M/V/F/U 等标准赋值 | 按规范枚举校验 |

| edges_foldAngle | 度；V 为正、M 为负 | 与 assignment 保持一致 |

| faces_vertices | 面顶点有序索引 | 面简单、面积大于容差 |

| faceOrders | 重叠面的相对顺序约束 | 只按官方方向语义写入 |

| file_frames | 子帧和继承关系 | frame_parent 无环 |


<!-- Table 8 -->

| 扩展或文件 | 内容 | 约束 |

| --- | --- | --- |

| go:schema_version | 自有协议版本 | 与 FOLD 版本分开演进 |

| go:stable_ids | vertex/edge/face 稳定 ID 映射 | 数组重排不能改变语义引用 |

| go:provenance | 来源、版本、license manifest 引用 | 不含用户隐私 |

| sequence.json | 宏动作、前后状态、移动层、依赖 | 不用渲染面序号代替稳定 ID |

| trajectory | 关节角轨迹、关键帧、接触事件 | 记录时间与 solver 版本 |

| validation.json | 各检查状态、指标、容差和证据 | pass/fail/unknown/not_applicable |

| tutorial.json | 文案、语音、箭头、摄像机、检查点 | 不得独立创造几何动作 |

| manifest.json | 哈希、尺寸、兼容性、发布信息 | 发布后不可变 |


<!-- Table 9 -->

| 等级 | 内容 | 产物 | 不能证明 |

| --- | --- | --- | --- |

| L1 | schema、拓扑、边界、度量及适用局部条件 | 静态检查报告 | 全局路径存在 |

| L2 | 折叠状态残差、相交、接触与层序 | 状态和接触证据 | 从初态可达 |

| L3 | 动作路径、扫掠碰撞、接触变化 | 经验证的轨迹 | 真实材料一定成功 |

| L4 | 真人按教程完成及困难记录 | 实折证据与完成数据 | 所有用户必然成功 |


<!-- Table 10 -->

| 动作类别 | 初始支持方式 | 发布要求 |

| --- | --- | --- |

| 谷折和山折 | 单铰链或已定义的多面组联动 | 明确轴、运动侧、固定侧和角路径 |

| 预折和展开 | 成对模板与折痕激活状态 | 保留折痕及准确参考线 |

| 翻纸和转纸 | 整体刚体操作 | 与摄像机变化区别显示 |

| 内翻和外翻 | base 专用宏动作 | 有完整中间轨迹和实折证据 |

| 压折和花瓣折 | 离线编写的复杂宏 | 可拆步，不把弯曲伪装成刚性 |

| 塞入和拉开 | 暂时限定已认证模板 | 明确入口纸层、可触达空间 |


<!-- Table 11 -->

| 风险项 | 初始计算方式 | 数据来源 |

| --- | --- | --- |

| r_steps | clip((主要动作数−15)/45) | 编译后的完整序列 |

| r_size | clip((10−最小操作宽度mm)/8) | 几何与指定纸张尺寸 |

| r_layers | clip((最大接触层数−4)/12) | 局部接触区域 |

| r_precision | clip((2−容许定位误差mm)/1.8) | 宏动作误差实验 |

| r_access | 已标记难触达操作数/操作总数 | 专家标注与用户卡点 |

| r_complex | clip(复杂宏动作加权数/10) | 内翻、压折、塞入等 |


<!-- Table 12 -->

| 实体 | 必需记录 | 用途 |

| --- | --- | --- |

| DesignCase | base、preset、版本、几何及难度特征 | 保证实验对象可复现 |

| PaperProfile | 边长、厚度测量、克重、批次、环境备注 | 解释厚纸和尺寸差异 |

| Participant | 匿名 ID、经验层、惯用手、同意状态 | 分层，不收多余身份数据 |

| FoldTrial | 指定版本、开始结束、成功/失败/退出 | 计算完成率和时间 |

| StepAttempt | 卡点、重播、回退、求助、误差 | 找到具体失败动作 |

| OutcomeReview | 成品照片、结构完整、独立辨识结果 | 区分完成和像不像 |

| EvidenceAsset | 授权媒体、访问权限、保留期限 | 复核与内容制作 |


<!-- Table 13 -->

| 层 | 建议技术 | 初始职责 |

| --- | --- | --- |

| 几何原型 | Python、NumPy、SciPy、专用网格代码 | 参数、约束、轨迹与验证 |

| API | FastAPI、Pydantic、SQLAlchemy、Alembic | 合同、鉴权、事务与迁移 |

| 数据 | PostgreSQL、Redis | 持久事实、队列通知和缓存 |

| 动画 | Three.js、WebGL、TypeScript | 材料面片、轨迹回放、标注 |

| 移动端 | Flutter 与受支持的 WebView 插件 | 页面、学习状态和下载 |

| 质量 | pytest、Flutter test、播放器回归 | 几何反例、协议和端到端 |


<!-- Table 14 -->

| 页面 | 核心内容 | 必须处理的异常 |

| --- | --- | --- |

| 输入页 | 目标、纸张、难度、支持范围 | 模糊描述、敏感权限拒绝 |

| 任务页 | 当前阶段、可取消、超时说明 | 断网重连、任务失败、配额超限 |

| 候选页 | 真实差异、步骤、验证范围 | 少于三个候选、无可靠结果 |

| 作品页 | 成品、纸张、来源、限制 | 旧版本下架、授权失效 |

| 播放器 | 当前动作、操作层、检查点 | 资产损坏、WebGL 不支持 |

| 我的学习 | 收藏、本地下载和版本进度 | 多设备进度冲突、缓存过期 |


<!-- Table 15 -->

| 表 | 核心字段 | 约束与索引 |

| --- | --- | --- |

| users | id、subject_id、role、created_at | subject_id 唯一 |

| targets | id、canonical_name、family、aliases | 名称别名检索索引 |

| generators | id、family、capability_manifest | 启用状态受审核控制 |

| generator_versions | id、generator_id、version、commit_sha | generator_id 与 version 唯一 |

| base_asset_versions | id、base_id、version、artifact_id、rights_id | 版本不可原地覆盖 |

| generation_jobs | id、user_id、request、status、idempotency_key | 用户与幂等键唯一 |

| candidates | id、job_id、design_version_id、rank、reject_code | job_id 与序号唯一 |

| designs | id、target_id、owner_id、visibility | 私有与公开权限隔离 |

| design_versions | id、design_id、version、base_id、params、hash | design_id 与 version 唯一 |

| validation_runs | id、design_version_id、policy、status、report | 版本、材料和时间索引 |

| tutorial_versions | id、design_version_id、locale、sequence_hash | 版本和语言唯一 |

| tutorial_steps | tutorial_version_id、step_no、stable_id、action | 教程与步号唯一 |

| artifacts | id、sha256、storage_key、size、media_type | sha256 与存储作用域索引 |

| rights_records | id、source、license、commercial_ok、evidence | 到期和撤回状态 |

| fold_trials | id、participant_id、tutorial_version_id、outcome | 绑定 consent 和材料 |

| step_attempts | trial_id、step_id、attempt_no、event | 防重采集键 |

| learning_progress | user_id、tutorial_version_id、step_id、revision | 复合主键与乐观锁 |

| favorites | user_id、design_id、created_at | 复合主键 |

| tutorial_requests | target、normalized_key、count、status | 归一需求键唯一 |

| outbox_events | id、job_id、event_type、delivered_at | 未投递部分索引 |

| audit_events | actor、action、resource、version、time | 只追加及受控访问 |


<!-- Table 16 -->

| 方法及路径 | 职责 | 成功响应 |

| --- | --- | --- |

| GET /v1/capabilities | 类别、材料、支持的参数域 | 200 及版本 |

| POST /v1/targets/parse | 文本转 TargetSpec | 200 或 needs_clarification |

| POST /v1/generations | 幂等创建生成任务 | 202 和 job_id |

| GET /v1/jobs/{id} | 查询阶段、结果及失败原因 | 200 |

| POST /v1/jobs/{id}/cancel | 请求取消可中断任务 | 202 或已终态 |

| GET /v1/designs/{id}/versions/{v} | 固定版本候选摘要 | 200 |

| GET /v1/designs/{id}/versions/{v}/bundle | manifest 和下载地址 | 200 |

| GET /v1/tutorials/{id}/versions/{v} | 步骤、语言和检查点 | 200 |

| PUT /v1/progress/{tutorial_version_id} | 带 revision 更新进度 | 200 或 409 |

| PUT 与 DELETE /v1/favorites/{design_id} | 幂等收藏或取消 | 204 |

| POST /v1/trials | 同意后的试折记录 | 201 |

| POST /v1/requests | 未覆盖需求 | 201 或累计结果 |

| POST /v1/admin/releases | 内部提交发布审核 | 202 和审核状态 |


<!-- Table 17 -->

| 状态或错误 | 语义 | 客户端动作 |

| --- | --- | --- |

| 401 / 403 | 未认证或无权限 | 登录或返回可访问页面 |

| 404 | 无资源或不披露存在性 | 提示资源不可用 |

| 409 | 幂等冲突或进度 revision 冲突 | 获取当前状态后确认更新 |

| 413 / 422 | 输入过大或 schema 不合法 | 指出可修改字段 |

| 429 | 用户配额或并发超限 | 按 Retry-After 重试 |

| NO_VERIFIED_CANDIDATE | 已处理但无可靠候选 | 显示替代目标与需求入口 |

| SIMULATION_TIMEOUT | 当前预算未得出结论 | 标注未决，不说物理不可折 |

| RIGHTS_NOT_CLEARED | 来源权利未完成 | 不提供受限资产下载 |

| 503 | 计算或存储暂不可用 | 保留任务 ID，可恢复重试 |


<!-- Table 18 -->

| 版本 | 主要能力 | 必须交付 | 进入下一阶段的条件 |

| --- | --- | --- | --- |

| PoC-01 | 一个四足 base 的可验证变体 | 三个配置、统一包、实折和用户实验 | 第 14 章门槛达标 |

| V0.1 | 五类参数化生成器框架 | Quadruped/Bird/Fish/Flower/Box 规格及基础实现 | 上线的每类均有完整验证资产 |

| V0.5 | 真人可折性筛选和测试闭环 | H 分、失败样本、材料档案、邀请测试 | 新手指标、成本与恢复演练达标 |

| V1.0 | 限定域内自动序列编译和统一动画 | 模板展开、宏组合、Flutter 完整闭环 | 冻结测试集通过且允许商用 |

| V2.0 | 检索与算法生成混合 | 多 base、受限 Tree/Box Pleating、局部规划 | 新 base 复用成本和路径可靠性可接受 |

| V3.0 | Text→Mesh→逆向折纸研究 | 网格简化、逆向 CP、教学复杂度优化 | 独立复现、许可、路径及真人验证 |


<!-- Table 19 -->

| 资产 | 具体要求 | 验收证据 |

| --- | --- | --- |

| Q4-B01 原始纸样 | 固定 200 mm 正方形纸及材料批次 | 成品和展开纸照片 |

| 权利记录 | 创作者、来源、允许用途、凭证 | rights_record 与文件哈希 |

| CP | 全部真实折痕、山谷、边界和正反方向 | FOLD 与展开纸交叉复核 |

| 宏动作程序 | 从展开纸到完成态，每步可定位 | 全程录像和结构化步骤 |

| 语义映射 | 四腿、身体、头尾对应的纸面区域 | 稳定面 ID 与标注图 |

| 轨迹 | 关键状态、合法接触和复杂过渡 | 检查点与仿真报告 |

| A/B/C 配置 | 三个邻近且可重复的造型或修形变体 | 每配置两次专家复折 |

| 教学包 | 文案、参考线、摄像机与错误提示 | 非作者完整试做 |


<!-- Table 20 -->

| 输入 | PoC 接受方式 | 实际输出 |

| --- | --- | --- |

| target_label | dog、fox 或简化动物意图 | 仅发布经辨识测试的名称 |

| paper_profile_id | 首轮固定 paper-200-01 | 记录具体材料和厚度 |

| body_to_leg_ratio | 目标视觉比例 | 映射至 A/B/C 的实际比例 |

| neck_to_body_ratio | 仅用于判断结构需求 | 超出 base 能力则拒绝 |

| head_variant | 离散已验证修形宏 | 不新增没有纸源的耳或鼻 |

| tail_variant | 离散已验证配置 | 保留实际可完成的尾角 |

| stance_variant | 已实折站姿 | 不对成品随意非刚性缩放 |

| max_steps | 排序偏好 | 不通过隐藏子步骤达标 |


<!-- Table 21 -->

| 编号 | 交付 | 主责 AI 或真人 | 可验收结果 |

| --- | --- | --- | --- |

| P01 | base 选择与权利记录 | 创始人及折纸协作者 | 可商用来源和实物 |

| P02 | CP 与宏动作录入 | 几何 AI 辅助真人 | 展开图和录像对应 |

| P03 | Target 与 FOLD profile schema | 核心 AI | 合法及非法 fixture |

| P04 | 稳定 ID 和同源编译器 | 核心 AI | 共享程序源哈希且各产物哈希正确 |

| P05 | L1/L2 验证器 | 验证 AI | 拒绝明确几何与层序反例 |

| P06 | 三个配置的轨迹 | 图形 AI 及真人 | 支持动作路径可复核 |

| P07 | L3 碰撞与未知状态 | 验证 AI | 中途穿透反例能检出 |

| P08 | Three.js 逐步播放器 | 客户端 AI | 暂停跳步和状态恢复 |

| P09 | FastAPI 任务与目录 API | 后端 AI | 幂等和中断恢复 |

| P10 | Flutter 最小闭环 | 客户端 AI | 实机完成一个教程 |

| P11 | 复折与 12 人实验 | 创始人及 QA AI | 原始记录和失败分母 |

| P12 | Gate 报告和下一步 | 总控 AI 及创始人 | Go 或有依据的收缩决定 |


<!-- Table 22 -->

| 角色 | 主要职责 | 必须提交 |

| --- | --- | --- |

| 创始人 | 目标、权利、实物、预算、合并和发布 | 决策、验收记录、授权凭证 |

| 总控 AI | 拆任务、依赖、ADR、事实源一致性 | 任务板、接口决定、Gate 报告 |

| 核心与后端 AI | 生成器、几何、API、数据和 worker | 代码、迁移、协议及测试证据 |

| Flutter 与图形 AI | APP、Three.js、bridge、作者工具 | 实机演示、协议与性能数据 |

| 内容与研究 AI | 来源、许可、宏动作标注、教学语言 | 来源表、教学包、实验脚本 |

| QA AI | 独立反例、回归、故障和验收 | 缺陷、复现步骤、通过证据 |


<!-- Table 23 -->

| 对象 | 核实情况 | 本项目执行规则 |

| --- | --- | --- |

| TreeMaker | 作者仓库声明 GPL-2.0-or-later [R10] | 商用可行；复制或分发前确定 GPL 履行方案 |

| Tachi 软件 | Origamizer 等为专有软件，默认非商用、需联系和署名 [R11] | 未获匹配书面许可，不作商业生产依赖 |

| FOLD | 官方仓库 MIT [R12] | 保留通知，schema 版本及来源可追溯 |

| Origami Simulator | 作者仓库 MIT [R13] | 固定 commit 并审计依赖与示例资产 |

| FastAPI | MIT [R14] | 保留通知，第三方依赖独立登记 |

| Three.js | MIT [R15] | 保留通知；其许可不覆盖教程媒体 |

| Flutter WebView 插件 | 官方插件 BSD-3-Clause [R8] | 核对锁定版平台支持和 notice |

| PostgreSQL | PostgreSQL License [R16] | 保留通知，扩展另审 |

| Redis 服务端 | 按版本使用不同许可 [R17] | 不能写为 MIT，记录实际选择及部署方式 |

| Valkey 可选替代 | BSD 许可 [R18] | 如需替代，先做队列和运维兼容测试 |


<!-- Table 24 -->

| 项目 | 月预算人民币 | 控制措施 |

| --- | --- | --- |

| API worker 数据和备份 | 300 至 1,200 | 小环境、限时计算、按需扩容 |

| AI 开发席位和 API | 500 至 2,000 | 固定月上限、减少重复上下文 |

| 监控和域名摊销 | 0 至 200 | 限制日志、优先已有工具 |

| 测试补贴和纸张 | 300 至 1,000 | 周度小样本、失败即修正 |

| 合计 | 1,100 至 4,400 | 90 天约 3,300 至 13,200 |


<!-- Table 25 -->

| 时间 | 核心任务 | 交付物 | 决策门 |

| --- | --- | --- | --- |

| Day 1 至 3 | 仓库、docs、能力边界、base 和材料 | 产品基线、权利方案、任务卡 | 选定可获得的合法 base |

| Day 4 至 10 | Q4-B01 实物、CP、宏步骤、关键帧 | 基准实折包和权利凭证 | 无可复折 base 则停止扩建 |

| Day 11 至 15 | schema、稳定 ID、同源编译、预检 | FOLD/Sequence fixture 和编译器 | 几何与步骤引用一致 |

| Day 16 至 20 | L1/L2、轨迹、播放器和反例 | 检查报告和可回放包 | 中途碰撞不能被漏掉 |

| Day 21 至 25 | A/B/C、两次专家复折、API 最小闭环 | 三个固定配置和教程 | 证据匹配设计版本 |

| Day 26 至 30 | 12 人测试、修正、Gate 报告 | 原始数据、失败清单和结论 | 按 PoC 标准 Go 或收缩 |


<!-- Table 26 -->

| 周次 | 工作重点 | 可交付证据 |

| --- | --- | --- |

| 第 5 周 | PoC 卡点修正、作者工具、导出自动化 | 新增 preset 不再手动复制多个文件 |

| 第 6 周 | Bird 或 Fish 的第二个 base | 至少一个新族完整实折包 |

| 第 7 周 | Flower 和 Box 专属约束、五类 manifest | 各类别能力清单，未达标的禁用 |

| 第 8 周 | Flutter 实机、离线包、收藏和进度 | 首个用户可自行走完整闭环 |


<!-- Table 27 -->

| 周次 | 工作重点 | 可交付证据 |

| --- | --- | --- |

| 第 9 周 | H 分特征、实验采集和失败定位 | 特征缺失规则和实验数据字典 |

| 第 10 周 | 30 名独立用户、累计 60 次试折 | 分组完成率、耗时、求助和辨识 |

| 第 11 周 | 断网、崩溃、worker 重试和权限 | 故障注入及恢复报告 |

| 第 12 周 | 许可清单、成本、付费访谈和发布候选 | SBOM、单位经济、邀请版本 |

| 第 13 周 | 冻结版本验收和下一阶段决定 | V0.5 Gate 与 V1.0 任务板 |


<!-- Table 28 -->

| 编号 | 用例 | 期望结果 |

| --- | --- | --- |

| T01 | 支持的短颈四足目标 | 返回范围内且证据完整的候选 |

| T02 | 三头龙带翅膀长鼻 | 明确不支持或让用户选近似 |

| T03 | 未认证纸张、过小尺寸、超域比例 | 不外推可折性承诺 |

| T04 | NaN、越界索引、重复稳定 ID | schema 或拓扑失败并定位 |

| T05 | CP 折线相交未切分、零长边 | L1 失败 |

| T06 | 成品顶点拉伸但外观正确 | 度量检查失败 |

| T07 | 局部角条件通过、全局层序冲突 | L2 拒绝，不能靠局部 pass 覆盖 |

| T08 | 同一重叠区域 A>B、B>C、C>A | 检出层序矛盾 |

| T09 | 合法共享铰链接触 | 不误报整对面片碰撞 |

| T10 | 首尾无碰撞、中途穿透 | 路径检查检出或明确未覆盖 |

| T11 | 翻折需柔性过渡但只提供刚体模型 | 返回 unknown 或切换认证宏 |

| T12 | 教学引用不存在的边或错误纸层 | 编译和导出被阻止 |

| T13 | 相同程序 seed 与锁定环境重编译 | 规范化产物一致或记录可接受误差 |

| T14 | manifest 哈希错误或旧主协议 | 播放器拒绝并可恢复 |

| T15 | 同幂等键同输入及不同输入 | 复用原任务；冲突返回 409 |

| T16 | worker 在上传后提交前崩溃 | 重试不重复发布和扣费 |

| T17 | Redis 重启与消息重复 | 从事实源恢复，副作用幂等 |

| T18 | 用户 A 读取用户 B 私有 job/媒体 | 拒绝访问，不泄露文件路径 |

| T19 | 暂停跳步、退出重开、断网、旋转 | 恢复同教程版本检查点 |

| T20 | WebGL2 不可用、上下文丢失 | 展示图文降级或清晰恢复入口 |

| T21 | 授权撤回或缺失 notice | 阻止新发布并追踪影响版本 |

| T22 | 真人卡在中途、求助或退出 | 如实计入实验，保留失败步骤 |


<!-- Table 29 -->

| 指标 | PoC 门槛 | V0.5 目标 |

| --- | --- | --- |

| 资产权利和版本 | 发布配置 100% 可追溯 | 上线全部版本可追溯 |

| 程序一致性 | 已知 CP/序列/轨迹错配为 0 | CI 阻止任何错配发布 |

| 专家实折 | 3 preset 各至少 2 次成功 | 每个新 base 和关键边界有证据 |

| 独立用户完成 | 至少 9/12，总体且各 preset ≥2/4 | 首次任务完成 ≥80%，报告区间 |

| 求助 | 需要研究者代折计失败 | 分组报告提示与代折比例 |

| 盲评辨识 | 预定义类别识别 ≥70% | 按家族和具体目标分别统计 |

| 主要动作数 | 初始预算 ≤35 | 不隐藏复杂子步骤以达标 |

| 热缓存 API | 固定环境 p95 ≤1 s | 锁定测试环境和负载 |

| PoC 在线目录命中 | p95 ≤5 s | 与真正冷生成分开统计 |

| 冷生成 | 有界异步，初始预算 60 s | 超时有明确状态和回退 |

| 播放 | 基线设备 ≥30 fps | 100 次加载无不可恢复崩溃 |

| 新增近邻 preset 成本 | 记录真实工时 | 连续两次 ≤1 人日为优化目标 |

| 恢复 | 演示 worker 崩溃可恢复 | 达到 RPO/RTO 并实际演练 |


<!-- Table 30 -->

| 风险 | 概率×影响 | 最早预警 | 应对与主责 |

| --- | --- | --- | --- |

| 无合法可复折 base | 4×5 | Day 10 纸样仍不稳定 | 换 base 或采购授权；创始人 |

| 参数变化破坏可折性 | 4×5 | 邻近样本频繁失败 | 离散认证、缩域；核心 AI |

| 碰撞或层序漏检 | 4×5 | 实折与仿真矛盾 | 增反例与接触模型；QA/核心 |

| 序列需大量手工修补 | 4×4 | 新配置逐步重画 | 固定宏和作者工具；图形 AI |

| 真人完成率低 | 4×5 | 同一步求助集中 | 拆步、改 base、重测；创始人 |

| 形似程度不足 | 3×4 | 盲评只认出泛化动物 | 新 base 或收窄物种标签；产品 |

| 软件和内容授权受限 | 3×5 | 缺凭证或不允许改编 | 替代组件与独立实现；研究 AI |

| 一人集成负担过高 | 4×4 | PR 积压、事实源分叉 | 两实现分支、缩范围；总控 |

| AI 输出相互矛盾 | 4×4 | 字段、ID 和单位不一致 | 合同先行、同源编译；总控 |

| 移动端 WebGL2 不稳 | 3×3 | 特定设备黑屏或掉帧 | 能力检测和图文包；客户端 |

| 成本超过收入空间 | 3×4 | 冷任务耗时和 token 攀升 | 预计算、配额、停研究；创始人 |

| 私有媒体或权限泄露 | 2×5 | 跨用户 URL 可下载 | 权限测试、短签名、撤回；后端 |

| 需求不足 | 3×5 | 能折但不愿再使用 | 访谈、聚焦场景、停止扩张；产品 |


<!-- Table 31 -->

| 决策 | 条件 | 资源决定 |

| --- | --- | --- |

| Go | PoC 权利、路径一致、专家实折及用户门槛均满足 | 扩展研发，配置发布仍须单独过门 |

| Conditional Go | 能折且用户能完成，但形似或作者成本弱 | 保持模型范围，限定两周优化 |

| No Go 生成 | 90 天仍无稳定变体，或每次都需重做全流程 | 停止扩大自动生成，转作者工具 |

| No Go 权利 | 无法取得匹配商业用途的资产或软件权利 | 更换来源，不能带病发布 |

| No Go 用户价值 | 两轮修正后完成、辨识或复用意愿仍不达标 | 调整目标用户或停止该产品假设 |

| No Go 单位经济 | 缩候选预计算后成本仍不支持拟定模式 | 停付费冷生成，重新设计商业模式 |