# graph_2.py
import requests
import pandas as pd
import time
from datetime import datetime
from requests.utils import quote

# User-Agent pour l'API Wikimedia Edits
UA_EDITS = "EditTrendBot/1.0 (contact@example.com)"
session_ed = requests.Session()
session_ed.headers.update({"User-Agent": UA_EDITS, "Accept": "application/json"})

# Fonction d'appel API pour séries temporelles d'éditions
def pageedits_timeseries(site: str, page: str, start: str, end: str, editor_type: str = "user") -> pd.DataFrame:
    start_ts = datetime.strptime(start, "%Y-%m-%d").strftime("%Y%m%d")
    end_ts = datetime.strptime(end, "%Y-%m-%d").strftime("%Y%m%d")
    encoded = quote(page, safe='')
    url = (
        f"https://wikimedia.org/api/rest_v1/metrics/edits/per-page/"
        f"{site}/{encoded}/{editor_type}/daily/{start_ts}/{end_ts}"
    )
    r = session_ed.get(url, timeout=30)
    r.raise_for_status()
    items = r.json().get("items", [])
    if not items or not items[0].get("results"):
        return pd.DataFrame(columns=["date", "edits", "page"])
    results = items[0]["results"]
    key = "count" if "count" in results[0] else ("edits" if "edits" in results[0] else None)
    if key is None:
        raise KeyError(f"Clé 'count' ou 'edits' introuvable dans {results[0].keys()}")
    df = pd.DataFrame({
    "date": pd.to_datetime(
        [r["timestamp"] for r in results], 
        utc=True
    ),
    "edits": [r.get(key, 0) for r in results],
    "page":  page
})

    return df

# Concaténation pour plusieurs pages
def fetch_pageedits(site: str, pages: list[str], start: str, end: str, editor_type: str = "user") -> pd.DataFrame:
    dfs = []
    for p in pages:
        dfs.append(pageedits_timeseries(site, p, start, end, editor_type))
        time.sleep(0.1)
    return pd.concat(dfs, ignore_index=True)


