# wikipedia_scoring_pipeline.py  – absolute v0.7 (scaling Heat linéaire, Quality log-inverse)
"""
Calcule Heat / Quality / Risk + score sensitivity par page,
avec :
  • Heat en scaling linéaire relatif (max dynamique)
  • Quality en scaling log-inverse
  • anon_edit amplifié ×ANON_EDIT_FACTOR capé à 1
"""

from __future__ import annotations
from typing import List, Dict, Tuple
from dataclasses import dataclass
import pandas as pd
import numpy as np
import re

# ───────────────────────────  Poids ────────────────────────────
HEAT_W = {
    "pageview_spike": 0.50,    # +50% poids sur le trafic
    "edit_spike":     0.20,    # 30% sur les pics d’édition
    "talk_intensity": 0.10,    # 10% sur la controverse
    "protection_level": 0.20   # 10% sur la protection
}

QUAL_W = {
    "citation_gap": -0.30,     # moins pénalisant qu’avant
    "readability":  -0.30,    # idem
    "blacklist_share": -20  # blacklist
}

RISK_W = {
    "anon_edit": 1.0           # unique métrica de risque
}

GLOB_W = {
    "heat":    0.50,           # 50% du score final
    "quality": -0.40,          # 20% pénalité qualité
    "risk":    0.10            # 30% du score final
}

ANON_EDIT_FACTOR = 2         # amplification contrôlée de anon_edit

@dataclass
class ScoringResult:
    heat: pd.Series
    quality: pd.Series
    risk: pd.Series
    sensitivity: pd.Series

def compute_scores(
    pages: List[str],
    start: str,
    end: str,
    lang: str = "fr"
) -> Tuple[ScoringResult, pd.DataFrame]:
    """
    Renvoie (ScoringResult, DataFrame des métriques brutes).
    """
    from pageviews   import get_pageview_spikes
    from edit        import get_edit_spikes
    from taille_talk import get_talk_activity
    from protection  import protection_rating
    from ref         import get_citation_gap
    from readability import get_readability_score
    from ano_edit    import get_anon_edit_share
    from blacklist_metric import get_blacklist_share


    # extract readability float
    def _readab(p: str) -> float:
        txt = get_readability_score([p], lang)
        m = re.search(r"([0-9]*\.?[0-9]+)", str(txt))
        return float(m.group(1)) if m else 0.0

    # 1. Collecte des métriques brutes
    raw: Dict[str, pd.Series] = {
        "pageview_spike":   get_pageview_spikes(pages, start, end, lang),
        "edit_spike":       get_edit_spikes(pages, start, end, lang),
        "talk_intensity":   get_talk_activity(pages),
        "protection_level": protection_rating(pages, lang)["Score"].astype(float),
        "citation_gap":     get_citation_gap(pages),
        "readability":      pd.Series({p: _readab(p) for p in pages}),
        "anon_edit":        get_anon_edit_share(pages, start, end, lang),
        "blacklist_share" : get_blacklist_share(pages, "/home/cytech/Documents/OPSCI/wiki_app/py/blacklist.csv", lang)

    }
    metrics = pd.DataFrame(raw).apply(pd.to_numeric, errors="coerce").fillna(0)
    """    
    # ── Normalisation des métriques ─────────────────────────────────────
    # On ramène chaque métrique sur une échelle [0,1] pour pouvoir les
    # combiner ensuite :
    #
    # 1) Métriques “positives” (pics d’activité) :
    #    pageview_spike, edit_spike, talk_intensity
    #    → valeur / valeur_max → 1 = pic max observé
    #
    # 2) Protection :
    #    protection_level (0–4) → /4 → 1 = totalement protégée
    #
    # 3) Métriques “négatives” (pénalités qualité) :
    #    citation_gap, readability
    #    → valeur / valeur_max → 1 = écart/soucis de lecture max observé
    #
    # 4) Risque d’édition anonyme :
    #    anon_edit → ×ANON_EDIT_FACTOR, puis cap à 1 → 1 = risque max
    #
    #    (on amplifie le risque d’édition anonyme pour qu’il ait un impact)
    #
    # ── Agrégation pondérée ───────────────────────────────────────────────
    # On combine ensuite :
    #   heat    = somme des métriques d’activité pondérées (HEAT_W)
    #   quality = somme des pénalités qualité pondérées (QUAL_W)
    #   risk    = somme du risque pondéré (RISK_W)
    #
    # Puis score global “sensitivity” :
    #   sensitivity = 0.50*heat − 0.40*quality + 0.10*risk
    #   → plus sensitivity est élevé, plus la page est “chaude”, de mauvaise
    #     qualité ou à risque.
    #     
    #
    # 3. Agrégation par pondération
    heat    = (metrics_norm[list(HEAT_W)]   * pd.Series(HEAT_W)).sum(axis=1)
    quality = (metrics_norm[list(QUAL_W)]   * pd.Series(QUAL_W)).sum(axis=1)
    risk    = (metrics_norm[list(RISK_W)]   * pd.Series(RISK_W)).sum(axis=1)

    sens_df = pd.concat([heat, quality, risk], axis=1)
    sens_df.columns = ["heat", "quality", "risk"]
    sensitivity = (sens_df * pd.Series(GLOB_W)).sum(axis=1)

        """
    
    # ── Normalisation Quality corrigée ────────────────────────────

    pos_metrics = ["pageview_spike", "edit_spike", "talk_intensity"]
    neg_metrics = ["citation_gap", "readability", "blacklist_share"]

    max_vals = metrics[[*pos_metrics, *neg_metrics]].max()
    eps = 1e-9
    metrics_norm = pd.DataFrame(index=metrics.index)

# dans la boucle de normalisation, remplacez la partie "elif m in neg_metrics" par : 

    for m in metrics.columns:
        if m in pos_metrics:
        # Heat (linéaire relatif)
            metrics_norm[m] = metrics[m] / (max_vals[m] + eps)
    
        elif m == "protection_level":
            metrics_norm[m] = metrics[m] / 4

        elif m == "citation_gap":
        # DIRECT : plus de gap → plus de pénalité
            metrics_norm[m] = metrics[m] / (max_vals[m] + eps)

        elif m == "readability":
        # DIRECT : plus c’est difficile (raw élevé) → plus de pénalité
            metrics_norm[m] = metrics[m] / (max_vals[m] + eps)

        elif m == "anon_edit":
        # amplification contrôlée car unique metrique de risque
            metrics_norm[m] = metrics[m].apply(lambda x: min(1, x * ANON_EDIT_FACTOR))

        else:
            metrics_norm[m] = metrics[m]


    # 3. Agrégation par pondération
    heat    = (metrics_norm[list(HEAT_W)] * pd.Series(HEAT_W)).sum(axis=1)
    quality = (metrics_norm[list(QUAL_W)] * pd.Series(QUAL_W)).sum(axis=1)
    risk    = (metrics_norm[list(RISK_W)] * pd.Series(RISK_W)).sum(axis=1)

    sens_df = pd.concat([heat, quality, risk], axis=1)
    sens_df.columns = ["heat", "quality", "risk"]
    sensitivity = (sens_df * pd.Series(GLOB_W)).sum(axis=1)

    return ScoringResult(heat, quality, risk, sensitivity), metrics

# CLI pour tests
if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("pages", nargs="+")
    ap.add_argument("--start", default="2025-04-21")
    ap.add_argument("--end",   default="2025-05-21")
    ap.add_argument("--lang",  default="fr")
    ns = ap.parse_args()

    scores, detail = compute_scores(ns.pages, ns.start, ns.end, ns.lang)
    print("\n### Métriques brutes\n", detail.round(3).to_markdown())
    final = pd.DataFrame({
        "heat":       scores.heat.round(3),
        "quality":    scores.quality.round(3),
        "risk":       scores.risk.round(3),
        "sensitivity": scores.sensitivity.round(3)
    }, index=ns.pages)
    print("\n### Scores finaux\n", final.to_markdown())
