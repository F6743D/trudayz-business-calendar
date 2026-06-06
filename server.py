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
    if HAS_POSTGRES and DATABASE_URL:
        try:
            conn = psycopg2.connect(DATABASE_URL)
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS leads (
                    id SERIAL PRIMARY KEY,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.commit()
            cur.close()
            conn.close()
            print("[DB] Unique table schema verified.")
        except Exception as e:
            print(f"[DB Warning] Schema initialization skipped: {e}")

class CaptureHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        # If root path is requested, serve the frontend index.html natively
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
                self.wfile.write(b"index.html not found in project directory.")
        else:
            # Fallback for general assets or flat ping
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
            
            if not email:
                try:
                    data = json.loads(post_data)
                    email = data.get('email')
                except:
                    pass

            if email:
                email = email.strip()
                saved = False
                duplicate = False

                # 1. DB Routing
                if HAS_POSTGRES and DATABASE_URL:
                    try:
                        conn = psycopg2.connect(DATABASE_URL)
                        cur = conn.cursor()
                        cur.execute(
                            "INSERT INTO leads (email) VALUES (%s) ON CONFLICT (email) DO NOTHING RETURNING id;",
                            (email,)
                        )
                        res = cur.fetchone()
                        conn.commit()
                        cur.close()
                        conn.close()
                        
                        if res is None:
                            duplicate = True
                        else:
                            saved = True
                            print(f"[DB Sync] Captured new lead: {email}")
                    except Exception as e:
                        print(f"[DB Error] Fallback triggered: {e}")

                # 2. Local File Storage Routing with Deduplication
                if not saved and not duplicate:
                    existing_leads = []
                    if os.path.exists(LOCAL_FILE):
                        with open(LOCAL_FILE, "r") as f:
                            existing_leads = [line.strip() for line in f.readlines()]
                    
                    if email in existing_leads:
                        duplicate = True
                        print(f"[Local Watch] Duplicate blocked: {email}")
                    else:
                        with open(LOCAL_FILE, "a") as f:
                            f.write(f"{email}\n")
                        saved = True
                        print(f"[Local Sync] Archived new lead: {email}")

                # Web Component Response Contract
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
