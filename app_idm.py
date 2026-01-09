import time
import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from streamlit_javascript import st_javascript

# =============== CONFIG VISUAL ===============
st.set_page_config(page_title="Admin Streaming", layout="wide")

st.markdown("""
<style>
#MainMenu, header, footer, .stAppDeployButton, [data-testid="stHeader"], 
[data-testid="stToolbar"], [data-testid="stManageAppButton"] {
    visibility: hidden !important; display: none !important;
}
div[class*="viewerBadge"] { display: none !important; }
[data-testid="stDecoration"] { display: none !important; }

.stApp {
    background-image:
        linear-gradient(rgba(0,0,0,0.96), rgba(0,0,0,0.96)),
        url("https://d3o2718znwp36h.cloudfront.net/prod/uploads/2023/01/netflix-web.jpg");
    background-size: cover;
    background-position: center;
    background-attachment: fixed;
    color: white;
}
.block-container { max-width: 100% !important; padding-top: 2rem !important; }

.login-box {
    text-align: center;
    background-color: rgba(15, 15, 15, 0.95);
    padding: 60px 40px;
    border-radius: 12px;
    border: 1px solid #333;
    box-shadow: 0 0 30px rgba(0,0,0,0.7);
    max-width: 520px;
    width: 100%;
    margin: 0 auto;
}
.spinner {
    display: inline-block;
    width: 40px;
    height: 40px;
    border: 4px solid rgba(229, 9, 20, 0.3);
    border-top-color: #e50914;
    border-radius: 50%;
    animation: spin 1s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* tabla */
[data-testid="stDataFrame"] { background-color: rgba(20,20,20,0.95); }
</style>
""", unsafe_allow_html=True)

# =============== SECRETS ===============
try:
    SHEET_URL = st.secrets["general"]["sheet_url"]
    admin_ips_str = st.secrets["general"]["admin_ips"]
    ALLOWED_IPS = [x.strip() for x in admin_ips_str.split(",") if x.strip()]
except Exception as e:
    st.error("⚠️ Falta configurar [general] sheet_url y admin_ips en secrets.toml")
    st.stop()

# =============== LOGIN POR IP (MISMO FLUJO) ===============
def get_my_ip():
    try:
        url = 'https://api.ipify.org'
        ip_js = st_javascript(f"await fetch('{url}').then(r => r.text())")
        if ip_js and isinstance(ip_js, str) and len(ip_js) > 6:
            return ip_js
        return None
    except:
        return None

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_ip_cached" not in st.session_state:
    st.session_state.user_ip_cached = None
if "validacion_completa" not in st.session_state:
    st.session_state.validacion_completa = False

if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        if not st.session_state.user_ip_cached:
            st.markdown("""
                <div class="login-box">
                    <h1 style='color:#e50914; font-size:32px; margin-bottom:5px; letter-spacing:2px;'>🔒 Admin Streaming</h1>
                    <p style='color:#b3b3b3; font-size:12px; letter-spacing:1px; text-transform:uppercase; margin-bottom:25px;'>VALIDACIÓN DE ACCESO</p>
                    <div class="spinner" style='margin:0 auto 20px;'></div>
                    <p style='color:#b3b3b3; font-size:14px;'>Detectando tu IP pública...</p>
                </div>
            """, unsafe_allow_html=True)
            for _ in range(3):
                ip = get_my_ip()
                if ip:
                    st.session_state.user_ip_cached = ip
                    break
                time.sleep(1)
            if not st.session_state.user_ip_cached:
                st.error("No se pudo detectar tu IP. Pulsa 'Reintentar'.")
                if st.button("🔄 Reintentar"):
                    st.session_state.user_ip_cached = None
                    st.session_state.validacion_completa = False
                    st.rerun()
                st.stop()

        if st.session_state.user_ip_cached and not st.session_state.validacion_completa:
            st.markdown(f"""
                <div class="login-box" style='padding:40px;'>
                    <p style='color:#e5e5e5; font-size:13px; margin-bottom:20px;'>IP Detectada:</p>
                    <p style='color:#e50914; font-weight:bold; font-size:20px; margin-bottom:40px;'>{st.session_state.user_ip_cached}</p>
                    <div class="spinner" style='margin:0 auto 20px;'></div>
                    <p style='color:#b3b3b3; font-size:13px;'>Validando acceso...</p>
                </div>
            """, unsafe_allow_html=True)
            time.sleep(2)
            if st.session_state.user_ip_cached in ALLOWED_IPS:
                st.session_state.logged_in = True
            st.session_state.validacion_completa = True
            st.rerun()

        elif st.session_state.validacion_completa:
            if st.session_state.logged_in:
                st.markdown("""
                    <div class="login-box" style='padding:60px 40px; text-align:center; border-color:#228b22;'>
                        <p style='font-size:40px; margin-bottom:20px;'>✅</p>
                        <h2 style='color:#46d369; font-size:24px; margin-bottom:15px;'>ACCESO CONCEDIDO</h2>
                        <p style='color:#b3b3b3; font-size:13px; margin-bottom:25px;'>¡Bienvenido!</p>
                    </div>
                """, unsafe_allow_html=True)
                time.sleep(1.5)
                st.rerun()
            else:
                st.markdown(f"""
                    <div class="login-box" style='padding:60px 40px; text-align:center; border-color:#8b0000;'>
                        <p style='font-size:40px; margin-bottom:20px;'>❌</p>
                        <h2 style='color:#e50914; font-size:24px; margin-bottom:15px;'>ACCESO DENEGADO</h2>
                        <p style='color:#b3b3b3; font-size:13px; margin-bottom:25px;'>Tu IP no tiene permisos para acceder</p>
                        <p style='color:#888; font-size:12px;'><strong>Tu IP:</strong> {st.session_state.user_ip_cached}</p>
                    </div>
                """, unsafe_allow_html=True)
                st.stop()
    st.stop()

# =============== CABECERA APP ===============
st.markdown(f"""
<div style="display:flex; justify-content:space-between; align-items:center;
            background:rgba(17,17,17,0.96); border:1px solid #333; border-radius:10px;
            padding:12px 18px; margin-bottom:18px;">
  <h2 style="margin:0; color:#e50914;">📺 Panel Streaming</h2>
  <div style="color:#b3b3b3; font-size:12px;">IP: {st.session_state.user_ip_cached}</div>
</div>
""", unsafe_allow_html=True)

# =============== CONEXIÓN GOOGLE SHEETS ===============
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
    # fila real en Sheets
    df.insert(0, "_sheet_row", range(2, 2 + len(df)))
    return df

def col_to_letter(n: int) -> str:
    letters = ""
    while n:
        n, r = divmod(n - 1, 26)
        letters = chr(65 + r) + letters
    return letters

def update_row_in_sheet(ws_title: str, sheet_row: int, headers: list[str], values: list):
    ws = open_ws(ws_title)
    last_col_letter = col_to_letter(len(headers))
    range_a1 = f"A{sheet_row}:{last_col_letter}{sheet_row}"
    ws.update(range_a1, [values])  # gspread >=6 usa (range, values) [web:216][web:205]

import time
import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from streamlit_javascript import st_javascript

# =============== CONFIG VISUAL ===============
st.set_page_config(page_title="Admin Streaming", layout="wide")

st.markdown("""
<style>
#MainMenu, header, footer, .stAppDeployButton, [data-testid="stHeader"], 
[data-testid="stToolbar"], [data-testid="stManageAppButton"] {
    visibility: hidden !important; display: none !important;
}
div[class*="viewerBadge"] { display: none !important; }
[data-testid="stDecoration"] { display: none !important; }

.stApp {
    background-image:
        linear-gradient(rgba(0,0,0,0.96), rgba(0,0,0,0.96)),
        url("https://d3o2718znwp36h.cloudfront.net/prod/uploads/2023/01/netflix-web.jpg");
    background-size: cover;
    background-position: center;
    background-attachment: fixed;
    color: white;
}
.block-container { max-width: 100% !important; padding-top: 2rem !important; }

.login-box {
    text-align: center;
    background-color: rgba(15, 15, 15, 0.95);
    padding: 60px 40px;
    border-radius: 12px;
    border: 1px solid #333;
    box-shadow: 0 0 30px rgba(0,0,0,0.7);
    max-width: 520px;
    width: 100%;
    margin: 0 auto;
}
.spinner {
    display: inline-block;
    width: 40px;
    height: 40px;
    border: 4px solid rgba(229, 9, 20, 0.3);
    border-top-color: #e50914;
    border-radius: 50%;
    animation: spin 1s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* tabla */
[data-testid="stDataFrame"] { background-color: rgba(20,20,20,0.95); }
</style>
""", unsafe_allow_html=True)

# =============== SECRETS ===============
try:
    SHEET_URL = st.secrets["general"]["sheet_url"]
    admin_ips_str = st.secrets["general"]["admin_ips"]
    ALLOWED_IPS = [x.strip() for x in admin_ips_str.split(",") if x.strip()]
except Exception as e:
    st.error("⚠️ Falta configurar [general] sheet_url y admin_ips en secrets.toml")
    st.stop()

# =============== LOGIN POR IP (MISMO FLUJO) ===============
def get_my_ip():
    try:
        url = 'https://api.ipify.org'
        ip_js = st_javascript(f"await fetch('{url}').then(r => r.text())")
        if ip_js and isinstance(ip_js, str) and len(ip_js) > 6:
            return ip_js
        return None
    except:
        return None

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_ip_cached" not in st.session_state:
    st.session_state.user_ip_cached = None
if "validacion_completa" not in st.session_state:
    st.session_state.validacion_completa = False

if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        if not st.session_state.user_ip_cached:
            st.markdown("""
                <div class="login-box">
                    <h1 style='color:#e50914; font-size:32px; margin-bottom:5px; letter-spacing:2px;'>🔒 Admin Streaming</h1>
                    <p style='color:#b3b3b3; font-size:12px; letter-spacing:1px; text-transform:uppercase; margin-bottom:25px;'>VALIDACIÓN DE ACCESO</p>
                    <div class="spinner" style='margin:0 auto 20px;'></div>
                    <p style='color:#b3b3b3; font-size:14px;'>Detectando tu IP pública...</p>
                </div>
            """, unsafe_allow_html=True)
            for _ in range(3):
                ip = get_my_ip()
                if ip:
                    st.session_state.user_ip_cached = ip
                    break
                time.sleep(1)
            if not st.session_state.user_ip_cached:
                st.error("No se pudo detectar tu IP. Pulsa 'Reintentar'.")
                if st.button("🔄 Reintentar"):
                    st.session_state.user_ip_cached = None
                    st.session_state.validacion_completa = False
                    st.rerun()
                st.stop()

        if st.session_state.user_ip_cached and not st.session_state.validacion_completa:
            st.markdown(f"""
                <div class="login-box" style='padding:40px;'>
                    <p style='color:#e5e5e5; font-size:13px; margin-bottom:20px;'>IP Detectada:</p>
                    <p style='color:#e50914; font-weight:bold; font-size:20px; margin-bottom:40px;'>{st.session_state.user_ip_cached}</p>
                    <div class="spinner" style='margin:0 auto 20px;'></div>
                    <p style='color:#b3b3b3; font-size:13px;'>Validando acceso...</p>
                </div>
            """, unsafe_allow_html=True)
            time.sleep(2)
            if st.session_state.user_ip_cached in ALLOWED_IPS:
                st.session_state.logged_in = True
            st.session_state.validacion_completa = True
            st.rerun()

        elif st.session_state.validacion_completa:
            if st.session_state.logged_in:
                st.markdown("""
                    <div class="login-box" style='padding:60px 40px; text-align:center; border-color:#228b22;'>
                        <p style='font-size:40px; margin-bottom:20px;'>✅</p>
                        <h2 style='color:#46d369; font-size:24px; margin-bottom:15px;'>ACCESO CONCEDIDO</h2>
                        <p style='color:#b3b3b3; font-size:13px; margin-bottom:25px;'>¡Bienvenido!</p>
                    </div>
                """, unsafe_allow_html=True)
                time.sleep(1.5)
                st.rerun()
            else:
                st.markdown(f"""
                    <div class="login-box" style='padding:60px 40px; text-align:center; border-color:#8b0000;'>
                        <p style='font-size:40px; margin-bottom:20px;'>❌</p>
                        <h2 style='color:#e50914; font-size:24px; margin-bottom:15px;'>ACCESO DENEGADO</h2>
                        <p style='color:#b3b3b3; font-size:13px; margin-bottom:25px;'>Tu IP no tiene permisos para acceder</p>
                        <p style='color:#888; font-size:12px;'><strong>Tu IP:</strong> {st.session_state.user_ip_cached}</p>
                    </div>
                """, unsafe_allow_html=True)
                st.stop()
    st.stop()

# =============== CABECERA APP ===============
st.markdown(f"""
<div style="display:flex; justify-content:space-between; align-items:center;
            background:rgba(17,17,17,0.96); border:1px solid #333; border-radius:10px;
            padding:12px 18px; margin-bottom:18px;">
  <h2 style="margin:0; color:#e50914;">📺 Panel Streaming</h2>
  <div style="color:#b3b3b3; font-size:12px;">IP: {st.session_state.user_ip_cached}</div>
</div>
""", unsafe_allow_html=True)

# =============== CONEXIÓN GOOGLE SHEETS ===============
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
    # fila real en Sheets
    df.insert(0, "_sheet_row", range(2, 2 + len(df)))
    return df

def col_to_letter(n: int) -> str:
    letters = ""
    while n:
        n, r = divmod(n - 1, 26)
        letters = chr(65 + r) + letters
    return letters

def update_row_in_sheet(ws_title: str, sheet_row: int, headers: list[str], values: list):
    ws = open_ws(ws_title)
    last_col_letter = col_to_letter(len(headers))
    range_a1 = f"A{sheet_row}:{last_col_letter}{sheet_row}"
    ws.update(range_a1, [values])  # gspread >=6 usa (range, values) [web:216][web:205]

# =============== HOJA CUENTAS: EDITOR ===============
PROTECTED_CUENTAS = {
    "Logo", "Estado", "Dias", "Perfiles Activos",
    "Perfiles Disponibles", "Fecha de fin"
}

LIST_COLUMNS_CUENTAS = {
    "Plataforma",
    "Suscripcion",
    "Modalidad",
    "Proveedor",
}

NUMBER_COLUMNS_CUENTAS = {"Costo"}
DATE_COLUMNS_CUENTAS = {"Fecha del pedido"}

@st.dialog("Editar cuenta", width="large")
def dialog_editar_cuenta(row_idx: int, df: pd.DataFrame):
    row = df.iloc[row_idx].to_dict()
    sheet_row = int(row["_sheet_row"])
    headers = [c for c in df.columns if c != "_sheet_row"]

    st.write(f"Fila Google Sheets: **{sheet_row}**")

    new_vals = {}
    for h in headers:
        val = row.get(h, "")
        if h in PROTECTED_CUENTAS:
            st.text_input(h, value=str(val), disabled=True)
            continue

        if h in DATE_COLUMNS_CUENTAS:
            # intentar parsear fecha
            try:
                parsed = pd.to_datetime(val, dayfirst=True).date() if val else None
            except:
                parsed = None
            new_date = st.date_input(h, value=parsed)
            new_vals[h] = new_date.strftime("%d/%m/%Y") if new_date else ""
        elif h in NUMBER_COLUMNS_CUENTAS:
            try:
                num_val = float(str(val).replace(",", ".") or 0)
            except:
                num_val = 0.0
            new_num = st.number_input(h, value=num_val, step=1.0)
            new_vals[h] = new_num
        elif h in LIST_COLUMNS_CUENTAS:
            opciones = sorted({x for x in df[h].unique() if str(x).strip()})
            if val and val not in opciones:
                opciones.append(val)
            new_sel = st.selectbox(h, opciones, index=opciones.index(val) if val in opciones else 0)
            new_vals[h] = new_sel
        else:
            new_text = st.text_input(h, value=str(val))
            new_vals[h] = new_text

    if st.button("💾 Guardar cambios", use_container_width=True):
        final_values = []
        for h in headers:
            if h in PROTECTED_CUENTAS:
                final_values.append(row.get(h, ""))
            else:
                final_values.append(new_vals.get(h, ""))
        update_row_in_sheet("Cuentas", sheet_row, headers, final_values)
        st.success("✅ Guardado en Google Sheets.")
        st.cache_data.clear()
        st.rerun()

def pantalla_cuentas():
    df = read_ws_df("Cuentas")
    if df.empty:
        st.warning("La hoja 'Cuentas' está vacía.")
        return

    st.subheader("📄 Cuentas")
    st.dataframe(df.drop(columns=["_sheet_row"]), use_container_width=True)

    st.markdown("### ✏️ Editar fila")
    for idx, row in df.iterrows():
        col1, col2 = st.columns([4, 1])
        with col1:
            st.write(f"Fila {int(row['_sheet_row'])} · {row.get('Plataforma','')} · {row.get('Correo','')}")
        with col2:
            if st.button("✏️ Editar", key=f"edit_{idx}", use_container_width=True):
                dialog_editar_cuenta(idx, df)

# =============== MAIN: solo Cuentas por ahora ===============
tab_cuentas, = st.tabs(["Cuentas"])
with tab_cuentas:
    pantalla_cuentas()
