#!/usr/bin/env python3
"""
N8N HTTP Server - 提供HTTP接口供N8N调用
N1验证用：验证N8N能否成功调用OpenClaw接口
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
from datetime import datetime
import sys
import os

# 导入webhook receiver的逻辑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from n8n_webhook_receiver import handle_request

class N8NHandler(BaseHTTPRequestHandler):
    """处理N8N请求"""
    
    def do_GET(self):
        """处理GET请求"""
        if self.path == '/health' or self.path == '/health/':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {"status": "healthy", "service": "OpenClaw-N8N-Integration"}
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {
                "status": "success",
                "message": "OpenClaw N8N Integration Server",
                "timestamp": datetime.now().isoformat(),
                "endpoints": ["/health", "/webhook", "/dispatch"]
            }
            self.wfile.write(json.dumps(response).encode())
    
    def do_POST(self):
        """处理POST请求"""
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data.decode('utf-8'))
        except:
            data = {}
        
        result = handle_request(data)
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(result, ensure_ascii=False).encode())
    
    def log_message(self, format, *args):
        """自定义日志格式"""
        print(f"[N8N-Server] {args[0]}")

def run_server(port=5679):
    """运行服务器"""
    server = HTTPServer(('localhost', port), N8NHandler)
    print(f"[N8N-Server] 启动于 http://localhost:{port}")
    print(f"[N8N-Server] 可用端点: /health, /webhook, /dispatch")
    server.serve_forever()

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5679
    run_server(port)
