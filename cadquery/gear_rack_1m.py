import cadquery as cq

# ================== 1. 基础参数 ==================
w = 100
t = 10.3       # 板厚 10mm
x = 50       # X 轴中心

# ================== 2. 创建主板 ==================
board = cq.Workplane("XY").box(w, w, t)

# 建立不同直径的孔位收集器 (直接存入 KiCad 绝对坐标)
holes_24 = []
holes_10 = []
holes_6  = []
holes_5  = []
holes_4  = []

# ================== 3. 坐标平铺写入 ==================

# ----------------- A. 上方 8mm 轴承座 -----------------
y1 = 47.5 / 2  # 23.75
holes_24.append((x, y1))                           
holes_5.append((x - 36.5/2, y1))                   
holes_5.append((x + 36.5/2, y1))
holes_4.append((x, y1 - 36.5/2))                   

# ----------------- B. 齿条阵列 (M=6) -----------------
dgr = y1 + 20 - 0.2  # 43.55
d = 4

for i in range(6):
    xi = (i + 0.5) * (w / 6.0)
    holes_4.append((xi, dgr + d/2))
    if i in [0, 5]:
        holes_4.append((xi, dgr - 10 - d/2 - 0.5))
    if i not in [1, 4]:
        holes_4.append((xi, dgr + d + 10 + d/2 + 0.5))

# ----------------- C. 中间辅助固定孔 -----------------
holes_6.append((x - 60/2, y1 - 4))
holes_6.append((x + 60/2, y1 - 4))

holes_6.append((50 - 30, 50 - 30))
holes_6.append((50 + 30, 50 - 30))
holes_6.append((50 - 30, 50 + 30))
holes_6.append((50 + 30, 50 + 30))

# ----------------- D. 下方 10mm 轴承座 -----------------
yb = dgr + d
y2 = yb + 19.9

holes_10.append((x, y2))                           
holes_6.append((x - 45/2, y2))                     
holes_6.append((x + 45/2, y2))


# ================== 4. 执行钻孔流水线 ==================
def drill_holes(solid, pts, diam):
    if not pts: return solid
    cq_points = [(px - w/2, w/2 - py) for px, py in pts]
    return (
        solid.faces(">Z")
        .workplane()
        .pushPoints(cq_points)
        .circle(diam / 2.0)
        .cutThruAll()
    )

board = drill_holes(board, holes_24, 24)
board = drill_holes(board, holes_10, 10)
board = drill_holes(board, holes_6, 6)
board = drill_holes(board, holes_5, 5)
board = drill_holes(board, holes_4, 4.5)
print(len(holes_4))

def clip_kicad_range(y1_kicad, y2_kicad):
    """
    在 KiCad 坐标系下，将 y1 到 y2 范围内的实体全部切除。
    自动引用全局定义的 board, w, t。
    """
    # 确保 y1 是较小值，y2 是较大值，防止传参顺序颠倒
    y_min_kicad = min(y1_kicad, y2_kicad)
    y_max_kicad = max(y1_kicad, y2_kicad)
    
    # 1. 转换为 CadQuery 中心坐标系下的 Y 轴位置
    # 记住：KiCad 的 Y 轴向下，所以 KiCad 的最大值对应 CQ 的最小值
    cq_y_max = w / 2.0 - y_min_kicad
    cq_y_min = w / 2.0 - y_max_kicad
    
    # 2. 计算切除方块的 Y 方向总长度（区间跨度）
    cut_box_len = cq_y_max - cq_y_min
    
    # 3. 计算切除方块在 CQ 中的 Y 轴中心点
    cut_box_y_center = cq_y_min + cut_box_len / 2.0
    
    # 4. 建立一个独立的临时“大粗刀”方块（宽度和厚度给足余量）
    cutter = (
        cq.Workplane("XY")
        .center(0, cut_box_y_center)
        .box(w + 50, cut_box_len, t + 50)
    )
    
    # 5. 提取底层纯实体进行强行硬切，并直接更新全局的 board 变量
    global board
    raw_board_solid = board.val()
    raw_cutter_solid = cutter.val()
    
    final_solid = raw_board_solid.cut(raw_cutter_solid)
    board = cq.Workplane(obj=final_solid)# ================== 6. 导出结果 ==================
clip_kicad_range(dgr-10,dgr)

clip_kicad_range(dgr + 4 + 16, 100)

cq.exporters.export(board, __file__+f".step")
show_object(board)  # 只保留这一行，显示最终的主板