import cadquery as cq

# ========== 参数定义 ==========
outer_diam = 100    # 外径 (mm)
inner_diam = 21   # 内径 (mm)
height =0.2       # 密封圈 95mm

outer_diam,inner_diam,height =29,27,6   #水龙头28
outer_diam,inner_diam,height =20.9,6.5,14   #水龙头28


outer_diam,inner_diam,height=100,30.5,0.3   #水龙头28

outer_diam,inner_diam,height=32.2,20.5,14
outer_diam,inner_diam,height=25,16.2,10
outer_diam,inner_diam,height=24,16.3,22
# 计算半径
outer_rad = outer_diam / 2.0    
inner_rad = inner_diam / 2.0

# ========== 建模 ==========
# 创建外圆柱体（实心）
result = (
    # 底座 Φ24 H22
cq.Workplane("XY").circle(outer_rad).extrude(height)
.faces("XY").circle(16).extrude(height-1.5)
.faces("XY").circle(20).extrude(height-4)
    # 再打通孔，cutThruAll穿透底座+凸台
.faces(">Z").circle(inner_rad).cutThruAll()
)
import os,bambu_slicer
step_file = os.path.splitext(__file__)[0] + f"_D{outer_diam}d{inner_diam}H{height}.step"
#result =  result.union(cq.Workplane("XY").circle(47/2).extrude(0.2))
# ========== 导出与显示 ==========
cq.exporters.export(result,step_file)
show_object(result)


f = bambu_slicer.to_gcode(
    cq_object=result,
    name=step_file,
    output_dir=r"D:\test\bambu-studio",
    material='PETG',
)