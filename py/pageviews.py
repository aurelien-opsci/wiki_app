"""
# pageviews.py
# spike : mesure de l’ampleur du pic de trafic par rapport à la valeur « habituelle »
#   = (nombre de vues maximal − trafic médian) / (trafic médian + 1)
# Interprétation du résultat :
#   • spike = 0      → pas de pic : le trafic maximal est égal à la médiane (courbe plate).  
#   • 0 < spike < 1  → pic modéré : le jour de pic a jusqu’à +100 % de vues en plus  
#                       que la journée « habituelle ».  
#   • spike = 1      → le pic représente un doublement du trafic par rapport à la médiane.  
#   • spike > 1      → pic très fort : par ex. spike = 2 signifie +200 % de vues (3× la  
#                       médiane), etc.  
# Plus le score est élevé, plus l’écart entre le jour de pic et le trafic « normal »  
# est important.

spike = (mx - med) / (med + 1)
"""
from __future__ import annotations
from typing import List, Dict
import pandas as pd
import requests
from datetime import datetime, timedelta
import argparse

API_ROOT = "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article"
UA = {"User-Agent": "PageviewSpike/1.3 (opsci)"}

# ─────────────────────────── helpers ────────────────────────────

def _date_fmt(date: str | datetime) -> str:
    """YYYYMMDD pour l’API REST."""
    if isinstance(date, datetime):
        return date.strftime("%Y%m%d")
    return date.replace("-", "")


def _fetch_series(title: str, start: str, end: str, lang: str) -> pd.Series:
    """Série quotidienne de pages vues (index : datetime, valeur : int)."""
    title_enc = requests.utils.quote(title.replace(" ", "_"), safe="")
    url = (
        f"{API_ROOT}/{lang}.wikipedia/all-access/user/"
        f"{title_enc}/daily/{_date_fmt(start)}/{_date_fmt(end)}"
    )
    try:
        r = requests.get(url, headers=UA, timeout=20)
        r.raise_for_status()
        items = r.json().get("items", [])
        data = {pd.to_datetime(i["timestamp"][:8]): i["views"] for i in items}
        return pd.Series(data, name=title).sort_index()
    except Exception:
        return pd.Series(name=title)

# ─────────────────────────── API publiques ─────────────────────

def get_pageviews_timeseries(pages: List[str], start: str, end: str, lang: str = "en") -> Dict[str, pd.Series]:
    """Renvoie un dict {title: Series} pour debug ou graphiques."""
    return {p: _fetch_series(p, start, end, lang) for p in pages}


def get_pageview_spikes(pages: List[str], start: str, end: str, lang: str = "en") -> pd.Series:
    """Score "spike" seul (float)."""
    return get_pageview_spike_detail(pages, start, end, lang)["spike"]


def get_pageview_spike_detail(
    pages: List[str], start: str, end: str, lang: str = "en"
) -> pd.DataFrame:
    """DataFrame `[spike, peak_day, peak_views]` par article."""
    rows: Dict[str, Dict[str, object]] = {}
    for title, serie in get_pageviews_timeseries(pages, start, end, lang).items():
        if serie.empty:
            rows[title] = {"spike": 0.0, "peak_day": None, "peak_views": 0}
            continue

        med = serie.median()            # trafic médian (filtre les outliers)
        mx  = serie.max()               # trafic maximum (jour du pic)
        spike = (mx - med) / (med + 1)  # normalisation (voir docstring)
        peak_day = serie.idxmax().date().isoformat()

        rows[title] = {
            "spike": round(spike, 4),
            "peak_day": peak_day,
            "peak_views": int(mx),}

    return pd.DataFrame.from_dict(rows, orient="index")

# ───────────────────────────  CLI ──────────────────────────────
if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Spike score + date + vues max des pages Wikipédia.")
    ap.add_argument("pages", nargs="+", help="Titres d’articles")
    ap.add_argument("--start", help="YYYY-MM-DD (défaut = aujourd’hui -30j)")
    ap.add_argument("--end",   help="YYYY-MM-DD (défaut = aujourd’hui)")
    ap.add_argument("--lang",  default="en", help="Code langue (en, fr, …)")
    ns = ap.parse_args()

    today = datetime.utcnow().date()
    end   = ns.end or today.isoformat()
    start = ns.start or (today - timedelta(days=30)).isoformat()

    df = get_pageview_spike_detail(ns.pages, start, end, ns.lang)
    print(df.to_markdown())