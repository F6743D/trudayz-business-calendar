
import os,json,hashlib,secrets,datetime
from typing import Dict,Any,Optional

KEYS_FILE=os.path.join(os.path.dirname(os.path.abspath(__file__)),"api_keys.json")
TIER_LIMITS={"starter":1000,"business":10000,"professional":100000,"enterprise":999999999}
TIER_PRICES={"starter":29,"business":99,"professional":299,"enterprise":0}

def _read_keys():
    if not os.path.exists(KEYS_FILE): return {}
    with open(KEYS_FILE) as f: return json.load(f)

def _write_keys(data):
    with open(KEYS_FILE,"w") as f: json.dump(data,f,indent=4)

def generate_api_key(): return "td_"+secrets.token_urlsafe(32)

def create_key(email,tier="starter",stripe_customer_id=None,stripe_subscription_id=None):
    if tier not in TIER_LIMITS: raise ValueError(f"Invalid tier: {tier}")
    raw_key=generate_api_key()
    key_hash=hashlib.sha256(raw_key.encode()).hexdigest()
    now=datetime.datetime.utcnow().isoformat()
    month_key=datetime.datetime.utcnow().strftime("%Y-%m")
    record={"key_hash":key_hash,"email":email.strip().lower(),"tier":tier,"status":"active","stripe_customer_id":stripe_customer_id,"stripe_subscription_id":stripe_subscription_id,"created_at":now,"last_used_at":None,"usage":{month_key:0},"monthly_limit":TIER_LIMITS[tier]}
    keys=_read_keys(); keys[key_hash]=record; _write_keys(keys)
    return {"api_key":raw_key,"key_hash":key_hash,"email":email,"tier":tier,"limit":TIER_LIMITS[tier],"created_at":now}

def validate_key(raw_key):
    if not raw_key or not raw_key.startswith("td_"): return {"valid":False,"reason":"Invalid key format."}
    key_hash=hashlib.sha256(raw_key.encode()).hexdigest()
    keys=_read_keys()
    if key_hash not in keys: return {"valid":False,"reason":"API key not found."}
    record=keys[key_hash]
    if record["status"]!="active": return {"valid":False,"reason":f"Key is {record['status']}."}
    month_key=datetime.datetime.utcnow().strftime("%Y-%m")
    if month_key not in record["usage"]: record["usage"][month_key]=0
    calls_used=record["usage"][month_key]
    limit=record["monthly_limit"]
    if calls_used>=limit: return {"valid":False,"reason":f"Monthly limit reached ({limit} calls). Upgrade your plan.","tier":record["tier"],"calls_used":calls_used,"calls_remaining":0}
    record["usage"][month_key]+=1
    record["last_used_at"]=datetime.datetime.utcnow().isoformat()
    keys[key_hash]=record; _write_keys(keys)
    return {"valid":True,"reason":"OK","tier":record["tier"],"email":record["email"],"calls_used":calls_used+1,"calls_remaining":limit-calls_used-1}

def deactivate_key(stripe_subscription_id):
    keys=_read_keys()
    for key_hash,record in keys.items():
        if record.get("stripe_subscription_id")==stripe_subscription_id:
            record["status"]="cancelled"; keys[key_hash]=record; _write_keys(keys); return True
    return False

def upgrade_key(stripe_subscription_id,new_tier):
    if new_tier not in TIER_LIMITS: return False
    keys=_read_keys()
    for key_hash,record in keys.items():
        if record.get("stripe_subscription_id")==stripe_subscription_id:
            record["tier"]=new_tier; record["monthly_limit"]=TIER_LIMITS[new_tier]
            keys[key_hash]=record; _write_keys(keys); return True
    return False

def get_usage(raw_key):
    key_hash=hashlib.sha256(raw_key.encode()).hexdigest()
    keys=_read_keys()
    if key_hash not in keys: return {"error":"Key not found."}
    record=keys[key_hash]
    month_key=datetime.datetime.utcnow().strftime("%Y-%m")
    calls_used=record["usage"].get(month_key,0)
    return {"email":record["email"],"tier":record["tier"],"status":record["status"],"calls_this_month":calls_used,"monthly_limit":record["monthly_limit"],"calls_remaining":max(0,record["monthly_limit"]-calls_used),"last_used_at":record["last_used_at"]}

def list_all_keys():
    keys=_read_keys()
    month_key=datetime.datetime.utcnow().strftime("%Y-%m")
    result=[]
    for key_hash,record in keys.items():
        result.append({"email":record["email"],"tier":record["tier"],"status":record["status"],"calls_this_month":record["usage"].get(month_key,0),"limit":record["monthly_limit"],"created_at":record["created_at"]})
    return sorted(result,key=lambda x:x["created_at"],reverse=True)

if __name__=="__main__":
    import sys
    if len(sys.argv)<2: print("Usage: python keys.py create <email> <tier>"); sys.exit(0)
    cmd=sys.argv[1]
    if cmd=="create":
        email=sys.argv[2] if len(sys.argv)>2 else input("Email: ")
        tier=sys.argv[3] if len(sys.argv)>3 else "starter"
        result=create_key(email,tier)
        print(f"API Key: {result['api_key']}")
        print(f"Tier: {result['tier']} ({result['limit']} calls/month)")
        print("Save this key - it won't be shown again.")
    elif cmd=="list":
        keys=list_all_keys()
        if not keys: print("No keys yet.")
        for k in keys: print(f"  {k['email']} | {k['tier']} | {k['status']} | {k['calls_this_month']}/{k['limit']}")
