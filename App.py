import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import date
import time

# Configuración visual
st.set_page_config(page_title="Taller Pro Cloud", layout="wide")

# Intentar la conexión segura con manejo de errores de formato
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error("❌ Error Crítico de Configuración")
    st.info("Revisa los 'Secrets' en Streamlit Cloud. Asegúrate de que la private_key use \\n para los saltos de línea.")
    st.stop()

def cargar_datos(pestana):
    try:
        # Forzamos ttl=0 para datos en tiempo real
        df = conn.read(worksheet=pestana, ttl=0)
        if df is not None:
            df.columns = [str(c).strip() for c in df.columns]
            return df
        return pd.DataFrame()
    except Exception as e:
        if "padding" in str(e).lower():
            st.error("🚨 Error de formato en 'private_key' (Padding).")
        else:
            st.warning(f"No se pudo leer la pestaña {pestana}.")
        return pd.DataFrame()

# --- VALIDACIÓN DE USUARIOS ---
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

df_u = cargar_datos("usuarios")

if not st.session_state.autenticado:
    st.title("🔐 Acceso al Sistema")
    
    if df_u.empty:
        st.warning("Esperando conexión con la base de datos segura...")
        st.stop()
    
    with st.form("login"):
        u = st.text_input("Usuario")
        p = st.text_input("Contraseña", type="password")
        if st.form_submit_button("Entrar"):
            # Validación robusta
            match = df_u[(df_u.iloc[:,0].astype(str) == str(u)) & (df_u.iloc[:,1].astype(str) == str(p))]
            if not match.empty:
                st.session_state.autenticado = True
                st.session_state.usuario = u
                st.rerun()
            else:
                st.error("Credenciales no válidas")
    st.stop()

# --- INTERFAZ DE TRABAJO ---
st.sidebar.success(f"Taller Conectado: {st.session_state.usuario}")

t1, t2 = st.tabs(["⚡ Registro", "🔍 Historial"])

with t1:
    df_rep = cargar_datos("reparaciones")
    c1, c2 = st.columns([1, 2])
    
    with c1:
        st.subheader("Ingreso de Equipo")
        folio = f"T-{len(df_rep)+1:03d}"
        with st.form("nueva_orden", clear_on_submit=True):
            st.code(f"Folio: {folio}")
            cli = st.text_input("Cliente")
            eq = st.text_input("Equipo")
            fa = st.text_area("Falla")
            
            if st.form_submit_button("Registrar"):
                nueva = pd.DataFrame([{
                    "Folio": folio, "Fecha": date.today().strftime("%d/%m/%Y"),
                    "Cliente": cli, "Equipo": eq, "Falla": fa, "Estado": "Recibido"
                }])
                # Guardar usando la conexión de Service Account
                try:
                    conn.update(worksheet="reparaciones", data=pd.concat([df_rep, nueva], ignore_index=True))
                    st.success("✅ ¡Orden Guardada!")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al guardar: {e}")

    with c2:
        st.subheader("Equipos en Taller")
        if not df_rep.empty:
            st.dataframe(df_rep[df_rep["Estado"] != "Entregado"], use_container_width=True)
