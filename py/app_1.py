# app_1_refactored.py – Streamlit v1.0 refactorisé (UI principale)

from __future__ import annotations
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional

from gaph_1 import fetch_pageviews
from graph_2 import fetch_pageedits
from wikipedia_scoring_pipeline import compute_scores

# ── 1. Styles & Fonts ───────────────────────────────────────────
def inject_styles():
    st.markdown(
        """
        <style>
          @import url('https://fonts.googleapis.com/css2?family=Inria+Sans:wght@400;700&display=swap');
          html, body, [class*="css"] {
            font-family: 'Inria Sans', sans-serif !important;
          }
          .stButton>button {
            background-color: #edff00 !important;
            color: #000000 !important;
            border: 1px solid #000000 !important;
          }
          .stButton>button:hover {
            background-color: #d4e800 !important;
          }
        </style>
        """, unsafe_allow_html=True
    )

# ── 2. Radar Builder ────────────────────────────────────────────
BASE_COLORS = ["#edff00", "#6dff00", "#9100ff", "#ff00ed", "#00ecff", "#e2e2e2"]
def build_radar(df: pd.DataFrame, sensitivity: pd.Series, title: str) -> go.Figure:
    categories = ["Heat", "Risk", "Quality (penalty)"]
    fig = go.Figure()
    for i, (idx, row) in enumerate(df.iterrows()):
        color = BASE_COLORS[i % len(BASE_COLORS)]
        q_pen = min(1, abs(row["quality"]))
        vals = [row["heat"], row["risk"], q_pen, row["heat"]]
        fig.add_trace(go.Scatterpolar(
            r=vals,
            theta=categories + [categories[0]],
            fill='toself',
            name=idx,
            line=dict(color=color, width=3),
            marker=dict(color=color, size=8),
            opacity=0.6 + 0.1*(i%3),
            hoverinfo='text',
            hovertext=(
                f"Heat: {row['heat']:.2f}<br>"
                f"Risk: {row['risk']:.2f}<br>"
                f"Quality: {row['quality']:.2f}"
            )
        ))
    for i, (idx, score) in enumerate(sensitivity.items()):
        fig.add_annotation(
            x=0, y=0.9 - i*0.1, xref="paper", yref="paper",
            text=f"{idx} – Sensitivity: {score:.2f}",
            showarrow=False,
            font=dict(family="Inria Sans", size=12, color="black"),
            bgcolor="rgba(255,255,255,0.6)",
            xanchor="left", yanchor="middle"
        )
    fig.update_layout(
        title=dict(text=title, font=dict(family="Inria Sans", color="black")),
        font=dict(family="Inria Sans", color="black"),
        paper_bgcolor='white', plot_bgcolor='white',
        margin=dict(l=150, r=50, t=80, b=80),
        polar=dict(
            radialaxis=dict(range=[0,1], dtick=0.2, gridcolor="lightgrey",
                            gridwidth=1, tickfont=dict(family="Inria Sans", color="black")),
            angularaxis=dict(rotation=90, direction="clockwise",
                              tickfont=dict(family="Inria Sans", color="black"))
        ),
        legend=dict(font=dict(family="Inria Sans", color="black"),
                    orientation="h", yanchor="bottom", y=-0.15,
                    xanchor="center", x=0.5)
    )
    return fig

# ── 3. Param Form (UI Principale) ─────────────────────────────────
def param_form() -> dict:
    with st.form("param_form"):
        pages_input = st.text_area(
            "Titres d'articles (séparés par des virgules)",
            value=""
        )
        pages = [p.strip() for p in pages_input.split(",") if p.strip()]

        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input(
                "Date de début", value=pd.to_datetime("2024-01-01")
            )
        with col2:
            end_date = st.date_input(
                "Date de fin", value=pd.to_datetime("2024-12-31")
            )

        site = st.text_input(
            "Wiki site (ex: fr.wikipedia)", value="fr.wikipedia"
        )

        graph_choice = st.selectbox(
            "Type de graphique",
            ["Évolution pages vues", "Évolution éditions", "Sensibilité (radar)"]
        )

        compare_mode: Optional[str] = None
        compare_sel: Optional[List[str]] = None
        if graph_choice == "Sensibilité (radar)":
            compare_mode = st.selectbox(
                "Mode d'affichage", ["Tous", "Comparer"]
            )
            if compare_mode == "Comparer":
                compare_sel = st.multiselect(
                    "Pages à comparer (max 3)", pages,
                    default=pages[:3], max_selections=3
                )

        submitted = st.form_submit_button("Afficher")
    return {
        "pages": pages,
        "start_date": start_date,
        "end_date": end_date,
        "site": site,
        "graph_choice": graph_choice,
        "compare_mode": compare_mode,
        "compare_sel": compare_sel,
        "submitted": submitted
    }

# ── 4. Mode Handlers ─────────────────────────────────────────────
def show_pageviews(params: dict):
    df = fetch_pageviews(
        params['site'], params['pages'],
        params['start_date'].isoformat(), params['end_date'].isoformat()
    )
    fig = px.line(
        df, x="date", y="views", color="page",
        title=f"Pageviews — {params['site']}"
    )
    st.plotly_chart(fig, use_container_width=True)

def show_pageedits(params: dict):
    df = fetch_pageedits(
        params['site'], params['pages'],
        params['start_date'].isoformat(), params['end_date'].isoformat()
    )
    fig = px.line(
        df, x="date", y="edits", color="page",
        title=f"Éditions — {params['site']}"
    )
    st.plotly_chart(fig, use_container_width=True)

def show_sensitivity(params: dict):
    scores, detail = compute_scores(
        params['pages'],
        params['start_date'].isoformat(),
        params['end_date'].isoformat(),
        lang=params['site'].split(".")[0]
    )
    st.subheader("Métriques brutes")
    st.dataframe(detail.round(3))

    final = pd.DataFrame({
        "heat": scores.heat,
        "quality": scores.quality,
        "risk": scores.risk,
        "sensitivity": scores.sensitivity
    }, index=params['pages']).round(3)

    st.subheader("Scores finaux")
    st.dataframe(final)

    if params['compare_mode'] == "Tous":
        for p in params['pages']:
            fig = build_radar(
                final.loc[[p]], scores.sensitivity[[p]], title=p
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        sel = params['compare_sel'] or params['pages'][:3]
        df_sel = final.loc[sel]
        fig = build_radar(
            df_sel, scores.sensitivity[sel],
            title="Comparaison: " + ", ".join(sel)
        )
        st.plotly_chart(fig, use_container_width=True)

# ── 5. Main App ──────────────────────────────────────────────────
def run_app1():
    inject_styles()
    
    st.markdown(
        "<h1 style='text-align:center;'>Analyse Wikipédia</h1>",
        unsafe_allow_html=True
    )

    params = param_form()
    if not params['submitted']:
        return

    if not params['pages']:
        st.error("Entrez au moins un titre d'article.")
        return
    if params['start_date'] > params['end_date']:
        st.error("La date de début doit être antérieure à la date de fin.")
        return
    if params['graph_choice'] == "Sensibilité (radar)" and \
       params['compare_mode'] == "Comparer" and not params['compare_sel']:
        st.error("Sélectionnez au moins une page pour la comparaison.")
        return

    choice = params['graph_choice']
    if choice == "Évolution pages vues":
        show_pageviews(params)
    elif choice == "Évolution éditions":
        show_pageedits(params)
    else:
        show_sensitivity(params)

if __name__ == "__main__":
    run_app1()
