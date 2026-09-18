import os, csv, io
from datetime import datetime
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse
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

class Division(Base):
    __tablename__="divisions"
    id=Column(Integer, primary_key=True, autoincrement=True)
    name=Column(String, unique=True)
    allocation_percentage=Column(Float)
    initial_capital=Column(Float)
    current_value=Column(Float)
    role=Column(String)

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
        db.add(Portfolio(id="TILISI-001"))
        db.add_all([
            Division(name="MALI", allocation_percentage=60, initial_capital=6000, current_value=6000, role="Control"),
            Division(name="ZIIDI", allocation_percentage=30, initial_capital=3000, current_value=3000, role="Resilience"),
            Division(name="TILISI AI AGENTS", allocation_percentage=10, initial_capital=1000, current_value=1000, role="Legacy"),
        ])
        db.commit()
    finally: db.close()

def get_summary():
    db=SessionLocal()
    try:
        p=db.query(Portfolio).first()
        divs=db.query(Division).all()
        m={d.name:d for d in divs}
        txs=db.query(Transaction).order_by(Transaction.created_at.asc()).all()
        # Build chart data
        chart_labels=[]; chart_total=[]
        running = {d.name: d.initial_capital for d in divs}
        total_points = [{"t": d.initial_capital} for d in divs]
        # simplified: total value over time
        hist=[]; cur_total=sum(running.values())
        hist.append(cur_total)
        labels=["Start"]
        for t in txs:
            if t.type=="INCOME": running[t.division_name]+=t.amount
            else: running[t.division_name]-=t.amount
            cur_total=sum(running.values())
            hist.append(cur_total)
            labels.append(t.created_at.strftime("%m/%d %H:%M"))
        income_ai = sum(t.amount for t in txs if t.division_name=="TILISI AI AGENTS" and t.type=="INCOME")
        return {"total":sum(d.current_value for d in divs), "deployed":10000, "divisions":m, "income":income_ai, "txs":list(reversed(txs))[:20], "chart_labels":labels[-20:], "chart_data":hist[-20:]}
    finally: db.close()

app=FastAPI(title="TILISI HEDGE FUND BOT", version="4.5-extras-light")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
@app.on_event("startup")
def startup(): init_db(); seed()

class TxIn(BaseModel):
    division_name: str; type: str; amount: float

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
        db.commit()
        return {"ok":True}
    finally: db.close()

@app.get("/export/csv")
def export_csv():
    db=SessionLocal()
    try:
        txs=db.query(Transaction).order_by(Transaction.id.asc()).all()
        output=io.StringIO()
        w=csv.writer(output)
        w.writerow(["Date","Division","Type","Amount","Old","New"])
        for t in txs: w.writerow([t.created_at, t.division_name, t.type, t.amount, t.old_value, t.new_value])
        output.seek(0)
        return StreamingResponse(io.BytesIO(output.getvalue().encode()), media_type="text/csv", headers={"Content-Disposition":"attachment; filename=tilisi_statement.csv"})
    finally: db.close()

@app.get("/", response_class=HTMLResponse)
def dashboard():
    s=get_summary(); m=s["divisions"]; pnl=s["total"]-s["deployed"]
    return f"""
<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
*{{font-family:Inter,system-ui;box-sizing:border-box;margin:0}}
body{{background:#070e1f;color:#e2e8f0;padding:10px}}
.matrix{{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}} @media(max-width:700px){{.matrix{{grid-template-columns:1fr}}}}
.card{{background:#0e1c36;border:1px solid #1e355e;border-radius:10px;padding:10px}}
.card.mali{{border-top:2px solid #38bdf8}} .card.ziidi{{border-top:2px solid #e2e8f0}} .card.ai{{border-top:2px solid #facc15}}
.card .top{{font-size:9px;color:#64748b;font-weight:800;letter-spacing:.1em}} .val{{font-size:18px;font-weight:800}}
.ctrl{{background:#0e1c36;border:1px solid #1e355e;border-radius:10px;padding:10px;margin-top:8px}}
select,input{{background:#0b1428;border:1px solid #1e355e;color:#fff;border-radius:8px;padding:0 10px;height:34px;font-size:12px;width:100%}}
.btn{{height:34px;padding:0 12px;border-radius:8px;border:none;font-size:11px;font-weight:800;cursor:pointer}} .btn-add{{background:#38bdf8}} .btn-loss{{background:#1e293b;color:#94a3b8;border:1px solid #334155}}
.grid2{{display:grid;grid-template-columns:1.1fr .9fr;gap:8px;margin-top:8px}} @media(max-width:700px){{.grid2{{grid-template-columns:1fr}}}}
</style></head><body>
<div style="display:flex;justify-content:space-between;padding:6px 0;font-size:12px;font-weight:800;letter-spacing:.08em">TILISI / HEDGE FUND BOT <span style="border:1px solid #38bdf8;color:#38bdf8;border-radius:20px;padding:2px 8px;font-size:9px">● LIVE</span></div>

<div class="matrix">
<div class="card mali"><div class="top">MALI 60% • CONTROL</div><div class="val">{m['MALI'].current_value:.0f} KES</div><div style="font-size:10px;color:#94a3b8">{m['MALI'].current_value-m['MALI'].initial_capital:+.0f} PnL</div></div>
<div class="card ziidi"><div class="top">ZIIDI 30% • RESILIENCE</div><div class="val">{m['ZIIDI'].current_value:.0f} KES</div><div style="font-size:10px;color:#94a3b8">{m['ZIIDI'].current_value-m['ZIIDI'].initial_capital:+.0f} PnL</div></div>
<div class="card ai"><div class="top">AI AGENTS 10% • LONGEVITY</div><div class="val" style="color:#facc15">{m['TILISI AI AGENTS'].current_value:.0f} KES</div><div style="font-size:10px;color:#facc15">Income {s['income']:.0f} KES</div></div>
</div>

<div class="grid2">
<div class="ctrl">
<h3 style="font-size:10px;letter-spacing:.1em;margin-bottom:8px">EXECUTION MATRIX</h3>
<div style="display:grid;grid-template-columns:1fr 1fr auto auto;gap:6px">
<select id="div"><option>MALI</option><option>ZIIDI</option><option>TILISI AI AGENTS</option></select>
<input id="amt" type="number" placeholder="Amount">
<button class="btn btn-add" onclick="send('INCOME')">+ADD</button>
<button class="btn btn-loss" onclick="send('LOSS')">-SUB</button>
</div>
<div id="msg" style="font-size:10px;color:#facc15;margin-top:6px;height:12px"></div>
<div style="margin-top:10px"><canvas id="growth" height="140"></canvas></div>
</div>

<div class="ctrl">
<h3 style="font-size:10px;letter-spacing:.1em;display:flex;justify-content:space-between">AI AGENT TRACKER • TOTAL {s['total']:.0f} ({pnl:+.0f}) <a href="/export/csv" style="color:#38bdf8;text-decoration:none">↓ CSV</a></h3>
<div style="background:#0b1428;border-radius:8px;padding:8px;margin:8px 0;font-size:11px">
<div style="display:flex;justify-content:space-between"><span>🤖 AI Income Generated</span><b style="color:#facc15">{s['income']:.0f} KES</b></div>
<div style="display:flex;justify-content:space-between;margin-top:4px"><span>📈 Total Portfolio PnL</span><b style="color:{'#22c55e' if pnl>=0 else '#ef4444'}">{pnl:+.0f} KES</b></div>
<div style="display:flex;justify-content:space-between;margin-top:4px"><span>🛡️ ZIIDI Safety Ratio</span><b>{m['ZIIDI'].current_value/s['total']*100:.1f}%</b></div>
</div>
<div style="max-height:220px;overflow:auto;font-size:11px">
{''.join([f"<div style='display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid #13223f'><span>{t.division_name[:4]} {t.type} {t.amount:.0f}</span><span style='color:#475569'>{t.created_at.strftime('%m/%d %H:%M')}</span></div>" for t in s['txs']])}
</div>
</div>
</div>

<script>
const labels={s['chart_labels']};
const data={s['chart_data']};
new Chart(document.getElementById('growth'),{{type:'line',data:{{labels:labels,datasets:[{{label:'Total Value',data:data,borderColor:'#38bdf8',backgroundColor:'rgba(56,189,248,0.1)',fill:true,tension:0.4,pointRadius:0}}]}},options:{{plugins:{{legend:{{display:false}}}} ,scales:{{x:{{ticks:{{font:{{size:8}},color:'#475569'}},grid:{{display:false}}}},y:{{ticks:{{font:{{size:8}},color:'#475569'}},grid:{{color:'#13223f'}}}}}}}}}});
async function send(type){{const d=document.getElementById('div').value;const a=parseFloat(document.getElementById('amt').value);if(!a){{document.getElementById('msg').innerText='Weka amount';return;}}document.getElementById('msg').innerText='Executing...';const r=await fetch('/api/transactions',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{division_name:d,type:type,amount:a}})}});if((await r.json()).ok){{document.getElementById('msg').innerText='Done ✓';setTimeout(()=>location.reload(),600)}}}}
</script>
</body></html>
"""
