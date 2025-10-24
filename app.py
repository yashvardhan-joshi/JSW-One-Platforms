# app.py — Advanced Analytics Workbench (JSW One Platforms | MSME)
import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path

import plotly.express as px
import plotly.graph_objects as go

import statsmodels.api as sm
from statsmodels.stats.proportion import proportions_ztest
from statsmodels.stats.outliers_influence import variance_inflation_factor
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from scipy.stats import zscore

st.set_page_config(page_title="JSW One Platforms | MSME Analytics", layout="wide")

# ----------------------- Data utilities -----------------------
@st.cache_data(show_spinner=False)
def load_df(src):
    if hasattr(src, "read"):  # uploaded file
        df = pd.read_csv(src)
    else:
        df = pd.read_csv(src)

    # Schema coercion
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    for c in ['impressions','clicks','page_visits','leads','registrations',
              'opportunities','orders','spend','target_cpl']:
        if c not in df.columns:
            df[c] = 0
        df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)

    for c, default in [('market','All Markets'),('segment','—'),('source','Unknown'),('campaign','Unknown')]:
        if c not in df.columns: df[c] = default
        df[c] = df[c].fillna(default)

    # Derived metrics
    df['reg_rate']   = df['registrations'] / df['leads'].replace(0, np.nan)
    df['opp_rate']   = df['opportunities'] / df['leads'].replace(0, np.nan)
    df['order_rate'] = df['orders'] / df['leads'].replace(0, np.nan)
    df['cpl'] = df['spend'] / df['leads'].replace(0, np.nan)
    return df

def ci_normal(p, n, z=1.96):
    """Normal approx CI for a proportion."""
    if n <= 0 or pd.isna(p): return (np.nan, np.nan)
    se = np.sqrt(p*(1-p)/n)
    return (p - z*se, p + z*se)

def add_ci_rates(g):
    out = []
    for _, r in g.iterrows():
        rr_l, rr_u = ci_normal(r['reg_rate'], r['leads'])
        or_l, or_u = ci_normal(r['order_rate'], r['leads'])
        out.append((rr_l, rr_u, or_l, or_u))
    g[['reg_ci_lo','reg_ci_hi','ord_ci_lo','ord_ci_hi']] = pd.DataFrame(out, index=g.index)
    return g

def ensure_nonneg(s): return s.fillna(0).clip(lower=0)

# ----------------------- Data Ingestion -----------------------
st.sidebar.title("Data")
uploaded = st.sidebar.file_uploader("Upload consolidated CSV (with 'leads' column)", type=["csv"])
DEFAULT_CSV = "campaign_data_consolidated.csv"
DEFAULT_CSV_URL = st.secrets.get("DEFAULT_CSV_URL")

if uploaded:
    df = load_df(uploaded)
elif Path(DEFAULT_CSV).exists():
    df = load_df(DEFAULT_CSV)
elif DEFAULT_CSV_URL:
    df = load_df(DEFAULT_CSV_URL)
else:
    st.error(
        "No data file found.\n\n"
        "Please either:\n"
        "• Upload a consolidated CSV (sidebar), or\n"
        f"• Commit `{DEFAULT_CSV}` to the repo root, or\n"
        "• Set `DEFAULT_CSV_URL` in Streamlit Secrets to a raw GitHub URL."
    )
    st.stop()

# ----------------------- Global Filters -----------------------
st.sidebar.title("Filters")
months   = st.sidebar.multiselect("Month", sorted(df['date'].dt.to_period('M').astype(str).unique().tolist()))
markets  = st.sidebar.multiselect("Market (State)", sorted(df['market'].dropna().unique().tolist()))
segments = st.sidebar.multiselect("Segment (Industry)", sorted(df['segment'].dropna().unique().tolist()))
sources  = st.sidebar.multiselect("Source (Channel)", sorted(df['source'].dropna().unique().tolist()))
campaigns= st.sidebar.multiselect("Campaign", sorted(df['campaign'].dropna().unique().tolist()))

f = df.copy()
if months:   f = f[f['date'].dt.to_period('M').astype(str).isin(months)]
if markets:  f = f[f['market'].isin(markets)]
if segments: f = f[f['segment'].isin(segments)]
if sources:  f = f[f['source'].isin(sources)]
if campaigns:f = f[f['campaign'].isin(campaigns)]

st.sidebar.caption(f"Rows: {len(f):,}")

# ----------------------- Header & KPI -----------------------
st.title("MSME Campaign Analytics — JSW One Platforms")
st.caption("Leads = COUNT DISTINCT SFID (Salesforce) • Registrations = SUM(Registered 1/0) • Media adds Delivery & Spend")

kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
kpi1.metric("Total Leads", int(f['leads'].sum()))
kpi2.metric("Registrations", int(f['registrations'].sum()))
kpi3.metric("Opportunities", int(f['opportunities'].sum()))
kpi4.metric("Orders", int(f['orders'].sum()))
kpi5.metric("Spend (₹)", f"₹{float(f['spend'].sum()):,.0f}")

st.divider()

# ----------------------- Tabs -----------------------
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "Overview", "Diagnostics", "Cohorts", "Drivers (Model)", "Forecast", "A/B Test"
])

# ======================= TAB 1: OVERVIEW =======================
with tab1:
    colA, colB = st.columns([1,1])
    with colA:
        st.subheader("Funnel (Leads → Registrations → Opportunities → Orders)")
        # Pure conversion funnel, no Impressions
        fun_vals = [
            ensure_nonneg(f['leads']).sum(),
            ensure_nonneg(f['registrations']).sum(),
            ensure_nonneg(f['opportunities']).sum(),
            ensure_nonneg(f['orders']).sum()
        ]
        fun_labels = ["Leads","Registrations","Opportunities","Orders"]
        fig_funnel = go.Figure(go.Funnel(
            y=fun_labels,
            x=fun_vals,
            textinfo="value+percent initial",
            marker={"color":["#6FA8DC","#3D85C6","#134F5C","#0C343D"]}
        ))
        st.plotly_chart(fig_funnel, use_container_width=True)

    with colB:
        st.subheader("Channel Mix & Conversion")
        mix = (f.groupby('source', as_index=False)
                 [['leads','registrations','orders','spend']]
                 .sum()
                 .assign(reg_rate=lambda d: d['registrations']/d['leads'].replace(0,np.nan),
                         order_rate=lambda d: d['orders']/d['leads'].replace(0,np.nan)))
        # add CI
        mix = add_ci_rates(mix)
        fig_mix = px.bar(mix, x='source', y=['leads','registrations','orders'],
                         barmode='group', title="Volume by Source")
        fig_mix.update_layout(legend_title_text="")
        st.plotly_chart(fig_mix, use_container_width=True)

        # Conversion scatter with CI
        fig_conv = go.Figure()
        fig_conv.add_trace(go.Scatter(
            x=mix['source'], y=mix['reg_rate'], mode='markers+lines', name='Reg Rate',
            line=dict(color="#3D85C6"), marker=dict(size=9)
        ))
        fig_conv.add_trace(go.Scatter(
            x=mix['source'], y=mix['reg_ci_lo'], mode='lines', line=dict(width=0, color='rgba(0,0,0,0)'),
            showlegend=False
        ))
        fig_conv.add_trace(go.Scatter(
            x=mix['source'], y=mix['reg_ci_hi'], mode='lines', line=dict(width=0, color='rgba(0,0,0,0)'),
            fill='tonexty', fillcolor='rgba(61,133,198,0.2)', name='Reg CI'
        ))
        fig_conv.update_layout(title="Registration Rate by Source (with CI)", yaxis_tickformat=".1%")
        st.plotly_chart(fig_conv, use_container_width=True)

    st.subheader("Market × Source Matrix — Rates and CPL")
    pvt = (f.groupby(['market','source'], as_index=False)
             [['leads','registrations','orders','spend']]
             .sum())
    pvt['reg_rate'] = pvt['registrations']/pvt['leads'].replace(0,np.nan)
    pvt['order_rate'] = pvt['orders']/pvt['leads'].replace(0,np.nan)
    pvt['cpl'] = pvt['spend']/pvt['leads'].replace(0,np.nan)
    # Heatmap on reg rate
    fig_heat = px.density_heatmap(pvt, x='source', y='market', z='reg_rate',
                                  color_continuous_scale='Blues',
                                  title="Registration Rate Heatmap (Market × Source)")
    fig_heat.update_layout(yaxis={'categoryorder':'total ascending'}, coloraxis_colorbar={'title':'Reg Rate'})
    st.plotly_chart(fig_heat, use_container_width=True)

# ==================== TAB 2: DIAGNOSTICS =======================
with tab2:
    st.subheader("Anomaly / Outlier Detection (Campaign)")
    # choose a metric to flag
    metric = st.selectbox("Metric for outlier detection", ["reg_rate","order_rate","cpl"])
    # aggregate at campaign
    cg = (f.groupby('campaign', as_index=False)
            [['leads','registrations','orders','spend']]
            .sum())
    cg['reg_rate'] = cg['registrations']/cg['leads'].replace(0,np.nan)
    cg['order_rate'] = cg['orders']/cg['leads'].replace(0,np.nan)
    cg['cpl'] = cg['spend']/cg['leads'].replace(0,np.nan)
    cg['z'] = zscore(cg[metric].astype(float).replace([np.inf,-np.inf], np.nan), nan_policy='omit')
    cg['outlier'] = (np.abs(cg['z']) > 2.5)

    fig_sc = px.scatter(cg, x='leads', y=metric, color='outlier',
                        hover_data=['campaign','registrations','orders','spend'],
                        title=f"Campaign Scatter — {metric} vs Leads (outliers in red)")
    st.plotly_chart(fig_sc, use_container_width=True)

    st.markdown("**Flagged Outliers (|z| > 2.5):**")
    st.dataframe(cg[cg['outlier']].sort_values('z', ascending=False))

    st.subheader("Control Chart — Registration Rate over Time")
    ts = (f.groupby('date', as_index=False)[['leads','registrations']].sum())
    ts['reg_rate'] = ts['registrations']/ts['leads'].replace(0,np.nan)
    mu = ts['reg_rate'].mean()
    sd = ts['reg_rate'].std()
    ucl = mu + 3*sd
    lcl = mu - 3*sd
    fig_ctl = go.Figure()
    fig_ctl.add_trace(go.Scatter(x=ts['date'], y=ts['reg_rate'], mode='lines+markers', name='Reg rate', line=dict(color="#3D85C6")))
    fig_ctl.add_hline(y=mu, line_dash="dot", line_color="gray", annotation_text="Mean", annotation_position="top left")
    fig_ctl.add_hline(y=ucl, line_dash="dash", line_color="red", annotation_text="UCL(+3σ)")
    fig_ctl.add_hline(y=lcl, line_dash="dash", line_color="red", annotation_text="LCL(-3σ)")
    fig_ctl.update_layout(yaxis_tickformat=".1%")
    st.plotly_chart(fig_ctl, use_container_width=True)

    st.subheader("Distributions")
    colD1, colD2 = st.columns(2)
    with colD1:
        fig_cpl = px.histogram(f, x='cpl', nbins=50, title="CPL Distribution", color_discrete_sequence=["#6FA8DC"])
        st.plotly_chart(fig_cpl, use_container_width=True)
    with colD2:
        fig_rr = px.histogram(f, x='reg_rate', nbins=50, title="Registration Rate Distribution", color_discrete_sequence=["#3D85C6"])
        fig_rr.update_layout(xaxis_tickformat=".1%")
        st.plotly_chart(fig_rr, use_container_width=True)

# ====================== TAB 3: COHORTS =========================
with tab3:
    st.subheader("Lead Cohorts → Registration Rate")
    # Cohort by Lead Month and Source (or Market)
    cohort_dim = st.selectbox("Cohort dimension", ["source","market","segment"])
    f['lead_month'] = f['date'].dt.to_period('M').astype(str)
    c = (f.groupby(['lead_month', cohort_dim], as_index=False)
           [['leads','registrations']].sum())
    c['reg_rate'] = c['registrations']/c['leads'].replace(0,np.nan)
    fig_cohort = px.line(c, x='lead_month', y='reg_rate', color=cohort_dim, markers=True,
                         title=f"Registration Rate by Lead Cohort Month × {cohort_dim.title()}")
    fig_cohort.update_layout(xaxis_title="Lead Month", yaxis_tickformat=".1%")
    st.plotly_chart(fig_cohort, use_container_width=True)

# =================== TAB 4: DRIVERS (MODEL) ====================
with tab4:
    st.subheader("What drives Orders / Registrations? (OLS)")
    target = st.selectbox("Target variable", ["orders","registrations"])
    # Build a modelling table (monthly by campaign)
    Xdf = (f.groupby(['date','market','segment','source','campaign'], as_index=False)
             [['leads','registrations','opportunities','orders','spend','clicks','impressions']]
             .sum())
    # Simple feature set
    features = ['leads','registrations','opportunities','spend','clicks','impressions']
    # Avoid perfect leakage: if target=registrations, drop 'registrations' as predictor
    feat = [x for x in features if x != target]
    X = Xdf[feat].fillna(0).astype(float)
    y = Xdf[target].astype(float)

    # Add constant and fit
    Xc = sm.add_constant(X, has_constant='add')
    model = sm.OLS(y, Xc).fit()
    st.write(model.summary())

    # VIF for multicollinearity
    st.markdown("**Variance Inflation Factor (VIF)**")
    vif = pd.DataFrame({
        "feature": Xc.columns,
        "VIF": [variance_inflation_factor(Xc.values, i) for i in range(Xc.shape[1])]
    })
    st.dataframe(vif)

# ======================= TAB 5: FORECAST =======================
with tab5:
    st.subheader("Forecast (Holt‑Winters ETS)")
    series_opt = st.selectbox("Metric to forecast", ["orders","registrations","leads"])
    ts = (f.groupby('date', as_index=False)[[series_opt]].sum()).dropna()
    ts = ts.sort_values('date')
    if len(ts) >= 6:
        hw = ExponentialSmoothing(ts[series_opt], trend='add', seasonal=None, initialization_method='estimated')
        res = hw.fit()
        horizon = st.slider("Forecast months", 1, 6, 3)
        fcast = res.forecast(horizon)
        df_fc = pd.DataFrame({"date": pd.date_range(ts['date'].max()+pd.offsets.MonthBegin(), periods=horizon, freq='MS'),
                              "forecast": fcast.values})
        fig_fc = go.Figure()
        fig_fc.add_trace(go.Scatter(x=ts['date'], y=ts[series_opt], mode='lines+markers', name='Actual'))
        fig_fc.add_trace(go.Scatter(x=df_fc['date'], y=df_fc['forecast'], mode='lines+markers', name='Forecast'))
        fig_fc.update_layout(title=f"{series_opt.title()} — Actual vs Forecast")
        st.plotly_chart(fig_fc, use_container_width=True)
        st.write("Forecast values:", df_fc)
    else:
        st.info("Need at least 6 time points to forecast.")

# ======================= TAB 6: A/B TEST ======================
with tab6:
    st.subheader("A/B Significance Test (2‑Proportion Z‑test)")
    st.caption("Choose two groups and compare conversion rate: Registrations / Leads.")

    # group dimension
    dim = st.selectbox("Group by", ["source","campaign","market","segment"])
    grp = (f.groupby(dim, as_index=False)[['leads','registrations']].sum())
    choices = grp[dim].tolist()

    colA, colB = st.columns(2)
    with colA:
        A = st.selectbox("Group A", choices, index=0)
    with colB:
        B = st.selectbox("Group B", choices, index=min(1, len(choices)-1))

    a_row = grp[grp[dim]==A].iloc[0]
    b_row = grp[grp[dim]==B].iloc[0]
    count = np.array([a_row['registrations'], b_row['registrations']])
    nobs  = np.array([a_row['leads'],         b_row['leads']])
    if (nobs > 0).all():
        stat, pval = proportions_ztest(count, nobs, alternative='two-sided')
        st.write(f"**A/B Result** — z = {stat:.2f}, p = {pval:.4f}")
        st.write(f"{A} Reg‑Rate = {a_row['registrations']/max(1,a_row['leads']):.2%} | "
                 f"{B} Reg‑Rate = {b_row['registrations']/max(1,b_row['leads']):.2%}")
        if pval < 0.05:
            st.success("Difference is statistically significant at α=0.05.")
        else:
            st.info("No statistically significant difference at α=0.05.")
    else:
        st.warning("One of the groups has zero leads; cannot test.")
