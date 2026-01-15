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


def create_data_type(workspace: ar_workspace.Workspace, data_type_name: str):
    """
    根据数据类型名称创建对应的实现数据类型引用
    """
    data_type_map = {
        'uint8': 'uint8',
        'uint16': 'uint16', 
        'uint32': 'uint32',
        'boolean': 'boolean'
    }
    
    impl_type_name = data_type_map.get(data_type_name.lower(), 'uint8')  # 默认使用uint8
    return workspace.find_element("PlatformImplementationDataTypes", impl_type_name)


def create_senderreceiver_interface(workspace: ar_workspace.Workspace, interface_name: str, element_name: str, data_type: str):
    """
    创建发送接收接口
    """
    # 检查接口是否已存在
    existing_interface = workspace.find_element("PortInterfaces", interface_name)
    if existing_interface is not None:
        return existing_interface
    
    # 获取数据类型
    impl_type = create_data_type(workspace, data_type)
    if impl_type is None:
        print(f"Warning: Data type {data_type} not found, using uint8 as default")
        impl_type = workspace.find_element("PlatformImplementationDataTypes", "uint8")
    
    # 创建发送接收接口
    port_interface = ar_element.SenderReceiverInterface(interface_name)
    port_interface.create_data_element(element_name, type_ref=impl_type.ref())
    workspace.add_element("PortInterfaces", port_interface)
    
    return port_interface

def create_clientserver_interface(workspace: ar_workspace.Workspace, interface_name: str, operation_name: str, data_type: str):
    """
    创建ClientServer接口
    如果接口已存在，则向其添加新的operation
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
    
    # 获取数据类型
    impl_type = create_data_type(workspace, data_type)
    if impl_type is None:
        print(f"Warning: Data type {data_type} not found, using uint8 as default")
        impl_type = workspace.find_element("PlatformImplementationDataTypes", "uint8")
    
    # 创建operation
    operation = portinterface.create_operation(operation_name)
    
    # 创建out参数
    operation.create_out_argument("outvalue",
                                 ar_enum.ServerArgImplPolicy.USE_ARGUMENT_TYPE,
                                 type_ref=impl_type.ref())
    
    # 创建in参数
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
                             interface_ref, direction: str, operation_name: str):
    """
    创建ClientServer类型的端口（提供端口或需求端口）
    需要指定operation引用
    """
    # 从接口中查找operation
    interface = interface_ref
    operation = None
    
    if hasattr(interface, 'operations') and interface.operations:
        for op in interface.operations:
            if op.name == operation_name:
                operation = op
                break
    
    if operation is None:
        raise ValueError(f"Operation '{operation_name}' not found in interface '{interface.name}'")
    
    # 获取operation引用
    operation_ref = operation.ref()
    if operation_ref is None:
        raise ValueError(f"Operation '{operation_name}' reference is None. Make sure the interface is added to workspace first.")
    
    # 创建com_spec（注意：需要放在列表中传递）
    if direction.lower() == 'provide':
        # 提供端口使用ServerComSpec
        com_spec = [ar_element.ServerComSpec(operation_ref=operation_ref)]
        return swc.create_provide_port(port_name, interface_ref, com_spec=com_spec)
    elif direction.lower() == 'require':
        # 需求端口使用ClientComSpec
        com_spec = [ar_element.ClientComSpec(operation_ref=operation_ref)]
        return swc.create_require_port(port_name, interface_ref, com_spec=com_spec)
    else:
        raise ValueError(f"Unknown direction: {direction}")


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


def create_constants(workspace: ar_workspace.Workspace, interface_data: dict):
    """
    创建常量规范（初始值）
    """
    for interface_name, element_info in interface_data.items():
        element_name = element_info['element_name']
        data_type = element_info['data_type']
        
        # 根据数据类型设置默认初始值
        if data_type.lower() == 'boolean':
            init_value = 0  # FALSE
        elif data_type.lower() in ['uint8', 'uint16', 'uint32']:
            init_value = 0
        else:
            init_value = 0
            
        constant_name = f"{element_name}_IV"
        constant = ar_element.ConstantSpecification.make_constant(constant_name, init_value)
        workspace.add_element("Constants", constant)


def read_excel_data(excel_file: str):
    """
    读取Excel文件并解析接口信息
    """
    try:
        df = pd.read_excel(excel_file)
        print(f"Successfully read Excel file: {excel_file}")
        print(f"Data shape: {df.shape}")
        print(f"Columns: {df.columns.tolist()}")
        
        # 清理列名（移除特殊字符）
        df.columns = df.columns.str.strip()
        
        return df
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        return None


def convert_xlsx_to_arxml(excel_file, output_file):
    """
    主函数
    """    
    # 读取Excel数据
    df = read_excel_data(excel_file)
    if df is None:
        return
    
    # 创建工作空间
    workspace = autosar.xml.Workspace()
    create_package_map(workspace)
    init_behavior_settings(workspace)
    create_platform_types(workspace)
    
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
        
        # 存储接口信息
        if interface_name not in interface_data:
            interface_data[interface_name] = {
                'element_name': element_name,
                'data_type': element_data_type,
                'interface_type': interface_type
            }
        
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
    create_constants(workspace, interface_data)
    
    # 创建接口（根据类型创建SenderReceiver或ClientServer接口）
    created_interfaces = {}
    for interface_name, info in interface_data.items():
        interface_type = info['interface_type'].strip().lower()
        
        if interface_type == 'clientserver':
            # 创建ClientServer接口
            interface = create_clientserver_interface(workspace, interface_name, info['element_name'], info['data_type'])
            created_interfaces[interface_name] = interface
            print(f"Created ClientServer interface: {interface_name} with operation: {info['element_name']}")
        else:
            # 创建SenderReceiver接口
            interface = create_senderreceiver_interface(workspace, interface_name, info['element_name'], info['data_type'])
            created_interfaces[interface_name] = interface
            print(f"Created SenderReceiver interface: {interface_name}")
    
    # 创建应用软件组件
    if swc_name:
        swc = ar_element.ApplicationSoftwareComponentType(swc_name)
        workspace.add_element("ComponentTypes", swc)
        
        # 创建端口，并分类收集端口信息
        sr_port_names = []  # SenderReceiver端口
        cs_port_operations = []  # ClientServer端口的operation信息
        
        for port in port_info:
            interface = created_interfaces[port['interface_name']]
            interface_type = port['interface_type']
            element_name = port['element_name']
            
            if interface_type.strip().lower() == 'clientserver':
                # ClientServer接口使用专门的函数创建端口
                create_clientserver_port(swc, port['port_name'], interface, port['direction'], element_name)
                # 只为provide端口创建runnable和event
                if port['direction'].lower() == 'provide':
                    cs_port_operations.append({
                        'port_name': port['port_name'],
                        'operation_name': element_name
                    })
                print(f"Created {port['direction']} CS port: {port['port_name']}")
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
    workspace.write_documents()
    
    print(f"Generated ARXML file: {output_file}")
    print("Generation completed successfully!")


if __name__ == "__main__":
    local_excel_file = "myswcautosar.xlsx"
    local_output_file = "myswc_gen.arxml"
    convert_xlsx_to_arxml(local_excel_file, local_output_file)