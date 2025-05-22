# Analyse Wikipédia

Une application **Streamlit** pour :

- Visualiser l’évolution temporelle des **pages vues** et des **éditions** sur Wikipédia  
- Calculer des scores **Heat**, **Quality**, **Risk** et un **score de sensibilité** agrégé  
- Afficher un **diagramme de Kiviat (radar)** pour explorer la sensibilité de plusieurs pages  
- Interface interactive : choix des pages, dates, langue, mode « Tous » vs « Comparer »  


---

## Fonctionnalités

1. **Évolution pages vues**  
   Récupère via l’API Wikimedia les vues quotidiennes et trace une courbe interactive.

2. **Évolution éditions**  
   Récupère via l’API Wikimedia le nombre d’éditions quotidiennes (éditeurs enregistrés) et trace une courbe.

3. **Sensibilité (radar)**  
   - Calcul absolu (indépendant des autres pages) des métriques Heat, Quality, Risk  
   - Agrégation pondérée + score de sensibilité global  
   - Diagramme radar par page, avec mode « Comparer » pour jusqu’à 3 pages simultanées.

---

## Prérequis

- **Python 3.8+**  
- **Accès Internet** (API Wikimedia)  
- Modules Python :
  - streamlit  
  - pandas  
  - plotly  
  - requests  
  - (et dépendances de `wikipedia_scoring_pipeline.py` : `pageviews`, `edit`, `taille_talk`, `protection`, `ref`, `readability`, `ano_edit`)

---

## Installation

1. **Cloner** le dépôt :
   ```bash
   git clone https://github.com/opinionscience/Wikipedia_tools.git
   cd analyse-wikipedia
