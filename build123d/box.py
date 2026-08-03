import sys
import builtins

# ============================================================
# 【黑科技补丁 1】：C 模块保险箱（彻底绕过“不能运行第二次”的限制）
# ============================================================
if not hasattr(builtins, "_CQ_PERSISTENT_MODULES"):
    builtins._CQ_PERSISTENT_MODULES = {}

# 在每次脚本运行前，强行将已加载的 C 模块塞回 sys.modules，防止重复初始化崩溃
for mod_name, mod_obj in builtins._CQ_PERSISTENT_MODULES.items():
    if mod_name not in sys.modules:
        sys.modules[mod_name] = mod_obj


# ============================================================
# 【补丁 2】：Windows 系统 TTC 复合字体防崩溃补丁
# ============================================================
try:
    from fontTools.ttLib import TTFont, TTLibFileIsCollectionError
    _orig_ttfont_init = TTFont.__init__

    def _patched_ttfont_init(self, file=None, *args, **kwargs):
        try:
            _orig_ttfont_init(self, file, *args, **kwargs)
        except TTLibFileIsCollectionError:
            kwargs['fontNumber'] = 0
            _orig_ttfont_init(self, file, *args, **kwargs)

    TTFont.__init__ = _patched_ttfont_init
except Exception:
    pass


# ============================================================
# 正式导入 build123d 并备份模块
# ============================================================
from build123d import *

# 首次导入成功后，立刻将关键 C 扩展模块锁入 builtins 保险箱
for name, mod in list(sys.modules.items()):
    if any(pkg in name for pkg in ["numpy", "scipy", "build123d", "OCP", "freetype", "fontTools"]):
        builtins._CQ_PERSISTENT_MODULES[name] = mod


# ============================================================
# Build123d 建模逻辑
# ============================================================
with BuildPart() as box:
    # 1. 外框 (149 x 89 x 32 mm)
    Box(149, 89, 32)
    
    # 2. 挖空内腔 (145 x 85 x 30 mm)
    top_face = box.faces().sort_by(Axis.Z)[-1]
    with Locations(top_face):
        Box(145, 85, 30, align=(Align.CENTER, Align.CENTER, Align.MAX), mode=Mode.SUBTRACT)

    # 3. 侧边倒角 (r = 3 mm)
    fillet(box.edges().filter_by(Axis.Z), radius=3)


# ============================================================
# 渲染到 CQ-Editor 视图
# ============================================================
if "show_object" in locals():
    import cadquery as cq
    # 将 build123d 的 Part 转换为 CQ-Editor 兼容的 cq.Shape
    show_object(cq.Shape(box.part.wrapped), name="Build123d_Box")