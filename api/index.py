from http.server import BaseHTTPRequestHandler
import cgi, io, os, tempfile
from swc_generator import convert_xlsx_to_arxml

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        form = cgi.FieldStorage(fp=self.rfile, headers=self.headers,
                                environ={'REQUEST_METHOD':'POST'})
        file_item = form['file']
        if not file_item.file:
            self.send_error(400, 'No file')
            return

        # 保存上传的临时 Excel
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
            tmp.write(file_item.file.read())
            tmp_path = tmp.name

        # 调用你的转换脚本
        arxml_path = tmp_path.replace('.xlsx', '.arxml')

        convert_xlsx_to_arxml(tmp_path, arxml_path)

        # 把 ARXML 读回并返回
        with open(arxml_path, 'rb') as f:
            data = f.read()
        os.remove(tmp_path)
        os.remove(arxml_path)

        self.send_response(200)
        self.send_header('Content-Type', 'application/xml')
        self.send_header('Content-Disposition', 'attachment; filename="result.arxml"')
        self.end_headers()
        self.wfile.write(data)

# 文件尾部新增
if __name__ == '__main__':
    from http.server import HTTPServer
    HTTPServer(('0.0.0.0', 8000), handler).serve_forever()