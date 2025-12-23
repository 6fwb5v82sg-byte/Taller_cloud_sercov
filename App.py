import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, date
import time
import urllib.parse

# ==========================================
# 1. CONFIGURACIÓN Y CONEXIÓN REFORZADA
# ==========================================
st.set_page_config(page_title="Taller Pro Cloud", layout="wide", page_icon="🛠️")

URL_HOJA = "https://docs.google.com/spreadsheets/d/1--gIzJOWEYBHbjICf8Ca8pjv549G4ATCO8nFZAW4BMQ/edit?usp=sharing"

conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos_seguro(nombre_pestana):
    """Intenta cargar datos hasta 3 veces si hay un error de red."""
    for intento in range(3):
        try:
            df = conn.read(spreadsheet=URL_HOJA, worksheet=nombre_pestana, ttl=0)
            if df is not None:
                df.columns = [str(c).strip() for c in df.columns]
                return df
        except Exception:
            time.sleep(1) # Espera un segundo antes de reintentar
    return pd.DataFrame()

def guardar_datos(df_completo, nombre_pestana):
    try:
        if nombre_pestana == "reparaciones":
            # Columnas exactas incluyendo el nuevo Folio
            columnas = ["Folio", "Fecha", "Cliente", "Telefono", "Equipo", "Falla", "Costo", "Abono", "Estado", "Tecnico"]
            for col in columnas:
                if col not in df_completo.columns: df_completo[col] = ""
            df_limpio = df_completo[columnas]
        else:
            df_limpio = df_completo
            
        conn.update(spreadsheet=URL_HOJA, worksheet=nombre_pestana, data=df_limpio)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Error al guardar: {e}")
        return False

# ==========================================
# 2. LOGIN Y SEGURIDAD
# ==========================================
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

df_u = cargar_datos_seguro("usuarios")

if not st.session_state.autenticado:
    st.title("🔐 Acceso Sistema Taller")
    if df_u.empty:
        st.error("Error: No se detecta la pestaña 'usuarios'. Revisa el nombre en Google Sheets.")
        st.stop()
    
    with st.form("login_form"):
        u_in = st.text_input("Usuario")
        p_in = st.text_input("Clave", type="password")
        if st.form_submit_button("Ingresar"):
            match = df_u[(df_u.iloc[:, 0].astype(str) == str(u_in)) & (df_u.iloc[:, 1].astype(str) == str(p_in))]
            if not match.empty:
                st.session_state.autenticado, st.session_state.usuario = True, u_in
                st.session_state.rol = str(match.iloc[0, 2]).lower()
                st.rerun()
            else:
                st.error("Datos incorrectos")
    st.stop()

# ==========================================
# 3. INTERFAZ Y PESTAÑAS
# ==========================================
df_conf = cargar_datos_seguro("config")
config = df_conf.iloc[0].to_dict() if not df_conf.empty else {"nombre": "Mi Taller"}

st.sidebar.title(f"🛠️ {config.get('nombre')}")
if st.sidebar.button("Cerrar Sesión"):
    st.session_state.autenticado = False
    st.rerun()

tab1, tab2, tab3 = st.tabs(["⚡ Taller", "🔍 Historial", "⚙️ Ajustes"])

with tab1:
    df_rep = cargar_datos_seguro("reparaciones")
    
    c1, c2 = st.columns([1, 2])
    with c1:
        st.subheader("Nueva Orden")
        # GENERACIÓN DE FOLIO AUTOMÁTICO
        proximo_folio = len(df_rep) + 1 if not df_rep.empty else 1
        folio_str = f"FT-{proximo_folio:03d}" # Ejemplo: FT-001
        
        st.info(f"Asignando Folio: **{folio_str}**")
        
        with st.form("registro", clear_on_submit=True):
            f_cli, f_tel, f_eq = st.text_input("Cliente"), st.text_input("Teléfono"), st.text_input("Equipo")
            f_fa = st.text_area("Falla")
            f_co, f_ab = st.number_input("Costo", 0.0), st.number_input("Abono", 0.0)
            lista_tec = df_u.iloc[:, 0].tolist() if not df_u.empty else ["General"]
            f_tec = st.selectbox("Técnico", lista_tec)
            
            if st.form_submit_button("Registrar Entrada"):
                nueva = pd.DataFrame([{
                    "Folio": folio_str, "Fecha": date.today().strftime("%Y-%m-%d"),
                    "Cliente": f_cli, "Telefono": f_tel, "Equipo": f_eq,
                    "Falla": f_fa, "Costo": f_co, "Abono": f_ab, 
                    "Estado": "Recibido", "Tecnico": f_tec
                }])
                if guardar_datos(pd.concat([df_rep, nueva], ignore_index=True), "reparaciones"):
                    st.success(f"¡Orden {folio_str} creada!")
                    time.sleep(1)
                    st.rerun()

    with c2:
        st.subheader("Listado de Equipos")
        if not df_rep.empty:
            # WhatsApp con Folio
            sel = st.selectbox("Avisar Cliente:", df_rep.index, format_func=lambda x: f"{df_rep.loc[x, 'Folio']} - {df_rep.loc[x, 'Cliente']}")
            if st.button("📲 Avisar Listo"):
                r = df_rep.loc[sel]
                msj = f"Hola {r['Cliente']}, tu equipo {r['Equipo']} (Folio: {r['Folio']}) está listo en {config.get('nombre')}. Saldo: ${r['Costo']-r['Abono']}."
                st.markdown(f'<a href="https://wa.me/{r["Telefono"]}?text={urllib.parse.quote(msj)}" target="_blank">Enviar WhatsApp</a>', unsafe_allow_html=True)
            
            st.divider()
            df_ed = st.data_editor(df_rep, hide_index=True, use_container_width=True)
            if st.button("Actualizar Todo"):
                if guardar_datos(df_ed, "reparaciones"): st.rerun()

with tab2:
    st.subheader("Buscador")
    busq = st.text_input("Buscar por Folio, Nombre o Equipo:")
    if busq and not df_rep.empty:
        res = df_rep[df_rep.astype(str).apply(lambda x: x.str.contains(busq, case=False)).any(axis=1)]
        st.dataframe(res)

with tab3:
    if st.session_state.rol == "owner":
        with st.form("aj"):
            n, d, t = st.text_input("Nombre", config.get('nombre')), st.text_input("Dir", config.get('dir')), st.text_input("Tel", config.get('tel'))
            if st.form_submit_button("Guardar"):
                if guardar_datos(pd.DataFrame([{"nombre": n, "dir": d, "tel": t}]), "config"): st.rerun()
