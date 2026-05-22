import cadquery as cq

# ========== 参数定义 ==========
outer_diam = 100    # 外径 (mm)
inner_diam = 96   # 内径 (mm)
height =3       # 高度 (mm)

# 计算半径
outer_rad = outer_diam / 2.0    
inner_rad = inner_diam / 2.0

# ========== 建模 ==========
# 创建外圆柱体（实心）
result = cq.Workplane("XY").circle(outer_rad).extrude(height)

# 挖出中心通孔（直径 = inner_diam）
result = (
    result.faces(">Z")          # 选择上表面
    .workplane()                # 在该表面创建新工作平面
    .circle(inner_rad)          # 内孔圆
    .cutThruAll()               # 完全穿透
)

# ========== 导出与显示 ==========
cq.exporters.export(result, __file__ +f"=D{outer_diam}d{inner_diam}H{height}.step")
show_object(result)