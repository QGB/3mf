import os, math
import cadquery as cq
import build123d_fix
from build123d import *

write_gcode = 1

# ============================================================
# 1. 极简核心尺寸参数定义
# ============================================================
top_inner_L = 51.0       # 顶部内腔长 (X方向)
top_inner_W = 51.0       # 顶部内腔宽 (Y方向)

bottom_inner_L = 34.0    # 底部内腔长 (X方向形成倒梯形)
bottom_inner_W = 51.0    # 底部内腔宽 (Y方向与顶部一致)

inner_height = 20.0      # 内腔高度
wall_thick = 2.0         # 侧壁厚度
base_thickness = 2.0     # 底板厚度
box_height = inner_height + base_thickness

drill_diameter = 3.3     # 钻孔直径
hole_spacing = 40.0      # 4孔正方形边长

cutout_width = 30.0      # 镂空宽度
cutout_depth = 20.0      # 镂空向下深度

# ============================================================
# 2. 自动化外径坐标与打孔点位计算
# ============================================================
top_outer_L = top_inner_L + 2 * wall_thick
top_outer_W = top_inner_W + 2 * wall_thick
bottom_outer_L = bottom_inner_L + 2 * wall_thick
bottom_outer_W = bottom_inner_W + 2 * wall_thick

# 4个孔的绝对坐标
hs = hole_spacing / 2.0
pts = [(hs, hs), (hs, -hs), (-hs, hs), (-hs, -hs)]

# ============================================================
# 3. 三维建模核心逻辑
# ============================================================
print("🚀 开始生成单向倒梯形盒子...")

with BuildPart() as box:
    # ----------------------------------------------------
    # 3.1 构造外壳实体
    # ----------------------------------------------------
    with BuildSketch(Plane.XY):
        Rectangle(bottom_outer_L, bottom_outer_W)
    with BuildSketch(Plane.XY.offset(box_height)):
        Rectangle(top_outer_L, top_outer_W)
    loft()

    # ----------------------------------------------------
    # 3.2 构造内腔并掏空
    # ----------------------------------------------------
    extra_cut = 2.0
    delta_x = (top_inner_L - bottom_inner_L) / 2.0
    top_cut_L = top_inner_L + (delta_x / inner_height) * (extra_cut * 2)
    top_cut_W = top_inner_W

    with BuildSketch(Plane.XY.offset(base_thickness)):
        Rectangle(bottom_inner_L, bottom_inner_W)
    with BuildSketch(Plane.XY.offset(box_height + extra_cut)):
        Rectangle(top_cut_L, top_cut_W)
    loft(mode=Mode.SUBTRACT)

    # ----------------------------------------------------
    # 3.3 生成实心螺丝外柱 (★终极修复1：从 Z=0 拔地而起，彻底消除底部悬空★)
    # ----------------------------------------------------
    with BuildSketch(Plane.XY): # 直接扎根于绝对原点 Z=0
        with Locations(*pts):
            Circle(radius=drill_diameter / 2.0 + min(wall_thick, 1.5))
    extrude(amount=box_height) # 一柱擎天直达顶面，保证底面100%着床

    # ----------------------------------------------------
    # 3.4 垂直两面(Y向面)中间镂空
    # ----------------------------------------------------
    cutout_z_center = box_height - (cutout_depth / 2.0) 
    with Locations((0.0, 0.0, cutout_z_center)):
        Box(cutout_width, top_outer_W + 10.0, cutout_depth, mode=Mode.SUBTRACT)

    # ----------------------------------------------------
    # 3.5 Y=16 内部加强筋横断墙 (降高 2.5mm)
    # ----------------------------------------------------
    rib_y = 16.0
    rib_top_z = box_height - 2.5
    rib_height_ratio = (rib_top_z - base_thickness) / inner_height
    rib_top_L = bottom_inner_L + (top_inner_L - bottom_inner_L) * rib_height_ratio

    with BuildSketch(Plane.XY.offset(base_thickness)):
        with Locations((0.0, rib_y)):
            Rectangle(bottom_inner_L + 2.0, wall_thick)
    with BuildSketch(Plane.XY.offset(rib_top_z)):
        with Locations((0.0, rib_y)):
            Rectangle(rib_top_L + 2.0, wall_thick)
    loft()

    # ----------------------------------------------------
    # 3.6 切割加强筋 U 型槽 (★终极修复2：摒弃 2D 草图，使用 3D 实体暴力切割★)
    # ----------------------------------------------------
    slot_w = 10.0
    slot_r = slot_w / 2.0
    slot_depth = wall_thick + 10.0 # 足够深，保证把墙切透

    # a. 底部完美的半圆倒角 (圆柱体，绕X轴旋转90度横跨Y轴)
    with Locations((0.0, rib_y, base_thickness + slot_r)):
        Cylinder(radius=slot_r, height=slot_depth, rotation=(90, 0, 0), mode=Mode.SUBTRACT)

    # b. 顶部的直筒矩形开口 (中心Z轴稍微往下沉0.1mm，确保和下面半圆互相嵌套，不留膜)
    with Locations((0.0, rib_y, base_thickness + slot_r + inner_height / 2.0 - 0.1)):
        Box(slot_w, slot_depth, inner_height + 0.2, mode=Mode.SUBTRACT)

    # ----------------------------------------------------
    # 3.7 全局贯穿打孔 (从地底 Z=-10 强行向上贯穿)
    # ----------------------------------------------------
    with BuildSketch(Plane.XY.offset(-10.0)): 
        with Locations(*pts):
            if drill_diameter:
                Circle(radius=drill_diameter / 2.0)
    extrude(amount=box_height + 30.0, mode=Mode.SUBTRACT)

print("✅ 模型生成完毕！准备输出。")

# ============================================================
# 4. 渲染与输出
# ============================================================
import bambu_slicer

step_file = os.path.splitext(__file__)[0] + f"_{base_thickness}.step" if "__file__" in globals() else f"single_taper_box_{base_thickness}.step"
export_step(box.part, step_file)
cq_object = cq.Shape(box.part.wrapped)
cq_object = bambu_slicer.add_brim(cq_object, 5)

if "show_object" in locals():
    show_object(cq_object, name=step_file[:-5])

if write_gcode:
    f = bambu_slicer.to_gcode(
        cq_object=cq_object,
        name=step_file,
        output_dir=r"D:\test\bambu-studio",
        material='PETG',
    )