import streamlit as st
import pandas as pd
from PIL import Image

# 1. Configuration de la page
st.set_page_config(page_title="Wind Farm Tool", layout="wide")

# 2. Sidebar : Affichage de l'image (Logo) et Paramètres
try:
    image = Image.open('logo.jpeg')
    st.sidebar.image(image, use_container_width=True)
except:
    st.sidebar.warning("Logo non trouvé (nommez-le logo.jpeg)")

st.sidebar.header("⚙️ Paramètres Manuels")
m_start = st.sidebar.text_input("Date Début (DD/MM/YYYY HH:MM:SS)")
m_end = st.sidebar.text_input("Date Fin (DD/MM/YYYY HH:MM:SS)")
m_resp = st.sidebar.selectbox("Responsabilité Exceptionnelle", ["EEM", "GE", "ONEE", "Autre"])

# 3. Titre Principal
st.title("📊 Analyseur d'Arrêts des Turbines")
st.markdown("---")

# 4. Base de données des Alarmes (Responsabilités par défaut)
base_rules = {
    'BackWind': 'EEM',
    'AnemCheck': 'WTG',
    'HiTemAux1': 'WTG',
    'ManualStop': 'WTG',
    'Corrective maintenance': 'WTG',
    'Out of Grid': 'ONEE'
}

# 5. Zone de téléchargement du fichier
uploaded_file = st.file_uploader("📂 Télécharger le fichier Excel SCADA", type=["xlsx"])

if uploaded_file:
    # Lecture des données
    df = pd.read_excel(uploaded_file)
    
    # Conversion des dates
    df['Start'] = pd.to_datetime(df['Start Data and Time'], dayfirst=True)
    df['End'] = pd.to_datetime(df['End Date and Time'], dayfirst=True)
    
    # Tri des données par WTG et Temps
    df = df.sort_values(['WTG0', 'Start'])
    
    processed_rows = []

    # Logique de fusion des chevauchements (Overlap)
    for wtg, group in df.groupby('WTG0'):
        if group.empty: continue
        
        c_s, c_e, c_a = group.iloc[0]['Start'], group.iloc[0]['End'], group.iloc[0]['Alarm text']
        
        for i in range(1, len(group)):
            row = group.iloc[i]
            if row['Start'] <= c_e: # Cas d'overlap
                c_e = max(c_e, row['End'])
            else:
                # Définition de la responsabilité
                resp = base_rules.get(c_a, 'WTG')
                
                # Appliquer l'exception manuelle si définie
                if m_start and m_end:
                    ms = pd.to_datetime(m_start, dayfirst=True)
                    me = pd.to_datetime(m_end, dayfirst=True)
                    if not (c_e <= ms or c_s >= me):
                        resp = m_resp

                processed_rows.append([wtg, c_a, c_s, c_e, resp])
                c_s, c_e, c_a = row['Start'], row['End'], row['Alarm text']
        
        # Ajouter la dernière ligne
        processed_rows.append([wtg, c_a, c_s, c_e, base_rules.get(c_a, 'WTG')])

    # Résultats finaux
    result_df = pd.DataFrame(processed_rows, columns=['WTG', 'Alarme', 'Début', 'Fin', 'Responsabilité'])
    result_df['Durée (Min)'] = (result_df['Fin'] - result_df['Début']).dt.total_seconds() / 60

    st.success("✅ Traitement terminé avec succès !")
    st.dataframe(result_df)

    # 6. Bouton de téléchargement du résultat
    output_filename = "Rapport_Final_Nettoyé.xlsx"
    result_df.to_excel(output_filename, index=False)
    
    with open(output_filename, "rb") as f:
        st.download_button(
            label="📥 Télécharger le fichier Excel Nettoyé",
            data=f,
            file_name=output_filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
