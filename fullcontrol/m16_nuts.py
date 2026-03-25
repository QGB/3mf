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

# M16 NUT PARAMETERS
part_type = "wing_nut"
dia_major, dia_minor, pitch = 16.0, 14.3, 2.0
wing_height = 8
clearance = 0.35
EH = 0.15
EW = 0.6

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

for i in range(layers):
    for j in range(segs):
        z_now = (i + (j / segs)) * EH
        a_max = (i * segs + j) * a_shift % tau
        a_now = (j / segs) * tau
        r_fraction_of_max = 1 - min(abs(a_now - a_max), abs(a_now - (a_max - tau)), abs(a_max - (a_now - tau))) / (tau / 2)
        r_now = rad_min + r_fraction_of_max * (rad_max - rad_min)
        steps.append(fc.polar_to_point(fc.Point(x=0, y=0, z=z_now), r_now, a_now))
    fill_offset = EW * 0.85
    for j in range(segs):
        z_now = (i + (j / segs)) * EH
        a_max = (i * segs + j) * a_shift % tau
        a_now = (j / segs) * tau
        r_fraction_of_max = 1 - min(abs(a_now - a_max), abs(a_now - (a_max - tau)), abs(a_max - (a_now - tau))) / (tau / 2)
        r_now = (rad_min + r_fraction_of_max * (rad_max - rad_min)) + fill_offset
        steps.append(fc.polar_to_point(fc.Point(x=0, y=0, z=z_now), r_now, a_now))
    centre_now = fc.Point(x=0, y=0, z=z_now)
    bezier_control_pts_1 = fc.rectangleXY(fc.polar_to_point(centre_now, rad_max + EW / 4, 0), -(rad_max + EW / 4) * 2, dia_major * 0.4, cw=True)[0:4]
    bezier_control_pts_1.insert(2, fc.Point(x=0, y=dia_major * 2.25, z=z_now))
    steps.extend(fclab.bezierXYdiscrete(bezier_control_pts_1, 32))
    bezier_control_pts_2 = fc.move_polar(bezier_control_pts_1, centre_now, 0, tau / 2)
    steps.extend(fclab.bezierXYdiscrete(bezier_control_pts_2, 32))

model_offset = fc.Vector(x=50, y=50, z=0.2)
steps = fc.move(steps, model_offset)

# ======================
# CUSTOM START CODE (PERFECT FORMAT)
# ======================
custom_start = """; Time to print!!!!!
; GCode created with FullControl
M140 S60 ; set bed temp
M104 S210 ; set hotend temp
G28 ; home all axes
G90 ; absolute coordinates
G21 ; units mm
M83 ; relative extrusion
M106 S255 ; fan 100%
M220 S100 ; speed factor
M221 S100 ; flow factor
G0 F8000 X5 Y5 Z10
M190 S60 ; wait bed
M109 S210 ; wait hotend
G1 F250 E20.7876
G0 F250 Z50
G0 F8000 X10 Y10 Z0.3
;----- END OF STARTING PROCEDURE -----
;----- START OF PRIMER PROCEDURE -----
G0 F8000 Y12 Z0.2
G1 F4000 X110 E3.741765
G1 Y14 E0.074835
G1 X10 E3.741765
G1 Y16 E0.074835
G1 X53.6 E1.63141
G1 Y50 E1.2722
;----- END OF PRIMER PROCEDURE -----
G1 F4000"""

# ======================
# GENERATE GCODE
# ======================
gcode_controls = fc.GcodeControls(
    printer_name=printer_name,
    save_as=design_name,
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

# ======================
# 🔥 完美结束代码（回抽 + 抬升 + 归位 + 无瘤子）
# ======================
end_code = """
G1 E-3.0 F2400 ; 回抽3mm，消除瘤子
G1 Z15 F3000 ; 抬Z 15mm 远离模型
G1 X0 Y220 F6000 ; 移到前面，不挡模型
M106 S0 ; 关闭风扇
M104 S0 ; 关闭喷头
M140 S0 ; 关闭热床
M84 ; 关闭电机
; PRINT COMPLETE
"""

gcode_final = custom_start + "\n" + gcode_base.split(";\n")[-1] + end_code

# ======================
# SAVE LOCAL FILE (NO UPLOAD!)
# ======================
with open("M16_NUT_FILLED.gcode", "w") as f:
    f.write(gcode_final)

print("✅ SUCCESS: G-code saved to your notebook folder!")
print("📁 File name: M16_NUT_FILLED.gcode")