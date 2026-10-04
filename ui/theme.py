"""Global CSS for the dark 'Circuit Studio' look."""

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [class*="css"], .stApp { font-family: 'Inter', sans-serif; }
.stApp {
  background:
    radial-gradient(1100px 500px at 8% -10%, rgba(34,211,238,.10), transparent 60%),
    radial-gradient(900px 480px at 100% 0%, rgba(167,139,250,.12), transparent 55%),
    #0a0e1a;
}
#MainMenu, footer { visibility: hidden; }
header[data-testid="stHeader"] { background: transparent; }
.block-container { padding-top: 1.4rem; max-width: 1500px; }

/* hero */
.hero { display:flex; align-items:center; justify-content:space-between; gap:24px; padding:22px 28px;
  border:1px solid #1e2a47; border-radius:18px; margin-bottom:18px;
  background: linear-gradient(120deg, rgba(34,211,238,.10), rgba(167,139,250,.10) 55%, rgba(244,114,182,.08)); }
.hero h1 { margin:0; font-size:2rem; font-weight:800; letter-spacing:-.5px;
  background: linear-gradient(90deg,#22d3ee,#a78bfa 60%,#f472b6); -webkit-background-clip:text;
  background-clip:text; color:transparent; }
.hero p { margin:4px 0 0; color:#8392b0; font-size:.95rem; }
.pills { display:flex; gap:8px; flex-wrap:wrap; justify-content:flex-end; }
.pill { font:500 .72rem 'JetBrains Mono',monospace; color:#9fb0cf; border:1px solid #243357;
  padding:4px 10px; border-radius:99px; background:rgba(15,21,38,.7); }

/* cards */
.card { border:1px solid #1e2a47; border-radius:16px; padding:16px 18px; background:rgba(15,21,38,.78);
  backdrop-filter: blur(6px); margin-bottom:14px; }
.card h4 { margin:0 0 8px; font-size:.78rem; letter-spacing:1.3px; text-transform:uppercase; color:#8392b0; font-weight:600; }
.metric { border:1px solid #1e2a47; border-radius:14px; padding:14px 16px; background:linear-gradient(160deg,#101a33,#0d1324); }
.metric .v { font-size:1.55rem; font-weight:700; color:#fff; line-height:1.1; }
.metric .l { font-size:.72rem; letter-spacing:1px; text-transform:uppercase; color:#8392b0; margin-top:4px; }
.metric.a .v { color:#22d3ee } .metric.b .v { color:#a78bfa } .metric.c .v { color:#34d399 } .metric.d .v { color:#fbbf24 }

.sec { display:flex; align-items:center; gap:10px; margin:22px 0 10px; font-weight:700; font-size:1.05rem; }
.sec i { width:4px; height:20px; border-radius:3px; background:linear-gradient(#22d3ee,#a78bfa); display:inline-block; }

/* widgets */
.stButton > button, .stDownloadButton > button { border-radius:10px; border:1px solid #243357; background:#111a30;
  color:#e6edf7; font-weight:600; transition:.15s; }
.stButton > button:hover, .stDownloadButton > button:hover { border-color:#22d3ee; color:#22d3ee; transform:translateY(-1px); }
.stButton > button[kind="primary"] { background:linear-gradient(90deg,#06b6d4,#8b5cf6); border:none; color:#fff;
  box-shadow:0 6px 24px rgba(34,211,238,.25); }
.stButton > button[kind="primary"]:hover { color:#fff; filter:brightness(1.1); transform:translateY(-1px); }
div[data-baseweb="tab-list"] { gap:6px; border-bottom:1px solid #1e2a47; }
button[data-baseweb="tab"] { border-radius:10px 10px 0 0; padding:10px 18px; font-weight:600; }
div[data-baseweb="tab-highlight"] { background:linear-gradient(90deg,#22d3ee,#a78bfa) !important; height:3px; }
.stTextArea textarea, .stCodeBlock pre, code { font-family:'JetBrains Mono',monospace !important; }
.stTextArea textarea { background:#0a1020; border:1px solid #1e2a47; border-radius:12px; font-size:.9rem; }
[data-testid="stSidebar"] { background:#0b1120; border-right:1px solid #1e2a47; }
iframe { border-radius:14px; }
div[data-testid="stExpander"] { border:1px solid #1e2a47; border-radius:14px; background:rgba(15,21,38,.6); }
.issue { border-left:3px solid #fb7185; background:rgba(251,113,133,.08); padding:8px 12px; border-radius:6px; margin:6px 0; font-size:.88rem; }
.issue.warn { border-color:#fbbf24; background:rgba(251,191,36,.08); }
.issue.ok { border-color:#34d399; background:rgba(52,211,153,.08); }
</style>
"""

HERO = """
<div class="hero">
  <div>
    <h1>⚡ Circuit Studio</h1>
    <p>Draw a circuit or type a netlist — then simulate it with the same MNA engine.</p>
  </div>
  <div class="pills">
    <span class="pill">MNA solver</span><span class="pill">Newton–Raphson diodes</span>
    <span class="pill">Backward-Euler transient</span><span class="pill">AC small-signal</span>
  </div>
</div>
"""


def section(title: str) -> str:
    return f'<div class="sec"><i></i>{title}</div>'


def metric(value, label, tone="a") -> str:
    return f'<div class="metric {tone}"><div class="v">{value}</div><div class="l">{label}</div></div>'
