import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import date
import urllib.parse
import time

# Configuración básica
st.set_page_config(page_title="Taller Pro Cloud", layout="wide")

# Conexión principal (usa automáticamente los Secrets de Service Account)
conn = st.connection("gsheets", type=GSheetsConnection)

# Funciones de datos simplificadas
def cargar_datos(pestana):
    try:
        return conn.read(worksheet=pestana, ttl=0)
    except Exception as e:
        st.error(f"Error cargando {pestana}: {e}")
        return pd.DataFrame()

def guardar_datos(df, pestana):
    try:
        conn.update(worksheet=pestana, data=df)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Error al guardar: {e}")
        return False

# --- GESTIÓN DE ACCESO ---
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

df_u = cargar_datos("usuarios")

if not st.session_state.autenticado:
    st.title("🔐 Acceso al Sistema")
    if df_u.empty:
        st.warning("Verificando conexión segura...")
        st.stop()
    
    with st.form("login_form"):
        u = st.text_input("Usuario")
        p = st.text_input("Clave", type="password")
        if st.form_submit_button("Entrar"):
            # Validación simple por columnas
            match = df_u[(df_u.iloc[:,0].astype(str) == str(u)) & (df_u.iloc[:,1].astype(str) == str(p))]
            if not match.empty:
                st.session_state.autenticado = True
                st.session_state.usuario = u
                st.rerun()
            else:
                st.error("Credenciales incorrectas")
    st.stop()

# --- PANEL PRINCIPAL ---
st.sidebar.info(f"Usuario: {st.session_state.usuario}")
if st.sidebar.button("Cerrar Sesión"):
    st.session_state.autenticado = False
    st.rerun()

t1, t2 = st.tabs(["⚡ Registro Taller", "🔍 Historial de Servicios"])

with t1:
    df_rep = cargar_datos("reparaciones")
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Nueva Orden")
        nuevo_folio = f"T-{len(df_rep)+1:03d}"
        with st.form("registro", clear_on_submit=True):
            st.code(f"Folio: {nuevo_folio}")
            cliente = st.text_input("Cliente")
            telefono = st.text_input("WhatsApp")
            equipo = st.text_input("Equipo")
            falla = st.text_area("Falla")
            
            if st.form_submit_button("Registrar"):
                nueva_orden = pd.DataFrame([{
                    "Folio": nuevo_folio, 
                    "Fecha": date.today().strftime("%d/%m/%Y"), 
                    "Cliente": cliente, 
                    "Telefono": telefono, 
                    "Equipo": equipo, 
                    "Falla": falla, 
                    "Estado": "Recibido"
                }])
                if guardar_datos(pd.concat([df_rep, nueva_orden], ignore_index=True), "reparaciones"):
                    st.success("✅ Orden registrada en la nube")
                    time.sleep(1)
                    st.rerun()

    with col2:
        st.subheader("Equipos en Taller")
        if not df_rep.empty:
            # Mostrar solo los que no están entregados
            df_activos = df_rep[df_rep["Estado"] != "Entregado"]
            df_edit = st.data_editor(df_activos, hide_index=True, use_container_width=True)
            
            if st.button("Guardar Cambios de Estado"):
                # Combinar con los datos históricos para no perder nada
                df_final = pd.concat([df_rep[df_rep["Estado"] == "Entregado"], df_edit]).drop_duplicates(subset="Folio", keep="last")
                if guardar_datos(df_final, "reparaciones"):
                    st.success("Sincronización completa")
                    st.rerun()

with t2:
    st.subheader("Buscador de Historial")
    st.dataframe(df_rep, use_container_width=True)
