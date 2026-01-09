import time
import re
import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from streamlit_javascript import st_javascript

# =========================
# 1) CONFIGURACIÓN DE PÁGINA
# =========================
st.set_page_config(page_title="Admin Panel", layout="wide")

# =========================
# 2) CSS (IGUAL A TU EJEMPLO)
# =========================
st.markdown("""
    <style>
    /* Ocultar elementos nativos */
    #MainMenu, header, footer, .stAppDeployButton, [data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stManageAppButton"] {
        visibility: hidden !important; display: none !important;
    }
    div[class*="viewerBadge"] { display: none !important; }
    [data-testid="stDecoration"] { display: none !important; }

    /* --- FONDO CON CAPA OSCURECIDA --- */
    .stApp {
        background-image:
            linear-gradient(rgba(0, 0, 0, 0.95), rgba(0, 0, 0, 0.95)),
            url("https://d3o2718znwp36h.cloudfront.net/prod/uploads/2023/01/netflix-web.jpg");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: fixed;
    }

    /* Ajuste contenedor */
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 3rem !important;
        max-width: 100% !important;
    }

    /* --- ANIMACIÓN DE CARGA --- */
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

    /* --- LOGIN BOX --- */
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

    /* --- TABS --- */
    .stTabs [role="tab"] {
        color: #b3b3b3;
        font-weight: 600;
        padding: 10px 16px;
    }
    .stTabs [role="tab"][aria-selected="true"] {
        color: #e50914;
        border-bottom: 3px solid #e50914;
    }

    /* --- DATAFRAME --- */
    [data-testid="stDataFrame"] { background-color: rgba(20, 20, 20, 0.95); }
    </style>
""", unsafe_allow_html=True)

# =========================
# 3) CARGAR SECRETS
# =========================
try:
    SHEET_URL = st.secrets["general"]["sheet_url"]  # [web:8]
    admin_ips_str = st.secrets["general"]["admin_ips"]
    ALLOWED_IPS = [x.strip() for x in admin_ips_str.split(",") if x.strip()]
except:
    st.error("⚠️ Falta configurar secrets: [general] sheet_url y admin_ips")
    st.stop()

# =========================
# 4) DETECTAR IP (IGUAL A TU EJEMPLO)
# =========================
def get_my_ip():
    """Detecta IP Real via JS (ipify)"""  # [web:186]
    try:
        url = 'https://api.ipify.org'
        ip_js = st_javascript(f"await fetch('{url}').then(r => r.text())")
        if ip_js and isinstance(ip_js, str) and len(ip_js) > 6:
            return ip_js
        return None
    except:
        return None

# =========================
# 5) LOGIN POR IP (IGUAL A TU FLUJO)
#    + mejora: botón "Reintentar" si no detecta IP
# =========================
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_ip_cached' not in st.session_state:
    st.session_state.user_ip_cached = None
if 'validacion_completa' not in st.session_state:
    st.session_state.validacion_completa = False

if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        # Intentar detectar IP unas veces (para no quedar colgado)
        if not st.session_state.user_ip_cached:
            st.markdown("""
                <div class="login-box">
                    <h1 style='color: #e50914; font-size: 32px; margin-bottom: 5px; letter-spacing: 2px;'>🔒 Admin Panel</h1>
                    <p style='color: #b3b3b3; font-size: 12px; letter-spacing: 1px; text-transform: uppercase; margin-bottom: 25px;'>VALIDACIÓN DE ACCESO</p>
                    <div class="spinner" style='margin: 0 auto 20px; display: flex; justify-content: center;'></div>
                    <p style='color: #b3b3b3; font-size: 14px;'>Detectando tu IP pública...</p>
                </div>
            """, unsafe_allow_html=True)

            # intentos cortos
            for _ in range(3):
                ip = get_my_ip()
                if ip:
                    st.session_state.user_ip_cached = ip
                    break
                time.sleep(1)

            if not st.session_state.user_ip_cached:
                st.error("No se pudo detectar tu IP (posible bloqueo de red).")
                if st.button("🔄 Reintentar"):
                    st.session_state.user_ip_cached = None
                    st.session_state.validacion_completa = False
                    st.rerun()
                st.stop()

        # PASO 1: IP detectada pero aún no validada
        if st.session_state.user_ip_cached and not st.session_state.validacion_completa:
            st.markdown(f"""
            <div class="login-box" style='padding: 40px;'>
                <p style='color: #e5e5e5; font-size: 13px; margin-bottom: 20px;'>IP Detectada:</p>
                <p style='color: #e50914; font-weight: bold; font-size: 20px; margin-bottom: 40px;'>{st.session_state.user_ip_cached}</p>
                <div class="spinner" style='margin: 0 auto 20px; display: flex; justify-content: center;'></div>
                <p style='color: #b3b3b3; font-size: 13px;'>Validando acceso...</p>
            </div>
            """, unsafe_allow_html=True)

            time.sleep(2)

            if st.session_state.user_ip_cached in ALLOWED_IPS:
                st.session_state.logged_in = True

            st.session_state.validacion_completa = True
            st.rerun()

        # PASO 2: Validación completa - Mostrar resultado
        elif st.session_state.validacion_completa:
            if st.session_state.logged_in:
                st.markdown("""
                <div class="login-box" style='padding: 60px 40px; text-align: center; border-color: #228b22;'>
                    <p style='font-size: 40px; margin-bottom: 20px;'>✅</p>
                    <h2 style='color: #46d369; font-size: 24px; margin-bottom: 15px;'>ACCESO CONCEDIDO</h2>
                    <p style='color: #b3b3b3; font-size: 13px; margin-bottom: 25px;'>¡Bienvenido!</p>
                </div>
                """, unsafe_allow_html=True)
                time.sleep(2)
                st.rerun()
            else:
                st.markdown(f"""
                <div class="login-box" style='padding: 60px 40px; text-align: center; border-color: #8b0000;'>
                    <p style='font-size: 40px; margin-bottom: 20px;'>❌</p>
                    <h2 style='color: #e50914; font-size: 24px; margin-bottom: 15px;'>ACCESO DENEGADO</h2>
                    <p style='color: #b3b3b3; font-size: 13px; margin-bottom: 25px;'>Tu IP no tiene permisos para acceder</p>
                    <p style='color: #888; font-size: 12px;'><strong>Tu IP:</strong> {st.session_state.user_ip_cached}</p>
                    <p style='color: #888; font-size: 12px; margin-top: 15px;'>Contacta al administrador para autorizar tu IP</p>
                </div>
                """, unsafe_allow_html=True)
                st.stop()

    st.stop()

# ============================================================================
# AQUÍ COMIENZA LA APP (SOLO SI ESTÁ LOGUEADO)
# ============================================================================

st.markdown(f"""
    <div style="display:flex; justify-content:space-between; align-items:center;
                background: rgba(17,17,17,0.95); border:1px solid #333; border-radius:10px; padding:12px 18px; margin-bottom:18px;">
        <h2 style='margin:0; color:#e50914;'>📄 Panel</h2>
        <div style="color:#b3b3b3; font-size:12px;">IP: {st.session_state.user_ip_cached}</div>
    </div>
""", unsafe_allow_html=True)

# =========================
# GOOGLE SHEETS (gspread)
# =========================
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
    df.insert(0, "_sheet_row", range(2, 2 + len(df)))  # fila real en Sheets
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
    ws.update([values], range_a1)  # [web:216][web:147]

# Columnas típicas que NO conviene editar porque suelen ser fórmulas
PROTECTED_COLUMNS = {
    "Dias", "Estado", "Fecha de fin", "Perfiles Disponibles", "Logo", "max_perfiles"
}

def vertical_editor(ws_title: str):
    df = read_ws_df(ws_title)

    if df.empty:
        st.warning(f"La hoja '{ws_title}' está vacía.")
        return

    st.dataframe(df.drop(columns=["_sheet_row"]), use_container_width=True)

    sheet_rows = df["_sheet_row"].tolist()
    selected_row = st.selectbox(
        f"Selecciona la fila a editar en '{ws_title}' (número de fila en Google Sheets):",
        sheet_rows,
        key=f"sel_{ws_title}",
    )

    row = df[df["_sheet_row"] == selected_row].iloc[0].to_dict()
    headers = [c for c in df.columns if c != "_sheet_row"]

    with st.form(key=f"form_{ws_title}_{selected_row}"):
        st.markdown("### ✏️ Editar fila (vertical)")
        new_values = {}
        for h in headers:
            if h in PROTECTED_COLUMNS:
                st.text_input(h, value=str(row.get(h, "")), disabled=True)
            else:
                new_values[h] = st.text_input(h, value=str(row.get(h, "")))

        save = st.form_submit_button("💾 Guardar cambios")

    if save:
        final_values = []
        for h in headers:
            if h in PROTECTED_COLUMNS:
                final_values.append(row.get(h, ""))
            else:
                final_values.append(new_values.get(h, ""))

        update_row_in_sheet(ws_title, int(selected_row), headers, final_values)
        st.success("✅ Guardado en Google Sheets.")
        st.cache_data.clear()
        st.rerun()

# =========================
# TABS: Datos / Cuentas
# =========================
tab_datos, tab_cuentas = st.tabs(["Datos", "Cuentas"])
with tab_datos:
    vertical_editor("Datos")
with tab_cuentas:
    vertical_editor("Cuentas")
