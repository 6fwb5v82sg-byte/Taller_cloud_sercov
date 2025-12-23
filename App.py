import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, date
import urllib.parse
import time

# ==========================================
# 1. CONFIGURACIÓN
# ==========================================
st.set_page_config(page_title="Taller Pro Cloud", layout="wide")

# URL limpia (sin parámetros extra)
URL_HOJA = "https://docs.google.com/spreadsheets/d/1--gIzJOWEYBHbjICf8Ca8pjv549G4ATCO8nFZAW4BMQ/edit?usp=sharing"

def conectar_seguro():
    try:
        # Forzamos la conexión usando los secretos del servidor
        return st.connection("gsheets", type=GSheetsConnection)
    except Exception as e:
        st.error(f"Error de configuración en Secrets: {e}")
        return None

conn = conectar_seguro()

def cargar_datos_robusto(pestana):
    try:
        # Intentamos leer la pestaña específica
        df = conn.read(spreadsheet=URL_HOJA, worksheet=pestana, ttl=0)
        if df is not None and not df.empty:
            df.columns = [str(c).strip() for c in df.columns]
            return df
        return pd.DataFrame()
    except:
        # Si falla, intentamos leer la primera hoja por defecto
        try:
            df = conn.read(spreadsheet=URL_HOJA, ttl=0)
            df.columns = [str(c).strip() for c in df.columns]
            return df
        except:
            return pd.DataFrame()

def guardar_datos(df_completo, pestana):
    try:
        conn.update(spreadsheet=URL_HOJA, worksheet=pestana, data=df_completo)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"No se pudo guardar: {e}")
        return False

# ==========================================
# 2. LOGIN Y SEGURIDAD
# ==========================================
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

# Intentamos cargar la tabla de usuarios
df_u = cargar_datos_robusto("usuarios")

if not st.session_state.autenticado:
    st.title("🔐 Acceso al Sistema")
    
    if df_u.empty:
        st.warning("⚠️ El sistema no detecta datos en la nube.")
        st.info("Asegúrate de que tu Google Sheet tenga una pestaña llamada 'usuarios' con datos.")
        # Botón de emergencia para técnicos/desarrollo
        if st.checkbox("¿Usar acceso de emergencia local?"):
            u_emergencia = st.text_input("Usuario Master")
            p_emergencia = st.text_input("Clave Master", type="password")
            if st.button("Entrar con Emergencia"):
                if u_emergencia == "admin" and p_emergencia == "taller2024":
                    st.session_state.autenticado = True
                    st.session_state.usuario = "admin"
                    st.session_state.rol = "admin"
                    st.rerun()
        st.stop()
    
    with st.form("login_form"):
        u = st.text_input("Usuario")
        p = st.text_input("Contraseña", type="password")
        if st.form_submit_button("Entrar"):
            # Validación por columnas (asumiendo 0=usuario, 1=clave)
            try:
                match = df_u[(df_u.iloc[:,0].astype(str) == str(u)) & (df_u.iloc[:,1].astype(str) == str(p))]
                if not match.empty:
                    st.session_state.autenticado = True
                    st.session_state.usuario = u
                    st.session_state.rol = str(match.iloc[0, 2]).lower() if len(match.columns) > 2 else "tecnico"
                    st.rerun()
                else:
                    st.error("Credenciales incorrectas")
            except:
                st.error("Error al procesar la tabla de usuarios")

    st.stop()

# ==========================================
# 3. INTERFAZ (TALLER)
# ==========================================
st.sidebar.success(f"Sesión iniciada: {st.session_state.usuario}")
if st.sidebar.button("Cerrar Sesión"):
    st.session_state.autenticado = False
    st.rerun()

t1, t2 = st.tabs(["⚡ Recepción de Equipos", "🔍 Historial"])

with t1:
    df_rep = cargar_datos_robusto("reparaciones")
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Nueva Orden")
        folio = f"T-{len(df_rep)+1:03d}"
        with st.form("orden", clear_on_submit=True):
            st.code(f"Folio Sugerido: {folio}")
            cli = st.text_input("Cliente")
            tel = st.text_input("WhatsApp")
            eq = st.text_input("Equipo")
            fa = st.text_area("Falla")
            co = st.number_input("Costo", 0.0)
            
            if st.form_submit_button("Registrar"):
                nueva = pd.DataFrame([{"Folio": folio, "Fecha": date.today().strftime("%d/%m/%Y"), "Cliente": cli, "Telefono": tel, "Equipo": eq, "Falla": fa, "Costo": co, "Estado": "Recibido"}])
                if guardar_datos(pd.concat([df_rep, nueva], ignore_index=True), "reparaciones"):
                    st.success("¡Registrado!")
                    time.sleep(1)
                    st.rerun()

    with col2:
        st.subheader("Equipos en Taller")
        if not df_rep.empty:
            df_ed = st.data_editor(df_rep, hide_index=True)
            if st.button("Guardar Cambios"):
                if guardar_datos(df_ed, "reparaciones"):
                    st.success("Sincronizado")
                    st.rerun()

with t2:
    st.subheader("Historial")
    st.dataframe(df_rep, use_container_width=True)
