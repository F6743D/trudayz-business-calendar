#!/usr/bin/env python3
import http.server
import json
import os

class CaptureHandler(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/api/capture':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode('utf-8'))
                email = data.get('email', '').strip()
                
                if email:
                    # Append the email securely to a local plain text file
                    storage_path = os.path.expanduser('~/business-day-calendar/leads.txt')
                    with open(storage_path, 'a') as f:
                        f.write(f"{email}\n")
                    
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps({"status": "success"}).encode('utf-8'))
                    return
            except Exception as e:
                print(f"Error capturing data: {e}")
                
            self.send_response(400)
            self.end_headers()
        else:
            super().do_POST()

if __name__ == "__main__":
    # Serve files from the project folder on port 8080
    os.chdir(os.path.expanduser('~/business-day-calendar'))
    server_address = ('', 8080)
    httpd = http.server.HTTPServer(server_address, CaptureHandler)
    print("TruDayz local capture engine live on http://localhost:8080")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down capture engine.")
