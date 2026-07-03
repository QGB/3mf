import sys;'qgb.U' in sys.modules or sys.path.append('C:/QGB/Anaconda3/Lib/site-packages/Pythonwin/');from qgb import *
import os
import sys
import json
import math
import cadquery as cq

# ================== 1. 基础参数 ==================
board_w = 100.0  
board_h = 100.4  
t = 5.5          

# ================== 2. 创建主板实体 ==================
board = cq.Workplane("XY").box(board_w, board_h, t)

# 孔位收集器
holes_6 = []
holes_4 = []
holes_5 = []     

# 绝对唯一基准坐标
hex_centers = [
    [35, 37.9], [65, 37.9],
    [35, 72.4], [65, 72.4]]

marker_squares = []  
marker_dots = []     

# 动态换算完美的对称孔心
cq_hex_centers = []
for x, y in hex_centers:
    cq_x = x - board_w / 2.0
    cq_y = board_h / 2.0 - y
    cq_hex_centers.append((cq_x, cq_y)) 
    
    marker_squares.append((cq_x, cq_y))
    marker_dots.append((cq_x - 10, cq_y - 10))
    marker_dots.append((cq_x + 10, cq_y - 10)) 
    marker_dots.append((cq_x - 10, cq_y + 10)) 
    marker_dots.append((cq_x + 10, cq_y + 10)) 

for x, y in [[35, 37.9], [65, 37.9]]:
    holes_6.append((x, y + 1))

y_two_hole = board_h - 40
holes_4.append((50 - 80 / 2, y_two_hole))
holes_4.append((50 + 80 / 2, y_two_hole))


# ================== 3. 先执行长方形裁剪 ==================
crop_cq_x = 50.0 - board_w / 2.0                  
crop_cq_y = board_h / 2.0 - (board_h - 40.0)      

crop_box = (
    cq.Workplane("XY")
    .center(crop_cq_x, crop_cq_y)
    .box(60.0, 80.0, t + 2)  
)
board = board.intersect(crop_box)


# ================== 4. 后执行常规圆形通孔切削 ==================
def drill_holes(solid, pts, diam):
    if not pts: return solid
    unique_pts = list(dict.fromkeys(pts))
    cq_points = [(px - board_w / 2.0, board_h / 2.0 - py) for px, py in unique_pts]
    
    for cx, cy in cq_points:
        cutter = (
            cq.Workplane("XY")
            .workplane(offset=t/2 + 1.0)  
            .center(cx, cy)
            .circle(diam / 2.0)
            .extrude(-t - 2.0)            
        )
        solid = solid.cut(cutter)
    return solid

board = drill_holes(board, holes_4, 4.0)
board = drill_holes(board, holes_5, 5.0)


# ================== 5. 后执行正六角孔切削 ==================
hex_dia = 11 * 2 / math.sqrt(3)
cq_hex_centers = [
    [-13.5+1-4-0.1+1.5,  9-0.4],  
    [ 14+1.5-3+1.5,  9.4-0.2],  
    [-15.0, -25+1.1],  
    [ 15.0, -25]   
]
for cq_hx, cq_hy in cq_hex_centers:
    hex_cutter = (
        cq.Workplane("XY")
        .workplane(offset=t/2 + 1.0)      
        .center(cq_hx, cq_hy)
        .polygon(6, hex_dia)
        .extrude(-t - 2.0)                
    )
    board = board.cut(hex_cutter)

# ================== 6. 后执行大盲孔切削 ==================
    if t>4:
        blind_cutter = (
            cq.Workplane("XY")
            .workplane(offset=-t/2 - 1.0)     
            .center(cq_hx, cq_hy)
            .circle(30.5 / 2.0)
            .extrude(2.0)                     
        )
        board = board.cut(blind_cutter)


# ================== 7. 执行模型整体翻转 ==================
def flip_model(solid, angle, axis='y'):
    axis = axis.lower()
    x_scale, y_scale = 1, 1
    if axis == 'x':
        vec = (1, 0, 0)
        if angle % 360 == 180: y_scale = -1
    elif axis == 'y':
        vec = (0, 1, 0)
        if angle % 360 == 180: x_scale = -1
    else:
        vec = (0, 0, 1)
        if angle % 360 == 180: x_scale, y_scale = -1, -1
            
    rotated_solid = solid.rotate((0, 0, 0), vec, angle)
    return rotated_solid, x_scale, y_scale

board, x_scale, y_scale = flip_model(board, angle=180, axis='y')


# ================== 8. 在翻转后的新表面精准刻字 (核心修复部分) ==================
smark = U.get_time_str_mark(sep=' ')

# 直接使用 CadQuery 原生方法：distance=-0.5 表示从表面直接向内切出 0.5mm 深的凹陷文字
text_cutter = (
    cq.Workplane("XY")
    .workplane(offset=t/2.0)                               
    .center(crop_cq_x * x_scale, -5 * y_scale)             
    .text(smark, fontsize=8, distance=-0.5, font="Arial", halign="center", valign="center", combine=False)
)
board = board.cut(text_cutter)

if len(board.solids().vals()) > 1:
    board = cq.Workplane(obj=max(board.solids().vals(), key=lambda s: s.Volume()))
    

# ================== 9. 纯预览辅助丝印标记 ==================
flipped_squares = [(cx * x_scale, cy * y_scale) for cx, cy in marker_squares]
flipped_dots = [(cx * x_scale, cy * y_scale) for cx, cy in marker_dots]

preview_squares = (
    cq.Workplane("XY")
    .workplane(offset=t/2 + 0.05)
    .pushPoints(flipped_squares)  
    .rect(20, 20)
    .rect(19.6, 19.6)  
    .extrude(0.01)
)

preview_dots = (
    cq.Workplane("XY")
    .workplane(offset=t/2 + 0.06)
    .pushPoints(flipped_dots)     
    .circle(0.5)       
    .extrude(0.01)
)

# ================== 10. 导出与切片预览 ==================
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