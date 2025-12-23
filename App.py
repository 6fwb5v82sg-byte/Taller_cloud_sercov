import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, date
import urllib.parse
import time

# ==========================================
# 1. CONFIGURACIÓN Y DIAGNÓSTICO
# ==========================================
st.set_page_config(page_title="Taller Pro Cloud", layout="wide")

# URL DIRECTA (Asegúrate que termine en /edit?usp=sharing)
URL_HOJA = "https://docs.google.com/spreadsheets/d/1--gIzJOWEYBHbjICf8Ca8pjv549G4ATCO8nFZAW4BMQ/edit?usp=sharing"

def conectar_y_diagnosticar():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        # Intentamos una lectura de prueba
        test = conn.read(spreadsheet=URL_HOJA, worksheet="usuarios", ttl=0)
        return conn, None
    except Exception as e:
        return None, e

conn, error_conexion = conectar_y_diagnosticar()

if error_conexion:
    st.error("❌ ERROR DE CONEXIÓN CON GOOGLE SHEETS")
    st.info(f"Detalle técnico: {error_conexion}")
    st.markdown("""
    **Cómo solucionar esto ahora mismo:**
    1. Abre tu Google Sheet.
    2. Botón **Compartir** (derecha arriba).
    3. Asegúrate que diga: **'Cualquier persona con el enlace'** y el rol sea **'Editor'**.
    4. Verifica que la pestaña se llame `usuarios` (en minúsculas).
    """)
    st.stop()

# ==========================================
# 2. FUNCIONES DE CARGA Y GUARDADO
# ==========================================
def cargar_datos(pestana):
    try:
        df = conn.read(spreadsheet=URL_HOJA, worksheet=pestana, ttl=0)
        if df is not None:
            df.columns = [str(c).strip() for c in df.columns]
            return df
        return pd.DataFrame()
    except:
        return pd.DataFrame()

def guardar_datos(df_completo, pestana):
    try:
        if pestana == "reparaciones":
            columnas = ["Folio", "Fecha", "Cliente", "Telefono", "Equipo", "Falla", "Costo", "Abono", "Estado", "Tecnico"]
            for col in columnas:
                if col not in df_completo.columns: df_completo[col] = ""
            df_limpio = df_completo[columnas]
        else:
            df_limpio = df_completo
            
        conn.update(spreadsheet=URL_HOJA, worksheet=pestana, data=df_limpio)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Error al guardar en '{pestana}': {e}")
        return False

# ==========================================
# 3. SEGURIDAD Y LOGIN
# ==========================================
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

df_u = cargar_datos("usuarios")

if not st.session_state.autenticado:
    st.title("🔐 Acceso Sistema Taller")
    if df_u.empty:
        st.warning("⚠️ No se encuentran datos en la pestaña 'usuarios'.")
        st.stop()
    
    with st.form("login"):
        user = st.text_input("Usuario")
        pw = st.text_input("Clave", type="password")
        if st.form_submit_button("Entrar"):
            # Validación robusta
            match = df_u[(df_u.iloc[:,0].astype(str) == str(user)) & (df_u.iloc[:,1].astype(str) == str(pw))]
            if not match.empty:
                st.session_state.autenticado = True
                st.session_state.usuario = user
                st.session_state.rol = str(match.iloc[0, 2]).lower()
                st.rerun()
            else:
                st.error("Usuario o clave incorrectos")
    st.stop()

# ==========================================
# 4. INTERFAZ (TALLER Y FOLIOS)
# ==========================================
df_conf = cargar_datos("config")
config = df_conf.iloc[0].to_dict() if not df_conf.empty else {"nombre": "Mi Taller"}

st.sidebar.title(f"🛠️ {config.get('nombre')}")
if st.sidebar.button("Cerrar Sesión"):
    st.session_state.autenticado = False
    st.rerun()

t1, t2, t3 = st.tabs(["⚡ Taller", "🔍 Historial", "⚙️ Ajustes"])

with t1:
    df_rep = cargar_datos("reparaciones")
    c1, c2 = st.columns([1, 2])
    
    with c1:
        st.subheader("Nueva Orden")
        folio = f"T-{len(df_rep)+1:03d}"
        st.code(f"Folio sugerido: {folio}")
        with st.form("reg", clear_on_submit=True):
            cli = st.text_input("Cliente")
            tel = st.text_input("WhatsApp")
            eq = st.text_input("Equipo")
            fa = st.text_area("Falla")
            co = st.number_input("Costo", 0.0)
            ab = st.number_input("Abono", 0.0)
            tec = st.selectbox("Técnico", df_u.iloc[:,0].tolist() if not df_u.empty else ["Gral"])
            
            if st.form_submit_button("Registrar"):
                nueva = pd.DataFrame([{"Folio": folio, "Fecha": date.today().strftime("%Y-%m-%d"), "Cliente": cli, "Telefono": tel, "Equipo": eq, "Falla": fa, "Costo": co, "Abono": ab, "Estado": "Recibido", "Tecnico": tec}])
                if guardar_datos(pd.concat([df_rep, nueva], ignore_index=True), "reparaciones"):
                    st.success("✅ ¡Orden Guardada!")
                    time.sleep(1)
                    st.rerun()
    
    with c2:
        st.subheader("Equipos en Taller")
        if not df_rep.empty:
            df_ed = st.data_editor(df_rep, hide_index=True, use_container_width=True)
            if st.button("Guardar Cambios de Tabla"):
                if guardar_datos(df_ed, "reparaciones"):
                    st.success("Sincronizado!")
                    st.rerun()
