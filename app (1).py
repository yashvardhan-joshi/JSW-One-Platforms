
import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from io import BytesIO

st.set_page_config(page_title="MSME Targets & Campaign Performance", layout="wide")

st.title("MSME – 3‑Month Target CPL & Campaign Performance (OGA / Repeat OGA)")
st.caption("Built for Yashvardhan Joshi – Option A flow (State × BU × Month Leads & Cost)")

# -----------------------------
# Helpers
# -----------------------------
@st.cache_data(show_spinner=False)
def read_tabular(file):
    name = file.name.lower()
    if name.endswith('.csv'):
        df = pd.read_csv(file)
    elif name.endswith('.xlsx') or name.endswith('.xls'):
        df = pd.read_excel(file, engine='openpyxl')
    else:
        raise ValueError("Please upload a CSV or XLSX file.")
    # Trim headers
    df.columns = [str(c).strip() for c in df.columns]
    return df

@st.cache_data(show_spinner=False)
def compute_targets(df_option_a, use_weighted=False):
    # Expect columns: State | Business Unit | Month (YYYY-MM or date) | Leads | Marketing Cost
    req = ['State', 'Business Unit', 'Month', 'Leads', 'Marketing Cost']
    missing = [c for c in req if c not in df_option_a.columns]
    if missing:
        raise ValueError(f"Missing required columns in Option A file: {missing}")

    df = df_option_a.copy()
    # Clean
    df['State'] = df['State'].astype(str).str.strip()
    df['Business Unit'] = df['Business Unit'].astype(str).str.strip()
    # Parse Month
    # Accept YYYY-MM, YYYY/MM, or full date; coerce to month period
    def to_period(x):
        x = str(x).strip()
        # Try common formats
        for fmt in ("%Y-%m", "%Y/%m", "%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%m/%d/%Y"):
            try:
                return pd.to_datetime(x, format=fmt).to_period('M')
            except Exception:
                pass
        # Fallback to pandas parser
        try:
            return pd.to_datetime(x, dayfirst=True).to_period('M')
        except Exception:
            return pd.NaT
    df['Month_Period'] = df['Month'].apply(to_period)
    df = df.dropna(subset=['Month_Period']).copy()

    # Numerics
    df['Leads'] = pd.to_numeric(df['Leads'], errors='coerce')
    df['Marketing Cost'] = pd.to_numeric(df['Marketing Cost'], errors='coerce')
    df = df.replace([np.inf, -np.inf], np.nan)

    # Compute monthly CPL
    df['CPL'] = df['Marketing Cost'] / df['Leads']

    # For each State × BU, take latest 3 distinct months present
    results = []
    for (state, bu), grp in df.groupby(['State', 'Business Unit']):
        grp = grp.dropna(subset=['CPL', 'Month_Period'])
        if grp.empty:
            continue
        # Order by month asc to slice last 3
        grp = grp.sort_values('Month_Period')
        # Take last 3 months present
        months = grp['Month_Period'].drop_duplicates().sort_values().to_list()
        last3 = months[-3:]
        grp3 = grp[grp['Month_Period'].isin(last3)].copy()
        if grp3.empty:
            continue
        if use_weighted:
            # Weighted by Leads
            w = grp3['Leads'].fillna(0)
            # Avoid divide-by-zero: if sum(w)==0, fallback to simple mean
            if w.sum() > 0:
                target = np.average(grp3['CPL'].fillna(0), weights=w)
            else:
                target = grp3['CPL'].mean()
        else:
            target = grp3['CPL'].mean()
        results.append({'State': state, 'Business Unit': bu, 'Target_CPL': round(float(target), 2), 'Months_Used': ', '.join([str(p) for p in last3])})

    targets = pd.DataFrame(results)
    return targets

@st.cache_data(show_spinner=False)
def aggregate_campaigns(df_enriched, start_date=None, end_date=None, states=None, bu=None):
    # Expect columns in enriched: Account SF Id, Created Date, Auto state, utm_source, utm_campaign, utm_medium,
    # Account Record Type, Business Unit, Registered, Opportunity Count, Success Opportunity Count, OGA_Flag, ROGA_Flag
    req = ['Account SF Id','Created Date','Auto state','Business Unit','utm_source','utm_campaign','utm_medium','Registered','OGA_Flag','ROGA_Flag']
    missing = [c for c in req if c not in df_enriched.columns]
    if missing:
        raise ValueError(f"Missing required columns in enriched file: {missing}")

    df = df_enriched.copy()
    # Parse dates
    df['Created Date Parsed'] = pd.to_datetime(df['Created Date'], errors='coerce', dayfirst=True)

    # Filters
    if start_date is not None:
        df = df[df['Created Date Parsed'] >= pd.to_datetime(start_date)]
    if end_date is not None:
        df = df[df['Created Date Parsed'] <= pd.to_datetime(end_date)]
    if states:
        df = df[df['Auto state'].astype(str).isin(states)]
    if bu:
        df = df[df['Business Unit'].astype(str).isin(bu)]

    # Ensure ints
    for c in ['Registered','OGA_Flag','ROGA_Flag']:
        df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0).astype(int)

    # Aggregate at campaign level
    group_cols = ['utm_source','utm_medium','utm_campaign','Auto state','Business Unit']
    agg = df.groupby(group_cols).agg(
        Accounts=('Account SF Id','nunique'),
        Registrations=('Registered','sum'),
        OGA_Accounts=('OGA_Flag','sum'),
        Repeat_OGA_Accounts=('ROGA_Flag','sum')
    ).reset_index()

    # Additional rates
    agg['Registration Rate'] = (agg['Registrations'] / agg['Accounts']).replace([np.inf, -np.inf], np.nan).round(3)
    agg['Repeat/OGA %'] = (agg['Repeat_OGA_Accounts'] / agg['OGA_Accounts']).replace([np.inf, -np.inf], np.nan).round(3)
    return agg

# -----------------------------
# Sidebar – Inputs
# -----------------------------
st.sidebar.header("Inputs")
st.sidebar.subheader("1) Monthly CPL Inputs (Option A)")
opt_a_file = st.sidebar.file_uploader("Upload State × Business Unit × Month × Leads × Marketing Cost (CSV/XLSX)", type=["csv","xlsx","xls"], key="opt_a")

st.sidebar.subheader("2) Enriched CRM Export")
enriched_file = st.sidebar.file_uploader("Upload MSME_Master_Enriched.csv", type=["csv"], key="enr")

use_weighted = st.sidebar.checkbox("Weighted by Leads (for target)", value=False)

st.sidebar.markdown("---")

st.sidebar.subheader("Filters for Campaign Aggregation")
start_date = st.sidebar.date_input("Start date", value=None)
end_date = st.sidebar.date_input("End date", value=None)

# Placeholder for dynamic filters after file load
state_filter = None
bu_filter = None

# -----------------------------
# Main – Targets
# -----------------------------
col1, col2 = st.columns([1.2,1])

with col1:
    st.header("Target CPL (Average of Latest 3 Months)")
    if opt_a_file is None:
        st.info("Upload the Option A file to compute targets. Use the template from the right panel.")
    else:
        df_opt_a = read_tabular(opt_a_file)
        try:
            targets = compute_targets(df_opt_a, use_weighted=use_weighted)
        except Exception as e:
            st.error(f"Error computing targets: {e}")
            targets = pd.DataFrame()

        if not targets.empty:
            st.success(f"Computed targets for {targets.shape[0]} State × BU pairs.")
            # Show chart
            top_states = targets.sort_values('Target_CPL', ascending=False).head(20)
            chart = alt.Chart(top_states).mark_bar().encode(
                x=alt.X('Target_CPL:Q', title='Target CPL'),
                y=alt.Y('State:N', sort='-x'),
                color='Business Unit:N',
                tooltip=['State','Business Unit','Target_CPL','Months_Used']
            ).properties(height=420)
            st.altair_chart(chart, use_container_width=True)

            st.dataframe(targets.sort_values(['Business Unit','State']).reset_index(drop=True))

            # Download
            csv = targets.to_csv(index=False).encode('utf-8')
            st.download_button("Download Target_CPL_Statewise.csv", data=csv, file_name="Target_CPL_Statewise.csv", mime="text/csv")
        else:
            st.warning("No targets computed. Check your columns and data.")

with col2:
    st.subheader("Template & Notes")
    st.write("**Option A expected columns**: `State`, `Business Unit`, `Month`, `Leads`, `Marketing Cost`.")
    st.write("`Month` can be `YYYY-MM` or any parsable date; only the month is used.")
    tmpl = pd.DataFrame({
        'State':['Maharashtra','Maharashtra','Maharashtra','Gujarat','Gujarat','Gujarat'],
        'Business Unit':['Manufacturing','Manufacturing','Manufacturing','Construct','Construct','Construct'],
        'Month':['2025-05','2025-06','2025-07','2025-05','2025-06','2025-07'],
        'Leads':[1200,1100,900,800,750,780],
        'Marketing Cost':[300000,275000,225000,120000,115000,117000]
    })
    st.dataframe(tmpl)
    csv_bytes = tmpl.to_csv(index=False).encode('utf-8')
    st.download_button("Download OptionA_Template.csv", data=csv_bytes, file_name="OptionA_Template.csv", mime="text/csv")

# -----------------------------
# Main – Campaign Aggregation
# -----------------------------
st.header("Campaign Performance (OGA / Repeat OGA / Registrations)")
if enriched_file is None:
    st.info("Upload MSME_Master_Enriched.csv to analyze campaign metrics.")
else:
    df_enr = read_tabular(enriched_file)

    # Dynamic state/BU filters
    states_all = sorted(df_enr['Auto state'].astype(str).dropna().unique().tolist()) if 'Auto state' in df_enr.columns else []
    bu_all = sorted(df_enr['Business Unit'].astype(str).dropna().unique().tolist()) if 'Business Unit' in df_enr.columns else []

    sel_states = st.multiselect("States", options=states_all, default=states_all[:10])
    sel_bu = st.multiselect("Business Unit", options=bu_all, default=bu_all)

    try:
        agg = aggregate_campaigns(df_enr, start_date=start_date if start_date else None, end_date=end_date if end_date else None, states=sel_states if sel_states else None, bu=sel_bu if sel_bu else None)
    except Exception as e:
        st.error(f"Error aggregating campaigns: {e}")
        agg = pd.DataFrame()

    if not agg.empty:
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Distinct Accounts", f"{int(agg['Accounts'].sum()):,}")
        k2.metric("Registrations", f"{int(agg['Registrations'].sum()):,}")
        k3.metric("OGA Accounts", f"{int(agg['OGA_Accounts'].sum()):,}")
        k4.metric("Repeat OGA Accounts", f"{int(agg['Repeat_OGA_Accounts'].sum()):,}")

        st.dataframe(agg.sort_values(['Repeat_OGA_Accounts','OGA_Accounts','Registrations','Accounts'], ascending=False).reset_index(drop=True))
        # Download
        csv2 = agg.to_csv(index=False).encode('utf-8')
        st.download_button("Download Campaign_Aggregation.csv", data=csv2, file_name="Campaign_Aggregation.csv", mime="text/csv")
    else:
        st.warning("No rows after filters. Try broadening the filters.")

st.divider()
st.caption("Notes: Target CPL uses the average of the latest 3 months present in the Option A file (per State × BU). If 'Weighted by Leads' is selected, months are weighted by their lead volumes.")
