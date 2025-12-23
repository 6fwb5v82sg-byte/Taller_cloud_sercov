import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, date
import urllib.parse
import time

# 1. CONFIGURACIÓN
st.set_page_config(page_title="Taller Pro Cloud", layout="wide")

# URL de tu hoja (Asegúrate que sea 'Cualquier persona con el enlace' y 'Editor')
URL_HOJA = "https://docs.google.com/spreadsheets/d/1--gIzJOWEYBHbjICf8Ca8pjv549G4ATCO8nFZAW4BMQ/edit?usp=sharing"

def conectar():
    try:
        return st.connection("gsheets", type=GSheetsConnection)
    except Exception as e:
        st.error(f"Error de configuración en Secrets: {e}")
        return None

conn = conectar()

def cargar_datos(pestana):
    try:
        # ttl=0 es clave para ver cambios inmediatos
        df = conn.read(spreadsheet=URL_HOJA, worksheet=pestana, ttl=0)
        if df is not None:
            df.columns = [str(c).strip() for c in df.columns]
            return df
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()

def guardar_datos(df_completo, pestana):
    try:
        conn.update(spreadsheet=URL_HOJA, worksheet=pestana, data=df_completo)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Error al guardar: {e}")
        return False

# 2. LOGIN Y SEGURIDAD
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

df_u = cargar_datos("usuarios")

if not st.session_state.autenticado:
    st.title("🔐 Acceso al Sistema")
    
    if df_u.empty:
        st.error("⚠️ No se pudo leer la pestaña 'usuarios'.")
        st.info("Verifica que en tu Google Sheet la pestaña se llame exactamente 'usuarios' y tenga al menos una fila con datos.")
        if st.button("🔄 Reintentar Conexión"):
            st.rerun()
        st.stop()
    
    with st.form("login"):
        u = st.text_input("Usuario")
        p = st.text_input("Clave", type="password")
        if st.form_submit_button("Entrar"):
            # Comparamos usuario (columna 0) y clave (columna 1)
            match = df_u[(df_u.iloc[:,0].astype(str) == str(u)) & (df_u.iloc[:,1].astype(str) == str(p))]
            if not match.empty:
                st.session_state.autenticado = True
                st.session_state.usuario = u
                st.session_state.rol = str(match.iloc[0, 2]).lower() if len(match.columns) > 2 else "tecnico"
                st.rerun()
            else:
                st.error("Usuario o clave incorrectos")
    st.stop()

# 3. INTERFAZ PRINCIPAL
df_conf = cargar_datos("config")
nombre_taller = df_conf.iloc[0,0] if not df_conf.empty else "Mi Taller Cloud"

st.sidebar.title(f"🛠️ {nombre_taller}")
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
        with st.form("reg", clear_on_submit=True):
            st.code(f"Folio: {folio}")
            cli = st.text_input("Cliente")
            tel = st.text_input("WhatsApp")
            eq = st.text_input("Equipo")
            fa = st.text_area("Falla")
            co = st.number_input("Costo", 0.0)
            ab = st.number_input("Abono", 0.0)
            tec = st.selectbox("Técnico", df_u.iloc[:,0].tolist())
            
            if st.form_submit_button("Registrar"):
                nueva = pd.DataFrame([{"Folio": folio, "Fecha": date.today().strftime("%d/%m/%Y"), "Cliente": cli, "Telefono": tel, "Equipo": eq, "Falla": fa, "Costo": co, "Abono": ab, "Estado": "Recibido", "Tecnico": tec}])
                if guardar_datos(pd.concat([df_rep, nueva], ignore_index=True), "reparaciones"):
                    st.success("✅ ¡Guardado!")
                    # Link WhatsApp
                    msg = urllib.parse.quote(f"Hola {cli}, recibimos tu {eq}. Folio: {folio}")
                    st.markdown(f"[📱 Enviar WhatsApp](https://wa.me/{tel}?text={msg})")
                    time.sleep(2)
                    st.rerun()
    
    with c2:
        st.subheader("En Proceso")
        if not df_rep.empty:
            df_vivos = df_rep[df_rep["Estado"] != "Entregado"]
            df_ed = st.data_editor(df_vivos, hide_index=True, use_container_width=True)
            if st.button("Actualizar Tabla"):
                df_hist = df_rep[df_rep["Estado"] == "Entregado"]
                df_final = pd.concat([df_hist, df_ed]).drop_duplicates(subset="Folio", keep="last")
                if guardar_datos(df_final, "reparaciones"):
                    st.success("Sincronizado")
                    st.rerun()

with t2:
    st.subheader("Historial")
    st.dataframe(df_rep, use_container_width=True)

with t3:
    if st.session_state.rol == "admin":
        st.write("### Usuarios")
        st.table(df_u)
