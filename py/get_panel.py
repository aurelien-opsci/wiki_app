#!/usr/bin/env python3
# panel_politique_recursive.py

from __future__ import annotations
from typing import List, Tuple, Set
import requests
import pandas as pd
from datetime import datetime, timedelta
import argparse

API_ROOT = "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article"
UA = {"User-Agent": "PageviewSpike/1.3 (opsci)"}
WIKI_API = "https://fr.wikipedia.org/w/api.php"

def _date_fmt(date: str | datetime) -> str:
    if isinstance(date, datetime):
        return date.strftime("%Y%m%d")
    return date.replace("-", "")

def _fetch_series(title: str, start: str, end: str, lang: str) -> pd.Series:
    title_enc = requests.utils.quote(title.replace(" ", "_"), safe="")
    url = (
        f"{API_ROOT}/{lang}.wikipedia/all-access/user/"
        f"{title_enc}/daily/{_date_fmt(start)}/{_date_fmt(end)}"
    )
    try:
        r = requests.get(url, headers=UA, timeout=20)
        r.raise_for_status()
        items = r.json().get("items", [])
        data = {pd.to_datetime(i["timestamp"][:8], format="%Y%m%d"): i["views"] for i in items}
        return pd.Series(data, name=title)
    except Exception:
        return pd.Series(name=title)

def get_category_members_recursive(
    root_cat: str,
    max_depth: int = 3,
    lang: str = "fr"
) -> List[str]:
    """
    Récupère tous les titres d'articles (namespace 0) dans la catégorie root_cat
    et ses sous-catégories jusqu'à max_depth (0 = uniquement root).
    """
    visited_cats: Set[str] = set()
    pages: Set[str] = set()

    def recurse(cat: str, depth: int):
        if depth > max_depth or cat in visited_cats:
            return
        visited_cats.add(cat)

        params = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": f"Category:{cat}",
            "cmlimit": "500",
            "format": "json",
        }

        while True:
            resp = requests.get(WIKI_API, params=params)
            resp.raise_for_status()
            data = resp.json()

            for member in data["query"]["categorymembers"]:
                ns = member["ns"]
                title = member["title"]
                if ns == 0:
                    pages.add(title)
                elif ns == 14:  # sous-catégorie
                    subcat = title.split(":", 1)[1]
                    recurse(subcat, depth + 1)

            if "continue" in data:
                params.update(data["continue"])
            else:
                break

    recurse(root_cat, 0)
    return list(pages)

def compute_total_views(
    pages: List[str],
    start: str,
    end: str,
    lang: str
) -> List[Tuple[str, int]]:
    results: List[Tuple[str, int]] = []
    for title in pages:
        serie = _fetch_series(title, start, end, lang)
        total = int(serie.sum()) if not serie.empty else 0
        results.append((title, total))
    return results

def main():
    ap = argparse.ArgumentParser(
        description="Génère panel.csv des 100 pages les plus vues d'une catégorie et de ses sous-catégories"
    )
    ap.add_argument(
        "--days", type=int, default=5,
        help="Nombre de jours à considérer (défaut=5)"
    )
    ap.add_argument(
        "--lang", default="fr",
        help="Code langue Wikipedia (défaut=fr)"
    )
    ap.add_argument(
        "--category", default="Personnalité du secteur des médias",
        help="Nom de la catégorie sans préfixe 'Category:' (défaut=Personnalité du secteur des médias)"
    )
    ap.add_argument(
        "--depth", type=int, default=1,
        help="Profondeur de recherche dans les sous-catégories (défaut=1)"
    )
    ap.add_argument(
        "--output", default="panel.csv",
        help="Nom du fichier CSV de sortie (défaut=panel.csv)"
    )
    ns = ap.parse_args()

    today = datetime.utcnow().date()
    start = (today - timedelta(days=ns.days)).isoformat()
    end = today.isoformat()

    print(f"🔍 Exploration de la catégorie « {ns.category} » jusqu'à une profondeur de {ns.depth}…")
    pages = get_category_members_recursive(ns.category, ns.depth, ns.lang)
    print(f"→ {len(pages)} articles trouvés au total.")

    print(f"📊 Calcul des vues sur {ns.days} jours ({start} → {end})…")
    views = compute_total_views(pages, start, end, ns.lang)

    df = (
        pd.DataFrame(views, columns=["page", "TotalViews"])
        .sort_values("TotalViews", ascending=False)
        .head(100)
        .reset_index(drop=True)
    )

    # Ajout de la colonne 'panel'
    df["panel"] = ns.category
    
  
    df.to_csv(ns.output, index=False)
    print(f"✅ {ns.output} généré avec la colonne 'panel'.")

if __name__ == "__main__":
    main()


