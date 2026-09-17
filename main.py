import os
from datetime import datetime
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base

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
    available_cash=Column(Float, default=0)
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
    source=Column(String, default="SYSTEM")
    created_at=Column(DateTime, default=datetime.utcnow)

class Agent(Base):
    __tablename__="ai_agents"
    id=Column(Integer, primary_key=True, autoincrement=True)
    name=Column(String)
    description=Column(String)
    capital_allocated=Column(Float, default=0)
    revenue=Column(Float, default=0)
    expenses=Column(Float, default=0)
    net_income=Column(Float, default=0)
    roi=Column(Float, default=0)
    status=Column(String, default="ACTIVE")

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
        return {
            "starting": p.starting_capital if p else 10000,
            "total": p.current_total_value if p else sum(d.current_value for d in divs),
            "deployed": p.total_deployed if p else 10000,
            "divisions": {
                "MALI": {"current": m["MALI"].current_value, "pct": 60, "role": m["MALI"].role},
                "ZIIDI": {"current": m["ZIIDI"].current_value, "pct": 30, "role": m["ZIIDI"].role},
                "TILISI AI AGENTS": {"current": m["TILISI AI AGENTS"].current_value, "pct": 10, "income": income},
            }
        }
    finally: db.close()

def get_signals():
    db = SessionLocal()
    try:
        divs = {d.name: d for d in db.query(Division).all()}
        def perf(d): return (d.current_value - d.initial_capital)/d.initial_capital*100 if d.initial_capital else 0
        return {
            "MALI": {"signal": "UP" if perf(divs["MALI"])>=0 else "DOWN", "strength": f"{perf(divs['MALI']):+.1f}%"},
            "ZIIDI": {"signal": "STABLE" if abs(perf(divs["ZIIDI"]))<5 else "WARNING", "strength": f"{perf(divs['ZIIDI']):+.1f}%"},
            "TILISI AI AGENTS": {"signal": "GENERATING", "strength": f"ROI {perf(divs['TILISI AI AGENTS']):+.1f}%"},
        }
    finally: db.close()

app = FastAPI(title="TILISI HEDGE FUND BOT", version="3.1.0-official")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
def startup():
    init_db()
    seed()

@app.get("/health")
def health(): return {"status":"OK","bot":"TILISI HEDGE FUND BOT","version":"3.1.0","private":True}

@app.get("/api/portfolio")
def portfolio(): return get_summary()

@app.get("/api/divisions")
def divisions():
    db = SessionLocal()
    try: return [{"name": d.name, "allocation": d.allocation_percentage, "initial": d.initial_capital, "current": d.current_value, "role": d.role, "philosophy": d.philosophy} for d in db.query(Division).all()]
    finally: db.close()

@app.get("/api/signals")
def signals(): return get_signals()

@app.get("/api/transactions")
def txs():
    db = SessionLocal()
    try: return [{"id": t.id, "division": t.division_name, "type": t.type, "amount": t.amount, "old": t.old_value, "new": t.new_value} for t in db.query(Transaction).order_by(Transaction.id.desc()).limit(50).all()]
    finally: db.close()

@app.post("/api/transactions")
def create_tx(division_name: str, type: str, amount: float):
    db = SessionLocal()
    try:
        div = db.query(Division).filter(Division.name==division_name.upper()).first()
        if not div: return {"error":"Division not found"}
        old = div.current_value
        if type in ["INCOME","PROFIT","RETURN"]: new = old + amount
        elif type in ["LOSS","EXPENSE"]: new = old - amount
        else: new = old
        if type in ["INCOME","PROFIT","LOSS","EXPENSE"]: div.current_value = new
        db.add(Transaction(division_name=div.name, type=type, amount=amount, old_value=old, new_value=new))
        port = db.query(Portfolio).first()
        if port: port.current_total_value = sum(d.current_value for d in db.query(Division).all())
        db.commit()
        return {"ok": True, "old": old, "new": new}
    finally: db.close()

@app.get("/", response_class=HTMLResponse)
def dashboard():
    s = get_summary()
    sig = get_signals()
    return f"""
<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<style>:root{{--navy:#0a1931;--sky:#38bdf8;--gold:#facc15;--white:#fff}}body{{margin:0;background:var(--navy);color:var(--white);font-family:system-ui;padding:12px}}.header{{background:#0f2447;border:1px solid #1e3a5f;border-bottom:3px solid var(--sky);border-radius:14px;padding:14px;display:flex;justify-content:space-between}}.kpi{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-top:12px}}.card{{background:#0f2447;border:1px solid #1e3a5f;border-radius:12px;padding:14px}}.signals{{margin-top:14px;background:#0f2447;border-radius:14px;padding:14px;border:1px solid #1e3a5f}}.row{{display:flex;justify-content:space-between;padding:12px 0;border-bottom:1px solid #1e293b}}.badge{{padding:6px 12px;border-radius:999px;font-weight:800;font-size:12px}}@media(max-width:800px){{.kpi{{grid-template-columns:1fr}}}}</style>
</head><body>
<div class="header"><div><b>TILISI</b> <span style="color:#38bdf8">HEDGE FUND PORTFOLIO</span><br><small style="color:#94a3b8">OFFICIAL • LIVE • MARKET OPEN</small></div><div style="color:#38bdf8;border:1px solid #38bdf8;border-radius:999px;padding:4px 10px;font-size:11px">BOT LIVE 🟢</div></div>
<div class="kpi">
<div class="card" style="border-top:4px solid #38bdf8"><div style="color:#38bdf8;font-weight:800">MALI 60%</div><div style="font-size:22px;font-weight:900">{s['divisions']['MALI']['current']} KES</div><div style="font-size:11px">Control / Standards / Process<br>How do we control the game?</div></div>
<div class="card" style="border-top:4px solid #fff"><div style="font-weight:800">ZIIDI 30%</div><div style="font-size:22px;font-weight:900">{s['divisions']['ZIIDI']['current']} KES</div><div style="font-size:11px">Resilience / Defense / Survival<br>How do we avoid losing it?</div></div>
<div class="card" style="border-top:4px solid #facc15"><div style="color:#facc15;font-weight:800">TILISI AI AGENTS 10%</div><div style="font-size:22px;font-weight:900">{s['divisions']['TILISI AI AGENTS']['current']} KES</div><div style="font-size:11px;color:#fde68a">Income {s['divisions']['TILISI AI AGENTS']['income']} KES<br>How do we build something that keeps winning?</div></div>
</div>
<div class="signals"><b>SIGNALS</b> • No Graph
<div class="row"><span style="color:#38bdf8">MALI CONTROL SIGNAL</span><span class="badge" style="background:#38bdf8;color:#0a1931">{sig['MALI']['signal']} {sig['MALI']['strength']}</span></div>
<div class="row"><span>ZIIDI DEFENSE SIGNAL</span><span class="badge" style="border:1px solid #fff">{sig['ZIIDI']['signal']}</span></div>
<div class="row" style="border:none"><span style="color:#facc15">AI AGENTS LEGACY SIGNAL</span><span class="badge" style="background:#facc15;color:#0a1931">{sig['TILISI AI AGENTS']['signal']}</span></div>
<div style="margin-top:12px;border-top:1px solid #1e3a5f;padding-top:8px;font-size:11px;text-align:center">THINK • PLAN • EXECUTE • EVOLVE<br>INSTITUTIONAL • RISK MANAGED • PRIVATE • CONFIDENTIAL</div>
</div>
<div style="text-align:center;margin-top:14px"><span style="background:#facc15;color:#0a1931;padding:8px 18px;border-radius:999px;font-weight:900">TOTAL DEPLOYED {s['deployed']} KES • VALUE {s['total']} KES</span></div>
</body></html>
"""
