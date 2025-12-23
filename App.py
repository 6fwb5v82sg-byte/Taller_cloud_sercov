import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, date
import time
from fpdf import FPDF
import os
import urllib.parse

# ==========================================
# 1. CONFIGURACIÓN Y CONEXIÓN
# ==========================================
st.set_page_config(page_title="Taller Pro Cloud", layout="wide", page_icon="🛠️")

URL_HOJA = "https://docs.google.com/spreadsheets/d/1--gIzJOWEYBHbjICf8Ca8pjv549G4ATCO8nFZAW4BMQ/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos(nombre_pestana):
    try:
        df = conn.read(spreadsheet=URL_HOJA, worksheet=nombre_pestana, ttl=0)
        if df is not None and not df.empty:
            df.columns = [str(c).strip() for c in df.columns]
            return df
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error en pestaña '{nombre_pestana}': {e}")
        return pd.DataFrame()

def guardar_datos(df_completo, nombre_pestana):
    try:
        # Definimos las columnas exactas para mantener el orden en Google Sheets
        if nombre_pestana == "reparaciones":
            columnas_reales = ["Fecha", "Cliente", "Telefono", "Equipo", "Falla", "Costo", "Abono", "Estado", "Tecnico"]
            df_limpio = df_completo[columnas_reales]
        else:
            df_limpio = df_completo
            
        conn.update(spreadsheet=URL_HOJA, worksheet=nombre_pestana, data=df_limpio)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Error al guardar: {e}")
        return False

# ==========================================
# 2. SEGURIDAD (LOGIN)
# ==========================================
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.title("🔐 Acceso Sistema Taller")
    df_u = cargar_datos("usuarios")
    u = st.text_input("Usuario")
    p = st.text_input("Clave", type="password")
    if st.button("Iniciar"):
        if not df_u.empty:
            match = df_u[(df_u.iloc[:,0].astype(str)==str(u)) & (df_u.iloc[:,1].astype(str)==str(p))]
            if not match.empty:
                st.session_state.autenticado, st.session_state.usuario = True, u
                st.session_state.rol = str(match.iloc[0, 2]).lower()
                st.rerun()
    st.stop()

# ==========================================
# 3. INTERFAZ PRINCIPAL
# ==========================================
df_conf = cargar_datos("config")
config = df_conf.iloc[0].to_dict() if not df_conf.empty else {}

st.sidebar.title(f"🛠️ {config.get('nombre', 'Taller')}")
if st.sidebar.button("Cerrar Sesión"):
    st.session_state.autenticado = False
    st.rerun()

t_taller, t_hist, t_finanzas, t_ajustes = st.tabs(["⚡ Taller", "🔍 Historial", "📊 Finanzas", "⚙️ Ajustes"])

with t_taller:
    df_rep = cargar_datos("reparaciones")
    df_u = cargar_datos("usuarios")
    lista_tecnicos = df_u.iloc[:, 0].tolist() if not df_u.empty else ["Sin Asignar"]

    c1, c2 = st.columns([1, 2])
    with c1:
        st.subheader("Nueva Orden")
        with st.form("reg", clear_on_submit=True):
            cli, tel, eq = st.text_input("Cliente"), st.text_input("WhatsApp"), st.text_input("Equipo")
            fl, co, ab = st.text_area("Falla"), st.number_input("Costo", 0.0), st.number_input("Abono", 0.0)
            tecnico = st.selectbox("Asignar a Técnico:", lista_tecnicos)
            if st.form_submit_button("Guardar"):
                nueva = pd.DataFrame([{"Fecha": date.today().strftime("%Y-%m-%d"), "Cliente": cli, "Telefono": tel, "Equipo": eq, "Falla": fl, "Costo": co, "Abono": ab, "Estado": "Recibido", "Tecnico": tecnico}])
                if guardar_datos(pd.concat([df_rep, nueva], ignore_index=True), "reparaciones"): st.rerun()
    
    with c2:
        st.subheader("Gestión de Equipos")
        if not df_rep.empty:
            df_edit = st.data_editor(df_rep, hide_index=True, use_container_width=True)
            if st.button("Confirmar Cambios"):
                if guardar_datos(df_edit, "reparaciones"): st.rerun()
            
            st.divider()
            st.subheader("📲 Notificar Cliente")
            sel = st.selectbox("Seleccionar para WhatsApp:", df_rep.index, format_func=lambda x: f"{df_rep.loc[x, 'Cliente']} - {df_rep.loc[x, 'Equipo']}")
            if st.button("Abrir WhatsApp"):
                row = df_rep.loc[sel]
                mensaje = f"Hola *{row['Cliente']}*, tu equipo *{row['Equipo']}* está siendo atendido por *{row['Tecnico']}* en *{config.get('nombre')}*."
                url_wa = f"https://wa.me/{row['Telefono']}?text={urllib.parse.quote(mensaje)}"
                st.markdown(f'<a href="{url_wa}" target="_blank">📲 Enviar Mensaje</a>', unsafe_allow_html=True)

with t_finanzas:
    if st.session_state.rol in ["admin", "owner"] and not df_rep.empty:
        st.subheader("📊 Productividad por Técnico")
        # Gráfico de carga de trabajo por técnico
        trabajo_tecnico = df_rep.groupby('Tecnico').size().reset_index(name='Cantidad')
        st.bar_chart(data=trabajo_tecnico, x='Tecnico', y='Cantidad')
        
        

        st.subheader("💰 Resumen Financiero")
        col_m1, col_m2 = st.columns(2)
        hoy = date.today().strftime("%Y-%m-%d")
        df_hoy = df_rep[df_rep['Fecha'] == hoy]
        col_m1.metric("Ingresos de Hoy", f"${df_hoy['Abono'].sum():,.2f}")
        col_m2.metric("Equipos en Proceso", len(df_rep[df_rep['Estado'] != 'Entregado']))

with t_hist:
    st.subheader("🔍 Buscador")
    busqueda = st.text_input("Buscar por Nombre, Teléfono o Técnico:")
    if busqueda and not df_rep.empty:
        res = df_rep[df_rep['Cliente'].astype(str).str.contains(busqueda, case=False) | 
                     df_rep['Telefono'].astype(str).str.contains(busqueda, case=False) |
                     df_rep['Tecnico'].astype(str).str.contains(busqueda, case=False)]
        st.dataframe(res, use_container_width=True)
