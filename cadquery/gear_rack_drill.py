import cadquery as cq

# ========== 参数定义 ==========
size = 20                  # 立方体边长 20mm
z_square_side = 12.3       # Z方向贯通正方形边长 10.2mm
side_hole_diam = 8.1       # 侧面盲孔直径 8.2mm

# ========== 建模 ==========
# 1. 创建中心对称的 20x20x20 立方体
result = cq.Workplane("XY").box(size+6, size, size)

# 2. Z 轴贯穿正方形孔
result = (
    result.faces(">Z")                # 选择顶面
    .workplane()
    .rect(z_square_side, z_square_side)  # 画 10.2x10.2 正方形
    .cutThruAll()                     # 完全贯穿
)

# 3. 侧面盲孔 (刚好到中心)
# 选择 YZ 面（中心点 X=0），画圆向外侧(正 X 方向)拉伸作为刀具
cutter = (
    cq.Workplane("YZ",).workplane(offset=-20)
    .circle(side_hole_diam / 2.0)     # 半径 4.1mm
    .extrude(44)          # size / 2.0 + 2向外拉伸 12mm (10mm到表面 + 2mm 冗余确保切透)
)


# cutter = (
#     cq.Workplane("YZ")
#     .circle(side_hole_diam / 2.0)     # 半径 4.1mm
#     .extrude(-20)
# )

# 使用布尔差集切除侧面孔
result = result.cut(cutter)

# ========== 导出 ==========
# 导出 STEP 文件
filename = __file__+f"_{size}_inner{z_square_side}_hole{side_hole_diam}.step"
cq.exporters.export(result, filename)

# 如果在 CQ-Editor 中运行，取消注释下一行以显示
show_object(result)