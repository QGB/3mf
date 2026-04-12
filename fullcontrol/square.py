import fullcontrol as fc
from math import tau
import lab.fullcontrol as fclab
import sys,os;'qgb.U' in sys.modules or sys.path.append('C:/QGB/Anaconda3/Lib/site-packages/Pythonwin/');from qgb import *

# 全局参数
nozzle_temp = 210
bed_temp = 60
print_speed = 4000
fan_percent = 100
printer_name = "generic"
print_x = 100  # 正方形中心X
print_y = 100  # 正方形中心Y
z_offset = 0.2

# 方形参数
square_size = 20  # 正方形边长 200mm
EW = 0.6  # 挤出宽度
EH = 0.15  # 层高
brim_gap = 2  # 裙边间隙

# 计算正方形边界
square_left = print_x - square_size/2
square_right = print_x + square_size/2
square_bottom = print_y - square_size/2
square_top = print_y + square_size/2

# 生成步骤列表
steps = []

# 2. 生成正方形外轮廓
z_main = z_offset
# 底部边
for i in range(101):
    x = square_left + square_size * (i/100)
    steps.append(fc.Point(x=x, y=square_bottom, z=z_main))

# 右侧边
for i in range(101):
    y = square_bottom + square_size * (i/100)
    steps.append(fc.Point(x=square_right, y=y, z=z_main))

# 顶部边
for i in range(101):
    x = square_right - square_size * (i/100)
    steps.append(fc.Point(x=x, y=square_top, z=z_main))

# 左侧边
for i in range(101):
    y = square_top - square_size * (i/100)
    steps.append(fc.Point(x=square_left, y=y, z=z_main))

# 3. 生成正方形内部密铺填充（100%填充）
fill_spacing = EW * 0.95  # 填充线间距（略小于线宽以获得100%填充）
fill_angle = 45  # 填充角度

# 方法1：对角线填充
for i in range(int(square_size * 1.5 / fill_spacing)):
    # 创建填充线
    offset = i * fill_spacing
    
    # 计算填充线的起点和终点
    if fill_angle == 45:
        # 45度对角线填充
        line_start_x = square_left - square_size
        line_start_y = square_bottom + offset
        line_end_x = square_right + square_size
        line_end_y = square_top - offset
        
        # 计算与正方形边界的交点
        intersections = []
        
        # 检查与左边界的交点
        if square_bottom <= line_start_y <= square_top:
            intersections.append((square_left, line_start_y))
        
        # 检查与底边界的交点
        if square_left <= line_start_x <= square_right:
            intersections.append((line_start_x, square_bottom))
        
        # 检查与右边界的交点
        if square_bottom <= line_end_y <= square_top:
            intersections.append((square_right, line_end_y))
        
        # 检查与顶边界的交点
        if square_left <= line_end_x <= square_right:
            intersections.append((line_end_x, square_top))
        
        # 如果找到两个交点，添加填充线
        if len(intersections) == 2:
            # 按X坐标排序以确保一致的打印方向
            intersections.sort(key=lambda p: p[0])
            start_point = fc.Point(x=intersections[0][0], y=intersections[0][1], z=z_main)
            end_point = fc.Point(x=intersections[1][0], y=intersections[1][1], z=z_main)
            
            # 添加填充线
            steps.append(start_point)
            steps.append(end_point)
    else:
        # 水平填充
        y = square_bottom + offset
        if square_bottom <= y <= square_top:
            start_point = fc.Point(x=square_left, y=y, z=z_main)
            end_point = fc.Point(x=square_right, y=y, z=z_main)
            steps.append(start_point)
            steps.append(end_point)
if 0:
    # 方法2：添加垂直填充以形成网格（可选）
    for i in range(int(square_size * 1.5 / fill_spacing)):
        offset = i * fill_spacing
        
        # 垂直填充线
        x = square_left + offset
        if square_left <= x <= square_right:
            start_point = fc.Point(x=x, y=square_bottom, z=z_main)
            end_point = fc.Point(x=x, y=square_top, z=z_main)
            steps.append(start_point)
            steps.append(end_point)

    # 方法3：添加另一角度的对角线填充（形成三角形网格）
    for i in range(int(square_size * 1.5 / fill_spacing)):
        offset = i * fill_spacing
        
        # 135度对角线填充
        line_start_x = square_right + square_size
        line_start_y = square_bottom + offset
        line_end_x = square_left - square_size
        line_end_y = square_top - offset
        
        # 计算与正方形边界的交点
        intersections = []
        
        # 检查与右边界的交点
        if square_bottom <= line_start_y <= square_top:
            intersections.append((square_right, line_start_y))
        
        # 检查与底边界的交点
        if square_left <= line_start_x <= square_right:
            intersections.append((line_start_x, square_bottom))
        
        # 检查与左边界的交点
        if square_bottom <= line_end_y <= square_top:
            intersections.append((square_left, line_end_y))
        
        # 检查与顶边界的交点
        if square_left <= line_end_x <= square_right:
            intersections.append((line_end_x, square_top))
        
        # 如果找到两个交点，添加填充线
        if len(intersections) == 2:
            # 按X坐标排序以确保一致的打印方向
            intersections.sort(key=lambda p: p[0])
            start_point = fc.Point(x=intersections[0][0], y=intersections[0][1], z=z_main)
            end_point = fc.Point(x=intersections[1][0], y=intersections[1][1], z=z_main)
            
            # 添加填充线
            steps.append(start_point)
            steps.append(end_point)

# 4. 生成顶部轮廓（可选，加固边缘）
z_top = z_main + EH  # 如果需要多层，可以增加
# 底部边（顶部轮廓）
for i in range(101):
    x = square_left + square_size * (i/100)
    steps.append(fc.Point(x=x, y=square_bottom, z=z_top))

# 右侧边（顶部轮廓）
for i in range(101):
    y = square_bottom + square_size * (i/100)
    steps.append(fc.Point(x=square_right, y=y, z=z_top))

# 顶部边（顶部轮廓）
for i in range(101):
    x = square_right - square_size * (i/100)
    steps.append(fc.Point(x=x, y=square_top, z=z_top))

# 左侧边（顶部轮廓）
for i in range(101):
    y = square_top - square_size * (i/100)
    steps.append(fc.Point(x=square_left, y=y, z=z_top))

# 5. 生成内部填充（交叉填充）
# 水平填充
for i in range(int(square_size / fill_spacing)):
    y = square_bottom + (i * fill_spacing) + fill_spacing/2
    if square_bottom <= y <= square_top:
        start_point = fc.Point(x=square_left, y=y, z=z_top)
        end_point = fc.Point(x=square_right, y=y, z=z_top)
        steps.append(start_point)
        steps.append(end_point)

# 垂直填充
for i in range(int(square_size / fill_spacing)):
    x = square_left + (i * fill_spacing) + fill_spacing/2
    if square_left <= x <= square_right:
        start_point = fc.Point(x=x, y=square_bottom, z=z_top)
        end_point = fc.Point(x=x, y=square_top, z=z_top)
        steps.append(start_point)
        steps.append(end_point)

# 6. 精简启动代码
custom_start = f"""
M140 S{bed_temp} ; 热床
M104 S{nozzle_temp} ; 喷头
G28 ; 归零
G90 ; 绝对坐标
G21 ; mm单位
M83 ; 相对挤出
G0 F8000 X5 Y5 Z10 ; 等待位
M190 S{bed_temp} ; 等热床
M109 S{nozzle_temp} ; 等喷头
G1 F300 E2.5 ; 排气
G0 F8000 X{print_x-square_size/2-10} Y{print_y-square_size/2-10} Z{z_offset} ; 引丝位
G1 F{print_speed/2} X{print_x-square_size/2} E1.2 ; 开始裙边
"""

# 7. 生成G-code
gcode_controls = fc.GcodeControls(
    printer_name=printer_name,
    initialization_data={
        "print_speed": print_speed,
        "nozzle_temp": nozzle_temp,
        "bed_temp": bed_temp,
        "fan_percent": fan_percent,
        "extrusion_width": EW,
        "extrusion_height": EH
    }
)

# 转换步骤为G-code
gcode_result = fc.transform(steps, "gcode", gcode_controls)

# 清理G-code（移除头部信息）
gcode_lines = gcode_result.split('\n')
gcode_body = []
in_gcode = False

for line in gcode_lines:
    if line.startswith(';') or 'start_print' in line.lower() or 'end_print' in line.lower():
        continue
    if line.strip() and not line.startswith(';'):
        gcode_body.append(line)

gcode_clean = '\n'.join(gcode_body)

# 8. 结束代码
end_code = f"""
G1 E-3.0 F2400 ; 回抽防瘤
G91 ; 切换相对坐标
G1 Z15 F2000 ; 抬Z
G1 X0 Y220 F4000 ; 快速移开
M106 S0 ; 关风扇
M104 S0 ; 关喷头
M140 S0 ; 关热床
M84 ; 关电机
; 打印完成 - 200x200mm 正方形
; 总尺寸: {square_size}x{square_size}mm
; 层高: {EH}mm
; 线宽: {EW}mm
; 填充密度: 100%
"""

# 9. 保存文件
gcode_final = custom_start + "\n" + gcode_clean + end_code
filename = "200x200_square_single_layer.gcode"

with open(filename, "w", encoding="utf-8") as f:
    f.write(gcode_final)

# 打印文件路径
file_path = os.path.realpath(filename)
U.cbs(file_path,p=1)
print(f"文件大小: {os.path.getsize(filename)} 字节")
print(f"\n打印参数:")
print(f"- 正方形尺寸: {square_size}x{square_size}mm")
print(f"- 中心位置: X={print_x}, Y={print_y}")
print(f"- 层高: {EH}mm")
print(f"- 线宽: {EW}mm")
print(f"- 喷嘴温度: {nozzle_temp}°C")
print(f"- 热床温度: {bed_temp}°C")
print(f"- 打印速度: {print_speed} mm/min")