import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import date
import time

# Configuración de la interfaz
st.set_page_config(page_title="Sistema Taller Cloud", layout="wide")

def inicializar_conexion():
    try:
        # Intentamos conectar con la Cuenta de Servicio configurada en Secrets
        return st.connection("gsheets", type=GSheetsConnection)
    except Exception as e:
        st.error("❌ Error de conexión con Google Sheets")
        st.info("Revisa que tus Secrets tengan el formato correcto de Service Account.")
        st.stop()

conn = inicializar_conexion()

def cargar_datos_seguros(pestana):
    try:
        # ttl=0 para leer datos frescos siempre
        df = conn.read(worksheet=pestana, ttl=0)
        if df is not None:
            df.columns = [str(c).strip() for c in df.columns]
            return df
        return pd.DataFrame()
    except Exception as e:
        error_str = str(e).lower()
        if "padding" in error_str:
            st.error("🚨 Error de Formato: La 'private_key' en tus Secrets tiene un error de padding (revisa los saltos de línea \\n).")
        elif "not found" in error_str:
            st.warning(f"⚠️ La pestaña '{pestana}' no existe en tu Google Sheet.")
        else:
            st.error(f"Error inesperado: {e}")
        return pd.DataFrame()

# ==========================================
# FLUJO DE ACCESO
# ==========================================
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

# Intentamos cargar usuarios al inicio
df_usuarios = cargar_datos_seguros("usuarios")

if not st.session_state.autenticado:
    st.title("🔐 Acceso al Sistema")
    
    if df_usuarios.empty:
        st.warning("Conectando con la base de datos segura... Si este mensaje no desaparece, revisa tus credenciales.")
        if st.button("🔄 Forzar Reintento"):
            st.rerun()
        st.stop()
    
    with st.form("login_form"):
        user_input = st.text_input("Usuario")
        pass_input = st.text_input("Contraseña", type="password")
        if st.form_submit_button("Ingresar"):
            # Validación comparando la columna 0 (usuario) y 1 (clave)
            credenciales = df_usuarios[(df_usuarios.iloc[:,0].astype(str) == user_input) & 
                                     (df_usuarios.iloc[:,1].astype(str) == pass_input)]
            if not credenciales.empty:
                st.session_state.autenticado = True
                st.session_state.usuario = user_input
                st.rerun()
            else:
                st.error("Credenciales incorrectas")
    st.stop()

# ==========================================
# PANEL DE CONTROL (TALLER)
# ==========================================
st.sidebar.success(f"Conectado: {st.session_state.usuario}")
if st.sidebar.button("Cerrar Sesión"):
    st.session_state.autenticado = False
    st.rerun()

tab_registro, tab_historial = st.tabs(["⚡ Registro de Equipos", "🔍 Historial"])

with tab_registro:
    df_reparaciones = cargar_datos_seguros("reparaciones")
    col_form, col_tabla = st.columns([1, 2])
    
    with col_form:
        st.subheader("Nueva Orden")
        folio_sugerido = f"T-{len(df_reparaciones) + 1:03d}"
        with st.form("form_registro", clear_on_submit=True):
            st.code(f"Folio: {folio_sugerido}")
            cliente = st.text_input("Nombre del Cliente")
            equipo = st.text_input("Equipo / Modelo")
            falla = st.text_area("Descripción de la Falla")
            
            if st.form_submit_button("Guardar en la Nube"):
                nueva_fila = pd.DataFrame([{
                    "Folio": folio_sugerido, 
                    "Fecha": date.today().strftime("%d/%m/%Y"),
                    "Cliente": cliente, 
                    "Equipo": equipo, 
                    "Falla": falla, 
                    "Estado": "Recibido"
                }])
                
                try:
                    # Actualización usando la conexión segura
                    df_final = pd.concat([df_reparaciones, nueva_fila], ignore_index=True)
                    conn.update(worksheet="reparaciones", data=df_final)
                    st.success("✅ ¡Datos guardados exitosamente!")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al escribir en la hoja: {e}")

    with col_tabla:
        st.subheader("Equipos en Proceso")
        if not df_reparaciones.empty:
            st.dataframe(df_reparaciones[df_reparaciones["Estado"] != "Entregado"], 
                         use_container_width=True, hide_index=True)

with tab_historial:
    st.subheader("Historial Completo")
    st.dataframe(df_reparaciones, use_container_width=True)
