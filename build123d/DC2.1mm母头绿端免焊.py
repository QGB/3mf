import build123d_fix
import math
from build123d import *

# ============================================================
# 1. 核心尺寸参数定义（基于 DC 接头实测内腔与外框）
# ============================================================
wall_thick = 1.8       # 外壁厚度 (mm)
corner_r = 1.0         # 矩形内角倒角半径 (mm)

# -- 1. 底层长方形框参数 (接线端 Z=0 -> Z=14) --
inner_l = 14.0         # 底部长方形长度 X (mm)
inner_w = 12.0         # 底部长方形宽度 Y (mm)
base_h = 14.0          # 矩形段高度 (mm)

# -- 2. 中层收缩过渡段参数 (Z=14 -> Z=24) --
sq_side = 11.0         # 收缩顶端正方形边长 (mm)
taper_h = 10.0         # 收缩高度 (mm)

# -- 3. 顶层 DC 母头圆孔段参数 (Z=24 -> Z=33) --
dc_inner_dia = 10.5    # DC 母头外径 / 贯通内孔直径 (mm)
top_h = 9.0            # 顶部圆柱高度 (mm)

# ============================================================
# 2. 关键 Z 轴高度分界计算
# ============================================================
z_base_top = base_h                    # Z = 14.0 mm
z_taper_top = z_base_top + taper_h     # Z = 24.0 mm
z_total_top = z_taper_top + top_h      # Z = 33.0 mm

# ============================================================
# 3. 三维实体建模 (修正 Context 上下文调用，保证 100% 组装)
# ============================================================
print("\n🚀 开始 DC 母头垂直无底外框建模...")

with BuildPart() as dc_housing:
    # --------------------------------------------------------
    # Step 1: 构造实心外壳主体 (Add Solid Body)
    # --------------------------------------------------------
    # 1.1 底部直筒长方形外壳 (Z=0 到 Z=14)
    with BuildSketch(Plane.XY) as sk_out_base:
        Rectangle(inner_l + 2 * wall_thick, inner_w + 2 * wall_thick)
        fillet(sk_out_base.vertices(), radius=corner_r + wall_thick)
    extrude(amount=base_h)

    # 1.2 渐变收缩段外壳 (Z=14 放样到 Z=24)
    with BuildSketch(Plane.XY.offset(z_base_top)) as sk_out_mid_bot:
        Rectangle(inner_l + 2 * wall_thick, inner_w + 2 * wall_thick)
        fillet(sk_out_mid_bot.vertices(), radius=corner_r + wall_thick)
    with BuildSketch(Plane.XY.offset(z_taper_top)) as sk_out_mid_top:
        Rectangle(sq_side + 2 * wall_thick, sq_side + 2 * wall_thick)
        fillet(sk_out_mid_top.vertices(), radius=corner_r + wall_thick)
    loft()  # 直接调用 loft() 自动消费上面两个草图，完美融合进主体

    # 1.3 顶部平滑过渡外壳 (从 11 正方形 平滑放样到 10.5 圆柱)
    with BuildSketch(Plane.XY.offset(z_taper_top)) as sk_out_top_bot:
        Rectangle(sq_side + 2 * wall_thick, sq_side + 2 * wall_thick)
        fillet(sk_out_top_bot.vertices(), radius=corner_r + wall_thick)
    with BuildSketch(Plane.XY.offset(z_total_top)) as sk_out_top_end:
        Circle(radius=dc_inner_dia / 2.0 + wall_thick)
    loft()

    # --------------------------------------------------------
    # Step 2: 掏空内腔 (Z=0 全通到底，形成纯外框)
    # --------------------------------------------------------
    # 2.1 掏空底部矩形内腔 (Z向下退1mm再挖，保证 Z=0 绝对无底残留)
    with BuildSketch(Plane.XY.offset(-1.0)) as sk_in_base:
        Rectangle(inner_l, inner_w)
        fillet(sk_in_base.vertices(), radius=corner_r)
    extrude(amount=base_h + 1.0, mode=Mode.SUBTRACT)

    # 2.2 掏空渐变收缩段内腔
    with BuildSketch(Plane.XY.offset(z_base_top)) as sk_in_mid_bot:
        Rectangle(inner_l, inner_w)
        fillet(sk_in_mid_bot.vertices(), radius=corner_r)
    with BuildSketch(Plane.XY.offset(z_taper_top)) as sk_in_mid_top:
        Rectangle(sq_side, sq_side)
        fillet(sk_in_mid_top.vertices(), radius=corner_r)
    loft(mode=Mode.SUBTRACT)

    # 2.3 掏空顶部 DC 圆孔 (内部直接直筒切通，形成天然台阶卡住 DC 橡胶头)
    with BuildSketch(Plane.XY.offset(z_taper_top - 0.1)) as sk_in_top:
        Circle(radius=dc_inner_dia / 2.0)
    extrude(amount=top_h + 2.0, mode=Mode.SUBTRACT)

print("✅ DC 母头全包围无底外框生成完毕！准备输出。")

# ============================================================
# 4. 渲染与切片输出
# ============================================================
import os, bambu_slicer, cadquery as cq

step_file = os.path.splitext(__file__)[0] + f"_DC_Housing.step"
export_step(dc_housing.part, step_file)
cq_object = cq.Shape(dc_housing.part.wrapped)
# cq_object = bambu_slicer.add_brim(cq_object, 0)

if "show_object" in locals():
    show_object(cq_object, name=step_file[:-5])

f = bambu_slicer.to_gcode(
    cq_object=cq_object,
    name=step_file,
    output_dir=r"D:\test\bambu-studio",
    material='PETG',
)