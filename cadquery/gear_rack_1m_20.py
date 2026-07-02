import cadquery as cq

# ================== 1. 基础参数 ==================
w = 100
t = 2       # 板厚 10.3mm
x = 50         # X 轴中心

# ================== 2. 创建主板 ==================
board = cq.Workplane("XY").box(w, w, t)

# 孔位收集器
holes_26_6 = []
holes_8    = []
holes_6    = []
holes_5    = []
hex_holes  = []

# ================== 3. 绝对坐标计算与孔位收集 ==================
y = w - 2 - 47.5 / 2  # 74.25

# 上方固定孔
y1 = y - (47.5 / 2 + 10)  # 40.5
y1h = y1 - 13.5           # 27.0
holes_6.append((x, y1h))
holes_6.append((x - 70/2, y1h))
holes_6.append((x + 70/2, y1h))

# 中间辅助固定孔
holes_6.append((x - 60/2, y - 4))
holes_6.append((x + 60/2, y - 4))

# KFL8 相关孔位 (物理圆孔)
holes_8.append((x, y))            # 中心轴通孔
holes_26_6.append((x, y))         # 中央圆形
holes_5.append((x - 18.25, y))    # 左固定孔
holes_5.append((x + 18.25, y))    # 右固定孔

# 齿条阵列 (M=6) 的六角螺母孔
dgr = y + 20 - 0.2  # 94.05
d = 4
M = 6
for i in range(M):
    xi = (i + 0.5) * (w / M)
    if i in [0, 5]:
        hex_holes.append((xi, dgr + d/2, 7))


# ================== 4. KFL8 法兰异形外廓切除 (绝对坐标版) ==================
def cut_kfl8_outline(solid, kx, ky):
    q1 = [(24.00, 0.00), (23.55, 2.28), (22.26, 4.22), (20.33, 5.53), 
          (5.06, 12.2), (4.08, 12.5), (3.09, 12.8), (2.07, 13), 
          (1.04, 13.17), (0.00, 13.3)]
    
    top = [(dx, dy) for dx, dy in q1] + [(-dx, dy) for dx, dy in reversed(q1[:-1])]
    bottom = [(-px, -py) for px, py in top[1:]]
    rel_path = top + bottom
    
    cq_points = []
    for dx, dy in rel_path:
        px = kx + dx
        py = ky + dy
        cq_points.append((px - w / 2.0, w / 2.0 - py))
        
    # 【修复】使用绝对不变的 XY 顶面作为基准生成实体，再进行硬切
    cutter = (
        cq.Workplane("XY")
        .workplane(offset=t/2)
        .polyline(cq_points).close()
        .extrude(-t - 2)
    )
    return solid.cut(cutter)

# 执行 KFL8 异形切除
board = cut_kfl8_outline(board, x, y)


# ================== 5. 执行常规钻孔流水线 (绝对坐标+自动去重) ==================
def drill_holes(solid, pts, diam):
    if not pts: return solid
    unique_pts = list(dict.fromkeys(pts))
    cq_points = [(px - w/2, w/2 - py) for px, py in unique_pts]
    
    # 【修复】改用独立绝对基准面，防止圆孔因重心改变而向边缘漂移错位
    cutters = (
        cq.Workplane("XY")
        .workplane(offset=t/2)
        .pushPoints(cq_points)
        .circle(diam / 2.0)
        .extrude(-t - 2)
    )
    return solid.cut(cutters)

# 执行标准圆形通孔切削
board = drill_holes(board, holes_26_6, 26.6)
board = drill_holes(board, holes_8, 8)
board = drill_holes(board, holes_6, 6)
board = drill_holes(board, holes_5, 5)

# 执行六角螺母孔切削 (绝对坐标版)
for hx, hy, dia in hex_holes:
    cq_hx = hx - w/2
    cq_hy = w/2 - hy
    # 【修复】杜绝循环中因面拓扑改变导致的原点漂移
    hex_cutter = (
        cq.Workplane("XY")
        .workplane(offset=t/2)
        .center(cq_hx, cq_hy)
        .polygon(6, dia)
        .extrude(-t - 2)
    )
    board = board.cut(hex_cutter)


# ================== 6. 实体区域粗切除 (滑槽/减重槽) ==================
def clip_kicad_range(y1_kicad, y2_kicad):
    global board
    y_min_kicad = min(y1_kicad, y2_kicad)
    y_max_kicad = max(y1_kicad, y2_kicad)
    
    cq_y_max = w / 2.0 - y_min_kicad
    cq_y_min = w / 2.0 - y_max_kicad
    cut_box_len = cq_y_max - cq_y_min
    cut_box_y_center = cq_y_min + cut_box_len / 2.0
    
    cutter = (
        cq.Workplane("XY")
        .center(0, cut_box_y_center)
        .box(w + 50, cut_box_len, t + 50)
    )
    
    final_solid = board.val().cut(cutter.val())
    board = cq.Workplane(obj=final_solid)

# 如果不需要切除齿条区域，保持注释即可
# clip_kicad_range(dgr - 10, dgr)
def keep_kicad_range(y1_keep, y2_keep):
    """
    正向保留函数：指定 KiCad Y 轴上需要【保留】的中间区域，自动切除两端。
    :param y1_keep: 保留区域的一个边界
    :param y2_keep: 保留区域的另一个边界
    """
    # 1. 自动识别保留区间的上边界和下边界
    keep_min = min(y1_keep, y2_keep)
    keep_max = max(y1_keep, y2_keep)
    
    # 2. 切除上方多余材料：从 KiCad 坐标 0 一直切到保留区的起点
    if keep_min > 0:
        clip_kicad_range(0, keep_min)
        
    # 3. 切除下方多余材料：从保留区的终点一直切到板子边缘 w (100)
    if keep_max < w:
        clip_kicad_range(keep_max, w)
# 切除底部边缘
y2 = y1 - 30  # 10.5
wg = 24
keep_kicad_range(50,100)


# ================== 7. 导出结果 ==================
cq.exporters.export(board, __file__ + ".step")
if "show_object" in globals():
    show_object(board)