import re
import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, date, timedelta

SHEET_URL = st.secrets["general"]["sheet_url"]

def gs_client():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    return gspread.authorize(creds)

def open_ws(title: str):
    client = gs_client()
    ss = client.open_by_url(SHEET_URL)
    return ss.worksheet(title)

def parse_meses(s: str) -> int:
    if not s:
        return 0
    m = re.search(r"(\d+)", str(s))
    return int(m.group(1)) if m else 0

def to_date(x):
    # Acepta fecha como string o datetime; ajusta dayfirst según cómo guardes en Sheets
    if x in (None, "", "N/A"):
        return None
    try:
        return pd.to_datetime(x, dayfirst=True).date()
    except:
        return None

def estado_por_dias(d: int) -> str:
    if d is None:
        return "Desconocido"
    if d < 0:
        return "Vencido"
    if d <= 2:
        return "Por vencer"
    return "Activo"

# --- Cargar hojas ---
ws_cuentas = open_ws("Cuentas")
df = pd.DataFrame(ws_cuentas.get_all_records())

ws_plat = open_ws("Buscarv")  # o "Plataformas" si así la llamas
df_plat = pd.DataFrame(ws_plat.get_all_records())

# --- Normalizar / merge para traer logo y max_perfiles ---
# Esperado en df_plat: Plataforma, logo_url, max_perfiles
df = df.merge(
    df_plat[["Plataforma", "logo_url", "max_perfiles"]],
    on="Plataforma",
    how="left"
)

# --- Calcular fechas / días / estado ---
hoy = date.today()

df["meses_num"] = df["Suscripcion"].apply(parse_meses)
df["Fecha del pedido_dt"] = df["Fecha del pedido"].apply(to_date)

df["Fecha de fin_calc"] = df.apply(
    lambda r: (r["Fecha del pedido_dt"] + timedelta(days=int(r["meses_num"])*30))
              if r["Fecha del pedido_dt"] and r["meses_num"] else None,
    axis=1
)

df["Dias"] = df["Fecha de fin_calc"].apply(lambda d: (d - hoy).days if d else None)
df["Estado"] = df["Dias"].apply(estado_por_dias)

# --- Perfiles disponibles ---
df["Perfiles Activos"] = pd.to_numeric(df.get("Perfiles Activos", 0), errors="coerce").fillna(0).astype(int)
df["max_perfiles"] = pd.to_numeric(df["max_perfiles"], errors="coerce")
df["Perfiles Disponibles"] = (df["max_perfiles"] - df["Perfiles Activos"]).clip(lower=0)

# --- Mostrar tabla con logo ---
st.dataframe(
    df,
    use_container_width=True,
    column_config={
        "logo_url": st.column_config.ImageColumn("Logo")
    }
)
