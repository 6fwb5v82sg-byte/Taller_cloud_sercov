import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, date
import urllib.parse
import time

# ==========================================
# 1. CONFIGURACIÓN E INTERFAZ INICIAL
# ==========================================
st.set_page_config(page_title="Taller Pro Cloud", layout="wide", page_icon="🛠️")

# URL de tu hoja (Asegúrate que sea pública: "Cualquier persona con el enlace - Editor")
URL_HOJA = "https://docs.google.com/spreadsheets/d/1--gIzJOWEYBHbjICf8Ca8pjv549G4ATCO8nFZAW4BMQ/edit?usp=sharing"

def conectar():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        return conn
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return None

conn = conectar()

# ==========================================
# 2. FUNCIONES DE BASE DE DATOS
# ==========================================
def cargar_datos(pestana):
    try:
        # ttl=0 para forzar la lectura de datos frescos siempre
        df = conn.read(spreadsheet=URL_HOJA, worksheet=pestana, ttl=0)
        if df is not None:
            df.columns = [str(c).strip() for c in df.columns]
            return df
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()

def guardar_datos(df_completo, pestana):
    try:
        # Limpieza de columnas para la pestaña reparaciones
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
        st.error(f"Error al guardar: {e}")
        return False

# ==========================================
# 3. SISTEMA DE AUTENTICACIÓN
# ==========================================
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

df_u = cargar_datos("usuarios")

if not st.session_state.autenticado:
    st.title("🔐 Acceso al Sistema")
    if df_u.empty:
        st.error("Error: No se pudo cargar la tabla de usuarios. Verifica tu conexión y el nombre de la pestaña.")
        st.stop()
    
    with st.container():
        c1, c2, c3 = st.columns([1,2,1])
        with c2:
            with st.form("login"):
                user = st.text_input("Usuario")
                pw = st.text_input("Contraseña", type="password")
                if st.form_submit_button("Ingresar"):
                    # Validación: buscamos coincidencia en las dos primeras columnas
                    match = df_u[(df_u.iloc[:,0].astype(str) == str(user)) & (df_u.iloc[:,1].astype(str) == str(pw))]
                    if not match.empty:
                        st.session_state.autenticado = True
                        st.session_state.usuario = user
                        st.session_state.rol = str(match.iloc[0, 2]).lower() if len(match.columns) > 2 else "tecnico"
                        st.rerun()
                    else:
                        st.error("Credenciales incorrectas")
    st.stop()

# ==========================================
# 4. DASHBOARD PRINCIPAL
# ==========================================
df_conf = cargar_datos("config")
nombre_taller = df_conf.iloc[0,0] if not df_conf.empty else "Mi Taller Pro"

st.sidebar.title(f"🛠️ {nombre_taller}")
st.sidebar.write(f"Usuario: **{st.session_state.usuario}**")
st.sidebar.write(f"Rol: {st.session_state.rol.capitalize()}")

if st.sidebar.button("Cerrar Sesión"):
    st.session_state.autenticado = False
    st.rerun()

t1, t2, t3 = st.tabs(["⚡ Recepción", "🔍 Historial", "⚙️ Configuración"])

# --- PESTAÑA 1: TALLER ---
with t1:
    df_rep = cargar_datos("reparaciones")
    col_izq, col_der = st.columns([1, 2])
    
    with col_izq:
        st.subheader("Nueva Orden")
        # Generar Folio automático basado en el número de filas
        nuevo_folio = f"T-{len(df_rep) + 1:03d}"
        
        with st.form("registro_orden", clear_on_submit=True):
            st.info(f"Folio: {nuevo_folio}")
            cli = st.text_input("Nombre del Cliente")
            tel = st.text_input("WhatsApp (ej: 521234567890)")
            eq = st.text_input("Equipo (Marca/Modelo)")
            fa = st.text_area("Descripción del problema")
            co = st.number_input("Costo Estimado", min_value=0.0, step=50.0)
            ab = st.number_input("Abono Inicial", min_value=0.0, step=50.0)
            tec = st.selectbox("Asignar a", df_u.iloc[:,0].tolist() if not df_u.empty else ["General"])
            
            if st.form_submit_button("Registrar Equipo"):
                nuevo_registro = pd.DataFrame([{
                    "Folio": nuevo_folio, "Fecha": date.today().strftime("%d/%m/%Y"),
                    "Cliente": cli, "Telefono": tel, "Equipo": eq, "Falla": fa,
                    "Costo": co, "Abono": ab, "Estado": "Recibido", "Tecnico": tec
                }])
                
                if guardar_datos(pd.concat([df_rep, nuevo_registro], ignore_index=True), "reparaciones"):
                    st.success("¡Orden guardada correctamente!")
                    
                    # Lógica de WhatsApp
                    msg = f"Hola *{cli}*, tu equipo *{eq}* fue recibido con el Folio: *{nuevo_folio}*. Falla: {fa}. Abono: ${ab}."
                    msg_url = urllib.parse.quote(msg)
                    tel_wa = "".join(filter(str.isdigit, tel))
                    link = f"https://wa.me/{tel_wa}?text={msg_url}"
                    
                    st.markdown(f'''<a href="{link}" target="_blank">
                        <button style="width:100%; background-color:#25D366; color:white; border:none; padding:12px; border-radius:8px; cursor:pointer; font-weight:bold;">
                        📱 Enviar Ticket por WhatsApp
                        </button></a>''', unsafe_allow_html=True)
                    
                    if st.button("🔄 Refrescar Lista"):
                        st.rerun()
    
    with col_der:
        st.subheader("Equipos en Proceso")
        if not df_rep.empty:
            # Solo mostramos lo que no está entregado para agilizar
            df_activos = df_rep[df_rep["Estado"] != "Entregado"]
            df_editado = st.data_editor(df_activos, hide_index=True, use_container_width=True)
            
            if st.button("Actualizar Estados"):
                # Combinamos los datos editados con los históricos (entregados)
                df_historial = df_rep[df_rep["Estado"] == "Entregado"]
                df_final = pd.concat([df_historial, df_editado]).drop_duplicates(subset="Folio", keep="last")
                if guardar_datos(df_final, "reparaciones"):
                    st.toast("Base de datos actualizada")
                    time.sleep(1)
                    st.rerun()

# --- PESTAÑA 2: HISTORIAL ---
with t2:
    st.subheader("Historial Completo")
    busqueda = st.text_input("Filtrar por nombre, folio o equipo...")
    if not df_rep.empty:
        if busqueda:
            df_res = df_rep[df_rep.astype(str).apply(lambda x: busqueda.lower() in x.str.lower().values, axis=1)]
            st.dataframe(df_res, use_container_width=True, hide_index=True)
        else:
            st.dataframe(df_rep, use_container_width=True, hide_index=True)

# --- PESTAÑA 3: CONFIGURACIÓN ---
with t3:
    if st.session_state.rol == "admin":
        st.subheader("Ajustes del Sistema")
        with st.form("conf_t"):
            n_nombre = st.text_input("Nombre Comercial", value=nombre_taller)
            if st.form_submit_button("Guardar Cambios"):
                if guardar_datos(pd.DataFrame([{"nombre": n_nombre}]), "config"):
                    st.success("Nombre actualizado")
                    st.rerun()
        
        st.divider()
        st.write("### Usuarios del Sistema")
        st.dataframe(df_u, use_container_width=True)
    else:
        st.warning("Acceso restringido. Solo administradores.")
