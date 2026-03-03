"""
AUTOSAR SWC Generator from Excel
根据Excel文件生成AUTOSAR软件组件描述文件
"""
import os
import pandas as pd
import autosar
import autosar.xml.element as ar_element
import autosar.xml.workspace as ar_workspace


def create_package_map(workspace: ar_workspace.Workspace):
    """
    在工作空间中创建包映射
    """
    workspace.create_package_map({
        "PlatformBaseTypes": "AUTOSAR_Platform/BaseTypes",
        "PlatformImplementationDataTypes": "AUTOSAR_Platform/ImplementationDataTypes",
        "PlatformDataConstraints": "AUTOSAR_Platform/DataConstraints",
        "PlatformCompuMethods": "AUTOSAR_Platform/CompuMethods",
        "Constants": "Constants",
        "PortInterfaces": "PortInterfaces",
        "ComponentTypes": "ComponentTypes"
    })


def init_behavior_settings(workspace: ar_workspace.Workspace):
    """
    定义默认事件名称前缀
    """
    workspace.behavior_settings.update({
        "background_event_prefix": "BT",
        "data_receive_error_event_prefix": "DRET",
        "data_receive_event_prefix": "DRT",
        "init_event_prefix": "IT",
        "operation_invoked_event_prefix": "OIT",
        "swc_mode_manager_error_event_prefix": "MMET",
        "swc_mode_switch_event_prefix": "MST",
        "timing_event_prefix": "TMT",
        "data_send_point_prefix": "SEND",
        "data_receive_point_prefix": "REC"
    })


def create_platform_types(workspace: ar_workspace.Workspace):
    """
    创建必要的平台数据类型
    """
    # 创建基础类型
    boolean_base_type = ar_element.SwBaseType('boolean', size=8, encoding="BOOLEAN")
    workspace.add_element("PlatformBaseTypes", boolean_base_type)
    
    uint8_base_type = ar_element.SwBaseType('uint8', size=8)
    workspace.add_element("PlatformBaseTypes", uint8_base_type)
    
    uint16_base_type = ar_element.SwBaseType('uint16', size=16)
    workspace.add_element("PlatformBaseTypes", uint16_base_type)
    
    uint32_base_type = ar_element.SwBaseType('uint32', size=32)
    workspace.add_element("PlatformBaseTypes", uint32_base_type)

    float32_base_type = ar_element.SwBaseType('float32', size=32, encoding="IEEE754")
    workspace.add_element("PlatformBaseTypes", float32_base_type)

    # 创建数据约束
    boolean_data_constr = ar_element.DataConstraint.make_internal("boolean_DataConstr", 0, 1)
    workspace.add_element("PlatformDataConstraints", boolean_data_constr)
    
    # 创建计算方法
    computation = ar_element.Computation.make_value_table(["FALSE", "TRUE"])
    boolean_compu_method = ar_element.CompuMethod(name="boolean_CompuMethod",
                                                  category="TEXTTABLE",
                                                  int_to_phys=computation)
    workspace.add_element("PlatformCompuMethods", boolean_compu_method)
    
    # 创建实现数据类型
    sw_data_def_props = ar_element.SwDataDefPropsConditional(
        base_type_ref=boolean_base_type.ref(),
        data_constraint_ref=boolean_data_constr.ref(),
        compu_method_ref=boolean_compu_method.ref()
    )
    boolean_impl_type = ar_element.ImplementationDataType("boolean",
                                                          category="VALUE",
                                                          sw_data_def_props=sw_data_def_props)
    workspace.add_element("PlatformImplementationDataTypes", boolean_impl_type)
    
    sw_data_def_props = ar_element.SwDataDefPropsConditional(base_type_ref=uint8_base_type.ref())
    uint8_impl_type = ar_element.ImplementationDataType("uint8",
                                                        category="VALUE",
                                                        sw_data_def_props=sw_data_def_props)
    workspace.add_element("PlatformImplementationDataTypes", uint8_impl_type)
    
    sw_data_def_props = ar_element.SwDataDefPropsConditional(base_type_ref=uint16_base_type.ref())
    uint16_impl_type = ar_element.ImplementationDataType("uint16",
                                                         category="VALUE",
                                                         sw_data_def_props=sw_data_def_props)
    workspace.add_element("PlatformImplementationDataTypes", uint16_impl_type)
    
    sw_data_def_props = ar_element.SwDataDefPropsConditional(base_type_ref=uint32_base_type.ref())
    uint32_impl_type = ar_element.ImplementationDataType("uint32",
                                                         category="VALUE",
                                                         sw_data_def_props=sw_data_def_props)
    workspace.add_element("PlatformImplementationDataTypes", uint32_impl_type)

    sw_data_def_props = ar_element.SwDataDefPropsConditional(base_type_ref=float32_base_type.ref())
    float32_impl_type = ar_element.ImplementationDataType("float32",
                                                          category="VALUE",
                                                          sw_data_def_props=sw_data_def_props)
    workspace.add_element("PlatformImplementationDataTypes", float32_impl_type)


def create_data_type(workspace: ar_workspace.Workspace, data_type_name: str, struct_types=None):
    """
    根据数据类型名称创建对应的实现数据类型引用
    支持基本类型和结构体类型
    """
    data_type_map = {
        'uint8': 'uint8',
        'uint16': 'uint16',
        'uint32': 'uint32',
        'float32': 'float32',
        'boolean': 'boolean'
    }

    # 先查基本类型
    if data_type_name.lower() in data_type_map:
        impl_type_name = data_type_map[data_type_name.lower()]
        return workspace.find_element("PlatformImplementationDataTypes", impl_type_name)

    # 再查结构体类型
    if struct_types and data_type_name in struct_types:
        return struct_types[data_type_name]

    # 尝试在包中直接查找
    result = workspace.find_element("PlatformImplementationDataTypes", data_type_name)
    if result is not None:
        return result

    # 默认回退到 uint8
    print(f"Warning: Data type '{data_type_name}' not found, using uint8 as default")
    return workspace.find_element("PlatformImplementationDataTypes", 'uint8')


def create_senderreceiver_interface(workspace: ar_workspace.Workspace, interface_name: str, element_name: str, data_type: str, struct_types=None):
    """
    创建发送接收接口
    """
    # 检查接口是否已存在
    existing_interface = workspace.find_element("PortInterfaces", interface_name)
    if existing_interface is not None:
        return existing_interface

    # 获取数据类型
    impl_type = create_data_type(workspace, data_type, struct_types)
    if impl_type is None:
        print(f"Warning: Data type {data_type} not found, using uint8 as default")
        impl_type = workspace.find_element("PlatformImplementationDataTypes", "uint8")
    
    # 创建发送接收接口
    port_interface = ar_element.SenderReceiverInterface(interface_name)
    port_interface.create_data_element(element_name, type_ref=impl_type.ref())
    workspace.add_element("PortInterfaces", port_interface)
    
    return port_interface

def create_clientserver_interface(workspace: ar_workspace.Workspace, interface_name: str, operation_name: str, data_type: str, struct_types=None, csop_defs=None):
    """
    创建ClientServer接口
    如果接口已存在，则向其添加新的operation
    当 csop_defs 中有 (interface_name, operation_name) 的自定义参数时使用自定义参数，
    否则使用固定的 invalue/outvalue（向后兼容）
    """
    import autosar.xml.enumeration as ar_enum

    # 检查接口是否已存在
    existing_interface = workspace.find_element("PortInterfaces", interface_name)

    if existing_interface is not None:
        # 接口已存在，添加新的operation
        portinterface = existing_interface
    else:
        # 创建新的ClientServer接口
        portinterface = ar_element.ClientServerInterface(interface_name, is_service=False)

    # 创建operation
    operation = portinterface.create_operation(operation_name)

    # 查找是否有自定义参数定义
    custom_args = None
    if csop_defs:
        custom_args = csop_defs.get((interface_name, operation_name))

    if custom_args:
        # 使用自定义参数
        for arg in custom_args:
            arg_type = create_data_type(workspace, arg['arg_type'], struct_types)
            if arg_type is None:
                print(f"Warning: Data type '{arg['arg_type']}' not found for argument '{arg['arg_name']}', using uint8")
                arg_type = workspace.find_element("PlatformImplementationDataTypes", "uint8")

            direction = arg['arg_direction']
            if direction == 'IN':
                operation.create_in_argument(arg['arg_name'],
                                             ar_enum.ServerArgImplPolicy.USE_ARGUMENT_TYPE,
                                             type_ref=arg_type.ref())
            elif direction == 'OUT':
                operation.create_out_argument(arg['arg_name'],
                                              ar_enum.ServerArgImplPolicy.USE_ARGUMENT_TYPE,
                                              type_ref=arg_type.ref())
            elif direction == 'INOUT':
                operation.create_inout_argument(arg['arg_name'],
                                                ar_enum.ServerArgImplPolicy.USE_ARGUMENT_TYPE,
                                                type_ref=arg_type.ref())
            else:
                print(f"Warning: Unknown argument direction '{direction}' for '{arg['arg_name']}', skipping")
    else:
        # 固定 invalue/outvalue（向后兼容）
        impl_type = create_data_type(workspace, data_type, struct_types)
        if impl_type is None:
            print(f"Warning: Data type {data_type} not found, using uint8 as default")
            impl_type = workspace.find_element("PlatformImplementationDataTypes", "uint8")

        operation.create_out_argument("outvalue",
                                     ar_enum.ServerArgImplPolicy.USE_ARGUMENT_TYPE,
                                     type_ref=impl_type.ref())
        operation.create_in_argument("invalue",
                                    ar_enum.ServerArgImplPolicy.USE_ARGUMENT_TYPE,
                                    type_ref=impl_type.ref())

    # 如果是新创建的接口，添加到工作空间
    if existing_interface is None:
        workspace.add_element("PortInterfaces", portinterface)

    return portinterface


def create_port(swc: ar_element.ApplicationSoftwareComponentType, port_name: str, interface_ref, 
                direction: str, init_value_ref=None):
    """
    创建SenderReceiver类型的端口（提供端口或需求端口）
    """
    com_spec = {}
    if init_value_ref:
        com_spec["init_value"] = init_value_ref
    com_spec["uses_end_to_end_protection"] = False
    
    if direction.lower() == 'provide':
        return swc.create_provide_port(port_name, interface_ref, com_spec=com_spec)
    elif direction.lower() == 'require':
        return swc.create_require_port(port_name, interface_ref, com_spec=com_spec)
    else:
        raise ValueError(f"Unknown direction: {direction}")


def create_clientserver_port(swc: ar_element.ApplicationSoftwareComponentType, port_name: str,
                             interface_ref, direction: str, operation_names):
    """
    创建ClientServer类型的端口（提供端口或需求端口）
    支持单个或多个operation
    """
    if isinstance(operation_names, str):
        operation_names = [operation_names]

    interface = interface_ref
    com_specs = []

    for operation_name in operation_names:
        operation = None
        if hasattr(interface, 'operations') and interface.operations:
            for op in interface.operations:
                if op.name == operation_name:
                    operation = op
                    break

        if operation is None:
            raise ValueError(f"Operation '{operation_name}' not found in interface '{interface.name}'")

        operation_ref = operation.ref()
        if operation_ref is None:
            raise ValueError(f"Operation '{operation_name}' reference is None. Make sure the interface is added to workspace first.")

        if direction.lower() == 'provide':
            com_specs.append(ar_element.ServerComSpec(operation_ref=operation_ref))
        elif direction.lower() == 'require':
            com_specs.append(ar_element.ClientComSpec(operation_ref=operation_ref))
        else:
            raise ValueError(f"Unknown direction: {direction}")

    if direction.lower() == 'provide':
        return swc.create_provide_port(port_name, interface_ref, com_spec=com_specs)
    elif direction.lower() == 'require':
        return swc.create_require_port(port_name, interface_ref, com_spec=com_specs)


def create_runnable(behavior, runnable_name: str, port_names: list):
    """
    创建可运行实体
    """
    runnable = behavior.create_runnable(runnable_name,
                                        can_be_invoked_concurrently=False,
                                        minimum_start_interval=0)
    if port_names:
        runnable.create_port_access(port_names)
    return runnable


def create_access_points(behavior, port_names: list):
    """
    创建访问点
    """
    if port_names:
        behavior.create_port_api_options("*", enable_take_address=False, indirect_api=False)


def _build_struct_init_value(struct_name, struct_defs):
    """
    递归构建结构体的 RecordValueSpecification 初始值
    每个成员默认为 0
    """
    members = struct_defs[struct_name]
    fields = []

    for member in members:
        member_name = member['member_name']
        member_type = member['member_type']

        if member_type.lower() in PRIMITIVE_TYPES:
            field = ar_element.NumericalValueSpecification(label=member_name, value=0)
        elif member_type in struct_defs:
            field = _build_struct_init_value(member_type, struct_defs)
        else:
            field = ar_element.NumericalValueSpecification(label=member_name, value=0)

        fields.append(field)

    return ar_element.RecordValueSpecification(fields=fields)


def create_constants(workspace: ar_workspace.Workspace, interface_data: dict, struct_defs=None):
    """
    创建常量规范（初始值）
    仅为SenderReceiver接口创建常量
    支持基本类型和结构体类型
    """
    for interface_name, info in interface_data.items():
        # ClientServer接口不需要初始值常量
        if info['interface_type'].strip().lower() == 'clientserver':
            continue

        for elem in info['elements']:
            element_name = elem['element_name']
            data_type = elem['data_type']

            constant_name = f"{element_name}_IV"

            if struct_defs and data_type in struct_defs:
                # 结构体类型：构建 RecordValueSpecification
                init_value = _build_struct_init_value(data_type, struct_defs)
                constant = ar_element.ConstantSpecification(constant_name, init_value)
            else:
                # 基本类型：数值 0
                constant = ar_element.ConstantSpecification.make_constant(constant_name, 0)

            workspace.add_element("Constants", constant)


def read_excel_data(excel_file: str):
    """
    读取Excel文件并解析接口信息
    返回 (main_df, struct_df, csop_df) 元组，struct_df 和 csop_df 可能为 None
    """
    try:
        df = pd.read_excel(excel_file, sheet_name=0)
        print(f"Successfully read Excel file: {excel_file}")
        print(f"Data shape: {df.shape}")
        print(f"Columns: {df.columns.tolist()}")

        # 清理列名（移除特殊字符）
        df.columns = df.columns.str.strip()

        # 尝试读取 Struct sheet（可选）
        struct_df = None
        try:
            struct_df = pd.read_excel(excel_file, sheet_name='Struct')
            struct_df.columns = struct_df.columns.str.strip()
            print(f"Found Struct sheet with {len(struct_df)} rows")
        except ValueError:
            print("No Struct sheet found, skipping struct type creation")

        # 尝试读取 CSOperation sheet（可选）
        csop_df = None
        try:
            csop_df = pd.read_excel(excel_file, sheet_name='CSOperation')
            csop_df.columns = csop_df.columns.str.strip()
            print(f"Found CSOperation sheet with {len(csop_df)} rows")
        except ValueError:
            print("No CSOperation sheet found, using default invalue/outvalue for CS operations")

        return df, struct_df, csop_df
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        return None, None, None


PRIMITIVE_TYPES = {'uint8', 'uint16', 'uint32', 'float32', 'boolean'}


def parse_struct_definitions(struct_df):
    """
    解析 Struct sheet 为结构体定义字典
    返回: OrderedDict { struct_name: [ {member_name, member_type}, ... ] }
    """
    from collections import OrderedDict

    if struct_df is None or struct_df.empty:
        return OrderedDict()

    structs = OrderedDict()
    for _, row in struct_df.iterrows():
        if pd.isna(row.get('StructName')) or pd.isna(row.get('MemberName')):
            continue

        struct_name = str(row['StructName']).strip()
        member_name = str(row['MemberName']).strip()
        member_type = str(row['MemberType']).strip()

        if struct_name not in structs:
            structs[struct_name] = []
        structs[struct_name].append({
            'member_name': member_name,
            'member_type': member_type
        })

    return structs


def parse_csoperation_definitions(csop_df):
    """
    解析 CSOperation sheet 为嵌套字典
    返回: { (interface_name, operation_name): [ {arg_name, arg_direction, arg_type}, ... ] }
    csop_df 为 None 时返回空字典
    """
    if csop_df is None or csop_df.empty:
        return {}

    csop_defs = {}
    for _, row in csop_df.iterrows():
        if pd.isna(row.get('InterfaceName')) or pd.isna(row.get('OperationName')) or pd.isna(row.get('ArgumentName')):
            continue

        iface = str(row['InterfaceName']).strip()
        op = str(row['OperationName']).strip()
        arg_name = str(row['ArgumentName']).strip()
        arg_dir = str(row['ArgumentDirection']).strip().upper()
        arg_type = str(row['ArgumentType']).strip()

        key = (iface, op)
        if key not in csop_defs:
            csop_defs[key] = []
        csop_defs[key].append({
            'arg_name': arg_name,
            'arg_direction': arg_dir,
            'arg_type': arg_type
        })

    return csop_defs


def validate_struct_definitions(struct_defs):
    """
    校验结构体定义的合法性
    """
    struct_names = set(struct_defs.keys())
    errors = []

    for struct_name, members in struct_defs.items():
        # 结构体名不能与基本类型冲突
        if struct_name.lower() in PRIMITIVE_TYPES:
            errors.append(f"Struct name '{struct_name}' conflicts with primitive type")

        # 成员名在结构体内唯一
        member_names = [m['member_name'] for m in members]
        if len(member_names) != len(set(member_names)):
            errors.append(f"Struct '{struct_name}' has duplicate member names")

        # 成员类型必须是基本类型或已定义的结构体
        for member in members:
            mt = member['member_type']
            if mt.lower() not in PRIMITIVE_TYPES and mt not in struct_names:
                errors.append(
                    f"Struct '{struct_name}' member '{member['member_name']}' "
                    f"has unknown type '{mt}'"
                )

    if errors:
        raise ValueError("Struct validation errors:\n" + "\n".join(errors))


def resolve_struct_order(struct_defs):
    """
    拓扑排序：被依赖的结构体先创建
    检测循环依赖
    """
    struct_names = set(struct_defs.keys())

    # 构建依赖图
    deps = {}
    for struct_name, members in struct_defs.items():
        deps[struct_name] = set()
        for member in members:
            mt = member['member_type']
            if mt.lower() not in PRIMITIVE_TYPES and mt in struct_names:
                deps[struct_name].add(mt)

    # Kahn 算法拓扑排序
    in_degree = {name: len(dep_set) for name, dep_set in deps.items()}
    queue = [name for name, d in in_degree.items() if d == 0]
    order = []

    while queue:
        current = queue.pop(0)
        order.append(current)
        for name in struct_names:
            if current in deps.get(name, set()):
                deps[name].discard(current)
                in_degree[name] -= 1
                if in_degree[name] == 0:
                    queue.append(name)

    if len(order) != len(struct_names):
        remaining = struct_names - set(order)
        raise ValueError(f"Circular struct dependency detected among: {remaining}")

    return order


def create_struct_types(workspace, struct_defs):
    """
    按拓扑序创建 STRUCTURE ImplementationDataType
    返回: dict { struct_name: ImplementationDataType }
    """
    created_structs = {}
    creation_order = resolve_struct_order(struct_defs)

    for struct_name in creation_order:
        members = struct_defs[struct_name]
        sub_elements = []

        for member in members:
            member_name = member['member_name']
            member_type = member['member_type']

            if member_type.lower() in PRIMITIVE_TYPES:
                impl_type = workspace.find_element("PlatformImplementationDataTypes",
                                                   member_type.lower())
            elif member_type in created_structs:
                impl_type = created_structs[member_type]
            else:
                raise ValueError(
                    f"Unknown member type '{member_type}' in struct '{struct_name}'"
                )

            sw_data_def_props = ar_element.SwDataDefPropsConditional(
                impl_data_type_ref=impl_type.ref()
            )
            sub_elem = ar_element.ImplementationDataTypeElement(
                member_name,
                category="TYPE_REFERENCE",
                sw_data_def_props=sw_data_def_props
            )
            sub_elements.append(sub_elem)

        struct_type = ar_element.ImplementationDataType(
            struct_name,
            category="STRUCTURE",
            sub_elements=sub_elements
        )
        workspace.add_element("PlatformImplementationDataTypes", struct_type)
        created_structs[struct_name] = struct_type
        print(f"Created STRUCTURE type: {struct_name} with {len(sub_elements)} members")

    return created_structs


def convert_xlsx_to_arxml(excel_file, output_file):
    """
    主函数
    """
    # 读取Excel数据（主 sheet + 可选的 Struct sheet + 可选的 CSOperation sheet）
    df, struct_df, csop_df = read_excel_data(excel_file)
    if df is None:
        return

    # 创建工作空间
    workspace = autosar.xml.Workspace()
    create_package_map(workspace)
    init_behavior_settings(workspace)
    create_platform_types(workspace)

    # 解析并创建结构体类型（在接口创建之前）
    struct_defs = parse_struct_definitions(struct_df)
    struct_types = {}
    if struct_defs:
        validate_struct_definitions(struct_defs)
        struct_types = create_struct_types(workspace, struct_defs)

    # 解析 CSOperation 自定义参数
    csop_defs = parse_csoperation_definitions(csop_df)
    
    # 解析Excel数据
    interface_data = {}
    swc_name = None
    port_info = []

    for _, row in df.iterrows():
        if pd.isna(row['SWCName']):
            continue

        swc_name = row['SWCName']
        direction = row['Direction']
        port_name = row['PortName']
        interface_name = row['InterfaceName']
        element_name = row['ElementName']
        interface_type = row['InterfaceType']
        element_data_type = row['ElementDataType']

        # 存储接口信息（支持同一接口多个element）
        if interface_name not in interface_data:
            interface_data[interface_name] = {
                'elements': [{'element_name': element_name, 'data_type': element_data_type}],
                'interface_type': interface_type
            }
        else:
            # 检查该element是否已存在，避免重复
            existing_names = [e['element_name'] for e in interface_data[interface_name]['elements']]
            if element_name not in existing_names:
                interface_data[interface_name]['elements'].append({
                    'element_name': element_name,
                    'data_type': element_data_type
                })

        # 存储端口信息
        port_info.append({
            'port_name': port_name,
            'interface_name': interface_name,
            'direction': direction,
            'element_name': element_name,
            'data_type': element_data_type,
            'interface_type': interface_type
        })
    
    print(f"Found SWC: {swc_name}")
    print(f"Number of ports: {len(port_info)}")
    
    # 创建常量
    create_constants(workspace, interface_data, struct_defs)
    
    # 创建接口（根据类型创建SenderReceiver或ClientServer接口）
    created_interfaces = {}
    for interface_name, info in interface_data.items():
        interface_type = info['interface_type'].strip().lower()

        if interface_type == 'clientserver':
            # 创建ClientServer接口，为每个element创建operation
            for elem in info['elements']:
                interface = create_clientserver_interface(workspace, interface_name, elem['element_name'], elem['data_type'], struct_types, csop_defs)
            created_interfaces[interface_name] = interface
            op_names = [e['element_name'] for e in info['elements']]
            print(f"Created ClientServer interface: {interface_name} with operations: {op_names}")
        else:
            # 创建SenderReceiver接口
            elem = info['elements'][0]
            interface = create_senderreceiver_interface(workspace, interface_name, elem['element_name'], elem['data_type'], struct_types)
            created_interfaces[interface_name] = interface
            print(f"Created SenderReceiver interface: {interface_name}")
    
    # 创建应用软件组件
    if swc_name:
        swc = ar_element.ApplicationSoftwareComponentType(swc_name)
        workspace.add_element("ComponentTypes", swc)
        
        # 创建端口，并分类收集端口信息
        sr_port_names = []  # SenderReceiver端口
        cs_port_operations = []  # ClientServer端口的operation信息
        cs_ports_grouped = {}  # 按port_name分组CS端口信息

        # 先分组收集CS端口的所有operation
        for port in port_info:
            interface_type = port['interface_type']
            if interface_type.strip().lower() == 'clientserver':
                pname = port['port_name']
                if pname not in cs_ports_grouped:
                    cs_ports_grouped[pname] = {
                        'interface_name': port['interface_name'],
                        'direction': port['direction'],
                        'operations': []
                    }
                cs_ports_grouped[pname]['operations'].append(port['element_name'])

        for port in port_info:
            interface = created_interfaces[port['interface_name']]
            interface_type = port['interface_type']
            element_name = port['element_name']

            if interface_type.strip().lower() == 'clientserver':
                pname = port['port_name']
                # 仅在第一次遇到该port时创建（带所有operation的com_spec）
                if pname in cs_ports_grouped:
                    all_ops = cs_ports_grouped.pop(pname)
                    create_clientserver_port(swc, pname, interface, all_ops['direction'], all_ops['operations'])
                    print(f"Created {all_ops['direction']} CS port: {pname} with operations: {all_ops['operations']}")

                # 为provide端口的每个operation收集runnable信息
                if port['direction'].lower() == 'provide':
                    cs_port_operations.append({
                        'port_name': port['port_name'],
                        'operation_name': element_name
                    })
            else:
                # SenderReceiver接口需要初始值
                init_value = workspace.find_element("Constants", f"{element_name}_IV")
                create_port(swc, port['port_name'], interface, port['direction'],
                           init_value.ref() if init_value else None)
                sr_port_names.append(port['port_name'])
                print(f"Created {port['direction']} SR port: {port['port_name']}")
        
        # 创建内部行为
        behavior = swc.create_internal_behavior()
        
        # 创建排他区域
        behavior.create_exclusive_area("ExampleExclusiveArea")
        
        # 创建可运行实体
        # 1. Init runnable
        init_runnable_name = f"{swc_name}_Init"
        create_runnable(behavior, init_runnable_name, [])
        
        # 2. Periodic runnable (用于SenderReceiver端口)
        if sr_port_names:
            periodic_runnable_name = f"{swc_name}_Run"
            create_runnable(behavior, periodic_runnable_name, sr_port_names)
        
        # 3. ClientServer operation runnables (每个operation一个runnable)
        for cs_op in cs_port_operations:
            cs_runnable_name = f"{swc_name}_{cs_op['port_name']}_{cs_op['operation_name']}"
            create_runnable(behavior, cs_runnable_name, [])
            print(f"Created CS runnable: {cs_runnable_name}")
        
        # 创建事件
        # 1. Init event
        behavior.create_init_event(init_runnable_name)
        
        # 2. Timing event (用于SenderReceiver端口)
        if sr_port_names:
            behavior.create_timing_event(periodic_runnable_name, period=0.1)
        
        # 3. Operation invoked events (用于ClientServer端口)
        for cs_op in cs_port_operations:
            cs_runnable_name = f"{swc_name}_{cs_op['port_name']}_{cs_op['operation_name']}"
            operation_ref = f"{cs_op['port_name']}/{cs_op['operation_name']}"
            behavior.create_operation_invoked_event(cs_runnable_name, operation_ref)
            print(f"Created operation invoked event for: {operation_ref}")
        
        # 创建访问点
        all_port_names = sr_port_names + [cs_op['port_name'] for cs_op in cs_port_operations]
        create_access_points(behavior, all_port_names)
        
        # 创建SWC实现对象
        impl = ar_element.SwcImplementation(f"{swc_name}_Implementation", 
                                           behavior_ref=swc.internal_behavior.ref())
        workspace.add_element("ComponentTypes", impl)
        
        print(f"Created SWC: {swc_name}")
    
    # 保存XML文件
    workspace.set_document_root(os.path.join(os.path.dirname(__file__), "generated"))
    
    # 确保输出目录存在
    os.makedirs(os.path.join(os.path.dirname(__file__), "generated"), exist_ok=True)
    
    # 创建单个文档包含所有内容
    workspace.create_document(output_file, packages=["/PortInterfaces", "/Constants", 
                                                    "/AUTOSAR_Platform", "/ComponentTypes"])
    workspace.write_documents(schema_version=46)
    
    print(f"Generated ARXML file: {output_file}")
    print("Generation completed successfully!")


if __name__ == "__main__":
    local_excel_file = "myswcautosar.xlsx"
    local_output_file = "myswc_gen.arxml"
    convert_xlsx_to_arxml(local_excel_file, local_output_file)