import sys;'qgb.U' in sys.modules or sys.path.append('C:/QGB/Anaconda3/Lib/site-packages/Pythonwin/');from qgb import *
import math, os, cadquery as cq, bambu_slicer

# ==========================================
# 1. 基础参数与加工特征数据
# ==========================================
t = 0.3  # 厚度

# 底面外轮廓坐标 (4个顶点，宽度死守 60mm：X 从 -30 到 30)
out_shape = [(30.0, 33.8), (30.0, -50.2), (-30.0, -50.2), (-30.0, 33.8)]

# 4 个【实际加工】的六边形螺母孔绝对坐标
hex_centers = [
    (-14.3+0.3, 9),   # 六边形 0 
    (14.6-0.6, 9.0),     # 六边形 1
    (-15.0, -25.0),  # 六边形 2
    (15.0, -25),     # 六边形 3  
]

# 螺母对边距离 11mm 精准换算外接圆直径
hex_flat_to_flat = 11.0  
hex_diameter = hex_flat_to_flat / math.cos(math.radians(30))

# 底部盲孔参数
blind_hole_dia = 30.5
blind_hole_depth = 1.5

# ==========================================
# 2. 纯理论预览标记坐标换算 (完全复现老代码逻辑)
# ==========================================
silk_centers = [
    (-15.0, 12.3),   # 对应 KiCad [35, 37.9]
    (15.0, 12.3),    # 对应 KiCad [65, 37.9]
    (-15.0, -22.2),  # 对应 KiCad [35, 72.4]
    (15.0, -22.2)    # 对应 KiCad [65, 72.4]
]

marker_dots = []
for cq_x, cq_y in silk_centers:
    marker_dots.append((cq_x - 10.0, cq_y - 10.0))
    marker_dots.append((cq_x + 10.0, cq_y - 10.0))
    marker_dots.append((cq_x - 10.0, cq_y + 10.0))
    marker_dots.append((cq_x + 10.0, cq_y + 10.0))

# ==========================================
# 3. 实体建模主流程
# ==========================================
# 3.1 生成基础主板
board = (
    cq.Workplane("XY")
    .workplane(offset=-t/2.0)
    .polyline(out_shape)
    .close()
    .extrude(t)
)

# 3.2 逐个切削六角形通孔
for n,(cq_hx, cq_hy) in enumerate(hex_centers):
    hex_cutter = (
        cq.Workplane("XY")
        .workplane(offset=t/2.0 + 1.0)      
        .center(cq_hx, cq_hy)
        .polygon(6, hex_diameter)
        .extrude(-t - 2.0)                
    )
    board = board.cut(hex_cutter)
    board, _smark = bambu_slicer.add_time_mark(board,smark=f'{n}',x=cq_hx-5,y=cq_hy+10,plane='bottom')

# 3.3 参考其它代码做法：逐个独立切削大圆形盲孔，外凸拉伸，防止底面碎裂
    if t>blind_hole_depth:
        blind_cutter = (
            cq.Workplane("XY")
            .workplane(offset=-t/2.0 - 1.0)     # 从板底面往下多延展 1mm 处作为起点
            .center(cq_hx, cq_hy)
            .circle(blind_hole_dia / 2.0)
            .extrude(blind_hole_depth + 1.0)   # 向上拉伸，刚好完美切过 1.5mm 盲孔深度
        )
        board = board.cut(blind_cutter)


# ==========================================
# 4. 辅助预览图层 (严格解耦，死死对齐 KiCad 原始网格)
# ==========================================
# 4.1 绿色 20x20 丝印边框
preview_squares = (
    cq.Workplane("XY")
    .workplane(offset=t/2.0 + 0.01)
    .pushPoints(silk_centers)
    .rect(20.0, 20.0)
    .rect(19.6, 19.6)  
    .extrude(0.01)
)

# 4.2 红色 1mm 辅助过孔点贴纸
preview_dots = (
    cq.Workplane("XY")
    .workplane(offset=t/2.0 + 0.02)
    .pushPoints(marker_dots)
    .circle(0.5)  
    .extrude(0.01)
)



board, x_scale, y_scale = bambu_slicer.flip_model(board, angle=180, axis='y')
# 执行跨模块标注，并同步解包更新本地的 board 与唯一的 smark
board, smark = bambu_slicer.add_time_mark(board)

if t>2:board = bambu_slicer.add_brim(board,12,0.4)#防止翘边，不要去除注释

# ==========================================
# 5. 导出与切片逻辑
# ==========================================
step_file = f'' + __file__ + f"{smark}.step"
cq.exporters.export(board, step_file)

if "show_object" in globals():
    show_object(board, name="Board_Body") 
    show_object(preview_squares, name="Silk_Squares", options={"rgba": (0.0, 1.0, 0.0, 0.6)})
    show_object(preview_dots, name="Helper_Dots", options={"rgba": (1.0, 0.0, 0.0, 0.7)})

f = bambu_slicer.to_gcode(
    cq_object=board, 
    name=step_file, 
    output_dir=r"D:\test\bambu-studio"
)