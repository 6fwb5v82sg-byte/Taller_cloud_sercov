import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import date
import urllib.parse
import time

# Configuración de página
st.set_page_config(page_title="Taller Pro Cloud", layout="wide")

# Conexión Segura
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"Error de conexión: Verifica que los Secrets estén bien pegados. Detalle: {e}")
    st.stop()

def cargar_datos(pestana):
    try:
        # Intentamos leer la pestaña; si falla por padding, capturamos el error
        df = conn.read(worksheet=pestana, ttl=0)
        if df is not None:
            df.columns = [str(c).strip() for c in df.columns]
            return df
        return pd.DataFrame()
    except Exception as e:
        if "padding" in str(e).lower():
            st.error("❌ Error de formato en la 'private_key' dentro de Secrets. Revisa los saltos de línea.")
        else:
            st.warning(f"No se pudo leer la pestaña '{pestana}': {e}")
        return pd.DataFrame()

def guardar_datos(df, pestana):
    try:
        conn.update(worksheet=pestana, data=df)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"No se pudo guardar: {e}")
        return False

# --- VALIDACIÓN DE ACCESO ---
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

df_u = cargar_datos("usuarios")

if not st.session_state.autenticado:
    st.title("🔐 Acceso al Sistema")
    
    if df_u.empty:
        st.info("Verificando credenciales de seguridad...")
        st.stop()
    
    with st.form("login"):
        u = st.text_input("Usuario")
        p = st.text_input("Clave", type="password")
        if st.form_submit_button("Entrar"):
            # Comparación robusta convirtiendo a string
            match = df_u[(df_u.iloc[:,0].astype(str) == str(u)) & (df_u.iloc[:,1].astype(str) == str(p))]
            if not match.empty:
                st.session_state.autenticado = True
                st.session_state.usuario = u
                st.rerun()
            else:
                st.error("Usuario o clave incorrectos")
    st.stop()

# --- INTERFAZ PRINCIPAL (TALLER) ---
st.sidebar.success(f"Conectado como: {st.session_state.usuario}")
t1, t2 = st.tabs(["⚡ Taller", "🔍 Historial"])

with t1:
    df_rep = cargar_datos("reparaciones")
    c1, c2 = st.columns([1, 2])
    
    with c1:
        st.subheader("Nueva Orden")
        folio = f"T-{len(df_rep)+1:03d}"
        with st.form("reg", clear_on_submit=True):
            cli = st.text_input("Cliente")
            tel = st.text_input("WhatsApp")
            eq = st.text_input("Equipo")
            fa = st.text_area("Falla")
            if st.form_submit_button("Registrar Equipo"):
                nueva = pd.DataFrame([{
                    "Folio": folio, 
                    "Fecha": date.today().strftime("%d/%m/%Y"), 
                    "Cliente": cli, 
                    "Telefono": tel, 
                    "Equipo": eq, 
                    "Falla": fa, 
                    "Estado": "Recibido"
                }])
                if guardar_datos(pd.concat([df_rep, nueva], ignore_index=True), "reparaciones"):
                    st.success("✅ Guardado en la nube")
                    time.sleep(1)
                    st.rerun()

    with c2:
        st.subheader("Equipos en Taller")
        if not df_rep.empty:
            df_activos = df_rep[df_rep["Estado"] != "Entregado"]
            df_ed = st.data_editor(df_activos, hide_index=True, use_container_width=True)
            if st.button("Sincronizar Estados"):
                df_hist = df_rep[df_rep["Estado"] == "Entregado"]
                df_final = pd.concat([df_hist, df_ed]).drop_duplicates(subset="Folio", keep="last")
                if guardar_datos(df_final, "reparaciones"):
                    st.success("Nube actualizada")
                    st.rerun()
