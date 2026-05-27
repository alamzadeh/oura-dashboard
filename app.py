import streamlit as st
import httpx
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

st.set_page_config(page_title="Oura Dashboard", page_icon="💍", layout="wide")

BASE_URL = "https://api.ouraring.com/v2/usercollection"

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("💍 Oura Dashboard")
    token = st.text_input(
        "Personal Access Token",
        type="password",
        help="Get it at cloud.ouraring.com/personal-access-tokens",
    )
    days = st.slider("Days to display", 7, 90, 30)
    st.markdown("---")
    st.caption("Your token is never stored or sent anywhere except Oura's API.")

if not token:
    st.title("💍 Oura Dashboard")
    st.info("👈 Enter your Oura Personal Access Token in the sidebar to get started.")
    st.markdown("""
    **How to get your token:**
    1. Go to [cloud.ouraring.com/personal-access-tokens](https://cloud.ouraring.com/personal-access-tokens)
    2. Sign in with your Oura account
    3. Click **Create New Personal Access Token**
    4. Copy it and paste it in the sidebar
    """)
    st.stop()

end_date = datetime.now().date()
start_date = end_date - timedelta(days=days)


# ── Data fetching ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def fetch(endpoint: str, _token: str, start, end):
    try:
        r = httpx.get(
            f"{BASE_URL}/{endpoint}",
            params={"start_date": str(start), "end_date": str(end)},
            headers={"Authorization": f"Bearer {_token}"},
            timeout=15,
        )
        r.raise_for_status()
        return r.json().get("data", [])
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            st.error("❌ Invalid token — double-check your Personal Access Token.")
        else:
            st.error(f"API error: {e.response.status_code}")
        return []
    except Exception as e:
        st.error(f"Connection error: {e}")
        return []


with st.spinner("Fetching your data from Oura..."):
    sleep_data = fetch("daily_sleep", token, start_date, end_date)
    readiness_data = fetch("daily_readiness", token, start_date, end_date)
    activity_data = fetch("daily_activity", token, start_date, end_date)

if not any([sleep_data, readiness_data, activity_data]):
    st.warning("No data returned. Check your token or try a wider date range.")
    st.stop()


# ── Helpers ────────────────────────────────────────────────────────────────────
def to_df(data, date_col="day"):
    if not data:
        return pd.DataFrame()
    df = pd.json_normalize(data)
    if date_col in df.columns:
        df[date_col] = pd.to_datetime(df[date_col])
        df = df.sort_values(date_col).reset_index(drop=True)
    return df


def score_color(score):
    if score >= 85:
        return "green"
    elif score >= 70:
        return "orange"
    return "red"


sleep_df = to_df(sleep_data)
readiness_df = to_df(readiness_data)
activity_df = to_df(activity_data)


# ── Header metrics ─────────────────────────────────────────────────────────────
st.title("💍 Oura Dashboard")
st.caption(f"Showing {days} days — {start_date} to {end_date}")

col1, col2, col3 = st.columns(3)

for df, label, col in [
    (sleep_df, "Sleep Score", col1),
    (readiness_df, "Readiness Score", col2),
    (activity_df, "Activity Score", col3),
]:
    if not df.empty and "score" in df.columns:
        latest = int(df["score"].iloc[-1])
        prev = int(df["score"].iloc[-2]) if len(df) > 1 else latest
        delta = latest - prev
        col.metric(label, latest, f"{'+' if delta >= 0 else ''}{delta} vs yesterday")

st.markdown("---")


# ── Tabs ───────────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["😴 Sleep", "⚡ Readiness", "🏃 Activity"])


# Sleep tab
with tab1:
    if sleep_df.empty:
        st.info("No sleep data available.")
    else:
        if "score" in sleep_df.columns:
            fig = px.line(
                sleep_df, x="day", y="score",
                title="Sleep Score Over Time",
                labels={"day": "Date", "score": "Score"},
                markers=True,
            )
            fig.add_hline(y=85, line_dash="dash", line_color="green", annotation_text="Excellent (85+)")
            fig.add_hline(y=70, line_dash="dash", line_color="orange", annotation_text="Good (70+)")
            fig.update_layout(yaxis_range=[0, 100])
            st.plotly_chart(fig, use_container_width=True)

        # Sleep stage contributors
        c1, c2 = st.columns(2)
        if "contributors.deep_sleep" in sleep_df.columns:
            fig2 = px.bar(
                sleep_df, x="day", y="contributors.deep_sleep",
                title="Deep Sleep Score", color_discrete_sequence=["#4B6BFB"],
                labels={"contributors.deep_sleep": "Score", "day": "Date"},
            )
            c1.plotly_chart(fig2, use_container_width=True)

        if "contributors.rem_sleep" in sleep_df.columns:
            fig3 = px.bar(
                sleep_df, x="day", y="contributors.rem_sleep",
                title="REM Sleep Score", color_discrete_sequence=["#9B59B6"],
                labels={"contributors.rem_sleep": "Score", "day": "Date"},
            )
            c2.plotly_chart(fig3, use_container_width=True)

        # HRV
        hrv_col = next(
            (c for c in sleep_df.columns if "average_hrv" in c or "hrv" in c.lower()),
            None,
        )
        if hrv_col:
            fig4 = px.line(
                sleep_df, x="day", y=hrv_col,
                title="HRV (Heart Rate Variability)",
                labels={hrv_col: "HRV (ms)", "day": "Date"},
                markers=True,
                color_discrete_sequence=["#E74C3C"],
            )
            st.plotly_chart(fig4, use_container_width=True)

        # Raw table toggle
        with st.expander("Raw sleep data"):
            st.dataframe(sleep_df)


# Readiness tab
with tab2:
    if readiness_df.empty:
        st.info("No readiness data available.")
    else:
        if "score" in readiness_df.columns:
            fig = px.area(
                readiness_df, x="day", y="score",
                title="Readiness Score Over Time",
                labels={"day": "Date", "score": "Score"},
                color_discrete_sequence=["#2ECC71"],
            )
            fig.add_hline(y=85, line_dash="dash", line_color="green", annotation_text="Excellent (85+)")
            fig.update_layout(yaxis_range=[0, 100])
            st.plotly_chart(fig, use_container_width=True)

        # Contributors breakdown for latest day
        contrib_cols = [c for c in readiness_df.columns if c.startswith("contributors.")]
        if contrib_cols:
            latest_row = readiness_df.iloc[-1][contrib_cols]
            latest_row.index = latest_row.index.str.replace("contributors.", "").str.replace("_", " ").str.title()
            fig2 = px.bar(
                x=latest_row.index, y=latest_row.values,
                title=f"Readiness Contributors — {readiness_df['day'].iloc[-1].date()}",
                labels={"x": "Factor", "y": "Score"},
                color=latest_row.values,
                color_continuous_scale="RdYlGn",
                range_color=[0, 100],
            )
            st.plotly_chart(fig2, use_container_width=True)

        with st.expander("Raw readiness data"):
            st.dataframe(readiness_df)


# Activity tab
with tab3:
    if activity_df.empty:
        st.info("No activity data available.")
    else:
        if "score" in activity_df.columns:
            fig = px.line(
                activity_df, x="day", y="score",
                title="Activity Score Over Time",
                labels={"day": "Date", "score": "Score"},
                markers=True,
                color_discrete_sequence=["#F39C12"],
            )
            fig.update_layout(yaxis_range=[0, 100])
            st.plotly_chart(fig, use_container_width=True)

        c1, c2 = st.columns(2)
        if "steps" in activity_df.columns:
            fig2 = px.bar(
                activity_df, x="day", y="steps",
                title="Daily Steps",
                labels={"steps": "Steps", "day": "Date"},
                color_discrete_sequence=["#3498DB"],
            )
            fig2.add_hline(y=10000, line_dash="dash", line_color="green", annotation_text="10k goal")
            c1.plotly_chart(fig2, use_container_width=True)

        if "active_calories" in activity_df.columns:
            fig3 = px.bar(
                activity_df, x="day", y="active_calories",
                title="Active Calories",
                labels={"active_calories": "Calories", "day": "Date"},
                color_discrete_sequence=["#E67E22"],
            )
            c2.plotly_chart(fig3, use_container_width=True)

        with st.expander("Raw activity data"):
            st.dataframe(activity_df)
