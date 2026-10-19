# C3-C 独立端点复核

日期：2026-10-18。复核仅新增本说明和独立静态检查工具，不替换既有运动、证书或设计审计。

## Flat 解析图

独立复查 `singular_bridge.py` 的逆自由转轴乘积方向、Taylor 系数卷积、h/h′/h″ 的指数尾界、二阶 interval jets、局部参数限制后的导数缩放，以及 evaluator 误差进入 joint/vertex/chord 界的路径，未发现当前默认输入与配置下新增的不保守 PASS 路径。

退奇异图使用 `1-x=t²h` 和 `beta=sign*2*asin(t*sqrt(h/2))`，正 h 与反三角分支由整段界证明。其数学运动是理想解析分支，有限 Taylor 是带误差的求值器；两者必须保持此区分。单纯小闭环残差无法证明精确 seam，原有完整误差传播及 exact-seam gate 均须保留。

独立重新执行 `test_singular_bridge.py`：9/9 PASS，耗时 1.420 秒。测试中的采样只用于回归发现问题，不替代解析全区间界。已有 `flat_recheck` 的九个源区间结果可承接，但正式总报告必须验证其 provenance 并合并最终重算证书；不能沿用修改 evaluator contract 前的旧 Flat PASS。

上述意见沿用实现声明的 reference 数值范围：outward nextafter 和明确 libm/FK guard，不是经过验证的 directed interval libm 形式化证明。

## Goal 的固定几何问题

Dog 的边界交点在 `foldgen.py` 被保留十位小数。由实际输入重算，扇区交替约为 0.7853981634324215 与 0.7853981633624749 rad；交替扇区和相对 pi 的差约为 1.39892541995e-10 rad。直接 rigid FK 的全 pi cyclic product Frobenius 残差约为 3.95676882236e-10，与现有 `goal_geometry_diagnostic.json` 相符。这些浮点数本身仅是诊断。

另新增 `tools/audit_c3c_endpoint_geometry.py`，避免依赖上述浮点残差判断静态恒等式。对机制实际存储的每个 unit2 分量取其精确有理数值，使用数学半转矩阵 `H(v)=2vvᵀ/(vᵀv)-I`，按 `[1,2,3,4,5,6,7,0]` 的顺序用 Fraction 精确相乘。无需三角函数即可判定 product 是否精确等于单位阵。

独立结果：**不等于单位阵**，其中非零 P01 约为 -2.7978556015463433e-10。完整精确分数和复现范围写入 `independent_goal_halfturn_audit.json`。它说明该固定轴几何的理想全 pi Goal 不能作为严格闭合的精确端点。此结论限于这个静态端点；不排除邻近端点、修改几何或有限容差桥，也不代表一般折纸不可行。

因此保持 Goal 的 exact chart 构造未证与 UNCERTAIN 是正确处理。不得将近乎重合的虚拟 A/B 轴按精确相等处理，也不得默默把原几何替换为等角几何。若下一轮修复端点，必须明确记录改变的是轴几何、Goal 角度还是认证目标，并重做相关材料 patch、连接及连续认证。