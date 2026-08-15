import os,math
import cadquery as cq
import build123d_fix
from build123d import *

# ============================================================
# 1. 核心尺寸参数定义（基于阶梯插座精确内腔尺寸）
# ============================================================
# -- 阶梯内腔双段尺寸 --
inner_L1 = 45.0          # 左侧内腔长度 (X方向, mm)
inner_W1 = 44.0          # 左侧内腔高度 (Y方向, mm)
inner_L2 = 30.0          # 右侧内腔长度 (X方向, mm)
inner_W2 = 55.5          # 右侧内腔高度 (Y方向, mm)

# -- 外壳与厚度参数 --
wall_thick = 2         # 盒子外沿壁厚 (mm) - 向外等距拓展
inner_height = 39      # 内腔深度/拉伸高度 (mm)
base_thickness = 0.0     # 底板厚度 (mm) - 设为0即为通孔框架，>0即为带底盒
box_height = inner_height + base_thickness

# ============================================================
# 2. 精确极值计算 (以几何中心 (0,0) 为原点构建轮廓，Y轴中线对齐)
# ============================================================
total_width = inner_L1 + inner_L2  # 75.0 mm

cx = total_width / 2.0             # 37.5 mm (X轴平移量，使整体居中)

# 左右两侧的Y轴极值 (以中线 Y=0 为基准)
y1_max = inner_W1 / 2.0            # 左侧上半部: +22.0
y1_min = -inner_W1 / 2.0           # 左侧下半部: -22.0
y2_max = inner_W2 / 2.0            # 右侧上半部: +27.75
y2_min = -inner_W2 / 2.0           # 右侧下半部: -27.75

# X轴关键节点
x_left = -cx                       # 最左侧: -37.5
x_mid = inner_L1 - cx              # 阶梯交界处: 7.5
x_right = total_width - cx         # 最右侧: 37.5

# ============================================================
# 3. 自动生成多边形 (精准表达 阶梯插座 中线对齐内腔外轮廓)
# ============================================================
# 逆时针依次追踪 8 个点
inner_profile = [
    (x_left, y1_min),      # 0. 左侧内腔 左下角 (-37.5, -22.0)
    (x_mid, y1_min),       # 1. 左右交界 下凹角 (7.5, -22.0)
    (x_mid, y2_min),       # 2. 右侧内腔 左下凸角 (7.5, -27.75)
    (x_right, y2_min),     # 3. 右侧内腔 右下角 (37.5, -27.75)
    (x_right, y2_max),     # 4. 右侧内腔 右上角 (37.5, 27.75)
    (x_mid, y2_max),       # 5. 右侧内腔 左上凸角 (7.5, 27.75)
    (x_mid, y1_max),       # 6. 左右交界 上凹角 (7.5, 22.0)
    (x_left, y1_max),      # 7. 左侧内腔 左上角 (-37.5, 22.0)
]

# ------------------------------------------------------------
# 显式定义所有拐角的圆角设置 (CORNER_FILLETS_CONFIG)
# - 数值：自定义圆角半径（自动防超限裁切）
# - None：自动套用该拐角的最大安全圆角极限
# ------------------------------------------------------------
CORNER_FILLETS_CONFIG = {
    0: 0.0,   # 0. 左侧 左下角 -> 平角(0mm)
    1: 1.5,   # 1. 交界 下凹角 -> 1.5mm
    2: 1.5,   # 2. 右侧 左下角 -> 1.5mm
    3: 1.5,   # 3. 右侧 右下角 -> 1.5mm
    4: 1.5,   # 4. 右侧 右上角 -> 1.5mm
    5: 1.5,   # 5. 右侧 左上角 -> 1.5mm
    6: 1.5,   # 6. 交界 上凹角 -> 1.5mm
    7: 0.0,   # 7. 左侧 左上角 -> 平角(0mm)
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
    user_val = CORNER_FILLETS_CONFIG.get(i, None)

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
pts = []             # 无额外定位孔时保持空列表

print("\n🚀 开始三维实体建模...")

# ============================================================
# 6. 建模核心逻辑 (Python 原生 min 寻找顶点倒角 + 自动过渡外壁)
# ============================================================
with BuildPart() as box:
    # 6.1 生成内腔草图并在 2D 草图顶点直接做倒角
    with BuildSketch() as inner_sk:
        Polygon(inner_profile)
        # 逐点倒角，使用 Python 原生 min
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
    extrude(amount=inner_height + 5.0, mode=Mode.SUBTRACT)  # 增加5mm掏空深度确保贯通

    # 6.4 批量打孔 (如有需求)
    if pts:
        top_face = box.faces().sort_by(Axis.Z)[-1]
        with Locations(top_face):
            with Locations(*pts):
                Hole(radius=drill_diameter / 2, depth=box_height + 5)

    # 左侧内腔底面生成 2mm宽、1mm 厚的内部筋条
    with BuildSketch(Plane.XY.offset(base_thickness)):
        with Locations((x_left, 0.0)):
            Rectangle(2, inner_W1)
    extrude(amount=1.0)
print("✅ 模型生成完毕！准备输出。")

# ============================================================
# 7. 渲染与输出
# ============================================================
import bambu_slicer

step_file = os.path.splitext(__file__)[0] + f"_{base_thickness}.step" if "__file__" in globals() else f"socket_frame_{base_thickness}.step"
export_step(box.part, step_file)
cq_object = cq.Shape(box.part.wrapped)
cq_object = bambu_slicer.add_brim(cq_object, 5)

if "show_object" in locals():
    show_object(cq_object, name=step_file[:-5])

try:
    f = bambu_slicer.to_gcode(
        cq_object=cq_object,
        name=step_file,
        output_dir=r"D:\test\bambu-studio",
        material='PETG',
    )
except Exception:
    pass