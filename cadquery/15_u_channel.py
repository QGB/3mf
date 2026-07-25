import sys
'qgb.U' in sys.modules or sys.path.append('C:/QGB/Anaconda3/Lib/site-packages/Pythonwin/')
from qgb import *
import bambu_slicer
import os,math
import cadquery as cq

# ==================== 1. 核心参数定义 ====================
length = 67.0       # X 方向总宽度
width  = 60.0       # Y 方向贯通长度（前后方向）
height = 10.0       # Z 方向侧墙高度
wall   = 1.0        # 左右侧壁厚度
b      = 0.4        # 底板厚度
xmid = length / 2.0       # X 轴中线 (33.5mm)
ymid = width / 2.0      # Y 轴中线 (30.0mm)

# ==================== 2. 构建 3 面结构 (U型槽) ====================
# 设置 centered=(False, False, False) 使模型左下角固定在 (0,0,0)

# 2.1 底板 (X: 0 -> length, Y: 0 -> width, Z: 0 -> b)
base = cq.Workplane("XY").box(length, width, b, centered=(False, False, False))



rx = length             # X 方向跨度复用 length
ry = width              # Y 方向跨度复用 width
line_w = wall           # 线宽复用侧壁厚度 wall
relief_h = 0.2          # 浮雕凸起高度

# 浮雕 Z 轴起点 (b = 底板厚度，即从底板表面向上凸起)
z_start = b             

# 计算对角线的实际长度与旋转角度
diag_len = math.hypot(rx, ry)
angle = math.degrees(math.atan2(ry, rx))
z_center = z_start + relief_h / 2.0

# 1. 水平横条
mi_h = (
    cq.Workplane("XY")
    .box(rx, line_w, relief_h)
    .translate((xmid, ymid, z_center))
)

# 2. 垂直竖条
mi_v = (
    cq.Workplane("XY")
    .box(line_w, ry, relief_h)
    .translate((xmid, ymid, z_center))
)

# 3. 对角线 1 (左下至右上)
mi_d1 = (
    cq.Workplane("XY")
    .box(diag_len, line_w, relief_h)
    .rotate((0, 0, 0), (0, 0, 1), angle)
    .translate((xmid, ymid, z_center))
)

# 4. 对角线 2 (左上至右下)
mi_d2 = (
    cq.Workplane("XY")
    .box(diag_len, line_w, relief_h)
    .rotate((0, 0, 0), (0, 0, 1), -angle)
    .translate((xmid, ymid, z_center))
)

# 将 4 根浮雕条合并到主模型中
base =base.union(mi_h).union(mi_v).union(mi_d1).union(mi_d2)




# 2.2 左侧墙 (位于 X=0 边缘)
left_wall = cq.Workplane("XY").box(wall, width, height, centered=(False, False, False))

# 2.3 右侧墙 (位于 X = length - wall 边缘)
right_wall = (
    cq.Workplane("XY")
    .box(wall, width, height, centered=(False, False, False))
    .translate((length - wall, 0, 0))
)

# 2.4 合并三面结构
box = base.union(left_wall).union(right_wall)

# ==================== 3. 在底板上打孔 (Y方向对称孔) ====================
hole_diameter = 4.0
hole_radius = hole_diameter / 2.0
hole_dist = 43.0            # 两孔中心间距 43mm


# 计算以 Y 中线对称分布的两个 Y 坐标 [8.5mm, 51.5mm]
hole_y_list = [ymid - hole_dist / 2.0, ymid + hole_dist / 2.0]

for hole_y in hole_y_list:
    cutter = (
        cq.Workplane("XY")
        .transformed(offset=(xmid, hole_y, 0))
        .circle(hole_radius)
        .extrude(height, combine=False)  # 向上切穿底板
    )
    box = box.cut(cutter)


# ==================== 关键修复参数 ====================
zd = 0.0          # 1. 严格锁定 Z=0，确保所有底面完全贴合热床（Brim 即可完美生成）
overlap = 0.1     # 2. 水平嵌入量：向两侧墙体内延伸 0.1mm，完美解决布尔合并/缝隙问题
ld=11
d=16/2
gap = 0.7         # 墙体外扩间隙/偏移量

# ---------------- 左侧墙 (Left) ----------------
# 宽度增加 overlap，并向右（主体墙内）微调，实现水平融合
left_wall_d = (
    cq.Workplane("XY")
    .box(ld + overlap, wall, height, centered=(False, False, False))
    .translate((-ld - gap, ymid - d, zd))
)
left_wall_u = (
    cq.Workplane("XY")
    .box(ld + overlap, wall, height, centered=(False, False, False))
    .translate((-ld - gap, ymid + d, zd))
)

# ---------------- 右侧墙 (Right) ----------------
# 起始位置向左（主体墙内）回退 overlap，实现水平融合
right_wall_d = (
    cq.Workplane("XY")
    .box(ld + overlap, wall, height, centered=(False, False, False))
    .translate((length + gap - overlap, ymid - d, zd))
)
right_wall_u = (
    cq.Workplane("XY")
    .box(ld + overlap, wall, height, centered=(False, False, False))
    .translate((length + gap - overlap, ymid + d, zd))
)

# ---------------- 布尔合并 ----------------
box = box.union(left_wall_d).union(left_wall_u).union(right_wall_d).union(right_wall_u)

# ==================== 4. 防翘边与导出切片 ====================
# 防翘边
box = bambu_slicer.add_brim(box,2)
box = bambu_slicer.add_brim(box,1)

cutter = (
    cq.Workplane("XY")
    .transformed(offset=(-ld/2-1,ymid+0.5,0))
    .box(ld+1,15, 150)
).union(
    cq.Workplane("XY")
    .transformed(offset=(length+ld/2+1,ymid+0.5,0))
    .box(ld+1,15, 150)
)        
box = box.cut(cutter)


# 导出 STEP
time_mark = U.get_time_str_mark(sep=' ')
step_file = os.path.splitext(__file__)[0] + f".step"
cq.exporters.export(box, step_file)

if "show_object" in globals():
    show_object(box, name="U_Channel_Box")

# 切片 Gcode
f = bambu_slicer.to_gcode(
    cq_object=box,
    name=step_file,
    output_dir=r"D:\test\bambu-studio"
)