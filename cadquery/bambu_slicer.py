import sys;'qgb.U' in sys.modules or sys.path.append('C:/QGB/Anaconda3/Lib/site-packages/Pythonwin/')
import sys;'qgb.U' in sys.modules or sys.path.append('C:/QGB/miniforge3/Lib/site-packages/pythonwin/');from qgb import *
import os,sys,json,shutil
import subprocess
import zipfile
import tempfile
import cadquery as cq

import os,re
import json
import tempfile
import subprocess
import zipfile
import shutil
import cadquery as cq

# ==================== 后台固定的默认环境配置 ====================
DEFAULT_BAMBU_EXE = r"D:\Bambu Studio\bambu-studio.exe"
DEFAULT_MACHINE_JSON = r"C:\Users\Administrator\AppData\Roaming\BambuStudio\user\1154792620\machine\Elegoo Neptune 4 0.2 nozzle - 拷贝.json"
DEFAULT_FILAMENT_JSON = r"C:\Users\Administrator\AppData\Roaming\BambuStudio\user\1154792620\filament\66-55.json"
DEFAULT_PROCESS_JSON = r"C:\Users\Administrator\AppData\Roaming\BambuStudio\user\1154792620\process\填充44  skirt5.json"

# ==================== 材质参数预设库 ====================
MATERIAL_PRESETS = {
    "PLA": {
        "filament_type": ["PLA"],
        "nozzle_temperature": ["205"],
        "nozzle_temperature_initial_layer": ["205"],
        "hot_plate_temp": ["60"],
        "hot_plate_temp_initial_layer": ["65"],
        "fan_max_speed": ["100"],
        "fan_min_speed": ["100"],
        "close_fan_the_first_x_layers": ["1"]
    },
    "PETG": {
        "filament_type": ["PETG"],
        "nozzle_temperature": ["235"],
        "nozzle_temperature_initial_layer": ["238"],
        "hot_plate_temp": ["65"],
        "hot_plate_temp_initial_layer": ["70"],
        "fan_max_speed": ["50"],
        "fan_min_speed": ["20"],
        "close_fan_the_first_x_layers": ["3"]
    },
    "ABS": {
        "filament_type": ["ABS"],
        "nozzle_temperature": ["250"],
        "nozzle_temperature_initial_layer": ["250"],
        "hot_plate_temp": ["100"],
        "hot_plate_temp_initial_layer": ["100"],
        "fan_max_speed": ["30"],
        "fan_min_speed": ["0"],
        "close_fan_the_first_x_layers": ["5"]
    },
    "TPU": {
        "filament_type": ["TPU"],
        "nozzle_temperature": ["220"],
        "nozzle_temperature_initial_layer": ["225"],
        "hot_plate_temp": ["50"],
        "hot_plate_temp_initial_layer": ["50"],
        "fan_max_speed": ["100"],
        "fan_min_speed": ["80"],
        "close_fan_the_first_x_layers": ["1"]
    }
}


def _preprocess_dependent_json(src_path, safe_name, type_tag, model_token, material_overrides=None):
    """内部函数：用于工艺和耗材配置文件的强行兼容性对齐及参数覆写"""
    try:
        with open(src_path, 'r', encoding='utf-8-sig') as f:
            config_data = json.load(f)
        
        config_data['type'] = type_tag
        config_data["compatible_printers"] = [model_token]
        
        config_data.pop("compatible_printers_condition", None)
        config_data.pop("compatible_prints_condition", None)
        config_data.pop("compatible_filaments_condition", None)
        
        # 核心改动：注入材质覆盖参数
        if material_overrides and isinstance(material_overrides, dict):
            config_data.update(material_overrides)
        
        tmp_dest = os.path.join(tempfile.gettempdir(), safe_name)
        with open(tmp_dest, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, ensure_ascii=False, indent=4)
        return tmp_dest
    except Exception as e:
        print(f"[ERROR] 强制对齐配置失败 [{safe_name}]: {e}")
        raise e


def to_gcode(cq_object, name="cq_model", output_dir=None, add_brim=0, layer_height="0.249mm", material="PLA", printer_name="Elegoo Neptune 4", print_time="17m34s"):
    """
    升级版封装：将 CadQuery 对象直接切片，动态注入材质参数（如 PETG 喷嘴/热床温度），成功则返回 G-code 绝对路径
    """
    # 核心修复：自动提取纯文件名，并剔除可能随路径传入的扩展名
    clean_name = os.path.basename(name)
    if clean_name.lower().endswith(('.step', '.solid', '.stl', '.py')):
        clean_name = os.path.splitext(clean_name)[0]

    if output_dir is None:
        output_dir = os.getcwd()
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 1. 匹配材质预设参数
    mat_key = material.strip().upper()
    material_overrides = MATERIAL_PRESETS.get(mat_key, MATERIAL_PRESETS["PETG"])
    print(f"[INFO] 正在应用材质配置: {mat_key} -> 喷嘴首层 {material_overrides['nozzle_temperature_initial_layer'][0]}℃, 热床首层 {material_overrides['hot_plate_temp_initial_layer'][0]}℃")

    # 2. 解析机型
    print("[INFO] 正在解析机型配置文件并提取兼容性锚点...")
    try:
        with open(DEFAULT_MACHINE_JSON, 'r', encoding='utf-8-sig') as f:
            machine_data = json.load(f)
        
        printer_model_token = machine_data.get("printer_model") or machine_data.get("inherits") or "Elegoo Neptune 4 0.2 nozzle"
        machine_data["printer_model"] = printer_model_token
        machine_data["type"] = "machine"
        
        safe_machine = os.path.join(tempfile.gettempdir(), "cli_machine.json")
        with open(safe_machine, 'w', encoding='utf-8') as f:
            json.dump(machine_data, f, ensure_ascii=False, indent=4)
        print(f"[INFO] 成功锁定机型兼容锚点: {printer_model_token}")
    except Exception as e:
        print(f"[ERROR] 提取机型锚点失败: {e}")
        return None

    # 3. 对齐工艺与耗材（将 PETG 参数动态注入耗材配置中）
    print("[INFO] 正在对工艺和耗材配置文件执行强行兼容性对齐及材质参数注入...")
    safe_process = _preprocess_dependent_json(DEFAULT_PROCESS_JSON, "cli_process.json", "process", printer_model_token)
    safe_filament = _preprocess_dependent_json(
        DEFAULT_FILAMENT_JSON, 
        "cli_filament.json", 
        "filament", 
        printer_model_token,
        material_overrides=material_overrides
    )
    print("[INFO] 配置文件闭环清洗完毕，安全沙盒映射成功。")

    # 4. 使用净化后的安全名称建立临时中转路径
    temp_stl = os.path.join(tempfile.gettempdir(), f"bambu_cli_temp_{clean_name}.stl")
    temp_3mf = os.path.join(tempfile.gettempdir(), f"bambu_cli_temp_{clean_name}.3mf")

    # 5. 导出 STL
    print("[STEP 1] 正在将 CadQuery 对象直接转换为高精度 STL 网格...")
    try:
        # 判断是否为 build123d 对象，优先使用其原生 STL 导出
        if hasattr(cq_object, "part"):#box.part.wrapped 在 build123d 中通常是一个 Compound，而 CadQuery 期望接收的是 Workplane、Shape 或者一个 Shapes 列表。直接传入 Compound 会触发参数解包错误。
            # build123d 的 BuildPart 上下文对象 (with BuildPart() as box:)
            from build123d import export_stl as b3d_export_stl
            b3d_export_stl(cq_object.part, temp_stl, tolerance=0.01) # 不能用 cq.exporters.export(box.part.wrapped)
        elif hasattr(cq_object, "val"):
            # CadQuery Workplane 或 Assembly
            shape_to_export = cq_object.val()
            cq.exporters.export(shape_to_export, temp_stl, tolerance=0.01)
        else:
            # 兜底：尝试作为 CadQuery Shape 导出
            cq.exporters.export(cq_object, temp_stl, tolerance=0.01)

        print("   -> [INFO] STL 内存网格转换成功！")
    except Exception as e:
        print(f"[ERROR] 导出 STL 失败: {e}")
        return None
    # 6. 调用拓竹引擎执行切片
    print("[STEP 2] 正在调用拓竹命令行引擎执行闭环切片...")
    composite_settings = f"{safe_machine};{safe_process}"
    cmd = [
        DEFAULT_BAMBU_EXE,
        "--slice", "0",
        "--load-settings", composite_settings,
        "--load-filaments", safe_filament,
        "--export-3mf", temp_3mf,
        temp_stl
    ]

    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='ignore')

    if result.returncode != 0:
        print("[ERROR] 拓竹切片失败！详细的底层错误日志如下：")
        print("====== STDOUT LOG ======")
        print(result.stdout if result.stdout else "[无输出]")
        print("====== STDERR LOG ======")
        print(result.stderr if result.stderr else "[无输出]")
        if os.path.exists(temp_stl): os.remove(temp_stl)
        return None

    # 7. 提取 G-code
    print("[STEP 3] 切片成功，正在从 3MF 数据包中解压并提取纯 G-code...")
    output_gcode_name = f"{clean_name}_{layer_height}_{material}_{printer_name}_{print_time}.gcode"
    final_gcode_path = os.path.join(output_dir, output_gcode_name)

    if os.path.exists(temp_3mf):
        try:
            with zipfile.ZipFile(temp_3mf, 'r') as zip_ref:
                gcode_in_zip = "Metadata/plate_1.gcode"
                if gcode_in_zip in zip_ref.namelist():
                    with zip_ref.open(gcode_in_zip) as source, open(final_gcode_path, 'wb') as target:
                        shutil.copyfileobj(source, target)
                    print(U.pformat(analyze_gcode(final_gcode_path)),'\n',f"路径 {final_gcode_path}",)
                    return final_gcode_path
                else:
                    print("[WARNING] 3mf 包内未发现 gcode 轨迹，请检查配置参数。")
                    return None
        except Exception as e:
            print(f"[ERROR] 提取 G-code 失败: {e}")
            return None
        finally:
            print("[STEP 4] 正在清理临时中转文件...")
            if os.path.exists(temp_stl): os.remove(temp_stl)
            if os.path.exists(temp_3mf): os.remove(temp_3mf)
            print("   -> [INFO] 清理完毕。")
    else:
        print("[ERROR] 未找到生成的临时 3mf 文件。")
        return None
########################

def flip_model(solid, angle, axis='y'):
    axis = axis.lower()
    x_scale, y_scale = 1, 1
    if axis == 'x':
        vec = (1, 0, 0)
        if angle % 360 == 180: y_scale = -1
    elif axis == 'y':
        vec = (0, 1, 0)
        if angle % 360 == 180: x_scale = -1
    else:
        vec = (0, 0, 1)
        if angle % 360 == 180: x_scale, y_scale = -1, -1
            
    rotated_solid = solid.rotate((0, 0, 0), vec, angle)
    return rotated_solid, x_scale, y_scale

# ==========================================
# 2. 顶面时间标注函数（绝对单向传递 smark）
def add_time_mark(obj, smark='', x=0, y=-7.5, plane='top', mode='auto', thickness=None, mark_depth=0.1):
    if not smark:
        smark = U.get_time_str_mark(sep=' ')
    current_t = thickness if thickness is not None else obj.val().BoundingBox().zlen
    mode_lower = str(mode).lower().strip()
    if mode_lower == 'auto':
        actual_mode = 'yin' if current_t >= 1.0 else 'yang'
    elif mode_lower in ['yin', '阴', '凹', 'engrave', 'deboss', 'recessed']:
        actual_mode = 'yin'
    elif mode_lower in ['yang', '阳', '凸', 'emboss', 'raised']:
        actual_mode = 'yang'
    else:
        actual_mode = 'yin' if current_t >= 1.0 else 'yang'
    if plane == 'top':
        offset = current_t / 2.0
        distance = -mark_depth if actual_mode == 'yin' else mark_depth
    elif plane == 'bottom':
        offset = -current_t / 2.0
        distance = mark_depth if actual_mode == 'yin' else -mark_depth
    else:
        raise ValueError("plane 参数只能是 'top' 或 'bottom'")
    text_cutter = (
        cq.Workplane("XY")
        .workplane(offset=offset)
        .center(x, y)
        .text(smark, fontsize=8, distance=distance, font="Arial", halign="center", valign="center", combine=False)
    )
    if actual_mode == 'yin':
        res_obj = obj.cut(text_cutter)
    else:
        res_obj = obj.union(text_cutter)
    if len(res_obj.solids().vals()) > 1:
        res_obj = cq.Workplane(obj=max(res_obj.solids().vals(), key=lambda s: s.Volume()))
    return res_obj, smark
    
def add_brim(obj, extend=10.0, thickness=0.4):
    """
    【任意异形完美适配版 - 修正版】
    """
    bbox = obj.val().BoundingBox()
    zmin = bbox.zmin
    
    # 1. 提取最底部的面 Workplane
    bottom_faces = obj.faces("<Z")
    
    # 2. 【修正关键】：使用 .val() 获取真实的 Face 对象，再提取最外圈外轮廓
    outer_wire = bottom_faces.val().outerWire()
    
    try:
        # 3. 绘制外扩后的实体
        outer_solid = (
            cq.Workplane("XY", origin=(0, 0, zmin))
            .add(outer_wire)
            .toPending()
            .offset2D(extend, kind="arc") 
            .extrude(thickness)
        )
        
        # 4. 绘制未外扩的原始实体
        inner_solid = (
            cq.Workplane("XY", origin=(0, 0, zmin))
            .add(outer_wire)
            .toPending()
            .extrude(thickness)
        )
        
        # 5. 外大圈 减去 内小圈 = 得到紧贴外沿的中空裙边
        brim_frame = outer_solid.cut(inner_solid)
        
        # 6. 和原模型求并集
        return obj.union(brim_frame)
        
    except Exception as e:
        print(f"[Brim Warning] 异形轮廓放大失败 ({e})，自动降级为包围盒标准矩形裙边！")
        # 如果报错，在此处调用你之前基于 BoundingBox 写的绝对稳定的标准矩形裙边函数作兜底
        return add_brim_bounding_box(obj, extend, thickness)


def get_bottom_outer_contour_points(obj):
    """
    寻找物体的绝对底面，并输出其外轮廓(outerWire)的顶点坐标列表。
    暂时不处理圆弧离散化，仅提取特征几何顶点。
关于未来“圆弧怎么解决”的剧透：
如果以后你的主板外围变成了带圆角的矩形，或者圆形板，Vertices() 就只会吐出圆弧的起点和终点，导致坐标残缺。那时候最完美的 Pro 级解法不是去数点，而是调用 outer_wire.tessellate(tolerance)。这是 3D 引擎底层的网格离散化/弦高差采样，它能根据你给的精度（比如 0.1mm），自动把任何圆弧、样条曲线均匀地切成一连串微小的直线段，并吐出完美的、连续的高精度围栏坐标轨迹。不过既然目前是纯矩形边界，上面这个数顶点的函数已经足够精准高效！    
    """
    import cadquery as cq
    # 1. 自动解包 Workplane 获取底层 Solid
    solid = obj.val() if hasattr(obj, "val") else obj
    if not solid:
        return []
        
    bottom_face = None
    min_z = float('inf')
    
    # 2. 扫描所有面，锁定 Z 轴位置最低的那个【水平底面】
    for face in solid.Faces():
        # 依靠法线方向判断是否为水平面 (Z 轴分量接近 1 或 -1)
        if abs(face.normalAt().z) > 0.99:
            face_z = face.Center().z
            if face_z < min_z:
                min_z = face_z
                bottom_face = face
                
    if not bottom_face:
        print("❌ 未找到有效的水平底面")
        return []
        
    # 3. 提取底面的最外围轮廓 (outerWire)
    outer_wire = bottom_face.outerWire()
    if not outer_wire:
        print("❌ 该底面没有有效的外轮廓")
        return []
        
    # 4. 提取顶点坐标 (保留 2 位小数)
    # 因为 OCCT 的 Wire.Vertices() 本身就是带有拓扑顺序的（顺时针或逆时针），
    # 我们直接顺着线圈提取，并做个邻近去重即可。
    raw_vertices = outer_wire.Vertices()
    coordinate_list = []
    
    for v in raw_vertices:
        pt = (round(v.X, 2), round(v.Y, 2))
        # 仅去除首尾闭合或重复的相邻点，保持原汁原味的拓扑走向
        if not coordinate_list or pt != coordinate_list[-1]:
            coordinate_list.append(pt)
            
    # 如果首尾因为闭合导致重复，切掉最后一个点
    if len(coordinate_list) > 1 and coordinate_list[0] == coordinate_list[-1]:
        coordinate_list.pop()
        
    return coordinate_list        
        

def super_feature_detector(obj, feature_type="circle", target_size=None):
    """
    【究极空间拓扑探测器 - 几何本质版】
    抛弃脆弱的顶点容差去重，直接对底层 Wire 的边缘属性进行拓扑断言。
    """
            
    import cadquery as cq
    import math
    from OCP.BRepAdaptor import BRepAdaptor_Curve, BRepAdaptor_Surface
    from OCP.GeomAbs import GeomAbs_Plane, GeomAbs_Line
    # 自动解包获取底层 Solid，防止传入 Workplane 导致类型不匹配
    solid = obj.val() if hasattr(obj, "val") else obj
    if not solid:
        return []
        
    results = []
    
    # ====================================================
    # A：圆柱孔/残缺圆探测
    # ====================================================
    if feature_type == "circle":
        for edge in solid.Edges():
            if edge.GeometryType() == "CIRCLE":
                try:
                    adaptor = BRepAdaptor_Curve(edge.wrapped)
                    circ = adaptor.Circle()
                    pnt = circ.Location()
                    radius = round(circ.Radius(), 2)
                    
                    # 尺寸过滤
                    if target_size is not None and not math.isclose(radius, target_size, abs_tol=0.1):
                        continue
                        
                    # 获取中心点
                    pos = (round(pnt.X(), 2), round(pnt.Y(), 2), round(pnt.Z(), 2))
                    
                    # XY 通道去重：同一个圆柱孔的上下边缘视为同一个孔
                    if not any(math.isclose(pos[0], ep[0], abs_tol=0.2) and 
                               math.isclose(pos[1], ep[1], abs_tol=0.2) for ep in results):
                        results.append(pos)
                except Exception:
                    pass

    # ====================================================
    # B：六边形螺母孔探测 (Pro 级边数断言法)
    # ====================================================
    elif feature_type == "hexagon":
        for face in solid.Faces():
            try:
                # 1. 过滤非平面
                surf = BRepAdaptor_Surface(face.wrapped)
                if surf.GetType() != GeomAbs_Plane:
                    continue
                
                # 2. 过滤非水平面（只看法线平行于 Z 轴的平面）
                gp_pln = surf.Plane()
                if abs(gp_pln.Axis().Direction().Z()) < 0.99:
                    continue
                
                # 3. 提取面上所有线圈 (合并外边界和所有内挖孔边界)
                wires = []
                if face.outerWire():
                    wires.append(face.outerWire())
                wires.extend(face.innerWires())
                
                # 4. 遍历线圈，进行几何本质断言
                for wire in wires:
                    edges = wire.Edges()
                    
                    # 核心突破：一个纯正的六边形孔，它的边缘数量绝对、严格等于 6
                    if len(edges) == 6:
                        
                        # 严谨校验：确保这 6 条边全是直线，而不是什么被切成 6 段的弧线
                        is_perfect_hex = True
                        for edge in edges:
                            curve_adaptor = BRepAdaptor_Curve(edge.wrapped)
                            if curve_adaptor.GetType() != GeomAbs_Line:
                                is_perfect_hex = False
                                break
                        
                        # 如果确实是 6 条直线组成的封闭多边形
                        if is_perfect_hex:
                            center = wire.Center()
                            pos = (round(center.x, 2), round(center.y, 2), round(center.z, 2))
                            
                            # 垂直通道去重：通孔会在顶面和底面各留下一个六边形线圈，坐标 XY 相同即视为同一个孔
                            if not any(math.isclose(pos[0], ep[0], abs_tol=0.5) and 
                                       math.isclose(pos[1], ep[1], abs_tol=0.5) for ep in results):
                                results.append(pos)
            except Exception:
                pass
                
    return results
        
        
        
        
        


        
        
import time,requests
from urllib.parse import quote


def ensure_z_offset(target_z=-2.4, printer_ip="192.168.1.113", printer_port=7125):
    """
    确保打印机的 Z 轴偏移值达到目标精度，不满足则动态调整
    """
    base_url = f"http://{printer_ip}:{printer_port}"
    status_url = f"{base_url}/printer/objects/query?toolhead&gcode_move"
    
    try:
        response = requests.get(status_url)
        if response.status_code != 200:
            print(f"[ERROR] 查询状态失败, 状态码: {response.status_code}")
            return False
        
        data = response.json()
        current_z = data["result"]["status"]["gcode_move"]["homing_origin"][2]
        print(f"[INFO] 当前Z偏移值: {current_z}")
        
        if abs(current_z - target_z) < 0.01:
            print(f"[INFO] 已是目标值 {target_z}，无需调整")
            return True
            
    except (KeyError, Exception) as e:
        print(f"[ERROR] 解析状态数据失败: {e}")
        return False
        
    # 执行调整
    cmd = f"SET_GCODE_OFFSET Z={target_z} MOVE=1"
    set_url = f"{base_url}/printer/gcode/script?script={quote(cmd)}"
    
    try:
        set_response = requests.post(set_url)
        if set_response.status_code != 200:
            print(f"[ERROR] 调整Z偏移失败, 状态码: {set_response.status_code}")
            return False
            
        time.sleep(0.5)  # 等待更新固件状态
        
        verify = requests.get(status_url).json()["result"]["status"]["gcode_move"]["homing_origin"][2]
        print(f"[SUCCESS] 调整成功! 验证后Z偏移: {verify}")
        return True
    except Exception as e:
        print(f"[ERROR] 调整Z偏移过程中发生异常: {e}")
        return False


def upload_and_print(file_path, printer_ip="192.168.1.113", printer_port=7125, target_z=-3.0):
    """
    封装函数：上传指定的 G-code 文件至 Klipper 并自动启动打印
    
    :param file_path: G-code 文件的本地绝对路径
    :param printer_ip: 打印机 IP 地址
    :param printer_port: Moonraker 端口号，默认 7125
    :param target_z: 启动打印后强制对齐的 Z 轴偏移值
    """
    if not os.path.exists(file_path):
        print(f"[ERROR] 找不到指定的 G-code 文件: {file_path}")
        return None

    base_url = f"http://{printer_ip}:{printer_port}"
    upload_url = f"{base_url}/server/files/upload"
    file_name = os.path.basename(file_path)

    print(f"[INFO] 正在上传文件 [{file_name}] 至打印机 {printer_ip}...")
    
    try:
        # 1. 上传 G-code 文件
        with open(file_path, "rb") as f:
            files = {"file": (file_name, f)}
            response = requests.post(upload_url, files=files)
            
        if response.status_code not in [200, 201]:
            print(f"[ERROR] 文件上传失败, 状态码: {response.status_code}")
            print(response.text)
            return None
            
        print("[SUCCESS] 文件上传成功!")
        result = response.json()
        uploaded_filename = result["item"]["path"]
        print(f"[INFO] 远程服务器文件路径: {uploaded_filename}")
        
        # 2. 开始打印
        print("[INFO] 正在向控制端发送启动打印指令...")
        encoded_filename = quote(uploaded_filename)
        start_print_url = f"{base_url}/printer/print/start?filename={encoded_filename}"
        
        start_response = requests.post(start_print_url)
        if start_response.status_code == 200:
            print("[SUCCESS] 打印任务已成功启动!")
            # 3. 触发 Z 轴偏移校准
            ensure_z_offset(target_z=target_z, printer_ip=printer_ip, printer_port=printer_port)
            return True
        else:
            print(f"[ERROR] 启动打印失败, 状态码: {start_response.status_code}")
            print(start_response.text)
            return None
            
    except Exception as e:
        print(f"[ERROR] 网络请求或传输过程中发生异常: {e}")
        return None        
        



def analyze_gcode(gcode_path):
    """
    解析 G-code 文件，提取切片参数。当总层数大于 1 时自动输出最后一层的参数。
    
    返回字典 Key 说明:
    - nozzle_temp   : 首层喷嘴温度 (℃)
    - bed_temp      : 首层热床温度 (℃)
    - layer_h       : 设定基础层高 (mm)
    - line_w        : 首层线宽 (mm)
    - total_layers  : 总层数
    - first_z       : 首层 Z 高度 (mm)
    
    【仅当 total_layers > 1 时追加】:
    - last_z        : 最后一层 Z 高度 (mm)
    - last_noz_temp : 最后一层喷嘴温度 (℃)
    - last_bed_temp : 最后一层热床温度 (℃)
    - last_layer_h  : 最后一层层高 (mm)
    - last_line_w   : 最后一层/顶层线宽 (mm)
    """
    if not os.path.exists(gcode_path):
        print(f"[ERROR] 文件不存在: {gcode_path}")
        return None

    config = {}
    layer_z_list = []
    total_layers_cfg = 0

    with open(gcode_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line_str = line.strip()

            # 1. 提取总层数
            if total_layers_cfg == 0:
                m_tot = re.search(r"^;\s*total layer number:\s*(\d+)", line_str, re.IGNORECASE)
                if m_tot:
                    total_layers_cfg = int(m_tot.group(1))

            # 2. 收集 Z 轴轨迹高度
            m_z = re.search(r"^;\s*Z_HEIGHT:\s*([0-9.]+)", line_str, re.IGNORECASE)
            if m_z:
                layer_z_list.append(float(m_z.group(1)))

            # 3. 提取最大 Z 高度
            if "max_z" not in config:
                m_max_z = re.search(r"^;\s*max_z_height:\s*([0-9.]+)", line_str, re.IGNORECASE)
                if m_max_z:
                    config["max_z"] = float(m_max_z.group(1))

            # 4. 解析配置块参数
            if line_str.startswith(";"):
                # 首层与非首层喷嘴温度
                if "noz_first" not in config and "nozzle_temperature_initial_layer" in line_str:
                    m = re.search(r"nozzle_temperature_initial_layer\s*=\s*([0-9.]+)", line_str)
                    if m: config["noz_first"] = float(m.group(1))

                if "noz_other" not in config and re.search(r"^\s*;\s*nozzle_temperature\s*=\s*([0-9.]+)", line_str):
                    m = re.search(r"nozzle_temperature\s*=\s*([0-9.]+)", line_str)
                    if m: config["noz_other"] = float(m.group(1))

                # 首层与非首层热床温度
                if "bed_first" not in config and "hot_plate_temp_initial_layer" in line_str:
                    m = re.search(r"hot_plate_temp_initial_layer\s*=\s*([0-9.]+)", line_str)
                    if m: config["bed_first"] = float(m.group(1))

                if "bed_other" not in config and re.search(r"^\s*;\s*hot_plate_temp\s*=\s*([0-9.]+)", line_str):
                    m = re.search(r"hot_plate_temp\s*=\s*([0-9.]+)", line_str)
                    if m: config["bed_other"] = float(m.group(1))

                # 层高（首层与后续层）
                if "h_first" not in config and "initial_layer_print_height" in line_str:
                    m = re.search(r"initial_layer_print_height\s*=\s*([0-9.]+)", line_str)
                    if m: config["h_first"] = float(m.group(1))

                if "h_std" not in config and re.search(r"^\s*;\s*layer_height\s*=\s*([0-9.]+)", line_str):
                    m = re.search(r"layer_height\s*=\s*([0-9.]+)", line_str)
                    if m: config["h_std"] = float(m.group(1))

                # 线宽（首层、普通层、顶层）
                if "w_first" not in config and "initial_layer_line_width" in line_str:
                    m = re.search(r"initial_layer_line_width\s*=\s*([0-9.]+)", line_str)
                    if m: config["w_first"] = float(m.group(1))

                if "w_top" not in config and "top_surface_line_width" in line_str:
                    m = re.search(r"top_surface_line_width\s*=\s*([0-9.]+)", line_str)
                    if m: config["w_top"] = float(m.group(1))

                if "w_std" not in config and re.search(r"^\s*;\s*line_width\s*=\s*([0-9.]+)", line_str):
                    m = re.search(r"line_width\s*=\s*([0-9.]+)", line_str)
                    if m: config["w_std"] = float(m.group(1))

    total_layers = total_layers_cfg or len(layer_z_list) or 0

    # 构建基础字典
    data = {
        "nozzle_temp": config.get("noz_first") or config.get("noz_other"),
        "bed_temp": config.get("bed_first") or config.get("bed_other"),
        "layer_h": config.get("h_std") or config.get("h_first"),
        "line_w": config.get("w_first") or config.get("w_std"),
        "total_layers": total_layers,
        "first_z": config.get("h_first") or (layer_z_list[0] if layer_z_list else None)
    }

    # 当层数大于 1 时追加最后一层信息
    if total_layers > 1:
        data["last_z"] = config.get("max_z") or (layer_z_list[-1] if layer_z_list else None)
        data["last_noz_temp"] = config.get("noz_other") or data["nozzle_temp"]
        data["last_bed_temp"] = config.get("bed_other") or data["bed_temp"]
        data["last_layer_h"] = config.get("h_std") or data["layer_h"]
        data["last_line_w"] = config.get("w_top") or config.get("w_std") or data["line_w"]

    return data