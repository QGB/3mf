
import cadquery as cq
import bambu_slicer
# ========== 参数定义 ==========
l = 82.837116   # X方向外尺寸
w =200   # Y方向外尺寸
h=4
result = cq.Workplane("XY").box(l, w, h, centered=True)

print(f'{l},{w},{h}')

bed = bambu_slicer.import_stl(r"D:/Bambu Studio/resources/profiles/Elegoo/elegoo_neptune4_buildplate_model.stl")


#result=result.union(cq.Workplane().add(bed))
result = result.add(bed)

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