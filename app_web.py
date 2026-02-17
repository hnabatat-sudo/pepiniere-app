import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import openpyxl
import os
import pandas as pd
from PIL import Image
import json

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
SHEET_NAME = "suivi des opérations"

SERRES = ['B', 'C', 'D', 'E', 'F', 'G', 'H']
DELTAS = [str(i) for i in range(1, 33)]
CULTURES = ['tomate', 'pastèque', 'poivron', 'concombre', 'laitue', 'ciboulette', 'courgette', 'herbes aromatiques']
TRAITEMENTS = ['fongicide', 'insecticide', 'acaricide', 'insecticide/acaricide', 'raticide',
               'bio-stimulant', 'désinfectant', 'engrais foliaire']
SOLUTIONS_IRRI = ['AB', 'CD', 'M', 'Urée', 'enracineur', 'désinfectant']
ECS = ['1.6', '1.8', '2', '2.5', '3', '3.5', '4']

EXCEL_PRODUITS = "produits.xlsx"

# ---------- SESSION STATE AMÉLIORÉ ----------
if "form_submitted" not in st.session_state:
    st.session_state.form_submitted = False
if "reset_form" not in st.session_state:
    st.session_state.reset_form = False

# ---------- CRÉATION AUTOMATIQUE PRODUITS.XLSX ----------
def create_produits_excel():
    if not os.path.exists(EXCEL_PRODUITS):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Produits"
        ws.append(["Designation", "Dose", "Cible"])
        wb.save(EXCEL_PRODUITS)
        return True
    return False

create_produits_excel()

# ---------- FONCTIONS ----------
@st.cache_data
def charger_produits():
    wb = openpyxl.load_workbook(EXCEL_PRODUITS)
    ws = wb.active
    produits = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if row and len(row) >= 3:
            produits.append({
                'nom': str(row[0]).strip(),
                'dose': str(row[1]).strip(),
                'cible': str(row[2]).strip(),
                'details': f"{row[0]} {row[1]} {row[2]}"
            })
    return produits

def ajouter_produit(designation, dose, cible):
    wb = openpyxl.load_workbook(EXCEL_PRODUITS)
    ws = wb.active
    ws.append([designation, dose, cible])
    wb.save(EXCEL_PRODUITS)
    st.cache_data.clear()

def get_or_create_sheet(client, serre_delta):
    sh = client.open(SHEET_NAME)
    try:
        return sh.worksheet(serre_delta)
    except gspread.WorksheetNotFound:
        sheet = sh.add_worksheet(title=serre_delta, rows=1000, cols=20)
        headers = ['Date', 'Serre', 'Delta', 'Culture', 'Operation', 'Details']
        sheet.append_row(headers)
        return sheet

def get_details_produits(selected_noms, produits):
    details_produits = []
    for nom in selected_noms:
        for p in produits:
            if p['nom'] == nom:
                details_produits.append(p['details'])
                break
    return details_produits

def reset_form():
    """Réinitialise tous les champs du formulaire"""
    for key in list(st.session_state.keys()):
        if any(prefix in key for prefix in ['serre', 'deltas', 'culture', 'operation', 'traitements', 'produits', 'solution', 'ec']):
            del st.session_state[key]
    st.session_state.reset_form = True
    st.session_state.form_submitted = False

# ---------- INTERFACE STREAMLIT ----------
st.set_page_config(
    page_title="Suivi Opérations Pépinière",
    page_icon="🌱",
    layout="wide"
)

# Sidebar logo et navigation
with st.sidebar:
    st.title("🌱 Pépinière")
    try:
        logo_path = os.path.join(os.path.dirname(__file__), "logo.png")
        logo = Image.open(logo_path)
        st.image(logo, width=120)
    except Exception:
        st.markdown("### 🌱")
    
    st.subheader("📦 Produits")
    produits = charger_produits()

    with st.form("ajout_produit"):
        st.markdown("**Nouveau produit:**")
        des = st.text_input("**Designation**", placeholder="ex: Amistar")
        dose = st.text_input("**Dose**", placeholder="ex: 2ml/L")
        cible = st.text_input("**Cible**", placeholder="ex: pucerons")
        submitted = st.form_submit_button("➕ **Ajouter**", use_container_width=True)

    if submitted and all([des, dose, cible]):
        ajouter_produit(des, dose, cible)
        st.success(f"✅ **{des}** ({dose}) → {cible} ajouté!")
        st.rerun()
    elif submitted:
        st.error("❌ Remplissez tous les champs!")

    st.markdown("**📋 Produits disponibles:**")
    if produits:
        for i, p in enumerate(produits, 1):
            st.write(f"{i}. **{p['nom']}** ({p['dose']}) → **{p['cible']}**")
    else:
        st.warning("⚠️ Aucun produit")

# Contenu principal
st.title("📊 Suivi Opérations Pépinière")
st.markdown("**Multi-Delta | Multi-Traitement | Multi-Produits**")

# Formulaire principal avec clés uniques
col1, col2, col3 = st.columns(3)
with col1:
    serre = st.selectbox("**Serre:**", SERRES, key="serre_key")
with col2:
    selected_deltas = st.multiselect("**Deltas:**", DELTAS, max_selections=10, key="deltas_key")
with col3:
    culture = st.selectbox("**Culture:**", CULTURES, key="culture_key")

operation = st.selectbox("**Opération:**", ['traitement', 'irrigation'], key="operation_key")

selected_noms = []
selected_traitements = []
solution = ""
ec = ""

if operation == 'traitement':
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        st.markdown("**🔥 Multi-Traitement**")
        selected_traitements = st.multiselect(
            "Catégories:", TRAITEMENTS,
            max_selections=4,
            key="traitements_key"
        )
    with col_t2:
        st.markdown("**📦 Multi-Produits**")
        noms_produits = [p['nom'] for p in produits]
        selected_noms = st.multiselect(
            "Produits:", noms_produits,
            max_selections=8,
            key="produits_key"
        )
        if selected_traitements and selected_noms:
            st.caption(f"**{len(selected_traitements)} catégories** | **{len(selected_noms)} produits**")

elif operation == 'irrigation':
    col6, col7 = st.columns(2)
    with col6:
        solution = st.selectbox("**Solution:**", SOLUTIONS_IRRI, key="solution_key")
    with col7:
        ec = st.selectbox("**EC:**", ECS, key="ec_key")

# Aperçu en temps réel
with st.expander("👀 **Aperçu enregistrement**", expanded=True):
    if operation == 'traitement':
        if selected_traitements:
            details = "; ".join(selected_traitements)
        else:
            details = "Aucun traitement"

        if selected_noms:
            details_produits = get_details_produits(selected_noms, produits)
            if details_produits:
                details += f" - {'; '.join(details_produits)}"
    else:
        details = f"{solution} EC{ec}"

    st.info(f"""
    **🗓️ Date:** {datetime.now().strftime("%Y-%m-%d %H:%M")}
    **🏠 Serre:** {serre or '---'}  
    **🔢 Deltas:** {', '.join(selected_deltas) if selected_deltas else 'Aucun'}  
    **🌱 Culture:** {culture or '---'}  
    **⚙️ Opération:** {operation}  
    **📝 Détails:** {details}
    """)

# Bouton ENREGISTRER avec confirmation
if st.button("💾 **ENREGISTRER**", type="primary", use_container_width=True, disabled=st.session_state.form_submitted):
    if not all([serre, selected_deltas, culture]):
        st.error("❌ **Serre, Deltas et Culture OBLIGATOIRES!**")
    elif operation == 'traitement' and not selected_traitements:
        st.error("❌ **Sélectionnez au moins 1 traitement!**")
    elif operation == 'irrigation' and not (solution and ec):
        st.error("❌ **Solution et EC obligatoires pour irrigation!**")
    else:
        # Modal de confirmation
        st.markdown("### ✅ **Confirmer l'enregistrement ?**")
        col_confirm, col_actions = st.columns([2, 1])
        
        with col_confirm:
            st.info(f"""
            **📝 À enregistrer dans {len(selected_deltas)} delta(s):**
            • **Serre:** {serre}
            • **Deltas:** {', '.join(selected_deltas)}
            • **Culture:** {culture}
            • **Opération:** {operation}
            • **Détails:** {details}
            """)
        
        with col_actions:
            col_yes, col_no = st.columns(2)
            with col_yes:
                if st.button("✅ **OUI, Enregistrer**", type="primary", use_container_width=True):
                    # Enregistrement des données
                    date = datetime.now().strftime("%Y-%m-%d %H:%M")
                    success_count = 0
                    
                    for delta in selected_deltas:
                        try:
                            sheet = get_or_create_sheet(client, f"{serre}{delta}")
                            row = [date, serre, delta, culture, operation, details]
                            sheet.append_row(row)
                            success_count += 1
                        except Exception as e:
                            st.error(f"❌ Delta {delta}: {str(e)}")
                    
                    if success_count > 0:
                        st.session_state.form_submitted = True
                        st.success(f"🎉 **SUCCÈS!** {success_count}/{len(selected_deltas)} delta(s) enregistré(s) avec succès!")
                        st.balloons()
                        
                        # Réinitialisation automatique
                        reset_form()
                        st.rerun()
                    else:
                        st.error("❌ Aucun delta n'a pu être enregistré!")
            
            with col_no:
                if st.button("❌ **Annuler**", use_container_width=True):
                    st.rerun()

# Message de succès final
if st.session_state.form_submitted:
    st.markdown("### 🎊 **Enregistrement terminé !**")
    st.success("✅ Tous les champs ont été réinitialisés. Prêt pour une nouvelle opération!")
    st.balloons()
    
    col_btn, col_hist = st.columns([1, 3])
    with col_btn:
        if st.button("🔄 **Nouvelle Opération**", type="secondary", use_container_width=True):
            reset_form()
            st.rerun()

# Historique
if st.checkbox("📋 **Afficher Historique**"):
    try:
        if serre and selected_deltas:
            sh = client.open(SHEET_NAME)
            if len(selected_deltas) == 1:
                feuille = sh.worksheet(f"{serre}{selected_deltas[0]}")
                data = feuille.get_all_values()
                if len(data) > 1:
                    df = pd.DataFrame(data[1:], columns=data[0])
                    st.dataframe(df.tail(15), use_container_width=True, height=400)
                else:
                    st.info("📭 Aucun enregistrement pour ce delta")
            else:
                st.warning("⚠️ Sélectionnez un seul delta pour voir l'historique")
        else:
            st.info("👆 Sélectionnez une serre et un delta pour voir l'historique")
    except Exception as e:
        st.error(f"❌ Erreur Google Sheets: {str(e)}")

st.markdown("---")
st.markdown("🌱 **Suivi Pépinière - Version Améliorée avec Confirmation & Reset**")
