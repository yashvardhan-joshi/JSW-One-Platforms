# consolidate.py
"""
Consolidate Google, Facebook and Salesforce MSME master into campaign_data_consolidated.csv

New logic:
- Leads = COUNT DISTINCT Salesforce 'Account SF Id'
- Registrations = SUM of Salesforce 'Registered' (1/0)
- Monthly grain (date -> first day of month)
- Media adds Impressions/Clicks/Spend; CRM adds Leads/Regs/Opps/Orders

Place your three files in ./data:
  - MSME_Google Data - Sheet2.csv
  - MSME_FB_Data.xlsx
  - MSME Master Data.csv

Run: python consolidate.py
"""
import pandas as pd, numpy as np, re
from pathlib import Path

DATA_DIR = Path('data')
OUT = Path('campaign_data_consolidated.csv')

STATE_MAP = {
    'MH':'Maharashtra','TN':'Tamil Nadu','KA':'Karnataka','GJ':'Gujarat','DL':'Delhi',
    'AP':'Andhra Pradesh','TL':'Telangana','AM':'All Markets','RJ':'Rajasthan','UP':'Uttar Pradesh',
    'WB':'West Bengal','HR':'Haryana','JK':'Jammu & Kashmir','OD':'Odisha'
}

def extract_state(name: str):
    if not isinstance(name, str): return None
    m = re.match(r'^([A-Z]{2})_', name)
    if m and m.group(1) in STATE_MAP: return STATE_MAP[m.group(1)]
    if name.startswith('Search-') or name.startswith('AM_'): return 'All Markets'
    return None

def month_start(s):
    s = str(s) if s is not None else ''
    if ' - ' in s: s = s.split(' - ')[0]
    d = pd.to_datetime(s, errors='coerce')
    return d.to_period('M').to_timestamp() if pd.notna(d) else pd.NaT

frames = []

# ---------- Google ----------
g_path = next(DATA_DIR.glob('MSME_Google Data*.csv'), None)
if g_path:
    g = pd.read_csv(g_path)
    g = g.rename(columns={
        'Campaign Name':'campaign','Advertising Channel':'segment',
        'Clicks':'clicks','Impressions':'impressions',
        'Cost (Spend)':'spend','Conversions':'conversions','Month':'month'
    })
    g['date'] = g['month'].apply(month_start)
    g['market'] = g['campaign'].apply(extract_state)
    g['source'] = 'Google'
    # media contributes only delivery metrics
    g['page_visits'] = 0.0
    g['signups'] = 0.0           # deprecated; will be replaced by leads in app
    g['registrations'] = 0.0     # CRM only
    g['opportunities'] = 0.0
    g['orders'] = 0.0
    g['target_cpl'] = 250.0
    frames.append(g[['date','market','segment','source','campaign','impressions','clicks','page_visits','signups','registrations','opportunities','orders','spend','target_cpl']])

# ---------- Facebook ----------
fb_path = next(DATA_DIR.glob('MSME_FB_Data*.xlsx'), None)
if fb_path:
    fb = pd.read_excel(fb_path, sheet_name=0, engine='openpyxl')
    fb = fb.rename(columns={
        'Campaign Name':'campaign','Impressions':'impressions','Link Clicks':'clicks',
        'Amount Spent':'spend','Results':'results','Month':'month'
    })
    for c in ['impressions','clicks','spend','results']:
        fb[c] = pd.to_numeric(fb[c], errors='coerce').fillna(0)
    fb['date'] = fb['month'].apply(month_start)
    fb['market'] = fb['campaign'].apply(extract_state)
    fb['source'] = 'Facebook'
    fb['segment'] = 'Paid Social'
    fb['page_visits'] = 0.0
    fb['signups'] = 0.0           # deprecated; will be replaced by leads in app
    fb['registrations'] = 0.0
    fb['opportunities'] = 0.0
    fb['orders'] = 0.0
    fb['target_cpl'] = 200.0
    frames.append(fb[['date','market','segment','source','campaign','impressions','clicks','page_visits','signups','registrations','opportunities','orders','spend','target_cpl']])

# ---------- Salesforce ----------
sf_path = next(DATA_DIR.glob('MSME Master Data*.csv'), None)
if sf_path:
    sf = None
    for enc in ['utf-8','latin1','ISO-8859-1']:
        try:
            sf = pd.read_csv(sf_path, encoding=enc)
            break
        except: continue
    if sf is not None:
        sf.columns = [c.strip() for c in sf.columns]
        # map headers (robust to variants)
        cmap = {}
        for c in sf.columns:
            lc = c.lower()
            if 'created date' in lc: cmap['created'] = c
            elif 'auto state' in lc: cmap['state'] = c
            elif 'utm_source' in lc: cmap['utm_source'] = c
            elif 'utm_campaign' in lc: cmap['utm_campaign'] = c
            elif 'account sf id' in lc or ('sf id' in lc and 'account' in lc): cmap['sfid'] = c
            elif 'account record type' in lc: cmap['rectype'] = c
            elif lc == 'registered' or ('registered' in lc and 'by' not in lc): cmap['registered'] = c
            elif 'opportunity count' in lc and 'success' not in lc: cmap['opps'] = c
            elif 'success opportunity count' in lc: cmap['orders'] = c

        # build CRM frame at row level
        crm = pd.DataFrame()
        crm['date'] = pd.to_datetime(sf[cmap.get('created')], errors='coerce', dayfirst=True).dt.to_period('M').dt.to_timestamp()
        def norm_state(x):
            if pd.isna(x): return None
            s = str(x).strip().upper()
            rev = {'GUJARAT':'Gujarat','GJ':'Gujarat','MAHARASHTRA':'Maharashtra','MH':'Maharashtra',
                   'KARNATAKA':'Karnataka','KA':'Karnataka','TAMIL NADU':'Tamil Nadu','TAMILNADU':'Tamil Nadu','TN':'Tamil Nadu',
                   'DELHI':'Delhi','DL':'Delhi','TELANGANA':'Telangana','TL':'Telangana','ANDHRA PRADESH':'Andhra Pradesh','AP':'Andhra Pradesh',
                   'UTTAR PRADESH':'Uttar Pradesh','UP':'Uttar Pradesh','RAJASTHAN':'Rajasthan','RJ':'Rajasthan','HARYANA':'Haryana','HR':'Haryana',
                   'ODISHA':'Odisha','ORISSA':'Odisha','OD':'Odisha'}
            return rev.get(s, s.title())
        crm['market'] = sf[cmap.get('state')].apply(norm_state) if cmap.get('state') else None
        crm['segment'] = sf[cmap.get('rectype')] if cmap.get('rectype') else 'CRM'
        # source & campaign from UTM
        def map_source(s):
            s = str(s).lower() if pd.notna(s) else ''
            if 'google' in s or s == 'gg': return 'Google'
            if 'meta-fb' in s or s == 'fb' or 'facebook' in s or 'meta' in s: return 'Facebook'
            if 'meta-ig' in s or 'ig' in s or 'instagram' in s: return 'Instagram'
            if 'moe' in s or 'moengage' in s: return 'MoEngage'
            return 'Direct'
        crm['source'] = sf[cmap.get('utm_source')].apply(map_source) if cmap.get('utm_source') else 'Direct'
        crm['campaign'] = sf[cmap.get('utm_campaign')] if cmap.get('utm_campaign') else 'CRM'

        # metrics from CRM:
        crm['sfid'] = sf[cmap.get('sfid')] if cmap.get('sfid') else np.nan
        crm['registered'] = pd.to_numeric(sf[cmap.get('registered')], errors='coerce').fillna(0) if cmap.get('registered') else 0
        crm['opportunities'] = pd.to_numeric(sf[cmap.get('opps')], errors='coerce').fillna(0) if cmap.get('opps') else 0
        crm['orders'] = pd.to_numeric(sf[cmap.get('orders')], errors='coerce').fillna(0) if cmap.get('orders') else 0

        # aggregate to grain with DISTINCT SFID for leads
        agg_crm = (crm
                   .groupby(['date','market','segment','source','campaign'], dropna=False)
                   .agg(leads=('sfid', lambda x: pd.Series(x).dropna().nunique()),
                        registrations=('registered','sum'),
                        opportunities=('opportunities','sum'),
                        orders=('orders','sum'))
                   .reset_index())

        # fill remaining numeric columns (delivery & spend = 0 for CRM)
        agg_crm['impressions'] = 0.0
        agg_crm['clicks'] = 0.0
        agg_crm['page_visits'] = 0.0
        agg_crm['signups'] = 0.0  # deprecated; app will use 'leads' column
        agg_crm['spend'] = 0.0
        def t_cpl(src):
            return 200.0 if src == 'Facebook' else 250.0 if src == 'Google' else 180.0 if src == 'MoEngage' else 0.0
        agg_crm['target_cpl'] = agg_crm['source'].apply(t_cpl)

        frames.append(agg_crm[['date','market','segment','source','campaign',
                               'impressions','clicks','page_visits','signups',
                               'registrations','opportunities','orders','spend','target_cpl','leads']])

# ---------- combine ----------
if not frames:
    raise SystemExit("No source files found in ./data. Place Google, Facebook and Salesforce files and rerun.")

combined = pd.concat(frames, ignore_index=True)
# ensure all numeric fields exist
for c in ['impressions','clicks','page_visits','signups','registrations','opportunities','orders','spend','target_cpl','leads']:
    if c not in combined.columns:
        combined[c] = 0
# handle markets
combined.loc[combined['market'].isna() & combined['campaign'].astype(str).str.startswith('AM_'), 'market'] = 'All Markets'
combined['segment'] = combined['segment'].fillna('—')
combined['date'] = pd.to_datetime(combined['date'], errors='coerce')

# sum by grain
agg = (combined
       .groupby(['date','market','segment','source','campaign'], as_index=False)
       .sum(numeric_only=True))

# final formatting
agg['date'] = agg['date'].dt.strftime('%Y-%m-%d')
# Save
agg.to_csv(OUT, index=False)
print("Wrote", OUT)
