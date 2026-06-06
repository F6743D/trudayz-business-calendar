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
