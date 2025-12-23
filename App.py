import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import date
import time

# ==========================================
# 1. CONFIGURACIÓN INICIAL
# ==========================================
st.set_page_config(page_title="Gestión Taller Cloud", layout="wide")

# URL de tu hoja (Asegúrate de que esté compartida como "Editor")
URL_HOJA = "https://docs.google.com/spreadsheets/d/1--gIzJOWEYBHbjICf8Ca8pjv549G4ATCO8nFZAW4BMQ/edit?usp=sharing"

# Establecer conexión
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_tabla(nombre_pestana):
    """Carga datos de una pestaña específica con manejo de errores."""
    try:
        # Forzamos la lectura sin caché para evitar datos viejos
        df = conn.read(spreadsheet=URL_HOJA, worksheet=nombre_pestana, ttl=0)
        if df is not None:
            df.columns = [str(c).strip() for c in df.columns]
            return df
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error cargando la pestaña '{nombre_pestana}': {e}")
        return pd.DataFrame()

def guardar_datos(df_completo, nombre_pestana):
    """Sobreescribe la pestaña con el nuevo DataFrame."""
    try:
        conn.update(spreadsheet=URL_HOJA, worksheet=nombre_pestana, data=df_completo)
        st.cache_data.clear()
        st.success(f"✅ Datos en '{nombre_pestana}' actualizados.")
        time.sleep(1) # Pausa breve para asegurar la escritura en Google
        return True
    except Exception as e:
        st.error(f"No se pudo guardar en Google Sheets: {e}")
        return False

# ==========================================
# 2. SISTEMA DE AUTENTICACIÓN
# ==========================================
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.title("🔐 Acceso al Sistema Taller")
    
    users_df = cargar_tabla("usuarios")
    
    col1, col2 = st.columns(2)
    with col1:
        u = st.text_input("Usuario")
        p = st.text_input("Contraseña", type="password")
        
        if st.button("Entrar"):
            if not users_df.empty:
                # Verificamos credenciales en las primeras dos columnas
                user_match = users_df[(users_df.iloc[:, 0].astype(str) == str(u)) & 
                                     (users_df.iloc[:, 1].astype(str) == str(p))]
                
                if not user_match.empty:
                    st.session_state.autenticado = True
                    st.session_state.usuario = u
                    st.session_state.rol = str(user_match.iloc[0, 2]).lower()
                    st.rerun()
                else:
                    st.error("Credenciales incorrectas")
            else:
                st.error("Error: La tabla de usuarios está vacía o no es accesible.")
    st.stop()

# ==========================================
# 3. INTERFAZ PRINCIPAL (Solo si logueado)
# ==========================================

# Carga de configuración inicial
conf_df = cargar_tabla("config")
if not conf_df.empty:
    config = conf_df.iloc[0].to_dict()
else:
    config = {"nombre": "Mi Taller", "dir": "Ciudad", "tel": "000"}

st.sidebar.title(f"🛠️ {config.get('nombre')}")
st.sidebar.write(f"Usuario: **{st.session_state.usuario}**")
if st.sidebar.button("Cerrar Sesión"):
    st.session_state.autenticado = False
    st.rerun()

tabs = st.tabs(["⚡ Taller", "📊 Finanzas", "🔍 Garantías", "⚙️ Ajustes"])

# --- TAB TALLER ---
with tabs[0]:
    df_rep = cargar_tabla("reparaciones")
    
    c1, c2 = st.columns([1, 2])
    with c1:
        st.subheader("Nueva Orden")
        with st.form("registro_form", clear_on_submit=True):
            cli = st.text_input("Cliente")
            tel = st.text_input("WhatsApp")
            eq = st.text_input("Equipo")
            fl = st.text_area("Falla")
            co = st.number_input("Costo $", min_value=0.0)
            ab = st.number_input("Abono $", min_value=0.0)
            
            if st.form_submit_button("Registrar Equipo"):
                nueva_data = {
                    "Fecha": date.today().strftime("%Y-%m-%d"),
                    "Cliente": cli, "Telefono": tel, "Equipo": eq,
                    "Falla": fl, "Costo": co, "Abono": ab, "Estado": "Recibido"
                }
                # Creamos el nuevo DataFrame con la nueva fila
                df_actualizado = pd.concat([df_rep, pd.DataFrame([nueva_data])], ignore_index=True)
                if guardar_datos(df_actualizado, "reparaciones"):
                    st.rerun()

    with c2:
        st.subheader("Equipos en Taller")
        if not df_rep.empty:
            # Filtramos para no mostrar entregados si se desea, o mostramos todo
            df_editado = st.data_editor(df_rep, hide_index=True, key="editor_taller")
            
            if st.button("Confirmar Cambios en Tabla"):
                if guardar_datos(df_editado, "reparaciones"):
                    st.rerun()
        else:
            st.info("No hay equipos registrados aún.")

# --- TAB FINANZAS ---
with tabs[1]:
    if st.session_state.rol in ["admin", "owner"]:
        st.subheader("Historial y Balances")
        st.dataframe(df_rep, use_container_width=True)
    else:
        st.warning("Acceso restringido a administradores.")

# --- TAB AJUSTES ---
with tabs[3]:
    if st.session_state.rol == "owner":
        st.subheader("Configuración del Negocio")
        with st.form("ajustes_form"):
            nuevo_nom = st.text_input("Nombre", config.get('nombre'))
            nueva_dir = st.text_input("Dirección", config.get('dir'))
            nuevo_tel = st.text_input("Teléfono", config.get('tel'))
            
            if st.form_submit_button("Guardar Configuración"):
                df_conf_nueva = pd.DataFrame([{"nombre": nuevo_nom, "dir": nueva_dir, "tel": nuevo_tel}])
                if guardar_datos(df_conf_nueva, "config"):
                    st.rerun()
