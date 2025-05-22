#!/usr/bin/env python3
import streamlit as st
from pathlib import Path
from datetime import datetime
import streamlit.components.v1 as components

# Vos deux apps factorisées
from app_1 import run_app1 as micro_explorer
from app_2 import run_app2 as macro_explorer

# ── 1. set_page_config must be first ────────────────────────────
st.set_page_config(page_title="Dashboard OPSCI", layout="wide")

# Initialisation de l'état de la page.
# Mettre à None pour qu'aucune page ne soit sélectionnée par défaut.
if "page" not in st.session_state:
    st.session_state.page = None

# ── 2. CSS global pour le style ─────────────────────────────────
def inject_styles():
    # ── 2. CSS global pour le style ─────────────────────────────────
  st.markdown("""
<style>
  /* Fond et typo */
  body {
    background-color: #0e1117;
  }
  .main {
    color: #ffffff;
    font-family: 'Inria Sans', sans-serif;
  }
  /* Header */
  .header {
    text-align: center;
    padding: 2rem 0;
  }
  .header img {
    width: 200px;
    margin-bottom: 1rem;
  }

  /* Styles pour les boutons de navigation principaux */
  div[data-testid="stHorizontalBlock"] button[data-testid="stButton"] {
    background-color: #edff00; /* NOUVEAU: Couleur de fond de base jaune */
    color: #000 !important;   /* NOUVEAU: Texte noir pour contraste sur fond jaune */
    border: none;
    padding: 0.5rem 1.5rem;
    margin: 0 0.5rem;
    border-radius: 0.5rem;
    cursor: pointer;
    width: 100%;
    text-align: center;
    transition: background-color 0.3s ease, color 0.3s ease; /* Transition pour fond et couleur texte */
  }

  div[data-testid="stHorizontalBlock"] button[data-testid="stButton"]:hover {
    background-color: #d2d800; /* NOUVEAU: Jaune légèrement plus foncé pour le survol */
    color: #000 !important;   /* Texte noir au survol */
  }

  button[data-testid="stButton"].nav-selected {
    background-color: #1f77b4 !important; /* NOUVEAU: Bleu pour le bouton sélectionné */
    color: white !important;               /* Texte blanc sur fond bleu pour sélection */
    font-weight: bold;
  }

  /* Conteneur central */
  .content {
    max-width: 1200px;
    margin: auto;
    padding: 1rem;
    background-color: #11141a;
    border-radius: 1rem;
  }
</style>
""", unsafe_allow_html=True)

# ── 3. Header / Logo / Title ─────────────────────────────────────
st.markdown('<div class="header main">', unsafe_allow_html=True)
st.image("py/opscilogo.png", width=300)
st.markdown("<h1>OPS​CI Dashboard</h1>", unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# ── 4. Menu de navigation horizontal ─────────────────────────────
# Utilisation de la disposition centrée [3, 2, 2, 3]
cols = st.columns([5, 2, 2, 4])

with cols[1]:
    # Les clés des boutons sont "micro" et "macro"
    if st.button("Micro Explorer", key="micro"):
        st.session_state.page = "micro"
        st.rerun() # st.rerun() force un rafraîchissement immédiat pour refléter le changement d'état.
with cols[2]:
    if st.button("Macro Explorer", key="macro"):
        st.session_state.page = "macro"
        st.rerun()

# Marquer le bouton sélectionné via JavaScript
# S'exécute seulement si une page ("micro" ou "macro") est sélectionnée
if st.session_state.page in ["micro", "macro"]:
    key_of_selected_button = st.session_state.page # Sera "micro" ou "macro"

    components.html(f"""
    <script>
      // Attend que le DOM soit chargé pour être sûr que les boutons existent.
      // (Souvent géré par Streamlit, mais c'est une bonne pratique)
      (function() {{
        // Tente de trouver le bouton avec l'attribut 'k' correspondant exactement à la clé.
        // C'est ainsi que votre script original semblait fonctionner.
        const targetButtons = document.querySelectorAll('button[k="{key_of_selected_button}"]');
        if (targetButtons.length > 0) {{
          targetButtons[0].classList.add('nav-selected');
        }} else {{
          // Si la correspondance directe échoue, Streamlit a peut-être modifié l'attribut 'k'
          // (par exemple, en ajoutant un préfixe/suffixe).
          // Vous pouvez décommenter et adapter le code ci-dessous pour une recherche plus robuste.
          // console.warn(`Bouton avec k="{key_of_selected_button}" non trouvé directement.`);
          /*
          const allStButtons = document.querySelectorAll('button[data-testid="stButton"]');
          allStButtons.forEach(button => {{
              const kValue = button.getAttribute('k');
              // Vérifier si la clé est incluse ou si kValue se termine par la clé
              if (kValue && kValue.includes("{key_of_selected_button}")) {{ 
                  button.classList.add('nav-selected');
              }}
          }});
          */
        }}
      }})();
    </script>
    """, height=0, width=0)

# ── 5. Body principal ────────────────────────────────────────────
st.markdown('<div class="content main">', unsafe_allow_html=True)

if st.session_state.page == "micro":
    micro_explorer()
elif st.session_state.page == "macro":
    macro_explorer()
else:
    # Ce bloc s'exécute si st.session_state.page est None (état initial)
    # Vous pouvez laisser vide pour ne rien afficher, ou mettre un message.
    st.markdown("<p style='text-align: center; padding: 2rem;'>Veuillez sélectionner un explorateur ci-dessus pour commencer.</p>", unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)
