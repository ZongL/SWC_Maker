from flask import Flask, request, send_file, jsonify
import os, tempfile, json
import psycopg2
import redis
from datetime import datetime, timedelta
import hashlib
from api.swc_generator import convert_xlsx_to_arxml

app = Flask(__name__)

# 数据库和Redis配置
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://username:password@host:port/database')
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# Redis连接
try:
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
except:
    redis_client = None

def get_client_ip():
    """获取客户端IP"""
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    else:
        return request.remote_addr

def get_redis_lock_key(code):
    """获取Redis锁键名"""
    return f"code_lock:{code}"

# ========== 新增：仅验证激活码（不扣减次数） ==========
def verify_activation_code_only(code):
    """
    仅验证激活码的有效性，不扣减使用次数
    用于前端仅校验激活码是否可用的场景（如输入后即时验证）
    """
    if not code or len(code.strip()) == 0:
        return {"success": False, "message": "激活码不能为空"}
    
    code = code.strip().upper()
    
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # 仅查询激活码的核心状态，不做任何修改
        cursor.execute("""
            SELECT id, remaining_uses, expires_at, is_active 
            FROM activation_codes 
            WHERE code = %s
        """, (code,))
        
        result = cursor.fetchone()
        
        if not result:
            return {"success": False, "message": "激活码无效或已禁用"}
        
        code_id, remaining_uses, expires_at, is_active = result
        
        # 检查激活码状态（保留你原有的时区处理逻辑）
        if not is_active:
            return {"success": False, "message": "激活码已被禁用"}
        
        if expires_at and datetime.now(tz=expires_at.tzinfo) > expires_at:
            return {"success": False, "message": "激活码已过期"}
        
        if remaining_uses <= 0:
            return {"success": False, "message": "激活码使用次数已用完"}
        
        # 验证成功，返回基础信息
        return {
            "success": True,
            "message": "激活码验证成功",
            "data": {
                "remaining_uses": remaining_uses,
                "code_id": code_id  # 用于后续扣减时快速定位
            }
        }
        
    except Exception as e:
        return {"success": False, "message": f"验证失败: {str(e)}"}
    
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

# ========== 重构：验证+扣减激活码（仅生成文件时调用） ==========
def check_activation_code(code, user_ip, user_agent):
    """验证激活码并扣除次数"""
    # 第一步：先调用仅验证函数，确认激活码有效
    verify_result = verify_activation_code_only(code)
    if not verify_result["success"]:
        return verify_result  # 直接返回验证失败的结果
    
    code = code.strip().upper()
    code_id = verify_result["data"]["code_id"]  # 从验证结果获取code_id
    
    # Redis防并发锁（保留原有逻辑）
    lock_key = get_redis_lock_key(code)
    lock_timeout = 10  # 10秒超时
    
    if redis_client:
        # 尝试获取锁
        lock_acquired = redis_client.set(lock_key, "locked", nx=True, ex=lock_timeout)
        if not lock_acquired:
            return {"success": False, "message": "请求过于频繁，请稍后重试"}
    
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # 查询激活码的完整信息（用于扣减）
        cursor.execute("""
            SELECT total_uses, used_count, remaining_uses, expires_at 
            FROM activation_codes 
            WHERE id = %s
        """, (code_id,))
        
        total_uses, used_count, remaining_uses, expires_at = cursor.fetchone()
        
        # 再次检查剩余次数（防止验证后到扣减前，次数被其他请求用完）
        if remaining_uses <= 0:
            return {"success": False, "message": "激活码使用次数已用完"}
        
        # 再次检查过期状态（保留时区处理）
        if expires_at and datetime.now(tz=expires_at.tzinfo) > expires_at:
            return {"success": False, "message": "激活码已过期"}
        
        # 扣除次数
        new_used_count = used_count + 1
        new_remaining_uses = remaining_uses - 1
        
        cursor.execute("""
            UPDATE activation_codes
            SET used_count = %s, remaining_uses = %s, last_used_at = %s,
                user_ip = %s, user_agent = %s
            WHERE id = %s
        """, (new_used_count, new_remaining_uses, datetime.now(tz=expires_at.tzinfo) if expires_at else datetime.now(), user_ip, user_agent, code_id))
        
        # 记录使用日志
        cursor.execute("""
            INSERT INTO code_usage_logs (code_id, user_ip, user_agent, success)
            VALUES (%s, %s, %s, %s)
        """, (code_id, user_ip, user_agent, True))
        
        conn.commit()
        
        return {
            "success": True,
            "message": "激活码验证成功",
            "data": {
                "remaining_uses": new_remaining_uses,
                "total_uses": total_uses,
                "used_count": new_used_count
            }
        }
        
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
        return {"success": False, "message": f"系统错误: {str(e)}"}
    
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()
        
        # 释放Redis锁
        if redis_client:
            redis_client.delete(lock_key)

@app.route('/api/check-code', methods=['POST'])
def check_code():
    """验证激活码API（仅校验，不扣减次数）"""
    try:
        data = request.get_json()
        if not data or 'code' not in data:
            return jsonify({"success": False, "message": "请提供激活码"}), 400
        
        code = data['code']
        # 仅调用验证函数，不扣减次数
        result = verify_activation_code_only(code)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({"success": False, "message": f"服务器错误: {str(e)}"}), 500


@app.route('/', methods=['GET'])
def serve_index():
    index_path = os.path.join(ROOT_DIR, 'index.html')
    if os.path.exists(index_path):
        return send_file(index_path)
    return 'index.html not found', 404


@app.route('/api/index', methods=['POST'])
def handle_upload():
    # 首先检查激活码
    activation_code = request.form.get('activation_code')
    if not activation_code:
        return jsonify({"success": False, "message": "请先输入激活码"}), 400
    
    user_ip = get_client_ip()
    user_agent = request.headers.get('User-Agent', '')
    
    # 验证激活码（此时才会扣减次数）
    code_result = check_activation_code(activation_code, user_ip, user_agent)
    if not code_result['success']:
        return jsonify(code_result), 400
    
    # 检查文件
    if 'file' not in request.files:
        return jsonify({"success": False, "message": "请选择文件"}), 400
    
    uploaded = request.files['file']
    if uploaded.filename == '':
        return jsonify({"success": False, "message": "请选择文件"}), 400

    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
        uploaded.save(tmp.name)
        tmp_path = tmp.name

    arxml_path = tmp_path.replace('.xlsx', '.arxml')
    try:
        convert_xlsx_to_arxml(tmp_path, arxml_path)
        if not os.path.exists(arxml_path):
            return jsonify({"success": False, "message": "文件转换失败"}), 500
        
        return send_file(arxml_path, mimetype='application/xml', download_name='result.arxml', as_attachment=True)
    except Exception as e:
        return jsonify({"success": False, "message": f"转换错误: {str(e)}"}), 500
    finally:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            if os.path.exists(arxml_path):
                os.remove(arxml_path)
        except Exception:
            pass


# project root (parent of api/)
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)