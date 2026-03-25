import fullcontrol as fc
from math import tau
import lab.fullcontrol as fclab

# 全局参数
design_name = "M16_BOLT"
nozzle_temp = 210
bed_temp = 60
print_speed = 4000
fan_percent = 100
printer_name = "generic"
print_x = 100
print_y = 100
z_offset = 0.2

# 你给的螺栓参数
part_type = "wing_bolt"
dia_major, dia_minor, pitch = 16, 14.3,2
bolt_or_tube_thread_length = 60
wing_height = 0.75 * dia_major
clearance = 0.1
EH = 0.15
EW = 0.6

# 裙边参数
brim_layers = 1
brim_lines =4
brim_gap =2
brim_speed =3000

# 生成模型
thread_type = "male"
wing_layers = int(wing_height / EH)
thread_layers = int(bolt_or_tube_thread_length / EH)
layers = wing_layers + thread_layers
offset = EW/2 + clearance
rad_min = (dia_minor/2)-offset
rad_max = (dia_major/2)-offset
segs = 64
a_shift = ((EH/segs)/pitch)*tau
steps = []

# 翼形适配裙边(无干涉)
z_brim = z_offset
wing_max_y = print_y + dia_major*2.25 + brim_gap
wing_min_y = print_y - dia_major*2.25 - brim_gap
wing_max_x = print_x + rad_max + brim_gap
wing_min_x = print_x - rad_max - brim_gap
for line in range(brim_lines):
    ox, oy = line*EW, line*EW
    for j in range(32):
        x = wing_min_x+ox + (wing_max_x-wing_min_x-2*ox)*(j/32)
        steps.append(fc.Point(x=x, y=wing_max_y-oy, z=z_brim))
    for j in range(32):
        x = wing_max_x-ox - (wing_max_x-wing_min_x-2*ox)*(j/32)
        steps.append(fc.Point(x=x, y=wing_min_y+oy, z=z_brim))

# 主体
for i in range(layers):
    for j in range(segs):
        z_now = i*EH + z_offset
        a_max = (i*segs+j)*a_shift % tau
        a_now = (j/segs)*tau
        r_frac = 1 - min(abs(a_now-a_max), abs(a_now-a_max+tau), abs(a_max-a_now+tau))/(tau/2)
        r_now = rad_min + r_frac*(rad_max-rad_min)
        steps.append(fc.polar_to_point(fc.Point(x=print_x, y=print_y, z=z_now), r_now, a_now))
    # 内部填充(螺杆不空心)
    fill_offset = EW*0.85
    for j in range(segs):
        z_now = i*EH + z_offset
        a_max = (i*segs+j)*a_shift % tau
        a_now = (j/segs)*tau
        r_frac = 1 - min(abs(a_now-a_max), abs(a_now-a_max+tau), abs(a_max-a_now+tau))/(tau/2)
        r_now = rad_min + r_frac*(rad_max-rad_min) - fill_offset
        steps.append(fc.polar_to_point(fc.Point(x=print_x, y=print_y, z=z_now), r_now, a_now))
    # 翼型把手
    if i < wing_layers:
        centre = fc.Point(x=print_x, y=print_y, z=i*EH+z_offset)
        bez1 = fc.rectangleXY(fc.polar_to_point(centre, rad_max+EW/4,0), -(rad_max+EW/4)*2, dia_major*0.4, cw=True)[0:4]
        bez1.insert(2, fc.Point(x=print_x, y=print_y+dia_major*2.25, z=i*EH+z_offset))
        steps.extend(fclab.bezierXYdiscrete(bez1, 32))
        bez2 = fc.move_polar(bez1, centre, 0, tau/2)
        steps.extend(fclab.bezierXYdiscrete(bez2, 32))

# 精简启动代码
custom_start = f"""; M16翼型螺栓
M140 S60 ; 热床
M104 S210 ; 喷头
G28 ; 归零
G90 ; 绝对坐标
G21 ; mm单位
M83 ; 相对挤出
G0 F8000 X5 Y5 Z10 ; 等待位
M190 S60 ; 等热床
M109 S210 ; 等喷头
G1 F300 E2.5 ; 排气
G0 F8000 X10 Y12 Z0.2 ; 引丝位
G1 F{brim_speed} X110 E1.2 ; 引丝
G1 X10 E1.2 ; 回退
G1 X{print_x} Y{print_y-100} E0.8 ; 移动到打印起点
G1 F{print_speed} ; 切换打印速度
""".format(brim_speed=brim_speed, print_x=print_x, print_y=print_y)

# 生成并清理FC开头
gcode_controls = fc.GcodeControls(
    printer_name=printer_name,
    include_date=False,
    initialization_data={
        "print_speed": print_speed,
        "nozzle_temp": nozzle_temp,
        "bed_temp": bed_temp,
        "fan_percent": fan_percent,
        "extrusion_width": EW,
        "extrusion_height": EH
    }
)
gcode_base = fc.transform(steps, "gcode", gcode_controls)
gcode_clean = gcode_base.split(";\n")[-1]

# 结束代码
end_code = """
G1 E-3.0 F2400 ; 回抽防瘤
G1 Z15 F3000 ; 抬Z
G1 X0 Y220 F6000 ; 快速移开
M106 S0 ; 关风扇
M104 S0 ; 关喷头
M140 S0 ; 关热床
M84 ; 关电机
; 打印完成
"""

# 保存
gcode_final = custom_start + "\n" + gcode_clean + end_code
filename = f"{design_name}_FINAL.gcode"
with open(filename, "w") as f:
    f.write(gcode_final)
print(f"✅ 生成完成: {filename}")