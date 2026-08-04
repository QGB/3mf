安装build123d  会造成
D:\test\github\CQ-editor>cq-editor.bat
VTK not installed
Traceback (most recent call last):
  File "D:\test\github\CQ-editor\run.py", line 17, in <module>
    from cq_editor.cqe_run import main
  File "D:\test\github\CQ-editor\cq_editor\cqe_run.py", line 9, in <module>
    from cq_editor.__main__ import main
  File "D:\test\github\CQ-editor\cq_editor\__main__.py", line 11, in <module>
    from .main_window import MainWindow
  File "D:\test\github\CQ-editor\cq_editor\main_window.py", line 17, in <module>
    import cadquery as cq
  File "D:\test\github\CQ-editor\Lib\site-packages\cadquery\__init__.py", line 11, in <module>
    from .occ_impl.shapes import (
    ...<9 lines>...
    )
  File "D:\test\github\CQ-editor\Lib\site-packages\cadquery\occ_impl\shapes.py", line 297, in <module>
    from OCP.IVtkOCC import IVtkOCC_Shape, IVtkOCC_ShapeMesher
ImportError: cannot import name 'IVtkOCC_Shape' from 'OCP.IVtkOCC' (D:\test\github\CQ-editor\Lib\site-packages\OCP\IVtkOCC\__init__.py)


只能先安装build123d 然后 --force-reinstall 恢复了 cadquery-ocp，
python -m pip install --force-reinstall cadquery-ocp==7.9.3.1.1


