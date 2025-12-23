import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, date, timedelta
from fpdf import FPDF
import urllib.parse

# ==========================================
# 1. CONFIGURACIÓN DE CONEXIÓN
# ==========================================
# REEMPLAZA ESTE ENLACE POR EL DE TU GOOGLE SHEET (MODO EDITOR)
URL_HOJA = https://docs.google.com/spreadsheets/d/1--gIzJOWEYBHbjICf8Ca8pjv549G4ATCO8nFZAW4BMQ/edit?usp=drivesdk

conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_tabla(nombre_pestana):
    try:
        return conn.read(spreadsheet=URL_HOJA, worksheet=nombre_pestana, ttl="0")
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
# 2. FUNCIONES DE APOYO (PDF Y WHATSAPP)
# ==========================================
def generar_ticket(datos, config):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, config['nombre'], ln=True, align='C')
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
    u = st.text_input("Usuario")
    p = st.text_input("Contraseña", type="password")
    if st.button("Iniciar Sesión"):
        users_df = cargar_tabla("usuarios")
        valid = users_df[(users_df['usuario'] == u) & (users_df['clave'] == p)]
        if not valid.empty:
            st.session_state.autenticado = True
            st.session_state.usuario = u
            st.session_state.rol = valid.iloc[0]['rol']
            st.rerun()
        else:
            st.error("Usuario o clave incorrectos")
    st.stop()

# ==========================================
# 4. INTERFAZ Y PESTAÑAS
# ==========================================
# Cargar Configuración
try:
    config = cargar_tabla("config").iloc[0]
except:
    config = {"nombre": "Mi Taller", "dir": "Ciudad", "tel": "000", "garantia": 30, "terminos": "N/A"}

st.sidebar.title(f"🛠️ {config['nombre']}")
st.sidebar.write(f"Rol: **{st.session_state.rol.upper()}**")
if st.sidebar.button("Cerrar Sesión"):
    st.session_state.autenticado = False
    st.rerun()

tabs = st.tabs(["⚡ Taller", "📊 Finanzas", "🔍 Garantías", "⚙️ Ajustes"])

# --- TAB 1: OPERACIONES ---
with tabs[0]:
    df_rep = cargar_tabla("reparaciones")
    c1, c2 = st.columns([1, 2])
    
    with c1:
        st.subheader("Nueva Orden")
        with st.form("registro", clear_on_submit=True):
            cli = st.text_input("Cliente")
            tel = st.text_input("WhatsApp (ej: 521...)")
            eq = st.text_input("Equipo")
            fl = st.text_area("Falla")
            co = st.number_input("Costo Total $", min_value=0.0)
            ab = st.number_input("Abono $", min_value=0.0)
            if st.form_submit_button("Registrar Equipo"):
                nueva = {
                    "Fecha": date.today().strftime("%Y-%m-%d"),
                    "Cliente": cli, "Telefono": tel, "Equipo": eq, 
                    "Falla": fl, "Costo": co, "Abono": ab, 
                    "Estado": "Recibido", "Notas": ""
                }
                guardar_fila(nueva, "reparaciones")
                st.success("Guardado en la nube")
                st.rerun()

    with c2:
        st.subheader("Equipos en Taller")
        if not df_rep.empty:
            df_activas = df_rep[df_rep['Estado'] != "Entregado"].copy()
            # Bloqueo por rol
            bloqueo = ["Fecha", "Cliente", "Equipo"]
            if st.session_state.rol == "tecnico": 
                bloqueo.extend(["Costo", "Abono"])
            
            editado = st.data_editor(df_activas, disabled=bloqueo, hide_index=True)
            if st.button("💾 Guardar Cambios"):
                df_rep.update(editado)
                actualizar_tabla_completa(df_rep, "reparaciones")
                st.rerun()
            
            # WhatsApp y PDF
            st.divider()
            sel = st.selectbox("Acciones para cliente:", df_activas['Cliente'].unique() if not df_activas.empty else [])
            if sel:
                fila = df_activas[df_activas['Cliente'] == sel].iloc[0]
                msg = f"Hola {fila['Cliente']}, tu {fila['Equipo']} está {fila['Estado']}. Saldo: ${fila['Costo']-fila['Abono']}"
                link = f"https://wa.me/{fila['Telefono']}?text={urllib.parse.quote(msg)}"
                st.link_button(f"Enviar WhatsApp a {sel}", link)
                st.download_button("Descargar Ticket PDF", generar_ticket(fila.to_dict(), config), f"ticket_{sel}.pdf")

# --- TAB 2: FINANZAS (ADMIN/OWNER) ---
with tabs[1]:
    if st.session_state.rol in ["admin", "owner"]:
        if not df_rep.empty:
            df_rep['Costo'] = pd.to_numeric(df_rep['Costo'])
            df_rep['Abono'] = pd.to_numeric(df_rep['Abono'])
            st.metric("Total en Caja (Abonos)", f"${df_rep['Abono'].sum():,.2f}")
            st.dataframe(df_rep)
    else:
        st.warning("Acceso restringido")

# --- TAB 3: GARANTÍAS ---
with tabs[2]:
    busq = st.text_input("Buscar Cliente:")
    if busq and not df_rep.empty:
        res = df_rep[df_rep['Cliente'].str.contains(busq, case=False)]
        for _, r in res.iterrows():
            fv = pd.to_datetime(r['Fecha']) + timedelta(days=int(config['garantia']))
            v = datetime.now() > fv
            st.write(f"**{r['Equipo']}** | Garantía: {'❌ Vencida' if v else '✅ Activa'} (Vence: {fv.date()})")

# --- TAB 4: AJUSTES (SOLO OWNER) ---
with tabs[3]:
    if st.session_state.rol == "owner":
        st.subheader("Configuración Global")
        with st.form("conf"):
            n = st.text_input("Nombre Taller", config['nombre'])
            d = st.text_input("Dirección", config['dir'])
            t = st.text_input("Teléfono", config['tel'])
            g = st.number_input("Días Garantía", value=int(config['garantia']))
            te = st.text_area("Términos", config['terminos'])
            if st.form_submit_button("Actualizar Empresa"):
                actualizar_tabla_completa(pd.DataFrame([{"nombre":n, "dir":d, "tel":t, "garantia":g, "terminos":te}]), "config")
                st.rerun()
    else:
        st.warning("Solo el dueño puede editar esto.")
