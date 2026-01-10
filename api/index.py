from flask import Flask, request, send_file
import os, tempfile
from swc_generator import convert_xlsx_to_arxml

app = Flask(__name__)

# project root (parent of api/)
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


@app.route('/', methods=['GET'])
def serve_index():
    index_path = os.path.join(ROOT_DIR, 'index.html')
    if os.path.exists(index_path):
        return send_file(index_path)
    return 'index.html not found', 404


@app.route('/api/index', methods=['POST'])
def handle_upload():
    if 'file' not in request.files:
        return 'No file uploaded', 400
    uploaded = request.files['file']
    if uploaded.filename == '':
        return 'No file selected', 400

    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
        uploaded.save(tmp.name)
        tmp_path = tmp.name

    arxml_path = tmp_path.replace('.xlsx', '.arxml')
    try:
        convert_xlsx_to_arxml(tmp_path, arxml_path)
        if not os.path.exists(arxml_path):
            return 'Conversion failed', 500
        return send_file(arxml_path, mimetype='application/xml', download_name='result.arxml', as_attachment=True)
    except Exception as e:
        return f'Internal server error: {e}', 500
    finally:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            if os.path.exists(arxml_path):
                os.remove(arxml_path)
        except Exception:
            pass


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)