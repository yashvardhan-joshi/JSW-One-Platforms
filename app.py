# app.py
import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Campaign Analytics | JSW One Platforms", layout="wide")

# -------- Utility functions --------
@st.cache_data
def load_df(file_or_path):
    if hasattr(file_or_path, "read"):  # uploaded file
        df = pd.read_csv(file_or_path)
    else:
        df = pd.read_csv(file_or_path)
    # coercions
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    num_cols = ['impressions','clicks','page_visits','signups','registrations','opportunities','orders','spend','target_cpl']
    for c in num_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
    df['market']  = df.get('market', '').fillna('All Markets')
    df['segment'] = df.get('segment', '').fillna('—')
    return df

def format_inr(x):
    try:
        return f"₹{float(x):,.0f}"
    except:
        return "₹0"

# -------- Sidebar --------
st.sidebar.title("Global Filters")

# Data source: default to repo CSV but allow upload
uploaded = st.sidebar.file_uploader("Upload consolidated CSV", type=["csv"]) 
# NOTE: keep a default CSV named 'campaign_data_consolidated.csv' in repo root
DEFAULT_CSV = "campaign_data_consolidated.csv"

df = load_df(uploaded if uploaded else DEFAULT_CSV)

# Filters
months   = st.sidebar.multiselect("Month", sorted(df['date'].dt.to_period('M').astype(str).unique().tolist()))
markets  = st.sidebar.multiselect("Market (State)", sorted(df['market'].dropna().unique().tolist()))
segments = st.sidebar.multiselect("Segment (Industry)", sorted(df['segment'].dropna().unique().tolist()))
sources  = st.sidebar.multiselect("Source (Channel)", sorted(df['source'].dropna().unique().tolist()))
campaigns= st.sidebar.multiselect("Campaign", sorted(df['campaign'].dropna().unique().tolist()))

# Apply filters
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
col5.metric("Spend", format_inr(f['spend'].sum()))

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
st.dataframe(ch.style.format({"spend": format_inr}))

# -------- Top Campaigns --------
st.subheader("Top Campaigns")
tc = f.groupby('campaign', as_index=False)[['orders','spend','signups','registrations']].sum()
tc['roas_proxy'] = np.where(tc['spend']>0, tc['orders']/tc['spend'], np.nan)
if rank_metric.startswith("Orders"):
    tc = tc.sort_values(['orders','roas_proxy'], ascending=False)
else:
    tc = tc.sort_values(['roas_proxy','orders'], ascending=False)
st.dataframe(tc.head(topn).style.format({"spend": format_inr, "roas_proxy": "{:.2f}"}))

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
flags_fmt['actual_cpl'] = flags_fmt['actual_cpl'].apply(format_inr)
st.dataframe(flags_fmt)

# Export flags
csv = flags.to_csv(index=False).encode('utf-8')
st.download_button("Download flagged_campaigns.csv", data=csv, file_name="flagged_campaigns.csv", mime="text/csv")

st.divider()
st.caption("Upload a fresh consolidated CSV anytime to refresh the dashboard. For scheduled updates, commit a new campaign_data_consolidated.csv to this repo.")
