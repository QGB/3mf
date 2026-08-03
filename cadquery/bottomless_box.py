import cadquery as cq

# 外部尺寸 (长 × 宽 × 高) 与壁厚
length, width, height = 148+4, 68+4,20
t =2  # 壁厚

# 1. 外部实心长方体（原点居中）
outer = cq.Workplane("XY").box(length, width, height)

# 2. 内部挖空部分（从底面向上切，保留顶面和侧壁）
inner_l = length - 2*t
inner_w = width  - 2*t
inner_h = height-0 #- t        # 无底，所以只需挖掉底面到顶壁下方的高度

# 内部长方体的中心位置：外部底面在 -height/2，挖掉区域从底面开始向上 inner_h
inner_z = -height/2 + inner_h/2
inner = cq.Workplane("XY").box(inner_l, inner_w, inner_h).translate((0, 0, inner_z-2))

# 3. 相减得到无底盒子
box = outer.cut(inner)

# 导出 STEP 文件
cq.exporters.export(box, __file__+f"{length}.step")

# 在 CQ-editor 中显示
if "show_object" in dir():
    show_object(box)