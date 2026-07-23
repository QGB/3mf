import cadquery as cq

def make_ruler(length=150.0, width=10.0, thick=1.0,cut_depth = -0.3, font_path="C:/Windows/Fonts/STENCIL.TTF"):
    """
    生成一把基础刻度尺（默认沿 X 轴延伸，中心点在原点）
    
    :param length: 尺子总长度 (mm)
    :param width:  尺子宽度 (mm)
    :param thick:  尺子厚度 (mm)
    :param font_path: 字体文件路径
    """
    margin = 5.0
    start_x = -length / 2 + margin  # -70.0 mm
    end_x   =  length / 2 - margin   #  70.0 mm

    len_10mm = 2.0
    line_width = 0.5
      # 雕刻深度

    pts_10mm = []
    text_data = [] 

    start_x_int = int(round(start_x)) # -70
    end_x_int   = int(round(end_x))   #  70

    # 1. 收集刻度与文字数据
    for x_mm in range(start_x_int, end_x_int + 1):
        if x_mm % 10 == 0:
            x = float(x_mm)
            pts_10mm.append((x, width/2 - len_10mm/2))
            num_str = str(x_mm // 10)
            # 适度缩放字号与位置，保证在 10mm 窄框内美观居中
            text_data.append((x, width/2 - len_10mm - 3.5, num_str))

    # 2. 创建尺子本体
    ruler = cq.Workplane("XY").box(length, width, thick)

    # 3. 制作刻度线刀具
    line_cutter = (
        cq.Workplane("XY")
        .workplane(offset=thick/2)
        .pushPoints(pts_10mm)
        .rect(line_width, len_10mm)
        .extrude(cut_depth)
    )

    # 4. 制作文字刀具
    text_cutter = cq.Workplane("XY")
    for tx, ty, num_str in text_data:
        single_text = (
            cq.Workplane("XY")
            .workplane(offset=thick/2)
            .center(tx, ty)
            .text(num_str, fontsize=4.5, distance=cut_depth, fontPath=font_path, halign="center", valign="center")
        )
        text_cutter = text_cutter.add(single_text.val())

    # 5. 一次性布尔切割
    ruler = ruler.cut(line_cutter).cut(text_cutter)
    
    return ruler


# ==================== 主程序：生成三轴刻度尺 ====================

# 1. 生成基础尺子（沿 X 轴）
ruler_x = make_ruler(length=150.0, width=10.0, thick=1.0)

# 2. 绕 Z 轴旋转 90 度 -> 沿 Y 轴
ruler_y = make_ruler(length=150.0, width=10.0, thick=1.0).rotate((0, 0, 0), (0, 0, 1), 90)

# 3. 绕 Y 轴旋转 -90 度 -> 沿 Z 轴
ruler_z = make_ruler(length=150.0, width=10.0, thick=1.0,cut_depth = -2).rotate((0, 0, 0), (0, 1, 0), -90)

# ========== 输出与显示 ==========

# 导出三合一三维坐标系 STEP 文件
xyz_combined = ruler_x.union(ruler_y).union(ruler_z)
cq.exporters.export(xyz_combined, "ruler_xyz_combined.step")

# 在 CQ-editor 中渲染展示（以经典的 X:红, Y:绿, Z:蓝 显示）
if "show_object" in globals():
    show_object(ruler_x, name="Ruler_X", options={"color": (255, 0, 0)})    # 红色代表 X 轴
    show_object(ruler_y, name="Ruler_Y", options={"color": (0, 255, 0)})    # 绿色代表 Y 轴
    show_object(ruler_z, name="Ruler_Z", options={"color": (0, 0, 255)})    # 蓝色代表 Z 轴