# blacklist_metric.py
"""
Calcule la part de références provenant d’un **domaine blacklisté**.

Fonction exposée
----------------
get_blacklist_share(pages, blacklist_csv="blacklist.csv", lang="fr") -> pd.Series

* `blacklist.csv` doit contenir **une colonne `domain`** (ex.: `breitbart.com`).
* Pour chaque page Wikipédia :
    1. Récupère le wikitext.
    2. Extrait toutes les URL dans les balises `<ref>`.
    3. Prend le nom de domaine (`urllib.parse.urlparse(url).hostname`).
    4. Ratio = domaines black‑listés / total domaines.
* Retourne un `Series` 0‑1 (`0` si pas de référence ou pas de domaine présent).
"""

from __future__ import annotations
import pandas as pd, re, requests, time, pathlib
from typing import List
from urllib.parse import urlparse

UA = {"User-Agent": "BlacklistMetric/1.1 (opsci)"}
URL_REGEX = re.compile(r"https?://[^\s<>\"]+")


def _load_blacklist(path: str | pathlib.Path) -> set[str]:
    p = pathlib.Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Blacklist introuvable : {p}")
    if p.suffix == ".csv":
        df = pd.read_csv(p)
        if "domain" in df.columns:
            return set(df["domain"].dropna().str.strip().str.lower())
        # fallback première colonne
        return set(df.iloc[:, 0].dropna().str.strip().str.lower())
    # txt une ligne par domaine
    return set(l.strip().lower() for l in p.read_text().splitlines() if l.strip())


def _wikitext(title: str, lang: str) -> str:
    api = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        "action": "query", "prop": "revisions", "rvprop": "content", "rvslots": "main",
        "titles": title, "format": "json", "formatversion": 2
    }
    r = requests.get(api, params=params, headers=UA, timeout=20)
    r.raise_for_status()
    pg = r.json()["query"]["pages"][0]
    return pg.get("revisions", [{}])[0].get("slots", {}).get("main", {}).get("content", "")


def get_blacklist_share(pages: List[str], blacklist_csv="blacklist.csv", lang="fr") -> pd.Series:
    bl_domains = _load_blacklist(blacklist_csv)
    ratios = {}
    for p in pages:
        text = _wikitext(p, lang)
        urls = URL_REGEX.findall(text)
        if not urls:
            ratios[p] = 0.0
        else:
            domains = [urlparse(u).hostname or "" for u in urls]
            bad = sum(1 for d in domains if any(bd in d for bd in bl_domains))
            ratios[p] = bad / len(domains)
        time.sleep(0.1)
    return pd.Series(ratios, name="blacklist_share")
# ───────────────────────────  CLI test ─────────────────────────
if __name__ == "__main__":
    import argparse, json
    ap = argparse.ArgumentParser(description="Ratio de références blacklistées par article")
    ap.add_argument("pages", nargs="+", help="Titres d’articles")
    ap.add_argument("--blacklist", default="blacklist.csv", help="Chemin vers blacklist.csv")
    ap.add_argument("--lang", default="fr", help="Code langue wiki")
    ap.add_argument("--json", action="store_true", help="Affiche le résultat en JSON")
    ns = ap.parse_args()

    res = get_blacklist_share(ns.pages, ns.blacklist, ns.lang)
    if ns.json:
        print(json.dumps(res.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(res.round(3).to_markdown())
