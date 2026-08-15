import sys;'qgb.U' in sys.modules or sys.path.append('C:/QGB/Anaconda3/Lib/site-packages/Pythonwin/')
import sys;'qgb.U' in sys.modules or sys.path.append('C:/QGB/miniforge3/Lib/site-packages/pythonwin/');from qgb import *
import os,sys,json,shutil,re
import subprocess
import zipfile
import tempfile
import cadquery as cq
# ==================== 后台固定的默认环境配置 ====================
DEFAULT_BAMBU_EXE = r"D:\Bambu Studio\bambu-studio.exe"
DEFAULT_MACHINE_JSON = r"C:\Users\Administrator\AppData\Roaming\BambuStudio\user\1154792620\machine\Elegoo Neptune 4 0.2 nozzle - 拷贝.json"
DEFAULT_FILAMENT_JSON = r"C:\Users\Administrator\AppData\Roaming\BambuStudio\user\1154792620\filament\66-55.json"
DEFAULT_PROCESS_JSON = r"C:\Users\Administrator\AppData\Roaming\BambuStudio\user\1154792620\process\填充44  skirt5.json"

# ==================== 修正后的材质参数预设库 解决 M140 S35 问题  ====================
MATERIAL_PRESETS_base = {  # TODO: ABS, TPU 只需增加条目
    "PLA": {
        "filament_type": "PLA",
        "nozzle_temperature": 205,
        "nozzle_temperature_initial_layer": 205,
        "bed_temp": 60,
        "bed_temp_initial_layer": 65,
        "fan_max_speed": 100,
        "fan_min_speed": 100,
        "close_fan_the_first_x_layers": 1
    },
    "PETG": {
        "filament_type": "PETG",
        "nozzle_temperature": 235,
        "nozzle_temperature_initial_layer": 238,
        "bed_temp": 65,
        "bed_temp_initial_layer": 70,
        "fan_max_speed": 50,
        "fan_min_speed": 20,
        "close_fan_the_first_x_layers": 3
    }
}
MATERIAL_PRESETS = {
    mat: {
        "filament_type": [c["filament_type"]],
        "nozzle_temperature": [str(c["nozzle_temperature"])],
        "nozzle_temperature_initial_layer": [str(c["nozzle_temperature_initial_layer"])],
        "hot_plate_temp": [str(c["bed_temp"])],
        "hot_plate_temp_initial_layer": [str(c["bed_temp_initial_layer"])],
        "textured_plate_temp": [str(c["bed_temp"])],
        "textured_plate_temp_initial_layer": [str(c["bed_temp_initial_layer"])],
        "cool_plate_temp": [str(c["bed_temp"])],
        "cool_plate_temp_initial_layer": [str(c["bed_temp_initial_layer"])],
        "eng_plate_temp": [str(c["bed_temp"])],
        "eng_plate_temp_initial_layer": [str(c["bed_temp_initial_layer"])],
        "fan_max_speed": [str(c["fan_max_speed"])],
        "fan_min_speed": [str(c["fan_min_speed"])],
        "close_fan_the_first_x_layers": [str(c["close_fan_the_first_x_layers"])],
    }
    for mat, c in MATERIAL_PRESETS_base.items()
}

MATERIAL_PRESETS = {
    mat: {
        **{k: [str(v)] for k, v in c.items() if k not in ["bed_temp","bed_temp_initial_layer"]},
        **{k: [str(c["bed_temp"])] for k in ("hot_plate_temp", "textured_plate_temp", "cool_plate_temp", "eng_plate_temp")},
        **{k: [str(c["bed_temp_initial_layer"])] for k in ("hot_plate_temp_initial_layer", "textured_plate_temp_initial_layer", "cool_plate_temp_initial_layer", "eng_plate_temp_initial_layer")}
    }
    for mat, c in MATERIAL_PRESETS_base.items()
}




def _preprocess_dependent_json(src_path, safe_name, type_tag, model_token, overrides=None):
    """内部函数：用于工艺和耗材配置文件的强行兼容性对齐及参数覆写（升级通用覆写逻辑）"""
    try:
        with open(src_path, 'r', encoding='utf-8-sig') as f:
            config_data = json.load(f)
        
        config_data['type'] = type_tag
        config_data["compatible_printers"] = [model_token]
        
        config_data.pop("compatible_printers_condition", None)
        config_data.pop("compatible_prints_condition", None)
        config_data.pop("compatible_filaments_condition", None)
        
        # 核心改动：注入通用覆盖参数（自动适配原配置文件中的 列表/单值 结构）
        if overrides and isinstance(overrides, dict):
            for key, val in overrides.items():
                # 判断配置文件中原有的数据类型
                if key in config_data and isinstance(config_data[key], list):
                    config_data[key] = [str(x) for x in val] if isinstance(val, list) else [str(val)]
                else:
                    config_data[key] = str(val[0]) if isinstance(val, list) else str(val)
        
        tmp_dest = os.path.join(tempfile.gettempdir(), safe_name)
        with open(tmp_dest, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, ensure_ascii=False, indent=4)
        return tmp_dest
    except Exception as e:
        print(f"[ERROR] 强制对齐配置失败 [{safe_name}]: {e}")
        raise e

def to_gcode(cq_object,name="cq_model", output_dir=None, layer_height="0.3mm", material="PLA", printer_name="Elegoo Neptune 4",add_brim=0):
    """
    封装切片流程：转换模型、调用拓竹引擎切片、解压 G-code 并自动分析日志与打印时间
    """
    # 1. 解析层高
    lh_str = f"{float(m.group()):g}" if (m := re.search(r"\d+\.?\d*", str(layer_height))) else "0.2"
    
    # 2. 自动提取纯文件名
    clean_name = os.path.basename(name)
    if clean_name.lower().endswith(('.step', '.solid', '.stl', '.py')):
        clean_name = os.path.splitext(clean_name)[0]

    if output_dir is None:
        output_dir = os.getcwd()
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 3. 匹配材质预设参数
    mat_key = material.strip().upper()
    material_overrides = MATERIAL_PRESETS.get(mat_key, MATERIAL_PRESETS["PETG"])
    print(f"[INFO] 正在应用材质配置: {mat_key} -> 喷嘴首层 {material_overrides['nozzle_temperature_initial_layer'][0]}℃, 热床首层 {material_overrides['hot_plate_temp_initial_layer'][0]}℃")

    # 4. 解析机型并修正软控起步温度

    try:
        with open(DEFAULT_MACHINE_JSON, 'r', encoding='utf-8-sig') as f:
            machine_data = json.load(f)
        print(f"[INFO] printer_model = {machine_data.get('printer_model')!r}")
        print(f"[INFO] inherits = {machine_data.get('inherits')!r}")
        print(f"[INFO] printable_area = {machine_data.get('printable_area')!r}")
        print(f"[INFO] bed_exclude_area = {machine_data.get('bed_exclude_area')!r}")
        
        printer_model_token = machine_data.get("printer_model") or machine_data.get("inherits") or "Elegoo Neptune 4 0.2 nozzle"
        machine_data["printer_model"] = printer_model_token
        machine_data["type"] = "machine"
        
        if "machine_start_gcode" in machine_data:
            start_gcode = machine_data["machine_start_gcode"]
            start_gcode = re.sub(r'M140\s+S\d+', 'M140 S[bed_temperature_initial_layer_single]', start_gcode)
            start_gcode = re.sub(r'M104\s+S\d+', 'M104 S[nozzle_temperature_initial_layer]', start_gcode)
            machine_data["machine_start_gcode"] = start_gcode

        safe_machine = os.path.join(tempfile.gettempdir(), "cli_machine.json")
        with open(safe_machine, 'w', encoding='utf-8') as f:
            json.dump(machine_data, f, ensure_ascii=False, indent=4)
        print(f"[INFO] 成功锁定机型兼容锚点: {printer_model_token}")
    except Exception as e:
        print(f"[ERROR] 提取机型锚点失败: {e}")
        return None

    # 5. 对齐工艺与耗材
    print("[INFO] 正在对工艺和耗材配置文件执行强行兼容性对齐及层高/材质参数注入...")
    process_overrides = {"layer_height": lh_str}
    
    safe_process = _preprocess_dependent_json(
        DEFAULT_PROCESS_JSON, 
        "cli_process.json", 
        "process", 
        printer_model_token,
        overrides=process_overrides
    )
    safe_filament = _preprocess_dependent_json(
        DEFAULT_FILAMENT_JSON, 
        "cli_filament.json", 
        "filament", 
        printer_model_token,
        overrides=material_overrides
    )
    print("[INFO] 配置文件闭环清洗完毕，安全沙盒映射成功。")

    # 6. 中转路径与 STL 导出
    temp_stl = os.path.join(tempfile.gettempdir(), f"bambu_cli_temp_{clean_name}.stl")
    temp_3mf = os.path.join(tempfile.gettempdir(), f"bambu_cli_temp_{clean_name}.3mf")

    print("[STEP 1] 正在将 CadQuery/build123d 对象直接转换为高精度 STL 网格...")
    try:
        if hasattr(cq_object, "part"):
            from build123d import export_stl as b3d_export_stl
            b3d_export_stl(cq_object.part, temp_stl, tolerance=0.01)
        elif hasattr(cq_object, "val"):
            shape_to_export = cq_object.val()
            cq.exporters.export(shape_to_export, temp_stl, tolerance=0.01)
        else:
            cq.exporters.export(cq_object, temp_stl, tolerance=0.01)

        print("   -> [INFO] STL 内存网格转换成功！")
    except Exception as e:
        print(f"[ERROR] 导出 STL 失败: {e}")
        return None

    # 7. 调用拓竹切片引擎
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

    # 8. 提取 G-code 并自动解析分析参数
    print("[STEP 3] 切片成功，正在从 3MF 数据包中解压并提取纯 G-code...")
    temp_extracted_gcode = os.path.join(tempfile.gettempdir(), f"temp_{clean_name}.gcode")

    if os.path.exists(temp_3mf):
        try:
            with zipfile.ZipFile(temp_3mf, 'r') as zip_ref:
                gcode_in_zip = "Metadata/plate_1.gcode"
                if gcode_in_zip in zip_ref.namelist():
                    with zip_ref.open(gcode_in_zip) as source, open(temp_extracted_gcode, 'wb') as target:
                        shutil.copyfileobj(source, target)

                    # 分析临时 G-code，提取打印时间与格式化参数字符串
                    gcode_info = analyze_gcode(temp_extracted_gcode) #analyze_gcode 已经定义，不用生成这个函数
                    print_time = gcode_info["print_time"]# 出错直接退出，因为不应该出错

                    # 重命名保存至最终输出路径
                    output_gcode_name = f"{clean_name}_{lh_str}mm_{material}_{printer_name}_{print_time}.gcode"
                    final_gcode_path = os.path.join(output_dir, output_gcode_name)
                    shutil.move(temp_extracted_gcode, final_gcode_path)

                    # 输出分析结果与路径
                    print(gcode_info["print_str"], '\n', f"路径 {final_gcode_path}")
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
            if os.path.exists(temp_extracted_gcode): os.remove(temp_extracted_gcode)
            print("   -> [INFO] 清理完毕。")
    else:
        print("[ERROR] 未找到生成的临时 3mf 文件。")
        return None 
        
########################

def import_stl_ocp(file_path: str) -> cq.Shape:
    ''' STL 导入出来是 Shell，不能做 union/cut/fuse 布尔运算，CadQuery/OCCT 布尔操作只支持 Solid。 '''
    from OCP.StlAPI import StlAPI_Reader
    from OCP.TopoDS import TopoDS_Shape
    # import cadquery as cq
    ocp_shape = TopoDS_Shape()
    reader = StlAPI_Reader()
    reader.Read(ocp_shape, file_path)
    return cq.Shape(ocp_shape)
import_stl=cadquery_import_stl=import_stl_ocp
    
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
#

import cadquery as cq
import traceback

def add_brim(obj, extend=5.0, thickness=0.4, overlap=0.5):
    """
    【终极调试与破局版：彻底放弃 Union 融合，改用 Compound 组合】
    包含详细打印日志，方便定位任何几何计算异常。
    """
    print("\n" + "="*60)
    print("🛠️ [Brim Debug] 开始执行异形裙边生成逻辑...")
    print("="*60)
    
    # ==========================================
    # 1. 智能类型转换机制
    # ==========================================
    is_shape_input = isinstance(obj, cq.Shape)
    if is_shape_input:
        wp = cq.Workplane("XY").add(obj)
        base_shape = obj
    elif isinstance(obj, cq.Workplane):
        wp = obj
        base_shape = obj.val()
    else:
        try:
            base_shape = cq.Shape(obj.wrapped)
            wp = cq.Workplane("XY").add(base_shape)
            is_shape_input = True 
        except Exception:
            print("❌ [Brim Debug] 无法识别输入对象类型！")
            return obj

    print(f"✅ [Brim Debug] 步骤1: 原始模型解析成功，体积: {base_shape.Volume():.2f} mm³")

    try:
        # ==========================================
        # 2. 提取最外圈轮廓
        # ==========================================
        bbox = base_shape.BoundingBox()
        zmin = bbox.zmin
        print(f"📊 [Brim Debug] 步骤2: 包围盒 Zmin 基准 = {zmin:.3f} mm")

        # 获取所有指向底部的面
        bottom_faces = wp.faces("<Z").vals()
        print(f"🔎 [Brim Debug] 步骤2: 共提取到 {len(bottom_faces)} 个底部平面")
        
        if len(bottom_faces) == 0:
            raise ValueError("未找到任何底部平面！")

        # 防御性编程：如果底面有多个（比如倒角导致的碎面），取面积最大的那个
        largest_face = max(bottom_faces, key=lambda f: f.Area())
        outer_wire = largest_face.outerWire()
        print(f"✅ [Brim Debug] 步骤2: 成功提取最大底面的最外圈轮廓 (Wire)")

        # ==========================================
        # 3. 构造 3D 重叠裙边
        # ==========================================
        print(f"⚙️ [Brim Debug] 步骤3: 正在向外扩展 {extend}mm, 向内咬合 {overlap}mm...")
        
        outer_solid_wp = (
            cq.Workplane("XY", origin=(0, 0, zmin))
            .add(outer_wire)
            .toPending()
            .offset2D(extend, kind="arc")
            .extrude(thickness)
        )
        print(f"✅ [Brim Debug] 步骤3: 外圈拉伸成功，体积: {outer_solid_wp.val().Volume():.2f} mm³")

        inner_solid_wp = (
            cq.Workplane("XY", origin=(0, 0, zmin))
            .add(outer_wire)
            .toPending()
            .offset2D(-overlap, kind="arc") 
            .extrude(thickness)
        )
        print(f"✅ [Brim Debug] 步骤3: 内圈(掏空基准)拉伸成功，体积: {inner_solid_wp.val().Volume():.2f} mm³")

        brim_frame = outer_solid_wp.cut(inner_solid_wp)
        brim_shape = brim_frame.val()
        print(f"✅ [Brim Debug] 步骤3: 布尔切割(外-内)成功！生成的裙边体积: {brim_shape.Volume():.2f} mm³")

        # ==========================================
        # 4. 破局核心：使用 Compound (组合) 替代 Union (融合)
        # ==========================================
        print(f"🔗 [Brim Debug] 步骤4: 绕过底层 Union 拓扑漏洞，将两者打包为 Compound...")
        
        # 将原始模型和生成的裙边强行“放进同一个组”中，不做网格和面的合并
        compound_shape = cq.Compound.makeCompound([base_shape, brim_shape])
        
        print(f"🎉 [Brim Debug] 步骤4: Compound 打包成功！总组合体积: {compound_shape.Volume():.2f} mm³")
        print("="*60 + "\n")
        
        # 恢复输出类型
        return compound_shape if is_shape_input else cq.Workplane("XY").add(compound_shape)

    except Exception as e:
        # ==========================================
        # 5. 详细的报错捕获与降级
        # ==========================================
        print(f"❌ [Brim Debug] 发生异常: {str(e)}")
        traceback.print_exc()  # 打印完整堆栈，方便你我定位到底错在哪一行
        print(f"⚠️ [Brim Debug] 已触发降级机制：退回使用 BoundingBox 矩形裙边...")
        print("="*60 + "\n")
        return add_brim_bounding_box(obj, extend, thickness, base_shape)


def add_brim_bounding_box(obj, extend, thickness, base_shape):
    """【绝对安全兜底版】基于 BoundingBox 生成标准矩形外接裙边，同样使用 Compound"""
    bbox = base_shape.BoundingBox()
    zmin = bbox.zmin

    rect_w = (bbox.xmax - bbox.xmin) + 2 * extend
    rect_h = (bbox.ymax - bbox.ymin) + 2 * extend
    cx = (bbox.xmin + bbox.xmax) / 2.0
    cy = (bbox.ymin + bbox.ymax) / 2.0

    brim_plate = (
        cq.Workplane("XY", origin=(cx, cy, zmin))
        .rect(rect_w, rect_h)
        .extrude(thickness)
    )

    # 兜底函数同样不再使用 union，使用组合
    compound_shape = cq.Compound.makeCompound([base_shape, brim_plate.val()])
    return compound_shape if isinstance(obj, cq.Shape) else cq.Workplane("XY").add(compound_shape)



    

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
        
        
        
        

def ensure_z_offset(target_z=-2.4, printer_ip="192.168.1.113", printer_port=7125):
    """
    确保打印机的 Z 轴偏移值达到目标精度，不满足则动态调整
    """
    import time,requests
    from urllib.parse import quote

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
    解析 G-code 文件，提取切片参数及打印预估时间。
    返回包含各个参数的字典，其中 dict['print_str'] 用于对齐格式化输出。
    """
    if not os.path.exists(gcode_path):
        print(f"[ERROR] 文件不存在: {gcode_path}")
        return None

    config = {}
    layer_z_list = []
    total_layers_cfg = 0
    print_time = "unknowntime"

    with open(gcode_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line_str = line.strip()

            # 提取预计打印时间
            if print_time == "unknowntime":
                m_time = re.search(r';\s*(?:estimated printing time|total estimated time)\s*(?:\([^)]*\))?\s*=\s*([^\r\n]+)', line_str, re.IGNORECASE)
                if m_time:
                    raw_time = m_time.group(1).strip()
                    clean_time = re.sub(r'\s+', '', raw_time)
                    if clean_time:
                        print_time = clean_time
                else:
                    m73_match = re.search(r'M73\s+P0\s+R(\d+)', line_str)
                    if m73_match:
                        mins = int(m73_match.group(1))
                        h, m = divmod(mins, 60)
                        print_time = f"{h}h{m}m" if h > 0 else f"{m}m"

            # 总层数
            if total_layers_cfg == 0:
                m_tot = re.search(r"^;\s*total layer number:\s*(\d+)", line_str, re.IGNORECASE)
                if m_tot:
                    total_layers_cfg = int(m_tot.group(1))

            # 收集 Z_HEIGHT
            m_z = re.search(r"^;\s*Z_HEIGHT:\s*([0-9.]+)", line_str, re.IGNORECASE)
            if m_z:
                layer_z_list.append(float(m_z.group(1)))

            # 最大 Z 高度
            if "max_z" not in config:
                m_max_z = re.search(r"^;\s*max_z_height:\s*([0-9.]+)", line_str, re.IGNORECASE)
                if m_max_z:
                    config["max_z"] = float(m_max_z.group(1))

            # 参数提取（注释行）
            if line_str.startswith(";"):
                # 喷嘴温度
                if "noz_first" not in config and "nozzle_temperature_initial_layer" in line_str:
                    m = re.search(r"nozzle_temperature_initial_layer\s*=\s*([0-9.]+)", line_str)
                    if m: config["noz_first"] = float(m.group(1))
                if "noz_other" not in config and re.search(r"^\s*;\s*nozzle_temperature\s*=\s*([0-9.]+)", line_str):
                    m = re.search(r"nozzle_temperature\s*=\s*([0-9.]+)", line_str)
                    if m: config["noz_other"] = float(m.group(1))

                # 热床温度
                if "bed_first" not in config and "hot_plate_temp_initial_layer" in line_str:
                    m = re.search(r"hot_plate_temp_initial_layer\s*=\s*([0-9.]+)", line_str)
                    if m: config["bed_first"] = float(m.group(1))
                if "bed_other" not in config and re.search(r"^\s*;\s*hot_plate_temp\s*=\s*([0-9.]+)", line_str):
                    m = re.search(r"hot_plate_temp\s*=\s*([0-9.]+)", line_str)
                    if m: config["bed_other"] = float(m.group(1))

                # 层高
                if "h_first" not in config and "initial_layer_print_height" in line_str:
                    m = re.search(r"initial_layer_print_height\s*=\s*([0-9.]+)", line_str)
                    if m: config["h_first"] = float(m.group(1))
                if "h_std" not in config and re.search(r"^\s*;\s*layer_height\s*=\s*([0-9.]+)", line_str):
                    m = re.search(r"layer_height\s*=\s*([0-9.]+)", line_str)
                    if m: config["h_std"] = float(m.group(1))

                # 线宽
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

    first_layer = {
        "#": "firs",
        "nozzle_temp": config.get("noz_first") or config.get("noz_other"),
        "bed_temp": config.get("bed_first") or config.get("bed_other"),
        "layer_h": config.get("h_first") or config.get("h_std"),
        "line_w": config.get("w_first") or config.get("w_std"),
        "z": config.get("h_first") or (layer_z_list[0] if layer_z_list else None),
        "total_layers": total_layers,
        "print_time": print_time
    }

    if total_layers <= 1:
        last_layer = None
        layers_list = [first_layer]
    else:
        last_layer = {
            "#": "last",
            "nozzle_temp": config.get("noz_other") or first_layer["nozzle_temp"],
            "bed_temp": config.get("bed_other") or first_layer["bed_temp"],
            "layer_h": config.get("h_std") or first_layer["layer_h"],
            "line_w": config.get("w_top") or config.get("w_std") or first_layer["line_w"],
            "z": config.get("max_z") or (layer_z_list[-1] if layer_z_list else None),
        }
        layers_list = [first_layer, last_layer]

    # 构建紧凑格式化字符串（统一单空格分隔，消除异常大间隙）
    lines = []
    for d in layers_list:
        parts = [
            d["#"],
            f"noz={d['nozzle_temp']}",
            f"bed={d['bed_temp']}",
            f"Lh={d['layer_h']}mm",
            f"w={d['line_w']}mm",
            f"z={d['z']}mm",
        ]
        if d["#"] == "firs":
            parts.append(f"Ln={d['total_layers']}")
            parts.append(f"{d['print_time']}")
        lines.append(" ".join(parts))

    print_str = "\n".join(lines)

    return {
        "print_str": print_str,
        "print_time": print_time,
        "total_layers": total_layers,
        "first_layer": first_layer,
        "last_layer": last_layer,
        "config": config
    }

