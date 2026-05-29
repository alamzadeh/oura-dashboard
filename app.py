import math
import streamlit as st
import httpx
import pandas as pd
import streamlit.components.v1 as components
from datetime import datetime, timedelta
from PIL import Image

try:
    _icon = Image.open("static/apple-touch-icon.png")
except:
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

F = ("background:rgba(239,235,229,0.88);"
     "backdrop-filter:blur(20px) saturate(1.5);"
     "-webkit-backdrop-filter:blur(20px) saturate(1.5);"
     "border:1px solid rgba(201,196,187,0.5);"
     "border-radius:16px;"
     "box-shadow:0 4px 20px rgba(0,0,0,0.06);")

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&display=swap');
html,body,.stApp,[data-testid="stAppViewContainer"],[data-testid="stMain"]{{
    background-color:{BG}!important;
    background-image:radial-gradient(circle,rgba(170,163,154,0.38) 1.5px,transparent 1.5px)!important;
    background-size:22px 22px!important;
    font-family:'DM Sans',sans-serif!important;
}}
[data-testid="stHeader"]{{background:{BG}!important;border-bottom:none!important;}}
section[data-testid="stSidebar"]{{background:{SURF}!important;border-right:1px solid {BRD}!important;}}
#MainMenu,footer,header{{visibility:hidden;}}
.block-container{{padding:1.5rem 1.5rem 3rem;max-width:1100px;}}
hr{{border:none!important;border-top:1px solid {BRD}!important;margin:1.2rem 0!important;}}
p,span,label{{color:{TEXT}!important;font-family:'DM Sans',sans-serif!important;}}

/* Edit pen */
button[data-testid="baseButton-secondary"]{{
    background:{SURF}!important;border:1px solid {BRD}!important;border-radius:6px!important;
    box-shadow:0 1px 2px rgba(0,0,0,0.07)!important;color:{DARK}!important;font-size:13px!important;
    width:30px!important;height:30px!important;min-height:30px!important;padding:0!important;cursor:pointer!important;
}}
button[data-testid="baseButton-secondary"]:hover{{background:{BRD}!important;}}

/* Orange buttons (plus / minus / confirm) */
button[data-testid="baseButton-primary"]{{
    background:{ACCENT}!important;border:1px solid {ACCENT}!important;border-radius:8px!important;
    box-shadow:0 2px 6px rgba(200,97,26,0.3)!important;color:#fff!important;
    font-size:16px!important;font-weight:700!important;
    min-width:36px!important;height:36px!important;min-height:36px!important;
    padding:0 8px!important;cursor:pointer!important;
}}
button[data-testid="baseButton-primary"]:hover{{background:#b5561a!important;}}

div[data-testid="stSlider"]{{padding:6px 0!important;}}
div[data-testid="stSlider"] label{{color:{MUTED}!important;font-size:11px!important;letter-spacing:1px;text-transform:uppercase;}}
</style>
""", unsafe_allow_html=True)

# PWA + local date
components.html("""
<script>
(function(){try{
  var p=window.parent.document,url=new URL(window.parent.location.href);
  var d=new Date(),ld=d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0');
  if(url.searchParams.get('ld')!==ld){
    var c=url.searchParams.get('card')||'';
    url.searchParams.set('ld',ld);
    c?url.searchParams.set('card',c):url.searchParams.delete('card');
    window.parent.location.replace(url.toString());return;
  }
  if(p.querySelector('meta[name="apple-mobile-web-app-capable"]'))return;
  [['apple-mobile-web-app-capable','yes'],['apple-mobile-web-app-status-bar-style','default'],
   ['apple-mobile-web-app-title',"Ali's Ring"],['theme-color','#E8E4DC'],['mobile-web-app-capable','yes']
  ].forEach(function(t){var m=p.createElement('meta');m.name=t[0];m.content=t[1];p.head.appendChild(m);});
  p.title="Ali's Ring";
}catch(e){}})();
</script>""", height=0)

for k,v in {"sleep_goal_h":8.0,"steps_goal":10000,"cal_goal":500,"editing":None}.items():
    if k not in st.session_state: st.session_state[k]=v
# Separate keys for sliders to avoid StreamlitAPIException
for gk in ["sleep_goal_h","steps_goal","cal_goal"]:
    sk=f"sl_{gk}"
    if sk not in st.session_state: st.session_state[sk]=float(st.session_state[gk])

saved_token = st.secrets.get("oura_token","") if hasattr(st,"secrets") else ""
with st.sidebar:
    st.markdown(f"<p style='font-size:10px;letter-spacing:2px;color:{MUTED};text-transform:uppercase;'>Settings</p>",unsafe_allow_html=True)
    token = saved_token if saved_token else st.text_input("Personal Access Token",type="password")
    days  = st.slider("Days",7,90,30)

if not token:
    st.markdown(f"<h1 style='font-family:DM Sans;font-size:32px;font-weight:700;color:{TEXT};'>Ali's Ring</h1>",unsafe_allow_html=True)
    st.info("Enter your token in the sidebar or save to `.streamlit/secrets.toml`"); st.stop()

end_date = datetime.now().date()
ld_str = st.query_params.get("ld","")
if ld_str:
    try: end_date = datetime.strptime(ld_str,"%Y-%m-%d").date()
    except: pass
start_date = end_date - timedelta(days=days)
raw = st.query_params.get("card","") or ""
active = raw if raw else None

@st.cache_data(ttl=300,show_spinner=False)
def fetch(ep,_tok,params):
    try:
        r=httpx.get(f"https://api.ouraring.com/v2/usercollection/{ep}",
                    params=params,headers={"Authorization":f"Bearer {_tok}"},timeout=15)
        r.raise_for_status(); return r.json().get("data",[])
    except httpx.HTTPStatusError as e:
        st.error("Invalid token." if e.response.status_code==401 else f"API error {e.response.status_code}"); return []
    except: return []

dp={"start_date":str(start_date),"end_date":str(end_date)}
hp={"start_datetime":f"{end_date}T00:00:00+00:00","end_datetime":f"{end_date}T23:59:59+00:00"}
with st.spinner(""):
    sd=fetch("daily_sleep",  token,dp); ad=fetch("daily_activity",token,dp)
    rd=fetch("daily_readiness",token,dp); dd=fetch("sleep",token,dp)
    hd=fetch("heartrate",token,hp);      xd=fetch("daily_stress",token,dp)

def to_df(data,dc="day"):
    if not data: return pd.DataFrame()
    df=pd.json_normalize(data)
    if dc in df.columns:
        df[dc]=pd.to_datetime(df[dc]); df=df.sort_values(dc).reset_index(drop=True)
    return df

sleep_df=to_df(sd); act_df=to_df(ad); ready_df=to_df(rd)
det_df=to_df(dd); hr_df=to_df(hd,"timestamp"); stress_df=to_df(xd)

def lat(df,col,d=0):
    if df.empty or col not in df.columns: return d
    v=df[col].dropna(); return float(v.iloc[-1]) if not v.empty else d

# Sleep hours
sleep_h=0.0
if not det_df.empty and "total_sleep_duration" in det_df.columns:
    rows=det_df[det_df["day"]==pd.Timestamp(end_date)]
    sleep_h=(rows["total_sleep_duration"].sum() if not rows.empty else det_df["total_sleep_duration"].iloc[-1])/3600

steps    = lat(act_df,"steps",0)
cals     = lat(act_df,"active_calories",0)
sleep_sc = lat(sleep_df,"score",0)
ready_sc = lat(ready_df,"score",0)

# Heart rate — use lowest_heart_rate from sleep (true resting HR proxy)
rhr = int(lat(det_df,"lowest_heart_rate",0)) or None
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

sg=st.session_state.sleep_goal_h; stg=st.session_state.steps_goal; cg=st.session_state.cal_goal
def sc(v): return "#3D6B3A" if v>=85 else ACCENT if v>=70 else "#8B2E1C"

# ── Prewritten text ────────────────────────────────────────────────────────────
def sleep_motiv(s,h):
    if not s: return "No data yet"
    if s>=85: return f"Outstanding. {h:.1f}h of quality rest."
    elif s>=70: return f"Good rest. {h:.1f}h logged."
    elif s>=50: return "Moderate. Aim for an earlier bedtime."
    else: return "Rest needed. Take it easy today."

def ready_motiv(s):
    if not s: return "No data yet"
    if s>=85: return "Primed. Push hard today."
    elif s>=70: return "Good shape. Moderate effort works."
    elif s>=50: return "Mixed signals. Keep it light."
    else: return "Rest day. Let your body recover."

def stress_motiv(l):
    return {"Restored":"Well recovered. Keep it up.","Balanced":"In check. Managing well.",
            "Elevated":"Some stress. Build in calm.","High":"High load. Protect your energy."}.get(l,"No data yet")

def hr_motiv(r):
    if not r: return "Lowest rate during sleep"
    if r<55: return f"{r} bpm · Excellent fitness marker."
    elif r<65: return f"{r} bpm · Heart working efficiently."
    elif r<75: return f"{r} bpm · Normal range."
    else: return f"{r} bpm · Slightly elevated."

def act_motiv(s,g):
    if not s: return "No data yet"
    p=s/g if g else 0
    if p>=1: return "Goal hit! Great movement today."
    elif p>=0.75: return "Almost there. Keep moving."
    elif p>=0.5: return "Halfway. Add some steps."
    else: return "Light day. Every step counts."

def get_summary(key):
    if key=="sleep":
        if not sleep_sc: return "Sleep","No sleep data yet."
        if sleep_sc>=85: return "Sleep",f"Outstanding night — {sleep_h:.1f}h of quality rest. Your body is fully recovered. A great day to push yourself."
        elif sleep_sc>=70: return "Sleep",f"Good sleep — {sleep_h:.1f}h logged. Solid energy reserves for today. Consistency will keep your scores here."
        elif sleep_sc>=50: return "Sleep",f"Moderate rest — {sleep_h:.1f}h. Partial recovery. Try winding down 30 minutes earlier tonight and reducing screen time before bed."
        else: return "Sleep",f"Limited rest — {sleep_h:.1f}h. Keep today light and make sleep the priority tonight."
    elif key=="readiness":
        if not ready_sc: return "Readiness","No readiness data yet."
        if ready_sc>=85: return "Readiness","Your body is primed. All signals are green — take on the day with confidence."
        elif ready_sc>=70: return "Readiness","You're in good shape. Moderate-to-hard effort is fine. Listen to your body and adjust."
        elif ready_sc>=50: return "Readiness","Mixed signals. Moderate activity is fine — avoid going all-out and give yourself extra recovery time."
        else: return "Readiness","Your body needs rest. Light movement, good nutrition, and an early night will set you up better tomorrow."
    elif key=="stress":
        t={"Restored":("Stress","Excellent recovery. Your body processed stress well and came back stronger. Keep your routine going."),
           "Balanced":("Stress","Stress and recovery are in balance. You're managing well — keep doing what you're doing."),
           "Elevated":("Stress","Elevated stress detected. Build in intentional calm: a walk, deep breathing, or quiet time will help bring this down."),
           "High":("Stress","High stress load. Protect your energy today, avoid overcommitting, and wind down properly tonight.")}
        return t.get(s_label,("Stress","No stress data for today."))
    elif key=="hr":
        if not rhr: return "Heart Rate","No resting heart rate yet — this is recorded during sleep."
        if rhr<55: return "Heart Rate",f"Resting at {rhr} bpm — excellent. A strong marker of cardiovascular fitness. Keep up your training."
        elif rhr<65: return "Heart Rate",f"Resting at {rhr} bpm — good range. Your heart is working efficiently at rest."
        elif rhr<75: return "Heart Rate",f"Resting at {rhr} bpm — normal range. Regular aerobic activity will continue to keep this healthy."
        else: return "Heart Rate",f"Resting at {rhr} bpm — slightly elevated. Can reflect stress, poor sleep, or illness. Worth monitoring if it stays up."
    elif key=="activity":
        p=steps/stg if stg else 0
        if p>=1: return "Activity",f"Goal reached — {int(steps):,} steps. Consistent daily movement like this is one of the best things you can do for long-term health."
        elif p>=0.75: return "Activity",f"{int(steps):,} steps — almost at your {int(stg):,} goal. A short walk would push you over."
        elif p>=0.5: return "Activity",f"{int(steps):,} steps — halfway. Some afternoon movement would make a real difference."
        else: return "Activity",f"{int(steps):,} steps — a light day. Even 15 minutes of walking benefits your health. Every step counts."
    return "","No data."

def day_summary_text():
    scores=[s for s in [sleep_sc,ready_sc] if s]
    avg=sum(scores)/len(scores) if scores else 0
    sp=steps/stg if stg and steps else 0
    if avg>=85 and s_label in ["Balanced","Restored"] and sp>=0.8:
        return "Everything is pointing in the right direction. Well-rested, recovered, stress in check, and moving well — this is a strong health day."
    elif avg>=80 and s_label in ["Balanced","Restored"]:
        return "A strong day overall. Sleep and recovery are solid, stress is managed. Keep the momentum with consistent movement and a good bedtime."
    elif avg>=70:
        return "A decent day. Body functioning well with room to improve. Wind down properly tonight and stay active through the day."
    elif avg>=55:
        return "Mixed signals. Some recovery is lagging. Moderate your activity, stay hydrated, and prioritize sleep tonight."
    elif avg>0:
        return "Your body is in recovery mode today. Rest is where adaptation happens — take it easy, eat well, and let your body do its work."
    else:
        return "Waiting for today's data to sync from your ring."

# ── Dots ───────────────────────────────────────────────────────────────────────
def circ_dots(cx,cy,r,pct,color,n=54):
    n_lit=int(round(min(pct,1.0)*n)); out=[]
    for i in range(n):
        a=(i/n)*2*math.pi-math.pi/2
        px=cx+r*math.cos(a); py=cy+r*math.sin(a)
        fill=color if i<n_lit else "#C5C0B7"
        op="1" if i<n_lit else "0.5"
        out.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="3.5" fill="{fill}" opacity="{op}"/>')
    return "".join(out)

def dot_bar(pct,color,n=22,sz=5):
    n_lit=int(round(min(pct,1.0)*n)); dots=[]
    for i in range(n):
        fill=color if i<n_lit else "#C5C0B7"
        op="1" if i<n_lit else "0.5"
        dots.append(f'<div style="width:{sz}px;height:{sz}px;border-radius:1px;background:{fill};opacity:{op};flex-shrink:0;"></div>')
    return f'<div style="display:flex;gap:3px;align-items:center;">{"".join(dots)}</div>'

# ── Rings ──────────────────────────────────────────────────────────────────────
def build_rings(sleep_h,sg,steps,stg,cals,cg,hr):
    def p(v,g): return min(v/g,1.0) if g>0 else 0
    cx=cy=150
    r1=circ_dots(cx,cy,128,p(sleep_h,sg),ACCENT,n=64)
    r2=circ_dots(cx,cy, 96,p(steps,stg),DARK,  n=48)
    r3=circ_dots(cx,cy, 64,p(cals,cg),  TAN,   n=32)
    ht=str(hr) if hr else "—"
    return f"""<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@600;700&display=swap" rel="stylesheet">
<style>body{{background:transparent!important;margin:0;padding:0;}}</style>
<div style="display:flex;justify-content:center;padding:4px 0 8px;">
  <div style="background:rgba(239,235,229,0.88);backdrop-filter:blur(20px) saturate(1.5);
              -webkit-backdrop-filter:blur(20px) saturate(1.5);
              border:1px solid rgba(201,196,187,0.5);border-radius:20px;
              padding:20px;display:inline-block;
              box-shadow:0 4px 20px rgba(0,0,0,0.06);">
    <svg width="300" height="300" viewBox="0 0 300 300" overflow="visible">
      <circle cx="150" cy="150" r="148" fill="rgba(239,235,229,0.5)"/>
      {r1}{r2}{r3}
      <text x="150" y="144" text-anchor="middle" dominant-baseline="middle"
            fill="{TEXT}" font-size="50" font-weight="700" font-family="DM Sans,sans-serif">{ht}</text>
      <text x="150" y="174" text-anchor="middle" dominant-baseline="middle"
            fill="{MUTED}" font-size="10" letter-spacing="2.5" font-family="DM Sans,sans-serif">BPM</text>
    </svg>
  </div>
</div>"""

# ── Cards — onclick JS, no <a> tags, no new tab ────────────────────────────────
def build_cards(active,cards):
    items=""
    for key,label,value,motiv,color in cards:
        is_act=active==key
        left=f"border-left:3px solid {color};" if is_act else "border-left:3px solid transparent;"
        shad="box-shadow:0 4px 16px rgba(0,0,0,0.1);" if is_act else "box-shadow:0 1px 4px rgba(0,0,0,0.06);"
        items+=f"""
<div onclick="sel('{key}')"
     style="background:rgba(239,235,229,0.92);backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px);
            border:1px solid rgba(201,196,187,0.5);{left}border-radius:12px;
            padding:12px 8px;cursor:pointer;{shad}transition:all .2s;
            box-sizing:border-box;height:76px;display:flex;flex-direction:column;justify-content:center;gap:5px;">
  <p style="font-family:'DM Sans',sans-serif;font-size:7px;letter-spacing:1.5px;color:{MUTED};
            text-transform:uppercase;margin:0;font-weight:600;
            white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{label}</p>
  <p style="font-family:'DM Sans',sans-serif;font-size:19px;font-weight:700;
            color:{color};margin:0;line-height:1;
            white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{value}</p>
</div>"""
    return f"""
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@600;700&display=swap" rel="stylesheet">
<style>
  body{{background:transparent!important;margin:0;padding:0;overflow:hidden;}}
  .grid{{display:grid;grid-template-columns:repeat(5,1fr);gap:5px;width:100%;box-sizing:border-box;}}
</style>
<div class="grid">{items}</div>
<script>
function sel(key){{
  try{{
    var p=window.parent,s=new URLSearchParams(p.location.search);
    var curr=s.get('card')||'';
    p.location.replace(p.location.pathname+(curr===key?'':'?card='+key));
  }}catch(e){{console.log(e);}}
}}
</script>"""

# ── Legend row with slider + orange ± buttons ──────────────────────────────────
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
        sk=f"sl_{goal_key}"
        mc,sc2,pc,dc=st.columns([1,9,1,1])
        with mc:
            if st.button("−",key=f"m_{goal_key}",type="primary"):
                nv=max(float(min_v),round(float(st.session_state[goal_key])-float(step),2))
                st.session_state[goal_key]=nv
                st.session_state[sk]=nv
                st.rerun()
        with sc2:
            # Use separate slider key — no value= param, reads from session_state[sk]
            st.slider("",float(min_v),float(max_v),step=float(step),
                      key=sk,label_visibility="collapsed")
            st.session_state[goal_key]=float(st.session_state[sk])
        with pc:
            if st.button("+",key=f"p_{goal_key}",type="primary"):
                nv=min(float(max_v),round(float(st.session_state[goal_key])+float(step),2))
                st.session_state[goal_key]=nv
                st.session_state[sk]=nv
                st.rerun()
        with dc:
            if st.button("✓",key=f"ok_{goal_key}",type="primary"):
                st.session_state.editing=None; st.rerun()
    st.markdown("<div style='height:4px;'></div>",unsafe_allow_html=True)

# ── Page ───────────────────────────────────────────────────────────────────────
st.markdown(f"""<div style="display:flex;align-items:baseline;gap:16px;margin-bottom:20px;">
  <h1 style="font-family:'DM Sans',sans-serif;font-size:26px;font-weight:700;color:{TEXT};margin:0;">Ali's Ring</h1>
  <span style="font-size:10px;letter-spacing:1px;color:{MUTED};text-transform:uppercase;">{end_date.strftime('%a %b %d %Y')} · {days}d</span>
</div>""",unsafe_allow_html=True)

# Cards
CARDS=[
    ("sleep","Sleep Score",f"{int(sleep_sc)}" if sleep_sc else "—",sleep_motiv(sleep_sc,sleep_h),sc(sleep_sc) if sleep_sc else MUTED),
    ("readiness","Readiness",f"{int(ready_sc)}" if ready_sc else "—",ready_motiv(ready_sc),sc(ready_sc) if ready_sc else MUTED),
    ("stress","Stress",s_label,stress_motiv(s_label),s_color),
    ("hr","Heart Rate",f"{rhr} bpm" if rhr else "—",hr_motiv(rhr),"#1C1917"),
    ("activity","Activity",f"{int(steps):,}" if steps else "—",act_motiv(steps,stg),TAN),
]
components.html(build_cards(active,CARDS),height=96)

# Text summary panel
if active:
    title,body=get_summary(active)
    st.markdown(f"""<div style="{F}padding:20px 24px;margin:6px 0 4px;">
  <p style="font-size:9px;letter-spacing:2.5px;color:{MUTED};text-transform:uppercase;margin:0 0 8px;font-weight:500;">{title}</p>
  <p style="font-size:15px;color:{TEXT};line-height:1.65;margin:0;">{body}</p>
</div>""",unsafe_allow_html=True)

st.markdown("<div style='height:4px;'></div>",unsafe_allow_html=True)

# Day summary
ds=day_summary_text()
st.markdown(f"""<div style="{F}padding:18px 22px;margin-bottom:12px;">
  <p style="font-size:9px;letter-spacing:2.5px;color:{MUTED};text-transform:uppercase;margin:0 0 8px;font-weight:500;">Today</p>
  <p style="font-size:14px;color:{TEXT};line-height:1.65;margin:0;">{ds}</p>
</div>""",unsafe_allow_html=True)

st.markdown("---")

# Rings + Legend
sp=min(sleep_h/sg,1.0) if sg else 0
stp=min(steps/stg,1.0) if stg else 0
cp=min(cals/cg,1.0) if cg else 0
rc,lc=st.columns([4,6])
with rc:
    components.html(build_rings(sleep_h,sg,steps,stg,cals,cg,center_hr),height=355)
with lc:
    st.markdown("<div style='height:28px;'></div>",unsafe_allow_html=True)
    legend_row("Sleep",   ACCENT,f"{sleep_h:.1f}h",  sp, "sleep_goal_h",4.0,  12.0, 0.5)
    legend_row("Steps",   DARK,  f"{int(steps):,}",  stp,"steps_goal",  1000, 25000,500)
    legend_row("Calories",TAN,   f"{int(cals)}",     cp, "cal_goal",    100,  1500, 50)