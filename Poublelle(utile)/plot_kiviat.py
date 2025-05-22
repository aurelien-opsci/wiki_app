# plot_kiviat.py – v1.1 (visual refresh)
"""
Trace un diagramme de Kiviat (radar) plus lisible et interactif :
  • Couleurs distinctes et translucides par page
  • Contours plus épais + marqueurs sur chaque sommet
  • Axe radial en traits pointillés et étiquette « Score 0‑1 »
  • Annotation textuelle du score de sensibilité à gauche

Usage (inchangé)  :
python plot_kiviat.py --start 2024-01-01 --end 2024-12-31 --lang fr \
                      "Vladimir Poutine" "Marine Le Pen"

Sortie : kiviat_prompt.html (ouvre auto).
"""

from __future__ import annotations
import argparse, pathlib, webbrowser, random
import plotly.graph_objects as go
import pandas as pd
from wikipedia_scoring_pipeline import compute_scores

BASE_COLORS = ["#EF553B", "#636EFA", "#00CC96", "#AB63FA", "#FFA15A", "#19D3F3"]

def build_radar(df: pd.DataFrame, sensitivity_scores: pd.Series) -> go.Figure:
    categories = ["Heat", "Risk", "Quality (penalty)"]
    fig = go.Figure()

    # traces radar (inchangé)
    for i, (idx, row) in enumerate(df.iterrows()):
        color = BASE_COLORS[i % len(BASE_COLORS)]
        q_pen = min(1, abs(row["quality"]))
        r_vals = [row["heat"], row["risk"], q_pen, row["heat"]]
        fig.add_trace(go.Scatterpolar(
            r=r_vals,
            theta=categories + [categories[0]],
            fill='toself',
            name=idx,
            line=dict(color=color, width=3),
            marker=dict(color=color, size=8),
            opacity=0.6 + 0.1*(i%3),
            hoverinfo='text',
            hovertext=f"Heat: {row['heat']:.2f}<br>Risk: {row['risk']:.2f}<br>Quality: {row['quality']:.2f}"
        ))

    # annotations de sensibilité
    for i, (idx, score) in enumerate(sensitivity_scores.items()):
        fig.add_annotation(
            x=0,  y=0.9 - i*0.1,   # x=0 pour être juste sur la marge gauche
            xref="paper", yref="paper",
            text=f"{idx} Sensitivity : {score:.2f}",
            showarrow=False,
            font=dict(size=12, color=BASE_COLORS[i % len(BASE_COLORS)]),
            bgcolor="rgba(255,255,255,0.6)",
            xanchor="left", yanchor="middle",
            opacity=0.8
        )

    # mise en page avec marge élargie
    fig.update_layout(
        margin=dict(l=150, r=50, t=80, b=80),
        polar=dict(
            radialaxis=dict(range=[0, 1], showticklabels=True, dtick=0.2,
                            gridcolor="lightgrey", gridwidth=1, tickfont=dict(size=12)),
            angularaxis=dict(rotation=90, direction="clockwise")
        ),
        template="plotly_white",
        title="Diagramme de Kiviat – Scores Heat / Risk / Quality",
        legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5)
    )
    return fig


def main():
    ap = argparse.ArgumentParser(description="Radar chart des scores Wikipédia PROMPT")
    ap.add_argument("pages", nargs="+", help="Titres d’articles", default=["Vladimir Poutine"])
    ap.add_argument("--start", default="2024-01-01")
    ap.add_argument("--end", default="2024-12-31")
    ap.add_argument("--lang", default="fr")
    ap.add_argument("--outfile", default="kiviat_prompt.html")
    ns = ap.parse_args()

    scores, _ = compute_scores(ns.pages, ns.start, ns.end, ns.lang)
    df = pd.DataFrame({
        "heat": scores.heat.clip(0, 1),
        "quality": scores.quality.clip(-1, 0),
        "risk": scores.risk.clip(0, 1),
    }, index=ns.pages)

    sensitivity_scores = scores.sensitivity

    fig = build_radar(df, sensitivity_scores)
    outfile = pathlib.Path(ns.outfile).with_suffix(".html").resolve()
    fig.write_html(outfile, include_plotlyjs="cdn")
    print(f"Diagramme de Kiviat enregistré dans {outfile}")
    webbrowser.open(outfile.as_uri())

if __name__ == "__main__":
    main()


