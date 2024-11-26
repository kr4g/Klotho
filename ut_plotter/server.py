from http.server import HTTPServer, SimpleHTTPRequestHandler
import json

class DataHandler(SimpleHTTPRequestHandler):
    # Class variable to store the latest data
    current_data = {"status": "success", "data": []}
    
    def do_GET(self):
        if self.path == '/data':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(self.current_data).encode())
            return
        return super().do_GET()
    
    def do_POST(self):
        if self.path == '/data':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            DataHandler.current_data = json.loads(post_data)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success"}).encode())
            return

if __name__ == "__main__":
    server = HTTPServer(('localhost', 8000), DataHandler)
    print("Server started at http://localhost:8000")
    server.serve_forever()