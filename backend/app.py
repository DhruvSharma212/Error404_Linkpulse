import os,re,io,csv,secrets,string,json,ipaddress
from datetime import datetime,timedelta,timezone
from urllib.parse import urlparse,unquote
from flask import Flask,request,jsonify,redirect,Response,send_file
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import qrcode
load_dotenv()
app=Flask(__name__)
url=os.getenv("DATABASE_URL","").strip()
if url.startswith("postgres://"): url=url.replace("postgres://","postgresql://",1)
app.config["SQLALCHEMY_DATABASE_URI"]=url or "sqlite:///linkpulse.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"]=False
db=SQLAlchemy(app); CORS(app)
def now(): return datetime.now(timezone.utc).replace(tzinfo=None)
class Link(db.Model):
 id=db.Column(db.Integer,primary_key=True); code=db.Column(db.String(32),unique=True,nullable=False,index=True)
 original_url=db.Column(db.Text,nullable=False); title=db.Column(db.String(160),default=""); campaign=db.Column(db.String(120),default="General")
 created_at=db.Column(db.DateTime,default=now); expires_at=db.Column(db.DateTime); click_limit=db.Column(db.Integer); is_active=db.Column(db.Boolean,default=True)
 clicks=db.relationship("Click",backref="link",cascade="all, delete-orphan",lazy=True)
class Click(db.Model):
 id=db.Column(db.Integer,primary_key=True); link_id=db.Column(db.Integer,db.ForeignKey("link.id"),index=True)
 clicked_at=db.Column(db.DateTime,default=now,index=True); referrer=db.Column(db.String(500),default="Direct")
 device=db.Column(db.String(30),default="Desktop"); browser=db.Column(db.String(50),default="Other"); is_bot=db.Column(db.Boolean,default=False)

class RiskAssessment(db.Model):
 id=db.Column(db.Integer,primary_key=True)
 link_id=db.Column(db.Integer,db.ForeignKey("link.id"),nullable=False,index=True)
 assessed_at=db.Column(db.DateTime,default=now,index=True)
 risk_score=db.Column(db.Integer,nullable=False)
 risk_level=db.Column(db.String(20),nullable=False)
 reasons_json=db.Column(db.Text,nullable=False,default="[]")
 link=db.relationship("Link",backref=db.backref("risk_assessments",cascade="all, delete-orphan",lazy=True))
def valid(u):
 try:
  p=urlparse((u or "").strip()); return p.scheme in ("http","https") and bool(p.netloc) and "." in p.netloc
 except: return False
def parse_dt(s):
 try:
  d=datetime.fromisoformat(s.replace("Z","+00:00"))
  return d.astimezone(timezone.utc).replace(tzinfo=None) if d.tzinfo else d
 except: return None
def base(): return os.getenv("BASE_URL",request.host_url.rstrip("/")).rstrip("/")
def state(l):
 if not l.is_active:return "Paused"
 if l.expires_at and l.expires_at<=now():return "Expired"
 if l.click_limit and len(l.clicks)>=l.click_limit:return "Limit reached"
 return "Active"
def dto(l):
 return {"id":l.id,"code":l.code,"original_url":l.original_url,"title":l.title or "","campaign":l.campaign or "General","created_at":l.created_at.isoformat()+"Z","expires_at":l.expires_at.isoformat()+"Z" if l.expires_at else None,"click_limit":l.click_limit,"is_active":l.is_active,"status":state(l),"clicks":len(l.clicks),"short_url":f"{base()}/r/{l.code}"}
def ua(ua):
 u=ua.lower(); bot=any(x in u for x in ["bot","crawler","spider","preview"])
 device="Mobile" if any(x in u for x in ["mobile","android","iphone"]) else ("Tablet" if "ipad" in u else "Desktop")
 browser="Edge" if "edg/" in u else ("Chrome" if "chrome/" in u else ("Firefox" if "firefox/" in u else ("Safari" if "safari/" in u else "Other")))
 return device,browser,bot

def alerts():
    out = []
    t = now()

    for l in Link.query.all():
        recent = Click.query.filter(
            Click.link_id == l.id,
            Click.clicked_at >= t - timedelta(minutes=10)
        ).count()

        bots = Click.query.filter_by(
            link_id=l.id,
            is_bot=True
        ).filter(
            Click.clicked_at >= t - timedelta(hours=24)
        ).count()

        if recent >= 8:
            severity = "High" if recent >= 20 else "Medium"
            reason = f"{recent} clicks recorded in the last 10 minutes."

            save_incident(
                l, "Traffic burst", severity, recent, reason
            )

            out.append({
                "id": f"burst-{l.id}",
                "link_id": l.id,
                "code": l.code,
                "title": l.title or l.code,
                "severity": severity,
                "kind": "Traffic burst",
                "count": recent,
                "reason": reason,
                "recommendation": "Review the source; pause if unexpected."
            })

        if bots >= 5:
            reason = (
                f"{bots} visits matched common bot/crawler "
                "user-agent patterns in 24 hours."
            )

            save_incident(
                l, "Bot-like traffic", "Medium", bots, reason
            )

            out.append({
                "id": f"bot-{l.id}",
                "link_id": l.id,
                "code": l.code,
                "title": l.title or l.code,
                "severity": "Medium",
                "kind": "Bot-like traffic",
                "count": bots,
                "reason": reason,
                "recommendation": (
                    "Check whether link previews or crawlers "
                    "explain this activity."
                )
            })

    return out

class SecurityIncident(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    incident_key = db.Column(db.String(100), unique=True, nullable=False)
    link_id = db.Column(db.Integer, db.ForeignKey("link.id"), nullable=False)
    kind = db.Column(db.String(50), nullable=False)
    severity = db.Column(db.String(20), nullable=False)
    count = db.Column(db.Integer, nullable=False, default=0)
    reason = db.Column(db.Text, nullable=False)
    first_seen = db.Column(db.DateTime, default=now, nullable=False)
    last_seen = db.Column(db.DateTime, default=now, nullable=False)


def save_incident(link, kind, severity, count, reason):
    key = f"{kind}-{link.id}"
    incident = SecurityIncident.query.filter_by(
        incident_key=key
    ).first()

    if incident is None:
        incident = SecurityIncident(
            incident_key=key,
            link_id=link.id,
            kind=kind,
            severity=severity,
            count=count,
            reason=reason,
            first_seen=now(),
            last_seen=now()
        )
        db.session.add(incident)
    else:
        incident.severity = severity
        incident.count = count
        incident.reason = reason
        incident.last_seen = now()

    db.session.commit()

# Rule-based URL Risk Engine. These signals are heuristics, not proof of phishing.

def analyze_url_risk(raw_url):
    import ipaddress
    from urllib.parse import urlparse, unquote

    score = 0
    reasons = []

    try:
        parsed = urlparse((raw_url or "").strip())
        hostname = parsed.hostname or ""
        path_query = unquote(
            (parsed.path or "") + "?" + (parsed.query or "")
        ).lower()

        # 1. HTTPS check
        if parsed.scheme.lower() != "https":
            score += 10
            reasons.append({
                "signal": "HTTPS missing",
                "points": 10,
                "detail": "The destination does not use HTTPS."
            })

        # 2. Raw IP address check
        try:
            ipaddress.ip_address(hostname)
            score += 25
            reasons.append({
                "signal": "IP address used as host",
                "points": 25,
                "detail": "The URL uses an IP address instead of a domain name."
            })
        except ValueError:
            pass

        # 3. Punycode domain check
        if "xn--" in hostname.lower():
            score += 20
            reasons.append({
                "signal": "Punycode hostname",
                "points": 20,
                "detail": "The hostname contains an encoded internationalized domain label."
            })

        # 4. Many subdomains
        if len(hostname.split(".")) >= 5:
            score += 10
            reasons.append({
                "signal": "Many subdomains",
                "points": 10,
                "detail": "The hostname contains many domain labels."
            })

        # 5. @ in URL authority
        if "@" in (parsed.netloc or ""):
            score += 25
            reasons.append({
                "signal": "At-sign in URL authority",
                "points": 25,
                "detail": "The URL authority contains @, which can obscure the actual host."
            })

        # 6. Unusually long URL
        if len(raw_url or "") > 180:
            score += 10
            reasons.append({
                "signal": "Unusually long URL",
                "points": 10,
                "detail": "The URL is longer than 180 characters."
            })

        # 7. Encoded URL
        if "%" in (raw_url or ""):
            score += 10
            reasons.append({
                "signal": "Percent-encoded URL",
                "points": 10,
                "detail": "Encoded characters are present; inspect the URL carefully."
            })

        # 8. Sensitive words: score each distinct matched word
        sensitive = [
            "login", "log-in", "signin", "sign-in", "verify",
            "password", "credential", "wallet", "banking",
            "account", "secure", "update", "token", "reset",
            "confirm", "payment", "billing", "authenticate"
        ]

        matches = sorted({
            word for word in sensitive if word in path_query
        })

        if matches:
            points = min(len(matches) * 5, 20)
            score += points
            reasons.append({
                "signal": "Sensitive keywords in path/query",
                "points": points,
                "detail": "Keywords found: " + ", ".join(matches[:8]) + "."
            })

        # 9. Known URL shorteners
        shorteners = {
            "bit.ly", "tinyurl.com", "t.co",
            "goo.gl", "ow.ly", "is.gd", "buff.ly"
        }

        if hostname.lower() in shorteners:
            score += 10
            reasons.append({
                "signal": "URL shortener",
                "points": 10,
                "detail": "The short URL hides its final destination until resolved."
            })

    except Exception:
        reasons.append({
            "signal": "URL parsing issue",
            "points": 0,
            "detail": "The URL could not be fully analyzed."
        })

    score = min(score, 100)

    if score >= 50:
        level = "High"
        recommendation = (
            "Multiple warning signals were found. Verify the destination "
            "independently before sharing or opening it."
        )
    elif score >= 25:
        level = "Medium"
        recommendation = (
            "Review the flagged signals and confirm the destination "
            "before sharing."
        )
    else:
        level = "Low"
        recommendation = (
            "No strong warning signals were found by these basic checks; "
            "still verify the destination."
        )

    return {
        "risk_score": score,
        "risk_level": level,
        "reasons": reasons,
        "recommendation": recommendation,
        "disclaimer": (
            "Heuristic screening only. This score is not proof that a URL "
            "is safe or malicious."
        )
    }

@app.get("/")
def root(): return jsonify({"name":"LinkPulse API","status":"ok","health":"/api/health"})
@app.get("/api/health")
def health(): return jsonify({"status":"ok","database":"connected"})
@app.get("/api/links")
def links():
 q=(request.args.get("q") or "").lower()
 return jsonify([dto(l) for l in Link.query.order_by(Link.created_at.desc()).all() if not q or q in (l.code+" "+l.original_url+" "+(l.title or "")+" "+(l.campaign or "")).lower()])
@app.post("/api/links")
def create():
 d=request.get_json(silent=True) or {}; u=(d.get("original_url") or "").strip()
 if not valid(u):return jsonify(error="Enter a valid http:// or https:// destination URL."),400
 alias=re.sub(r"[^A-Za-z0-9_-]","",(d.get("alias") or "").strip())
 if alias and len(alias)<3:return jsonify(error="Custom alias must be at least 3 characters."),400
 if len(alias)>32:return jsonify(error="Alias must be 32 characters or fewer."),400
 code=alias or "".join(secrets.choice(string.ascii_letters+string.digits) for _ in range(7))
 if Link.query.filter_by(code=code).first():return jsonify(error="That alias already exists."),409
 try:
  limit=int(d.get("click_limit")) if d.get("click_limit") not in (None,"",0,"0") else None
  if limit is not None and limit<1:raise ValueError()
 except: return jsonify(error="Click limit must be a positive whole number."),400
 expiry=parse_dt(d.get("expires_at")) if d.get("expires_at") else None
 if d.get("expires_at") and (not expiry or expiry<=now()):return jsonify(error="Expiry must be a valid future date."),400
 l=Link(code=code,original_url=u,title=(d.get("title") or "")[:160],campaign=(d.get("campaign") or "General")[:120],click_limit=limit,expires_at=expiry)
 
 db.session.add(l)
 db.session.flush()

 result = analyze_url_risk(l.original_url)
 assessment = RiskAssessment(
     link_id=l.id,
     risk_score=result["risk_score"],
     risk_level=result["risk_level"],
     reasons_json=json.dumps(result["reasons"])
 )
 db.session.add(assessment)
 db.session.commit()
 return jsonify(dto(l)), 201

@app.get("/api/analytics")
def analytics():
 links=Link.query.all(); events=Click.query.order_by(Click.clicked_at.desc()).all(); days={}
 for i in range(6,-1,-1):days[(now()-timedelta(days=i)).date().isoformat()]=0
 devices={}; browsers={}; campaigns={}
 for e in events:
  day=e.clicked_at.date().isoformat()
  if day in days:days[day]+=1
  devices[e.device]=devices.get(e.device,0)+1;browsers[e.browser]=browsers.get(e.browser,0)+1
  c=e.link.campaign or "General";campaigns[c]=campaigns.get(c,0)+1
 top=sorted([{"code":l.code,"title":l.title or l.code,"clicks":len(l.clicks),"campaign":l.campaign} for l in links],key=lambda x:x["clicks"],reverse=True)[:5]
 return jsonify(total_clicks=len(events),total_links=len(links),active_links=sum(state(l)=="Active" for l in links),flagged_links=len(set(a["link_id"] for a in alerts())),weekly=[{"date":k,"clicks":v} for k,v in days.items()],devices=[{"name":k,"value":v} for k,v in devices.items()],browsers=[{"name":k,"value":v} for k,v in browsers.items()],campaigns=[{"name":k,"clicks":v} for k,v in campaigns.items()],top_links=top,recent_clicks=[{"id":e.id,"code":e.link.code,"clicked_at":e.clicked_at.isoformat()+"Z","device":e.device,"browser":e.browser,"referrer":e.referrer,"is_bot":e.is_bot} for e in events[:10]])
@app.get("/api/guard")
def guard():return jsonify(alerts())


@app.get("/api/incidents")
def incident_history():
    rows = SecurityIncident.query.order_by(
        SecurityIncident.last_seen.desc()
    ).limit(100).all()

    result = []

    for x in rows:
        link = db.session.get(Link, x.link_id)

        result.append({
            "id": x.id,
            "link_id": x.link_id,
            "code": link.code if link else None,
            "kind": x.kind,
            "severity": x.severity,
            "count": x.count,
            "reason": x.reason,
            "first_seen": x.first_seen.isoformat() + "Z",
            "last_seen": x.last_seen.isoformat() + "Z"
        })

    return jsonify(result)

@app.post("/api/links/<int:i>/risk-assessment")
def assess_link_risk(i):
 l=Link.query.get_or_404(i)
 result=analyze_url_risk(l.original_url)
 assessment=RiskAssessment(link_id=l.id,risk_score=result["risk_score"],risk_level=result["risk_level"],reasons_json=json.dumps(result["reasons"]))
 db.session.add(assessment);db.session.commit()
 result.update({"id":assessment.id,"link_id":l.id,"assessed_at":assessment.assessed_at.isoformat()+"Z","url":l.original_url,"title":l.title or l.code})
 return jsonify(result),201

@app.get("/api/links/<int:i>/risk-assessments")
def link_risk_history(i):
 Link.query.get_or_404(i)
 rows=RiskAssessment.query.filter_by(link_id=i).order_by(RiskAssessment.assessed_at.desc()).limit(50).all()
 return jsonify([{"id":a.id,"link_id":a.link_id,"assessed_at":a.assessed_at.isoformat()+"Z","risk_score":a.risk_score,"risk_level":a.risk_level,"reasons":json.loads(a.reasons_json)} for a in rows])

@app.patch("/api/links/<int:i>")
def update(i):
 l=Link.query.get_or_404(i);d=request.get_json(silent=True) or {}
 if "is_active" in d:l.is_active=bool(d["is_active"])
 if "title" in d:l.title=(d["title"] or "")[:160]
 db.session.commit();return jsonify(dto(l))
@app.delete("/api/links/<int:i>")
def delete(i):
 l=Link.query.get_or_404(i);db.session.delete(l);db.session.commit();return jsonify(ok=True)
@app.get("/api/links/<int:i>/qr")
def qr(i):
 l=Link.query.get_or_404(i);buf=io.BytesIO();qrcode.make(f"{base()}/r/{l.code}").save(buf,format="PNG");buf.seek(0)
 return send_file(buf,mimetype="image/png",download_name=f"linkpulse-{l.code}.png")
@app.get("/api/export.csv")
def export():
 out=io.StringIO();w=csv.writer(out);w.writerow(["Code","Title","Short URL","Destination","Campaign","Status","Clicks","Created","Expires"])
 for l in Link.query.all():w.writerow([l.code,l.title,f"{base()}/r/{l.code}",l.original_url,l.campaign,state(l),len(l.clicks),l.created_at,l.expires_at or ""])
 return Response(out.getvalue(),mimetype="text/csv",headers={"Content-Disposition":"attachment; filename=linkpulse-links.csv"})
@app.get("/r/<code>")
def resolve(code):
 l=Link.query.filter_by(code=code).first()
 if not l:return Response("<h1>Link not found</h1>",404,mimetype="text/html")
 s=state(l)
 if s!="Active":return Response(f"<h1>Link unavailable</h1><p>This link is {s.lower()}.</p>",410,mimetype="text/html")
 device,browser,bot=ua(request.headers.get("User-Agent",""));ref=(request.referrer or "Direct")[:500]
 db.session.add(Click(link_id=l.id,device=device,browser=browser,is_bot=bot,referrer=ref));db.session.commit()
 return redirect(l.original_url,302)
with app.app_context():db.create_all()
if __name__=="__main__":app.run(host="0.0.0.0",port=int(os.getenv("PORT",5000)),debug=True)
