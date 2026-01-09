import time
import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from streamlit_javascript import st_javascript

# =========================
# 1) CONFIG + CSS
# =========================
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
.block-container {
    padding-top: 2rem !important;
    padding-bottom: 2rem !important;
    max-width: 100% !important;
}

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

[data-testid="stDataEditor"] {
    background-color: rgba(20,20,20,0.95);
}
</style>
""", unsafe_allow_html=True)

# =========================
# 2) SECRETS
# =========================
try:
    SHEET_URL = st.secrets["general"]["sheet_url"]
    admin_ips_str = st.secrets["general"]["admin_ips"]
    ALLOWED_IPS = [x.strip() for x in admin_ips_str.split(",") if x.strip()]
except Exception:
    st.error("⚠️ Falta configurar [general] sheet_url y admin_ips en secrets.toml")
    st.stop()

# =========================
# 3) LOGIN POR IP
# =========================
def get_my_ip():
    try:
        url = "https://api.ipify.org"
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

# =========================
# 4) HEADER
# =========================
st.markdown(f"""
<div style="display:flex; justify-content:space-between; align-items:center;
            background:rgba(17,17,17,0.96); border:1px solid #333; border-radius:10px;
            padding:12px 18px; margin-bottom:18px;">
  <h2 style="margin:0; color:#e50914;">📺 Panel Streaming</h2>
  <div style="color:#b3b3b3; font-size:12px;">IP: {st.session_state.user_ip_cached}</div>
</div>
""", unsafe_allow_html=True)

# =========================
# 5) GOOGLE SHEETS
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
    df.insert(0, "_sheet_row", range(2, 2 + len(df)))
    return df

def col_to_letter(n: int) -> str:
    letters = ""
    while n:
        n, r = divmod(n - 1, 26)
        letters = chr(65 + r) + letters
    return letters

def update_single_cells(ws_title: str, sheet_row: int, col_indices: list[int], values: list):
    if not col_indices:
        return
    ws = open_ws(ws_title)
    for idx, val in zip(col_indices, values):
        col_letter = col_to_letter(idx + 1)  # A = 1
        a1 = f"{col_letter}{sheet_row}"
        ws.update(a1, [[val]])

def append_ingreso(ws_title: str, valores_dict: dict):
    """
    Para hoja Cuentas: solo escribe columnas editables
    (Plataforma, Suscripcion, Correo, Proveedor, Fecha del pedido, Costo).
    """
    ws = open_ws(ws_title)

    ws.append_row([], value_input_option="USER_ENTERED")

    data = ws.get_all_values()
    last_row = len(data)

    headers = data[0]
    for col_name, value in valores_dict.items():
        if col_name in headers:
            col_index = headers.index(col_name) + 1
            col_letter = col_to_letter(col_index)
            a1 = f"{col_letter}{last_row}"
            ws.update(a1, [[value]])

def append_dato(ws_title: str, valores_dict: dict):
    """
    Para hoja Datos: solo escribe columnas editables
    (las del formulario) y no toca columnas con fórmula ni Logo.
    """
    ws = open_ws(ws_title)

    ws.append_row([], value_input_option="USER_ENTERED")

    data = ws.get_all_values()
    last_row = len(data)

    headers = data[0]
    for col_name, value in valores_dict.items():
        if col_name in headers:
            col_index = headers.index(col_name) + 1
            col_letter = col_to_letter(col_index)
            a1 = f"{col_letter}{last_row}"
            ws.update(a1, [[value]])

def delete_ingreso(ws_title: str, sheet_row: int):
    ws = open_ws(ws_title)
    ws.delete_rows(sheet_row)

def sort_cuentas_por_plataforma():
    ws = open_ws("Cuentas")
    headers = ws.row_values(1)
    if "Plataforma" in headers:
        col_index = headers.index("Plataforma") + 1
        ws.sort((col_index, "asc"))

# =========================
# 6) CONFIG CAMPOS CUENTAS
# =========================
PROTECTED_CUENTAS = {
    "LogoURL",
    "Logo",
    "Estado",
    "Dias",
    "Perfiles Activos",
    "Perfiles Disponibles",
    "Fecha de fin",
}

LIST_COLUMNS_CUENTAS = {"Plataforma", "Suscripcion", "Modalidad", "Proveedor"}
NUMBER_COLUMNS_CUENTAS = {"Costo"}
DATE_COLUMNS_CUENTAS = {"Fecha del pedido"}

@st.dialog("Editar cuenta", width="large")
def dialog_editar_cuenta(sheet_row: int, row_data: dict, df_noidx: pd.DataFrame):
    headers = list(row_data.keys())
    st.write(f"Fila en Google Sheets: **{sheet_row}**")

    new_vals = {}

    for h in headers:
        val = row_data.get(h, "")

        if h in PROTECTED_CUENTAS:
            st.text_input(h, value=str(val), disabled=True)
            continue

        if h in DATE_COLUMNS_CUENTAS:
            s = str(val).strip()
            parsed = None
            if s:
                try:
                    parsed = pd.to_datetime(s, dayfirst=True, errors="raise").date()
                except Exception:
                    try:
                        meses = {
                            "enero": "01","febrero": "02","marzo": "03","abril": "04",
                            "mayo": "05","junio": "06","julio": "07","agosto": "08",
                            "septiembre": "09","setiembre": "09","octubre": "10",
                            "noviembre": "11","diciembre": "12",
                        }
                        s_low = s.lower()
                        partes = s_low.replace(" de ", " ").split()
                        if len(partes) == 3 and partes[1] in meses:
                            dia = partes[0]
                            mes = meses[partes[1]]
                            anio = partes[2]
                            s_norm = f"{dia}/{mes}/{anio}"
                            parsed = pd.to_datetime(s_norm, dayfirst=True, errors="raise").date()
                    except Exception:
                        parsed = None
            new_date = st.date_input(h, value=parsed, key=f"date_{h}_{sheet_row}")
            new_vals[h] = new_date.strftime("%d/%m/%Y") if new_date else ""
            continue

        if h in NUMBER_COLUMNS_CUENTAS:
            s = str(val).strip()
            for ch in ["S/.", "S/ ", "S/", "s/.", "s/ ", "s/"]:
                s = s.replace(ch, "")
            s = s.replace(" ", "").replace(",", ".")
            try:
                num_val = float(s) if s else 0.0
            except Exception:
                num_val = 0.0
            new_num = st.number_input(h, value=num_val, step=1.0, key=f"num_{h}_{sheet_row}")
            new_vals[h] = new_num
            continue

        if h in LIST_COLUMNS_CUENTAS:
            opciones = sorted({x for x in df_noidx[h].unique() if str(x).strip()})
            if val and val not in opciones:
                opciones.append(val)
            default_idx = opciones.index(val) if val in opciones and opciones else 0
            new_sel = st.selectbox(h, opciones, index=default_idx, key=f"sel_{h}_{sheet_row}")
            new_vals[h] = new_sel
            continue

        new_text = st.text_input(h, value=str(val), key=f"txt_{h}_{sheet_row}")
        new_vals[h] = new_text

    if st.button("💾 Guardar cambios", use_container_width=True, key=f"save_{sheet_row}"):
        df_cols = [c for c in df_noidx.columns]
        col_indices = []
        values = []
        for h in df_cols:
            if h in PROTECTED_CUENTAS:
                continue
            if h in new_vals:
                idx = df_cols.index(h)
                col_indices.append(idx)
                values.append(new_vals[h])
        update_single_cells("Cuentas", sheet_row, col_indices, values)
        st.success("✅ Guardado en Google Sheets.")
        st.cache_data.clear()
        time.sleep(1)
        st.rerun()

# =========================
# 7) PANTALLA CUENTAS
# =========================
def pantalla_cuentas():
    df = read_ws_df("Cuentas")
    if df.empty:
        st.warning("La hoja 'Cuentas' está vacía.")
        return

    st.subheader("📄 Cuentas")

    col_ref, col_ord = st.columns([1, 1])
    with col_ref:
        if st.button("🔄 Refrescar tabla", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    with col_ord:
        if st.button("🔤 Ordenar por plataforma", use_container_width=True):
            sort_cuentas_por_plataforma()
            st.success("✅ Cuentas ordenadas por plataforma (A → Z).")
            st.cache_data.clear()
            st.rerun()

    df_noidx = df.drop(columns=["_sheet_row"]).copy()

    # ---------- FORMULARIO NUEVO INGRESO ----------
    st.markdown("### ➕ Nuevo ingreso")

    with st.form("form_nuevo_ingreso"):
        col1, col2, col3 = st.columns(3)

        with col1:
            plataformas_exist = sorted({x for x in df_noidx["Plataforma"].unique() if str(x).strip()})
            plataforma_new = st.selectbox("Plataforma", plataformas_exist)
            suscs_exist = sorted({x for x in df_noidx["Suscripcion"].unique() if str(x).strip()})
            suscripcion_new = st.selectbox("Suscripción", suscs_exist)

        with col2:
            correo_new = st.text_input("Correo")
            proved_exist = sorted({x for x in df_noidx["Proveedor"].unique() if str(x).strip()})
            proveedor_new = st.selectbox("Proveedor", proved_exist)

        with col3:
            fecha_pedido_new = st.date_input("Fecha del pedido")
            costo_new = st.number_input("Costo", min_value=0.0, step=1.0)

        submitted = st.form_submit_button("💾 Guardar nuevo ingreso")

    if submitted:
        valores_dict = {
            "Plataforma": plataforma_new,
            "Suscripcion": suscripcion_new,
            "Correo": correo_new,
            "Proveedor": proveedor_new,
            "Fecha del pedido": fecha_pedido_new.strftime("%d/%m/%Y"),
            "Costo": str(costo_new),
        }

        append_ingreso("Cuentas", valores_dict)
        st.success("✅ Nuevo ingreso agregado.")
        st.cache_data.clear()
        st.rerun()

    st.markdown("---")

    # ---------- TABLA PRINCIPAL ----------
    columnas_visibles = [
        "Plataforma",
        "LogoURL",          # se mostrará como "Logo"
        "Suscripcion",
        "Correo",
        "Estado",
        "Dias",
        "Perfiles Activos",
        "Perfiles Disponibles",
        "Fecha del pedido",
        "Fecha de fin",
        "Costo",
        "Proveedor",
        "Notas",
    ]
    df_vista = df_noidx[columnas_visibles].copy()

    st.data_editor(
        df_vista,
        use_container_width=True,
        disabled=True,
        column_config={
            "LogoURL": st.column_config.ImageColumn("Logo", width="small"),
        },
    )

    # ---------- EDITAR FILA ----------
    opciones = [
        f"{i} · {r.get('Plataforma','')} · {r.get('Correo','')}"
        for i, (_, r) in enumerate(df_noidx.iterrows())
    ]
    mapa_idx = {opt: i for i, opt in enumerate(opciones)}

    st.markdown("#### ✏️ Editar fila")
    col_sel, col_btn = st.columns([3, 1])

    with col_sel:
        seleccion = st.selectbox(
            "Selecciona la fila a editar:",
            opciones,
            index=0 if opciones else None,
            key="cuentas_fila_sel",
        )

    with col_btn:
        if st.button("✏️ Editar", use_container_width=True):
            idx = mapa_idx[seleccion]
            row = df.iloc[idx]
            sheet_row = int(row["_sheet_row"])
            row_data = row.drop(labels=["_sheet_row"]).to_dict()
            dialog_editar_cuenta(sheet_row, row_data, df_noidx)

    # ---------- ELIMINAR INGRESO ----------
    st.markdown("---")
    st.markdown("### 🗑️ Eliminar ingreso")

    opciones_del = [
        f"{int(r['_sheet_row'])} · {r.get('Plataforma','')} · {r.get('Correo','')}"
        for _, r in df.iterrows()
    ]
    mapa_row_del = {
        opt: int(r["_sheet_row"])
        for opt, (_, r) in zip(opciones_del, df.iterrows())
    }

    col_sel_del, col_btn_del = st.columns([3, 1])

    with col_sel_del:
        seleccion_del = st.selectbox(
            "Selecciona la fila a eliminar (Cuentas):",
            opciones_del,
            index=0 if opciones_del else None,
            key="cuentas_fila_del",
        )

    with col_btn_del:
        if st.button("🗑️ Eliminar", use_container_width=True):
            sheet_row_del = mapa_row_del[seleccion_del]
            delete_ingreso("Cuentas", sheet_row_del)
            st.success(f"✅ Ingreso eliminado (fila {sheet_row_del} en 'Cuentas').")
            st.cache_data.clear()
            st.rerun()

# =========================
# 8) PANTALLA DATOS
# =========================
@st.dialog("Editar dato", width="large")
def dialog_editar_dato(sheet_row: int, row_data: dict, df_noidx: pd.DataFrame):
    st.write(f"Fila en Google Sheets (Datos): **{sheet_row}**")

    # Columnas que NO se deben tocar
    protected = {
        "Logo",
        "LogoURL",
        "Estado",
        "Dias Restantes",
        "Fecha de fin",
        "Contraseña",
        "Info Cliente",
    }

    list_columns = {
        "Plataforma",
        "Suscripcion",
        "Combo",
        "Pago",
        "Activación",
        "Proveedor",
    }

    number_columns = {"Costo"}
    date_columns = {"Fecha del pedido"}

    new_vals = {}
    headers = list(row_data.keys())

    for h in headers:
        val = row_data.get(h, "")

        if h in protected:
            st.text_input(h, value=str(val), disabled=True)
            continue

        if h in date_columns:
            s = str(val).strip()
            parsed = None
            if s:
                try:
                    parsed = pd.to_datetime(s, dayfirst=True, errors="raise").date()
                except Exception:
                    parsed = None
            new_date = st.date_input(h, value=parsed, key=f"date_datos_{h}_{sheet_row}")
            new_vals[h] = new_date.strftime("%d/%m/%Y") if new_date else ""
            continue

        if h in number_columns:
            s = str(val).strip().replace(",", ".")
            try:
                num_val = float(s) if s else 0.0
            except Exception:
                num_val = 0.0
            new_num = st.number_input(h, value=num_val, step=1.0, key=f"num_datos_{h}_{sheet_row}")
            new_vals[h] = new_num
            continue

        if h in list_columns:
            opciones = sorted({x for x in df_noidx[h].unique() if str(x).strip()})
            if val and val not in opciones:
                opciones.append(val)
            idx_default = opciones.index(val) if val in opciones and opciones else 0
            new_sel = st.selectbox(h, opciones, index=idx_default, key=f"sel_datos_{h}_{sheet_row}")
            new_vals[h] = new_sel
            continue

        new_text = st.text_input(h, value=str(val), key=f"txt_datos_{h}_{sheet_row}")
        new_vals[h] = new_text

    if st.button("💾 Guardar cambios (Datos)", use_container_width=True, key=f"save_datos_{sheet_row}"):
        df_cols = [c for c in df_noidx.columns]
        col_indices = []
        values = []
        for h in df_cols:
            if h in protected:
                continue
            if h in new_vals:
                idx = df_cols.index(h)
                col_indices.append(idx)
                values.append(new_vals[h])
        update_single_cells("Datos", sheet_row, col_indices, values)
        st.success("✅ Cambios guardados en 'Datos'.")
        st.cache_data.clear()
        time.sleep(1)
        st.rerun()

def pantalla_datos():
    df = read_ws_df("Datos")
    if df.empty:
        st.warning("La hoja 'Datos' está vacía.")
        return

    st.subheader("📄 Datos")

    col_ref, col_ord = st.columns([1, 1])
    with col_ref:
        if st.button("🔄 Refrescar tabla (Datos)", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    def sort_datos_por_plataforma():
        ws = open_ws("Datos")
        headers = ws.row_values(1)
        if "Plataforma" in headers:
            col_index = headers.index("Plataforma") + 1
            ws.sort((col_index, "asc"))

    with col_ord:
        if st.button("🔤 Ordenar Datos por plataforma", use_container_width=True):
            sort_datos_por_plataforma()
            st.success("✅ Datos ordenados por plataforma (A → Z).")
            st.cache_data.clear()
            st.rerun()

    df_noidx = df.drop(columns=["_sheet_row"]).copy()

    # ---------- FORMULARIO NUEVO DATO ----------
    st.markdown("### ➕ Nuevo dato")

    with st.form("form_nuevo_dato"):
        col1, col2, col3 = st.columns(3)

        with col1:
            plataformas_exist = sorted({x for x in df_noidx["Plataforma"].unique() if str(x).strip()})
            plataforma_new = st.selectbox("Plataforma", plataformas_exist)

            suscs_exist = sorted({x for x in df_noidx["Suscripcion"].unique() if str(x).strip()})
            suscripcion_new = st.selectbox("Suscripción", suscs_exist)

            combo_exist = sorted({x for x in df_noidx["Combo"].unique() if str(x).strip()})
            combo_new = st.selectbox("Combo", combo_exist)

        with col2:
            cliente_new = st.text_input("Cliente")
            notas_new = st.text_area("Notas", height=80)

            pago_exist = sorted({x for x in df_noidx["Pago"].unique() if str(x).strip()})
            pago_new = st.selectbox("Pago", pago_exist)

            activ_exist = sorted({x for x in df_noidx["Activación"].unique() if str(x).strip()})
            activ_new = st.selectbox("Activación", activ_exist)

        with col3:
            proved_exist = sorted({x for x in df_noidx["Proveedor"].unique() if str(x).strip()})
            proveedor_new = st.selectbox("Proveedor", proved_exist)

            fecha_pedido_new = st.date_input("Fecha del pedido")

            correo_new = st.text_input("Correo")

            usuario_new = st.text_input("Usuario")
            pin_new = st.text_input("PIN")
            costo_new = st.number_input("Costo", min_value=0.0, step=1.0)

        submitted = st.form_submit_button("💾 Guardar nuevo dato")

    if submitted:
        valores_dict = {
            "Plataforma": plataforma_new,
            "Cliente": cliente_new,
            "Notas": notas_new,
            "Suscripcion": suscripcion_new,
            "Combo": combo_new,
            "Pago": pago_new,
            "Fecha del pedido": fecha_pedido_new.strftime("%d/%m/%Y"),
            "Activación": activ_new,
            "Proveedor": proveedor_new,
            "Correo": correo_new,
            "Usuario": usuario_new,
            "PIN": pin_new,
            "Costo": str(costo_new),
        }

        append_dato("Datos", valores_dict)
        st.success("✅ Nuevo dato agregado.")
        st.cache_data.clear()
        st.rerun()

    st.markdown("---")

    # ---------- TABLA DE DATOS ----------
    columnas_visibles = [
        "Plataforma",
        "LogoURL",
        "Cliente",
        "Notas",
        "Suscripcion",
        "Combo",
        "Pago",
        "Estado",
        "Dias Restantes",
        "Fecha del pedido",
        "Fecha de fin",
        "Activación",
        "Proveedor",
        "Correo",
        "Usuario",
        "PIN",
        "Costo",
        "Info Cliente",
    ]

    df_vista = df_noidx[columnas_visibles].copy()

    st.data_editor(
        df_vista,
        use_container_width=True,
        disabled=True,
        column_config={
            "LogoURL": st.column_config.ImageColumn("Logo", width="small"),
        },
    )
        # ---------- EDITAR DATO ----------
    st.markdown("#### ✏️ Editar dato")

    opciones_edit = [
        f"{i} · {r.get('Plataforma','')} · {r.get('Cliente','')}"
        for i, (_, r) in enumerate(df_noidx.iterrows())
    ]
    mapa_idx_edit = {opt: i for i, opt in enumerate(opciones_edit)}

    col_sel_edit, col_btn_edit = st.columns([3, 1])

    with col_sel_edit:
        seleccion_edit = st.selectbox(
            "Selecciona la fila a editar (Datos):",
            opciones_edit,
            index=0 if opciones_edit else None,
            key="datos_fila_sel",
        )

    with col_btn_edit:
        if st.button("✏️ Editar dato", use_container_width=True):
            idx = mapa_idx_edit[seleccion_edit]
            row = df.iloc[idx]
            sheet_row = int(row["_sheet_row"])
            row_data = row.drop(labels=["_sheet_row"]).to_dict()
            dialog_editar_dato(sheet_row, row_data, df_noidx)

    # ---------- ELIMINAR DATO ----------
    st.markdown("### 🗑️ Eliminar dato")

    opciones_del = [
        f"{int(r['_sheet_row'])} · {r.get('Plataforma','')} · {r.get('Cliente','')}"
        for _, r in df.iterrows()
    ]
    mapa_row_del = {
        opt: int(r["_sheet_row"])
        for opt, (_, r) in zip(opciones_del, df.iterrows())
    }

    col_sel_del, col_btn_del = st.columns([3, 1])

    with col_sel_del:
        seleccion_del = st.selectbox(
            "Selecciona la fila a eliminar (Datos):",
            opciones_del,
            index=0 if opciones_del else None,
            key="datos_fila_del",
        )

    with col_btn_del:
        if st.button("🗑️ Eliminar dato", use_container_width=True):
            sheet_row_del = mapa_row_del[seleccion_del]
            delete_ingreso("Datos", sheet_row_del)
            st.success(f"✅ Dato eliminado (fila {sheet_row_del} en 'Datos').")
            st.cache_data.clear()
            st.rerun()

# =========================
# 9) TABS
# =========================
tab_cuentas, tab_datos = st.tabs(["Cuentas", "Datos"])

with tab_cuentas:
    pantalla_cuentas()

with tab_datos:
    pantalla_datos()
