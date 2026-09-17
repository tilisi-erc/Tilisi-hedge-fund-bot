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

def init_db(): Base.metadata.create_all(bind=engine)
def seed():
    db=SessionLocal()
    try:
        if db.query(Portfolio).first(): return
        db.add(Portfolio(id="TILISI-001", starting_capital=10000, current_total_value=10000, total_deployed=10000))
        db.add_all([
            Division(name="MALI", allocation_percentage=60, initial_capital=6000, current_value=6000, role="Control / Standards / Process", philosophy="How do we control the game?"),
            Division(name="ZIIDI", allocation_percentage=30, initial_capital=3000, current_value=3000, role="Resilience / Defense / Survival", philosophy="How do we avoid losing it?"),
            Division(name="TILISI AI AGENTS", allocation_percentage=10, initial_capital=1000, current_value=1000, role="Longevity / Culture / Legacy", philosophy="How do we keep winning?"),
        ])
        db.commit()
    finally: db.close()

def get_summary():
    db=SessionLocal()
    try:
        p=db.query(Portfolio).first()
        divs=db.query(Division).all()
        m={d.name:d for d in divs}
        inc=sum(t.amount for t in db.query(Transaction).filter(Transaction.division_name=="TILISI AI AGENTS", Transaction.type=="INCOME").all())
        total = p.current_total_value if p else sum(d.current_value for d in divs)
        return {"total":total, "deployed":p.total_deployed if p else 10000, "divisions":m, "income":inc, "txs":db.query(Transaction).order_by(Transaction.id.desc()).limit(12).all()}
    finally: db.close()

app=FastAPI(title="TILISI HEDGE FUND BOT", version="4.0-pro-matrix")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
@app.on_event("startup")
def startup(): init_db(); seed()

class TxIn(BaseModel):
    division_name: str
    type: str
    amount: float

@app.get("/health")
def health(): return {"status":"OK"}

@app.post("/api/transactions")
def create_tx(data: TxIn):
    db=SessionLocal()
    try:
        div=db.query(Division).filter(Division.name==data.division_name.upper()).first()
        if not div: return {"error":"not found"}
        old=div.current_value
        new=old+data.amount if data.type=="INCOME" else old-data.amount
        div.current_value=new
        db.add(Transaction(division_name=div.name, type=data.type, amount=data.amount, old_value=old, new_value=new))
        port=db.query(Portfolio).first()
        if port: port.current_total_value=sum(d.current_value for d in db.query(Division).all())
        db.commit()
        return {"ok":True,"new":new}
    finally: db.close()

@app.get("/", response_class=HTMLResponse)
def dashboard():
    s=get_summary(); m=s["divisions"]
    pnl = s["total"]-s["deployed"]
    return f"""
<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap" rel="stylesheet">
<style>
*{{font-family:Inter,system-ui;margin:0;box-sizing:border-box}}
body{{background:#070e1f;color:#e2e8f0;padding:10px}}
.header{{display:flex;justify-content:space-between;align-items:center;padding:12px 4px}}
.logo{{font-weight:800;letter-spacing:.08em;font-size:13px}}
.live{{border:1px solid #38bdf8;color:#38bdf8;border-radius:20px;padding:3px 10px;font-size:10px;font-weight:800}}
.matrix{{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}}
@media(max-width:700px){{.matrix{{grid-template-columns:1fr 1fr}}.matrix .full{{grid-column:1/-1}}}}
.card{{background:#0e1c36;border:1px solid #1e355e;border-radius:10px;padding:10px;position:relative;overflow:hidden}}
.card .top{{font-size:9px;letter-spacing:.12em;color:#64748b;font-weight:800;margin-bottom:6px}}
.card .val{{font-size:18px;font-weight:800;line-height:1}}
.card .sub{{font-size:10px;color:#94a3b8;margin-top:4px}}
.card.mali{{border-top:2px solid #38bdf8}} .card.ziidi{{border-top:2px solid #e2e8f0}} .card.ai{{border-top:2px solid #facc15}}
.card.ai .val{{color:#facc15}}
.row{{display:grid;grid-template-columns:1.2fr .8fr;gap:8px;margin-top:8px}}
@media(max-width:700px){{.row{{grid-template-columns:1fr}}}}
.ctrl{{background:#0e1c36;border:1px solid #1e355e;border-radius:10px;padding:10px}}
.ctrl h3{{font-size:11px;letter-spacing:.08em;margin-bottom:8px}}
.ctrl-grid{{display:grid;grid-template-columns:1fr 1fr auto auto;gap:6px;align-items:end}}
@media(max-width:700px){{.ctrl-grid{{grid-template-columns:1fr 1fr}}}}
select,input{{background:#0b1428;border:1px solid #1e355e;color:#fff;border-radius:8px;padding:8px 10px;font-size:12px;width:100%;height:36px}}
.btn{{height:36px;padding:0 14px;border-radius:8px;border:none;font-size:11px;font-weight:800;cursor:pointer;white-space:nowrap}}
.btn-add{{background:#38bdf8;color:#071020}} .btn-loss{{background:#1e293b;color:#94a3b8;border:1px solid #334155}}
.stats{{display:flex;gap:12px;font-size:10px;color:#64748b;margin-top:6px}}
.stats b{{color:#e2e8f0}}
.tx{{font-size:11px;display:flex;justify-content:space-between;padding:7px 0;border-bottom:1px solid #13223f}}
.pill{{font-size:9px;padding:2px 6px;border-radius:10px;background:#13223f}}
</style></head><body>
<div class="header"><div class="logo">TILISI / HEDGE FUND BOT</div><div class="live">● LIVE</div></div>

<div class="matrix">
  <div class="card mali"><div class="top">MALI — 60% • CONTROL</div><div class="val">{m['MALI'].current_value:.0f} KES</div><div class="sub">Standards / Process</div><div class="stats"><span><b>{m['MALI'].allocation_percentage:.0f}%</b> ALLOC</span><span><b>{m['MALI'].current_value-m['MALI'].initial_capital:+.0f}</b> PnL</span></div></div>
  <div class="card ziidi"><div class="top">ZIIDI — 30% • RESILIENCE</div><div class="val">{m['ZIIDI'].current_value:.0f} KES</div><div class="sub">Defense / Survival</div><div class="stats"><span><b>{m['ZIIDI'].allocation_percentage:.0f}%</b> ALLOC</span><span><b>{m['ZIIDI'].current_value-m['ZIIDI'].initial_capital:+.0f}</b> PnL</span></div></div>
  <div class="card ai full"><div class="top">TILISI AI AGENTS — 10% • LONGEVITY</div><div class="val">{m['TILISI AI AGENTS'].current_value:.0f} KES</div><div class="sub">Culture / Legacy • Income {s['income']:.0f} KES</div><div class="stats"><span><b>{m['TILISI AI AGENTS'].allocation_percentage:.0f}%</b> ALLOC</span><span><b>{m['TILISI AI AGENTS'].current_value-m['TILISI AI AGENTS'].initial_capital:+.0f}</b> PnL</span></div></div>
</div>

<div class="row">
  <div class="ctrl">
    <h3>EXECUTION MATRIX</h3>
    <div class="ctrl-grid">
      <select id="div"><option>MALI</option><option>ZIIDI</option><option>TILISI AI AGENTS</option></select>
      <input id="amt" type="number" placeholder="Amount">
      <button class="btn btn-add" onclick="send('INCOME')">+ ADD</button>
      <button class="btn btn-loss" onclick="send('LOSS')">- SUB</button>
    </div>
    <div id="msg" style="font-size:10px;color:#facc15;margin-top:6px;height:12px"></div>
  </div>
  <div class="ctrl">
    <h3>PORTFOLIO • {s['deployed']:.0f} DEPLOYED / {s['total']:.0f} VALUE • <span style="color:{'#22c55e' if pnl>=0 else '#ef4444'}">{pnl:+.0f} KES</span></h3>
    <div style="max-height:132px;overflow:auto">
    {''.join([f"<div class='tx'><span><span class='pill'>{t.division_name[:4]}</span> {t.type} {t.amount:.0f}</span><span style='color:#475569'>{t.old_value:.0f}→{t.new_value:.0f}</span></div>" for t in s['txs']])}
    </div>
  </div>
</div>

<div style="text-align:center;margin-top:10px;font-size:9px;letter-spacing:.15em;color:#334155">THINK • PLAN • EXECUTE • EVOLVE — PRIVATE & CONFIDENTIAL</div>

<script>
async function send(type){{
 const div=document.getElementById('div').value;
 const amt=parseFloat(document.getElementById('amt').value);
 if(!amt){{document.getElementById('msg').innerText='Enter amount';return;}}
 document.getElementById('msg').innerText='Executing...';
 const r=await fetch('/api/transactions',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{division_name:div,type:type,amount:amt}})}});
 const j=await r.json();
 if(j.ok){{document.getElementById('msg').innerText='Done ✓';setTimeout(()=>location.reload(),500)}} else {{document.getElementById('msg').innerText='Error'}}
}}
</script>
</body></html>
"""
