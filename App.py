import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, date, timedelta
from fpdf import FPDF
import urllib.parse

# ==========================================
# 1. CONFIGURACIÓN DE CONEXIÓN
# ==========================================
URL_HOJA = "https://docs.google.com/spreadsheets/d/1--gIzJOWEYBHbjICf8Ca8pjv549G4ATCO8nFZAW4BMQ/edit?usp=drivesdk"

conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_tabla(nombre_pestana):
    try:
        df = conn.read(spreadsheet=URL_HOJA, worksheet=nombre_pestana, ttl="0")
        # Limpieza de espacios en nombres de columnas
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except:
        return pd.DataFrame()

def guardar_fila(datos_dict, nombre_pestana):
    df_actual = cargar_tabla(nombre_pestana)
    df_nuevo = pd.concat([df_actual, pd.DataFrame([datos_dict])], ignore_index=True)
    conn.update(spreadsheet=URL_HOJA, worksheet=nombre_pestana, data=df_nuevo)
    st.cache_data.clear()

def actualizar_tabla_completa(df_completo, nombre_pestana):
    conn.update(spreadsheet=URL_HOJA, worksheet=nombre_pestana, data=df_completo)
    st.cache_data.clear()

# ==========================================
# 2. FUNCIONES DE APOYO
# ==========================================
def generar_ticket(datos, config):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, str(config['nombre']), ln=True, align='C')
    pdf.set_font("Arial", size=10)
    pdf.cell(0, 5, f"{config['dir']} | Tel: {config['tel']}", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "ORDEN DE SERVICIO", ln=True, border='B')
    pdf.set_font("Arial", size=10)
    for k, v in datos.items():
        pdf.cell(50, 7, f"{k}:", ln=0)
        pdf.cell(0, 7, str(v), ln=1)
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 9)
    pdf.cell(0, 5, "TERMINOS Y CONDICIONES:", ln=True)
    pdf.set_font("Arial", size=7)
    pdf.multi_cell(0, 4, str(config['terminos']))
    return pdf.output(dest='S').encode('latin-1')

# ==========================================
# 3. SEGURIDAD Y LOGIN
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
            # BUSQUEDA SEGURA: Por posición de columna para evitar KeyError
            # Col 0 = usuario, Col 1 = clave, Col 2 = rol
            try:
                valid = users_df[(users_df.iloc[:, 0].astype(str) == str(u)) & 
                                 (users_df.iloc[:, 1].astype(str) == str(p))]
                if not valid.empty:
                    st.session_state.autenticado = True
                    st.session_state.usuario = u
                    st.session_state.rol = str(valid.iloc[0, 2]).lower()
                    st.rerun()
                else:
                    st.error("Usuario o clave incorrectos")
            except:
                st.error("Error: La hoja 'usuarios' no tiene el formato correcto (A:usuario, B:clave, C:rol)")
        else:
            st.error("No se pudo conectar con la base de datos de usuarios.")
    st.stop()

# ==========================================
# 4. INTERFAZ (Solo carga si está autenticado)
# ==========================================
try:
    conf_df = cargar_tabla("config")
    config = conf_df.iloc[0]
except:
    config = {"nombre": "Mi Taller", "dir": "Ciudad", "tel": "000", "garantia": 30, "terminos": "N/A"}

st.sidebar.title(f"🛠️ {config['nombre']}")
st.sidebar.write(f"Usuario: **{st.session_state.usuario}**")
if st.sidebar.button("Cerrar Sesión"):
    st.session_state.autenticado = False
    st.rerun()

tabs = st.tabs(["⚡ Taller", "📊 Finanzas", "🔍 Garantías", "⚙️ Ajustes"])

with tabs[0]: # TALLER
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
                nueva = {"Fecha": date.today().strftime("%Y-%m-%d"), "Cliente": cli, "Telefono": tel, 
                         "Equipo": eq, "Falla": fl, "Costo": co, "Abono": ab, "Estado": "Recibido"}
                guardar_fila(nueva, "reparaciones")
                st.rerun()
    with c2:
        st.subheader("Equipos en Taller")
        if not df_rep.empty:
            editado = st.data_editor(df_rep[df_rep['Estado'] != "Entregado"], hide_index=True)
            if st.button("Guardar Cambios"):
                df_rep.update(editado)
                actualizar_tabla_completa(df_rep, "reparaciones")
                st.rerun()

with tabs[1]: # FINANZAS
    if st.session_state.rol in ["admin", "owner"]:
        st.dataframe(df_rep)
    else:
        st.warning("No tienes permiso.")

with tabs[2]: # GARANTIAS
    busq = st.text_input("Buscar Cliente:")
    if busq and not df_rep.empty:
        res = df_rep[df_rep['Cliente'].astype(str).str.contains(busq, case=False)]
        st.write(res)

with tabs[3]: # AJUSTES
    if st.session_state.rol == "owner":
        with st.form("conf"):
            n = st.text_input("Nombre", config['nombre'])
            if st.form_submit_button("Actualizar"):
                actualizar_tabla_completa(pd.DataFrame([{"nombre":n, "dir":config['dir'], "tel":config['tel'], "garantia":config['garantia'], "terminos":config['terminos']}]), "config")
                st.rerun()
