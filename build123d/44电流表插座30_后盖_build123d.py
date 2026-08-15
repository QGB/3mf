import os, math
import cadquery as cq
import build123d_fix
from build123d import *

write_gcode = 1

# ============================================================
# 1. 核心尺寸参数定义（倒梯形开口盒子）
# ============================================================
# -- 顶部内径尺寸 (开通道口, mm) --
top_inner_L = 46.0       # 顶部内腔长度 (X方向, 必须 >= 底部)
top_inner_W = 46.0       # 顶部内腔宽度 (Y方向, 必须 >= 底部)

# -- 底部内径尺寸 (底面内腔, mm) --
bottom_inner_L = 36.0    # 底部内腔长度 (X方向)
bottom_inner_W = 36.0    # 底部内腔宽度 (Y方向)

# -- 外壳与厚度参数 --
wall_thick = 2         # 侧壁厚度 (mm)
inner_height = 24.0      # 内腔深度/拉伸高度 (mm)
base_thickness = 2.0     # 底板厚度 (mm)
corner_r_bottom = 2.0    # 底部内腔拐角圆角半径 (mm)

box_height = inner_height + base_thickness

# -- 钻孔参数 --
drill_diameter   = 5.3    # 钻孔直径 (mm)
drill_interval_x = 40   # 长边 (X方向) 钻孔间距 (mm)
drill_interval_y = drill_interval_x  # 短边 (Y方向) 钻孔间距 (mm)
margin_x         = 30   # 长边端头留边距离 (mm)
margin_y         = margin_x          # 短边端头留边距离 (mm)

# ============================================================
# 2. 拔模角度、内外径尺寸与打孔坐标计算
# ============================================================
# 2.1 外径尺寸计算
top_outer_L = top_inner_L + 2 * wall_thick         # 顶部外径长度 (51.0mm)
top_outer_W = top_inner_W + 2 * wall_thick         # 顶部外径宽度 (50.0mm)
bottom_outer_L = bottom_inner_L + 2 * wall_thick   # 底部外径长度 (36.0mm)
bottom_outer_W = bottom_inner_W + 2 * wall_thick   # 底部外径宽度 (36.0mm)

# 2.2 拔模角与倾角计算
delta_x = (top_inner_L - bottom_inner_L) / 2.0
delta_y = (top_inner_W - bottom_inner_W) / 2.0

draft_angle_x = math.degrees(math.atan2(delta_x, inner_height))
draft_angle_y = math.degrees(math.atan2(delta_y, inner_height))

wall_angle_x = 90.0 - draft_angle_x
wall_angle_y = 90.0 - draft_angle_y

# 顶部内腔圆角随尺寸比例缩放
scale_r = (top_inner_L / bottom_inner_L) if bottom_inner_L > 0 else 1.0
corner_r_top = corner_r_bottom * scale_r

# 2.3 顶面壁厚中线轨迹与打孔坐标计算
top_mid_L = top_inner_L + wall_thick   # 顶面中线长度 (48.0mm)
top_mid_W = top_inner_W + wall_thick   # 顶面中线宽度 (47.0mm)

# X方向孔位分布
if top_mid_L > 2 * margin_x:
    n_x = max(1, round((top_mid_L - 2 * margin_x) / drill_interval_x))
    x_coords = [-top_mid_L/2 + margin_x + i * (top_mid_L - 2 * margin_x) / n_x for i in range(n_x + 1)]
else:
    x_coords = [0.0]

# Y方向孔位分布
if top_mid_W > 2 * margin_y:
    n_y = max(1, round((top_mid_W - 2 * margin_y) / drill_interval_y))
    y_coords = [-top_mid_W/2 + margin_y + i * (top_mid_W - 2 * margin_y) / n_y for i in range(n_y + 1)]
else:
    y_coords = [0.0]

# 组装四条边坐标
pts = []
for x in x_coords:
    pts.append((round(x, 4), round(top_mid_W/2, 4)))
    pts.append((round(x, 4), round(-top_mid_W/2, 4)))
for y in y_coords:
    pts.append((round(top_mid_L/2, 4), round(y, 4)))
    pts.append((round(-top_mid_L/2, 4), round(y, 4)))

# 保持顺序去重
seen = set()
unique_pts = []
for p in pts:
    if p not in seen:
        seen.add(p)
        unique_pts.append(p)
pts = unique_pts
pts=[(44/2-6,44/2-12),(-(44/2-12),-(44/2-6),)]
# 2.4 打印详细尺寸与坐标信息
print("\n" + "="*80)
print("📐 倒梯形盒子 几何尺寸与拔模倾角计算结果表")
print("="*80)
print(f"顶部尺寸 (Top)   : 内径 {top_inner_L:.2f} × {top_inner_W:.2f} mm  |  外径 {top_outer_L:.2f} × {top_outer_W:.2f} mm")
print(f"底部尺寸 (Bottom): 内径 {bottom_inner_L:.2f} × {bottom_inner_W:.2f} mm  |  外径 {bottom_outer_L:.2f} × {bottom_outer_W:.2f} mm")
print(f"X方向 (长): 拔模角 {draft_angle_x:>5.2f}° | 壁面倾角 {wall_angle_x:>5.2f}°")
print(f"Y方向 (宽): 拔模角 {draft_angle_y:>5.2f}° | 壁面倾角 {wall_angle_y:>5.2f}°")
print(f"高度参数   : 底板厚度 {base_thickness:.2f}mm | 内腔深度 {inner_height:.2f}mm | 外壳总高 {box_height:.2f}mm | 侧壁厚度 {wall_thick:.2f}mm")

print("="*80)
print(f"📍 顶部安装孔位计算结果 (共计 {len(pts)} 个钻孔点)")
print("="*80)
print(f"钻孔参数: 孔径 Ø{drill_diameter:.2f}mm | 间距 X={drill_interval_x:.1f}mm, Y={drill_interval_y:.1f}mm | 端头留边 {margin_x:.1f}mm")
print(f"顶面中线轨迹: {top_mid_L:.2f}mm × {top_mid_W:.2f}mm")
print("坐标列表 (X, Y):")
for idx, pt in enumerate(pts, 1):
    print(f"  孔 [{idx:02d}]: ({pt[0]:>8.4f}, {pt[1]:>8.4f})")
print("="*80 + "\n")

# ============================================================
# 3. 三维建模核心逻辑 (Loft 放样 + 顶部打孔)
# ============================================================
print("🚀 开始生成倒梯形开口盒子...")

with BuildPart() as box:
    # 3.1 构造渐变外壳实体 (Outer Loft)
    with BuildSketch(Plane.XY) as outer_bot_sk:
        Rectangle(bottom_outer_L, bottom_outer_W)
        if (corner_r_bottom + wall_thick) > 0:
            fillet(outer_bot_sk.vertices(), radius=corner_r_bottom + wall_thick)

    with BuildSketch(Plane.XY.offset(box_height)) as outer_top_sk:
        Rectangle(top_outer_L, top_outer_W)
        if (corner_r_top + wall_thick) > 0:
            fillet(outer_top_sk.vertices(), radius=corner_r_top + wall_thick)

    loft()  # 放样生成外壳

    # 3.2 构造渐变内腔掏空实体 (Inner Loft Cutout)
    extra_cut = 2.0
    top_cut_L = top_inner_L + (delta_x / inner_height) * (extra_cut * 2)
    top_cut_W = top_inner_W + (delta_y / inner_height) * (extra_cut * 2)
    top_cut_r = corner_r_top + (corner_r_top - corner_r_bottom) * (extra_cut / inner_height)

    with BuildSketch(Plane.XY.offset(base_thickness)) as inner_bot_sk:
        Rectangle(bottom_inner_L, bottom_inner_W)
        if corner_r_bottom > 0:
            fillet(inner_bot_sk.vertices(), radius=corner_r_bottom)

    with BuildSketch(Plane.XY.offset(box_height + extra_cut)) as inner_top_sk:
        Rectangle(top_cut_L, top_cut_W)
        if top_cut_r > 0:
            fillet(inner_top_sk.vertices(), radius=top_cut_r)

    loft(mode=Mode.SUBTRACT)  # 掏空内腔

    # 3.3 顶部均匀打孔
    if pts:
        top_face = box.faces().sort_by(Axis.Z)[-1]
        with Locations(top_face):
            with Locations(*pts):
                if drill_diameter:
                    Hole(radius=drill_diameter / 2.0, depth=box_height + 5.0)
# ============================================================
    # 3.4 -X 侧壁顶部中点 U型缺口 (圆心完全同原圆孔，仅向上开口)
    # ============================================================
    with BuildSketch(Plane.YZ.offset(-(top_inner_L / 2 + wall_thick))) as u_sk:
        with Locations((0.0, box_height - 4.5 / 2)):  # 严格保持原圆孔圆心位置不变
            Circle(4.5 / 2)
        with Locations((0.0, box_height)):            # 从圆心向上切出直边开口 (切透顶面)
            Rectangle(4.5, 4.5)

    extrude(amount=10.0, mode=Mode.SUBTRACT)          # 向内切透 2mm 侧壁      # 向 +X 方向切透 2mm 壁厚

print("✅ 模型生成完毕！准备输出。")

# ============================================================
# 4. 渲染与输出
# ============================================================
import bambu_slicer

step_file = os.path.splitext(__file__)[0] + f"_{base_thickness}.step" if "__file__" in globals() else f"tapered_box_{base_thickness}.step"
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