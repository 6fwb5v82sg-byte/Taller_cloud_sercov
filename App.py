import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import date
from fpdf import FPDF

# ==========================================
# 1. CONFIGURACIÓN DE CONEXIÓN
# ==========================================
# Asegúrate de que el enlace sea "Cualquier persona con el enlace puede EDITAR"
URL_HOJA = "https://docs.google.com/spreadsheets/d/1--gIzJOWEYBHbjICf8Ca8pjv549G4ATCO8nFZAW4BMQ/edit?usp=sharing"

conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_tabla(nombre_pestana):
    try:
        # Usamos ttl=0 para evitar que Streamlit guarde datos viejos en memoria
        df = conn.read(spreadsheet=URL_HOJA, worksheet=nombre_pestana, ttl=0)
        if df is not None:
            df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Error cargando '{nombre_pestana}': {e}")
        return pd.DataFrame()

def actualizar_tabla_completa(df_completo, nombre_pestana):
    try:
        conn.update(spreadsheet=URL_HOJA, worksheet=nombre_pestana, data=df_completo)
        # IMPORTANTE: Limpiar el caché específico de esta función
        st.cache_data.clear() 
        st.success("✅ Base de datos actualizada con éxito")
    except Exception as e:
        st.error(f"Error al guardar: {e}")

# ==========================================
# 2. SEGURIDAD Y LOGIN
# ==========================================
st.set_page_config(page_title="Gestión Taller Cloud", layout="wide")

if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.title("🔐 Acceso al Sistema Taller")
    users_df = cargar_tabla("usuarios")
    
    u = st.text_input("Usuario")
    p = st.text_input("Contraseña", type="password")
    
    if st.button("Iniciar Sesión"):
        if not users_df.empty:
            # Validación robusta de credenciales
            valid = users_df[(users_df.iloc[:, 0].astype(str) == str(u)) & 
                             (users_df.iloc[:, 1].astype(str) == str(p))]
            if not valid.empty:
                st.session_state.autenticado = True
                st.session_state.usuario = u
                st.session_state.rol = str(valid.iloc[0, 2]).lower()
                st.rerun()
            else:
                st.error("Usuario o clave incorrectos")
        else:
            st.error("No se pudo leer la tabla de usuarios.")
    st.stop()

# ==========================================
# 3. INTERFAZ PRINCIPAL
# ==========================================
# Cargar configuración del taller
conf_df = cargar_tabla("config")
config = conf_df.iloc[0].to_dict() if not conf_df.empty else {"nombre": "Mi Taller"}

st.sidebar.title(f"🛠️ {config.get('nombre')}")
st.sidebar.write(f"Usuario: **{st.session_state.usuario}** ({st.session_state.rol})")

if st.sidebar.button("Cerrar Sesión"):
    st.session_state.autenticado = False
    st.rerun()

tabs = st.tabs(["⚡ Taller", "📊 Finanzas", "🔍 Garantías", "⚙️ Ajustes"])

with tabs[0]: 
    df_rep = cargar_tabla("reparaciones")
    c1, c2 = st.columns([1, 2])
    
    with c1:
        st.subheader("Nueva Orden")
        with st.form("registro", clear_on_submit=True):
            cli = st.text_input("Cliente")
            tel = st.text_input("WhatsApp")
            eq = st.text_input("Equipo")
            fl = st.text_area("Falla")
            co = st.number_input("Costo $", min_value=0.0)
            ab = st.number_input("Abono $", min_value=0.0)
            
            if st.form_submit_button("Registrar"):
                nueva_fila = pd.DataFrame([{
                    "Fecha": date.today().strftime("%Y-%m-%d"),
                    "Cliente": cli, "Telefono": tel, "Equipo": eq,
                    "Falla": fl, "Costo": co, "Abono": ab, "Estado": "Recibido"
                }])
                df_final = pd.concat([df_rep, nueva_fila], ignore_index=True)
                actualizar_tabla_completa(df_final, "reparaciones")
                st.rerun()

    with c2:
        st.subheader("Equipos en Taller")
        if not df_rep.empty:
            # Editamos el DataFrame directamente
            df_editado = st.data_editor(df_rep, hide_index=True, key="editor_taller")
            
            if st.button("Guardar Cambios en Lista"):
                actualizar_tabla_completa(df_editado, "reparaciones")
                st.rerun()
