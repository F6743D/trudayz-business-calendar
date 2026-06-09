import os,json,datetime
from engine import calculate,get_current_context
from flask import Flask,request,jsonify,send_from_directory
try:
    import psycopg2
    HAS_PG=True
except:
    HAS_PG=False

DATABASE_URL=os.environ.get("DATABASE_URL")
LOCAL_LEADS=os.path.join(os.path.dirname(__file__),"leads.txt")
STATIC_DIR=os.path.dirname(__file__)
app=Flask(__name__,static_folder=STATIC_DIR)

def init_db():
    if not HAS_PG or not DATABASE_URL: return False
    try:
        conn=psycopg2.connect(DATABASE_URL); cur=conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS leads (id SERIAL PRIMARY KEY,email VARCHAR(255) UNIQUE NOT NULL,days_input VARCHAR(50),source VARCHAR(100) DEFAULT 'web',created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);")
        conn.commit(); cur.close(); conn.close(); return True
    except Exception as e: print(f"[DB] {e}"); return False

def save_lead(email,days,source="web"):
    email=email.strip().lower()
    if HAS_PG and DATABASE_URL:
        try:
            conn=psycopg2.connect(DATABASE_URL); cur=conn.cursor()
            cur.execute("INSERT INTO leads (email,days_input,source) VALUES (%s,%s,%s) ON CONFLICT (email) DO NOTHING RETURNING id;",(email,days,source))
            row=cur.fetchone(); conn.commit(); cur.close(); conn.close()
            return "saved" if row else "duplicate"
        except Exception as e: print(f"[DB] {e}")
    existing=set()
    if os.path.exists(LOCAL_LEADS):
        with open(LOCAL_LEADS,"r") as f:
            for line in f:
                parts=line.split(",")
                if parts: existing.add(parts[0].strip().lower())
    if email in existing: return "duplicate"
    with open(LOCAL_LEADS,"a") as f: f.write(f"{email},{days},{source},{datetime.datetime.now().isoformat()}\n")
    return "saved"

def get_count():
    if HAS_PG and DATABASE_URL:
        try:
            conn=psycopg2.connect(DATABASE_URL); cur=conn.cursor()
            cur.execute("SELECT COUNT(*) FROM leads;"); count=cur.fetchone()[0]
            cur.close(); conn.close(); return count
        except: pass
    if os.path.exists(LOCAL_LEADS):
        with open(LOCAL_LEADS) as f: return len(f.readlines())
    return 0

@app.route("/",methods=["GET"])
def index(): return send_from_directory(STATIC_DIR,"index.html")

@app.route("/api/calculate",methods=["POST"])
def api_calculate():
    try:
        data=request.get_json(force=True) or {}
        days=int(data.get("days",0))
        if days<=0 or days>1000: return jsonify({"error":"Days must be 1-1000."}),400
        start=None
        if "start_date" in data: start=datetime.date.fromisoformat(data["start_date"])
        result=calculate(days,start); result["context"]=get_current_context()
        return jsonify(result)
    except Exception as e: return jsonify({"error":str(e)}),500

@app.route("/api/capture",methods=["POST"])
def api_capture():
    data=request.get_json(force=True) if request.is_json else request.form.to_dict()
    email=data.get("email","").strip(); days=str(data.get("days","")).strip() or "unknown"; source=data.get("source","web")
    if not email or "@" not in email: return jsonify({"status":"error","message":"Valid email required."}),400
    result=save_lead(email,days,source)
    if result=="duplicate": return jsonify({"status":"error","message":"Already on the list."}),409
    if result=="saved": return jsonify({"status":"success","message":"You're on the list."}),200
    return jsonify({"status":"error","message":"Try again."}),500

@app.route("/api/count",methods=["GET"])
def api_count(): return jsonify({"count":get_count()})

@app.route("/api/health",methods=["GET"])
def api_health(): return jsonify({"status":"ok","db":"postgres" if (HAS_PG and DATABASE_URL) else "flatfile","timestamp":datetime.datetime.now().isoformat()})

if __name__=="__main__":
    init_db(); port=int(os.environ.get("PORT",8080))
    print(f"TruDayz live → http://localhost:{port}")
    app.run(host="0.0.0.0",port=port,debug=True)

app=app
