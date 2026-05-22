import cadquery as cq
from math import sqrt

# === 1. 核心几何参数 ===
w = 102
# 计算相切条件
d_main = -w/2 * (-1 + sqrt(5 - 2*sqrt(6)))
r = d_main / 2
t = r + sqrt((2*r)**2 - (w/2 - r)**2)
g = (t + w/2 + r) / 3

# 计算 8 个圆心坐标
coords = [
    (r - w/2, r - w/2),   (w-r - w/2, r - w/2),     # 左上, 右上
    (r - w/2, w-r - w/2), (w-r - w/2, w-r - w/2),   # 左下, 右下
    (t - w/2, 0),         (w-t - w/2, 0),           # 左中, 右中
    (0, t - w/2),         (0, w-t - w/2)            # 上中, 下中
]

# === 2. 生成正方形基板 ===
result = cq.Workplane("XY").rect(w+2, w+2).extrude(10)
# 四个角倒圆角（半径 4mm）
result = result.edges("|Z").fillet(10)
result = (
    result.faces(">Z").workplane()
    .pushPoints(coords)
    .circle(34.3 / 2)
    .cutBlind(-10+1)
)

# === 3. 批量挖孔 ===
w = 100
d_main = -w/2 * (-1 + sqrt(5 - 2*sqrt(6)))
r = d_main / 2
t = r + sqrt((2*r)**2 - (w/2 - r)**2)
g = (t + w/2 + r) / 3

coords = [
    (r - w/2, r - w/2),   (w-r - w/2, r - w/2),     # 左上, 右上
    (r - w/2, w-r - w/2), (w-r - w/2, w-r - w/2),   # 左下, 右下
    (t - w/2, 0),         (w-t - w/2, 0),           # 左中, 右中
    (0, t - w/2),         (0, w-t - w/2)            # 上中, 下中
]

# --- 3.1 挖出 8 个大内孔 (盲孔) ---
result = (
    result.faces(">Z").workplane()
    .pushPoints(coords)
    .circle(16 / 2)
    .cutBlind(-10)
)

# --- 3.3 挖出交叉长条矩形分布孔 (通孔, d=6) ---
m6=6.5
# 纵向分布
result = (
    result.faces(">Z").workplane()
    .rect(28, w - 10, forConstruction=True)
    .vertices("<Y")
    .circle(m6 / 2)
    .cutThruAll()
)

# 横向分布
result = (
    result.faces(">Z").workplane()
    .rect(w - 10, 28, forConstruction=True)
    .vertices()
    .circle(m6 / 2)
    .cutThruAll()
)

# --- 3.5 挖出中心主定位孔 (通孔, d=10) ---
result = (
    result.faces(">Z").workplane()
    .circle(10.0 / 2)
    .cutThruAll()
)

# --- 3.6 六角盲孔 (对边 6) ---
result = (
    result.workplane(offset=0-1) #实际4mm
    .pushPoints([(-13,43),(13,43)]) # 坐标和正面完全一致
    .polygon(nSides=7, diameter=12/ sqrt(3))
    .cutBlind(-11)  # 向上切5mm（背面朝向+Z方向）
)

# --- 3.7 在 (0, 47) 打孔 m6 ---
result = (
    result.faces(">Z").workplane()
    .pushPoints([(0, 47)])
    .circle(3)
    .cutThruAll()
)

# === 4. 输出模型 ===
cq.exporters.export(result,__file__+'.step')
show_object(result)
