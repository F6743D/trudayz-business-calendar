
import os
from keys import create_key, deactivate_key, upgrade_key, TIER_LIMITS

try:
    import stripe
    HAS_STRIPE=True
except ImportError:
    HAS_STRIPE=False

STRIPE_SECRET_KEY=os.environ.get("STRIPE_SECRET_KEY","")
STRIPE_WEBHOOK_SECRET=os.environ.get("STRIPE_WEBHOOK_SECRET","")
PRICE_TO_TIER={
    os.environ.get("STRIPE_PRICE_STARTER","price_starter"):"starter",
    os.environ.get("STRIPE_PRICE_BUSINESS","price_business"):"business",
    os.environ.get("STRIPE_PRICE_PROFESSIONAL","price_professional"):"professional",
}

def send_key_email(to_email,api_key,tier,limit):
    print(f"[EMAIL] Key for {to_email}: {api_key} | {tier} | {limit} calls/month")

def handle_webhook(payload,sig_header):
    if not HAS_STRIPE: return {"status":"error","message":"stripe not installed"}
    stripe.api_key=STRIPE_SECRET_KEY
    try:
        event=stripe.Webhook.construct_event(payload,sig_header,STRIPE_WEBHOOK_SECRET)
    except Exception as e:
        return {"status":"error","message":str(e)}
    etype=event["type"]
    print(f"[WEBHOOK] {etype}")
    if etype=="customer.subscription.created":
        sub=event["data"]["object"]
        cid=sub["customer"]; sid=sub["id"]
        price_id=sub["items"]["data"][0]["price"]["id"]
        tier=PRICE_TO_TIER.get(price_id,"starter")
        try:
            customer=stripe.Customer.retrieve(cid)
            email=customer["email"]
        except:
            email="unknown@trudayz.com"
        result=create_key(email=email,tier=tier,stripe_customer_id=cid,stripe_subscription_id=sid)
        send_key_email(email,result["api_key"],tier,TIER_LIMITS[tier])
        return {"status":"ok","action":"key_created","email":email}
    elif etype=="customer.subscription.deleted":
        sid=event["data"]["object"]["id"]
        deactivate_key(sid)
        return {"status":"ok","action":"key_deactivated"}
    elif etype=="customer.subscription.updated":
        sub=event["data"]["object"]
        sid=sub["id"]
        price_id=sub["items"]["data"][0]["price"]["id"]
        new_tier=PRICE_TO_TIER.get(price_id,"starter")
        upgrade_key(sid,new_tier)
        return {"status":"ok","action":"key_upgraded","tier":new_tier}
    return {"status":"ok","action":"ignored"}
