import sys,builtins
if not hasattr(builtins, "_CQ_PERSISTENT_MODULES"):
    builtins._CQ_PERSISTENT_MODULES = {}

# 在每次脚本运行前，强行将已加载的 C 模块塞回 sys.modules，防止重复初始化崩溃
for mod_name, mod_obj in builtins._CQ_PERSISTENT_MODULES.items():
    if mod_name not in sys.modules:
        sys.modules[mod_name] = mod_obj

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

try:
    import bambu_slicer
except:    
    sys.path.append(r'D:\test\3mf\cadquery')
    
import bambu_slicer