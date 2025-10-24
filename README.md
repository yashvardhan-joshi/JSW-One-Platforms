# Campaign Analytics Dashboard — JSW One Platforms (MSME)

This repo hosts a Streamlit app for a shareable, online dashboard.

## Lead & Registration definitions
- **Leads** = Facebook *Results* + Google *Conversions*
- **Registrations** = Salesforce *Registered* (1/0), summed

## Files
- `app.py`: Streamlit app
- `campaign_data_consolidated.csv`: consolidated dataset (Month × Market × Segment × Source × Campaign)
- `requirements.txt`: dependencies

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy (Streamlit Cloud)
1. Push this repo to GitHub: `yashvardhan-joshi/JSW-One-Platforms`.
2. Go to https://share.streamlit.io → Deploy → select this repo → main file = `app.py`.
3. The app gets a public URL (e.g., `https://jsw-one-platforms.streamlit.app`).

## Updating data
Replace/commit a new `campaign_data_consolidated.csv` (same schema). The app will load the latest file.

---

### Data schema
```
date, market, segment, source, campaign,
impressions, clicks, page_visits, signups, registrations,
opportunities, orders, spend, target_cpl
```
