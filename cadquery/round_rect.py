import cadquery as cq
import math

# ========== 可调参数 ==========
side = 100          # 正方形边长 (mm)
thickness = 3       # 拉伸厚度 (mm)

# ========== 计算外接圆半径 R ==========
# 公式：R = (side/2 - r)*sqrt(2) + r 圆角半径 (mm)
r=4
R = (side/2 - r) * math.sqrt(2) + r   # 精确值

# (可选) 打印验证
print(f"外接圆直径: {2*R:.4f} mm")

# ========== 建模：圆 ∩ 正方形 ==========
# 正方形平板
plate = cq.Workplane("XY").rect(side, side).extrude(thickness)

# 圆柱体（半径 R，相同厚度）
cylinder = cq.Workplane("XY").circle(R).extrude(thickness)

# 布尔交集
result = plate.intersect(cylinder)

# ========== 导出与显示 ==========
cq.exporters.export(result, __file__ + f"_circle_sq_side{side}_r{r}_h{thickness}.step")
show_object(result)