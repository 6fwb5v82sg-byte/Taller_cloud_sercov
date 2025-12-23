import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import date
import time

# Configuración de la aplicación
st.set_page_config(page_title="Taller Pro Cloud", layout="wide")

# Intento de conexión centralizado
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error("❌ Error en la configuración de Secrets (private_key)")
    st.stop()

def cargar_datos(pestana):
    try:
        # ttl=0 asegura que siempre leas los datos más recientes
        return conn.read(worksheet=pestana, ttl=0)
    except Exception as e:
        if "padding" in str(e).lower():
            st.error("🚨 Error de 'Padding': La llave privada en Secrets está mal formateada.")
        return pd.DataFrame()

# --- SISTEMA DE LOGUEO ---
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

df_u = cargar_datos("usuarios")

if not st.session_state.autenticado:
    st.title("🔐 Acceso al Sistema")
    
    if df_u.empty:
        st.warning("Conectando con la base de datos segura...")
        st.stop()
    
    with st.form("login"):
        u = st.text_input("Usuario")
        p = st.text_input("Contraseña", type="password")
        if st.form_submit_button("Ingresar"):
            # Validación comparando como texto
            match = df_u[(df_u.iloc[:,0].astype(str) == str(u)) & (df_u.iloc[:,1].astype(str) == str(p))]
            if not match.empty:
                st.session_state.autenticado = True
                st.session_state.usuario = u
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos")
    st.stop()

# --- PANEL DE TRABAJO ---
st.sidebar.success(f"Usuario: {st.session_state.usuario}")
if st.sidebar.button("Cerrar Sesión"):
    st.session_state.autenticado = False
    st.rerun()

t1, t2 = st.tabs(["⚡ Registro", "🔍 Historial"])

with t1:
    df_rep = cargar_datos("reparaciones")
    c1, c2 = st.columns([1, 2])
    
    with c1:
        st.subheader("Nueva Orden")
        folio = f"T-{len(df_rep)+1:03d}"
        with st.form("nueva_orden", clear_on_submit=True):
            cli = st.text_input("Cliente")
            eq = st.text_input("Equipo")
            fa = st.text_area("Falla")
            if st.form_submit_button("Guardar"):
                nueva = pd.DataFrame([{
                    "Folio": folio, "Fecha": date.today().strftime("%d/%m/%Y"),
                    "Cliente": cli, "Equipo": eq, "Falla": fa, "Estado": "Recibido"
                }])
                try:
                    # Guardado directo en la nube
                    conn.update(worksheet="reparaciones", data=pd.concat([df_rep, nueva], ignore_index=True))
                    st.success("✅ ¡Registrado en Google Sheets!")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al guardar: {e}")

    with c2:
        st.subheader("Equipos en Taller")
        if not df_rep.empty:
            st.dataframe(df_rep[df_rep["Estado"] != "Entregado"], use_container_width=True, hide_index=True)
