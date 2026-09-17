import os
from datetime import datetime
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
from pydantic import BaseModel

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./tilisi.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()

class Portfolio(Base):
    __tablename__="portfolios"
    id=Column(String, primary_key=True)
    starting_capital=Column(Float, default=10000)
    current_total_value=Column(Float, default=10000)
    total_deployed=Column(Float, default=10000)
    last_updated=Column(DateTime, default=datetime.utcnow)

class Division(Base):
    __tablename__="divisions"
    id=Column(Integer, primary_key=True, autoincrement=True)
    name=Column(String, unique=True)
    allocation_percentage=Column(Float)
    initial_capital=Column(Float)
    current_value=Column(Float)
    role=Column(String)
    philosophy=Column(String)
    status=Column(String, default="ACTIVE")

class Transaction(Base):
    __tablename__="transactions"
    id=Column(Integer, primary_key=True, autoincrement=True)
    division_name=Column(String)
    type=Column(String)
    amount=Column(Float)
    old_value=Column(Float)
    new_value=Column(Float)
    created_at=Column(DateTime, default=datetime.utcnow)

def init_db():
    Base.metadata.create_all(bind=engine)

def seed():
    db = SessionLocal()
    try:
        if db.query(Portfolio).first(): return
        db.add(Portfolio(id="TILISI-001", starting_capital=10000, current_total_value=10000, total_deployed=10000))
        db.add_all([
            Division(name="MALI", allocation_percentage=60, initial_capital=6000, current_value=6000, role="Control / Standards / Process", philosophy="How do we control the game?"),
            Division(name="ZIIDI", allocation_percentage=30, initial_capital=3000, current_value=3000, role="Resilience / Defense / Survival", philosophy="How do we avoid losing it?"),
            Division(name="TILISI AI AGENTS", allocation_percentage=10, initial_capital=1000, current_value=1000, role="Longevity / Culture / Legacy", philosophy="How do we build something that keeps winning?"),
        ])
        db.commit()
    finally: db.close()

def get_summary():
    db = SessionLocal()
    try:
        p = db.query(Portfolio).first()
        divs = db.query(Division).all()
        m = {d.name: d for d in divs}
        income = sum(t.amount for t in db.query(Transaction).filter(Transaction.division_name=="TILISI AI AGENTS", Transaction.type=="INCOME").all())
        return {"total": p.current_total_value if p else sum(d.current_value for d in divs), "deployed": p.total_deployed if p else 10000, "divisions": m, "income": income, "txs": db.query(Transaction).order_by(Transaction.id.desc()).limit(10).all()}
    finally: db.close()

app = FastAPI(title="TILISI HEDGE FUND BOT", version="3.2-buttons")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
def startup():
    init_db()
    seed()

class TxIn(BaseModel):
    division_name: str
    type: str
    amount: float

@app.get("/health")
def health(): return {"status":"OK"}

@app.get("/api/portfolio")
def portfolio():
    db = SessionLocal()
    try:
        s = get_summary()
        return {"total": s["total"], "divisions": {k: {"current": v.current_value, "initial": v.initial_capital} for k,v in s["divisions"].items()}}
    finally: db.close()

@app.post("/api/transactions")
def create_tx(data: TxIn):
    db = SessionLocal()
    try:
        div = db.query(Division).filter(Division.name==data.division_name.upper()).first()
        if not div: return {"error":"Division not found"}
        old = div.current_value
        new = old + data.amount if data.type=="INCOME" else old - data.amount
        div.current_value = new
        db.add(Transaction(division_name=div.name, type=data.type, amount=data.amount, old_value=old, new_value=new))
        port = db.query(Portfolio).first()
        if port: port.current_total_value = sum(d.current_value for d in db.query(Division).all())
        db.commit()
        return {"ok": True, "new": new}
    finally: db.close()

@app.get("/", response_class=HTMLResponse)
def dashboard():
    s = get_summary()
    m = s["divisions"]
    return f"""
<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
body{{margin:0;background:#0a1931;color:#fff;font-family:system-ui;padding:12px}}
.card{{background:#0f2447;border:1px solid #1e3a5f;border-radius:12px;padding:14px;margin-top:10px}}
.kpi{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px}}
select,input,button{{width:100%;padding:12px;border-radius:10px;border:1px solid #1e3a5f;margin-top:8px;font-weight:700}}
button{{background:#38bdf8;color:#0a1931;border:none;cursor:pointer}}
button.loss{{background:#ef4444;color:#fff}}
.badge{{padding:4px 8px;border-radius:999px;font-size:11px;font-weight:800}}
@media(max-width:800px){{.kpi{{grid-template-columns:1fr}}}}
</style></head><body>
<div style="display:flex;justify-content:space-between;align-items:center"><b>TILISI HEDGE FUND</b><span style="border:1px solid #38bdf8;color:#38bdf8;border-radius:999px;padding:4px 10px;font-size:11px">LIVE 🟢</span></div>

<div class="kpi">
<div class="card" style="border-top:4px solid #38bdf8"><small>MALI 60%</small><div style="font-size:22px;font-weight:900">{m['MALI'].current_value} KES</div><small>{m['MALI'].role}</small></div>
<div class="card" style="border-top:4px solid #fff"><small>ZIIDI 30%</small><div style="font-size:22px;font-weight:900">{m['ZIIDI'].current_value} KES</div><small>{m['ZIIDI'].role}</small></div>
<div class="card" style="border-top:4px solid #facc15"><small>TILISI AI AGENTS 10%</small><div style="font-size:22px;font-weight:900;color:#facc15">{m['TILISI AI AGENTS'].current_value} KES</div><small>Income {s['income']} KES</small></div>
</div>

<div class="card">
<b>ONGEZA / TOA PESA (Buttons ziko hapa sasa)</b>
<select id="div"><option>MALI</option><option>ZIIDI</option><option>TILISI AI AGENTS</option></select>
<input id="amt" type="number" placeholder="Amount eg 500">
<button onclick="send('INCOME')">➕ ONGEZA PESA (INCOME)</button>
<button class="loss" onclick="send('LOSS')">➖ TOA PESA (LOSS/EXPENSE)</button>
<div id="msg" style="margin-top:8px;color:#facc15"></div>
</div>

<div class="card"><b>TOTAL DEPLOYED</b> {s['deployed']} KES | <b>VALUE</b> {s['total']} KES<br><br>
<b>LAST TRANSACTIONS</b><br>
{''.join([f"<div style='border-bottom:1px solid #1e293b;padding:6px 0;display:flex;justify-content:space-between'><span>{t.division_name} {t.type} {t.amount}</span><span style='color:#94a3b8'>{t.old_value}->{t.new_value}</span></div>" for t in s['txs']])}
</div>

<script>
async function send(type){{
  const div=document.getElementById('div').value;
  const amt=parseFloat(document.getElementById('amt').value);
  if(!amt){{document.getElementById('msg').innerText='Weka amount!';return;}}
  document.getElementById('msg').innerText='Ina-update...';
  const r=await fetch('/api/transactions',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{division_name:div,type:type,amount:amt}})}});
  const j=await r.json();
  if(j.ok){{document.getElementById('msg').innerText='Imefanikiwa! Ina-reload...';setTimeout(()=>location.reload(),800)}} else {{document.getElementById('msg').innerText='Error: '+JSON.stringify(j)}}
}}
</script>
</body></html>
"""
