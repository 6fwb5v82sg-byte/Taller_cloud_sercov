import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import date
import urllib.parse
import time

# CONFIGURACIÓN
st.set_page_config(page_title="Taller Pro Cloud", layout="wide")

# Conexión Segura usando Service Account (Configurada en Secrets)
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos(pestana):
    try:
        # Ya no necesitamos pasar la URL aquí si está en Secrets
        return conn.read(worksheet=pestana, ttl=0)
    except:
        return pd.DataFrame()

def guardar_datos(df, pestana):
    try:
        conn.update(worksheet=pestana, data=df)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Error técnico: {e}")
        return False

# --- LÓGICA DE ACCESO ---
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

df_u = cargar_datos("usuarios")

if not st.session_state.autenticado:
    st.title("🔐 Acceso al Sistema")
    if df_u.empty:
        st.error("Error: No se pudo conectar con la base de datos segura.")
        st.stop()
    
    with st.form("login"):
        u = st.text_input("Usuario")
        p = st.text_input("Clave", type="password")
        if st.form_submit_button("Entrar"):
            match = df_u[(df_u.iloc[:,0].astype(str) == str(u)) & (df_u.iloc[:,1].astype(str) == str(p))]
            if not match.empty:
                st.session_state.autenticado = True
                st.session_state.usuario = u
                st.rerun()
            else:
                st.error("Clave incorrecta")
    st.stop()

# --- INTERFAZ TALLER ---
st.sidebar.write(f"Usuario: {st.session_state.usuario}")
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
            if st.form_submit_button("Registrar"):
                nueva = pd.DataFrame([{"Folio": folio, "Fecha": date.today().strftime("%d/%m/%Y"), "Cliente": cli, "Telefono": tel, "Equipo": eq, "Falla": fa, "Estado": "Recibido"}])
                if guardar_datos(pd.concat([df_rep, nueva], ignore_index=True), "reparaciones"):
                    st.success("✅ ¡Guardado con éxito!")
                    time.sleep(1)
                    st.rerun()

    with c2:
        st.subheader("Equipos en Taller")
        if not df_rep.empty:
            df_vivos = df_rep[df_rep["Estado"] != "Entregado"]
            df_ed = st.data_editor(df_vivos, hide_index=True)
            if st.button("Sincronizar Cambios"):
                df_final = pd.concat([df_rep[df_rep["Estado"] == "Entregado"], df_ed]).drop_duplicates(subset="Folio", keep="last")
                if guardar_datos(df_final, "reparaciones"):
                    st.success("Nube actualizada")
                    st.rerun()
