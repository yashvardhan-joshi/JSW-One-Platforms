# consolidate.py
"""
Consolidate Google, Facebook and Salesforce MSME master into campaign_data_consolidated.csv
Assumptions:
- Leads = FB Results + Google Conversions
- Registrations = Salesforce Registered (1/0) summed
- Monthly grain with date rolled to first day of month
Place source files in ./data and run: python consolidate.py
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

# Google
g_path = next(DATA_DIR.glob('MSME_Google Data*.csv'), None)
if g_path:
    g = pd.read_csv(g_path)
    g = g.rename(columns={'Campaign Name':'campaign','Advertising Channel':'channel','Clicks':'clicks','Impressions':'impressions','Cost (Spend)':'spend','Conversions':'conversions','Month':'month'})
    g['date'] = g['month'].apply(month_start)
    g['market'] = g['campaign'].apply(extract_state)
    g['source'] = 'Google'
    g['segment'] = g['channel']
    g['signups'] = pd.to_numeric(g['conversions'], errors='coerce').fillna(0)
    g['registrations'] = 0.0; g['opportunities'] = 0.0; g['orders'] = 0.0
    g['page_visits'] = 0.0; g['target_cpl'] = 250.0
    frames.append(g[['date','market','segment','source','campaign','impressions','clicks','page_visits','signups','registrations','opportunities','orders','spend','target_cpl']])

# Facebook
fb_path = next(DATA_DIR.glob('MSME_FB_Data*.xlsx'), None)
if fb_path:
    fb = pd.read_excel(fb_path, sheet_name=0, engine='openpyxl')
    fb = fb.rename(columns={'Campaign Name':'campaign','Impressions':'impressions','Link Clicks':'clicks','Amount Spent':'spend','Results':'results','Month':'month'})
    for c in ['impressions','clicks','spend','results']:
        fb[c] = pd.to_numeric(fb[c], errors='coerce').fillna(0)
    fb['date'] = fb['month'].apply(month_start)
    fb['market'] = fb['campaign'].apply(extract_state)
    fb['source'] = 'Facebook'; fb['segment'] = 'Paid Social'
    fb['signups'] = fb['results']
    fb['registrations'] = 0.0; fb['opportunities'] = 0.0; fb['orders'] = 0.0
    fb['page_visits'] = 0.0; fb['target_cpl'] = 200.0
    frames.append(fb[['date','market','segment','source','campaign','impressions','clicks','page_visits','signups','registrations','opportunities','orders','spend','target_cpl']])

# Salesforce
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
        cmap = {}
        for c in sf.columns:
            lc = c.lower()
            if 'created date' in lc: cmap['created']=c
            elif 'auto state' in lc: cmap['state']=c
            elif 'utm_source' in lc: cmap['utm_source']=c
            elif 'utm_campaign' in lc: cmap['utm_campaign']=c
            elif 'account record type' in lc: cmap['record_type']=c
            elif lc == 'registered' or ('registered' in lc and 'by' not in lc): cmap['registered']=c
            elif 'opportunity count' in lc and 'success' not in lc: cmap['opps']=c
            elif 'success opportunity count' in lc: cmap['orders']=c
        sf_use = pd.DataFrame()
        created = pd.to_datetime(sf.get(cmap.get('created')), errors='coerce', dayfirst=True)
        sf_use['date'] = created.dt.to_period('M').dt.to_timestamp()
        def norm_state(x):
            if pd.isna(x): return None
            s = str(x).strip().upper()
            rev = {
                'GUJARAT':'Gujarat','GJ':'Gujarat','MAHARASHTRA':'Maharashtra','MH':'Maharashtra',
                'KARNATAKA':'Karnataka','KA':'Karnataka','TAMIL NADU':'Tamil Nadu','TAMILNADU':'Tamil Nadu','TN':'Tamil Nadu',
                'DELHI':'Delhi','DL':'Delhi','TELANGANA':'Telangana','TL':'Telangana','ANDHRA PRADESH':'Andhra Pradesh','AP':'Andhra Pradesh',
                'UTTAR PRADESH':'Uttar Pradesh','UP':'Uttar Pradesh','RAJASTHAN':'Rajasthan','RJ':'Rajasthan','HARYANA':'Haryana','HR':'Haryana',
                'ODISHA':'Odisha','ORISSA':'Odisha','OD':'Odisha'
            }
            return rev.get(s, s.title())
        sf_use['market'] = sf.get(cmap.get('state')).apply(norm_state) if cmap.get('state') else None
        sf_use['segment'] = sf.get(cmap.get('record_type')) if cmap.get('record_type') else 'CRM'
        def map_source(s):
            s = str(s).lower() if pd.notna(s) else ''
            if 'google' in s or s=='gg': return 'Google'
            if 'meta-fb' in s or s=='fb' or 'facebook' in s or 'meta' in s: return 'Facebook'
            if 'meta-ig' in s or 'ig' in s or 'instagram' in s: return 'Instagram'
            if 'moe' in s or 'moengage' in s: return 'MoEngage'
            return 'Direct'
        sf_use['source'] = sf.get(cmap.get('utm_source')).apply(map_source) if cmap.get('utm_source') else 'Direct'
        sf_use['campaign'] = sf.get(cmap.get('utm_campaign')) if cmap.get('utm_campaign') else 'CRM'
        for src_col, dest in [(cmap.get('registered'),'registrations'), (cmap.get('opps'),'opportunities'), (cmap.get('orders'),'orders')]:
            if src_col:
                sf_use[dest] = pd.to_numeric(sf.get(src_col), errors='coerce').fillna(0)
            else:
                sf_use[dest] = 0
        sf_use['signups'] = 0.0
        sf_use['impressions'] = 0.0
        sf_use['clicks'] = 0.0
        sf_use['page_visits'] = 0.0
        sf_use['spend'] = 0.0
        def t_cpl(src):
            return 200.0 if src=='Facebook' else 250.0 if src=='Google' else 180.0 if src=='MoEngage' else 0.0
        sf_use['target_cpl'] = sf_use['source'].apply(t_cpl)
        frames.append(sf_use[['date','market','segment','source','campaign','impressions','clicks','page_visits','signups','registrations','opportunities','orders','spend','target_cpl']])

if not frames:
    raise SystemExit("No source files found in ./data. Place Google, Facebook and Salesforce files and rerun.")

combined = pd.concat(frames, ignore_index=True)
combined['date'] = pd.to_datetime(combined['date'], errors='coerce')
for c in ['impressions','clicks','page_visits','signups','registrations','opportunities','orders','spend','target_cpl']:
    combined[c] = pd.to_numeric(combined[c], errors='coerce').fillna(0)
combined.loc[combined['market'].isna() & combined['campaign'].astype(str).str.startswith('AM_'), 'market'] = 'All Markets'
combined['segment'] = combined['segment'].fillna('—')

agg = combined.groupby(['date','market','segment','source','campaign'], as_index=False).sum(numeric_only=True)
agg['date'] = agg['date'].dt.strftime('%Y-%m-%d')
agg.to_csv(OUT, index=False)
print('Wrote', OUT)
