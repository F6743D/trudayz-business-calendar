
import os,json,datetime
from engine import calculate,get_current_context
from keys import validate_key,get_usage,list_all_keys,TIER_LIMITS,TIER_PRICES
from flask import Flask,request,jsonify,send_from_directory
from functools import wraps

try:
    import psycopg2
    HAS_PG=True
except:
    HAS_PG=False

try:
    from stripe_webhook import handle_webhook
    HAS_STRIPE=True
except:
    HAS_STRIPE=False

DATABASE_URL=os.environ.get("DATABASE_URL")
LOCAL_LEADS=os.path.join(os.path.dirname(__file__),"leads.txt")
STATIC_DIR=os.path.dirname(__file__)
ADMIN_KEY=os.environ.get("TRUDAYZ_ADMIN_KEY","admin_change_this")
app=Flask(__name__,static_folder=STATIC_DIR)

def get_key(): return request.headers.get("X-API-Key","") or request.args.get("api_key","")

def require_api_key(f):
    @wraps(f)
    def dec(*a,**k):
        raw=get_key()
        if not raw: return jsonify({"error":"API key required.","signup":"https://trudayz.com/#pricing"}),401
        r=validate_key(raw)
        if not r["valid"]: return jsonify({"error":r["reason"],"docs":"https://trudayz.com/docs"}),403
        request.key_info=r
        return f(*a,**k)
    return dec

def require_admin(f):
    @wraps(f)
    def dec(*a,**k):
        if request.headers.get("X-Admin-Key","")!=ADMIN_KEY: return jsonify({"error":"Unauthorized"}),401
        return f(*a,**k)
    return dec

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
        with open(LOCAL_LEADS) as f:
            for line in f:
                parts=line.split(",")
                if parts: existing.add(parts[0].strip().lower())
    if email in existing: return "duplicate"
    with open(LOCAL_LEADS,"a") as f: f.write(f"{email},{days},{source},{datetime.datetime.now().isoformat()}
")
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
@require_api_key
def api_calculate():
    try:
        data=request.get_json(force=True) or {}
        days=int(data.get("days",0))
        if days<=0 or days>1000: return jsonify({"error":"Days must be 1-1000."}),400
        start=None
        if "start_date" in data: start=datetime.date.fromisoformat(data["start_date"])
        result=calculate(days,start); result["context"]=get_current_context()
        result["usage"]={"calls_used":request.key_info.get("calls_used"),"calls_remaining":request.key_info.get("calls_remaining"),"tier":request.key_info.get("tier")}
        return jsonify(result)
    except Exception as e: return jsonify({"error":str(e)}),500

@app.route("/api/usage",methods=["GET"])
@require_api_key
def api_usage(): return jsonify(get_usage(get_key()))

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
def api_health(): return jsonify({"status":"ok","timestamp":datetime.datetime.now().isoformat()})

@app.route("/stripe/webhook",methods=["POST"])
def stripe_webhook():
    if not HAS_STRIPE: return jsonify({"error":"Stripe not configured"}),500
    result=handle_webhook(request.get_data(),request.headers.get("Stripe-Signature",""))
    return jsonify(result),200 if result.get("status")=="ok" else 400

@app.route("/admin/keys",methods=["GET"])
@require_admin
def admin_keys(): return jsonify(list_all_keys())

if __name__=="__main__":
    port=int(os.environ.get("PORT",8080))
    print(f"TruDayz live → http://localhost:{port}")
    app.run(host="0.0.0.0",port=port,debug=True)

application = app
