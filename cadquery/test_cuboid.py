
import cadquery as cq
import bambu_slicer
# ========== 参数定义 ==========
l = 82.837116   # X方向外尺寸
w =200   # Y方向外尺寸
l=w=10
h=0.1
result = cq.Workplane("XY").workplane(offset=1).box(l, w, h, centered=False)

print(f'{l},{w},{h}')

bed = bambu_slicer.import_stl(r"D:/Bambu Studio/resources/profiles/Elegoo/elegoo_neptune4_buildplate_model.stl")



# 1. 在 CadQuery 中导入 STEP 文件
ibt = cq.importers.importStep(r"D:\test\3mf\build123d\H桥IBT_2模块_2.0.step")
#result=result.union(cq.Workplane().add(bed))
result = result.add(ibt)


result=bambu_slicer.add_brim(result,5)
# ========== 导出与显示 ==========
cq.exporters.export(result, __file__+f"_{l}x{w}.step")
if "show_object" in globals():
    show_object(result)

step_file=__file__+f'.step'

f = bambu_slicer.to_gcode(
    cq_object=result,
    name=step_file,
    output_dir=r"D:\test\bambu-studio",
    material='PETG',
)