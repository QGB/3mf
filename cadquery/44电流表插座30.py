import cadquery as cq
import os

# ==========================================
# 1. 核心参数定义 (完全参数化)
# ==========================================
# 📐 内径尺寸 (单位: mm)
inner_L1 = 45.0  # 左侧主体内腔长度 (X方向)
inner_W1 = 44.0  # 左侧主体内腔宽度 (Y方向)
inner_L2 = 30.0  # 右侧延伸内腔长度 (X方向)
inner_W2 = 30.0  # 右侧延伸内腔宽度 (Y方向，根据图纸比例推算)

# 🧱 框架厚度与高度
wall_thickness = 3.0   # 统一壁厚
frame_height   = 30.0  # 整体拉伸高度

print("\n" + "="*40)
print("🚀 开始构建阶梯形插座中空框架")
print("="*40)
print(f"📏 [左侧内腔] {inner_L1} x {inner_W1} mm")
print(f"📏 [右侧内腔] {inner_L2} x {inner_W2} mm")
print(f"📏 [整体高度] {frame_height} mm")
print(f"📏 [外围壁厚] {wall_thickness} mm")

# ==========================================
# 2. 轮廓坐标计算 (底层逻辑)
# ==========================================
# 以左侧内腔的左下角为原点 (0,0)，逆时针绘制多边形轮廓

# 🔹 内侧轮廓 (挖空的洞)
inner_pts = [
    (0, 0),                                      # 左下角
    (inner_L1 + inner_L2, 0),                    # 右下角
    (inner_L1 + inner_L2, inner_W2),             # 右上角
    (inner_L1, inner_W2),                        # 阶梯内凹角
    (inner_L1, inner_W1),                        # 阶梯左上角
    (0, inner_W1)                                # 左上角
]

# 🔸 外侧轮廓 (实体的壳)
# 将内轮廓向外侧偏移一个 wall_thickness (3mm) 的距离
T = wall_thickness
outer_pts = [
    (-T, -T),                                    # 外左下角
    (inner_L1 + inner_L2 + T, -T),               # 外右下角
    (inner_L1 + inner_L2 + T, inner_W2 + T),     # 外右上角
    (inner_L1 + T, inner_W2 + T),                # 阶梯内凹角对应的外拐点
    (inner_L1 + T, inner_W1 + T),                # 阶梯左侧最高点
    (-T, inner_W1 + T)                           # 外左上角
]

# ==========================================
# 3. 3D 实体构建
# ==========================================
# 💡 CQ 技巧：在同一个 Workplane 上依次绘制外轮廓和内轮廓，
# 然后执行 extrude，CQ 会自动将内部闭合线框识别为孔洞，直接生成中空薄壁实体。
print("\n[生成中...] 正在生成嵌套 2D 轮廓并拉伸...")

frame_solid = (
    cq.Workplane("XY")
    .polyline(outer_pts).close()  # 绘制实心外壳外围
    .polyline(inner_pts).close()  # 绘制内部空心边界
    .extrude(frame_height)        # 向上拉伸 30mm
)

# 检查模型体积以验证有效性
vol = frame_solid.val().Volume()
print(f"✅ 模型生成成功！实体体积: {vol:.2f} mm³")

# ==========================================
# 4. 导出与显示
# ==========================================
# 导出 STEP 文件
step_filename = __file__+f"_{int(inner_L1)}_{int(inner_W1)}_h{int(frame_height)}.step"
cq.exporters.export(frame_solid, step_filename)
print(f"📁 STEP 模型已保存至: {os.path.abspath(step_filename)}")

# 适配 CQ-Editor 或 Jupyter Notebook 的图形显示
if "show_object" in globals():
    show_object(frame_solid, name="Parameteric_Socket_Frame")