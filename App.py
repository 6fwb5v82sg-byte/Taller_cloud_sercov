import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, date
import urllib.parse
import time

# ==========================================
# 1. CONFIGURACIÓN DE PÁGINA
# ==========================================
st.set_page_config(page_title="Taller Pro Cloud", layout="wide", page_icon="🛠️")

# URL de tu hoja (Debe estar en "Cualquier persona con el enlace" como "Editor")
URL_HOJA = "https://docs.google.com/spreadsheets/d/1--gIzJOWEYBHbjICf8Ca8pjv549G4ATCO8nFZAW4BMQ/edit?usp=sharing"

def conectar():
    try:
        # Intenta conectar usando los Secrets configurados en Streamlit Cloud
        conn = st.connection("gsheets", type=GSheetsConnection)
        return conn
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return None

conn = conectar()

# ==========================================
# 2. FUNCIONES DE CARGA Y GUARDADO
# ==========================================
def cargar_datos(pestana):
    try:
        # ttl=0 evita que Streamlit guarde datos viejos en memoria
        df = conn.read(spreadsheet=URL_HOJA, worksheet=pestana, ttl=0)
        if df is not None:
            df.columns = [str(c).strip() for c in df.columns]
            return df
        return pd.DataFrame()
    except Exception as e:
        st.warning(f"Aviso: No se pudo leer la pestaña '{pestana}'.")
        return pd.DataFrame()

def guardar_datos(df_completo, pestana):
    try:
        if pestana == "reparaciones":
            columnas = ["Folio", "Fecha", "Cliente", "Telefono", "Equipo", "Falla", "Costo", "Abono", "Estado", "Tecnico"]
            for col in columnas:
                if col not in df_completo.columns: df_completo[col] = ""
            df_final = df_completo[columnas]
        else:
            df_final = df_completo
            
        conn.update(spreadsheet=URL_HOJA, worksheet=pestana, data=df_final)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Error al guardar en Google Sheets: {e}")
        return False

# ==========================================
# 3. SEGURIDAD (LOGIN)
# ==========================================
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

# Carga inicial de usuarios
df_u = cargar_datos("usuarios")

if not st.session_state.autenticado:
    st.title("🔐 Acceso al Sistema")
    
    if df_u.empty:
        st.error("❌ ERROR CRÍTICO: No se encontró la tabla de usuarios.")
        st.info("Revisa que en tu Google Sheet la pestaña se llame 'usuarios' (todo minúsculas) y tenga datos.")
        st.stop()
    
    with st.container():
        _, col_login, _ = st.columns([1, 2, 1])
        with col_login:
            with st.form("login"):
                u = st.text_input("Usuario")
                p = st.text_input("Clave", type="password")
                if st.form_submit_button("Entrar"):
                    # Verificación por posición de columna (0=usuario, 1=clave, 2=rol)
                    match = df_u[(df_u.iloc[:,0].astype(str) == str(u)) & (df_u.iloc[:,1].astype(str) == str(p))]
                    if not match.empty:
                        st.session_state.autenticado = True
                        st.session_state.usuario = u
                        st.session_state.rol = str(match.iloc[0, 2]).lower()
                        st.rerun()
                    else:
                        st.error("Usuario o clave incorrectos")
    st.stop()

# ==========================================
# 4. INTERFAZ PRINCIPAL
# ==========================================
df_conf = cargar_datos("config")
nombre_taller = df_conf.iloc[0,0] if not df_conf.empty else "Mi Taller Cloud"

st.sidebar.title(f"🛠️ {nombre_taller}")
st.sidebar.write(f"Conectado: **{st.session_state.usuario}**")

if st.sidebar.button("Cerrar Sesión"):
    st.session_state.autenticado = False
    st.rerun()

t1, t2, t3 = st.tabs(["⚡ Taller", "🔍 Historial", "⚙️ Ajustes"])

# --- PESTAÑA 1: RECEPCIÓN ---
with t1:
    df_rep = cargar_datos("reparaciones")
    c1, c2 = st.columns([1, 2])
    
    with c1:
        st.subheader("Registrar Ingreso")
        # El folio se basa en el total de filas + 1
        folio_auto = f"F-{len(df_rep) + 1:03d}"
        
        with st.form("nuevo_registro", clear_on_submit=True):
            st.code(f"Folio: {folio_auto}")
            cliente = st.text_input("Cliente")
            whatsapp = st.text_input("WhatsApp (Solo números)")
            equipo = st.text_input("Equipo / Modelo")
            falla = st.text_area("Falla reportada")
            costo = st.number_input("Costo", 0.0)
            abono = st.number_input("Abono", 0.0)
            tecnico = st.selectbox("Técnico", df_u.iloc[:,0].tolist())
            
            if st.form_submit_button("Guardar Orden"):
                nueva_fila = pd.DataFrame([{
                    "Folio": folio_auto, "Fecha": date.today().strftime("%d/%m/%Y"),
                    "Cliente": cliente, "Telefono": whatsapp, "Equipo": equipo,
                    "Falla": falla, "Costo": costo, "Abono": abono, 
                    "Estado": "Recibido", "Tecnico": tecnico
                }])
                
                if guardar_datos(pd.concat([df_rep, nueva_fila], ignore_index=True), "reparaciones"):
                    st.success("✅ Guardado en la nube")
                    
                    # Generar link de WhatsApp
                    texto_wa = f"Hola {cliente}, recibimos tu {equipo}. Folio: {folio_auto}. Costo: ${costo}."
                    url_wa = f"https://wa.me/{whatsapp}?text={urllib.parse.quote(texto_wa)}"
                    st.markdown(f'[📱 Enviar comprobante por WhatsApp]({url_wa})')
                    time.sleep(2)
                    st.rerun()

    with c2:
        st.subheader("Equipos en Taller")
        if not df_rep.empty:
            # Filtramos para mostrar solo pendientes o en proceso
            df_vivos = df_rep[df_rep["Estado"] != "Entregado"]
            df_edit = st.data_editor(df_vivos, hide_index=True, use_container_width=True)
            
            if st.button("Sincronizar Cambios"):
                # Combinamos lo editado con lo que ya estaba entregado para no perder datos
                df_entregados = df_rep[df_rep["Estado"] == "Entregado"]
                df_total = pd.concat([df_entregados, df_edit]).drop_duplicates(subset="Folio", keep="last")
                if guardar_datos(df_total, "reparaciones"):
                    st.success("¡Datos actualizados!")
                    st.rerun()

# --- PESTAÑA 2: HISTORIAL ---
with t2:
    st.subheader("Buscador Global")
    query = st.text_input("Buscar por nombre o folio")
    if not df_rep.empty:
        if query:
            df_res = df_rep[df_rep.astype(str).apply(lambda x: query.lower() in x.str.lower().values, axis=1)]
            st.dataframe(df_res, use_container_width=True)
        else:
            st.dataframe(df_rep, use_container_width=True)

# --- PESTAÑA 3: AJUSTES ---
with t3:
    if st.session_state.rol == "admin":
        st.subheader("Configuración de Administrador")
        nuevo_nom = st.text_input("Nombre del Negocio", value=nombre_taller)
        if st.button("Actualizar Nombre"):
            if guardar_datos(pd.DataFrame([{"nombre": nuevo_nom}]), "config"):
                st.success("Nombre actualizado")
                st.rerun()
        st.divider()
        st.write("### Lista de Usuarios")
        st.table(df_u)
    else:
        st.warning("No tienes permisos para ver esta sección.")
