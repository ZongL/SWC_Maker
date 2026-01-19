import json
import os
import tempfile
import base64
import sys

# Add the project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

# Import local modules
from multipart_parser import get_file_from_multipart

try:
    from api.swc_generator import convert_xlsx_to_arxml
except ImportError as e:
    print(f"Import error: {e}")
    convert_xlsx_to_arxml = None


def handler(event, context):
    """Netlify Function handler for the AUTOSAR SWC generator"""
    
    # Handle CORS preflight
    if event['httpMethod'] == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'GET, POST, OPTIONS'
            },
            'body': ''
        }
    
    # Handle POST request - file upload and conversion
    if event['httpMethod'] == 'POST':
        try:
            if not convert_xlsx_to_arxml:
                return {
                    'statusCode': 500,
                    'headers': {'Access-Control-Allow-Origin': '*'},
                    'body': json.dumps({'error': 'Conversion module not available'})
                }
            
            # Get request body
            body = event.get('body', '')
            is_base64 = event.get('isBase64Encoded', False)
            
            if is_base64:
                body = base64.b64decode(body)
            elif isinstance(body, str):
                body = body.encode('utf-8')
            
            # Get content type
            headers = event.get('headers', {})
            content_type = headers.get('content-type') or headers.get('Content-Type', '')
            
            if 'multipart/form-data' not in content_type:
                return {
                    'statusCode': 400,
                    'headers': {'Access-Control-Allow-Origin': '*'},
                    'body': json.dumps({'error': 'Content-Type must be multipart/form-data'})
                }
            
            # Parse multipart form data
            file_info = get_file_from_multipart(body, content_type, 'file')
            
            if not file_info:
                return {
                    'statusCode': 400,
                    'headers': {'Access-Control-Allow-Origin': '*'},
                    'body': json.dumps({'error': 'No file uploaded or invalid file format'})
                }
            
            file_content = file_info['content']
            filename = file_info['filename']
            
            if not file_content:
                return {
                    'statusCode': 400,
                    'headers': {'Access-Control-Allow-Origin': '*'},
                    'body': json.dumps({'error': 'Empty file'})
                }
            
            # Validate file extension
            if not filename.lower().endswith(('.xlsx', '.xls')):
                return {
                    'statusCode': 400,
                    'headers': {'Access-Control-Allow-Origin': '*'},
                    'body': json.dumps({'error': 'Invalid file type. Only .xlsx and .xls files are supported'})
                }
            
            # Create temporary files
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
                tmp.write(file_content)
                tmp_path = tmp.name
            
            arxml_path = tmp_path.replace('.xlsx', '.arxml')
            
            try:
                # Convert xlsx to arxml
                convert_xlsx_to_arxml(tmp_path, arxml_path)
                
                if not os.path.exists(arxml_path):
                    return {
                        'statusCode': 500,
                        'headers': {'Access-Control-Allow-Origin': '*'},
                        'body': json.dumps({'error': 'Conversion failed - output file not generated'})
                    }
                
                # Read the generated arxml file
                with open(arxml_path, 'rb') as f:
                    arxml_content = f.read()
                
                if not arxml_content:
                    return {
                        'statusCode': 500,
                        'headers': {'Access-Control-Allow-Origin': '*'},
                        'body': json.dumps({'error': 'Generated ARXML file is empty'})
                    }
                
                # Return as base64 encoded attachment
                return {
                    'statusCode': 200,
                    'headers': {
                        'Content-Type': 'application/xml',
                        'Content-Disposition': 'attachment; filename="swc_result.arxml"',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': base64.b64encode(arxml_content).decode('utf-8'),
                    'isBase64Encoded': True
                }
                
            except Exception as e:
                return {
                    'statusCode': 500,
                    'headers': {'Access-Control-Allow-Origin': '*'},
                    'body': json.dumps({'error': f'Conversion error: {str(e)}'})
                }
            finally:
                # Clean up temporary files
                try:
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)
                    if os.path.exists(arxml_path):
                        os.remove(arxml_path)
                except Exception:
                    pass
                    
        except Exception as e:
            return {
                'statusCode': 500,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': f'Internal server error: {str(e)}'})
            }
    
    else:
        return {
            'statusCode': 405,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': 'Method not allowed'})
        }