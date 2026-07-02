import sys;'qgb.U' in sys.modules or sys.path.append('C:/QGB/Anaconda3/Lib/site-packages/Pythonwin/');from qgb import *
import os
import sys
import json
import math
import cadquery as cq

# ================== 1. 基础参数 ==================
board_w = 100.0  # 主板宽度
board_h = 100.4  # 对应原脚本中的 w=100.4
t = 0.4          # 根据你图 1 中的实际板厚 t=10.3

# ================== 2. 创建主板实体 ==================
board = cq.Workplane("XY").box(board_w, board_h, t)

# 孔位收集器（注意：存入此处的必须是【原始 KiCad 坐标】）
holes_6 = []
holes_4 = []
holes_5 = []     # 存放你图 1 中的自定义 5mm 孔，请确保传入的是原始 KiCad 坐标！

# 四个方形结构的中心绝对坐标（原始 KiCad 坐标）
hex_centers = [
    [35, 37.9], [65, 37.9],
    [35, 72.4], [65, 72.4]]

# ─── 预览标记收集器（不参与实体切削） ───
marker_squares = []  # 收集 20x20 正方形线框中心
marker_dots = []     # 收集 1mm 的角标记点

# ================== 3. 绝对坐标计算与分流 ==================

# 3.1 解析 s20(x, y) 内部特征
for x, y in hex_centers:
    # 转换为 CadQuery 内部绝对坐标，用于构建纯视觉标记
    cq_x = x - board_w / 2.0
    cq_y = board_h / 2.0 - y
    
    # 收集 20x20 方框中心
    marker_squares.append((cq_x, cq_y))
    
    # 收集原 hole_rect_center 四个角上的 1mm 辅助点
    marker_dots.append((cq_x - 10, cq_y - 10))
    marker_dots.append((cq_x + 10, cq_y - 10))
    marker_dots.append((cq_x - 10, cq_y + 10))
    marker_dots.append((cq_x + 10, cq_y + 10))

# 3.2 解析独立的 6mm 圆孔
for x, y in [[35, 37.9], [65, 37.9]]:
    holes_6.append((x, y + 1))

# 3.3 解析 two_hole 逻辑
y_two_hole = board_h - 40
holes_4.append((50 - 80 / 2, y_two_hole))
holes_4.append((50 + 80 / 2, y_two_hole))


# ================== 4. 执行常规圆形通孔切削（安全版） ==================
def drill_holes(solid, pts, diam):
    if not pts: return solid
    unique_pts = list(dict.fromkeys(pts))
    
    # 核心映射转换
    cq_points = [(px - board_w / 2.0, board_h / 2.0 - py) for px, py in unique_pts]
    
    # 【安全修正】放弃 cutThruAll()，改回实体拉伸切削。
    cutters = (
        cq.Workplane("XY")
        .workplane(offset=t/2)
        .pushPoints(cq_points)
        .circle(diam / 2.0)
        .extrude(-t - 2)
    )
    return solid.cut(cutters)

# 依次执行各组真实实体孔切削
#board = drill_holes(board, holes_6, 6.0)
board = drill_holes(board, holes_4, 4.0)
board = drill_holes(board, holes_5, 5.0)  # 切削你的 holes_5


# ================== 5. 执行正六角孔切削（真正保留的特征） ==================
# 对边距离 10mm 换算为外接圆直径 20 / sqrt(3)
hex_dia = 11 * 2 / math.sqrt(3)
cq_hex_centers = [
    [-13.5+1-4-0.1,  9],  # 对应 KiCad 的 [35, 37.9]
    [ 14+1.5-3+1.5,  9.4],  # 对应 KiCad 的 [65, 37.9]
    [-15.0, -25+1.1],  # 对应 KiCad 的 [35, 72.4]
    [ 15.0, -25]   # 对应 KiCad 的 [65, 72.4]
]

for cq_hx, cq_hy in cq_hex_centers:
    hex_cutter = (
        cq.Workplane("XY")
        .workplane(offset=t/2)
        .center(cq_hx, cq_hy)
        .polygon(6, hex_dia)
        .extrude(-t - 2)
    )
    board = board.cut(hex_cutter)

# ================== 6. 长方形内部裁剪 ==================
crop_cq_x = 50.0 - board_w / 2.0                  
crop_cq_y = board_h / 2.0 - (board_h - 40.0)      

crop_box = (
    cq.Workplane("XY")
    .center(crop_cq_x, crop_cq_y)
    .box(60, 80.0, t + 2)
)
board = board.intersect(crop_box)

# ================== 6.5 【实心盲槽方案】上表面下切 0.1mm 且彻底抹平数字孤岛 ==================
# 1. 先在原点生成高度为 1.0 的标准文本（此时字体的顶面精确位于 Z = 1.0）
smark=U.get_time_str_mark(sep=' ')
raw_text = cq.Workplane("XY").text(
    smark, fontsize=8, distance=0.9, font="Arial", halign="center", valign="center"
)

# 2. 核心几何大招：提取文本顶面，并只保留外围轮廓（outerWire），从而彻底将“0”内部的孔洞填平为纯实心面
filled_faces = [cq.Face.makeFromWires(f.outerWire()) for f in raw_text.faces(">Z").vals()]

# 3. 精准对齐 Z 轴并构造实心刀具：
# 目标：在上表面（Z=0.2）向下切 0.1mm，即切除 Z=0.1 到 Z=0.2 之间的材质。
# 计算：当前面在 Z=1.0，平移量 Z = 目标起点(0.1) - 当前高度(1.0) = -0.9
text_cutter = (
    cq.Workplane("XY")
    .add(cq.Compound.makeCompound(filled_faces))
    .translate((crop_cq_x, -5, -0.9))  # 精准定位 X、Y，并将面降落到 Z=0.1
    .extrude(0.5)                     # 向上拉伸 0.5mm，完美覆盖并切除 Z=0.1 至 Z=0.2 的空间
)

# 4. 执行切削（由于刀具本身是实心的，刻出来的“0”字内部将是一个完美的平底凹坑）
board = board.cut(text_cutter)


# 核心过滤：如果切出了多个独立实体，只保留体积最大的那块（即主板本身）
# 字符 “0” 内部被切断分离开的悬空孤岛会被自动识别并无情丢弃
if len(board.solids().vals()) > 1:
    board = cq.Workplane(obj=max(board.solids().vals(), key=lambda s: s.Volume()))
    

# ================== 7. 构造纯预览的辅助丝印标记（不影响 STEP 导出） ==================
# 7.1 生成绿色 20x20 丝印边框
preview_squares = (
    cq.Workplane("XY")
    .workplane(offset=t/2 + 0.05)
    .pushPoints(marker_squares)
    .rect(20, 20)
    .rect(19.6, 19.6)  # 内圈，留出 0.4mm 宽的线
    .extrude(0.01)
)

# 7.2 生成红色 1mm 辅助过孔点贴纸
preview_dots = (
    cq.Workplane("XY")
    .workplane(offset=t/2 + 0.06)
    .pushPoints(marker_dots)
    .circle(0.5)       # 半径 0.5 对应直径 1mm
    .extrude(0.01)
)


# ================== 8. 导出与分流预览 ==================
nums_flat = []
for sub in cq_hex_centers:
    nums_flat.extend(sub)
unique_nums = []
for n in nums_flat:
    if str(n) not in unique_nums:
        unique_nums.append(str(n))

snum = ",".join(unique_nums)
step_file = f''+__file__ + f"{smark}.step"
cq.exporters.export(board, step_file)

if "show_object" in globals():
    show_object(board, name="Board_Body") 
    show_object(preview_squares, name="Silk_Squares", options={"rgba": (0.0, 1.0, 0.0, 0.6)})
    show_object(preview_dots, name="Helper_Dots", options={"rgba": (1.0, 0.0, 0.0, 0.7)})
    
import bambu_slicer
f = bambu_slicer.to_gcode(
    cq_object=board, 
    name=step_file, 
    output_dir=r"D:\test\bambu-studio"
)