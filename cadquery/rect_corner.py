import sys
'qgb.U' in sys.modules or sys.path.append('C:/QGB/Anaconda3/Lib/site-packages/Pythonwin/')
from qgb import *
import bambu_slicer
import os
import math
import cadquery as cq

# =========== 1. 基础尺寸参数 ===========
length = 20.0       # X 方向（长）
width  = 150.0      # Y 方向（宽）
height = 10.0       # Z 方向（高）
wall   = 1.0        # 壁厚（可按需调整）
b      = 0.4
dw     = (wall - b) / 2


# =========== 2. 角落选择参数 ===========
# 可选值: "BL" (或 1), "BR" (或 2), "TR" (或 3), "TL" (或 4)
corner = "BL"  

# ------------------ 3. 构建底板 ------------------
base = (
    cq.Workplane("XY")
    .transformed(offset=(length / 2, width / 2, wall / 2))
    .box(length, width, b)
)

# ------------------ 4. 根据 corner 计算墙体位置 ------------------
corner_str = str(corner).upper()

# 判断是前(Y=0)还是后(Y=width)
is_bottom = corner_str in ["BL", "BR", "1", "2", "BOTTOM_LEFT", "BOTTOM_RIGHT"]
# 判断是左(X=0)还是右(X=length)
is_left   = corner_str in ["BL", "TL", "1", "4", "BOTTOM_LEFT", "TOP_LEFT"]

# 计算沿 X 轴方向牆（前后墙）的 Y 轴中心坐标
y_wall_pos = (wall / 2) if is_bottom else (width - wall / 2)

# 计算沿 Y 轴方向牆（左右墙）的 X 轴中心坐标
x_wall_pos = (wall / 2) if is_left else (length - wall / 2)

# 构建沿 X 轴方向的侧墙（长条墙）
wall_x = (
    cq.Workplane("XY")
    .transformed(offset=(length / 2, y_wall_pos, -height / 2 + dw))
    .box(length, wall, height)
)

# 构建沿 Y 轴方向的侧墙（宽条墙）
wall_y = (
    cq.Workplane("XY")
    .transformed(offset=(x_wall_pos, width / 2, -height / 2 + dw))
    .box(wall, width, height)
)

# ------------------ 5. 合并底板与两个侧墙 ------------------
box = base.union(wall_x).union(wall_y)

# ------------------ 6. 在底板上打通孔 φ4mm ------------------
yd=55
for hole_center in [(12, yd, wall), (12, yd + 72, wall)]:
    cutter = (
        cq.Workplane("XY")
        .transformed(offset=hole_center)
        .circle(4.0 / 2.0)
        .extrude(-wall, both=False)
    )
    box = box.cut(cutter)



yc=88
enclosure_len = 10  # 延伸长度 10mm
cut_w=15.4
cutout_center = (-7.5+1, yc, 0)
cutter_notch = (
    cq.Workplane("XY")
    .transformed(offset=cutout_center)
    .box(15+2+1, cut_w, 150)
)
box = box.cut(cutter_notch)
# 计算缺口在 Y 轴上的下边界和上边界 (中心在 Y=40, 宽度 15mm)
y_lower = yc - cut_w / 2.0  # 32.5
y_upper = yc + cut_w / 2.0  # 47.5

h      = height+b
# 下侧包围墙（紧贴 Y=32.5 下方）

wall_lower = (
    cq.Workplane("XY")
    .transformed(offset=(-enclosure_len / 2.0,y_lower - wall / 2.0,-h/2+0.7))
    .box(enclosure_len, wall, h)
)

# 上侧包围墙（
wall_upper = (
    cq.Workplane("XY")
    .transformed(offset=(-enclosure_len / 2.0, y_upper + wall / 2.0,-h/2+0.7))
    .box(enclosure_len, wall, h)
)

cross_wall = (
    cq.Workplane("XY")
    .transformed(offset=(-enclosure_len, (y_lower + y_upper)/2,b+0.1))
    .box(wall, y_upper - y_lower+2,b)
)
# ======================================================

# 合并上下竖墙 + 左端横墙
box = box.union(wall_lower).union(wall_upper).union(cross_wall)
# ------------------ 7. 可选：防翘边 ------------------
box, x_scale, y_scale = bambu_slicer.flip_model(box, angle=180, axis='y')
box = bambu_slicer.add_brim(box, 2)

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