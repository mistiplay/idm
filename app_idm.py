import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ====== CONFIG ======
st.set_page_config(page_title="Admin Panel", page_icon="⚙️", layout="wide")
st.markdown("""
<style>
#MainMenu, header, footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

SHEET_URL = st.secrets["general"]["sheet_url"]

def gs_client():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    return gspread.authorize(creds)

def open_ws(title: str):
    client = gs_client()
    ss = client.open_by_url(SHEET_URL)
    return ss.worksheet(title)

# ====== CARGA ======
ws_cuentas = open_ws("Cuentas")
df = pd.DataFrame(ws_cuentas.get_all_records())

ws_buscarv = open_ws("Buscarv")
df_plat = pd.DataFrame(ws_buscarv.get_all_records())

# ====== LIMPIAR NOMBRES DE COLUMNAS (IMPORTANTE) ======
df.columns = df.columns.str.strip()
df_plat.columns = df_plat.columns.str.strip()

# ====== MOSTRAR COLUMNAS Y PARAR (PARA DIAGNOSTICAR) ======
st.subheader("Diagnóstico de columnas")
st.write("Columnas en Cuentas:")
st.write(df.columns.tolist())  # muestra lista [web:137]
st.write("Columnas en Buscarv:")
st.write(df_plat.columns.tolist())  # muestra lista [web:137]
st.warning("Cuando veas aquí la columna exacta que corresponde a Plataforma, me dices cuál es para ajustar el merge. Por ahora el app se detiene aquí.")
st.stop()
