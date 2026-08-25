import build123d_fix
import math
from build123d import *

# ============================================================
# 1. 核心尺寸参数定义（基于 IEC 60320 C13 轮廓）
# ============================================================
# -- 核心内腔尺寸 (内径) --
inner_h = 16.0         # 内部总高 (Y方向)
inner_w_max = 24.0     # 底部长边最大宽度 (X方向)
inner_w_top = 12.0     # 顶部小宽度 (X方向)
straight_height = 9.8  # 底边向上直边高度

# -- 长圆孔参数 --
slot_len = 5.0             # 长圆孔长度 (X方向)
slot_h = 2.7               # 长圆孔高度 (Y方向)
slot_dist_from_bot = 5.0   # 距离底部 24mm 长边的垂直距离

# -- 外壳与厚度参数 --
wall_thick = 1.8      # 侧壁厚度 (mm)
inner_depth = 20.0    # 内腔深度 (mm)
base_thickness = 2.0   # 底板厚度 (mm)
box_height = inner_depth + base_thickness

# -- 附加无底方框参数 (长边24mm外侧) --
ext_frame_len = 31.0   # 方框长度 (X方向, 对应24mm边居中)
ext_frame_width = 17 # 方框宽度 (Y方向)

# ============================================================
# 2. 精确极值计算 (以原点0,0为中心)
# ============================================================
y_max = inner_h / 2.0         # +8.0
y_min = -inner_h / 2.0        # -8.0
x_max = inner_w_max / 2.0     # ±12.0
x_top = inner_w_top / 2.0     # ±6.0

y_slant_start = y_min + straight_height # -8.0 + 9.8 = +1.8

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
    0: 0.0,   # 顶部中心
    1: 1.5,   # 顶部右角
    2: 2.0,   # 钝角转折
    3: 1.0,   # 底部直角
    4: 0.0,   # 底部中心
}

# ============================================================
# 4. 逐拐角精准极限算法
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
half_n = n_pts // 2

for i in range(n_pts):
    info = corner_analysis[i]
    cfg_idx = i if i <= half_n else n_pts - i
    user_val = CORNER_FILLETS_CONFIG.get(cfg_idx, None)

    r_in = info["max_r_inner"] if user_val is None else min(user_val, info["max_r_inner"])
    info["applied_r_inner"] = r_in
    final_corner_data.append(info)

# ============================================================
# 5. 三维实体建模与开孔
# ============================================================
print("\n🚀 开始三维实体建模...")

with BuildPart() as box:
    # 5.1 生成内腔草图并做顶点倒角
    with BuildSketch() as inner_sk:
        Polygon(inner_profile)
        for info in final_corner_data:
            r_in = info["applied_r_inner"]
            if r_in > 0.001:
                pt = info["p_inner"]
                target_v = min(inner_sk.vertices(), key=lambda v: (v.X - pt[0])**2 + (v.Y - pt[1])**2)
                if (target_v.X - pt[0])**2 + (target_v.Y - pt[1])**2 < 1.0:
                    fillet(target_v, radius=r_in)

    # 5.2 外壁轮廓扩展 (壁厚1.8mm)
    with BuildSketch() as outer_sk:
        add(inner_sk)
        offset(amount=wall_thick, kind=Kind.ARC)

    # 5.3 拉伸品字外壳主体
    extrude(amount=box_height)

    # 5.4 从底板上方掏空品字内腔
    with BuildSketch(Plane.XY.offset(base_thickness)):
        add(inner_sk)
    extrude(amount=inner_depth, mode=Mode.SUBTRACT)

    # 5.5 距底部 24mm 长边 5mm 处打贯通长圆孔
    with BuildSketch(Plane.XY):
        with Locations((0, y_min + slot_dist_from_bot)):
            SlotOverall(width=slot_len, height=slot_h)
    extrude(amount=box_height + 5, mode=Mode.SUBTRACT)

    # 5.6 距顶部短边 4mm 处打 3.4mm 贯通圆孔
    with BuildSketch(Plane.XY):
        with Locations((0, y_max - 4)):
            Circle(radius=3.4 / 2)
    extrude(amount=box_height + 5, mode=Mode.SUBTRACT)

    # 5.7 在 24mm 长边外侧生成无底方框 (31mm x 27.3mm，壁厚1.8mm，贯通全高)
    y_attach_wall = y_min #- wall_thick  # 24mm 长边外壁 Y 坐标 (-9.8mm)
    frame_y_center = y_attach_wall - (ext_frame_width / 2.0)

    with BuildSketch(Plane.XY):
        with Locations((0, frame_y_center)):
            Rectangle(ext_frame_len, ext_frame_width)
            Rectangle(ext_frame_len - 2 * wall_thick, ext_frame_width - 2 * wall_thick, mode=Mode.SUBTRACT)
    extrude(amount=box_height)

print("✅ 模型生成完毕！准备输出。")

# ============================================================
# 6. 渲染与输出
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