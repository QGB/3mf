import build123d_fix
import math
from build123d import *

# ============================================================
# 1. 核心尺寸参数定义
# ============================================================
# --- 品字头 (C13) 参数 ---
inner_h = 16.0         # 内部总高 (Y方向)
inner_w_max = 24.0     # 底部长边最大宽度 (X方向)
inner_w_top = 12.0     # 顶部小宽度 (X方向)
straight_height = 9.8  # 底边向上直边高度

slot_len = 5.0             # 长圆孔长度 (X方向)
slot_h = 2.7               # 长圆孔高度 (Y方向)
slot_dist_from_bot = 5.0   # 距离底部 24mm 长边的垂直距离

wall_thick = 1.8      # 侧壁厚度 (mm)
inner_depth = 20.0    # 内腔深度 (mm)
base_thickness = 2.0   # 底板厚度 (mm)
box_height = inner_depth + base_thickness

frame_inner_top_len = 29.2   # 上底/共壁侧内圈长度 (X方向)
frame_inner_bot_len = 31.2   # 下底/最外侧内圈长度 (X方向)
ext_frame_width = 17.2       # 梯形内部宽度/高度 (Y方向)
frame_inner_r = 2.0          # 靠近品字头2角(内侧)圆角半径
frame_outer_r = 0.2          # 最外侧2角(远离品字头)圆角半径

# --- DC 母头参数 ---
corner_r = 1.0         # 矩形内角倒角半径 (mm)
inner_l = 14.0         # 底部长方形长度 X (mm)
inner_w = 12.0         # 底部长方形宽度 Y (mm)
base_h = 14.0          # 矩形段高度 (mm)
sq_side = 11.0         # 收缩顶端正方形边长 (mm)
taper_h = 10.0         # 收缩高度 (mm)
dc_inner_dia = 10.5    # DC 母头外径 / 贯通内孔直径 (mm)
top_h = 9.0            # 顶部圆柱高度 (mm)

# ============================================================
# 2. 关键坐标与高度计算
# ============================================================
y_max = inner_h / 2.0         # +8.0
y_min = -inner_h / 2.0        # -8.0
x_max = inner_w_max / 2.0     # ±12.0
x_top = inner_w_top / 2.0     # ±6.0
y_slant_start = y_min + straight_height # -8.0 + 9.8 = +1.8

# DC模块中心Y轴偏移量 (共壁核心算法)
dc_cy = y_max + wall_thick + (inner_w / 2.0)  # 8.0 + 1.8 + 6.0 = 15.8

# DC模块Z轴高度分界
z_base_top = base_h                    # Z = 14.0 mm
z_taper_top = z_base_top + taper_h     # Z = 24.0 mm
z_total_top = z_taper_top + top_h      # Z = 33.0 mm

# ============================================================
# 3. 自动生成对称多边形 (品字母头内腔)
# ============================================================
right_half = [
    (0.0,   y_max),           # 0. 顶部中心 (0, 8)
    (x_top, y_max),           # 1. 顶部右角 (6, 8)
    (x_max, y_slant_start),   # 2. 右侧斜边起点 (12, 1.8)
    (x_max, y_min),           # 3. 右下直角 (12, -8)
    (0.0,   y_min)            # 4. 底部中心 (0, -8)
]

left_half = [(-x, y) for x, y in reversed(right_half) if x != 0.0] 
inner_profile = right_half + left_half

CORNER_FILLETS_CONFIG = {
    0: 0.0, 1: 1.5, 2: 2.0, 3: 1.0, 4: 0.0
}

def analyze_corners_and_calc_limits(pts, wall_thickness, safety_margin=0.01):
    n = len(pts)
    corners = []
    for i in range(n):
        p_prev = pts[i - 1]
        p_curr = pts[i]
        p_next = pts[(i + 1) % n]
        v_in = (p_curr[0] - p_prev[0], p_curr[1] - p_prev[1])
        v_out = (p_next[0] - p_curr[0], p_next[1] - p_curr[1])
        len_in, len_out = math.hypot(*v_in), math.hypot(*v_out)
        
        if len_in < 1e-5 or len_out < 1e-5:
            corners.append({"index": i, "max_r_inner": 0.0, "p_inner": p_curr})
            continue

        v1_away, v2_away = (-v_in[0] / len_in, -v_in[1] / len_in), (v_out[0] / len_out, v_out[1] / len_out)
        dot = max(-1.0, min(1.0, v1_away[0]*v2_away[0] + v1_away[1]*v2_away[1]))
        angle = math.acos(dot)

        if angle < 1e-3 or abs(angle - math.pi) < 1e-3:
            corners.append({"index": i, "max_r_inner": 0.0, "p_inner": p_curr})
            continue

        t_max = min(len_in, len_out) / 2.0
        r_max_inner = max(0.0, t_max * math.tan(angle / 2.0) - safety_margin)
        corners.append({"index": i, "p_inner": p_curr, "max_r_inner": r_max_inner})
    return corners

corner_analysis = analyze_corners_and_calc_limits(inner_profile, wall_thick)
final_corner_data = []
n_pts, half_n = len(inner_profile), len(inner_profile) // 2

for i in range(n_pts):
    info = corner_analysis[i]
    cfg_idx = i if i <= half_n else n_pts - i
    user_val = CORNER_FILLETS_CONFIG.get(cfg_idx, None)
    info["applied_r_inner"] = info["max_r_inner"] if user_val is None else min(user_val, info["max_r_inner"])
    final_corner_data.append(info)

# ============================================================
# 4. 三维实体建模与合并
# ============================================================
print("\n🚀 开始品字头与 DC 模块融合建模...")

with BuildPart() as box:
    # --------------------------------------------------------
    # Step 1: 品字外壳主体 (Extrude to box_height: 22mm)
    # --------------------------------------------------------
    with BuildSketch() as inner_sk:
        Polygon(inner_profile)
        for info in final_corner_data:
            r_in = info["applied_r_inner"]
            if r_in > 0.001:
                pt = info["p_inner"]
                target_v = min(inner_sk.vertices(), key=lambda v: (v.X - pt[0])**2 + (v.Y - pt[1])**2)
                if (target_v.X - pt[0])**2 + (target_v.Y - pt[1])**2 < 1.0:
                    fillet(target_v, radius=r_in)

    with BuildSketch() as outer_sk:
        add(inner_sk)
        offset(amount=wall_thick, kind=Kind.ARC)
    extrude(amount=box_height)

    # --------------------------------------------------------
    # Step 2: 品字底部无底倒梯形框 (Extrude to box_height: 22mm)
    # --------------------------------------------------------
    y_attach_wall_bot = y_min - wall_thick  
    y_bot = y_attach_wall_bot - ext_frame_width  

    p_top_r, p_bot_r = (frame_inner_top_len / 2.0, y_attach_wall_bot), (frame_inner_bot_len / 2.0, y_bot)
    p_bot_l, p_top_l = (-frame_inner_bot_len / 2.0, y_bot), (-frame_inner_top_len / 2.0, y_attach_wall_bot)
    x_outer_top = frame_inner_top_len / 2.0 + wall_thick       

    with BuildSketch(Plane.XY) as frame_sk:
        with BuildSketch() as sk_in:
            Polygon([p_top_l, p_top_r, p_bot_r, p_bot_l])
            top_v = [v for v in sk_in.vertices() if abs(v.Y - y_attach_wall_bot) < 0.1]
            bot_v = [v for v in sk_in.vertices() if abs(v.Y - y_bot) < 0.1]
            if top_v and frame_inner_r > 0: fillet(top_v, radius=frame_inner_r)
            if bot_v and frame_outer_r > 0: fillet(bot_v, radius=frame_outer_r)
        
        with BuildSketch() as sk_out:
            add(sk_in)
            offset(amount=wall_thick, kind=Kind.ARC)

        with BuildSketch() as sk_fill_bot:
            Polygon([(13.8, y_slant_start-1), (x_outer_top+0.14, y_attach_wall_bot-2), (12.0, y_attach_wall_bot)])
            Polygon([(-13.8, y_slant_start-1), (-x_outer_top-0.14, y_attach_wall_bot-2), (-12.0, y_attach_wall_bot)])

        add(sk_out)
        add(sk_fill_bot)
        add(sk_in, mode=Mode.SUBTRACT)
    extrude(amount=box_height)

    # --------------------------------------------------------
    # Step 3: DC 母头共壁外框外层实体生成 (居中偏置Y向 15.8)
    # --------------------------------------------------------
    # 3.1 底部直筒长方形外壳 (Z=0 到 Z=14)
    with BuildSketch(Plane.XY) as dc_sk_base:
        with Locations((0, dc_cy)):
            Rectangle(inner_l + 2 * wall_thick, inner_w + 2 * wall_thick)
            fillet(dc_sk_base.vertices(), radius=corner_r + wall_thick)
    extrude(amount=base_h)

    # 3.2 渐变收缩段外壳 (Z=14 到 Z=24)
    with BuildSketch(Plane.XY.offset(z_base_top)) as dc_sk_mid_bot:
        with Locations((0, dc_cy)):
            Rectangle(inner_l + 2 * wall_thick, inner_w + 2 * wall_thick)
            fillet(dc_sk_mid_bot.vertices(), radius=corner_r + wall_thick)
    with BuildSketch(Plane.XY.offset(z_taper_top)) as dc_sk_mid_top:
        with Locations((0, dc_cy)):
            Rectangle(sq_side + 2 * wall_thick, sq_side + 2 * wall_thick)
            fillet(dc_sk_mid_top.vertices(), radius=corner_r + wall_thick)
    loft()

    # 3.3 顶部圆柱平滑外壳 (Z=24 到 Z=33)
    with BuildSketch(Plane.XY.offset(z_taper_top)) as dc_sk_top_bot:
        with Locations((0, dc_cy)):
            Rectangle(sq_side + 2 * wall_thick, sq_side + 2 * wall_thick)
            fillet(dc_sk_top_bot.vertices(), radius=corner_r + wall_thick)
    with BuildSketch(Plane.XY.offset(z_total_top)) as dc_sk_top_end:
        with Locations((0, dc_cy)):
            Circle(radius=dc_inner_dia / 2.0 + wall_thick)
    loft()

    # --------------------------------------------------------
    # Step 4: 【核心修复】完美圆滑过渡填充两模块缝隙
    # 采用几何精确交点与 4.0mm 半径 Fillet，彻底消除锐利台阶
    # --------------------------------------------------------
    with BuildSketch(Plane.XY) as sk_fill_top:
        # 1. 精确生成右侧过渡补骨
        with BuildLine():
            Polyline([
                (0.0, 12.0),
                (8.8, 12.0),
                (8.8, 7.695),    # 数学精确交点: DC右外墙与C13斜外墙交界
                (12.376, 4.0),   # 沿C13斜外墙向下无缝延伸点
                (0.0, 4.0),
                (0.0, 12.0)
            ])
        make_face()
        
        # 2. 精确生成左侧过渡补骨
        with BuildLine():
            Polyline([
                (0.0, 12.0),
                (-8.8, 12.0),
                (-8.8, 7.695),   # 左侧对称精准交点
                (-12.376, 4.0),
                (0.0, 4.0),
                (0.0, 12.0)
            ])
        make_face()
        
        # 3. 抓取交接的锐利拐角，打上 R=4.0 的大圆角，形成完美弧面
        target_verts = [
            min(sk_fill_top.vertices(), key=lambda v: (v.X - 8.8)**2 + (v.Y - 7.695)**2),
            min(sk_fill_top.vertices(), key=lambda v: (v.X + 8.8)**2 + (v.Y - 7.695)**2)
        ]
        fillet(target_verts, radius=4.0)
        
    extrude(amount=base_h) # 拉伸至 14mm 完美融合进模型

    # --------------------------------------------------------
    # Step 5: 掏空内腔 (分离掏空，保全共用 1.8mm 墙壁)
    # --------------------------------------------------------
    # 5.1 掏空品字头内腔 (带底板)
    with BuildSketch(Plane.XY.offset(base_thickness)):
        add(inner_sk)
    extrude(amount=inner_depth, mode=Mode.SUBTRACT)

    # 5.2 掏空 DC 矩形底层 (向下多退1mm，确保 Z=0 完全无底框)
    with BuildSketch(Plane.XY.offset(-1.0)) as sk_in_dc_base:
        with Locations((0, dc_cy)):
            Rectangle(inner_l, inner_w)
            fillet(sk_in_dc_base.vertices(), radius=corner_r)
    extrude(amount=base_h + 1.0, mode=Mode.SUBTRACT)

    # 5.3 掏空 DC 渐变段
    with BuildSketch(Plane.XY.offset(z_base_top)) as sk_in_dc_mid_bot:
        with Locations((0, dc_cy)):
            Rectangle(inner_l, inner_w)
            fillet(sk_in_dc_mid_bot.vertices(), radius=corner_r)
    with BuildSketch(Plane.XY.offset(z_taper_top)) as sk_in_dc_mid_top:
        with Locations((0, dc_cy)):
            Rectangle(sq_side, sq_side)
            fillet(sk_in_dc_mid_top.vertices(), radius=corner_r)
    loft(mode=Mode.SUBTRACT)

    # 5.4 掏空 DC 顶部圆柱台阶
    with BuildSketch(Plane.XY.offset(z_taper_top - 0.1)) as sk_in_dc_top:
        with Locations((0, dc_cy)):
            Circle(radius=dc_inner_dia / 2.0)
    extrude(amount=top_h + 2.0, mode=Mode.SUBTRACT)

    # --------------------------------------------------------
    # Step 6: 钻出品字外壳需要的侧孔 (孔全部避开共壁)
    # --------------------------------------------------------
    with BuildSketch(Plane.XY):
        with Locations((0, y_min + slot_dist_from_bot)):
            SlotOverall(width=slot_len, height=slot_h)
    extrude(amount=box_height + 5, mode=Mode.SUBTRACT)

    with BuildSketch(Plane.XY):
        with Locations((0, y_max - 4)):
            Circle(radius=3.4 / 2)
    extrude(amount=box_height + 5, mode=Mode.SUBTRACT)

print("✅ DC共壁品字头复合模型生成完毕！准备输出。")

# ============================================================
# 5. 渲染与输出
# ============================================================
import os, bambu_slicer, cadquery as cq

step_file = os.path.splitext(__file__)[0] + f"_{base_thickness}.step"
export_step(box.part, step_file)
cq_object = cq.Shape(box.part.wrapped)
cq_object = bambu_slicer.add_brim(cq_object, 0)

if "show_object" in locals():
    show_object(cq_object, name=step_file[:-5])

f = bambu_slicer.to_gcode(
    cq_object=cq_object,
    name=step_file,
    output_dir=r"D:\test\bambu-studio",
    material='PETG',
)