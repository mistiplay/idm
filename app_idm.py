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
def dialog_editar_cuenta(sheet_row: int, row_data: dict, df: pd.DataFrame):
    headers = [c for c in df.columns if c != "_sheet_row"]

    st.write(f"Fila en Google Sheets: **{sheet_row}**")

    new_vals = {}
    for h in headers:
        val = row_data.get(h, "")

        if h in PROTECTED_CUENTAS:
            st.text_input(h, value=str(val), disabled=True)
            continue

        if h in DATE_COLUMNS_CUENTAS:
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
            default_idx = opciones.index(val) if val in opciones and opciones else 0
            new_sel = st.selectbox(h, opciones, index=default_idx)
            new_vals[h] = new_sel

        else:
            new_text = st.text_input(h, value=str(val))
            new_vals[h] = new_text

    if st.button("💾 Guardar cambios", use_container_width=True):
        final_values = []
        for h in headers:
            if h in PROTECTED_CUENTAS:
                final_values.append(row_data.get(h, ""))
            else:
                final_values.append(new_vals.get(h, ""))

        update_row_in_sheet("Cuentas", sheet_row, headers, final_values)
        st.success("✅ Guardado en Google Sheets.")
        st.cache_data.clear()
        time.sleep(1)
        st.rerun()


def pantalla_cuentas():
    df = read_ws_df("Cuentas")
    if df.empty:
        st.warning("La hoja 'Cuentas' está vacía.")
        return

    st.subheader("📄 Cuentas")

    # Vista para tabla (sin _sheet_row, sin acción)
    df_view = df.drop(columns=["_sheet_row"]).copy()

    st.data_editor(
        df_view,
        use_container_width=True,
        disabled=True,  # solo lectura, para que no se edite directamente
    )

    # Selector compacto para elegir fila + botón ✏️
    opciones = [
        f"Fila {int(r['_sheet_row'])} · {r.get('Plataforma','')} · {r.get('Correo','')}"
        for _, r in df.iterrows()
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
            row_data = row.to_dict()
            dialog_editar_cuenta(sheet_row, row_data, df)
