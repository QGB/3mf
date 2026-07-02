import cadquery as cq

# ========== 参数定义 ==========
outer_length = 205   # X方向外尺寸
outer_width  = 232   # Y方向外尺寸
thickness    = 0.2   # Z方向厚度 (mm)
frame_width  = 1     # 边框宽度 (mm)

# 内框尺寸（外框减去两侧边框）
inner_length = outer_length - 2 * frame_width   # 231 mm
inner_width  = outer_width  - 2 * frame_width   # 194 mm

# ========== 创建外框（实体板） ==========
frame = cq.Workplane("XY").box(outer_length, outer_width, thickness, centered=True)

# ========== 创建内部切除体（同样厚度，居中） ==========
inner_cut = cq.Workplane("XY").box(inner_length, inner_width, thickness, centered=True)

# ========== 切除内部，留下边框 ==========
result = frame.cut(inner_cut)

# ========== 导出与显示 ==========
cq.exporters.export(result, __file__+f"_{outer_length}x{outer_width}.step")
if "show_object" in globals():
    show_object(result)