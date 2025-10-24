# app.py (patched)
import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path

st.set_page_config(page_title="Campaign Analytics | JSW One Platforms", layout="wide")

# -------- Utility functions --------
@st.cache_data(show_spinner=False)
def load_df_any(src):
    """Load CSV from uploaded file handle, local path, or URL."""
    if hasattr(src, "read"):  # uploaded file-like
        return pd.read_csv(src)
    return pd.read_csv(src)   # local path or URL

def coerce_schema(df: pd.DataFrame) -> pd.DataFrame:
    # Dates & numerics
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    num_cols = [
        'impressions','clicks','page_visits','signups','registrations',
        'opportunities','orders','spend','target_cpl'
    ]
    for c in num_cols:
        if c not in df.columns:
            df[c] = 0
        df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)

    # Ensure categorical columns exist
    for c, default in [('market','All Markets'),('segment','—'),('source','Unknown'),('campaign','Unknown')]:
        if c not in df.columns:
            df[c] = default
        else:
            df[c] = df[c].fillna(default)
    return df

# -------- Data source handling --------
st.sidebar.title("Global Filters")
uploaded = st.sidebar.file_uploader("Upload consolidated CSV", type=["csv"])

DEFAULT_CSV = "campaign_data_consolidated.csv"  # expected in repo root
DEFAULT_CSV_URL = st.secrets.get("DEFAULT_CSV_URL")  # optional raw GitHub URL fallback

if uploaded:
    df = coerce_schema(load_df_any(uploaded))
elif Path(DEFAULT_CSV).exists():
    df = coerce_schema(load_df_any(DEFAULT_CSV))
elif DEFAULT_CSV_URL:
    df = coerce_schema(load_df_any(DEFAULT_CSV_URL))
else:
    st.error(
        "No data file found.\n\n"
        "Please either:\n"
        "• Upload a consolidated CSV (sidebar), or\n"
        f"• Commit `{DEFAULT_CSV}` to the repo root, or\n"
        "• Set `DEFAULT_CSV_URL` in Streamlit Secrets to a raw GitHub URL."
    )
    st.stop()

# -------- Filters --------
months   = st.sidebar.multiselect("Month", sorted(df['date'].dt.to_period('M').astype(str).unique().tolist()))
markets  = st.sidebar.multiselect("Market (State)", sorted(df['market'].dropna().unique().tolist()))
segments = st.sidebar.multiselect("Segment (Industry)", sorted(df['segment'].dropna().unique().tolist()))
sources  = st.sidebar.multiselect("Source (Channel)", sorted(df['source'].dropna().unique().tolist()))
campaigns= st.sidebar.multiselect("Campaign", sorted(df['campaign'].dropna().unique().tolist()))

f = df.copy()
if months:    f = f[f['date'].dt.to_period('M').astype(str).isin(months)]
if markets:   f = f[f['market'].isin(markets)]
if segments:  f = f[f['segment'].isin(segments)]
if sources:   f = f[f['source'].isin(sources)]
if campaigns: f = f[f['campaign'].isin(campaigns)]

st.sidebar.caption(f"Rows: {len(f):,}")

# Top-N & ranking metric
topn = st.sidebar.slider("Top N Campaigns", 3, 20, 5)
rank_metric = st.sidebar.selectbox("Rank by", ["Orders", "ROAS-proxy (Orders/Spend)"])

# -------- Header --------
st.title("Campaign Analytics Dashboard — JSW One Platforms (MSME)")
st.caption("Leads = FB Results + Google Conversions | Registrations = CRM Registered (1/0)")
st.divider()

# -------- KPIs --------
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Leads", int(f['signups'].sum()))
col2.metric("Registrations", int(f['registrations'].sum()))
col3.metric("Opportunities", int(f['opportunities'].sum()))
col4.metric("Orders", int(f['orders'].sum()))
col5.metric("Spend", f"₹{float(f['spend'].sum()):,.0f}")

st.divider()

# -------- Funnel --------
st.subheader("Funnel Analysis")
funnel = pd.DataFrame({
    "Stage": ["Impressions","Clicks","Leads","Registrations","Opportunities","Orders"],
    "Value": [f['impressions'].sum(), f['clicks'].sum(), f['signups'].sum(), f['registrations'].sum(), f['opportunities'].sum(), f['orders'].sum()]
})
st.bar_chart(funnel.set_index("Stage"))

# -------- Channel Performance --------
st.subheader("Channel Performance")
ch = f.groupby('source', as_index=False)[['signups','registrations','orders','spend']].sum()
ch = ch.sort_values('orders', ascending=False)
st.dataframe(ch.style.format({"spend": lambda x: f"₹{x:,.0f}"}))

# -------- Top Campaigns --------
st.subheader("Top Campaigns")
tc = f.groupby('campaign', as_index=False)[['orders','spend','signups','registrations']].sum()
tc['roas_proxy'] = np.where(tc['spend']>0, tc['orders']/tc['spend'], np.nan)
if rank_metric.startswith("Orders"):
    tc = tc.sort_values(['orders','roas_proxy'], ascending=False)
else:
    tc = tc.sort_values(['roas_proxy','orders'], ascending=False)
st.dataframe(tc.head(topn).style.format({"spend": lambda x: f"₹{x:,.0f}", "roas_proxy": "{:.2f}"}))

# -------- Flag Summary --------
st.subheader("Flag Summary")
out = f.copy()
out['actual_cpl'] = out['spend'] / out['signups'].replace(0, np.nan)
out['registration_rate'] = out['registrations'] / out['signups'].replace(0, np.nan)
out['Reg Flag'] = np.where(out['registration_rate'].fillna(0) < 0.10, '⚠️', '✅')
out['CPL Flag'] = np.where((np.abs(out['actual_cpl'] - out['target_cpl']) / out['target_cpl']).fillna(0) > 0.10, '⚠️', '✅')
flags = out[['date','market','segment','source','campaign','registration_rate','actual_cpl','Reg Flag','CPL Flag']].copy()
flags_fmt = flags.copy()
flags_fmt['registration_rate'] = (flags_fmt['registration_rate']*100).round(1).astype(str) + "%"
flags_fmt['actual_cpl'] = flags_fmt['actual_cpl'].apply(lambda x: f"₹{x:,.0f}" if pd.notna(x) else "₹0")
st.dataframe(flags_fmt)

# Export flags
csv = flags.to_csv(index=False).encode('utf-8')
st.download_button("Download flagged_campaigns.csv", data=csv, file_name="flagged_campaigns.csv", mime="text/csv")

st.divider()
st.caption("Upload a fresh consolidated CSV anytime to refresh the dashboard. For scheduled updates, commit a new campaign_data_consolidated.csv to this repo.")
