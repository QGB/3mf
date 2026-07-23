import sys
'qgb.U' in sys.modules or sys.path.append('C:/QGB/Anaconda3/Lib/site-packages/Pythonwin/')
from qgb import *
import bambu_slicer
import os
import math
import cadquery as cq

# ===========positioning location 单词区别
length = 20      # X 方向（长）
width  = 120.0     # Y 方向（宽）
height = 10.0      # Z 方向（高）
wall   = 1.0       # 壁厚（可按需调整）
b=0.4
dw=(wall-b)/2
# ------------------ 1. 构建底板 ------------------
# 底板尺寸：length × width × wall，底面放在 Z=0，使左下角为原点方便定位
base = (
    cq.Workplane("XY")
    .transformed(offset=(length/2, width/2, wall/2))   # 中心移到 (length/2, width/2, wall/2)
    .box(length, width,b)
)

# ------------------ 2. 构建前壁（Y=0 面） ------------------
# ------------------ 2. 构建前壁（Y=0 面），向 Z 负方向 ------------------
h = height
front = (
    cq.Workplane("XY")
    .transformed(offset=(length/2, wall/2, -h/2+dw))   # 修改此处
    .box(length, wall, h)
)

# ------------------ 3. 构建右壁（X=length 面），向 Z 负方向 ------------------
right = (
    cq.Workplane("XY")
    .transformed(offset=(wall/2, width/2, -h/2+dw))    # 修改此处
    .box(wall, width, h)
)

# ------------------ 4. 合并三个面 ------------------
box = base.union(front).union(right)

# ------------------ 5. 在底板上打通孔 φ4mm @ (12, 45) ------------------
# 孔的中心位于 (12, 45)，钻孔从 Z=wall 向下贯穿至 Z=0
for hole_center in [(12,45,wall),(12,45+72,wall)]:
    cutter = (
        cq.Workplane("XY")
        .transformed(offset=hole_center)        # 定位到孔心
        .circle(4.0 / 2.0)                      # 半径 2.0
        .extrude(-wall, both=False)       # 向下切穿底板（多切一点确保贯穿）
    )
    box = box.cut(cutter)

# ------------------ 6. 可选：防翘边 ------------------
# if wall > 2:
box, x_scale, y_scale = bambu_slicer.flip_model(box, angle=180, axis='y')
box = bambu_slicer.add_brim(box, 2)

# ------------------ 7. 导出 STEP & 切片 ------------------
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