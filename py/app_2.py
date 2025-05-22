# app_panels.py – Streamlit v1.3 refactorisé

from __future__ import annotations
import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
from datetime import datetime, timedelta
import plotly.graph_objects as go
import io

from wikipedia_scoring_pipeline import compute_scores, HEAT_W
from gaph_1 import fetch_pageviews
from graph_2 import fetch_pageedits

# ── Radar builder ──────────────────────────────────────────────
BASE_COLORS = ["#edff00", "#6dff00", "#9100ff", "#ff00ed", "#00ecff", "#e2e2e2"]
def build_radar(df: pd.DataFrame, sensitivity: pd.Series, title: str) -> go.Figure:
    categories = ["Heat", "Risk", "Quality (penalty)"]
    fig = go.Figure()
    for i, (idx, row) in enumerate(df.iterrows()):
        color = BASE_COLORS[i % len(BASE_COLORS)]
        q_pen = min(1, abs(row["quality"]))
        vals = [row["heat"], row["risk"], q_pen, row["heat"]]
        fig.add_trace(go.Scatterpolar(
            r=vals, theta=categories + [categories[0]], fill='toself',
            name=idx, line=dict(color=color, width=3),
            marker=dict(color=color, size=8), opacity=0.6 + 0.1*(i%3),
            hoverinfo='text',
            hovertext=(f"Heat: {row['heat']:.2f}<br>"
                       f"Risk: {row['risk']:.2f}<br>"
                       f"Quality: {row['quality']:.2f}")
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

# ── Data loading ────────────────────────────────────────────────
def load_panels(path: Path) -> pd.DataFrame:
    if not path.exists():
        st.error(f"`{path}` introuvable – créez un CSV avec colonnes 'panel,page'.")
        st.stop()
    return pd.read_csv(path)

def load_blacklist(path: Path) -> pd.DataFrame:
    if not path.exists():
        pd.DataFrame(columns=["domain"]).to_csv(path, index=False)
    return pd.read_csv(path)

# ── Sidebar inputs ─────────────────────────────────────────────
def sidebar_inputs(
    df_panels: pd.DataFrame,
    panel_csv: Path,
    blacklist_csv: Path
) -> tuple[str, datetime, datetime, str, str, list[str]]:
    panels = sorted(df_panels["panel"].unique())
    
    

    panel_sel = st.sidebar.selectbox("Panel", panels)
    start = st.sidebar.date_input("Date début",
        value=datetime.utcnow().date() - timedelta(days=30))
    end = st.sidebar.date_input("Date fin",
        value=datetime.utcnow().date())
    if start > end:
        st.sidebar.error("⛔ Date début > date fin.")
        st.stop()

    lang = st.sidebar.text_input("Langue wiki", value="fr")
    mode = st.sidebar.radio("Mode", ["Panel complet", "Sensibilité", "Évolution vues"])

    st.sidebar.markdown("---")
    st.sidebar.markdown("**Blacklist**")
    new_dom = st.sidebar.text_input("Ajouter domaine", placeholder="exemple.com")
    if st.sidebar.button("Ajouter"):
        df_bl = load_blacklist(blacklist_csv)
        dom = new_dom.strip().lower()
        if dom and dom not in df_bl["domain"].str.lower().tolist():
            df_bl = pd.concat([df_bl, pd.DataFrame([{"domain": dom}])], ignore_index=True)
            df_bl.to_csv(blacklist_csv, index=False)
            st.sidebar.success(f"Domaine '{dom}' ajouté.")
        else:
            st.sidebar.warning("Domaine invalide ou existant.")

    pages = df_panels.loc[df_panels["panel"] == panel_sel, "page"].tolist()
    return panel_sel, start, end, lang, mode, pages

# ── Mode handlers ──────────────────────────────────────────────
def show_panel_complete(pages: list[str], max_items: int = None):
    st.subheader("Liste complète des pages")
    df = pd.DataFrame({"page": pages})
    st.dataframe(df.head(max_items) if max_items else df)
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    st.download_button("Télécharger CSV", buf.getvalue(),
                       file_name="py/panel.csv", mime="text/csv")

def show_sensitivity(pages: list[str], start: str, end: str, lang: str, max_items: int = 10):
    # pré-classement Heat
    from pageviews import get_pageview_spikes
    from edit import get_edit_spikes
    from taille_talk import get_talk_activity
    from protection import protection_rating

    with st.spinner("Pré-classement Heat…"):
        heat_raw = pd.DataFrame({
            "pageview_spike": get_pageview_spikes(pages, start, end, lang),
            "edit_spike":      get_edit_spikes(pages, start, end, lang),
            "talk_intensity":  get_talk_activity(pages),
            "protection_level":protection_rating(pages, lang)["Score"].astype(float)
        })
        heat_norm = heat_raw.divide(heat_raw.max().replace(0,1))
        heat_score = (heat_norm * pd.Series(HEAT_W)).sum(axis=1)

    top = heat_score.nlargest(max_items).index.tolist()
    with st.spinner("Compute_scores TOP…"):
        scores, detail = compute_scores(top, start, end, lang)

    # override heat
    detail["heat"] = heat_score[top].values
    scores.heat[:] = heat_score[top].values

    st.subheader("Métriques brutes")
    st.dataframe(detail.round(3))
    final = pd.DataFrame({
        "heat":        scores.heat,
        "quality":     scores.quality,
        "risk":        scores.risk,
        "sensitivity": scores.sensitivity
    }).round(3)

    st.subheader("Scores TOP")
    st.dataframe(final)
    st.subheader("Radar comparatif")
    radar_df = final.rename(columns={"sensitivity":"global"})
    st.plotly_chart(build_radar(radar_df, scores.sensitivity, title="Radar TOP"), use_container_width=True)

    st.subheader("Focus page")
    focus = st.selectbox("Page", top)
    c1, c2 = st.columns(2)
    dfv = fetch_pageviews(f"{lang}.wikipedia.org", [focus], start, end)
    dfe = fetch_pageedits(f"{lang}.wikipedia.org", [focus], start, end)
    with c1:
        st.plotly_chart(px.line(dfv, x="date", y="views", title=f"Vues – {focus}"), use_container_width=True)
    with c2:
        st.plotly_chart(px.line(dfe, x="date", y="edits", title=f"Éditions – {focus}"), use_container_width=True)

def show_evolution(pages: list[str], start: str, end: str, lang: str, max_items: int = 10):
    with st.spinner("Chargement vues…"):
        df_all = fetch_pageviews(f"{lang}.wikipedia.org", pages, start, end)
    grp = next((c for c in ("article","page","title") if c in df_all.columns), None)
    if grp is None:
        st.error("Colonne article manquante")
        return
    top = df_all.groupby(grp)["views"].sum().nlargest(max_items).index.tolist()
    df_top = df_all[df_all[grp].isin(top)]
    st.subheader("Évolution des vues – TOP")
    st.plotly_chart(px.line(df_top, x="date", y="views", color=grp), use_container_width=True)

# ── Main app ───────────────────────────────────────────────────
def run_app2():
    
    # bouton CSS override…
    st.markdown("""<style>
      .stButton>button{background:#edff00!important;color:#000!important;border:1px solid #000!important;}
      .stButton>button:hover{background:#d4e800!important;}
    </style>""", unsafe_allow_html=True)

    panel_sel, start_dt, end_dt, lang, mode, pages = sidebar_inputs(
        df_panels=load_panels(Path("panel.csv")),
        panel_csv=Path("py/panel.csv"),
        blacklist_csv=Path("py/blacklist.csv")
    )

    st.title(f"Panel « {panel_sel} » – {mode}")
    start, end = start_dt.isoformat(), end_dt.isoformat()

    if mode == "Panel complet":
        show_panel_complete(pages)
    elif mode == "Sensibilité":
        show_sensitivity(pages, start, end, lang)
    else:
        show_evolution(pages, start, end, lang)

if __name__ == "__main__":
    run_app2()
