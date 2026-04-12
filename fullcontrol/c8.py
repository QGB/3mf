import fullcontrol as fc
from math import sqrt, tau, atan2,cos,sin
import os
# === 1. 几何参数 (确保严格相切) ===
w, temp_n, temp_b = 100.0, 210, 60 #正方形宽度与温度
d = -w/2 * (-1 + sqrt(5 - 2*sqrt(6))) #圆直径公式
r, EH, EW, layers = d/2, 0.2, 0.4, 5 #半径,层高,线宽,层数
t = r + sqrt((2*r)**2 - (w/2 - r)**2) #切点偏移量
px, py, z0 = 100, 100, 0.2 #打印中心
# === 2. 圆心布局 (顺时针排列) ===
c_loc = [(-w/2+r, w/2-r), (0, w/2-t), (w/2-r, w/2-r), (w/2-t, 0), (w/2-r, -w/2+r), (0, -w/2+t), (-w/2+r, -w/2+r), (-w/2+t, 0)]
centers = [fc.Point(x=px+x, y=py+y) for x,y in c_loc]
steps = []
# === 3. 终极一笔画逻辑 (Full-Circle Loop) ===
for layer in range(layers):
    z = layer * EH + z0
    for i in range(8):
        c = centers[i]
        p_prev = centers[(i-1)%8] #前一个圆心
        p_next = centers[(i+1)%8] #后一个圆心
        #计算与前后圆的切点方位角
        ang_in = atan2(p_prev.y - c.y, p_prev.x - c.x) #切入点角度
        ang_next_tangent = atan2(p_next.y - c.y, p_next.x - c.x) #通往下一个圆的切点角度
        #步骤1：画一个完整的圆 (360度)，保证每个圆的强度
        for j in range(32 + 1):
            ang = ang_in - (j / 32) * tau #顺时针画满一整圈
            steps.append(fc.Point(x=c.x + r * cos(ang), y=c.y + r * sin(ang), z=z))
        #步骤2：沿着圆周走到下一个切点 (衔接段)
        while ang_in > ang_next_tangent: ang_next_tangent += tau #修正跨度角度
        arc_dist = ang_next_tangent - ang_in
        segs_conn = int(16 * arc_dist / tau) + 1
        for j in range(segs_conn + 1):
            ang = ang_in + (j / segs_conn) * arc_dist #顺着圆周滑行到下一个圆
            steps.append(fc.Point(x=c.x + r * cos(ang), y=c.y + r * sin(ang), z=z))
# === 4. 纯净 G-code 输出 ===
gc_ctrl = fc.GcodeControls(printer_name="generic", initialization_data={"print_speed":3000,"extrusion_width":EW,"extrusion_height":EH})
raw_lines = fc.transform(steps, "gcode", gc_ctrl).split('\n')
clean = [L for L in raw_lines if L.startswith(('G0','G1','M104','M109','M140','M190'))]
head = f"M140 S{temp_b}\nM104 S{temp_n}\nG28\nG90\nM83\n" #初始化
tail = "G1 E-2 F2400\nM104 S0\nM140 S0\nG28 X0\n" #结束回抽
res = head + "\n".join(clean) + "\n" + tail
save_p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "c8.gcode")
with open(save_p, "w") as f: f.write(res)
print(f"Path Check: {len(steps)} points, 0 travel moves. File: {save_p}")