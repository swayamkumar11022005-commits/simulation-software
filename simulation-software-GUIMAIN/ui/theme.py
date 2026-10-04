"""Global CSS for the light, PSpice-style 'Circuit Studio' look.

Soft greys, flat docked panels, a cream schematic sheet and muted classic
colours (steel blue accent, maroon parts, green wires, teal annotations).
"""

CSS = """
<style>
html, body, [class*="css"], .stApp { font-family: "Segoe UI", Tahoma, Arial, sans-serif; color:#1f2933; }
.stApp { background:#e7eaee; }
#MainMenu, footer { visibility: hidden; }
header[data-testid="stHeader"] { background: transparent; }
.block-container { padding-top: 1.2rem; max-width: 1500px; }

/* window title bar */
.titlebar { display:flex; align-items:center; justify-content:space-between; gap:20px; padding:8px 14px;
  border:1px solid #b8bfc8; border-radius:4px 4px 0 0; margin-bottom:14px;
  background:linear-gradient(#f9fafb,#dde3ea); }
.titlebar .name { display:flex; align-items:center; gap:10px; font-size:1rem; font-weight:600; color:#26323f; }
.titlebar .logo { width:16px; height:16px; border-radius:3px; background:#3d6b99; position:relative; display:inline-block; }
.titlebar .logo:after { content:""; position:absolute; left:3px; right:3px; top:7px; height:2px; background:#fff; }
.titlebar .sub { color:#5d6978; font-weight:400; font-size:.86rem; }
.pills { display:flex; gap:6px; flex-wrap:wrap; justify-content:flex-end; }
.pill { font:500 .72rem Consolas, monospace; color:#4a5766; border:1px solid #c3cad2;
  padding:2px 8px; border-radius:3px; background:#f6f7f9; }

/* docked-panel headings */
.sec { display:flex; align-items:center; gap:8px; margin:18px 0 8px; padding:5px 10px;
  font-weight:600; font-size:.88rem; color:#2b3947; border:1px solid #b8bfc8; border-radius:3px;
  background:linear-gradient(#f7f8fa,#dfe4ea); }
.sec i { width:8px; height:8px; border-radius:2px; background:#3d6b99; display:inline-block; }

/* summary tiles */
.metric { border:1px solid #c3cad2; border-left:3px solid #3d6b99; border-radius:3px; padding:10px 14px; background:#ffffff; }
.metric .v { font-size:1.3rem; font-weight:600; color:#1f2933; line-height:1.15; }
.metric .l { font-size:.74rem; color:#5d6978; margin-top:3px; }
.metric.a { border-left-color:#3d6b99 } .metric.b { border-left-color:#8a6aa0 }
.metric.c { border-left-color:#4c8a5a } .metric.d { border-left-color:#b08a3c }

/* buttons */
.stButton > button, .stDownloadButton > button { border-radius:3px; border:1px solid #aab2bc;
  background:linear-gradient(#ffffff,#eceff2); color:#1f2933; font-weight:500; }
.stButton > button:hover, .stDownloadButton > button:hover { border-color:#3d6b99; color:#23496e; background:#e2eaf3; }
.stButton > button[kind="primary"] { background:linear-gradient(#4d7aa8,#3d6b99); border:1px solid #2f5a85; color:#fff; }
.stButton > button[kind="primary"]:hover { background:linear-gradient(#5a86b3,#46759f); color:#fff; }
.stButton > button:disabled { opacity:.5; }

/* tabs */
div[data-baseweb="tab-list"] { gap:2px; border-bottom:1px solid #b8bfc8; }
button[data-baseweb="tab"] { border-radius:3px 3px 0 0; padding:7px 16px; font-weight:500; background:#dde2e8; }
button[data-baseweb="tab"][aria-selected="true"] { background:#ffffff; }
div[data-baseweb="tab-highlight"] { background:#3d6b99 !important; height:2px; }

/* inputs, code, sidebar */
.stTextArea textarea, .stCodeBlock pre, code { font-family:Consolas, "Courier New", monospace !important; }
.stTextArea textarea { background:#ffffff; border:1px solid #aab2bc; border-radius:3px; font-size:.9rem; }
.stCodeBlock pre { background:#f7f8f9 !important; border:1px solid #d3d8de; border-radius:3px; }
[data-testid="stSidebar"] { background:#f3f4f6; border-right:1px solid #b8bfc8; }
iframe { border-radius:4px; }
div[data-testid="stExpander"] { border:1px solid #c3cad2; border-radius:3px; background:#ffffff; }

/* design-check messages */
.issue { border-left:3px solid #a94a4a; background:#f8ecec; padding:7px 12px; border-radius:2px; margin:5px 0; font-size:.88rem; color:#4a2a2a; }
.issue.warn { border-color:#b08a3c; background:#f8f2e2; color:#4d3f1c; }
.issue.ok { border-color:#4c8a5a; background:#eaf3ec; color:#26452e; }
</style>
"""

HERO = """
<div class="titlebar">
  <div class="name"><span class="logo"></span>Circuit Studio
    <span class="sub">Schematic capture and simulation</span></div>
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
