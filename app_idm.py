import time
import re
from datetime import date, timedelta

import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# =======================
# CONFIG + OCULTAR BARRA
# =======================
st.set_page_config(page_title="Admin Panel", page_icon="⚙️", layout="wide")
st.markdown("""
<style>
#MainMenu, header, footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

SHEET_URL = st.secrets["general"]["sheet_url"]

# =======================
# FUNCIONES GOOGLE SHEETS
# =======================
@st.cache_resource
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

def safe_strip_columns(df: pd.DataFrame) -> pd.DataFrame:
    # Convierte cualquier nombre de columna a texto y quita espacios
    df = df.copy()
    df.columns = pd.Index([str(c).strip() for c in df.columns])
    return df

@st.cache_data(ttl=120)  # cache 2 minutos para evitar 429 [web:155]
def read_worksheet_as_df(title: str) -> pd.DataFrame:
    ws = open_ws(title)
    data = ws.get_all_records()
    df = pd.DataFrame(data)
    return safe_strip_columns(df)

# =======================
# FUNCIONES DE NEGOCIO
# =======================
def parse_meses(s) -> int:
    if not s:
        return 0
    m = re.search(r"(\d+)", str(s))
    return int(m.group(1)) if m else 0

def to_date(x):
    if x in (None, "", "N/A"):
        return None
    try:
        # Si tus fechas están como "30/05/2025" o similares
        return pd.to_datetime(x, dayfirst=True).date()
    except:
        return None

def estado_por_dias(d):
    if d is None:
        return "Desconocido"
    if d < 0:
        return "Vencido"
    if d <= 2:
        return "Por vencer"
    return "Activo"

# =======================
# APP
# =======================
st.markdown("<h2 style='text-align:center; color:#00C6FF;'>📺 CUENTAS</h2>", unsafe_allow_html=True)

try:
    df = read_worksheet_as_df("Cuentas")
    df_plat = read_worksheet_as_df("Buscarv")

except gspread.exceptions.APIError as e:
    # Si es 429, normalmente se arregla esperando un rato [web:145]
    st.error("Google bloqueó por muchas lecturas (Error 429). Espera 1–2 minutos y presiona Reboot.")
    st.exception(e)
    st.stop()

except Exception as e:
    st.error("Error cargando Google Sheets. Revisa que las hojas existan y que tengan encabezados en la fila 1.")
    st.exception(e)
    st.stop()

# Mostrar columnas para que confirmes (modo fácil)
with st.expander("Ver columnas detectadas (diagnóstico)"):
    st.write("Columnas en Cuentas:", df.columns.tolist())  # [web:137]
    st.write("Columnas en Buscarv:", df_plat.columns.tolist())  # [web:137]

# Validación mínima (para evitar errores raros)
if df.empty:
    st.warning("La hoja 'Cuentas' está vacía o no tiene datos aún.")
    st.stop()

# IMPORTANTE: Estas columnas deben existir tal cual en ambas hojas:
# - En Cuentas: 'Plataforma'
# - En Buscarv: 'Plataforma', 'logo_url', 'max_perfiles'
required_cuentas = ["Plataforma", "Suscripcion", "Fecha del pedido"]
required_buscarv = ["Plataforma", "logo_url", "max_perfiles"]

missing_cuentas = [c for c in required_cuentas if c not in df.columns]
missing_buscarv = [c for c in required_buscarv if c not in df_plat.columns]

if missing_cuentas:
    st.error(f"En la hoja 'Cuentas' faltan estas columnas: {missing_cuentas}")
    st.stop()

if missing_buscarv:
    st.error(f"En la hoja 'Buscarv' faltan estas columnas: {missing_buscarv}")
    st.stop()

# Merge para traer logo_url y max_perfiles
df = df.merge(
    df_plat[["Plataforma", "logo_url", "max_perfiles"]],
    on="Plataforma",
    how="left"
)

# Cálculos de fechas/días/estado
hoy = date.today()
df["meses_num"] = df["Suscripcion"].apply(parse_meses)
df["Fecha del pedido_dt"] = df["Fecha del pedido"].apply(to_date)

df["Fecha de fin"] = df.apply(
    lambda r: (r["Fecha del pedido_dt"] + timedelta(days=int(r["meses_num"]) * 30))
    if r["Fecha del pedido_dt"] and r["meses_num"] else None,
    axis=1
)

df["Dias"] = df["Fecha de fin"].apply(lambda d: (d - hoy).days if d else None)
df["Estado"] = df["Dias"].apply(estado_por_dias)

# Perfiles
if "Perfiles Activos" not in df.columns:
    df["Perfiles Activos"] = 0

df["Perfiles Activos"] = pd.to_numeric(df["Perfiles Activos"], errors="coerce").fillna(0).astype(int)
df["max_perfiles"] = pd.to_numeric(df["max_perfiles"], errors="coerce")
df["Perfiles Disponibles"] = (df["max_perfiles"] - df["Perfiles Activos"]).clip(lower=0)

# Mostrar tabla
st.dataframe(
    df,
    use_container_width=True,
    column_config={
        "logo_url": st.column_config.ImageColumn("Logo"),
    }
)
