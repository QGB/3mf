import cadquery as cq
from math import sqrt

# === 1. 核心几何参数 ===
w = 102
# 计算相切条件
d_main = -w/2 * (-1 + sqrt(5 - 2*sqrt(6)))
r = d_main / 2
t = r + sqrt((2*r)**2 - (w/2 - r)**2)
g = (t + w/2 + r) / 3

# 计算 8 个圆心坐标 (CadQuery 原点在正中心 0,0，所以要把 KiCAD 的坐标平移 w/2)
coords = [
    (r - w/2, r - w/2),   (w-r - w/2, r - w/2),     # 左上, 右上
    (r - w/2, w-r - w/2), (w-r - w/2, w-r - w/2),   # 左下, 右下
    (t - w/2, 0),         (w-t - w/2, 0),           # 左中, 右中
    (0, t - w/2),         (0, w-t - w/2)            # 上中, 下中
]

# === 2. 生成正方形基板 ===
#基础方块
result = cq.Workplane("XY").rect(w+2, w+2).extrude(10)

# === 3. 批量挖孔 ===
blind_depth = -8

# --- 3.1 挖出 8 个大内孔 (盲孔) ---
# 使用 cutBlind 确保不切穿底部
result = (
    result.faces(">Z").workplane()
    .pushPoints(coords)
    .circle(16 / 2)
    .cutBlind(-10)
)


result = (
    result.faces(">Z").workplane()
    .pushPoints(coords)
    .circle(34.4 / 2)
    .cutBlind(-10+1.5)
)

# --- 3.2 挖出中心矩形分布孔 (通孔, d=3) ---
# 直接在参数中进行 w - 2*g 计算，保持代码精简
result = (
    result.faces(">Z").workplane()
    .rect(w - 2 * g, w - 2 * g, forConstruction=True)
    .vertices()
    .circle(3.0 / 2)
    .cutThruAll()
)

# --- 3.3 挖出交叉长条矩形分布孔 (通孔, d=6) ---
# 纵向分布
result = (
    result.faces(">Z").workplane()
    .rect(28, w - 10, forConstruction=True)
    .vertices()
    .circle(6.0 / 2)
    .cutThruAll()
)
# 横向分布
result = (
    result.faces(">Z").workplane()
    .rect(w - 10, 28, forConstruction=True)
    .vertices()
    .circle(6.0 / 2)
    .cutThruAll()
)

# --- 3.4 挖出最外围分布孔 (通孔, d=3) ---
result = (
    result.faces(">Z").workplane()
    .rect(95, 95, forConstruction=True)
    .vertices()
    .circle(3.0 / 2)
    .cutThruAll()
)

# --- 3.5 挖出中心主定位孔 (通孔, d=10) ---
result = (
    result.faces(">Z").workplane()
    .circle(10.0 / 2)
    .cutThruAll()
)
# === 4. 输出模型 ===
show_object(result)
cq.exporters.export(result,__file__+'.step')