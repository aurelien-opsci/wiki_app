# graph_1.py
import requests
import pandas as pd
from datetime import datetime
import time

# User-Agent pour l'API Wikimedia
UA = "PageviewsDemo/1.0 (https://github.com/aureliusLF; alefichoux@gmail.com)"
session = requests.Session()
session.headers.update({"User-Agent": UA})

# Fonction d'appel API pour time series de pageviews
def pageviews_timeseries(site: str, page: str, start: str, end: str) -> pd.DataFrame:
    start_ts = datetime.strptime(start, "%Y-%m-%d").strftime("%Y%m%d00")
    end_ts = datetime.strptime(end, "%Y-%m-%d").strftime("%Y%m%d00")
    url = (
        f"https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
        f"{site}/all-access/user/{page}/daily/{start_ts}/{end_ts}"
    )
    r = session.get(url, timeout=30)
    r.raise_for_status()
    items = r.json().get("items", [])
    df = pd.DataFrame({
        "date": pd.to_datetime([it["timestamp"] for it in items], format="%Y%m%d00"),
        "views": [it["views"] for it in items],
        "page": page
    })
    return df

# Fonction pour plusieurs pages
def fetch_pageviews(site: str, pages: list[str], start: str, end: str) -> pd.DataFrame:
    dfs = []
    for p in pages:
        dfs.append(pageviews_timeseries(site, p, start, end))
        time.sleep(0.1)
    return pd.concat(dfs, ignore_index=True)
