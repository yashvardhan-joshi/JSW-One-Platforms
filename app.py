# app.py
import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Campaign Analytics | MSME", layout="wide")

# -------- Utility functions --------
@st.cache_data
def load_df(file_or_path):
    if hasattr(file_or_path, "read"):  # uploaded file
        df = pd.read_csv(file_or_path)
    else:
        df = pd.read_csv(file_or_path)
    # type coercions
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    num_cols = ['impressions','clicks','page_visits','signups','registrations','opportunities','orders','spend','target_cpl']
    for c in num_cols: df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
    df['market']  = df['market'].fillna('All Markets')
    df['segment'] = df['segment'].fillna('—')
    return df

def kpi_box(label, value, help_text=None):
    st.metric(label, value, help=help_text)

def flagged_table(df):
    leads = df['signups'].sum()
    regs  = df['registrations'].sum()
    spend = df['spend'].sum()

    out = df.copy()
    out['actual_cpl'] = out['spend'] / out['signups'].replace(0, np.nan)
    out['registration_rate'] = out['registrations'] / out['signups'].replace(0, np.nan)
    out['Reg Flag'] = np.where(out['registration_rate'].fillna(0) < 0.10, '⚠️', '✅')
    out['CPL Flag'] = np.where((np.abs(out['actual_cpl'] - out['target_cpl']) / out['target_cpl']).fillna(0) > 0.10, '⚠️', '✅')
    return out[['date','market','segment','source','campaign','registration_rate','actual_cpl','Reg Flag','CPL Flag']]

def format_inr(x): 
    try: return f"₹{float(x):,.0f}"
    except: return "₹0"

# -------- Sidebar --------
st.sidebar.title("Global Filters")

# Data source: default to repo CSV but allow upload
uploaded = st.sidebar.file_uploader("Upload consolidated CSV", type=["csv"])
default_path = "campaign_data_consolidated.csv"  # keep this file in your repo
df = load_df(uploaded if uploaded else default_path)

# Filters
months   = st.sidebar.multiselect("Month", sorted(df['date'].dt.to_period('M').astype(str).unique().tolist()))
markets  = st.sidebar.multiselect("Market (State)", sorted(df['market'].unique().tolist()))
segments = st.sidebar.multiselect("Segment (Industry)", sorted(df['segment'].unique().tolist()))
sources  = st.sidebar.multiselect("Source (Channel)", sorted(df['source'].unique().tolist()))
campaigns= st.sidebar.multiselect("Campaign", sorted(df['campaign'].unique().tolist()))

# Apply filters
f = df.copy()
if months:    f = f[f['date'].dt.to_period('M').astype(str).isin(months)]
if markets:   f = f[f['market'].isin(markets)]
if segments:  f = f[f['segment'].isin(segments)]
if sources:   f = f[f['source'].isin(sources)]
if campaigns: f = f[f['campaign'].isin(campaigns)]

st.sidebar.caption(f"Rows: {len(f):,}")

# Top-N and ranking metric
topn = st.sidebar.slider("Top N Campaigns", 3, 15, 5)
rank_metric = st.sidebar.selectbox("Rank by", ["Orders", "ROAS-proxy (Orders/Spend)"])

# -------- Header --------
st.title("Campaign Analytics Dashboard — MSME")
st.caption("Leads = FB Results + Google Conversions | Registrations = CRM Registered (1/0)")
st.divider()

# -------- KPI Row --------
col1, col2, col3, col4, col5 = st.columns(5)
kpi_box("Total Leads", f['signups'].sum())
kpi_box("Registrations", f['registrations'].sum())
kpi_box("Opportunities", f['opportunities'].sum())
kpi_box("Orders", f['orders'].sum())
kpi_box("Spend", format_inr(f['spend'].sum()))

st.divider()

# -------- Funnel --------
st.subheader("Funnel Analysis")
funnel = pd.DataFrame({
    "Stage": ["Impressions","Clicks","Leads","Registrations","Opportunities","Orders"],
    "Value": [f['impressions'].sum(), f['clicks'].sum(), f['signups'].sum(), f['registrations'].sum(), f['opportunities'].sum(), f['orders'].sum()]
})
funnel_chart = funnel.set_index("Stage")
st.bar_chart(funnel_chart)

# -------- Channel Performance --------
st.subheader("Channel Performance")
ch = f.groupby('source', as_index=False)[['signups','registrations','orders','spend']].sum()
ch = ch.sort_values('orders', ascending=False)
st.dataframe(ch.style.format({"spend":format_inr}))

# -------- Top Campaigns --------
st.subheader("Top Campaigns")
tc = f.groupby('campaign', as_index=False)[['orders','spend','signups','registrations']].sum()
tc['roas_proxy'] = np.where(tc['spend']>0, tc['orders']/tc['spend'], np.nan)
if rank_metric.startswith("Orders"):
    tc = tc.sort_values(['orders','roas_proxy'], ascending=False)
else:
    tc = tc.sort_values(['roas_proxy','orders'], ascending=False)
st.dataframe(tc.head(topn).style.format({"spend":format_inr, "roas_proxy":"{:.2f}"}))

# -------- Flag Summary --------
st.subheader("Flag Summary")
flags = flagged_table(f)
flags_fmt = flags.copy()
flags_fmt['registration_rate'] = (flags_fmt['registration_rate']*100).round(1).astype(str) + "%"
flags_fmt['actual_cpl'] = flags_fmt['actual_cpl'].apply(format_inr)
st.dataframe(flags_fmt)

# Export flags
csv = flags.to_csv(index=False).encode('utf-8')
st.download_button("Download flagged_campaigns.csv", data=csv, file_name="flagged_campaigns.csv", mime="text/csv")

st.divider()
st.caption("Tip: Upload a fresh consolidated CSV anytime to refresh the entire dashboard.")
