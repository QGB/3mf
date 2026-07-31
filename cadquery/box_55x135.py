import sys
import bambu_slicer

import os
import math
import cadquery as cq

# =========== 1. 尺寸与厚度独立控制参数 ===========
# 内腔尺寸 (mm)
inner_length = 135   # 内腔长（X方向）
inner_width  = 55    # 内腔宽（Y方向）
inner_height = 55

# 厚度控制（可独立修改）
wall_thickness   = 2  # 四周侧壁厚度 (mm)
bottom_thickness = 2  # 底部平板厚度 (mm)

# 圆角倒角参数
outer_corner_radius = 5  # 外壁直角圆弧半径 (mm)
# 内腔圆角半径：若希望拐角处壁厚均匀，设为 outer_corner_radius - wall_thickness
inner_corner_radius = max(0.1, outer_corner_radius - wall_thickness)

# =========== 2. 计算外轮廓尺寸 ===========
outer_length = inner_length + 2 * wall_thickness
outer_width  = inner_width  + 2 * wall_thickness
outer_height = inner_height + bottom_thickness

# =========== 3. 构建无盖盒子 ===========
# 1) 生成底面置于 Z=0 的实心外框长方体
box = (
    cq.Workplane("XY")
    .box(outer_length, outer_width, outer_height, centered=(True, True, False))
    # 2) 先将外侧 4 条竖直边倒圆角 R3mm（倒完后外侧竖边变为曲面）
    .edges("|Z")
    .fillet(outer_corner_radius)
    # 3) 选中顶面，绘制内腔矩形并向下盲孔切削 (cutBlind)
    .faces(">Z")
    .workplane()
    .rect(inner_length, inner_width)
    .cutBlind(-inner_height)  # 精确向下切削 inner_height 深度，留下 bottom_thickness 底厚
)

# 4) 倒内腔 4 条竖直角边（此时模型中仅剩的平行于 Z 轴的直线边即为内腔 4 个直角）
if inner_corner_radius > 0:
    box = box.edges("|Z").fillet(inner_corner_radius)

# =========== 4. 防翘边 (Brim) ===========
box = bambu_slicer.add_brim(box, 5)

# =========== 5. 导出 STEP & 切片 ===========
time_mark = '' # U.get_time_str_mark(sep=' ')
step_file = os.path.splitext(__file__)[0] + f"_open_box_{time_mark}.step"
cq.exporters.export(box, step_file)

if "show_object" in globals():
    show_object(box, name="Open_Box_145x85x30")

f = bambu_slicer.to_gcode(
    cq_object=box,
    name=step_file,
    output_dir=r"D:\test\bambu-studio"
)