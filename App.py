import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, date
import time
from fpdf import FPDF
import os
import urllib.parse

# ==========================================
# 1. CONFIGURACIÓN Y CONEXIÓN ROBUSTA
# ==========================================
st.set_page_config(page_title="Taller Pro Cloud", layout="wide", page_icon="🛠️")

# URL de tu hoja de cálculo
URL_HOJA = "https://docs.google.com/spreadsheets/d/1--gIzJOWEYBHbjICf8Ca8pjv549G4ATCO8nFZAW4BMQ/edit?usp=sharing"

conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos(nombre_pestana):
    """Carga de datos optimizada para evitar el Error 400."""
    try:
        # Intentamos leer la pestaña de forma directa
        df = conn.read(spreadsheet=URL_HOJA, worksheet=nombre_pestana, ttl=0)
        if df is not None and not df.empty:
            # Limpiamos nombres de columnas (quita espacios invisibles)
            df.columns = [str(c).strip() for c in df.columns]
            return df
        return pd.DataFrame()
    except Exception as e:
        # Este mensaje ayuda a diagnosticar si el problema es el nombre de la pestaña
        st.error(f"Error de acceso: No se encontró la pestaña '{nombre_pestana}'.")
        return pd.DataFrame()

def guardar_datos(df_completo, nombre_pestana):
    """Guarda los datos respetando las columnas originales."""
    try:
        if nombre_pestana == "reparaciones":
            columnas = ["Fecha", "Cliente", "Telefono", "Equipo", "Falla", "Costo", "Abono", "Estado", "Tecnico"]
            df_limpio = df_completo[columnas]
        else:
            df_limpio = df_completo
            
        conn.update(spreadsheet=URL_HOJA, worksheet=nombre_pestana, data=df_limpio)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Error al guardar datos: {e}")
        return False

# ==========================================
# 2. SISTEMA DE SEGURIDAD (LOGIN)
# ==========================================
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.title("🔐 Acceso Sistema Taller")
    
    # Intentamos cargar la tabla de usuarios
    df_u = cargar_datos("usuarios")
    
    col_login, _ = st.columns([1, 1])
    with col_login:
        u = st.text_input("Usuario")
        p = st.text_input("Contraseña", type="password")
        
        if st.button("Ingresar al Sistema"):
            if not df_u.empty:
                # Buscamos coincidencia de usuario y clave
                match = df_u[(df_u.iloc[:, 0].astype(str) == str(u)) & 
                             (df_u.iloc[:, 1].astype(str) == str(p))]
                
                if not match.empty:
                    st.session_state.autenticado = True
                    st.session_state.usuario = u
                    st.session_state.rol = str(match.iloc[0, 2]).lower()
                    st.rerun()
                else:
                    st.error("Credenciales incorrectas. Verifica mayúsculas y minúsculas.")
            else:
                st.warning("No se pudo leer la tabla de usuarios. Revisa los permisos de la hoja.")
    st.stop()

# ==========================================
# 3. INTERFAZ PRINCIPAL
# ==========================================
df_conf = cargar_datos("config")
config = df_conf.iloc[0].to_dict() if not df_conf.empty else {"nombre": "Mi Taller"}

st.sidebar.title(f"🛠️ {config.get('nombre')}")
st.sidebar.write(f"Usuario: **{st.session_state.usuario}**")
if st.sidebar.button("Cerrar Sesión"):
    st.session_state.autenticado = False
    st.rerun()

t_taller, t_hist, t_finanzas, t_ajustes = st.tabs(["⚡ Taller", "🔍 Historial", "📊 Finanzas", "⚙️ Ajustes"])

# --- TAB TALLER ---
with t_taller:
    df_rep = cargar_datos("reparaciones")
    df_usuarios_tecnicos = cargar_datos("usuarios")
    lista_tecnicos = df_usuarios_tecnicos.iloc[:, 0].tolist() if not df_usuarios_tecnicos.empty else ["General"]

    # Alertas de tiempo
    if not df_rep.empty:
        df_rep['Días'] = df_rep['Fecha'].apply(lambda x: (date.today() - datetime.strptime(str(x), "%Y-%m-%d").date()).days)
        retrasados = df_rep[(df_rep['Días'] >= 5) & (df_rep['Estado'] != "Entregado")]
        if not retrasados.empty:
            st.warning(f"🔔 Tienes {len(retrasados)} equipos con más de 5 días en taller.")

    c1, c2 = st.columns([1, 2])
    with c1:
        st.subheader("Entrada de Equipo")
        with st.form("form_registro", clear_on_submit=True):
            f_cli = st.text_input("Cliente")
            f_tel = st.text_input("WhatsApp (Código de país + número)")
            f_eq = st.text_input("Equipo")
            f_fa = st.text_area("Falla")
            f_co = st.number_input("Costo Total", 0.0)
            f_ab = st.number_input("Abono", 0.0)
            f_te = st.selectbox("Asignar Técnico", lista_tecnicos)
            
            if st.form_submit_button("Registrar"):
                nueva_fila = pd.DataFrame([{
                    "Fecha": date.today().strftime("%Y-%m-%d"),
                    "Cliente": f_cli, "Telefono": f_tel, "Equipo": f_eq,
                    "Falla": f_fa, "Costo": f_co, "Abono": f_ab, 
                    "Estado": "Recibido", "Tecnico": f_te
                }])
                if guardar_datos(pd.concat([df_rep, nueva_fila], ignore_index=True), "reparaciones"):
                    st.success("Registrado correctamente")
                    st.rerun()

    with c2:
        st.subheader("Estado del Taller")
        if not df_rep.empty:
            # WhatsApp rápido
            st.write("Aviso rápido:")
            sel_wa = st.selectbox("Seleccionar Cliente:", df_rep.index, format_func=lambda x: f"{df_rep.loc[x, 'Cliente']} ({df_rep.loc[x, 'Equipo']})")
            if st.button("📲 Enviar Aviso 'Listo'"):
                r = df_rep.loc[sel_wa]
                msj = f"Hola {r['Cliente']}, tu {r['Equipo']} está listo en {config.get('nombre')}. Saldo: ${r['Costo']-r['Abono']}."
                st.markdown(f'<a href="https://wa.me/{r["Telefono"]}?text={urllib.parse.quote(msj)}" target="_blank">Abrir WhatsApp</a>', unsafe_allow_html=True)
            
            st.divider()
            # Editor de tabla
            df_editado = st.data_editor(df_rep, hide_index=True, use_container_width=True)
            if st.button("Guardar todos los cambios"):
                if guardar_datos(df_editado, "reparaciones"):
                    st.success("Base de datos actualizada")
                    st.rerun()

# --- TAB HISTORIAL ---
with t_hist:
    st.subheader("🔍 Consultar Historial")
    query = st.text_input("Buscar por Nombre o Celular:")
    if query and not df_rep.empty:
        filtro = df_rep[df_rep['Cliente'].astype(str).str.contains(query, case=False) | 
                        df_rep['Telefono'].astype(str).str.contains(query, case=False)]
        st.table(filtro)

# --- TAB FINANZAS ---
with t_finanzas:
    if st.session_state.rol in ["admin", "owner"] and not df_rep.empty:
        st.subheader("📊 Estadísticas Mensuales")
        df_rep['Mes'] = pd.to_datetime(df_rep['Fecha']).dt.strftime('%Y-%m')
        grafico_data = df_rep.groupby('Mes').size().reset_index(name='Equipos')
        st.bar_chart(data=grafico_data, x='Mes', y='Equipos')
        
        st.subheader("💰 Resumen de Hoy")
        hoy = date.today().strftime("%Y-%m-%d")
        df_hoy = df_rep[df_rep['Fecha'] == hoy]
        st.metric("Abonos Recibidos Hoy", f"${df_hoy['Abono'].sum():,.2f}")
    else:
        st.info("No tienes permisos para ver finanzas o no hay datos.")

# --- TAB AJUSTES ---
with t_ajustes:
    if st.session_state.rol == "owner":
        st.subheader("Configuración General")
        with st.form("ajustes"):
            n = st.text_input("Nombre del Negocio", config.get('nombre'))
            d = st.text_input("Dirección", config.get('dir'))
            t = st.text_input("Teléfono", config.get('tel'))
            gar = st.text_area("Términos de Garantía", config.get('terminos'))
            if st.form_submit_button("Guardar Configuración"):
                df_c = pd.DataFrame([{"nombre": n, "dir": d, "tel": t, "terminos": gar}])
                if guardar_datos(df_c, "config"):
                    st.success("Configuración guardada")
                    st.rerun()
