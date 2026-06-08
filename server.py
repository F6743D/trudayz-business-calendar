#!/usr/bin/env python3
import http.server
import json
import os
import urllib.parse

try:
    import psycopg2
    HAS_POSTGRES = True
except ImportError:
    HAS_POSTGRES = False

DATABASE_URL = os.environ.get("DATABASE_URL")
BASE_DIR = os.path.expanduser("~/business-day-calendar")
LOCAL_FILE = os.path.join(BASE_DIR, "leads.txt")
INDEX_FILE = os.path.join(BASE_DIR, "index.html")

def init_db():
    if not HAS_POSTGRES or not DATABASE_URL:
        print("[DB] PostgreSQL client missing or DATABASE_URL unset. Falling back to text file.")
        return
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS leads (
                id SERIAL PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL,
                days_window VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        cur.close()
        conn.close()
        print("[DB] Unique table schema verified.")
    except Exception as e:
        print(f"[DB Error] Failed schema initialization: {e}")

class CaptureHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            if os.path.exists(INDEX_FILE):
                self.send_response(200)
                self.send_header("Content-type", "text/html; charset=utf-8")
                self.end_headers()
                with open(INDEX_FILE, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.send_response(404)
                self.end_headers()
        elif self.path == "/api/count":
            # Admin Mode: Query live PostgreSQL row count tally
            count = 0
            if HAS_POSTGRES and DATABASE_URL:
                try:
                    conn = psycopg2.connect(DATABASE_URL)
                    cur = conn.cursor()
                    cur.execute("SELECT COUNT(*) FROM leads;")
                    count = cur.fetchone()[0]
                    cur.close()
                    conn.close()
                except Exception as e:
                    print(f"[DB Error] Row query failed: {e}")
            else:
                # Fallback to counting text file lines if DB is unreachable
                if os.path.exists(LOCAL_FILE):
                    with open(LOCAL_FILE, "r") as f:
                        count = len(f.readlines())

            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"count": count}).encode())
        else:
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Engine Active.")

    def do_POST(self):
        if self.path == "/api/capture":
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            
            params = urllib.parse.parse_qs(post_data)
            email = params.get('email', [None])[0]
            days = params.get('days', [None])[0]
            
            if email:
                email = email.strip()
                days = days.strip() if days else "68"
                saved = False
                duplicate = False

                # 1. Attempt PostgreSQL Write Optimization
                if HAS_POSTGRES and DATABASE_URL:
                    try:
                        conn = psycopg2.connect(DATABASE_URL)
                        cur = conn.cursor()
                        cur.execute(
                            "INSERT INTO leads (email, days_window) VALUES (%s, %s) ON CONFLICT (email) DO NOTHING RETURNING id;",
                            (email, f"{days} Days")
                        )
                        res = cur.fetchone()
                        conn.commit()
                        cur.close()
                        conn.close()
                        if res:
                            saved = True
                            print(f"[DB Sync] Captured record: {email}")
                        else:
                            duplicate = True
                            print(f"[DB Watch] Duplicate blocked: {email}")
                    except Exception as e:
                        print(f"[DB Error] Falling back to text file write: {e}")

                # 2. Text File Backup Layer
                if not saved and not duplicate:
                    existing_leads = []
                    if os.path.exists(LOCAL_FILE):
                        with open(LOCAL_FILE, "r") as f:
                            for line in f.readlines():
                                if "," in line:
                                    existing_leads.append(line.split(",")[0].strip())
                                else:
                                    existing_leads.append(line.strip())
                    
                    if email in existing_leads:
                        duplicate = True
                    else:
                        with open(LOCAL_FILE, "a") as f:
                            f.write(f"{email}, {days} Days\n")
                        saved = True
                        print(f"[Local Sync] Archived backup entry: {email}")

                if duplicate:
                    self.send_response(400)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"status": "error", "message": "Already registered."}).encode())
                else:
                    self.send_response(200)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"status": "success", "message": "Verified."}).encode())
            else:
                self.send_response(400)
                self.end_headers()

if __name__ == "__main__":
    init_db()
    server_address = ('', 8080)
    httpd = http.server.HTTPServer(server_address, CaptureHandler)
    print("TruDayz local capture engine live on port 8080")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down capture engine.")

# Vercel Serverless WSGI Gateway Engine
def handler(environ, start_response):
    from io import BytesIO
    import sys
    
    # Reconstruct request context for the existing CaptureHandler
    class VercelRequest:
        def __init__(self):
            self.rfile = environ.get('wsgi.input', BytesIO())
            self.headers = {k.replace('HTTP_', '').replace('_', '-').title(): v for k, v in environ.items() if k.startswith('HTTP_')}
            if 'CONTENT_TYPE' in environ: self.headers['Content-Type'] = environ['CONTENT_TYPE']
            if 'CONTENT_LENGTH' in environ: self.headers['Content-Length'] = environ['CONTENT_LENGTH']
            self.command = environ.get('REQUEST_METHOD', 'GET')
            self.path = environ.get('PATH_INFO', '/')
            self.wfile = BytesIO()
            self.status_code = 200
            self.response_headers = []

        def send_response(self, code):
            self.status_code = code

        def send_header(self, keyword, value):
            self.response_headers.append((keyword, value))

        def end_headers(self):
            pass

    req = VercelRequest()
    try:
        # Initialize database logic once inside the execution thread
        init_db()
        
        # Instantiate and execute the existing capture logic dynamically
        handler_instance = CaptureHandler(None, None, None)
        handler_instance.rfile = req.rfile
        handler_instance.wfile = req.wfile
        handler_instance.headers = req.headers
        handler_instance.command = req.command
        handler_instance.path = req.path
        
        # Map routing execution
        if req.command == 'POST':
            handler_instance.do_POST()
        else:
            handler_instance.do_GET()
            
        status = f"{req.status_code} OK" if req.status_code == 200 else f"{req.status_code} Error"
        start_response(status, req.response_headers)
        return [req.wfile.getvalue()]
    except Exception as e:
        start_response("500 Internal Server Error", [("Content-Type", "text/plain")])
        return [str(e).encode()]

app = handler

# ==============================================================================
# UNIVERSAL PLATFORM ADAPTER (VERCEL SERVERLESS COMPATIBILITY LAYER)
# ==============================================================================
import os
import io

class MockSocket:
    """Simulates a live network socket file pointer for serverless environments."""
    def __init__(self, data):
        self.data = data
    def makefile(self, mode='r', bufsize=-1):
        if 'b' in mode:
            return io.BytesIO(self.data)
        return io.StringIO(self.data.decode('utf-8', errors='ignore'))

def handler(environ, start_response):
    """WSGI entry point that translates serverless events into standard socket HTTP requests."""
    try:
        # Initialize your database logic automatically
        if 'init_db' in globals():
            globals()['init_db']()
            
        # Reconstruct a standard HTTP raw request line from the cloud environment
        method = environ.get('REQUEST_METHOD', 'GET')
        path = environ.get('PATH_INFO', '/')
        query = environ.get('QUERY_STRING', '')
        if query:
            path = f"{path}?{query}"
            
        request_line = f"{method} {path} HTTP/1.1\r\n"
        
        # Rebuild standard HTTP headers
        headers_payload = ""
        for key, value in environ.items():
            if key.startswith('HTTP_'):
                header_name = key[5:].replace('_', '-').title()
                headers_payload += f"{header_name}: {value}\r\n"
            elif key in ('CONTENT_TYPE', 'CONTENT_LENGTH'):
                header_name = key.replace('_', '-').title()
                headers_payload += f"{header_name}: {value}\r\n"
        
        # Read incoming request body telemetry
        try:
            request_length = int(environ.get('CONTENT_LENGTH', 0))
            request_body = environ['wsgi.input'].read(request_length)
        except Exception:
            request_body = b""
            
        # Combine everything into a single raw byte stream
        full_raw_stream = request_line.encode('utf-8') + headers_payload.encode('utf-8') + b"\r\n" + request_body
        
        # Instantiate a fake socket stream containing our data
        mock_socket = MockSocket(full_raw_stream)
        
        # Safely instantiate your exact custom CaptureHandler
        if 'CaptureHandler' in globals():
            handler_instance = globals()['CaptureHandler'](mock_socket, ('127.0.0.1', 8080), None)
            
            # Extract the generated response bytes from the handler's output stream
            response_bytes = handler_instance.wfile.getvalue()
            
            # Split headers from body to comply with WSGI specifications
            if b"\r\n\r\n" in response_bytes:
                raw_headers, body = response_bytes.split(b"\r\n\r\n", 1)
            else:
                raw_headers, body = response_bytes, b""
                
            header_lines = raw_headers.decode('utf-8', errors='ignore').split('\r\n')
            status_line = header_lines[0]
            status_code = status_line.split(' ')[1] if len(status_line.split(' ')) > 1 else "200"
            status_text = f"{status_code} OK" if status_code == "200" else f"{status_code} Error"
            
            # Parse response headers back into pairs
            wsgi_headers = []
            for line in header_lines[1:]:
                if ":" in line:
                    k, v = line.split(":", 1)
                    wsgi_headers.append((k.strip(), v.strip()))
                    
            start_response(status_text, wsgi_headers)
            return [body]
            
        start_response("500 Internal Server Error", [("Content-Type", "text/plain")])
        return [b"CaptureHandler class not found in script namespace."]
        
    except Exception as e:
        start_response("500 Internal Server Error", [("Content-Type", "text/plain")])
        return [str(e).encode('utf-8')]

# Export the application handle Vercel looks for
app = handler

# ==============================================================================
# UNIVERSAL PLATFORM ADAPTER (FIXED STREAM RESOLUTION LAYER)
# ==============================================================================
import os
import io

class UniversalMockSocket:
    """Simulates an active network socket stream with built-in file pointers."""
    def __init__(self, data):
        self.rfile = io.BytesIO(data)
        self.wfile = io.BytesIO()
    def makefile(self, mode='r', bufsize=-1):
        if 'w' in mode:
            return self.wfile
        return self.rfile

def handler(environ, start_response):
    try:
        if 'init_db' in globals():
            globals()['init_db']()
            
        method = environ.get('REQUEST_METHOD', 'GET')
        path = environ.get('PATH_INFO', '/')
        query = environ.get('QUERY_STRING', '')
        if query:
            path = f"{path}?{query}"
            
        request_line = f"{method} {path} HTTP/1.1\r\n"
        
        headers_payload = ""
        for key, value in environ.items():
            if key.startswith('HTTP_'):
                header_name = key[5:].replace('_', '-').title()
                headers_payload += f"{header_name}: {value}\r\n"
            elif key in ('CONTENT_TYPE', 'CONTENT_LENGTH'):
                header_name = key.replace('_', '-').title()
                headers_payload += f"{header_name}: {value}\r\n"
        
        try:
            request_length = int(environ.get('CONTENT_LENGTH', 0))
            request_body = environ['wsgi.input'].read(request_length)
        except Exception:
            request_body = b""
            
        full_raw_stream = request_line.encode('utf-8') + headers_payload.encode('utf-8') + b"\r\n" + request_body
        
        # Instantiate the updated mock socket containing both rfile and wfile
        mock_socket = UniversalMockSocket(full_raw_stream)
        
        if 'CaptureHandler' in globals():
            # Pass the updated mock socket into the handler namespace
            handler_instance = globals()['CaptureHandler'](mock_socket, ('127.0.0.1', 8080), None)
            
            # Read output bytes from the wrapper
            response_bytes = mock_socket.wfile.getvalue()
            
            if b"\r\n\r\n" in response_bytes:
                raw_headers, body = response_bytes.split(b"\r\n\r\n", 1)
            else:
                raw_headers, body = response_bytes, b""
                
            header_lines = raw_headers.decode('utf-8', errors='ignore').split('\r\n')
            status_line = header_lines[0]
            status_code = status_line.split(' ')[1] if len(status_line.split(' ')) > 1 else "200"
            status_text = f"{status_code} OK" if status_code == "200" else f"{status_code} Error"
            
            wsgi_headers = []
            for line in header_lines[1:]:
                if ":" in line:
                    k, v = line.split(":", 1)
                    wsgi_headers.append((k.strip(), v.strip()))
                    
            start_response(status_text, wsgi_headers)
            return [body]
            
        start_response("500 Internal Server Error", [("Content-Type", "text/plain")])
        return [b"CaptureHandler missing."]
        
    except Exception as e:
        start_response("500 Internal Server Error", [("Content-Type", "text/plain")])
        return [str(e).encode('utf-8')]

app = handler
