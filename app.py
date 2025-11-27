import streamlit as st
import pandas as pd
import time
import uuid
from io import BytesIO
import requests
import msal
from PIL import Image
from pyzbar.pyzbar import decode
import streamlit.components.v1 as components

# ==========================================
# CONFIGURACIÓN DE LA PÁGINA
# ==========================================
st.set_page_config(
    page_title="Put To Store PJLT",
    page_icon="📦",
    layout="wide",                 # usar todo el ancho de la pantalla
    initial_sidebar_state="collapsed"  # ocultar barra lateral en móvil
)


# ==========================================
# CONFIGURACIÓN ONEDRIVE / MICROSOFT GRAPH
# ==========================================
CLIENT_ID = "0de56420-3ff9-4183-b2cc-ad318f219994"   # Id. de aplicación (cliente)
TENANT_ID = "701edd3e-c7a8-4789-b1ce-8a243620d68f"   # Id. de directorio (inquilino)

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPES = ["User.Read", "Files.Read.All"]  # o "Files.ReadWrite.All" si luego quieres escribir
GRAPH_BASE = "https://graph.microsoft.com/v1.0"

# Ruta de la carpeta en OneDrive
ONEDRIVE_FOLDER_LABEL = "/pry_pts_amphora/"
ONEDRIVE_FOLDER_PATH = "/pry_pts_amphora"  # ruta relativa al root de tu OneDrive



# ==========================================
# ESTILOS CSS (TU INTERFAZ ACTUAL)
# ==========================================
st.markdown("""
    <style>
    .stApp {
        background-color: #f3f2f1;
    }

    /* Reducir padding global y centrar contenido en una columna cómoda */
    main .block-container {
        padding-top: 0.6rem;
        padding-bottom: 0.8rem;
        padding-left: 0.9rem;
        padding-right: 0.9rem;
        max-width: 640px;      /* ancho cómodo en escritorio y móvil */
        margin: 0 auto;
    }

    .header-bar {
        background-color: #0078d4;
        padding: 0.8rem 1rem;
        color: white;
        border-radius: 5px;
        margin-bottom: 14px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        box-shadow: 0 2px 6px rgba(0,0,0,0.15);
    }
    .task-card {
        background-color: white;
        padding: 16px 18px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border: 1px solid #e0e0e0;
        margin-bottom: 10px;
    }
    .big-number {
        font-size: 2rem;
        font-weight: bold;
        color: #0078d4;
    }
    .store-name {
        font-size: 1.4rem;
        font-weight: bold;
        color: #333;
    }

    /* Botones un poco más compactos */
    .stButton>button {
        border-radius: 6px;
        padding: 0.4rem 0.9rem;
        font-weight: 600;
    }

    /* ----- VERSIÓN MÓVIL (pantallas estrechas) ----- */
    @media (max-width: 600px) {

        main .block-container {
            padding-top: 0.4rem;
            padding-bottom: 0.6rem;
            padding-left: 0.5rem;
            padding-right: 0.5rem;
        }

        /* Fila horizontal de métricas */
        .kv-row {
            display: flex;
            flex-direction: row;
            gap: 1.5rem;              /* 🔹 Más separación horizontal */
            margin-top: 1rem;
            margin-bottom: 0.5rem;
        }
    
        /* Caja de cada métrica (Cant / Bulto) */
        .kv-box {
            flex: 1;
            background-color: #f4f6fb;
            border: 1px solid #dde1f0;
            border-radius: 10px;
            padding: 0.6rem 0.8rem;
            position: relative;              /* 🔹 para posicionar el icono */
            display: flex;
            align-items: center;
            justify-content: center;         /* 🔹 centramos el bloque de texto */
            box-shadow: 0 1px 2px rgba(0,0,0,0.06);
        }
    
        .kv-icon {
            position: absolute;              /* 🔹 icono “flotante” a la izquierda */
            left: 0.6rem;
            top: 50%;
            transform: translateY(-50%);
            font-size: 1.6rem;
        }
        /* Bloque de textos (label + número) */
        .kv-text-block {
            width: 100%;                     /* 🔹 bloque ocupa todo el ancho */
            display: flex;
            flex-direction: column;
            align-items: center;             /* 🔹 centrado horizontal */
            text-align: center;
        }
        .kv-item-label {
            font-size: 0.8rem;
            color: #555;
            margin-bottom: 0.15rem;
        }
    
        .kv-item-value {
            font-size: 3rem;
            font-weight: 600;
            color: #0078d4;
            line-height: 1.1;
        }
        .header-bar {
            padding: 0.6rem 0.75rem;
            margin-bottom: 10px;
        }

        .task-card {
            padding: 12px 12px;
        }

        h1 {
            font-size: 1.25rem !important;
            margin-bottom: 0.4rem !important;
        }
        h2 {
            font-size: 1.05rem !important;
            margin-bottom: 0.3rem !important;
        }

        .store-name {
            font-size: 1.15rem;
        }
        .big-number {
            font-size: 1.5rem;
        }

        /* Etiquetas y textos más pequeños */
        label, .stTextInput label, .stMetric label {
            font-size: 0.85rem !important;
        }

        .stButton>button {
            padding-top: 0.35rem;
            padding-bottom: 0.35rem;
            font-size: 0.9rem;
        }
    }
    /* Ajuste extra para la pantalla de ejecución en móvil */
@media (max-width: 600px) {
    .task-card {
        padding: 10px 12px;
        margin-bottom: 8px;
    }
    .store-name {
        font-size: 1.1rem;
        margin-bottom: 0.1rem;
    }
    .stMetric {
        margin-bottom: 0 !important;
    }
}


    </style>
    """, unsafe_allow_html=True)


# ==========================================
# GESTIÓN DEL ESTADO (SESSION STATE)
# ==========================================
if 'current_screen' not in st.session_state:
    st.session_state.current_screen = 'screen_file_selection'

if 'file_data' not in st.session_state:
    st.session_state.file_data = pd.DataFrame()

if 'scanned_codes' not in st.session_state:
    st.session_state.scanned_codes = []

if 'session_tasks' not in st.session_state:
    st.session_state.session_tasks = pd.DataFrame()

if 'current_task_index' not in st.session_state:
    st.session_state.current_task_index = 0

if 'processed_ids' not in st.session_state:
    st.session_state.processed_ids = []

# token y archivos de OneDrive en sesión
if 'graph_token' not in st.session_state:
    st.session_state.graph_token = None

if 'onedrive_files' not in st.session_state:
    st.session_state.onedrive_files = []

if 'show_camera' not in st.session_state:
    st.session_state.show_camera = False

if 'scroll_to_top' not in st.session_state:
    st.session_state.scroll_to_top = False


# ==========================================
# FUNCIONES AUXILIARES DE DATOS (MOCK)
# ==========================================
def scroll_to_top():
    """Inyecta JS para mover el scroll al inicio de la página."""
    components.html(
        """
        <script>
        window.scrollTo({top: 0, left: 0, behavior: 'smooth'});
        </script>
        """,
        height=0,
        scrolling=False,
    )

def generate_mock_data():
    data = []
    skus = ['SKU-101', 'SKU-102', '36710325']
    stores = [
        {'id': '20023', 'name': 'Primavera'},
        {'id': '20024', 'name': 'Los Olivos'},
        {'id': '20025', 'name': 'Jockey Plaza'}
    ]
    
    id_counter = 1
    for sku in skus:
        for store in stores:
            for i in range(2):
                data.append({
                    'ID': id_counter,
                    'CodSucDestino': store['id'],
                    'SucDestino': store['name'],
                    'CodArtRipley': sku,          # lo dejamos por si lo necesitas luego
                    'CodArtVenta': sku,           # 🔹 ahora trabajaremos con este
                    'DescArtProveedor': f"ARTICULO GENERICO {sku}",
                    'CANTIDAD': 4,
                    'BULTO': i + 1,
                    'GUIA': '',
                    'COSTO_BASE_UNITARIO': 10.5,
                    'LPNs': f"NA000{id_counter}999",
                    'Estado_Sys': 'Pendiente'
                })
                id_counter += 1
    return pd.DataFrame(data)


def generate_invalid_data():
    """Genera datos con error en LPN para probar validación."""
    df = generate_mock_data()
    df.at[0, 'LPNs'] = '123456'  # No empieza con NA
    return df


# ==========================================
# FUNCIONES DE NAVEGACIÓN
# ==========================================

def navigate_to(screen_name):
    st.session_state.current_screen = screen_name
    st.rerun()

def reset_session():
    st.session_state.scanned_codes = []
    st.session_state.session_tasks = pd.DataFrame()
    st.session_state.current_task_index = 0
    st.session_state.processed_ids = []
    navigate_to('screen_scan')


# ==========================================
# FUNCIONES ONEDRIVE / MS GRAPH
# ==========================================

def get_access_token():
    """Obtiene (y cachea) un access token de Microsoft Graph usando MSAL (device code)."""
    if st.session_state.graph_token:
        return st.session_state.graph_token

    app = msal.PublicClientApplication(client_id=CLIENT_ID, authority=AUTHORITY)

    # Intentar token en caché
    accounts = app.get_accounts()
    result = None
    if accounts:
        result = app.acquire_token_silent(SCOPES, account=accounts[0])

    if not result:
        # Flujo de dispositivo: muestra código en pantalla para que el usuario lo introduzca en la URL indicada
        flow = app.initiate_device_flow(scopes=SCOPES)
        if "user_code" not in flow:
            st.error("No se pudo iniciar el flujo de autenticación con Microsoft.")
            return None

        st.warning(
            "Para conectar con OneDrive:\n\n"
            f"1. Abre la URL: **{flow['verification_uri']}**\n"
            f"2. Introduce el código: **{flow['user_code']}**\n"
            "3. Inicia sesión con tu cuenta de Microsoft.\n\n"
            "La app continuará automáticamente cuando termines."
        )
        result = app.acquire_token_by_device_flow(flow)

    if "access_token" in result:
        st.session_state.graph_token = result["access_token"]
        return result["access_token"]
    else:
        st.error(f"Error obteniendo token: {result.get('error_description')}")
        return None


def list_onedrive_files():
    """Lista archivos de la carpeta ONEDRIVE_FOLDER_PATH en OneDrive."""
    token = get_access_token()
    if not token:
        return []

    headers = {"Authorization": f"Bearer {token}"}
    url = f"{GRAPH_BASE}/me/drive/root:{ONEDRIVE_FOLDER_PATH}:/children"

    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        st.error(f"No se pudieron listar archivos ({resp.status_code}).")
        st.error(resp.text)
        return []

    items = resp.json().get("value", [])
    # Filtrar solo Excel (.xlsx)
    excel_files = [
        item for item in items
        if item.get("file") and item["name"].lower().endswith(".xlsx")
    ]
    return excel_files


def load_excel_from_onedrive(item_id: str) -> pd.DataFrame | None:
    """Descarga un Excel por id de OneDrive y lo carga en un DataFrame."""
    token = get_access_token()
    if not token:
        return None

    headers = {"Authorization": f"Bearer {token}"}
    url = f"{GRAPH_BASE}/me/drive/items/{item_id}/content"

    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        st.error(f"No se pudo descargar el archivo ({resp.status_code}).")
        st.error(resp.text)
        return None

    try:
        return pd.read_excel(BytesIO(resp.content))
    except Exception as e:
        st.error(f"Error leyendo el Excel descargado: {e}")
        return None


# ==========================================
# HEADER COMÚN
# ==========================================
def render_header():
    subtitle_map = {
        'screen_file_selection': 'Selección',
        'screen_scan': 'Escaneo',
        'screen_execution': 'Ejecución',
        'screen_audit_main': 'Auditoría',
        'screen_audit_details': 'Sobrantes'
    }
    subtitle = subtitle_map.get(st.session_state.current_screen, '')
    
    st.markdown(f"""
    <div class="header-bar">
        <div>
            <strong>Put To Store</strong> | {subtitle}
        </div>
        <div>
            <span style="background-color: white; color: #0078d4; border-radius: 50%; padding: 5px 10px; font-weight: bold;">U</span>
            Usuario CD
        </div>
    </div>
    """, unsafe_allow_html=True)


# ==========================================
# PANTALLAS (VISTAS)
# ==========================================
# --- FASE A: SELECCIÓN DE ARCHIVO ---
def validate_and_set_file(df: pd.DataFrame, source_name: str = "archivo"):
    """Normaliza columnas, valida LPNs y guarda la tabla base en session_state."""
    df = df.copy()
    df.columns = df.columns.str.strip()

    # Mapear nombres del Excel a nombres internos (ajusta si tus columnas tienen otros nombres)
    rename_map = {
        'Cod Art Ripley': 'CodArtRipley',
        'Cod Art Venta': 'CodArtVenta',
        'Cod Suc Destino': 'CodSucDestino',
        'Suc Destino': 'SucDestino',
        'Desc Art Proveedor (Case Pack)': 'DescArtProveedor',
        'COSTO BASE UNITARIO': 'COSTO_BASE_UNITARIO',
    }
    for old, new in rename_map.items():
        if old in df.columns and new not in df.columns:
            df = df.rename(columns={old: new})

    required_cols = [
        'ID',
        'CodSucDestino',
        'SucDestino',
        'CodArtVenta',           # 🔹 clave base
        'CANTIDAD',
        'BULTO',
        'COSTO_BASE_UNITARIO',
        'LPNs',
    ]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        st.error("❌ El {} no tiene las columnas obligatorias: {}".format(
            source_name, ", ".join(missing)))
        return

    # Asegurar columna Estado_Sys
    if 'Estado_Sys' not in df.columns:
        df['Estado_Sys'] = 'Pendiente'
    else:
        df['Estado_Sys'] = df['Estado_Sys'].fillna('Pendiente')

    # Validar LPNs
    invalid_lpns = df[~df['LPNs'].astype(str).str.startswith('NA')]
    if not invalid_lpns.empty:
        st.error("❌ Error: Se encontraron LPNs que no inician con 'NA'.")
        return

    # Si todo bien, guardamos
    st.session_state.file_data = df
    st.success(f"✅ {source_name} válido. {len(df)} registros cargados.")
    time.sleep(1)
    navigate_to('screen_scan')

def screen_file_selection():
    st.title("Seleccionar Archivo Base")
    st.caption(f"📂 Ruta: {ONEDRIVE_FOLDER_LABEL}")

    col1, col2 = st.columns(2)
    
    # ================== OPCIÓN ONEDRIVE REAL ==================
    with col1:
        st.markdown("### Archivos en OneDrive")
        if st.button("🔐 Conectar y listar archivos", use_container_width=True):
            with st.spinner("Conectando con OneDrive y listando archivos..."):
                files = list_onedrive_files()
                st.session_state.onedrive_files = files
                if files:
                    st.success(f"Se encontraron {len(files)} archivos en la carpeta.")
                else:
                    st.info("La carpeta no contiene archivos .xlsx.")

        files = st.session_state.onedrive_files
        if files:
            st.markdown("#### Selecciona un archivo:")
            for item in files:
                if st.button(f"📄 {item['name']}", key=item["id"], use_container_width=True):
                    with st.spinner("Descargando y validando estructura..."):
                        df = load_excel_from_onedrive(item["id"])
                        if df is None:
                            continue
                        # Aquí podrías hacer validaciones adicionales, por ahora asumimos que la estructura coincide
                        # con tus columnas actuales: CodSucDestino, CodArtRipley, etc.
                        # Si tu Excel tiene otros nombres, aquí los puedes renombrar.
                        st.session_state.file_data = df
                        st.success(f"✅ Archivo '{item['name']}' cargado con {len(df)} registros.")
                        time.sleep(1)
                        navigate_to('screen_scan')
        else:
            st.info("Pulsa el botón 'Conectar y listar archivos' para ver los Excel de la carpeta.")

    # ================== OPCIÓN DEMO (MOCK) ==================
    with col2:
        st.markdown("### Cargar archivo local")
        uploaded = st.file_uploader(
            "Selecciona un archivo Excel",
            type=["xlsx"],
            key="local_upload"
        )

        if uploaded is not None:
            with st.spinner("Leyendo y validando archivo..."):
                try:
                    df_local = pd.read_excel(uploaded)
                    validate_and_set_file(df_local, source_name=f"archivo '{uploaded.name}'")
                except Exception as e:
                    st.error(f"❌ No se pudo leer el archivo: {e}")
        st.markdown("### Modo Demo / Pruebas")

        if st.button("📄 Distribucion_Lunes.xlsx (Simular válido)", use_container_width=True):
            with st.spinner("Generando datos de ejemplo..."):
                time.sleep(1)
                df = generate_mock_data()
                # Validación LPN simple
                invalid_lpns = df[~df['LPNs'].astype(str).str.startswith('NA')]
                if not invalid_lpns.empty:
                    st.error("❌ Error: Se encontraron LPNs que no inician con 'NA'.")
                else:
                    st.session_state.file_data = df
                    st.success(f"✅ Archivo de ejemplo válido. {len(df)} registros cargados.")
                    time.sleep(1)
                    navigate_to('screen_scan')

        if st.button("📄 Error_LPN.xlsx (Simular error)", use_container_width=True):
            with st.spinner("Validando..."):
                time.sleep(1)
                df = generate_invalid_data()
                st.error("❌ Validación fallida: En la fila 1, el campo 'LPNs' tiene el valor '123456'. Todos los LPNs deben comenzar con 'NA'.")


# --- FASE B: ESCANEO ---
def screen_scan():
    st.title("Escanear Códigos")

    # =========================
    # 1) Entrada manual
    # =========================
    with st.form("scan_form", clear_on_submit=True):
        col_in, col_btn = st.columns([3, 1])
        with col_in:
            code_input = st.text_input(
                "Ingrese SKU o Código",
                placeholder="Ej: 36710325"
            )
        with col_btn:
            st.markdown("<br>", unsafe_allow_html=True)
            submitted = st.form_submit_button("Agregar ➕")

        if submitted and code_input:
            code_input = code_input.strip()
            if not code_input:
                st.warning("Ingrese un código válido.")
            elif code_input in st.session_state.scanned_codes:
                st.warning(f"⚠️ El código {code_input} ya está en la lista.")
            else:
                st.session_state.scanned_codes.append(code_input)
                st.success(f"Código {code_input} agregado.")

    # =========================
    # 2) Escaneo con cámara
    # =========================

    with st.expander("📷 Escanear con cámara", expanded=False):
        if not st.session_state.show_camera:
            st.caption("Pulsa el botón para abrir la cámara del dispositivo.")
            if st.button("Activar cámara 📷", key="btn_open_cam"):
                st.session_state.show_camera = True
                st.rerun()
        else:
            st.caption("La cámara está activa. Toma una foto del código de barras.")
            cam_img = st.camera_input(
                "Usar cámara del dispositivo",
                key="cam_input",
                label_visibility="collapsed"
            )

            # Botón para cerrar la cámara (opcional)
            if st.button("Cerrar cámara ✖️", key="btn_close_cam"):
                st.session_state.show_camera = False
                st.rerun()

            if cam_img is not None:
                image = Image.open(cam_img)
                decoded_objects = decode(image)

                if decoded_objects:
                    cam_code = decoded_objects[0].data.decode("utf-8").strip()
                    if cam_code:
                        if cam_code in st.session_state.scanned_codes:
                            st.info(f"El código {cam_code} ya está en la lista.")
                        else:
                            st.session_state.scanned_codes.append(cam_code)
                            st.success(f"Código {cam_code} agregado desde cámara.")
                    else:
                        st.error("No se pudo interpretar el código leído.")
                else:
                    st.error("No se detectó ningún código de barras en la imagen. Intenta acercar más la cámara.")

    # =========================
    # 3) Botón Demo (opcional)
    # =========================
    if st.button("Simular Escaneo (Demo)"):
        demos = ['SKU-101', '36710325']
        for d in demos:
            if d not in st.session_state.scanned_codes:
                st.session_state.scanned_codes.append(d)
        st.rerun()

    # =========================
    # 4) Lista de códigos
    # =========================
    st.subheader(f"Códigos en sesión ({len(st.session_state.scanned_codes)})")

    if st.session_state.scanned_codes:
        df_codigos = pd.DataFrame(
            {"Código": st.session_state.scanned_codes}
        )
        st.dataframe(
            df_codigos,
            use_container_width=True,
            height=160
        )

        if st.button("Limpiar lista", type="primary"):
            st.session_state.scanned_codes = []
            st.rerun()
    else:
        st.info("No hay códigos escaneados.")

    st.divider()

    # =========================
    # 5) Cargar Tareas
    # =========================
    if st.button("Cargar Tareas ➡️", type="primary", use_container_width=True):
        if not st.session_state.scanned_codes:
            st.error("Debe agregar al menos un código.")
        else:
            full_df = st.session_state.file_data
            if full_df.empty:
                st.error("No hay datos cargados. Vuelva al inicio.")
                return

            tasks = full_df[
                (full_df['CodArtVenta'].astype(str).isin(st.session_state.scanned_codes)) &
                (full_df['Estado_Sys'] == 'Pendiente')
            ]

            if tasks.empty:
                st.warning("No se encontraron tareas pendientes para estos códigos.")
            else:
                st.session_state.session_tasks = tasks.reset_index(drop=True)  # Reset index importante
                st.session_state.current_task_index = 0
                st.session_state.processed_ids = []
                st.success(f"Se cargaron {len(tasks)} tareas.")
                time.sleep(1)
                navigate_to('screen_execution')



# --- FASE C: EJECUCIÓN (PTS) ---
def screen_execution():
    tasks = st.session_state.session_tasks
    idx = st.session_state.current_task_index
    total = len(tasks)
    
    # 👇 Si está marcado, subimos el scroll y apagamos el flag
    if st.session_state.get('scroll_to_top', False):
        scroll_to_top()
        st.session_state.scroll_to_top = False

    if idx >= total:
        st.warning("Índice fuera de rango. Redirigiendo...")
        navigate_to('screen_audit_main')
        return

    current_task = tasks.iloc[idx]

    # --- TARJETA COMPACTA DE LA TAREA ---
    with st.container():
        st.markdown('<div class="task-card">', unsafe_allow_html=True)

        # Fila superior: ID + progreso "Tarea x de y"
        col_top1, col_top2 = st.columns([2.5, 1])
        with col_top1:
            st.caption(f"ID Base: {current_task['ID']}")
            st.markdown(
                f"<div class='store-name'>{current_task['CodSucDestino']} - "
                f"{current_task['SucDestino']}</div>",
                unsafe_allow_html=True
            )
        with col_top2:
            st.markdown(
                f"<div style='text-align:right; font-size:0.8rem; color:#555;'>"
                f"Tarea {idx + 1} de {total}</div>",
                unsafe_allow_html=True
            )

        st.markdown("---")

        # Detalle de producto + métricas en 2 columnas
        col_det1, col_det2 = st.columns([2, 1])
        with col_det1:
            st.markdown("**Producto / Cod. Venta**")
            st.text(f"{current_task['CodArtVenta']}")
            st.caption(current_task['DescArtProveedor'])
                    
        # 🔹 Cant y Bulto en la misma fila, con icono a la izquierda
        st.markdown(
            f"""
            <div class="kv-row">
                <div class="kv-box">
                    <div class="kv-icon">#️⃣</div>
                    <div class="kv-text-block">
                        <div class="kv-item-label">Cant.</div>
                        <div class="kv-item-value">{current_task['CANTIDAD']}</div>
                    </div>
                </div>
                <div class="kv-box">
                    <div class="kv-icon">📦</div>
                    <div class="kv-text-block">
                        <div class="kv-item-label">Bulto</div>
                        <div class="kv-item-value">{current_task['BULTO']}</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown("---")
        

        # Datos logísticos
        st.markdown(f"**LPN Teórico:** `{current_task['LPNs']}`")
        st.text_input(
            "Guía (Opcional)",
            key=f"guia_{current_task['ID']}",
            label_visibility="visible",
            placeholder="Escanee guía si aplica..."
        )

        # Botones dentro de la tarjeta, así quedan más arriba en móvil
        col_confirm, col_cancel = st.columns([3, 1])
        with col_confirm:
            if st.button("CONFIRMAR ✅", type="primary", use_container_width=True):
                st.session_state.processed_ids.append(current_task['ID'])
                st.session_state.current_task_index += 1
                # Guardar ID procesado
                st.session_state.processed_ids.append(current_task['ID'])
                # Avanzar
                st.session_state.current_task_index += 1

                if st.session_state.current_task_index >= len(st.session_state.session_tasks):
                    st.success("¡Lote finalizado!")
                    time.sleep(0.5)
                    navigate_to('screen_audit_main')
                else:
                    st.success("Tarea confirmada")
                    time.sleep(0.2)
                    st.rerun()

        with col_cancel:
            if st.button(
                "Cancelar ❌",
                use_container_width=True,
                key=f"btn_cancel_{current_task['ID']}"
            ):
                if st.session_state.get('confirm_cancel', False):
                    reset_session()
                else:
                    st.warning("Presione de nuevo para confirmar cancelación")
                    st.session_state.confirm_cancel = True

        st.markdown('</div>', unsafe_allow_html=True)



# --- FASE D: AUDITORÍA (MAIN) ---
def screen_audit_main():
    st.title("Auditoría de Lote")
    
    st.success("✅ Se han procesado todas las tareas asignadas a esta sesión.")
    
    st.info("⚠️ Control de Inventario: ¿Se detectó algún sobrante físico después de surtir?")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Confirmar PTS (Sin Sobrantes) 👍", type="primary", use_container_width=True):
            finish_batch_process()
            st.balloons()
            st.success("Proceso finalizado. Estado actualizado a 'Completado'.")
            time.sleep(3)
            reset_session()

    with col2:
        if st.button("Menú Sobrantes 📋", use_container_width=True):
            navigate_to('screen_audit_details')


# --- FASE D: AUDITORÍA (DETALLES) ---
def screen_audit_details():
    st.title("Regularización de Sobrantes")
    
    if st.button("⬅️ Atrás"):
        navigate_to('screen_audit_main')

    processed_tasks = st.session_state.session_tasks
    unique_codes = processed_tasks['CodArtVenta'].unique()
    selected_code = st.selectbox("Seleccione código con sobrante:", unique_codes)
    
    if selected_code:
        sku_data = processed_tasks[processed_tasks['CodArtVenta'] == selected_code]
        summary = sku_data.groupby(['CodSucDestino', 'SucDestino'])['CANTIDAD'].sum().reset_index()
        
        # 🔹 Forzamos a texto para evitar errores de numpy/pandas
        summary['Sucursal'] = (
            summary['CodSucDestino'].astype(str).fillna("") + " - " +
            summary['SucDestino'].astype(str).fillna("")
        )
  
        st.subheader("Resumen por Tienda")
        st.dataframe(
            summary[['Sucursal', 'CANTIDAD']], 
            hide_index=True, 
            use_container_width=True
        )
        
        st.info("ℹ️ Use esta información para validar físicamente dónde ocurrió el error.")
        
        st.markdown("---")
        
        if st.button("Confirmar Regularización 🔴", type="primary"):
            finish_batch_process()
            st.success("Regularización guardada y lote cerrado.")
            time.sleep(2)
            reset_session()


def finish_batch_process():
    """Cierra el lote marcando los IDs procesados como 'Completado'."""
    main_df = st.session_state.file_data
    processed = st.session_state.processed_ids
    
    main_df.loc[main_df['ID'].isin(processed), 'Estado_Sys'] = 'Completado'
    st.session_state.file_data = main_df


# ==========================================
# RUTEO PRINCIPAL
# ==========================================

render_header()

if st.session_state.current_screen == 'screen_file_selection':
    screen_file_selection()
elif st.session_state.current_screen == 'screen_scan':
    screen_scan()
elif st.session_state.current_screen == 'screen_execution':
    screen_execution()
elif st.session_state.current_screen == 'screen_audit_main':
    screen_audit_main()
elif st.session_state.current_screen == 'screen_audit_details':
    screen_audit_details()
else:
    st.error("Pantalla no encontrada")















