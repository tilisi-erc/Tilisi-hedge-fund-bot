from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from app.api import portfolio, divisions, transactions, positions, signals, health, agents
from app.database import init_db, seed

app = FastAPI(title="TILISI HEDGE FUND BOT", version="3.1.0-official")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
def startup():
    init_db()
    seed()

app.include_router(health.router)
app.include_router(portfolio.router)
app.include_router(divisions.router)
app.include_router(transactions.router)
app.include_router(positions.router)
app.include_router(signals.router)
app.include_router(agents.router)

@app.get("/", response_class=HTMLResponse)
def dashboard():
    from app.services.portfolio_service import get_portfolio_summary
    from app.services.signal_service import get_signals
    p = get_portfolio_summary()
    s = get_signals()
    return f"""
<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<title>TILISI</title>
<style>:root{{--navy:#0a1931;--sky:#38bdf8;--gold:#facc15;--white:#fff}}body{{margin:0;background:var(--navy);color:var(--white);font-family:system-ui;padding:12px}}.header{{background:#0f2447;border:1px solid #1e3a5f;border-bottom:3px solid var(--sky);border-radius:14px;padding:14px;display:flex;justify-content:space-between}}.kpi{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-top:12px}}.card{{background:#0f2447;border:1px solid #1e3a5f;border-radius:12px;padding:14px}}.signals{{margin-top:14px;background:#0f2447;border-radius:14px;padding:14px;border:1px solid #1e3a5f}}.row{{display:flex;justify-content:space-between;padding:12px 0;border-bottom:1px solid #1e293b}}.badge{{padding:6px 12px;border-radius:999px;font-weight:800;font-size:12px}}@media(max-width:800px){{.kpi{{grid-template-columns:1fr}}}}</style>
</head><body>
<div class="header"><div><b>TILISI</b> <span style="color:var(--sky)">HEDGE FUND PORTFOLIO</span><br><small style="color:#94a3b8">OFFICIAL • LIVE • MARKET OPEN</small></div><div style="color:var(--sky);border:1px solid var(--sky);border-radius:999px;padding:4px 10px;font-size:11px">BOT LIVE 🟢</div></div>
<div class="kpi">
<div class="card" style="border-top:4px solid var(--sky)"><div style="color:var(--sky);font-weight:800">MALI 60%</div><div style="font-size:22px;font-weight:900">{p['divisions']['MALI']['current_value']} KES</div><div>Control / Standards / Process</div><small>How do we control the game?</small></div>
<div class="card" style="border-top:4px solid var(--white)"><div style="font-weight:800">ZIIDI 30%</div><div style="font-size:22px;font-weight:900">{p['divisions']['ZIIDI']['current_value']} KES</div><div>Resilience / Defense / Survival</div><small>How do we avoid losing it?</small></div>
<div class="card" style="border-top:4px solid var(--gold)"><div style="color:var(--gold);font-weight:800">TILISI AI AGENTS 10%</div><div style="font-size:22px;font-weight:900">{p['divisions']['TILISI AI AGENTS']['current_value']} KES</div><div style="color:var(--gold)">Income {p['divisions']['TILISI AI AGENTS']['income']} KES</div><small>How do we build something that keeps winning?</small></div>
</div>
<div class="signals"><b>SIGNALS</b>
<div class="row"><span style="color:var(--sky)">MALI CONTROL SIGNAL</span><span class="badge" style="background:var(--sky);color:var(--navy)">{s['MALI']['signal']} {s['MALI']['strength']}</span></div>
<div class="row"><span>ZIIDI DEFENSE SIGNAL</span><span class="badge" style="border:1px solid #fff">{s['ZIIDI']['signal']}</span></div>
<div class="row" style="border:none"><span style="color:var(--gold)">AI AGENTS LEGACY SIGNAL</span><span class="badge" style="background:var(--gold);color:var(--navy)">{s['TILISI AI AGENTS']['signal']}</span></div>
<div style="margin-top:12px;border-top:1px solid #1e3a5f;padding-top:8px;font-size:11px"><b>PHILOSOPHY</b><br>MALI: How do we control the game? • Control Standards Process<br>ZIIDI: How do we avoid losing it? • Resilience Defense Survival<br>AI AGENTS: How do we build something that keeps winning? • Longevity Culture Legacy</div>
</div>
<div style="text-align:center;margin-top:14px"><span style="background:var(--gold);color:var(--navy);padding:8px 18px;border-radius:999px;font-weight:900">TOTAL DEPLOYED {p['total_deployed']} KES • VALUE {p['current_total_value']} KES</span></div>
<div style="text-align:center;letter-spacing:3px;margin-top:12px;font-size:10px;color:#475569">THINK • PLAN • EXECUTE • EVOLVE • INSTITUTIONAL • RISK MANAGED • PRIVATE • CONFIDENTIAL</div>
</body></html>
"""
