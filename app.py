import math
import streamlit as st
import httpx
import pandas as pd
import streamlit.components.v1 as components
from datetime import datetime, timedelta
from PIL import Image

try:
    _icon = Image.open("static/apple-touch-icon.png")
except Exception:
    _icon = "🔴"

st.set_page_config(page_title="Ali's Ring", page_icon=_icon,
                   layout="wide", initial_sidebar_state="collapsed")

BG     = "#E8E4DC"
SURF   = "#EFEBE5"
BRD    = "#C9C4BB"
TEXT   = "#1C1917"
MUTED  = "#6B6558"
ACCENT = "#C8611A"
DARK   = "#4A4540"
TAN    = "#8B7355"

FROSTED = (f"background:rgba(239,235,229,0.88);"
           f"backdrop-filter:blur(20px) saturate(1.6);"
           f"-webkit-backdrop-filter:blur(20px) saturate(1.6);"
           f"border:1px solid rgba(201,196,187,0.55);"
           f"border-radius:18px;"
           f"box-shadow:0 4px 24px rgba(0,0,0,0.06);")

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&display=swap');

html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {{
    background-color:{BG} !important;
    background-image:radial-gradient(circle,rgba(170,163,154,0.35) 1.5px,transparent 1.5px) !important;
    background-size:22px 22px !important;
    font-family:'DM Sans',sans-serif !important;
}}
[data-testid="stHeader"] {{ background:{BG} !important; border-bottom:none !important; }}
section[data-testid="stSidebar"] {{ background:{SURF} !important; border-right:1px solid {BRD} !important; }}
#MainMenu,footer,header {{ visibility:hidden; }}
.block-container {{ padding:1.5rem 1.5rem 3rem; max-width:1100px; }}
hr {{ border:none !important; border-top:1px solid {BRD} !important; margin:1.2rem 0 !important; }}
p,span,label {{ color:{TEXT} !important; font-family:'DM Sans',sans-serif !important; }}

/* Edit pen */
button[data-testid="baseButton-secondary"] {{
    background:{SURF} !important; border:1px solid {BRD} !important;
    border-radius:6px !important; box-shadow:0 1px 2px rgba(0,0,0,0.07) !important;
    color:{DARK} !important; font-size:13px !important; font-weight:600 !important;
    width:30px !important; height:30px !important; min-height:30px !important;
    padding:0 !important; cursor:pointer !important;
}}
button[data-testid="baseButton-secondary"]:hover {{ background:{BRD} !important; }}

/* Confirm + plus/minus */
button[data-testid="baseButton-primary"] {{
    background:{ACCENT}18 !important; border:1px solid {ACCENT}55 !important;
    border-radius:6px !important; box-shadow:none !important;
    color:{ACCENT} !important; font-size:15px !important; font-weight:700 !important;
    min-width:30px !important; height:30px !important; min-height:30px !important;
    padding:0 6px !important; cursor:pointer !important;
}}

div[data-testid="stNumberInput"] input {{
    background:{SURF} !important; border:1px solid {BRD} !important;
    border-radius:8px !important; color:{TEXT} !important;
    font-family:'DM Sans',sans-serif !important; font-size:15px !important;
    text-align:center !important;
}}
div[data-testid="stNumberInput"] label {{ color:{MUTED} !important; font-size:11px !important; letter-spacing:1px; text-transform:uppercase; }}
div[data-testid="stNumberInput"] button {{ background:{SURF} !important; border:1px solid {BRD} !important; border-radius:6px !important; color:{TEXT} !important; }}

div[data-testid="stExpander"] {{ background:{SURF} !important; border:1px solid {BRD} !important; border-radius:12px !important; }}
.streamlit-expanderHeader {{ font-size:11px !important; letter-spacing:1.5px !important; text-transform:uppercase !important; color:{MUTED} !important; }}
</style>
""", unsafe_allow_html=True)

# ── PWA ────────────────────────────────────────────────────────────────────────
components.html("""
<script>
(function(){try{
  var p=window.parent.document,url=new URL(window.parent.location.href);
  var d=new Date(),ld=d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0');
  if(url.searchParams.get('ld')!==ld){
    var card=url.searchParams.get('card')||'';
    url.searchParams.set('ld',ld);
    card?url.searchParams.set('card',card):url.searchParams.delete('card');
    window.parent.location.replace(url.toString());return;
  }
  if(p.querySelector('meta[name="apple-mobile-web-app-capable"]'))return;
  [['apple-mobile-web-app-capable','yes'],['apple-mobile-web-app-status-bar-style','default'],
   ['apple-mobile-web-app-title',"Ali's Ring"],['theme-color','#E8E4DC'],['mobile-web-app-capable','yes']
  ].forEach(function(t){var m=p.createElement('meta');m.name=t[0];m.content=t[1];p.head.appendChild(m);});
  var iconUrl=window.parent.location.origin+'/app/static/apple-touch-icon.png';
  p.querySelectorAll('link[rel*="icon"]').forEach(function(el){el.parentNode&&el.parentNode.removeChild(el);});
  ['apple-touch-icon','icon'].forEach(function(r){var l=p.createElement('link');l.rel=r;l.href=iconUrl;p.head.appendChild(l);});
  p.title="Ali's Ring";
}catch(e){}})();
</script>""", height=0)

for k,v in {"sleep_goal_h":8.0,"steps_goal":10000,"cal_goal":500,"editing":None}.items():
    if k not in st.session_state: st.session_state[k]=v

saved_token = st.secrets.get("oura_token","") if hasattr(st,"secrets") else ""
with st.sidebar:
    st.markdown(f"<p style='font-size:10px;letter-spacing:2px;color:{MUTED};text-transform:uppercase;'>Settings</p>",unsafe_allow_html=True)
    token = saved_token if saved_token else st.text_input("Personal Access Token",type="password")
    days  = st.slider("Days",7,90,30)

if not token:
    st.markdown(f"<h1 style='font-family:DM Sans;font-size:32px;font-weight:700;color:{TEXT};'>Ali's Ring</h1>",unsafe_allow_html=True)
    st.info("Enter your token in the sidebar or save to `.streamlit/secrets.toml`")
    st.stop()

end_date = datetime.now().date()
ld_str = st.query_params.get("ld","")
if ld_str:
    try: end_date = datetime.strptime(ld_str,"%Y-%m-%d").date()
    except: pass
start_date = end_date - timedelta(days=days)
raw = st.query_params.get("card","") or ""
active = raw if raw else None

@st.cache_data(ttl=300,show_spinner=False)
def fetch(endpoint,_token,params):
    try:
        r=httpx.get(f"https://api.ouraring.com/v2/usercollection/{endpoint}",
                    params=params,headers={"Authorization":f"Bearer {_token}"},timeout=15)
        r.raise_for_status(); return r.json().get("data",[])
    except httpx.HTTPStatusError as e:
        st.error("Invalid token." if e.response.status_code==401 else f"API error {e.response.status_code}"); return []
    except: return []

dp={"start_date":str(start_date),"end_date":str(end_date)}
hp={"start_datetime":f"{end_date}T00:00:00+00:00","end_datetime":f"{end_date}T23:59:59+00:00"}

with st.spinner(""):
    sleep_data  = fetch("daily_sleep",   token,dp)
    act_data    = fetch("daily_activity",token,dp)
    ready_data  = fetch("daily_readiness",token,dp)
    detail_data = fetch("sleep",         token,dp)
    hr_data     = fetch("heartrate",     token,hp)
    stress_data = fetch("daily_stress",  token,dp)

def to_df(data,dc="day"):
    if not data: return pd.DataFrame()
    df=pd.json_normalize(data)
    if dc in df.columns:
        df[dc]=pd.to_datetime(df[dc]); df=df.sort_values(dc).reset_index(drop=True)
    return df

sleep_df  = to_df(sleep_data)
act_df    = to_df(act_data)
ready_df  = to_df(ready_data)
det_df    = to_df(detail_data)
hr_df     = to_df(hr_data,"timestamp")
stress_df = to_df(stress_data)

def lat(df,col,d=0):
    if df.empty or col not in df.columns: return d
    v=df[col].dropna(); return float(v.iloc[-1]) if not v.empty else d

sleep_h=0.0
if not det_df.empty and "total_sleep_duration" in det_df.columns:
    rows=det_df[det_df["day"]==pd.Timestamp(end_date)]
    sleep_h=(rows["total_sleep_duration"].sum() if not rows.empty else det_df["total_sleep_duration"].iloc[-1])/3600

steps    = lat(act_df,"steps",0)
cals     = lat(act_df,"active_calories",0)
sleep_sc = lat(sleep_df,"score",0)
ready_sc = lat(ready_df,"score",0)
rhr_col  = next((c for c in ready_df.columns if "resting_heart_rate" in c.lower()),None)
rhr      = int(lat(ready_df,rhr_col,0)) if rhr_col else None

try:
    bpm_s=hr_df["bpm"].dropna() if not hr_df.empty and "bpm" in hr_df.columns else pd.Series(dtype=float)
    cur_hr=int(bpm_s.iloc[-1]) if not bpm_s.empty else None
except: cur_hr=None
center_hr=cur_hr or rhr

SM={"restored":("Restored",ACCENT),"normal":("Balanced",DARK),
    "stressful":("Elevated","#A0521A"),"very_stressful":("High","#8B2E1C")}
rs=""
if not stress_df.empty and "day_summary" in stress_df.columns:
    v=stress_df["day_summary"].dropna()
    if not v.empty: rs=str(v.iloc[-1]) if v.iloc[-1] else ""
s_label,s_color=SM.get(rs,("—",MUTED))

sg=st.session_state.sleep_goal_h
stg=st.session_state.steps_goal
cg=st.session_state.cal_goal
def sc(v): return "#3D6B3A" if v>=85 else ACCENT if v>=70 else "#8B2E1C"

# ── Prewritten text ────────────────────────────────────────────────────────────
def sleep_motiv(score,hours):
    if not score: return "No data yet"
    if score>=85: return f"Outstanding. {hours:.1f}h of quality rest."
    elif score>=70: return f"Good rest. {hours:.1f}h logged."
    elif score>=50: return f"Moderate. Aim for an earlier bedtime."
    else: return f"Rest needed. Take it easy today."

def ready_motiv(score):
    if not score: return "No data yet"
    if score>=85: return "Primed. Push hard today."
    elif score>=70: return "Good shape. Moderate effort works."
    elif score>=50: return "Mixed signals. Keep intensity light."
    else: return "Rest day. Let your body recover."

def stress_motiv(label):
    return {"Restored":"Well recovered. Keep it up.","Balanced":"In check. Managing well.",
            "Elevated":"Some stress. Build in calm.","High":"High load. Protect your energy."}.get(label,"No data yet")

def hr_motiv(r):
    if not r: return "No data yet"
    if r<55: return "Excellent cardiovascular fitness."
    elif r<65: return "Heart working efficiently."
    elif r<75: return "Normal range. Stay active."
    else: return "Slightly elevated. Worth monitoring."

def act_motiv(s,g):
    if not s: return "No data yet"
    p=s/g if g else 0
    if p>=1: return "Goal hit! Great movement today."
    elif p>=0.75: return "Almost there. Keep moving."
    elif p>=0.5: return "Halfway. Add some steps."
    else: return "Light day. Every step counts."

def get_summary(key):
    if key=="sleep":
        if not sleep_sc: return "Sleep","No sleep data available yet."
        if sleep_sc>=85: return "Sleep",f"Outstanding night — {sleep_h:.1f} hours of quality rest. Your body is fully recovered. Today's a great day to take on something challenging."
        elif sleep_sc>=70: return "Sleep",f"Good sleep — {sleep_h:.1f} hours logged. You have solid energy reserves. A consistent bedtime will keep your scores in this range."
        elif sleep_sc>=50: return "Sleep",f"Moderate rest — {sleep_h:.1f} hours. Your body recovered partially. Try winding down 30 minutes earlier tonight and reducing screen time before bed."
        else: return "Sleep",f"Limited rest — {sleep_h:.1f} hours. Your body didn't get the recovery it needed. Keep today's demands light and make sleep the priority tonight."
    elif key=="readiness":
        if not ready_sc: return "Readiness","No readiness data yet."
        if ready_sc>=85: return "Readiness","Your body is primed and ready. All signals are green. Take on the day with confidence — this is a good day to push yourself."
        elif ready_sc>=70: return "Readiness","You're in good shape. Your body has recovered well enough for moderate-to-hard effort. Listen to how you feel and adjust as you go."
        elif ready_sc>=50: return "Readiness","Mixed signals today. Your body is functioning but not fully recovered. Moderate activity is fine — avoid going all-out and give yourself extra recovery time."
        else: return "Readiness","Your body is asking for rest. Focus on light movement, good nutrition, and an early night. Recovery is part of the process."
    elif key=="stress":
        texts={"Restored":("Stress","Excellent recovery. Your body processed yesterday's stress well and came back stronger. Keep your routine going."),
               "Balanced":("Stress","Stress and recovery are in balance. You're managing the demands of your day well. Keep doing what you're doing."),
               "Elevated":("Stress","Elevated stress detected — physical, mental, or both. Build in intentional calm: a walk, deep breathing, or quiet time will help."),
               "High":("Stress","High stress load. Your nervous system is working hard. Protect your energy today, avoid overcommitting, and prioritize wind-down time tonight.")}
        return texts.get(s_label,("Stress","No stress data available for today."))
    elif key=="hr":
        if not rhr: return "Heart Rate","No resting heart rate data yet. The ring collects this while you sleep."
        if rhr<55: return "Heart Rate",f"Resting at {rhr} bpm — excellent. A low resting heart rate is one of the strongest markers of cardiovascular fitness."
        elif rhr<65: return "Heart Rate",f"Resting at {rhr} bpm — good range. Your heart is pumping efficiently at rest."
        elif rhr<75: return "Heart Rate",f"Resting at {rhr} bpm — normal range. Regular aerobic exercise will continue to keep this healthy."
        else: return "Heart Rate",f"Resting at {rhr} bpm — slightly elevated. This can reflect stress, poor sleep, or illness. Worth monitoring if it stays elevated."
    elif key=="activity":
        p=steps/stg if stg else 0
        if p>=1: return "Activity",f"Goal reached — {int(steps):,} steps. Consistent daily movement like this is one of the most impactful things you can do for long-term health."
        elif p>=0.75: return "Activity",f"{int(steps):,} steps so far — almost at your {int(stg):,} goal. A short walk would push you over the line."
        elif p>=0.5: return "Activity",f"{int(steps):,} steps — halfway to your goal. Adding some movement to your afternoon, even a short walk, makes a real difference."
        else: return "Activity",f"{int(steps):,} steps so far — a light day. Even a 15-minute walk benefits your cardiovascular health and mood. Small steps count."
    return "","No data."

def day_summary_text():
    scores=[s for s in [sleep_sc,ready_sc] if s]
    avg=sum(scores)/len(scores) if scores else 0
    sp=steps/stg if stg and steps else 0
    if avg>=85 and s_label in ["Balanced","Restored"] and sp>=0.8:
        return "Everything is pointing in the right direction. Well-rested, recovered, stress managed, and moving — this is what a strong health day looks like."
    elif avg>=80 and s_label in ["Balanced","Restored"]:
        return "A strong day overall. Sleep and recovery are solid, stress is in check. Keep the momentum with some movement and a consistent bedtime tonight."
    elif avg>=70:
        return "A decent day. Your body is functioning well, though there's room for improvement. Focus on winding down properly tonight and staying active."
    elif avg>=55:
        return "Mixed signals today. Some areas of recovery are lagging. Moderate your activity, stay hydrated, and make sleep a priority — tomorrow will be better."
    elif avg>0:
        return "Your body is in recovery mode. That's normal and important — rest is where adaptation happens. Take it easy, eat well, and let your body do its work."
    else:
        return "Waiting for today's data to sync from your ring."

# ── Dots ───────────────────────────────────────────────────────────────────────
def circ_dots(cx,cy,r,pct,color,n=56,dot_r=3.5):
    n_lit=int(round(min(pct,1.0)*n))
    out=[]
    for i in range(n):
        a=(i/n)*2*math.pi-math.pi/2
        px=cx+r*math.cos(a); py=cy+r*math.sin(a)
        fill=color if i<n_lit else "#C8C3BA"
        op="1" if i<n_lit else "0.5"
        out.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{dot_r}" fill="{fill}" opacity="{op}"/>')
    return "".join(out)

def dot_bar(pct,color,n=22,sz=5):
    n_lit=int(round(min(pct,1.0)*n))
    dots=[]
    for i in range(n):
        fill=color if i<n_lit else "#C8C3BA"
        op="1" if i<n_lit else "0.5"
        dots.append(f'<div style="width:{sz}px;height:{sz}px;border-radius:1px;background:{fill};opacity:{op};flex-shrink:0;"></div>')
    return f'<div style="display:flex;gap:3px;align-items:center;">{"".join(dots)}</div>'

# ── Rings ──────────────────────────────────────────────────────────────────────
def build_rings(sleep_h,sg,steps,stg,cals,cg,hr):
    def p(v,g): return min(v/g,1.0) if g>0 else 0
    cx=cy=150
    r1=circ_dots(cx,cy,128,p(sleep_h,sg),ACCENT,n=66,dot_r=3.5)
    r2=circ_dots(cx,cy, 96,p(steps,stg),DARK,  n=50,dot_r=3.5)
    r3=circ_dots(cx,cy, 64,p(cals,cg),  TAN,   n=34,dot_r=3.5)
    ht=str(hr) if hr else "—"
    return f"""<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@600;700&display=swap" rel="stylesheet">
<div style="display:flex;justify-content:center;padding:4px 0 8px;">
  <div style="{FROSTED}padding:20px;display:inline-block;">
    <svg width="300" height="300" viewBox="0 0 300 300" overflow="visible">
      <circle cx="150" cy="150" r="148" fill="rgba(239,235,229,0.6)"/>
      {r1}{r2}{r3}
      <text x="150" y="144" text-anchor="middle" dominant-baseline="middle"
            fill="{TEXT}" font-size="50" font-weight="700" font-family="DM Sans,sans-serif">{ht}</text>
      <text x="150" y="174" text-anchor="middle" dominant-baseline="middle"
            fill="{MUTED}" font-size="10" letter-spacing="2.5" font-family="DM Sans,sans-serif">BPM</text>
    </svg>
  </div>
</div>"""

# ── Cards ──────────────────────────────────────────────────────────────────────
def build_cards(active,cards):
    items=""
    for key,label,value,motiv,color in cards:
        is_act=active==key
        left=f"border-left:3px solid {color};" if is_act else f"border-left:3px solid transparent;"
        shadow="box-shadow:0 6px 24px rgba(0,0,0,0.1);" if is_act else "box-shadow:0 2px 8px rgba(0,0,0,0.05);"
        items+=f"""<a href="{'?' if is_act else f'?card={key}'}" target="_parent"
   style="text-decoration:none;flex:1;min-width:0;">
  <div style="background:rgba(239,235,229,0.88);backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px);
              border:1px solid rgba(201,196,187,0.55);{left}border-radius:14px;
              padding:18px 14px 14px;cursor:pointer;{shadow}transition:all .2s;
              box-sizing:border-box;min-height:110px;">
    <p style="font-family:'DM Sans',sans-serif;font-size:8px;letter-spacing:2px;color:{MUTED};
              text-transform:uppercase;margin:0 0 8px;font-weight:500;">{label}</p>
    <p style="font-family:'DM Sans',sans-serif;font-size:26px;font-weight:700;
              color:{color};margin:0;line-height:1;">{value}</p>
    <p style="font-family:'DM Sans',sans-serif;font-size:10px;color:{MUTED};
              margin:6px 0 0;line-height:1.4;">{motiv}</p>
  </div>
</a>"""
    return f"""<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@500;700&display=swap" rel="stylesheet">
<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:8px;width:100%;">
  {items}
</div>
<style>@media(max-width:640px){{div[style*="grid-template-columns:repeat(5"]{{grid-template-columns:repeat(2,1fr)!important;}}}}</style>"""

# ── Legend row ─────────────────────────────────────────────────────────────────
def legend_row(label,color,value_str,pct_val,goal_key,min_v,max_v,step):
    is_editing=st.session_state.editing==goal_key
    bar=dot_bar(pct_val,color)
    st.markdown(f"""<div style="display:flex;align-items:center;gap:12px;padding:10px 0;border-bottom:1px solid {BRD};">
  <div style="width:9px;height:9px;border-radius:2px;background:{color};flex-shrink:0;"></div>
  <span style="font-size:11px;letter-spacing:1.5px;color:{TEXT};text-transform:uppercase;font-weight:500;width:92px;">{label}</span>
  {bar}
  <span style="font-size:18px;font-weight:700;color:{TEXT};min-width:72px;text-align:right;">{value_str}</span>
</div>""",unsafe_allow_html=True)
    if not is_editing:
        bc,_=st.columns([1,12])
        with bc:
            if st.button("✎",key=f"pen_{goal_key}",type="secondary"):
                st.session_state.editing=goal_key; st.rerun()
    else:
        mc,sc2,pc,dc=st.columns([1,8,1,1])
        with mc:
            if st.button("−",key=f"m_{goal_key}",type="primary"):
                st.session_state[goal_key]=max(min_v,round(st.session_state[goal_key]-step,2)); st.rerun()
        with sc2:
            v=st.number_input("",min_value=float(min_v),max_value=float(max_v),
                              value=float(st.session_state[goal_key]),step=float(step),
                              key=f"ni_{goal_key}",label_visibility="collapsed")
            st.session_state[goal_key]=v
        with pc:
            if st.button("+",key=f"p_{goal_key}",type="primary"):
                st.session_state[goal_key]=min(max_v,round(st.session_state[goal_key]+step,2)); st.rerun()
        with dc:
            if st.button("✓",key=f"ok_{goal_key}",type="primary"):
                st.session_state.editing=None; st.rerun()
    st.markdown("<div style='height:4px;'></div>",unsafe_allow_html=True)

# ── Page ───────────────────────────────────────────────────────────────────────
st.markdown(f"""<div style="display:flex;align-items:baseline;gap:16px;margin-bottom:20px;">
  <h1 style="font-family:'DM Sans',sans-serif;font-size:26px;font-weight:700;color:{TEXT};margin:0;">Ali's Ring</h1>
  <span style="font-size:10px;letter-spacing:1px;color:{MUTED};text-transform:uppercase;">{end_date.strftime('%a %b %d %Y')} · {days}d</span>
</div>""",unsafe_allow_html=True)

# 5 cards on top
CARDS=[
    ("sleep","Sleep Score",f"{int(sleep_sc)}" if sleep_sc else "—",sleep_motiv(sleep_sc,sleep_h),sc(sleep_sc) if sleep_sc else MUTED),
    ("readiness","Readiness",f"{int(ready_sc)}" if ready_sc else "—",ready_motiv(ready_sc),sc(ready_sc) if ready_sc else MUTED),
    ("stress","Stress",s_label,stress_motiv(s_label),s_color),
    ("hr","Heart Rate",f"{rhr}" if rhr else f"{cur_hr}" if cur_hr else "—",hr_motiv(rhr or cur_hr),TEXT),
    ("activity","Activity",f"{int(steps):,}" if steps else "—",act_motiv(steps,stg),TAN),
]
components.html(build_cards(active,CARDS),height=140)

# Summary panel
if active:
    title,body=get_summary(active)
    st.markdown(f"""<div style="{FROSTED}padding:20px 24px;margin:10px 0 4px;">
  <p style="font-size:9px;letter-spacing:2.5px;color:{MUTED};text-transform:uppercase;margin:0 0 8px;font-weight:500;">{title}</p>
  <p style="font-size:15px;color:{TEXT};line-height:1.65;margin:0;">{body}</p>
</div>""",unsafe_allow_html=True)

st.markdown("<div style='height:6px;'></div>",unsafe_allow_html=True)

# Day summary
ds=day_summary_text()
st.markdown(f"""<div style="{FROSTED}padding:18px 22px;margin-bottom:10px;">
  <p style="font-size:9px;letter-spacing:2.5px;color:{MUTED};text-transform:uppercase;margin:0 0 8px;font-weight:500;">Today</p>
  <p style="font-size:14px;color:{TEXT};line-height:1.65;margin:0;">{ds}</p>
</div>""",unsafe_allow_html=True)

st.markdown("---")

# Rings + Legend
sp  = min(sleep_h/sg,  1.0) if sg  else 0
stp = min(steps/stg,   1.0) if stg else 0
cp  = min(cals/cg,     1.0) if cg  else 0

rc,lc=st.columns([4,6])
with rc:
    components.html(build_rings(sleep_h,sg,steps,stg,cals,cg,center_hr),height=355)
with lc:
    st.markdown("<div style='height:28px;'></div>",unsafe_allow_html=True)
    legend_row("Sleep",   ACCENT, f"{sleep_h:.1f}h",   sp,  "sleep_goal_h", 4.0,  12.0, 0.5)
    legend_row("Steps",   DARK,   f"{int(steps):,}",   stp, "steps_goal",   1000, 25000, 500)
    legend_row("Calories",TAN,    f"{int(cals)}",      cp,  "cal_goal",     100,  1500, 50)