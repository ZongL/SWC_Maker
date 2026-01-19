"""
简化的multipart/form-data解析器
专为Netlify Functions设计
"""
import re
from typing import Dict, Any, Optional


def parse_multipart_data(body: bytes, content_type: str) -> Dict[str, Any]:
    """
    解析multipart/form-data
    
    Args:
        body: 请求体字节数据
        content_type: Content-Type头部值
        
    Returns:
        解析后的表单数据字典
    """
    # 提取boundary
    boundary_match = re.search(r'boundary=([^;]+)', content_type)
    if not boundary_match:
        return {}
    
    boundary = boundary_match.group(1).strip('"')
    boundary_bytes = f'--{boundary}'.encode()
    
    # 分割数据块
    parts = body.split(boundary_bytes)
    files = {}
    
    for part in parts:
        if not part or part == b'--\r\n' or part == b'--':
            continue
            
        # 移除开头的换行符
        part = part.lstrip(b'\r\n')
        if not part:
            continue
            
        # 分离头部和内容
        if b'\r\n\r\n' in part:
            headers_section, content = part.split(b'\r\n\r\n', 1)
        else:
            continue
            
        # 移除结尾的换行符
        content = content.rstrip(b'\r\n')
        
        # 解析Content-Disposition头部
        headers_str = headers_section.decode('utf-8', errors='ignore')
        
        # 提取name和filename
        name_match = re.search(r'name="([^"]+)"', headers_str)
        filename_match = re.search(r'filename="([^"]*)"', headers_str)
        
        if name_match:
            field_name = name_match.group(1)
            
            if filename_match:
                # 这是一个文件字段
                filename = filename_match.group(1)
                files[field_name] = {
                    'filename': filename,
                    'content': content
                }
            else:
                # 这是一个普通字段
                files[field_name] = content.decode('utf-8', errors='ignore')
    
    return files


def get_file_from_multipart(body: bytes, content_type: str, field_name: str = 'file') -> Optional[Dict[str, Any]]:
    """
    从multipart数据中提取指定的文件字段
    
    Args:
        body: 请求体字节数据
        content_type: Content-Type头部值
        field_name: 文件字段名，默认为'file'
        
    Returns:
        文件信息字典，包含filename和content，如果未找到则返回None
    """
    try:
        parsed_data = parse_multipart_data(body, content_type)
        
        if field_name in parsed_data and isinstance(parsed_data[field_name], dict):
            file_info = parsed_data[field_name]
            if 'filename' in file_info and 'content' in file_info:
                return file_info
                
        return None
        
    except Exception as e:
        print(f"Error parsing multipart data: {e}")
        return None