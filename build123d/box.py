from build123d import *

# 使用 Build123d 的现代化语法建模
with BuildPart() as box:
    # 1. 外框
    Box(149, 89, 32)
    # 2. 挖空内腔
    with BuildPart(mode=Mode.SUBTRACT):
        top_face = box.faces().sort_by(Axis.Z)[-1]
        with Locations(top_face):
            Box(145, 85, 30, align=(Align.CENTER, Align.CENTER, Align.MAX))
            
    # 3. 倒角
    fillet(box.edges().filter_by(Axis.Z), radius=3)

# 【关键点】CQ-editor 的 show_object 可以直接接收 box.part
show_object(box.part, name="Build123d_Box")