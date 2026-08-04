import build123d_fix
import math
from build123d import *

# ============================================================
# 1. 参数定义（完全参数化）
# ============================================================
# 基础尺寸
outer_length = 147    # 外框长度 (mm)
outer_width  = 67     # 外框宽度 (mm)
inner_height = 10     # 内腔深度 (h)
box_height   = inner_height + 2  # 外框总高
inner_length = 130    # 内腔长度 (mm)
inner_width  = 54     # 内腔宽度 (mm)
fillet_radius = 3     # 侧面倒角半径 (mm)

# 钻孔参数
drill_diameter   = 3.5    # 钻孔直径 (mm)
drill_interval_x = 20   # 长边 (X方向) 孔间距
drill_interval_y = 15   # 短边 (Y方向) 孔间距
margin_x         = 10   # 长边端头留边
margin_y         = 15   # 短边端头留边

# 自动计算壁厚及中线位置（孔位布置基准线）
wall_thickness_x = (outer_length - inner_length) / 2
wall_thickness_y = (outer_width  - inner_width)  / 2
mid_len = inner_length + wall_thickness_x   # 长边孔位所在中线总长
mid_wid = inner_width  + wall_thickness_y   # 短边孔位所在中线总宽

print("\n" + "="*40)
print("🚀 构建矩形中空框架（build123d 纯正语法）")
print("="*40)
print(f"📏 [外框尺寸] {outer_length} x {outer_width} x {box_height} mm")
print(f"📏 [内腔尺寸] {inner_length} x {inner_width} x {inner_height} mm")
print(f"📏 [壁厚] X方向: {wall_thickness_x:.2f} mm, Y方向: {wall_thickness_y:.2f} mm")
print(f"🔩 [钻孔参数] 长边间距: {drill_interval_x}mm, 短边间距: {drill_interval_y}mm, 孔径: {drill_diameter}mm")

# ============================================================
# 2. 钻孔坐标计算
# ============================================================
# 2.1 长边（X方向）孔位坐标
if mid_len > 2 * margin_x:
    n_x = max(1, round((mid_len - 2 * margin_x) / drill_interval_x))
    x_coords = [-mid_len/2 + margin_x + i * (mid_len - 2 * margin_x) / n_x for i in range(n_x + 1)]
else:
    x_coords = [0]

# 2.2 短边（Y方向）孔位坐标
if mid_wid > 2 * margin_y:
    n_y = max(1, round((mid_wid - 2 * margin_y) / drill_interval_y))
    y_coords = [-mid_wid/2 + margin_y + i * (mid_wid - 2 * margin_y) / n_y for i in range(n_y + 1)]
else:
    y_coords = [0]

# 2.3 生成所有钻孔点
pts = []
for x in x_coords:
    pts.append((round(x, 4), round( mid_wid/2, 4)))
    pts.append((round(x, 4), round(-mid_wid/2, 4)))
for y in y_coords:
    pts.append((round( mid_len/2, 4), round(y, 4)))
    pts.append((round(-mid_len/2, 4), round(y, 4)))

# 坐标去重
pts = list(dict.fromkeys(pts))
print(f"✅ 共计算出 {len(pts)} 个钻孔坐标点。")

# ============================================================
# 3. 统一构建模型（单 BuildPart 上下文）
# ============================================================
with BuildPart() as box:
    # 3.1 外部实心长方体
    Box(outer_length, outer_width, box_height)
    
    # 3.2 挖空内腔：顶面向下挖出 inner_height 深度
    top_face = box.faces().sort_by(Axis.Z)[-1]
    with Locations(top_face):
        Box(
            inner_length, 
            inner_width, 
            inner_height,
            align=(Align.CENTER, Align.CENTER, Align.MAX),
            mode=Mode.SUBTRACT
        )
    
    # 3.3 侧边四条竖直棱倒角
    fillet(box.edges().filter_by(Axis.Z), radius=fillet_radius)

    # 3.4 批量打孔（定位到顶面，按 pts 坐标下钻穿透）
    if pts:
        top_face_updated = box.faces().sort_by(Axis.Z)[-1]
        with Locations(top_face_updated):
            with Locations(*pts):
                Hole(radius=drill_diameter / 2, depth=box_height + 5)
        print("✅ 批量打孔完成。")

print("✅ 模型构建完毕！")

# ============================================================
# 4. 渲染与输出（兼容 CQ-Editor 及 Build123d 视图）
# ============================================================
import os,bambu_slicer,cadquery as cq
step_file = os.path.splitext(__file__)[0] + f"_{outer_length}x{outer_width}.step"
cq_object=cq.Shape(box.part.wrapped)
if "show_object" in locals():
    # 将 build123d 的 Part 转换为 CQ 兼容的 Shape 进行渲染
    show_object(cq_object, name=step_file[:-5])

f = bambu_slicer.to_gcode(
    cq_object=cq_object,
    name=step_file,
    output_dir=r"D:\test\bambu-studio"
)