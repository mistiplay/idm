import re
from datetime import date, timedelta

import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from streamlit_javascript import st_javascript

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
# LOGIN POR IP (ADMIN)
# =======================
def get_public_ip():
    # El navegador consulta ipify y devuelve la IP pública [web:184][web:186]
    try:
        script = """
        const r = await fetch("https://api.ipify.org?format=json");
        return await r.json();
        """
        result = st_javascript(script)
        if isinstance(result, dict) and "ip" in result:
            return result["ip"]
    except:
        pass
    return None

def is_admin_ip(ip: str) -> bool:
    admin_ips_str = st.secrets["general"]["admin_ips"]
    admin_ips = [x.strip() for x in admin_ips_str.split(",") if x.strip()]
    return ip in admin_ips

if "admin_ok" not in st.session_state:
    st.session_state.admin_ok = False
if "user_ip" not in st.session_state:
    st.session_state.user_ip = None

if not st.session_state.admin_ok:
    if st.session_state.user_ip is None:
        st.session_state.user_ip = get_public_ip()
        st.rerun()

    if st.session_state.user_ip is None:
        st.warning("Detectando IP... recarga en unos segundos.")
        st.stop()

    if not is_admin_ip(st.session_state.user_ip):
        st.error(f"❌ IP no autorizada: {st.session_state.user_ip}")
        st.stop()

    st.session_state.admin_ok = True
    st.rerun()

st.markdown(
    f"<div style='text-align:center; color:#00C6FF; font-weight:700;'>🔐 ADMIN MODE - IP: {st.session_state.user_ip}</div>",
    unsafe_allow_html=True
)

# =======================
# GOOGLE SHEETS (CON CACHE)
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
    df = df.copy()
    df.columns = pd.Index([str(c).strip() for c in df.columns])
    return df

@st.cache_data(ttl=300)
def read_worksheet_as_df(title: str) -> pd.DataFrame:
    ws = open_ws(title)
    values = ws.get_all_values()
    if not values:
        return pd.DataFrame()
    headers = [h.strip() for h in values[0]]
    rows = values[1:]
    df = pd.DataFrame(rows, columns=headers)
    return safe_strip_columns(df)

# =======================
# PARSEO FECHA EN ESPAÑOL
# =======================
MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12
}

def parse_fecha_es(x):
    # Acepta "30 de mayo de 2025" o "30/05/2025"
    if x in (None, "", "N/A"):
        return None
    s = str(x).strip().lower()

    # Formato 30/05/2025
    try:
        if "/" in s:
            return pd.to_datetime(s, dayfirst=True).date()
    except:
        pass

    # Formato "30 de mayo de 2025"
    m = re.match(r"(\d{1,2})\s+de\s+([a-záéíóúñ]+)\s+de\s+(\d{4})", s)
    if not m:
        return None
    dd = int(m.group(1))
    mes_txt = m.group(2).replace("á","a").replace("é","e").replace("í","i").replace("ó","o").replace("ú","u")
    mm = MESES.get(mes_txt)
    yy = int(m.group(3))
    if not mm:
        return None
    return date(yy, mm, dd)

def parse_meses(s) -> int:
    if not s:
        return 0
    m = re.search(r"(\d+)", str(s))
    return int(m.group(1)) if m else 0

def estado_por_dias(d):
    if d is None:
        return "Desconocido"
    if d < 0:
        return "Vencido"
    if d <= 2:
        return "Por vencer"
    return "Activo"

# =======================
# APP: CUENTAS
# =======================
st.markdown("<h2 style='text-align:center; color:#00C6FF;'>📺 CUENTAS</h2>", unsafe_allow_html=True)

df = read_worksheet_as_df("Cuentas")
df_plat = read_worksheet_as_df("Buscarv")

with st.expander("Ver columnas detectadas (diagnóstico)"):
    st.write("Columnas en Cuentas:", df.columns.tolist())
    st.write("Columnas en Buscarv:", df_plat.columns.tolist())

if df.empty:
    st.warning("La hoja 'Cuentas' está vacía.")
    st.stop()

# Validar columnas mínimas
for col in ["Plataforma", "Suscripcion", "Fecha del pedido"]:
    if col not in df.columns:
        st.error(f"En 'Cuentas' falta la columna: {col}")
        st.stop()

for col in ["Plataforma", "logo_url", "max_perfiles"]:
    if col not in df_plat.columns:
        st.error(f"En 'Buscarv' falta la columna: {col}")
        st.stop()

# Merge (traer logo y max perfiles)
df = df.merge(df_plat[["Plataforma", "logo_url", "max_perfiles"]], on="Plataforma", how="left")

# Convertir números / defaults
if "Perfiles Activos" not in df.columns:
    df["Perfiles Activos"] = 0
df["Perfiles Activos"] = pd.to_numeric(df["Perfiles Activos"], errors="coerce").fillna(0).astype(int)
df["max_perfiles"] = pd.to_numeric(df["max_perfiles"], errors="coerce")

# Calcular fechas/días/estado en la APP
hoy = date.today()
df["meses_num"] = df["Suscripcion"].apply(parse_meses)
df["Fecha del pedido_dt"] = df["Fecha del pedido"].apply(parse_fecha_es)

df["Fecha de fin"] = df.apply(
    lambda r: (r["Fecha del pedido_dt"] + timedelta(days=int(r["meses_num"]) * 30))
    if r["Fecha del pedido_dt"] and r["meses_num"] else None,
    axis=1
)

df["Dias"] = df["Fecha de fin"].apply(lambda d: (d - hoy).days if d else None)
df["Estado"] = df["Dias"].apply(estado_por_dias)
df["Perfiles Disponibles"] = (df["max_perfiles"] - df["Perfiles Activos"]).clip(lower=0)

# Mostrar
st.dataframe(
    df,
    use_container_width=True,
    column_config={"logo_url": st.column_config.ImageColumn("Logo")}
)
