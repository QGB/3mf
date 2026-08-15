import build123d_fix
import math
from build123d import *


with BuildPart() as box:
    # 3.1 外部实心长方体
    Box(40,10,0.5)
    
print("✅ 模型生成完毕！准备输出。")

# ============================================================
# 7. 渲染与输出
# ============================================================
import os, bambu_slicer, cadquery as cq
step_file = os.path.splitext(__file__)[0] + f"_.step"
export_step(box.part, step_file)
cq_object = cq.Shape(box.part.wrapped)

if "show_object" in locals():
    show_object(cq_object, name=step_file[:-5])

f = bambu_slicer.to_gcode(
    cq_object=box,
    name=step_file,
    output_dir=r"D:\test\bambu-studio",
    material='PETG',
    layer_height=0.39,
)