import cadquery as cq

# ==========================================
# 1. 参数定义
# ==========================================
inner_diameter = 60   # 内径 D_in (mm)
wall_thickness = 6    # 底面壁厚 W (mm) -> 直角三角形底边长
ring_height    = 6    # 圆环高度 H (mm) -> 直角三角形高

# 自动计算外径 (若外径固定80，可改为 outer_diameter = 80.0, inner_diameter = 80.0 - 2*wall_thickness)
outer_diameter = inner_diameter + 2 * wall_thickness  # 外径 = 92mm

r_in  = inner_diameter / 2.0  # 内半径 = 40mm
r_out = outer_diameter / 2.0 # 外半径 = 46mm

print("\n" + "="*40)
print("🚀 开始构建直角三角截面圆环实体 (Solid)")
print("="*40)
print(f"📏 [内径] {inner_diameter} mm (半径: {r_in} mm)")
print(f"📏 [外径] {outer_diameter} mm (半径: {r_out} mm)")
print(f"📏 [高度 h] {ring_height} mm")
print(f"📏 [底面壁厚] {wall_thickness} mm")
print("📐 [截面特征] 直角在圆环外侧 (外侧为垂直圆柱面)")

# ==========================================
# 方法一：布尔相减法 (最稳妥，100% 生成 3D 实体)
# ==========================================
# 1. 生成外侧实心圆柱体 (直角外侧，R = r_out, H = ring_height)
outer_cylinder = cq.Workplane("XY").circle(r_out).extrude(ring_height)

# 2. 生成内侧斜面切割体 (底面半径 r_in，顶面半径 r_out)
inner_cone_cut = (
    cq.Workplane("XY")
    .circle(r_in)
    .workplane(offset=ring_height)
    .circle(r_out)
    .loft(ruled=True)
)

# 3. 切割得到直角在外侧的三角形截面圆环
final_solid = outer_cylinder.cut(inner_cone_cut)

# ==========================================
# 检查模型属性
# ==========================================
vol = final_solid.val().Volume()
shape_type = final_solid.val().ShapeType()

print(f"\n✅ 模型生成成功！")
print(f"🔹 模型类型: {shape_type}")  # 应显示 Solid (实体)
print(f"🔹 实体体积: {vol:.2f} mm³")

# ==========================================
# 导出 STEP 文件
# ==========================================
step_file = f"solid_triangle_ring_in{int(inner_diameter)}_out{int(outer_diameter)}_h{int(ring_height)}.step"
cq.exporters.export(final_solid, step_file)
print(f"📁 STEP 文件已保存至: {step_file}")

if "show_object" in globals():
    show_object(final_solid, name="TriangleRingSolid")