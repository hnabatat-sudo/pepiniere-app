import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import pandas as pd
from PIL import Image
import os
import re

# ---------- CONFIG ----------
SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive",
]


@st.cache_resource
def init_google_sheets():
    credentials_dict = st.secrets["google"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, SCOPE)
    return gspread.authorize(creds)


client = init_google_sheets()
SHEET_NAME = "Gestion Serres Étiquettes"

# Listes fixes
SERRES = ['B', 'C', 'D', 'E', 'F', 'G', 'H']
DELTAS = [str(i) for i in range(1, 33)]

# ---------- SESSION STATE ----------
if 'success_message' not in st.session_state:
    st.session_state.success_message = False


# ---------- FONCTIONS ----------
def get_or_create_sheet(client, serre_delta):
    """Crée ou récupère la feuille pour une serre-delta"""
    sh = client.open(SHEET_NAME)
    try:
        return sh.worksheet(f"{serre_delta}")
    except gspread.WorksheetNotFound:
        sheet = sh.add_worksheet(title=f"{serre_delta}", rows=1000, cols=15)
        headers = ['Date_Photo', 'Serre', 'Delta', 'Code_Client', 'Nom_Client',
                   'Batch', 'Quantité', 'Date_Semis', 'Date_Greffage',
                   'Date_Repiquage', 'Photo_URL', 'Notes']
        sheet.append_row(headers)
        return sheet


def extraire_infos_photo(photo_bytes):
    """Extrait les infos de l'étiquette via nom du fichier ou OCR simple"""
    # Simulation OCR - en vrai il faudrait Google Vision API ou Tesseract
    nom_fichier = f"Photo_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # Ici vous pourriez intégrer un OCR réel
    # Pour l'instant on laisse l'utilisateur saisir manuellement
    return nom_fichier


def enregistrer_photo(serre, delta, code_client, nom_client, batch, quantite,
                      date_semis, date_greffage, date_repiquage, notes, uploaded_file):
    """Enregistre photo + données dans Google Sheets"""
    date_photo = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Sauvegarde photo localement (optionnel)
    if uploaded_file:
        photo_path = f"photos/{serre}{delta}_{code_client}_{batch}.jpg"
        os.makedirs("photos", exist_ok=True)
        with open(photo_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        photo_url = f"file://{photo_path}"
    else:
        photo_url = "Pas de photo"

    # Enregistrement dans Google Sheets
    sheet = get_or_create_sheet(client, f"{serre}{delta}")
    row = [
        date_photo, serre, delta, code_client, nom_client, batch, quantite,
        date_semis, date_greffage, date_repiquage, photo_url, notes
    ]
    sheet.append_row(row)
    return True


# ---------- INTERFACE MOBILE ----------
st.set_page_config(
    page_title="📱 Gestion Serres - Scanner Étiquettes",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Message succès
if st.session_state.success_message:
    st.markdown("### 🎉 **ENREGISTRÉ AVEC SUCCÈS!**")
    st.success("✅ Plante enregistrée + photo sauvegardée!")
    st.balloons()
    if st.button("➕ **Nouvelle Plante**", use_container_width=True):
        st.session_state.success_message = False
        st.rerun()
    st.markdown("---")

# Titre mobile
st.title("🌱 **Gestion Serres**")
st.markdown("**📱 Scanner étiquettes par photo**")

# Sélection Serre + Delta (2 colonnes)
col1, col2 = st.columns(2)
with col1:
    serre = st.selectbox("🏠 **Serre:**", SERRES, help="Choisir serre")
with col2:
    delta = st.selectbox("🔢 **Delta:**", DELTAS, help="Choisir delta (1-32)")

# Upload photo + données
uploaded_file = st.file_uploader("📸 **Photo étiquette**", type=['jpg', 'jpeg', 'png'])

col_code, col_client = st.columns(2)
with col_code:
    code_client = st.text_input("**Code Client**", placeholder="CLI001")
with col_client:
    nom_client = st.text_input("**Nom Client**", placeholder="Dupont")

col_batch, col_qte = st.columns(2)
with col_batch:
    batch = st.text_input("**Batch/Lot**", placeholder="BATCH-2026-001")
with col_qte:
    quantite = st.number_input("**Quantité**", min_value=1, step=1, format="%d")

# Dates
col_date1, col_date2, col_date3 = st.columns(3)
with col_date1:
    date_semis = st.date_input("🌱 **Semis**", value=datetime.now())
with col_date2:
    date_greffage = st.date_input("🌳 **Greffage**")
with col_date3:
    date_repiquage = st.date_input("🌿 **Repiquage**")

notes = st.text_area("📝 **Notes**", placeholder="Variété, observations...", height=60)

# Aperçu photo
if uploaded_file:
    st.image(uploaded_file, caption="📸 Étiquette scannée", width=300)

# BOUTON ENREGISTRER PRINCIPAL
if st.button("💾 **ENREGISTRER PLANTE**", type="primary", use_container_width=True):
    if not all([serre, delta, code_client, nom_client, batch, quantite]):
        st.error("❌ **Remplir: Serre, Delta, Code, Client, Batch, Quantité**")
    else:
        try:
            success = enregistrer_photo(
                serre, delta, code_client, nom_client, batch, quantite,
                date_semis.strftime("%Y-%m-%d") if date_semis else "",
                date_greffage.strftime("%Y-%m-%d") if date_greffage else "",
                date_repiquage.strftime("%Y-%m-%d") if date_repiquage else "",
                notes, uploaded_file
            )
            if success:
                st.session_state.success_message = True
                st.rerun()
        except Exception as e:
            st.error(f"❌ Erreur: {str(e)}")

# Sidebar Historique rapide
with st.sidebar:
    st.header("📊 **Historique**")
    if st.button("🔍 **Voir Delta**"):
        try:
            if serre and delta:
                sheet = get_or_create_sheet(client, f"{serre}{delta}")
                data = sheet.get_all_values()
                if len(data) > 1:
                    df = pd.DataFrame(data[1:], columns=data[0])
                    df['Date_Photo'] = pd.to_datetime(df['Date_Photo'])
                    df_sorted = df.sort_values('Date_Photo', ascending=False)
                    st.dataframe(df_sorted.head(10), use_container_width=True)
                else:
                    st.info("📭 Aucun enregistrement")
        except Exception as e:
            st.error(f"Erreur: {e}")

st.markdown("---")
st.markdown("**📱 Mobile-first | Photos → Google Sheets** 🌱")
