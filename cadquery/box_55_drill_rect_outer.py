import math
import cadquery as cq
import os

# ==========================================
# 1. 参数定义
# ==========================================
inner_length = 139
inner_width  = 59
frame_height = 8
bevel_angle  = 60  # 斜边与水平面的夹角

# 3D打印配合间隙 (单边间隙，单位: mm)
clearance = 0#.5  

# 壁厚由高度和角度自动计算
wall_thickness = frame_height / math.tan(math.radians(bevel_angle))

# 钻孔参数
drill_diameter   = 3
drill_interval_x = 20
drill_interval_y = 15
margin_x         = 10
margin_y         = 15

print("=" * 40)
print("构建两个配合零件：斜边框架 + 外侧三角补件")
print(f"内腔尺寸：{inner_length} x {inner_width} mm")
print(f"框架高度：{frame_height} mm, 斜边角度：{bevel_angle}°")
print(f"自动壁厚：{wall_thickness:.2f} mm")
print(f"打印间隙：单边 {clearance} mm (双边总间隙 {2*clearance} mm)")
print("=" * 40)

# ==========================================
# 2. 构建框架外部实心梯台
# ==========================================
outer_solid = (
    cq.Workplane("XY")
    .rect(inner_length, inner_width)          # 底面 (Z=0)
    .workplane(offset=frame_height)
    .rect(inner_length + 2 * wall_thickness,
          inner_width  + 2 * wall_thickness)  # 顶面 (Z=H)
    .loft(ruled=True)
)

# ==========================================
# 3. 构建斜边框架壳体
# ==========================================
inner_cut = (
    cq.Workplane("XY", origin=(0, 0, -1))
    .rect(inner_length, inner_width)
    .extrude(frame_height + 2)
)

# 挖出内腔
frame_shell = outer_solid.cut(inner_cut)

# ==========================================
# 4. 构建外侧三角补件壳体 (带配合间隙)
# ==========================================
# 切割补件用的放大梯台
outer_solid_for_comp = (
    cq.Workplane("XY")
    .rect(inner_length + 2 * clearance, 
          inner_width  + 2 * clearance)
    .workplane(offset=frame_height)
    .rect(inner_length + 2 * wall_thickness + 2 * clearance,
          inner_width  + 2 * wall_thickness + 2 * clearance)
    .loft(ruled=True)
)

# 补件外包长方体
outer_box = (
    cq.Workplane("XY")
    .rect(inner_length + 2 * wall_thickness + 2 * clearance,
          inner_width  + 2 * wall_thickness + 2 * clearance)
    .extrude(frame_height)
)

# 补件壳体
complement_shell = outer_box.cut(outer_solid_for_comp)

# ==========================================
# 5. 计算孔位并统一打孔 (采用坐标平移切割，避免选择面报错)
# ==========================================
mid_len = inner_length + wall_thickness
mid_wid = inner_width  + wall_thickness

def hole_positions(length, width, margin_l, margin_w, interval_l, interval_w):
    pts = []
    if length > 2 * margin_l:
        n = max(1, round((length - 2 * margin_l) / interval_l))
        xs = [-length/2 + margin_l + i * (length - 2 * margin_l) / n for i in range(n + 1)]
        for x in xs:
            continue
            pts.append((x,  width/2))
            pts.append((x, -width/2))
    if width > 2 * margin_w:
        n = max(1, round((width - 2 * margin_w) / interval_w))
        ys = [-width/2 + margin_w + i * (width - 2 * margin_w) / n for i in range(n + 1)]
        for y in ys:
            pts.append(( length/2, y))
            #pts.append((-length/2, y))
    return list(dict.fromkeys(pts))

pts = hole_positions(mid_len, mid_wid, margin_x, margin_y,
                     drill_interval_x, drill_interval_y)

if pts:
    # 生成贯穿整个高度的独立钻孔切割柱体（从 Z=H+1 向下贯穿至 Z=-1）
    drill_cutters = (
        cq.Workplane("XY")
        .workplane(offset=frame_height + 1)
        .pushPoints(pts)
        .circle(drill_diameter / 2)
        .extrude(-frame_height - 2)
    )
    
    # 统一施加到两个零件上
    frame = frame_shell.cut(drill_cutters)
    complement = complement_shell.cut(drill_cutters)
else:
    frame = frame_shell
    complement = complement_shell

print("\n零件生成完毕：")
print(f"  框架体积：{frame.val().Volume():.2f} mm³")
print(f"  补件体积：{complement.val().Volume():.2f} mm³")

# ==========================================
# 6. 导出与显示
# ==========================================
base_name = os.path.splitext(__file__)[0] if '__file__' in dir() else "assembly"
step_frame = base_name + f"_frame_{bevel_angle}.step"
step_comp  = base_name + f"_complement_{bevel_angle}.step"

cq.exporters.export(frame, step_frame)
cq.exporters.export(complement, step_comp)

if "show_object" in dir():
    show_object(frame, name="斜边框架", options={"color": (100, 149, 237)})   # 玉米蓝
    show_object(complement, name="外侧补件", options={"color": (255, 165, 0)}) # 橙色