import build123d_fix
import math
from build123d import *

# ============================================================
# 1. 核心尺寸参数定义（基于精确的 PCB/内腔尺寸）
# ============================================================
# -- 高度与主身 --
box_h_total = 96+1     # 上下总高 (Y方向)
box_w_body  = 127+1     # 主体宽 (不含吊耳, X方向)

# -- 上吊耳 --
ear_top_w   = 170.0      # 左右含吊耳总宽
ear_top_len = 20.0       # 上吊耳上下高度

# -- 顶部外凸特征 --
top_bulge_w = 107.0      # 上部中间段宽度
top_bulge_amount = 2.0   # 上部中间外凸量 (mm)

# -- 下吊耳 --
ear_bot_w   = 145+1      # 下小吊耳外距离
ear_bot_len = 13+1       # 下吊耳上下高度
ear_bot_top_dist = 36.0  # 下吊耳上沿距离底部的高度

# -- 底部特征 --
bot_flat_w  = 98.0       # 底部去除斜边后的直线段宽度
slant_y_offset = 10.0    # 侧面开始向内收斜角的位置（距底部的垂直高度）

# -- 盒子厚度参数 --
wall_thick = 2           # 盒子外沿壁厚 (mm) - 会在内腔基础上向外拓展
inner_height = 30        # 内腔深度 (mm)
base_thickness = 2       # 底板厚度 (mm)
box_height = inner_height + base_thickness

# ============================================================
# 2. 精确极值计算 (以原点0,0为中心，构建内腔/PCB轮廓)
# ============================================================
y_max = box_h_total / 2.0                       # 顶边基准: +48.0
y_min = -box_h_total / 2.0                      # 底边基准: -48.0
x_body = box_w_body / 2.0                       # 侧壁: ±63.5
x_top_ear = ear_top_w / 2.0                     # 上耳外侧: ±85.0
x_bot_ear = ear_bot_w / 2.0                     # 下耳外侧: ±72.5
x_bot_flat = bot_flat_w / 2.0                   # 底部直边: ±49.0
x_top_bulge = top_bulge_w / 2.0                 # 顶部凸起边缘: ±53.5

# 下吊耳及斜边 Y轴计算
y_bot_ear_top = y_min + ear_bot_top_dist        # 下耳上沿: -12.0
y_bot_ear_bot = y_bot_ear_top - ear_bot_len     # 下耳下沿: -25.0
y_slant_start = y_min + slant_y_offset          # 斜边起点: -38.0

# ============================================================
# 3. 自动生成对称多边形 (精准表达 PCB/内腔外轮廓)
# ============================================================
right_half = [
    (0.0,         y_max + top_bulge_amount),  # 0. 顶部中心外凸点 (0, 50)
    (x_top_bulge, y_max + top_bulge_amount),  # 1. 顶部外凸右拐角 (53.5, 50)
    (x_top_bulge, y_max),                     # 2. 跌回基准顶边 (53.5, 48)
    (x_top_ear,   y_max),                     # 3. 顶边直达右上吊耳外上角 (85, 48)
    (x_top_ear,   y_max - ear_top_len),       # 4. 右上吊耳外下角 (85, 28)
    (x_body,      y_max - ear_top_len),       # 5. 退回右主侧壁 (63.5, 28)
    (x_body,      y_bot_ear_top),             # 6. 右侧壁抵下吊耳上缘 (63.5, -12)
    (x_bot_ear,   y_bot_ear_top),             # 7. 右下吊耳外上角 (72.5, -12)
    (x_bot_ear,   y_bot_ear_bot),             # 8. 右下吊耳外下角 (72.5, -25)
    (x_body,      y_bot_ear_bot),             # 9. 退回右主侧壁 (63.5, -25)
    (x_body,      y_slant_start),             # 10. 右侧斜边起点 (63.5, -38)
    (x_bot_flat,  y_min),                     # 11. 底部斜边终点 (49, -48)
    (0.0,         y_min)                      # 12. 底部中心 (0, -48)
]

left_half = [(-x, y) for x, y in reversed(right_half) if x != 0.0] # 自动镜像左半边（排除中心点避免顶点重复）
inner_profile = right_half + left_half
# ------------------------------------------------------------
# 显式定义所有拐角的圆角设置 (CORNER_FILLETS_CONFIG)
# - 数值：自定义圆角半径（自动防超限裁切）
# - None：自动套用该拐角的最大安全圆角极限
# ------------------------------------------------------------
CORNER_FILLETS_CONFIG = {
    0:  0.0,   # 顶部中心 (0, 50) - 平角
    1:  None,  # 顶部外凸右拐角 (53.5, 50) -> 自动设为极限 (0.99mm)
    2:  None,  # 跌回基准顶边 (53.5, 48)   -> 自动设为极限 (0.99mm)
    3:  3.0,   # 右上吊耳外上角 (85, 48)   -> 显式自定义 3.0mm
    4:  2.0,   # 右上吊耳外下角 (85, 28)   -> 显式自定义 2.0mm
    5:  2.0,   # 退回右主侧壁 (63.5, 28)   -> 显式自定义 2.0mm
    6:  4,   # 右侧壁抵下吊耳上缘 (63.5, -12)
    7:  2.0,   # 右下吊耳外上角 (72.5, -12)
    8:  2.0,   # 右下吊耳外下角 (72.5, -25)
    9:  4,   # 退回右主侧壁 (63.5, -25)
    10: 2.0,   # 右侧斜边起点 (63.5, -38)
    11: 3.0,   # 底部斜边终点 (49, -48)
    12: 0.0,   # 底部中心 (0, -48) - 平角
}

# ============================================================
# 4. 逐拐角精准极限算法 & 显式圆角定义
# ============================================================
def analyze_corners_and_calc_limits(pts, wall_thickness, safety_margin=0.01):
    n = len(pts)
    corners = []
    for i in range(n):
        p_prev = pts[i - 1]
        p_curr = pts[i]
        p_next = pts[(i + 1) % n]

        v_in = (p_curr[0] - p_prev[0], p_curr[1] - p_prev[1])
        v_out = (p_next[0] - p_curr[0], p_next[1] - p_curr[1])

        len_in = math.hypot(v_in[0], v_in[1])
        len_out = math.hypot(v_out[0], v_out[1])

        if len_in < 1e-5 or len_out < 1e-5:
            corners.append({"index": i, "type": "平角", "max_r_inner": 0.0, "p_inner": p_curr})
            continue

        v1_away = (-v_in[0] / len_in, -v_in[1] / len_in)
        v2_away = (v_out[0] / len_out, v_out[1] / len_out)

        dot = max(-1.0, min(1.0, v1_away[0]*v2_away[0] + v1_away[1]*v2_away[1]))
        angle = math.acos(dot)

        if angle < 1e-3 or abs(angle - math.pi) < 1e-3:
            corners.append({"index": i, "type": "平角", "max_r_inner": 0.0, "p_inner": p_curr})
            continue

        cross = v_in[0] * v_out[1] - v_in[1] * v_out[0]
        corner_type = "凸角" if cross < 0 else "凹角"

        t_max = min(len_in, len_out) / 2.0
        r_max_inner = max(0.0, t_max * math.tan(angle / 2.0) - safety_margin)

        corners.append({
            "index": i,
            "p_inner": p_curr,
            "type": corner_type,
            "angle_deg": math.degrees(angle),
            "max_r_inner": r_max_inner
        })
    return corners

corner_analysis = analyze_corners_and_calc_limits(inner_profile, wall_thick)



final_corner_data = []
n_pts = len(inner_profile)

print("\n" + "="*70)
print("📐 逐拐角独立最大圆角计算与内外壁分配结果表")
print("="*70)
print(f"{'索引':^4} | {'拐角类型':^6} | {'内腔坐标(X, Y)':^18} | {'最大安全内R':^10} | {'最终内圆角':^9} | {'最终外圆角':^9}")
print("-" * 70)

for i in range(n_pts):
    info = corner_analysis[i]
    cfg_idx = i if i <= 12 else (24 - i) % 24
    user_val = CORNER_FILLETS_CONFIG.get(cfg_idx, None)

    if user_val is None:
        r_in = info["max_r_inner"]
    else:
        r_in = min(user_val, info["max_r_inner"])

    if info["type"] == "凸角":
        r_out = r_in + wall_thick if r_in > 0 else wall_thick
    elif info["type"] == "凹角":
        r_out = max(0.0, r_in - wall_thick)
    else:
        r_out = 0.0

    info["applied_r_inner"] = r_in
    info["applied_r_outer"] = r_out
    final_corner_data.append(info)

    px, py = info["p_inner"]
    print(f"{i:^4} | {info['type']:^6} | ({px:>6.1f}, {py:>6.1f}) | {info['max_r_inner']:>8.2f} mm | {r_in:>7.2f} mm | {r_out:>7.2f} mm")

print("="*70)

# ============================================================
# 5. 打孔坐标设置
# ============================================================
drill_diameter = 4   # M3螺丝孔径

hole_top_x = (x_body + x_top_ear) / 2.0
hole_top_y = y_max - (ear_top_len / 2.0)

hole_bot_x = (x_body + x_bot_ear) / 2.0 + 14
hole_bot_y = y_bot_ear_top - (ear_bot_len / 2.0) - 6

pts = []

print("\n🚀 开始三维实体建模...")

# ============================================================
# 6. 建模核心逻辑 (Python 原生 min 寻找顶点倒角 + 自动过渡外壁)
# ============================================================
with BuildPart() as box:
    # 6.1 生成内腔草图并在 2D 草图顶点直接做倒角
    with BuildSketch() as inner_sk:
        Polygon(inner_profile)
        # 逐点倒角，使用 Python 原生 min 替代 build123d 中不存在的 min_by
        for info in final_corner_data:
            r_in = info["applied_r_inner"]
            if r_in > 0.001:
                pt = info["p_inner"]
                target_v = min(inner_sk.vertices(), key=lambda v: (v.X - pt[0])**2 + (v.Y - pt[1])**2)
                dist_sq = (target_v.X - pt[0])**2 + (target_v.Y - pt[1])**2
                if dist_sq < 1.0:  # 容差范围内匹配成功
                    fillet(target_v, radius=r_in)

    # 6.2 外壁轮廓扩展 (kind=Kind.ARC 保证内外圆角联动平滑过渡)
    with BuildSketch() as outer_sk:
        add(inner_sk)
        offset(amount=wall_thick, kind=Kind.ARC)
    extrude(amount=box_height)

    # 6.3 从底板上方掏空内腔
    with BuildSketch(Plane.XY.offset(base_thickness)):
        add(inner_sk)
    extrude(amount=inner_height, mode=Mode.SUBTRACT)

    # 6.4 批量打孔 (打通外沿法兰)
    if pts:
        top_face = box.faces().sort_by(Axis.Z)[-1]
        with Locations(top_face):
            with Locations(*pts):
                Hole(radius=drill_diameter / 2, depth=box_height + 5)

        with Locations(box.faces().sort_by(Axis.Z)[-1]):
            with Locations((0,-3)):
                Hole(radius=40, depth=box_height + 5)

print("✅ 模型生成完毕！准备输出。")

# ============================================================
# 7. 渲染与输出
# ============================================================
import os, bambu_slicer, cadquery as cq
step_file = os.path.splitext(__file__)[0] + f"_{base_thickness}.step"
export_step(box.part, step_file)
cq_object = cq.Shape(box.part.wrapped)

if "show_object" in locals():
    show_object(cq_object, name=step_file[:-5])

f = bambu_slicer.to_gcode(
    cq_object=box,
    name=step_file,
    output_dir=r"D:\test\bambu-studio",
    material='PETG',
)