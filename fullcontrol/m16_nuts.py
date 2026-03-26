import fullcontrol as fc
from math import tau
import lab.fullcontrol as fclab

# ======================
# SETTINGS
# ======================
design_name = "M16_NUT"
nozzle_temp = 210
bed_temp = 60
print_speed = 4000
fan_percent = 100
printer_name = "generic"
# 零件打印位置
print_x = 100
print_y = 120
z_offset = 0.2
# M16 NUT PARAMETERS
part_type = "wing_nut"
dia_major, dia_minor, pitch = 16.0, 14.3, 2.0
wing_height = 16
clearance = 0.35
EH = 0.15
EW = 0.6
# BRIM SETTINGS (裙边参数)
brim_layers = 1
brim_lines =3
brim_gap = 3
brim_speed = 3000

# ======================
# CREATE DESIGN
# ======================
thread_type = "female"
wing_layers = int(wing_height / EH)
layers = wing_layers
offset = EW / 2 + clearance
rad_min = (dia_minor / 2) + offset
rad_max = (dia_major / 2) + offset
segs = 64
a_shift = ((EH / segs) / pitch) * tau
steps = []

# 🔥 翼形适配裙边(无干涉)
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

# 主体螺母
for i in range(layers):
    z_layer = i * EH + z_offset
    for j in range(segs):
        z_now = (i + j/segs) * EH + z_offset
        a_max = (i*segs + j) * a_shift % tau
        a_now = (j/segs)*tau
        r_fraction = 1 - min(abs(a_now-a_max), abs(a_now-(a_max-tau)), abs(a_max-(a_now-tau))) / (tau/2)
        r_now = rad_min + r_fraction * (rad_max - rad_min)
        steps.append(fc.polar_to_point(fc.Point(x=print_x, y=print_y, z=z_now), r_now, a_now))
    # 内部填充
    fill_offset = EW*0.85
    for j in range(segs):
        z_now = (i + j/segs) * EH + z_offset
        a_max = (i*segs + j) * a_shift % tau
        a_now = (j/segs)*tau
        r_fraction = 1 - min(abs(a_now-a_max), abs(a_now-(a_max-tau)), abs(a_max-(a_now-tau))) / (tau/2)
        r_now = rad_min + r_fraction * (rad_max - rad_min) + fill_offset
        steps.append(fc.polar_to_point(fc.Point(x=print_x, y=print_y, z=z_now), r_now, a_now))
    # 翅膀
    centre_now = fc.Point(x=print_x, y=print_y, z=z_layer)
    bezier_control_pts_1 = fc.rectangleXY(fc.polar_to_point(centre_now, rad_max+EW/4, 0), -(rad_max+EW/4)*2, dia_major*0.4, cw=True)[0:4]
    bezier_control_pts_1.insert(2, fc.Point(x=print_x, y=print_y + dia_major*2.25, z=z_layer))
    steps.extend(fclab.bezierXYdiscrete(bezier_control_pts_1, 32))
    bezier_control_pts_2 = fc.move_polar(bezier_control_pts_1, centre_now, 0, tau/2)
    steps.extend(fclab.bezierXYdiscrete(bezier_control_pts_2, 32))

# ======================
# CUSTOM START CODE
# ======================
custom_start = f"""M140 S60 ; 热床
M104 S210 ; 喷头
G28 ; 归零
G90 ; 绝对坐标
G21 ; mm单位
M83 ; 相对挤出
G0 F8000 X5 Y5 Z10 ; 移动等待位
M190 S60 ; 等热床
M109 S210 ; 等喷头
G1 F300 E2.5 ; 排气
G0 F8000 X10 Y12 Z0.2 ; 引丝位
G1 F{brim_speed} X110 E1.2 ; 引丝
G1 X10 E1.2 ; 回退
G1 X{print_x} Y{print_y-100} E0.8 ; 移动到打印起点
G1 F{print_speed} ; 切换打印速度
""".format(brim_speed=brim_speed, print_x=print_x,print_y=print_y)

# ======================
# GENERATE GCODE
# ======================
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

# ======================
# 结束代码
# ======================
end_code = """
G1 E-3.0 F2400 ; 回抽防瘤
G91 ; 切换相对坐标
G1 Z20 F1000 ; 抬Z
G1 X0 Y220 F2000 ; 快速移开
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