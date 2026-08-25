import os, math
import cadquery as cq
import build123d_fix
from build123d import *
+Y  +X 方向 需要从上向下切 边缘芯片方块
write_gcode = 1

# ============================================================
# 1. 极简核心尺寸参数定义
# ============================================================
top_inner_L = 48.0       # 顶部内腔长 (X方向)
top_inner_W = 48.0       # 顶部内腔宽 (Y方向)

bottom_inner_L = 34.0    # 底部内腔长 (X方向，恢复标准对称定义)
bottom_inner_W = 51.0    # 底部内腔宽 (Y方向)

inner_height = 18.0      # 内腔高度
wall_thick = 2.0         # 侧壁厚度
base_thickness = 2.0     # 底板厚度
box_height = inner_height + base_thickness

drill_diameter = 3.4     # 钻孔直径
hole_spacing = 40.0      # 4孔正方形边长

# ------------------------------------------------------------
# ★ 侧壁切除（镂空）3 参数独立控制 ★
# ------------------------------------------------------------
cutout_depth = inner_height                # 镂空向下深度

# 1) -Y 侧壁切除宽度 (整体单侧控制)
cutout_width_neg_y = 32                 

# 2) +Y 侧壁切除宽度 (+X / -X 两侧分别控制)
cutout_width_pos_y_pos_x = 17.0            # +Y 面上 +X 方向切除半宽
cutout_width_pos_y_neg_x = 5             # +Y 面上 -X 方向切除半宽

# ============================================================
# 2. 自动化外径坐标与切除中心点计算
# ============================================================
top_outer_L = top_inner_L + 2 * wall_thick
top_outer_W = top_inner_W + 2 * wall_thick
bottom_outer_L = bottom_inner_L + 2 * wall_thick
bottom_outer_W = bottom_inner_W + 2 * wall_thick

# +Y 侧壁切除的总宽度与偏心 X 坐标计算
pos_y_cut_total_width = cutout_width_pos_y_pos_x + cutout_width_pos_y_neg_x
pos_y_cut_x_center = (cutout_width_pos_y_pos_x - cutout_width_pos_y_neg_x) / 2.0

# 4个孔的绝对坐标
hs = hole_spacing / 2.0
hsdy = 2.0
pts = [(hs, hs+hsdy), (hs, -hs+hsdy), (-hs, hs+hsdy), (-hs, -hs+hsdy)]

# ============================================================
# 3. 三维建模核心逻辑
# ============================================================
print("🚀 开始生成标准对称外壳及非对称切除盒子...")

with BuildPart() as box:
    # ----------------------------------------------------
    # 3.1 构造对称外壳实体 ( ruled=True 保证垂直拉直面 )
    # ----------------------------------------------------
    with BuildSketch(Plane.XY):
        Rectangle(bottom_outer_L, bottom_outer_W)
    with BuildSketch(Plane.XY.offset(box_height)):
        Rectangle(top_outer_L, top_outer_W)
    loft(ruled=True)

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
    loft(ruled=True, mode=Mode.SUBTRACT)

    # ----------------------------------------------------
    # 3.3 生成实心螺丝外柱 (从 Z=0 拔地而起)
    # ----------------------------------------------------
    with BuildSketch(Plane.XY): 
        with Locations(*pts):
            Circle(radius=drill_diameter / 2.0 + min(wall_thick, 2))
    extrude(amount=box_height)

    # ----------------------------------------------------
    # 3.4 侧壁按 3 参数精准挖空切除
    # ----------------------------------------------------
    cutout_z_center = box_height - (cutout_depth / 2.0)
    
    # a. -Y 侧壁切除 (-Y 面)
    with Locations((0.0, -top_outer_W / 2.0, cutout_z_center)):
        Box(cutout_width_neg_y, wall_thick + 10.0, cutout_depth, mode=Mode.SUBTRACT)

    # b. +Y 侧壁切除 (+Y 面，支持 +X/-X 非对称定义)
    with Locations((pos_y_cut_x_center, top_outer_W / 2.0, cutout_z_center)):
        Box(pos_y_cut_total_width, wall_thick + 10.0, cutout_depth, mode=Mode.SUBTRACT)

    # ----------------------------------------------------
    # 3.5 Y=16 内部加强筋横断墙
    # ----------------------------------------------------
    rib_y = 16.0
    rib_top_z = box_height - 0 #2.5
    rib_height_ratio = (rib_top_z - base_thickness) / inner_height
    rib_top_L = bottom_inner_L + (top_inner_L - bottom_inner_L) * rib_height_ratio

    with BuildSketch(Plane.XY.offset(base_thickness)):
        with Locations((0.0, rib_y)):
            Rectangle(bottom_inner_L + 2.0, wall_thick)
    with BuildSketch(Plane.XY.offset(rib_top_z)):
        with Locations((0.0, rib_y)):
            Rectangle(rib_top_L + 2.0, wall_thick)
    loft(ruled=True)

    # ----------------------------------------------------
    # 3.6 切割加强筋中央圆洞
    # ----------------------------------------------------
    hole_r = 5.0
    hole_depth = wall_thick + 10.0

    with Locations((0.0, rib_y, base_thickness + hole_r)):
        Cylinder(radius=hole_r, height=hole_depth, rotation=(90, 0, 0), mode=Mode.SUBTRACT)

    # ----------------------------------------------------
    # 3.7 全局贯穿打孔
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
