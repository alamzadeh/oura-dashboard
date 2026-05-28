import math
import streamlit as st
import httpx
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit.components.v1 as components
from datetime import datetime, timedelta

st.set_page_config(page_title="Ali's Ring", layout="wide", initial_sidebar_state="collapsed")

# ── Braun / Dieter Rams palette ────────────────────────────────────────────────
BG     = "#E8E4DC"
SURF   = "#EFEBE5"
BRD    = "#C9C4BB"
TEXT   = "#1C1917"
MUTED  = "#6B6558"
ACCENT = "#C8611A"   # burnt orange — used sparingly
DARK   = "#4A4540"   # charcoal
TAN    = "#8B7355"   # warm brown

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400&display=swap');

html, body, .stApp,
[data-testid="stAppViewContainer"],
[data-testid="stMain"] {{
    background-color: {BG} !important;
    font-family: 'DM Sans', sans-serif !important;
}}
[data-testid="stHeader"] {{ background: {BG} !important; border-bottom: none !important; }}
section[data-testid="stSidebar"] {{
    background: {SURF} !important;
    border-right: 1px solid {BRD} !important;
}}
#MainMenu, footer, header {{ visibility: hidden; }}
.block-container {{ padding: 1.5rem 1.5rem 3rem; max-width: 1100px; }}
hr {{ border: none !important; border-top: 1px solid {BRD} !important; margin: 1.5rem 0 !important; }}
p, span, label {{ color: {TEXT} !important; font-family: 'DM Sans', sans-serif !important; }}
h1, h2, h3 {{ color: {TEXT} !important; font-family: 'DM Sans', sans-serif !important; }}

/* Edit pen */
button[data-testid="baseButton-secondary"] {{
    background: {SURF} !important;
    border: 1px solid {BRD} !important;
    border-radius: 6px !important;
    box-shadow: 0 1px 2px rgba(0,0,0,0.08) !important;
    color: {DARK} !important;
    font-size: 13px !important;
    width: 30px !important; height: 30px !important;
    min-height: 30px !important; padding: 0 !important;
    cursor: pointer !important; transition: all .15s !important;
}}
button[data-testid="baseButton-secondary"]:hover {{ background: {BRD} !important; }}

/* Confirm */
button[data-testid="baseButton-primary"] {{
    background: {ACCENT}18 !important;
    border: 1px solid {ACCENT}55 !important;
    border-radius: 6px !important;
    box-shadow: none !important;
    color: {ACCENT} !important;
    font-size: 15px !important;
    width: 30px !important; height: 30px !important;
    min-height: 30px !important; padding: 0 !important;
    cursor: pointer !important;
}}

div[data-testid="stSlider"] label {{ font-size: 11px !important; color: {MUTED} !important; }}
div[data-testid="stExpander"] {{ background: {SURF} !important; border: 1px solid {BRD} !important; border-radius: 10px !important; }}
.streamlit-expanderHeader {{ font-size: 11px !important; letter-spacing: 1.5px !important; text-transform: uppercase !important; color: {MUTED} !important; }}
div[data-testid="metric-container"] {{ background: {SURF} !important; border: 1px solid {BRD} !important; border-radius: 10px !important; padding: 14px !important; box-shadow: 0 1px 3px rgba(0,0,0,0.05) !important; }}
div[data-testid="metric-container"] label {{ font-size: 10px !important; letter-spacing: 1.5px !important; text-transform: uppercase !important; color: {MUTED} !important; }}
div[data-testid="metric-container"] [data-testid="stMetricValue"] {{ font-size: 24px !important; font-weight: 600 !important; color: {TEXT} !important; }}
</style>
""", unsafe_allow_html=True)

BCHART = dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font_color=MUTED, font_family="DM Sans",
    title_font_color=TEXT, title_font_size=12,
    xaxis=dict(gridcolor="#DDD9D1", linecolor=BRD, tickfont=dict(size=11, color=MUTED)),
    yaxis=dict(gridcolor="#DDD9D1", linecolor=BRD, tickfont=dict(size=11, color=MUTED)),
    margin=dict(l=0, r=0, t=40, b=0),
)

for k, v in {"sleep_goal_h": 8.0, "steps_goal": 10000, "cal_goal": 500, "editing": None,
             "active_card": None}.items():
    if k not in st.session_state: st.session_state[k] = v

saved_token = st.secrets.get("oura_token", "") if hasattr(st, "secrets") else ""
with st.sidebar:
    st.markdown(f"<p style='font-size:10px;letter-spacing:2px;color:{MUTED};text-transform:uppercase;'>Settings</p>", unsafe_allow_html=True)
    token = saved_token if saved_token else st.text_input("Personal Access Token", type="password")
    days  = st.slider("Days", 7, 90, 30)

if not token:
    st.markdown(f"<h1 style='font-family:DM Sans,sans-serif;font-size:32px;font-weight:700;color:{TEXT};letter-spacing:1px;'>Ali's Ring</h1>", unsafe_allow_html=True)
    st.info("Enter your token in the sidebar or save to `.streamlit/secrets.toml`")
    st.stop()

end_date   = datetime.now().date()
start_date = end_date - timedelta(days=days)
active     = st.session_state.active_card

@st.cache_data(ttl=300, show_spinner=False)
def fetch(endpoint, _token, params):
    try:
        r = httpx.get(f"https://api.ouraring.com/v2/usercollection/{endpoint}",
                      params=params, headers={"Authorization": f"Bearer {_token}"}, timeout=15)
        r.raise_for_status()
        return r.json().get("data", [])
    except httpx.HTTPStatusError as e:
        st.error("Invalid token." if e.response.status_code == 401 else f"API error {e.response.status_code}")
        return []
    except Exception as e:
        st.error(f"Connection error: {e}")
        return []

dp = {"start_date": str(start_date), "end_date": str(end_date)}
hp = {"start_datetime": f"{end_date}T00:00:00+00:00", "end_datetime": f"{end_date}T23:59:59+00:00"}

with st.spinner(""):
    sleep_data  = fetch("daily_sleep",    token, dp)
    act_data    = fetch("daily_activity", token, dp)
    ready_data  = fetch("daily_readiness",token, dp)
    detail_data = fetch("sleep",          token, dp)
    hr_data     = fetch("heartrate",      token, hp)
    stress_data = fetch("daily_stress",   token, dp)

def to_df(data, dc="day"):
    if not data: return pd.DataFrame()
    df = pd.json_normalize(data)
    if dc in df.columns:
        df[dc] = pd.to_datetime(df[dc])
        df = df.sort_values(dc).reset_index(drop=True)
    return df

sleep_df  = to_df(sleep_data)
act_df    = to_df(act_data)
ready_df  = to_df(ready_data)
det_df    = to_df(detail_data)
hr_df     = to_df(hr_data, "timestamp")
stress_df = to_df(stress_data)

def lat(df, col, d=0):
    if df.empty or col not in df.columns: return d
    v = df[col].dropna()
    return float(v.iloc[-1]) if not v.empty else d

sleep_h    = 0.0
if not det_df.empty and "total_sleep_duration" in det_df.columns:
    rows = det_df[det_df["day"] == pd.Timestamp(end_date)]
    sleep_h = (rows["total_sleep_duration"].sum() if not rows.empty
               else det_df["total_sleep_duration"].iloc[-1]) / 3600

steps      = lat(act_df,   "steps", 0)
cals       = lat(act_df,   "active_calories", 0)
hrv        = lat(det_df,   "average_hrv", 0)
hrv_avg    = float(det_df["average_hrv"].mean()) if not det_df.empty and "average_hrv" in det_df.columns else 0
sleep_sc   = lat(sleep_df, "score", 0)
ready_sc   = lat(ready_df, "score", 0)
resp       = lat(det_df,   "average_breath", 0)
rhr_col    = next((c for c in ready_df.columns if "resting_heart_rate" in c.lower()), None)
rhr        = int(lat(ready_df, rhr_col, 0)) if rhr_col else None
cur_hr     = int(hr_df["bpm"].dropna().iloc[-1]) if not hr_df.empty and "bpm" in hr_df.columns else None
center_hr  = cur_hr or rhr

SM = {"restored":("Restored",ACCENT), "normal":("Balanced",DARK),
      "stressful":("Elevated","#A0521A"), "very_stressful":("High","#8B2E1C")}
rs = ""
if not stress_df.empty and "day_summary" in stress_df.columns:
    v = stress_df["day_summary"].dropna()
    if not v.empty: rs = str(v.iloc[-1]) if v.iloc[-1] else ""
s_label, s_color = SM.get(rs, ("—", MUTED))

sg = st.session_state.sleep_goal_h
stg= st.session_state.steps_goal
cg = st.session_state.cal_goal
hrv_pct = min(hrv / hrv_avg, 1.0) if hrv_avg else 0
def sc(v): return "#3D6B3A" if v >= 85 else ACCENT if v >= 70 else "#8B2E1C"

# ── Dot helpers ────────────────────────────────────────────────────────────────
def circ_dots(cx, cy, r, pct, color, n=60, dr=3.5):
    n_lit = int(round(min(pct, 1.0) * n))
    out = []
    for i in range(n):
        a  = (i / n) * 2 * math.pi - math.pi / 2
        px = cx + r * math.cos(a)
        py = cy + r * math.sin(a)
        fill = color if i < n_lit else "#D4CFC8"
        op   = "1" if i < n_lit else "0.6"
        out.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{dr}" fill="{fill}" opacity="{op}"/>')
    return "".join(out)

def dot_bar(pct, color, n=22, sz=5):
    n_lit = int(round(min(pct, 1.0) * n))
    dots = []
    for i in range(n):
        fill = color if i < n_lit else "#D4CFC8"
        op   = "1" if i < n_lit else "0.5"
        dots.append(f'<div style="width:{sz}px;height:{sz}px;border-radius:1px;background:{fill};opacity:{op};flex-shrink:0;"></div>')
    return f'<div style="display:flex;gap:3px;align-items:center;">{"".join(dots)}</div>'

# ── Rings SVG ─────────────────────────────────────────────────────────────────
def build_rings(sleep_h, sg, steps, stg, cals, cg, hr):
    def p(v, g): return min(v/g, 1.0) if g > 0 else 0
    cx = cy = 140
    r1 = circ_dots(cx, cy, 120, p(sleep_h, sg),  ACCENT, n=62, dr=3.8)
    r2 = circ_dots(cx, cy,  90, p(steps, stg),   DARK,   n=48, dr=3.2)
    r3 = circ_dots(cx, cy,  60, p(cals, cg),     TAN,    n=32, dr=2.6)
    ht = str(hr) if hr else "—"
    return f"""
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;600;700&display=swap" rel="stylesheet">
<div style="display:flex;justify-content:center;padding:4px 0 8px;">
  <div style="background:{SURF};border:1px solid {BRD};border-radius:20px;
              padding:16px;display:inline-block;
              box-shadow:0 2px 12px rgba(0,0,0,0.07),0 1px 3px rgba(0,0,0,0.05);">
    <svg width="280" height="280" viewBox="0 0 280 280">
      <circle cx="140" cy="140" r="138" fill="{SURF}"/>
      {r1}{r2}{r3}
      <text x="140" y="134" text-anchor="middle" dominant-baseline="middle"
            fill="{TEXT}" font-size="52" font-weight="700"
            font-family="DM Sans,sans-serif">{ht}</text>
      <text x="140" y="164" text-anchor="middle" dominant-baseline="middle"
            fill="{MUTED}" font-size="10" letter-spacing="2.5"
            font-family="DM Sans,sans-serif">BPM</text>
    </svg>
  </div>
</div>"""

# ── Legend row ─────────────────────────────────────────────────────────────────
def legend_row(label, color, value_str, pct_val, goal_key):
    is_editing = st.session_state.editing == goal_key
    bar = dot_bar(pct_val, color)
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:12px;padding:10px 0;
                border-bottom:1px solid {BRD};">
      <div style="width:10px;height:10px;border-radius:2px;background:{color};flex-shrink:0;"></div>
      <span style="font-size:11px;letter-spacing:1.5px;color:{TEXT};text-transform:uppercase;
                   font-weight:500;width:88px;">{label}</span>
      {bar}
      <span style="font-size:18px;font-weight:600;color:{TEXT};min-width:68px;
                   text-align:right;font-family:'DM Sans',sans-serif;">{value_str}</span>
    </div>""", unsafe_allow_html=True)
    bc, sc2 = st.columns([1, 12])
    with bc:
        if not is_editing:
            if st.button("✎", key=f"pen_{goal_key}", type="secondary"):
                st.session_state.editing = goal_key; st.rerun()
        else:
            if st.button("✓", key=f"ok_{goal_key}", type="primary"):
                st.session_state.editing = None; st.rerun()
    if is_editing:
        with sc2:
            if goal_key == "sleep_goal_h":
                v = st.slider("", 4.0, 12.0, float(st.session_state.sleep_goal_h), 0.5,
                             key="sl_sleep", label_visibility="collapsed")
            elif goal_key == "steps_goal":
                v = st.slider("", 1000, 25000, int(st.session_state.steps_goal), 500,
                             key="sl_steps", label_visibility="collapsed")
            elif goal_key == "cal_goal":
                v = st.slider("", 100, 1500, int(st.session_state.cal_goal), 50,
                             key="sl_cal", label_visibility="collapsed")
            st.session_state[goal_key] = v
    st.markdown("<div style='height:2px;'></div>", unsafe_allow_html=True)

# ── Cards HTML ────────────────────────────────────────────────────────────────
def build_cards(active, cards):
    items = ""
    for key, label, value, sub, color in cards:
        is_act = active == key
        left_border = f"border-left:3px solid {ACCENT};" if is_act else f"border-left:3px solid transparent;"
        bg = f"background:{BRD};" if is_act else f"background:{SURF};"
        items += f"""
<div onclick="sel('{key}')"
     style="{bg}border:1px solid {BRD};{left_border}border-radius:10px;
            padding:18px 16px 14px;cursor:pointer;transition:all .15s;
            box-shadow:0 1px 3px rgba(0,0,0,0.05),0 2px 8px rgba(0,0,0,0.04);
            box-sizing:border-box;min-height:106px;">
  <p style="font-family:'DM Sans',sans-serif;font-size:9px;letter-spacing:2px;
            color:{MUTED};text-transform:uppercase;margin:0 0 8px;font-weight:500;">{label}</p>
  <p style="font-family:'DM Sans',sans-serif;font-size:28px;font-weight:700;
            color:{color};margin:0;line-height:1;">{value}</p>
  <p style="font-family:'DM Sans',sans-serif;font-size:11px;color:{MUTED};
            margin:6px 0 0;">{sub}</p>
</div>"""

    return f"""
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&display=swap" rel="stylesheet">
<div style="display:grid;grid-template-columns:repeat(6,1fr);gap:8px;width:100%;">
  {items}
</div>
<style>
@media(max-width:640px){{
  div[style*="grid-template-columns:repeat(6"] {{
    grid-template-columns:repeat(2,1fr) !important;
  }}
}}
</style>
<script>
function sel(key) {{
  try {{
    var p = window.parent;
    var curr = new URLSearchParams(p.location.search).get('card') || '';
    var path = p.location.pathname;
    p.location.replace(path + (curr===key ? '' : '?card='+encodeURIComponent(key)));
  }} catch(e) {{ console.warn(e); }}
}}
</script>"""

# ── Chart helpers ──────────────────────────────────────────────────────────────
def cline(df, x, y, color, title, yr=None, ref=None, rl=""):
    fig = px.line(df, x=x, y=y, title=title, markers=True, color_discrete_sequence=[color])
    fig.update_traces(line_width=2, marker_size=5, marker_color=color)
    if ref: fig.add_hline(y=ref, line_dash="dot", line_color=BRD, line_width=1,
                          annotation_text=rl, annotation_font_color=MUTED, annotation_font_size=10)
    fig.update_layout(**BCHART)
    if yr: fig.update_layout(yaxis_range=yr)
    return fig

def cbar(df, x, y, color, title, ref=None, rl=""):
    fig = px.bar(df, x=x, y=y, title=title, color_discrete_sequence=[color])
    fig.update_traces(marker_line_width=0)
    if ref: fig.add_hline(y=ref, line_dash="dot", line_color=BRD, line_width=1,
                          annotation_text=rl, annotation_font_color=MUTED, annotation_font_size=10)
    fig.update_layout(**BCHART)
    return fig

# ── Active card from URL ───────────────────────────────────────────────────────
raw = st.query_params.get("card", "") or ""
active = raw if raw else None

# ── Page ───────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="margin-bottom:20px;">
  <h1 style="font-family:'DM Sans',sans-serif;font-size:26px;font-weight:700;
             color:{TEXT};margin:0;letter-spacing:0.5px;">Ali's Ring</h1>
  <p style="font-size:11px;letter-spacing:1px;color:{MUTED};margin:4px 0 0;text-transform:uppercase;">
    {end_date.strftime('%A, %B %d %Y')} · {days} days
  </p>
</div>""", unsafe_allow_html=True)

# Rings
components.html(
    build_rings(sleep_h, sg, steps, stg, cals, cg, center_hr),
    height=330,
)

# Legend
sp  = min(sleep_h / sg,  1.0) if sg  else 0
stp = min(steps   / stg, 1.0) if stg else 0
cp  = min(cals    / cg,  1.0) if cg  else 0
legend_row("Sleep",    ACCENT, f"{sleep_h:.1f}h", sp,  "sleep_goal_h")
legend_row("Steps",    DARK,   f"{int(steps):,}", stp, "steps_goal")
legend_row("Calories", TAN,    f"{int(cals)}",    cp,  "cal_goal")

st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)

# Cards
CARDS = [
    ("sleep",     "Sleep Score",  f"{int(sleep_sc)}" if sleep_sc else "—",     f"{sleep_h:.1f}h tonight",                     sc(sleep_sc) if sleep_sc else MUTED),
    ("readiness", "Readiness",    f"{int(ready_sc)}" if ready_sc else "—",     "perform" if ready_sc>=85 else "moderate" if ready_sc>=70 else "rest", sc(ready_sc) if ready_sc else MUTED),
    ("stress",    "Stress",       s_label,                                       f"{int(lat(stress_df,'stress_high',0))}min" if not stress_df.empty else "—", s_color),
    ("hr",        "Heart Rate",   f"{rhr}" if rhr else f"{cur_hr}" if cur_hr else "—", "resting bpm", TEXT),
    ("hrv",       "HRV",          f"{int(hrv)}ms" if hrv else "—",             f"{'↑' if hrv>=hrv_avg else '↓'} {int(hrv_avg)}ms avg" if hrv_avg else "—", DARK),
    ("activity",  "Activity",     f"{int(steps):,}" if steps else "—",         f"of {int(stg):,} steps", TAN),
]
components.html(build_cards(active, CARDS), height=130)

# ── Detail panels ──────────────────────────────────────────────────────────────
if active:
    st.markdown(f"<div style='height:1px;background:{BRD};margin:12px 0;'></div>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)

    if active == "sleep":
        if "score" in sleep_df.columns:
            c1.plotly_chart(cline(sleep_df,"day","score",ACCENT,"Sleep Score",[0,100],85,"85"), use_container_width=True)
        if "average_hrv" in det_df.columns:
            c2.plotly_chart(cline(det_df,"day","average_hrv",DARK,"HRV (ms)",ref=hrv_avg,rl=f"{hrv_avg:.0f} avg" if hrv_avg else ""), use_container_width=True)
        if resp: st.metric("Respiratory Rate", f"{resp:.1f} br/min")

    elif active == "readiness":
        if "score" in ready_df.columns:
            c1.plotly_chart(cline(ready_df,"day","score","#3D6B3A","Readiness",[0,100],85,"85"), use_container_width=True)
        cc = [c for c in ready_df.columns if c.startswith("contributors.")]
        if cc and not ready_df.empty:
            row = ready_df.iloc[-1][cc]
            row.index = row.index.str.replace("contributors.","").str.replace("_"," ").str.title()
            clrs = ["#3D6B3A" if v>=80 else ACCENT if v>=60 else "#8B2E1C" for v in row.values]
            fig = go.Figure(go.Bar(x=row.index, y=row.values, marker_color=clrs, marker_line_width=0))
            fig.update_layout(**BCHART, title="Contributors", yaxis_range=[0,100])
            c2.plotly_chart(fig, use_container_width=True)

    elif active == "stress":
        if stress_df.empty: st.info("No stress data.")
        else:
            if "stress_high" in stress_df.columns:
                c1.plotly_chart(cbar(stress_df,"day","stress_high",ACCENT,"High Stress (min)"), use_container_width=True)
            if "recovery_high" in stress_df.columns:
                c2.plotly_chart(cbar(stress_df,"day","recovery_high","#3D6B3A","High Recovery (min)"), use_container_width=True)

    elif active == "hr":
        if not hr_df.empty and "bpm" in hr_df.columns:
            fig = cline(hr_df,"timestamp","bpm",ACCENT,"Heart Rate Today")
            fig.update_traces(fill="tozeroy", fillcolor=f"{ACCENT}12")
            c1.plotly_chart(fig, use_container_width=True)
        else:
            c1.info("No intraday HR yet — ring syncs every few hours.")
        if rhr_col and not ready_df.empty:
            c2.plotly_chart(cline(ready_df,"day",rhr_col,DARK,"Resting HR Trend"), use_container_width=True)

    elif active == "hrv":
        if "average_hrv" in det_df.columns:
            c1.plotly_chart(cline(det_df,"day","average_hrv",DARK,"HRV (ms)",ref=hrv_avg,rl=f"{hrv_avg:.0f} avg" if hrv_avg else ""), use_container_width=True)
        if "score" in sleep_df.columns:
            c2.plotly_chart(cline(sleep_df,"day","score",ACCENT,"Sleep Score",[0,100]), use_container_width=True)

    elif active == "activity":
        if "steps" in act_df.columns:
            c1.plotly_chart(cbar(act_df,"day","steps",DARK,"Steps",stg,f"{int(stg):,} goal"), use_container_width=True)
        if "active_calories" in act_df.columns:
            c2.plotly_chart(cbar(act_df,"day","active_calories",TAN,"Active Calories",cg,f"{int(cg)} goal"), use_container_width=True)
        sed = next((c for c in act_df.columns if "sedentary" in c or "inactive" in c), None)
        if sed:
            act_df["sed_h"] = act_df[sed] / 3600
            st.plotly_chart(cbar(act_df,"day","sed_h",MUTED,"Sedentary (hours)",8,"8h"), use_container_width=True)