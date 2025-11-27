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
from streamlit_webrtc import webrtc_streamer, VideoProcessorBase, WebRtcMode
import av
import cv2
from pyzbar.pyzbar import decode as decode_barcodes

RTC_CONFIGURATION = {
    "iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]
}

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
        padding: 0.6rem 0.9rem;
        color: white;
        border-radius: 5px;
        margin-bottom: 12px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        box-shadow: 0 2px 6px rgba(0,0,0,0.15);
    }
    .task-card {
        background-color: white;
        padding: 14px;
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
        font-size: 1.2rem;
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
    
if 'processed_original_indices' not in st.session_state:
    st.session_state.processed_original_indices = []

# token y archivos de OneDrive en sesión
if 'graph_token' not in st.session_state:
    st.session_state.graph_token = None

if 'onedrive_files' not in st.session_state:
    st.session_state.onedrive_files = []

if 'show_camera' not in st.session_state:
    st.session_state.show_camera = False

if 'scroll_to_top' not in st.session_state:
    st.session_state.scroll_to_top = False
    
if 'show_base_table' not in st.session_state:
    st.session_state.show_base_table = False


# ==========================================
# FUNCIONES AUXILIARES DE DATOS (MOCK)
# ==========================================
class LiveBarcodeProcessor(VideoProcessorBase):
    """
    Procesa frames de la cámara en vivo y detecta códigos de barras/QR.
    - Define una zona central (ROI) donde se espera el código.
    - Hace zoom digital sobre esa zona.
    - Intenta decodificar códigos con pyzbar.
    - Guarda el último código detectado en self.last_code.
    """
    def __init__(self) -> None:
        self.last_code = None

    def recv(self, frame):
        # Frame de webrtc -> numpy BGR
        img = frame.to_ndarray(format="bgr24")

        # Convertimos a gris
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        h, w = gray.shape
        mw = int(w * 0.2)
        mh = int(h * 0.2)

        # Si por alguna razón el ROI queda muy pequeño, devolvemos imagen sin procesar
        if (h - 2 * mh) <= 0 or (w - 2 * mw) <= 0:
            return av.VideoFrame.from_ndarray(img, format="bgr24")

        # Zona central (60% central aprox.)
        roi = gray[mh:h - mh, mw:w - mw]

        # Zoom digital
        roi_big = cv2.resize(
            roi,
            None,
            fx=1.8,
            fy=1.8,
            interpolation=cv2.INTER_LINEAR
        )

        # Intentamos decodificar sólo en el ROI agrandado
        decoded = decode_barcodes(roi_big)

        code = None
        obj_rect = None
        if decoded:
            obj = decoded[0]
            code = obj.data.decode("utf-8", "ignore").strip()
            obj_rect = obj.rect

        # Si encontramos código, lo guardamos
        if code:
            self.last_code = code

        # Dibujamos el rectángulo del ROI en la imagen original para guiar al usuario
        cv2.rectangle(
            img,
            (mw, mh),
            (w - mw, h - mh),
            (255, 255, 255),
            1,
        )

        # Si tenemos rectángulo del código, lo aproximamos a la imagen original
        if obj_rect:
            x, y, rw, rh = obj_rect

            # revertimos el zoom (x1.8) y sumamos el offset del recorte
            x = int(x / 1.8) + mw
            y = int(y / 1.8) + mh
            rw = int(rw / 1.8)
            rh = int(rh / 1.8)

            cv2.rectangle(img, (x, y), (x + rw, y + rh), (0, 255, 0), 2)
            cv2.putText(
                img,
                code,
                (x, y - 8),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2,
            )

        # Devolvemos SIEMPRE un frame para que la cámara se vea
        return av.VideoFrame.from_ndarray(img, format="bgr24")



def screen_base_table():
    st.title("Tabla Base - Resumen")

    # Botón para volver al menú de escaneo
    if st.button("⬅️ Volver a Escanear Códigos", key="btn_volver_scan"):
        navigate_to('screen_scan')
        return

    base_df = st.session_state.file_data

    if base_df.empty:
        st.warning("No hay tabla base cargada. Vuelva a **Seleccionar Archivo Base**.")
        return

    # ---------------------
    # Datos generales
    # ---------------------
    pendientes = base_df[base_df['Estado_Sys'] == 'Pendiente']

    unidades_pendientes = pendientes['CANTIDAD'].sum() if not pendientes.empty else 0
    codigos_pendientes = pendientes['CodArtVenta'].nunique() if not pendientes.empty else 0

    col_kpi1, col_kpi2 = st.columns(2)
    with col_kpi1:
        st.metric("Unidades Pendientes", int(unidades_pendientes))
    with col_kpi2:
        st.metric("Códigos Pendientes", int(codigos_pendientes))

    st.markdown("---")

    # ---------------------
    # Filtro por Estado_Sys
    # ---------------------
    estados_unicos = (
        base_df['Estado_Sys']
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )
    estados_unicos = sorted(estados_unicos)
    opciones = ["Todos"] + estados_unicos

    estado_sel = st.selectbox(
        "Filtrar por Estado_Sys:",
        opciones,
        index=0,
        key="filtro_estado_sys_base"
    )

    if estado_sel == "Todos":
        df_mostrar = base_df
    else:
        df_mostrar = base_df[base_df['Estado_Sys'].astype(str) == estado_sel]

    st.subheader("Detalle de Tabla Base")
    st.dataframe(
        df_mostrar,
        hide_index=True,
        use_container_width=True
    )

def scroll_to_top():
    """Sube el scroll al inicio de la app (incluye un pequeño delay para que el layout termine de renderizar)."""
    components.html(
        """
        <html>
        <body>
        <script>
        (function() {
            function doScroll() {
                try {
                    // App de Streamlit suele estar en un iframe, así que usamos window.parent
                    var parentWindow = window.parent || window;
                    // Contenedor principal del contenido
                    var mainSection = parentWindow.document.querySelector('section.main') 
                                      || parentWindow.document.querySelector('main')
                                      || parentWindow.document.body;

                    if (mainSection && mainSection.scrollTo) {
                        mainSection.scrollTo({top: 0, left: 0, behavior: 'smooth'});
                    } else if (parentWindow.scrollTo) {
                        parentWindow.scrollTo({top: 0, left: 0, behavior: 'smooth'});
                    } else {
                        window.scrollTo(0, 0);
                    }
                } catch (e) {
                    // Fallback simple dentro del propio iframe
                    window.scrollTo(0, 0);
                }
            }
            // Pequeño delay para asegurarnos de que el DOM ya está cargado
            setTimeout(doScroll, 50);
        })();
        </script>
        </body>
        </html>
        """,
        height=0,
        width=0,
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
                    'LPNs': '',
                    'Estado_Sys': 'Pendiente'
                })
                id_counter += 1
    return pd.DataFrame(data)


def generate_invalid_data():
    """Genera datos con error en LPN para probar validación."""
    df = generate_mock_data()
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
    st.session_state.processed_original_indices = []
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
    # ------------------------------------------------------------------
    # CABECERA: Título + botón "Ver tabla base" en la MISMA fila
    # ------------------------------------------------------------------
    header_col1, header_col2 = st.columns([3, 1])

    with header_col1:
        # Título un poco más compacto que st.title
        st.subheader("Escanear Códigos")

    with header_col2:
        if st.button(
            "Ver tabla base 📊",
            key="btn_ver_tabla_base",
            use_container_width=True,
        ):
            navigate_to("screen_base_table")
            return  # salimos de esta vista

    st.write("")  # pequeño espacio

    # ------------------------------------------------------------------
    # 1) FORMULARIO DE ENTRADA MANUAL (input + botón en la misma fila)
    # ------------------------------------------------------------------
    with st.form("scan_form_manual", clear_on_submit=True):
        col_in, col_btn = st.columns([4, 1])

        code_input = col_in.text_input(
            "Ingrese SKU o Código",
            placeholder="Ej: 36710325",
            key="txt_manual_code",
        )

        # 👇 importante: usamos form_submit_button DESDE LA COLUMNA
        submitted = col_btn.form_submit_button(
            "Agregar ➕",
            use_container_width=True,
        )

        if submitted and code_input:
            code_input = str(code_input).strip()
            if code_input in st.session_state.scanned_codes:
                st.warning(f"⚠️ El código {code_input} ya está en la lista.")
            else:
                st.session_state.scanned_codes.append(code_input)
                st.success(f"Código {code_input} agregado.")

    # ------------------------------------------------------------------
    # 2) ESCÁNER EN VIVO CON CÁMARA (TRASERA)
    # ------------------------------------------------------------------
    st.markdown("### Escanear con cámara (en vivo)")
    st.caption(
        "Apunte el código dentro del recuadro. "
        "Cuando lo tenga enfocado, pulse **'Validar código detectado'** "
        "para agregarlo a la lista."
    )

    webrtc_ctx = webrtc_streamer(
        key="barcode-scanner-live",
        video_processor_factory=LiveBarcodeProcessor,
        media_stream_constraints={
            "video": {
                # 👇 intenta siempre usar la cámara trasera
                "facingMode": {"ideal": "environment"}
            },
            "audio": False,
        },
        async_processing=True,
    )

    detected_code = None
    if webrtc_ctx and webrtc_ctx.video_processor:
        detected_code = webrtc_ctx.video_processor.last_code

    if st.button("Validar código detectado ✅", key="btn_use_camera_code"):
        if not detected_code:
            st.warning("Todavía no se ha detectado ningún código en la cámara.")
        else:
            detected_code = str(detected_code).strip()
            if detected_code not in st.session_state.scanned_codes:
                st.session_state.scanned_codes.append(detected_code)
                st.success(f"Código {detected_code} agregado desde la cámara.")
            else:
                st.info(f"El código {detected_code} ya está en la lista.")

            # limpiamos para no reutilizarlo en el siguiente frame
            if webrtc_ctx and webrtc_ctx.video_processor:
                webrtc_ctx.video_processor.last_code = None

    # ------------------------------------------------------------------
    # 3) BOTÓN DEMO
    # ------------------------------------------------------------------
    if st.button("Simular Escaneo (Demo)", key="btn_demo_scan"):
        demo_codes = ["SKU-101", "36710325"]
        any_new = False
        for d in demo_codes:
            if d not in st.session_state.scanned_codes:
                st.session_state.scanned_codes.append(d)
                any_new = True
        if any_new:
            st.success("Se agregaron códigos de demostración.")
        else:
            st.info("Los códigos de demo ya estaban en la lista.")

    # ------------------------------------------------------------------
    # 4) LISTA DE CÓDIGOS EN SESIÓN
    # ------------------------------------------------------------------
    st.subheader(f"Códigos en sesión ({len(st.session_state.scanned_codes)})")

    if st.session_state.scanned_codes:
        st.table(pd.DataFrame(st.session_state.scanned_codes, columns=["Código"]))

        if st.button(
            "Limpiar lista",
            type="primary",
            key="btn_limpiar_lista",
        ):
            st.session_state.scanned_codes = []
            st.success("Lista de códigos limpiada.")
            st.rerun()
    else:
        st.info("No hay códigos escaneados.")

    st.divider()

    # ------------------------------------------------------------------
    # 5) CARGAR TAREAS (USANDO ÍNDICE DE LA TABLA BASE)
    # ------------------------------------------------------------------
    if st.button(
        "Cargar Tareas ➡️",
        type="primary",
        use_container_width=True,
        key="btn_cargar_tareas",
    ):
        if not st.session_state.scanned_codes:
            st.error("Debe agregar al menos un código.")
            return

        if "file_data" not in st.session_state or st.session_state.file_data.empty:
            st.error("No hay datos cargados. Vuelva a **Seleccionar Archivo Base**.")
            return

        base_df = st.session_state.file_data.reset_index(drop=True)
        st.session_state.file_data = base_df  # guardamos de vuelta

        df = base_df.copy()
        df["CodArtVenta"] = df["CodArtVenta"].astype(str)
        scanned = [str(c).strip() for c in st.session_state.scanned_codes]

        mask = (df["CodArtVenta"].isin(scanned)) & (df["Estado_Sys"] == "Pendiente")
        tasks = df.loc[mask].copy()

        if tasks.empty:
            st.warning("No se encontraron tareas pendientes para estos códigos.")
        else:
            # guardamos el índice real como identificador único
            tasks["_row_index"] = tasks.index
            st.session_state.session_tasks = tasks.reset_index(drop=True)
            st.session_state.current_task_index = 0
            st.session_state.processed_ids = []
            st.success(f"Se cargaron {len(tasks)} tareas.")
            time.sleep(0.8)
            navigate_to("screen_execution")




# --- FASE C: EJECUCIÓN (PTS) ---
def screen_execution():
    tasks = st.session_state.session_tasks
    idx = st.session_state.current_task_index
    total = len(tasks)

    # Scroll-to-top opcional
    if st.session_state.get("scroll_to_top", False):
        scroll_to_top()
        st.session_state.scroll_to_top = False

    if idx >= total:
        st.warning("Índice fuera de rango. Redirigiendo...")
        navigate_to("screen_audit_main")
        return

    current_task = tasks.iloc[idx]

    # Índice real en la tabla base
    row_idx = int(current_task.get("_row_index", idx))
    row_no = row_idx + 1  # para mostrar 1,2,3... en pantalla

    # --- TARJETA COMPACTA DE LA TAREA ---
    with st.container():
        st.markdown('<div class="task-card">', unsafe_allow_html=True)

        # Fila superior: ID Base (número de registro) + "Tarea x de y"
        col_top1, col_top2 = st.columns([2.5, 1])
        with col_top1:
            st.caption(f"ID Base: {row_no}")
            st.markdown(
                f"<div class='store-name'>{current_task['CodSucDestino']} - "
                f"{current_task['SucDestino']}</div>",
                unsafe_allow_html=True,
            )
        with col_top2:
            st.markdown(
                f"<div style='text-align:right; font-size:0.8rem; color:#555;'>"
                f"Tarea {idx + 1} de {total}</div>",
                unsafe_allow_html=True,
            )

        st.markdown("---")

        # Detalle de producto
        col_det1, col_det2 = st.columns([2, 1])
        with col_det1:
            st.markdown("**Producto / Cod. Venta**")
            st.text(f"{current_task['CodArtVenta']}")
            st.caption(current_task["DescArtProveedor"])

        # Cant y Bulto en la misma fila (usa tu CSS kv-row / kv-box existente)
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
            unsafe_allow_html=True,
        )

        st.markdown("---")

        # Datos logísticos
        st.markdown(f"**LPN Teórico:** `{current_task['LPNs']}`")
        guia = st.text_input(
            "Guía (Opcional)",
            key=f"guia_{row_idx}",
            label_visibility="visible",
            placeholder="Escanee guía si aplica...",
        )

        st.write("")

        # Botones de acción
        col_confirm, col_cancel = st.columns([3, 1])

        with col_confirm:
            if st.button(
                "CONFIRMAR ✅",
                type="primary",
                use_container_width=True,
                key=f"btn_confirm_{row_idx}",
            ):
                # Guardamos índice REAL de la tabla base
                st.session_state.processed_ids.append(row_idx)
                st.session_state.current_task_index += 1
                st.session_state.scroll_to_top = True

                if st.session_state.current_task_index >= len(
                    st.session_state.session_tasks
                ):
                    st.success("¡Lote finalizado!")
                    time.sleep(0.5)
                    navigate_to("screen_audit_main")
                else:
                    st.success("Tarea confirmada")
                    time.sleep(0.2)
                    st.rerun()

        with col_cancel:
            if st.button(
                "Cancelar ❌",
                use_container_width=True,
                key=f"btn_cancel_{row_idx}",
            ):
                if st.session_state.get("confirm_cancel", False):
                    reset_session()
                else:
                    st.warning("Presione de nuevo para confirmar cancelación")
                    st.session_state.confirm_cancel = True

        st.markdown("</div>", unsafe_allow_html=True)



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

    # Tareas trabajadas en la sesión
    processed_tasks = st.session_state.session_tasks

    # 👉 ahora por CodArtVenta (antes era CodArtRipley)
    unique_skus = processed_tasks['CodArtVenta'].unique()
    selected_sku = st.selectbox("Seleccione código con sobrante:", unique_skus)

    if selected_sku:
        # Filtrar por el código seleccionado
        sku_data = processed_tasks[processed_tasks['CodArtVenta'] == selected_sku]

        # 🔹 Agrupar por sucursal Y por bulto
        summary = (
            sku_data
            .groupby(['CodSucDestino', 'SucDestino', 'BULTO'])['CANTIDAD']
            .sum()
            .reset_index()
        )

        # Construimos texto de sucursal como string (evita errores de tipos)
        summary['Sucursal'] = (
            summary['CodSucDestino'].astype(str).fillna("") + " - " +
            summary['SucDestino'].astype(str).fillna("")
        )

        # Ordenar un poco la tabla (opcional)
        summary = summary.sort_values(['CodSucDestino', 'BULTO'])

        st.subheader("Resumen por Tienda y Bulto")
        st.dataframe(
            summary[['Sucursal', 'BULTO', 'CANTIDAD']],
            hide_index=True,
            use_container_width=True
        )

        st.info("ℹ️ Use esta información para validar físicamente sobrantes por tienda y bulto.")

        st.markdown("---")

        if st.button("Confirmar Regularización 🔴", type="primary"):
            finish_batch_process()
            st.success("Regularización guardada y lote cerrado.")
            time.sleep(2)
            reset_session()


def finish_batch_process():
    """
    Marca como 'Completado' en la tabla base (file_data)
    sólo las filas cuyos índices están en processed_ids.
    """
    if "file_data" not in st.session_state or st.session_state.file_data.empty:
        st.warning("No hay tabla base cargada en memoria.")
        return

    if "processed_ids" not in st.session_state or not st.session_state.processed_ids:
        st.warning("No hay tareas procesadas en esta sesión.")
        return

    main_df = st.session_state.file_data.copy().reset_index(drop=True)

    # Índices únicos y válidos
    idxs = sorted(
        set(
            int(i)
            for i in st.session_state.processed_ids
            if isinstance(i, (int, float)) and 0 <= int(i) < len(main_df)
        )
    )

    if not idxs:
        st.warning("No se encontró ningún registro en la base para esos índices.")
        return

    main_df.loc[idxs, "Estado_Sys"] = "Completado"
    st.session_state.file_data = main_df
    st.info(f"Se marcaron {len(idxs)} registros como 'Completado'.")




# ==========================================
# RUTEO PRINCIPAL
# ==========================================

render_header()

if st.session_state.current_screen == 'screen_file_selection':
    screen_file_selection()
elif st.session_state.current_screen == 'screen_scan':
    screen_scan()
elif st.session_state.current_screen == 'screen_base_table':   # 👈 NUEVA
    screen_base_table()
elif st.session_state.current_screen == 'screen_execution':
    screen_execution()
elif st.session_state.current_screen == 'screen_audit_main':
    screen_audit_main()
elif st.session_state.current_screen == 'screen_audit_details':
    screen_audit_details()
else:
    st.error("Pantalla no encontrada")











































