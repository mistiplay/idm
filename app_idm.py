import time
import string
import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from streamlit_javascript import st_javascript

# =======================
# CONFIG + "TAPAR TODO"
# =======================
st.set_page_config(page_title="Admin Panel", page_icon="⚙️", layout="wide")
st.markdown(
    """
<style>
#MainMenu, header, footer {visibility: hidden;}
.stApp { background-color: #0e0e0e; color: white; }
</style>
""",
    unsafe_allow_html=True,
)

SHEET_URL = st.secrets["general"]["sheet_url"]

# =======================
# LOGIN POR IP
# =======================
def get_public_ip():
    # IP pública desde el navegador (ipify) [web:186]
    script = """
    const r = await fetch("https://api.ipify.org?format=json");
    return await r.json();
    """
    try:
        result = st_javascript(script)
        if isinstance(result, dict) and "ip" in result:
            return result["ip"]
    except:
        return None
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
        st.warning("Detectando IP... si no avanza, recarga la página.")
        st.stop()

    if not is_admin_ip(st.session_state.user_ip):
        st.error(f"❌ IP no autorizada: {st.session_state.user_ip}")
        st.stop()

    st.session_state.admin_ok = True
    st.rerun()

st.markdown(
    f"<div style='text-align:center; color:#00C6FF; font-weight:800; margin-bottom:10px;'>🔐 ADMIN - IP: {st.session_state.user_ip}</div>",
    unsafe_allow_html=True,
)

# =======================
# GOOGLE SHEETS (CLIENTE)
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

@st.cache_data(ttl=120)
def read_ws_df(title: str) -> pd.DataFrame:
    ws = open_ws(title)
    values = ws.get_all_values()
    if not values:
        return pd.DataFrame()
    headers = [h.strip() for h in values[0]]
    rows = values[1:]
    df = pd.DataFrame(rows, columns=headers)
    df = safe_strip_columns(df)

    # Guardar número real de fila en Sheets (fila 2 = primer registro)
    df.insert(0, "_sheet_row", range(2, 2 + len(df)))
    return df

def col_to_letter(n: int) -> str:
    # 1->A, 2->B...
    letters = ""
    while n:
        n, r = divmod(n - 1, 26)
        letters = chr(65 + r) + letters
    return letters

def update_row_in_sheet(ws_title: str, sheet_row: int, headers: list[str], values: list):
    ws = open_ws(ws_title)
    last_col_letter = col_to_letter(len(headers))
    range_a1 = f"A{sheet_row}:{last_col_letter}{sheet_row}"
    ws.update([values], range_a1)  # actualiza el rango con una fila [web:216][web:147]

# =======================
# EDITOR VERTIC
