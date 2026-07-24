import sys
'qgb.U' in sys.modules or sys.path.append('C:/QGB/Anaconda3/Lib/site-packages/Pythonwin/')
from qgb import *
import bambu_slicer
import os
import math
import cadquery as cq

# =========== 参数定义 ===========
length = 20.0      # X 方向（长）
width  = 150.0     # Y 方向（宽）
height = 10.0      # Z 方向（高）
wall   = 1.0       # 壁厚
b      = 0.4
dw     = (wall - b) / 2
h      = height

# ------------------ 1. 构建底板 ------------------
base = (
    cq.Workplane("XY")
    .transformed(offset=(length / 2, width / 2, wall / 2))
    .box(length, width, b)
)

# ------------------ 2. 构建前壁（Y=0 面） ------------------
front = (
    cq.Workplane("XY")
    .transformed(offset=(length / 2, wall / 2, h / 2 + dw))
    .box(length, wall, h)
)

# ------------------ 3. 构建右侧墙（X=0..wall 面） ------------------
right = (
    cq.Workplane("XY")
    .transformed(offset=(wall / 2, width / 2, height / 2 + dw))
    .box(wall, width, h)
)

# ------------------ 4. 合并三个基础面 ------------------
box = base.union(front).union(right)

# ------------------ 5. 切割缺口 ------------------
yc=90
cutout_center = (-7.5+1, yc, 0)
cutter_notch = (
    cq.Workplane("XY")
    .transformed(offset=cutout_center)
    .box(15, 15, 150)
)
box = box.cut(cutter_notch)

# ------------------ 6. 新增：缺口上下两侧的包围墙 (长度 10mm) ------------------
enclosure_len = 15.3  # 延伸长度 10mm

# 计算缺口在 Y 轴上的下边界和上边界 (中心在 Y=40, 宽度 15mm)
y_lower = yc - 15.0 / 2.0  # 32.5
y_upper = yc + 15.0 / 2.0  # 47.5

# 下侧包围墙（紧贴 Y=32.5 下方）
wall_lower = (
    cq.Workplane("XY")
    .transformed(offset=(-enclosure_len / 2.0, y_lower - wall / 2.0, h / 2.0 + dw))
    .box(enclosure_len, wall, h)
)

# 上侧包围墙（紧贴 Y=47.5 上方）
wall_upper = (
    cq.Workplane("XY")
    .transformed(offset=(-enclosure_len / 2.0, y_upper + wall / 2.0, h / 2.0 + dw))
    .box(enclosure_len, wall, h)
)

# ==========【新增：左端横向连接墙，闭合方框】==========
# X位置：最外端 -enclosure_len，Y跨度覆盖上下两根竖墙，厚度wall
ch=0.4
cross_wall = (
    cq.Workplane("XY")
    .transformed(offset=(-enclosure_len, (y_lower + y_upper)/2,ch+0.1))
    .box(wall, y_upper - y_lower+2,ch)
)
# ======================================================

# 合并上下竖墙 + 左端横墙
box = box.union(wall_lower).union(wall_upper).union(cross_wall)

# ------------------ 7. 打通孔 φ4mm ------------------
yd=56
for hole_center in [(12, yd, wall), (12, yd + 72, wall)]:
    cutter = (
        cq.Workplane("XY")
        .transformed(offset=hole_center)
        .circle(4.0 / 2.0)
        .extrude(-wall, both=False)
    )
    box = box.cut(cutter)


box = bambu_slicer.add_brim(box,2)
# ------------------ 8. 导出 STEP & 切片 ------------------
time_mark = U.get_time_str_mark(sep=' ')
step_file = os.path.splitext(__file__)[0] + f"_three_walls_{time_mark}.step"
cq.exporters.export(box, step_file)

if "show_object" in globals():
    show_object(box, name="Three_Wall_Box")

f = bambu_slicer.to_gcode(
    cq_object=box,
    name=step_file,
    output_dir=r"D:\test\bambu-studio"
)