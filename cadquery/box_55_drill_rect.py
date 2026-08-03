import math,cadquery as cq

# ==========================================
# 1. 参数定义与初始化
# ==========================================
inner_length = 136  # 内腔长 (mm)
inner_width  = 56   # 内腔宽 (mm)
frame_height = 16   # 框架高度 H (mm)

# 📐 角度参数 (斜边与水平面的夹角)
bevel_angle  = 60   # 支持任意角度，例如 45, 60, 30 等

# 根据高度和斜边角度，自动计算顶面壁厚 W (单位: mm)
# 注：若希望固定壁厚而根据角度计算高度，可修改为: frame_height = wall_thickness * math.tan(math.radians(bevel_angle))
wall_thickness = frame_height / math.tan(math.radians(bevel_angle))

# 钻孔参数
drill_diameter   = 3     # 钻孔直径
drill_interval_x = 20    # 长边 (X方向) 钻孔间距
drill_interval_y = 15    # 短边 (Y方向) 钻孔间距
margin_x         = 10    # 长边端头留边距离
margin_y         = 15    # 短边端头留边距离

print("\n" + "="*40)
print("🚀 开始构建直角三角截面中空框架 (动态角度版)")
print("="*40)
print(f"📏 [内腔尺寸] {inner_length} x {inner_width} mm")
print(f"📐 [斜边角度] {bevel_angle}° (与水平面夹角)")
print(f"📏 [框架高度] {frame_height} mm")
print(f"📏 [自动计算壁厚] {wall_thickness:.2f} mm")
print(f"📏 [顶面外廓] {inner_length + 2*wall_thickness:.2f} x {inner_width + 2*wall_thickness:.2f} mm")
print(f"🔩 [钻孔参数] 长边间距: {drill_interval_x}mm, 短边间距: {drill_interval_y}mm, 孔径: {drill_diameter}mm")

# ==========================================
# 2. 构建主体外形 (实心梯台)
# ==========================================
print("\n[步骤 1] 构建外部梯台 (Loft)...")
outer_solid = (
    cq.Workplane("XY")
    .rect(inner_length, inner_width)  # 底面 Z=0 (直角顶点处)
    .workplane(offset=frame_height)
    .rect(inner_length + 2*wall_thickness, inner_width + 2*wall_thickness) # 顶面 Z=H (向外放样)
    .loft(ruled=True)
)
vol_outer = outer_solid.val().Volume()
print(f"✅ 外部梯台生成完毕。体积: {vol_outer:.2f} mm³")

# ==========================================
# 3. 构建内腔挖空体 (实心长方体)
# ==========================================
print("\n[步骤 2] 构建内腔切割工具...")
inner_solid = (
    cq.Workplane("XY", origin=(0, 0, -1))
    .rect(inner_length, inner_width)
    .extrude(frame_height + 2) # 从 Z=-1 切到 Z=H+1，彻底切透
)
vol_inner = inner_solid.val().Volume()
print(f"✅ 内部切割体生成完毕。体积: {vol_inner:.2f} mm³")

# ==========================================
# 4. 布尔运算相减 (掏空)
# ==========================================
print("\n[步骤 3] 执行布尔相减 (掏空)...")
frame = outer_solid.cut(inner_solid)
vol_frame = frame.val().Volume()
print(f"✅ 挖空完成！当前框架体积: {vol_frame:.2f} mm³")

# ==========================================
# 5. 分别计算长短边孔位并钻孔
# ==========================================
print("\n[步骤 4] 计算孔位并钻孔...")

# 顶面中线位置 (自动随壁厚更新)
mid_len = inner_length + wall_thickness  
mid_wid = inner_width  + wall_thickness  

# 1) 计算长边孔位 (X方向)
x_coords = []
if mid_len > 2 * margin_x:
    n_x = max(1, round((mid_len - 2 * margin_x) / drill_interval_x))
    x_coords = [-mid_len/2 + margin_x + i * (mid_len - 2 * margin_x) / n_x for i in range(n_x + 1)]
else:
    x_coords = [0]

# 2) 计算短边孔位 (Y方向)
y_coords = []
if mid_wid > 2 * margin_y:
    n_y = max(1, round((mid_wid - 2 * margin_y) / drill_interval_y))
    y_coords = [-mid_wid/2 + margin_y + i * (mid_wid - 2 * margin_y) / n_y for i in range(n_y + 1)]
else:
    y_coords = [0]

# 组装坐标
pts = []
for x in x_coords:
    pts.append((round(x, 4), round( mid_wid/2, 4)))
    pts.append((round(x, 4), round(-mid_wid/2, 4)))
for y in y_coords:
    pts.append((round( mid_len/2, 4), round(y, 4)))
    pts.append((round(-mid_len/2, 4), round(y, 4)))

pts = list(dict.fromkeys(pts))  # 去重

print(f"✅ 共计算出 {len(pts)} 个钻孔点。前3个坐标示例: {pts[:3]}")

if pts:
    final_solid = (
        frame.faces(">Z")
        .workplane()
        .pushPoints(pts)
        .circle(drill_diameter / 2)
        .cutBlind(-frame_height - 2)
    )
    print(f"✅ 打孔完成！最终模型体积: {final_solid.val().Volume():.2f} mm³")
else:
    final_solid = frame
    print("⚠️ 无孔位，跳过打孔步骤。")

# ==========================================
# 6. 导出与显示
# ==========================================
import os,bambu_slicer
step_file = os.path.splitext(__file__)[0] + f"_open_box_{bevel_angle}.step"
cq.exporters.export(final_solid, step_file)

if "show_object" in globals():
    show_object(final_solid, name=step_file[:-5])

f = bambu_slicer.to_gcode(
    cq_object=final_solid,
    name=step_file,
    output_dir=r"D:\test\bambu-studio"
)