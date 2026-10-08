import io
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from database import Database
from excel_web import (
    analizar_excel, cargar_excel, leer_hojas, normalizar_product_owner, filtrar_adjunto
)
from auth import iniciar_sesion, cerrar_sesion
from usuarios import (
    mostrar_modulo_usuarios, encabezado_ventana, ficha, seccion, obtener_pods,
    obtener_usuarios, obtener_cliente_admin
)
from correo import configuracion_correo, enviar_correo_backlog, nombre_backlog
from pods import mostrar_modulo_pods

# Tiempo máximo (segundos) que se reutilizan los datos consultados entre
# interacciones. Cualquier cambio guardado limpia la caché de inmediato.
TTL_CACHE = 60

st.set_page_config(
    page_title="PODEX - Sistema de Gestión POD's Extendidos",
    page_icon="📋",
    layout="wide"
)

# ============================================================
# OCULTAR BARRA SUPERIOR NATIVA DE STREAMLIT
# ============================================================
st.markdown("""
<style>
/* Barra superior de Streamlit (Share, estrella, editar, menú) */
header[data-testid="stHeader"],
[data-testid="stToolbar"],
[data-testid="stDecoration"] {
    display: none !important;
    visibility: hidden !important;
    height: 0 !important;
    min-height: 0 !important;
}

/* Eliminar el espacio que deja la barra superior */
.block-container {
    padding-top: 0.5rem !important;
}
</style>
""", unsafe_allow_html=True)

# ============================================================
# AUTENTICACIÓN Y USUARIO ACTUAL
# ============================================================

def obtener_usuario_por_auth_id(auth_user_id):
    """Obtiene el usuario de PODEX asociado al usuario autenticado en Supabase."""
    db = Database()
    try:
        db.conectar()
        db.execute(
            """
            SELECT "USUARIO", "PERFIL", "NOMBRE"
            FROM public."USUARIOS"
            WHERE "AUTH_USER_ID" = %s
            LIMIT 1
            """,
            (auth_user_id,)
        )
        registro = db.fetchone()

        if not registro:
            return None

        return {
            "USUARIO": registro[0],
            "PERFIL": registro[1],
            "NOMBRE": registro[2],
        }
    finally:
        db.cerrar()


def mostrar_login():
    """Muestra el inicio de sesión: logo a la izquierda y acceso a la derecha."""

    st.markdown(
        """
        <style>
        /* ======================================================
           PANTALLA DE LOGIN (colores del logo PODEX)
           ====================================================== */
        [data-testid="stSidebar"] { display: none !important; }
        header[data-testid="stHeader"] { display: none !important; }
        .block-container, [data-testid="stMainBlockContainer"] {
            padding: 0 !important;
            max-width: 100% !important;
        }
        /* Los bloques que solo traen estilos no deben ocupar espacio */
        div[data-testid="stElementContainer"]:has(style) { display: none; }
        [data-testid="stMainBlockContainer"] [data-testid="stVerticalBlock"] { gap: 0; }
        [data-testid="stForm"] [data-testid="stVerticalBlock"] { gap: 1rem; }

        div[data-testid="stHorizontalBlock"]:has(.podex-marca) {
            gap: 0 !important;
            min-height: 100vh;
        }

        /* Panel izquierdo: logo sobre degradado claro */
        div[data-testid="stColumn"]:has(.podex-marca) {
            background:
                radial-gradient(circle at 15% 20%, rgba(183, 213, 31, 0.20), transparent 45%),
                radial-gradient(circle at 85% 85%, rgba(15, 115, 95, 0.16), transparent 45%),
                linear-gradient(160deg, #F1F8EC 0%, #E7F3E6 55%, #EEF6DC 100%);
            border-right: 1px solid #DDE9DA;
        }
        div[data-testid="stColumn"]:has(.podex-marca),
        div[data-testid="stColumn"]:has(.podex-acceso) { min-height: 100vh; }
        div[data-testid="stColumn"]:has(.podex-marca) > div,
        div[data-testid="stColumn"]:has(.podex-acceso) > div {
            height: 100%;
            display: flex;
            flex-direction: column;
            justify-content: center;
        }
        div[data-testid="stColumn"]:has(.podex-marca) > div { padding: 2rem 3.5rem; }
        div[data-testid="stColumn"]:has(.podex-acceso) > div { padding: 2rem 1.5rem; }

        div[data-testid="stColumn"]:has(.podex-marca) [data-testid="stElementContainer"],
        div[data-testid="stColumn"]:has(.podex-marca) [data-testid="stImage"] > div {
            width: 100% !important;
        }
        div[data-testid="stColumn"]:has(.podex-marca) [data-testid="stImage"] img {
            display: block;
            margin: 0 auto;
            width: min(320px, 46%) !important;
            max-width: 100%;
            height: auto;
            filter: drop-shadow(0 12px 24px rgba(11, 61, 51, 0.16));
        }

        /* Panel derecho: acceso */
        .podex-acceso { text-align: center; }
        .podex-acceso h3 {
            color: #0B3D33;
            font-weight: 700;
            font-size: 1.75rem !important;
            margin: 0;
            padding: 0 0 0.3rem;
        }
        .podex-acceso p { color: #5E6E69; font-size: 1.05rem; margin: 0 0 1.4rem; }

        div[data-testid="stColumn"]:has(.podex-acceso) [data-testid="stForm"] {
            background: #FFFFFF;
            border: 1px solid #E2EBE4;
            border-radius: 14px;
            box-shadow: 0 10px 30px rgba(11, 61, 51, 0.08);
            padding: 1.6rem 1.6rem 1.2rem;
        }
        div[data-testid="stForm"] input:focus {
            border-color: #0F735F !important;
            box-shadow: 0 0 0 1px #0F735F !important;
        }
        div[data-testid="stFormSubmitButton"] button {
            background: linear-gradient(90deg, #0B5B4D 0%, #0F735F 50%, #7FA82A 100%) !important;
            border: none !important;
            color: #FFFFFF !important;
            border-radius: 8px !important;
            min-height: 44px !important;
            font-weight: 700 !important;
            box-shadow: 0 4px 14px rgba(15, 115, 95, 0.25);
        }
        div[data-testid="stFormSubmitButton"] button:hover { filter: brightness(1.07); }

        .podex-pie {
            text-align: center;
            color: #5E6E69;
            font-size: 0.83rem;
            line-height: 1.5;
            margin-top: 1.8rem;
        }
        .podex-pie p { margin: 0 0 0.8rem; }
        .podex-pie b { color: #0B3D33; }
        .podex-pie .firma { font-size: 0.78rem; letter-spacing: 0.02em; }

        @media (max-width: 640px) {
            div[data-testid="stHorizontalBlock"]:has(.podex-marca),
            div[data-testid="stColumn"]:has(.podex-marca),
            div[data-testid="stColumn"]:has(.podex-acceso) { min-height: auto; }
            div[data-testid="stColumn"]:has(.podex-marca) > div { padding: 2.5rem 1.5rem 2rem; }
            div[data-testid="stColumn"]:has(.podex-acceso) > div { padding: 2rem 1rem; }
            div[data-testid="stColumn"]:has(.podex-marca) [data-testid="stImage"] img {
                width: 46% !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    marca, acceso = st.columns(2)

    with marca:
        st.markdown('<div class="podex-marca"></div>', unsafe_allow_html=True)
        st.image("Logo_PODEX.png", width="stretch")

    with acceso:
        st.markdown(
            """
            <div class="podex-acceso">
                <h3>Bienvenido de nuevo</h3>
                <p>Ingresa con tus credenciales para continuar</p>
            </div>
            """,
            unsafe_allow_html=True
        )

        _, centro, _ = st.columns([0.12, 0.76, 0.12])
        with centro:
            with st.form("form_login"):
                email = st.text_input(
                    "Correo electrónico",
                    placeholder="usuario@dominio.com"
                )
                password = st.text_input(
                    "Contraseña",
                    type="password",
                    placeholder="Ingrese su contraseña"
                )
                ingresar = st.form_submit_button(
                    "Ingresar",
                    type="primary",
                    width="stretch"
                )

        st.markdown(
            """
            <div class="podex-pie">
                <p><b>PODEX</b> · Sistema Integrado de Gestión de Peticiones, Incidentes y Vulnerabilidades<br>
                Acceso protegido mediante autenticación segura.</p>
                <p class="firma">Powered by <b>JAJEROHE Systems</b></p>
            </div>
            """,
            unsafe_allow_html=True
        )

        if ingresar:
            email = email.strip()

            if not email or not password:
                st.warning("⚠️ Debe ingresar el correo electrónico y la contraseña.")
                return

            try:
                with st.spinner("Validando credenciales..."):
                    respuesta = iniciar_sesion(email, password)

                if not respuesta or not getattr(respuesta, "user", None):
                    st.error("❌ No fue posible iniciar sesión.")
                    return

                auth_user_id = str(respuesta.user.id)
                usuario = obtener_usuario_por_auth_id(auth_user_id)

                if not usuario:
                    cerrar_sesion()
                    st.error(
                        "❌ El usuario está autenticado en Supabase, "
                        "pero no está registrado en PODEX."
                    )
                    return

                st.session_state["auth_user_id"] = auth_user_id
                st.session_state["usuario_actual"] = usuario["USUARIO"]
                st.session_state["perfil_actual"] = usuario["PERFIL"]
                st.session_state["nombre_actual"] = usuario["NOMBRE"]
                st.session_state["email_actual"] = email

                st.rerun()

            except Exception:
                st.error(
                    "❌ Correo o contraseña incorrectos, o no fue posible autenticar."
                )


# ============================================================
# CONTROL DE ACCESO
# ============================================================

# El botón circular de cerrar sesión del encabezado es un enlace a ?logout=1.
if st.query_params.get("logout"):
    cerrar_sesion()
    for clave in ["auth_user_id","usuario_actual","perfil_actual","nombre_actual","email_actual","pagina_actual"]:
        st.session_state.pop(clave,None)
    st.query_params.clear()

if "usuario_actual" not in st.session_state:
    mostrar_login()
    st.stop()

usuario_actual = st.session_state["usuario_actual"]
perfil_actual = st.session_state.get("perfil_actual", "")
nombre_actual = st.session_state.get("nombre_actual", "")

# Perfil Administrador: acceso completo a carga y solicitudes.
# Perfil Operador: acceso restringido a las solicitudes de sus POD asignados.
es_administrador = str(perfil_actual or "").strip().lower() == "administrador"

# Página activa del menú lateral: "solicitudes", o "cargar", "usuarios" y
# "pods" (solo administrador).
if "pagina_actual" not in st.session_state or not es_administrador:
    st.session_state["pagina_actual"] = "solicitudes"
pagina_actual = st.session_state["pagina_actual"]

# ============================================================
# ESTILO GENERAL DE LA APLICACIÓN
# ============================================================
st.markdown("""
<style>
:root{--dark:#0b5b4d;--dark2:#0f735f;--lime:#b7d51f;--bg:#f4f5f7;--border:#e0e5e5;--text:#17342f;--muted:#78827f}
html,body,[data-testid="stAppViewContainer"]{background:var(--bg)!important}
[data-testid="stHeader"]{background:#fff!important;border-bottom:1px solid var(--border)}
[data-testid="stAppViewContainer"]>.main{background:var(--bg)!important}
.block-container{padding:1.05rem 1.45rem 2rem!important;max-width:100%!important}
section[data-testid="stSidebar"]{background:#fff!important;border-right:1px solid #e1e5e8!important;min-width:235px!important;width:235px!important}
section[data-testid="stSidebar"]>div{padding:.8rem .8rem 1rem!important}
.podex-side-brand{padding:4px 7px 13px;border-bottom:1px solid #edf0f1;margin-bottom:10px}
.podex-side-title{color:var(--dark);font-size:10px;font-weight:800;text-transform:uppercase;letter-spacing:.4px;margin-top:3px}
.podex-menu-section{color:#7b8582;font-size:10px;font-weight:800;text-transform:uppercase;margin:16px 7px 6px;letter-spacing:.6px}
.st-key-podex_menu div[data-testid="stButton"]>button,.st-key-podex_menu_admin div[data-testid="stButton"]>button{justify-content:flex-start!important;height:auto!important;min-height:38px!important;padding:9px!important;margin:0!important;border:none!important;border-radius:7px!important;background:transparent!important;color:#40514d!important;font-size:12px!important;font-weight:600!important;box-shadow:none!important}
.st-key-podex_menu div[data-testid="stButton"]>button:hover,.st-key-podex_menu_admin div[data-testid="stButton"]>button:hover{background:#edf6f2!important}
.st-key-podex_menu div[data-testid="stButton"]>button[kind="primary"],.st-key-podex_menu_admin div[data-testid="stButton"]>button[kind="primary"]{color:#fff!important;background:linear-gradient(90deg,#0b5b4d,#147b66)!important;box-shadow:0 3px 10px rgba(11,91,77,.16)!important}
.st-key-podex_menu div[data-testid="stButton"]>button>div,.st-key-podex_menu_admin div[data-testid="stButton"]>button>div{justify-content:flex-start!important;width:100%!important}
.st-key-podex_menu div[data-testid="stButton"]>button p,.st-key-podex_menu_admin div[data-testid="stButton"]>button p{font-size:12px!important;font-weight:600!important;text-align:left!important}
.st-key-podex_menu,.st-key-podex_menu_admin{gap:3px!important}
.podex-topbar{background:#fff;border:1px solid #9ec91f;border-radius:8px;min-height:64px;padding:9px 16px;display:flex;align-items:center;justify-content:space-between;box-shadow:inset 0 3px 0 var(--lime);margin-bottom:12px}
.podex-top-title{color:var(--dark);font-size:18px;font-weight:800}.podex-top-subtitle{color:#7b8582;font-size:10px;margin-top:2px}.podex-user-pill{background:#f1f6f4;border:1px solid #dce9e4;color:#28564d;border-radius:20px;padding:7px 12px;font-size:10px;font-weight:700}.podex-top-actions{display:flex;align-items:center;gap:10px}.podex-logout{width:36px;height:36px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;background:linear-gradient(160deg,#C3C5C6,#403833);box-shadow:0 2px 6px rgba(64,56,51,.3);transition:transform .15s,box-shadow .15s;text-decoration:none!important}.podex-logout:hover{transform:scale(1.08);box-shadow:0 3px 10px rgba(64,56,51,.4)}
.podex-section-title{color:#16473e;font-size:15px;font-weight:800;margin:2px 0 5px}.podex-section-caption{color:#7b8582;font-size:10px;margin-bottom:8px}
div[data-testid="stVerticalBlockBorderWrapper"]{border-color:var(--border)!important;border-radius:8px!important;background:#fff!important}
div[data-testid="stFileUploader"]{background:#f7f9f8!important;border:1px dashed #b9c9c4!important;border-radius:7px!important}
div[data-testid="stTextInput"] input,div[data-testid="stTextArea"] textarea,div[data-baseweb="select"]>div{border-radius:6px!important}
button[kind="primaryFormSubmit"]{background:var(--dark)!important;border-color:var(--dark)!important;color:#fff!important}button[kind="primaryFormSubmit"]:hover{background:#08493e!important;border-color:#08493e!important}button[kind="primary"]{background:var(--dark)!important;border-color:var(--dark)!important;border-radius:6px!important;font-weight:700!important}button[kind="primary"]:hover{background:#08493e!important;border-color:#08493e!important}
[data-testid="stMetric"]{background:#fff;border:1px solid var(--border);border-radius:7px;padding:9px 11px}[data-testid="stMetricLabel"]{color:#70807a!important}[data-testid="stMetricValue"]{color:var(--dark)!important}
div[data-testid="stAlert"]{border-radius:7px!important}
span[data-baseweb="tag"],[data-testid="stMultiSelectTagsContainer"] span[data-tag]{background:var(--dark)!important}
.podex-ficha{display:grid;gap:12px 22px;background:#fff;border:1px solid var(--border);border-radius:8px;padding:14px 16px;margin:2px 0 6px;box-shadow:0 2px 7px rgba(20,45,40,.035)}
.podex-ficha-label{color:#7b8582;font-size:9px;font-weight:800;text-transform:uppercase;letter-spacing:.4px}
.podex-ficha-valor{color:var(--text);font-size:12px;margin-top:3px;line-height:1.35;word-break:break-word}
.podex-dialog-section{margin-top:14px!important}
div[role="dialog"] div[data-testid="stForm"]{border-color:var(--border)!important;border-radius:8px!important;background:#fff!important}
/* Botones circulares de acción (contenedores con key "acciones_*").
   Un color de la paleta corporativa por función. */
[class*="st-key-acciones_"] div[data-testid="stButton"] button,[class*="st-key-acciones_"] div[data-testid="stFormSubmitButton"] button{width:40px!important;height:40px!important;min-height:40px!important;padding:0!important;border-radius:50%!important;border:none!important;background:linear-gradient(160deg,#2f6db5,#00214D)!important;box-shadow:0 2px 6px rgba(20,60,90,.25)!important;transition:transform .15s,box-shadow .15s}
[class*="st-key-acciones_"] div[data-testid="stButton"] button:hover,[class*="st-key-acciones_"] div[data-testid="stFormSubmitButton"] button:hover{transform:scale(1.08);box-shadow:0 3px 10px rgba(20,60,90,.35)!important}
[class*="st-key-acciones_"] div[data-testid="stButton"] button:disabled,[class*="st-key-acciones_"] div[data-testid="stFormSubmitButton"] button:disabled{opacity:.35;transform:none;box-shadow:none!important}
[class*="st-key-acciones_"] div[data-testid="stButton"] button span,[class*="st-key-acciones_"] div[data-testid="stFormSubmitButton"] button span{color:#fff!important;font-size:20px!important;margin:0!important}
.st-key-btn_gestionar div[data-testid="stButton"] button,.st-key-btn_usr_nuevo div[data-testid="stButton"] button,.st-key-btn_cargar div[data-testid="stButton"] button,.st-key-btn_pod_nuevo div[data-testid="stButton"] button{background:linear-gradient(160deg,#CCD32A,#004236)!important}
.st-key-btn_ver_gestion div[data-testid="stButton"] button,.st-key-btn_usr_editar div[data-testid="stButton"] button,.st-key-btn_pod_editar div[data-testid="stButton"] button{background:linear-gradient(160deg,#2f6db5,#00214D)!important}
.st-key-btn_actualizar div[data-testid="stButton"] button,.st-key-btn_usr_estado div[data-testid="stButton"] button{background:linear-gradient(160deg,#F7DB17,#FF5F00)!important}
.st-key-btn_usr_clave div[data-testid="stButton"] button{background:linear-gradient(160deg,#C3C5C6,#403833)!important}
.st-key-btn_usr_eliminar div[data-testid="stButton"] button,.st-key-btn_pod_eliminar div[data-testid="stButton"] button{background:linear-gradient(160deg,#FF5F00,#8a2c00)!important}
[class*="st-key-btn_ok_"] div[data-testid="stFormSubmitButton"] button{background:linear-gradient(160deg,#CCD32A,#004236)!important}
[class*="st-key-btn_info_"] div[data-testid="stFormSubmitButton"] button{background:linear-gradient(160deg,#2f6db5,#00214D)!important}
[class*="st-key-btn_warn_"] div[data-testid="stFormSubmitButton"] button{background:linear-gradient(160deg,#F7DB17,#FF5F00)!important}
[class*="st-key-btn_neutral_"] div[data-testid="stFormSubmitButton"] button,[class*="st-key-btn_cancel_"] div[data-testid="stFormSubmitButton"] button{background:linear-gradient(160deg,#C3C5C6,#403833)!important}
[class*="st-key-btn_danger_"] div[data-testid="stFormSubmitButton"] button{background:linear-gradient(160deg,#FF5F00,#8a2c00)!important}
div[data-testid="stButton"]>button{border-radius:6px!important;min-height:27px!important;height:27px!important;padding:0 7px!important;font-size:11px!important;color:var(--dark)!important;border:1px solid #cfe0db!important;background:#f5f9f7!important}div[data-testid="stButton"]>button:hover{background:#e8f2ee!important;border-color:#9fc3b8!important}
div[data-testid="stFormSubmitButton"]>button{border-radius:6px!important;min-height:32px!important;font-weight:700!important}hr{margin:8px 0!important;border-color:#e3e8e6!important}
@media(max-width:900px){.block-container{padding:.7rem .75rem 1.5rem!important}section[data-testid="stSidebar"]{min-width:200px!important;width:200px!important}.podex-topbar{min-height:58px}}
</style>
""",unsafe_allow_html=True)

# ============================================================
# ENCABEZADO DE SESIÓN / SIDEBAR
# ============================================================
with st.sidebar:
    st.markdown('<div class="podex-side-brand">',unsafe_allow_html=True)
    st.image("Logo_PODEX.png",width=175)
    st.markdown('<div class="podex-side-title">Sistema Integrado de Gestión</div></div>',unsafe_allow_html=True)
    def mostrar_menu(clave_menu, opciones_menu):
        with st.container(key=clave_menu):
            for clave_pagina, etiqueta in opciones_menu:
                if st.button(
                    etiqueta,
                    key=f"menu_{clave_pagina}",
                    type="primary" if pagina_actual == clave_pagina else "secondary",
                    width="stretch"
                ):
                    st.session_state["pagina_actual"] = clave_pagina
                    st.rerun()

    if es_administrador:
        st.markdown('<div class="podex-menu-section">Administración</div>',unsafe_allow_html=True)
        mostrar_menu("podex_menu_admin", [("usuarios", "👥  Usuarios"), ("pods", "🧩  POD's")])

    st.markdown('<div class="podex-menu-section">Operaciones</div>',unsafe_allow_html=True)

    opciones_menu = [("solicitudes", "▣  Solicitudes")]
    if es_administrador:
        opciones_menu.append(("cargar", "📥  Cargar solicitudes"))
    mostrar_menu("podex_menu", opciones_menu)


# ============================================================
# ENCABEZADO INTERNO
# ============================================================
TITULOS_PAGINA = {
    "solicitudes": "Gestión de Solicitudes",
    "cargar": "Cargar Solicitudes",
    "usuarios": "Administración de Usuarios",
    "pods": "Administración de POD's",
}

st.markdown(f"""
<div class="podex-topbar"><div><div class="podex-top-title">{TITULOS_PAGINA.get(pagina_actual, 'Gestión de Solicitudes')}</div>
<div class="podex-top-subtitle">Sistema Integrado de Gestión de Peticiones, Incidentes y Vulnerabilidades · PODEX</div></div>
<div class="podex-top-actions"><div class="podex-user-pill">👤 {nombre_actual or usuario_actual} · Usuario: {usuario_actual} · Perfil: {perfil_actual or 'Sin perfil'}</div>
<a class="podex-logout" href="?logout=1" target="_self" title="Cerrar sesión" aria-label="Cerrar sesión"><svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="#fff" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 4h3a1 1 0 0 1 1 1v3M18 16v3a1 1 0 0 1-1 1h-3"/><path d="M5 4.5 11 3a1 1 0 0 1 1.2 1v16a1 1 0 0 1-1.2 1L5 19.5z" fill="#fff"/><path d="M14.5 12H22M19 9l3 3-3 3"/></svg></a></div></div>
""",unsafe_allow_html=True)

st.markdown('<div style="height:8px"></div>',unsafe_allow_html=True)

# ============================================================
# ADMINISTRACIÓN DE POD'S Y USUARIOS — SOLO ADMINISTRADOR
# ============================================================
if es_administrador and pagina_actual == "pods":
    mostrar_modulo_pods()
    st.stop()

if es_administrador and pagina_actual == "usuarios":
    mostrar_modulo_usuarios(usuario_actual)
    st.stop()

# ============================================================
# CARGA DE EXCEL — SOLO ADMINISTRADOR
# ============================================================
archivo_excel = None

if es_administrador and pagina_actual == "cargar":
    with st.container(border=True):
        st.markdown('<div class="podex-section-title">📥 Cargar solicitudes desde Excel</div>',unsafe_allow_html=True)
        st.markdown('<div class="podex-section-caption">Seleccione el archivo de origen para analizar y cargar las solicitudes en PODEX.</div>',unsafe_allow_html=True)
        archivo_excel=st.file_uploader(
            "Seleccione un archivo Excel",
            type=["xlsx"],
            help="Se procesarán únicamente DETALLE_GENERAL y DETALLE_FUNCIONALES.",
            key=f"archivo_excel_{st.session_state.get('uploader_version', 0)}"
        )


@st.cache_data(ttl=TTL_CACHE, show_spinner=False)
def obtener_solicitudes(usuario, administrador=False):
    """
    Consulta las solicitudes según el perfil:
      - Administrador: todas las solicitudes pendientes, sin restricción de POD.
      - Operador: únicamente solicitudes de los POD asociados al usuario.
    """
    db = Database()
    try:
        db.conectar()

        if administrador:
            sql = '''
                SELECT
                    s."ID_SOLICITUD",
                    s."TITULO",
                    s."FECHA_APERTURA",
                    s."SUBSERVICIO_AFECTADO",
                    s."PRODUCT_OWNER",
                    s."STATUS",
                    s."ASIGNADO_A",
                    s."NOMBRE_ASIGNATARIO",
                    s."CORREO_ASIGNATARIO",
                    s."FECHA_CIERRE",
                    s."CODIGO_CIERRE"
                FROM public."SOLICITUDES" s
                WHERE s."CODIGO_CIERRE" IS NULL
                  AND s."FECHA_CIERRE" IS NULL
                ORDER BY s."FECHA_APERTURA" ASC
            '''
            db.execute(sql)
        else:
            sql = '''
                SELECT
                    s."ID_SOLICITUD",
                    s."TITULO",
                    s."FECHA_APERTURA",
                    s."SUBSERVICIO_AFECTADO",
                    s."PRODUCT_OWNER",
                    s."STATUS",
                    s."ASIGNADO_A",
                    s."NOMBRE_ASIGNATARIO",
                    s."CORREO_ASIGNATARIO",
                    s."FECHA_CIERRE",
                    s."CODIGO_CIERRE"
                FROM public."SOLICITUDES" s
                WHERE s."CODIGO_CIERRE" IS NULL
                  AND s."FECHA_CIERRE" IS NULL
                  AND EXISTS (
                      SELECT 1
                      FROM public."PODS" p
                      JOIN public."USUARIOS_PODS" up ON up."ID_POD" = p."ID_POD"
                      WHERE up."USUARIO" = %s
                        AND UPPER(TRIM(p."NOMBRE")) = UPPER(TRIM(s."PRODUCT_OWNER"))
                  )
                ORDER BY s."FECHA_APERTURA" ASC
            '''
            db.execute(sql, (usuario,))

        registros = db.fetchall()
        columnas = [
            "ID_SOLICITUD","TITULO","FECHA_APERTURA","SUBSERVICIO_AFECTADO",
            "PRODUCT_OWNER","STATUS","ASIGNADO_A","NOMBRE_ASIGNATARIO",
            "CORREO_ASIGNATARIO","FECHA_CIERRE","CODIGO_CIERRE"
        ]
        return pd.DataFrame(registros, columns=columnas)
    finally:
        db.cerrar()

@st.cache_data(ttl=TTL_CACHE, show_spinner=False)
def obtener_gestiones(id_solicitud):
    db = Database()
    try:
        db.conectar()
        db.execute('''
            SELECT "FECHA_GESTION","OBSERVACION","USUARIO_REGISTRO","FECHA_REGISTRO"
            FROM public."GESTIONES"
            WHERE "ID_SOLICITUD" = %s
            ORDER BY "FECHA_GESTION" DESC
        ''', (id_solicitud,))
        return pd.DataFrame(
            db.fetchall(),
            columns=["FECHA_GESTION","OBSERVACION","USUARIO_REGISTRO","FECHA_REGISTRO"]
        )
    finally:
        db.cerrar()


def guardar_auditoria(
    db,
    nombre_archivo,
    registros_generales,
    registros_funcionales,
    estado,
    observaciones,
    usuario_carga
):
    """Guarda la auditoría de la carga en public."AUDITORIA"."""
    fecha_actual = pd.Timestamp.now().to_pydatetime()

    db.execute("""
        INSERT INTO public."AUDITORIA"
        (
            "NOMBRE_ARCHIVO",
            "FECHA_CARGUE",
            "REGISTROS_GENERALES",
            "REGISTROS_FUNCIONALES",
            "ESTADO",
            "OBSERVACIONES",
            "USUARIO_CARGA",
            "FECHA_REGISTRO"
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        nombre_archivo,
        fecha_actual,
        int(registros_generales or 0),
        int(registros_funcionales or 0),
        estado,
        observaciones,
        usuario_carga,
        fecha_actual
    ))

@st.cache_data(show_spinner=False, max_entries=2)
def leer_hojas_cacheadas(contenido, product_owners):
    """Lee el Excel una sola vez por archivo: la vista previa y la carga
    reutilizan el resultado en lugar de volver a procesarlo en cada clic."""
    return leer_hojas(io.BytesIO(contenido), product_owners)


def resumen_carga(archivo, hojas):
    """Datos del correo de backlog: (Product Owner, TIPO, RANGTIEMPO) de las
    solicitudes cargadas, separados por hoja."""
    registros = {}
    for hoja, df in hojas:
        columnas = [c for c in ("PRODUCT_OWNER", "TIPO", "RANGTIEMPO") if c in df.columns]
        datos = df[columnas].copy()
        for c in ("TIPO", "RANGTIEMPO"):
            datos[c] = (datos[c].fillna("Sin dato").astype(str).str.strip()
                        if c in datos.columns else "Sin dato")
        datos["TIPO"] = datos["TIPO"].str.upper()
        registros[hoja] = list(datos[["PRODUCT_OWNER", "TIPO", "RANGTIEMPO"]].itertuples(index=False, name=None))

    return {
        "archivo": archivo.name,
        "usuario_carga": nombre_actual or usuario_actual,
        "general": registros.get("DETALLE_GENERAL", []),
        "funcional": registros.get("DETALLE_FUNCIONALES", []),
    }


def notificar_carga(resumen, archivo_bytes):
    """Envía un solo correo de backlog (con el Excel adjunto) a los usuarios
    activos de perfil Operador. Devuelve (tipo, mensaje)."""
    try:
        usuarios = obtener_usuarios()
        correos = usuarios.loc[
            (usuarios["ACTIVO"] == True)  # noqa: E712
            & usuarios["CORREO"].notna()
            & (usuarios["PERFIL"].astype(str).str.strip().str.upper() == "OPERADOR"),
            "CORREO"
        ].tolist()
        if not correos:
            return "warning", "⚠️ No hay usuarios Operador activos con correo para notificar la carga."

        # El adjunto lleva aplicado el filtro de PRODUCT_OWNER con los PODS
        # registrados y la hoja JDU con las tablas del correo; si no se puede
        # preparar, se envía el archivo original.
        aviso_adjunto = ""
        try:
            with st.spinner("Preparando el adjunto (filtro de PODS y hoja JDU)..."):
                adjunto = filtrar_adjunto(
                    archivo_bytes,
                    obtener_pods()["NOMBRE"].dropna().tolist(),
                    tablas_jdu=(resumen["general"], resumen["funcional"]),
                )
        except Exception as e:
            adjunto = archivo_bytes
            aviso_adjunto = f" No fue posible preparar el adjunto con el filtro de PODS y la hoja JDU ({e}); se envió el archivo original."

        with st.spinner("Enviando el resumen de la carga por correo..."):
            enviados = enviar_correo_backlog(correos, resumen, adjunto)
    except Exception as e:
        return "warning", f"⚠️ La carga se guardó, pero no fue posible enviar el resumen por correo: {e}"

    if aviso_adjunto:
        return "warning", (f"⚠️ Correo de backlog ({nombre_backlog(resumen['archivo'])}) enviado a "
                           f"{enviados} usuario(s) Operador activo(s).{aviso_adjunto}")
    return "info", f"📧 Correo de backlog ({nombre_backlog(resumen['archivo'])}) enviado a {enviados} usuario(s) Operador activo(s)."


def ejecutar_carga(archivo, hojas, notificar=False):
    """Carga las solicitudes del archivo y registra la auditoría."""
    db = Database()

    try:
        db.conectar()

        with st.spinner("Cargando solicitudes en Supabase..."):
            # Cargar las solicitudes
            # Los TITULO se guardan en MAYÚSCULAS desde cargar_excel().
            resultado = cargar_excel(hojas, db)

            generales = int(resultado.get("generales", 0) or 0)
            funcionales = int(resultado.get("funcionales", 0) or 0)
            duplicados = int(resultado.get("duplicados", 0) or 0)
            errores = int(resultado.get("errores", 0) or 0)

            # Estado de la auditoría
            estado_auditoria = "EXITOSO" if errores == 0 else "CON ERRORES"

            observaciones = (
                f"Archivo procesado. "
                f"Duplicados: {duplicados}. "
                f"Errores: {errores}."
            )

            # Guardar auditoría usando la misma conexión
            guardar_auditoria(
                db=db,
                nombre_archivo=archivo.name,
                registros_generales=generales,
                registros_funcionales=funcionales,
                estado=estado_auditoria,
                observaciones=observaciones,
                usuario_carga=nombre_actual or usuario_actual
            )

            # Confirmar solicitudes + auditoría
            db.commit()

        st.cache_data.clear()

        # El resultado se muestra después del st.rerun().
        st.session_state["resultado_carga"] = {
            "archivo": archivo.name,
            "generales": generales,
            "funcionales": funcionales,
            "duplicados": duplicados,
            "errores": errores,
        }

        # El correo es informativo: si falla, la carga ya quedó guardada.
        if notificar:
            st.session_state["resultado_carga"]["correo"] = notificar_carga(
                resumen_carga(archivo, hojas), archivo.getvalue()
            )

        # Limpia el archivo seleccionado para evitar cargarlo dos veces.
        st.session_state["uploader_version"] = st.session_state.get("uploader_version", 0) + 1
        return True

    except Exception as e:
        db.rollback()
        st.error(
            "❌ No fue posible cargar el archivo ni registrar la auditoría."
        )
        st.error(f"Detalle del error: {e}")
        st.exception(e)
        return False

    finally:
        db.cerrar()


# ============================================================
# VENTANA TIPO OVERLAY PARA CONFIRMAR LA CARGA
# ============================================================
@st.dialog(" ", width="large")
def ventana_confirmar_carga(archivo, preview, hojas):

    encabezado_ventana("Confirmar Carga de Solicitudes")

    ficha([
        ("Archivo", archivo.name),
        ("Solicitudes", len(preview)),
        ("DETALLE_GENERAL", int((preview["HOJA"] == "DETALLE_GENERAL").sum())),
        ("DETALLE_FUNCIONALES", int((preview["HOJA"] == "DETALLE_FUNCIONALES").sum())),
    ], columnas=4)

    seccion("¿Está seguro que desea cargar estas solicitudes?")

    with st.form("form_confirmar_carga"):
        puede_notificar = configuracion_correo() is not None and obtener_cliente_admin() is not None
        notificar = st.checkbox(
            "Enviar correo de backlog a los usuarios Operador activos",
            value=puede_notificar,
            disabled=not puede_notificar,
            help=(
                "Se envía un solo correo con las tablas del backlog y el Excel adjunto a los usuarios Operador activos."
                if puede_notificar else
                "Requiere la sección [email] y supabase.service_role_key en los secretos."
            )
        )
        with st.container(key="acciones_dlg_carga", horizontal=True,
                          horizontal_alignment="right", gap="small"):
            cancelar = st.form_submit_button("", icon=":material/close:", key="btn_cancel_carga", help="Cancelar")
            confirmar = st.form_submit_button("", icon=":material/upload:", key="btn_ok_carga", help="Sí, cargar solicitudes")

    if cancelar:
        st.rerun()

    if confirmar and ejecutar_carga(archivo, hojas, notificar):
        st.rerun()


if es_administrador and pagina_actual == "cargar":

    resultado_carga = st.session_state.pop("resultado_carga", None)
    if resultado_carga:
        st.success(
            f"✅ Archivo {resultado_carga['archivo']} cargado y "
            "auditoría registrada correctamente."
        )
        a, b, c, d = st.columns(4)
        a.metric("Generales", resultado_carga["generales"])
        b.metric("Funcionales", resultado_carga["funcionales"])
        c.metric("Duplicados", resultado_carga["duplicados"])
        d.metric("Errores", resultado_carga["errores"])

        if resultado_carga.get("correo"):
            tipo, mensaje = resultado_carga["correo"]
            (st.warning if tipo == "warning" else st.info)(mensaje)

if es_administrador and archivo_excel is not None:
    try:
        pods = obtener_pods()
    except Exception as e:
        st.error("❌ No fue posible consultar la tabla PODS.")
        st.exception(e)
        st.stop()

    product_owners = pods["NOMBRE"].dropna().tolist()

    if not product_owners:
        st.warning("⚠️ La tabla PODS no tiene registros; no hay solicitudes para cargar.")
        st.stop()

    try:
        with st.spinner("Analizando archivo Excel..."):
            hojas = leer_hojas_cacheadas(archivo_excel.getvalue(), tuple(product_owners))
            preview = analizar_excel(hojas)
    except Exception as e:
        st.error("❌ Error analizando el archivo.")
        st.exception(e)
        st.stop()

    with st.container(border=True):
        c_titulo, c_acciones_carga = st.columns([4, 1], vertical_alignment="center")
        with c_titulo:
            st.markdown('<div class="podex-section-title">👁️ Vista previa de la información a cargar</div>',unsafe_allow_html=True)
            st.markdown(f'<div class="podex-section-caption">Archivo: {archivo_excel.name} · Solo se incluyen solicitudes de los POD registrados en la tabla PODS.</div>',unsafe_allow_html=True)
        with c_acciones_carga:
            with st.container(key="acciones_carga", horizontal=True,
                              horizontal_alignment="right"):
                if st.button("", icon=":material/upload:", key="btn_cargar",
                             disabled=preview.empty, help="Cargar solicitudes"):
                    ventana_confirmar_carga(archivo_excel, preview, hojas)

        if preview.empty:
            st.warning("⚠️ El archivo no contiene solicitudes de los POD registrados en la tabla PODS.")
            st.stop()

        # Asociar cada solicitud con el ID_POD de su Product Owner.
        id_pod_por_nombre = {
            normalizar_product_owner(n): i
            for i, n in zip(pods["ID_POD"], pods["NOMBRE"])
        }
        preview.insert(1, "ID_POD", preview["PRODUCT_OWNER"].map(id_pod_por_nombre))

        a, b, c = st.columns(3)
        a.metric("Solicitudes a cargar", len(preview))
        b.metric("DETALLE_GENERAL", int((preview["HOJA"] == "DETALLE_GENERAL").sum()))
        c.metric("DETALLE_FUNCIONALES", int((preview["HOJA"] == "DETALLE_FUNCIONALES").sum()))

        st.markdown("**👥 Solicitudes por POD**")
        resumen = (
            preview.groupby(["ID_POD", "PRODUCT_OWNER"])
            .size()
            .reset_index(name="CANTIDAD")
            .sort_values("ID_POD")
        )
        st.dataframe(resumen, width="stretch", hide_index=True)

        st.markdown("**📋 Solicitudes**")
        st.dataframe(
            preview[[
                "ID_SOLICITUD", "ID_POD", "PRODUCT_OWNER", "HOJA", "STATUS",
                "FECHA_APERTURA", "TITULO", "SUBSERVICIO_AFECTADO"
            ]],
            width="stretch",
            hide_index=True
        )

# La página de carga termina aquí; el resto corresponde a la página de solicitudes.
if pagina_actual == "cargar":
    st.stop()

try:
    df = obtener_solicitudes(usuario_actual, es_administrador)
except Exception as e:
    st.error("❌ No fue posible consultar las solicitudes.")
    st.exception(e)
    st.stop()

texto = st.text_input(
    "🔎 Buscar solicitud",
    placeholder="Digite ID, título, estado, asignado, Product Owner..."
)

if texto:
    mascara = df.astype(str).apply(
        lambda col: col.str.lower().str.contains(texto.lower(), na=False)
    )
    df_filtrado = df[mascara.any(axis=1)]
else:
    df_filtrado = df


def ficha_solicitud(solicitud):
    """Datos principales de la solicitud en la tarjeta estilo PODEX."""
    fecha_apertura = solicitud["FECHA_APERTURA"]
    if pd.notna(fecha_apertura):
        fecha_apertura = pd.to_datetime(fecha_apertura).strftime("%Y-%m-%d %H:%M:%S")
    ficha([
        ("ID solicitud", solicitud["ID_SOLICITUD"]),
        ("Product Owner", solicitud["PRODUCT_OWNER"]),
        ("Estado", solicitud["STATUS"]),
        ("Título", solicitud["TITULO"]),
        ("Asignado a", solicitud["ASIGNADO_A"]),
        ("Fecha apertura", fecha_apertura),
        ("Subservicio afectado", solicitud["SUBSERVICIO_AFECTADO"]),
        ("Nombre asignatario", solicitud["NOMBRE_ASIGNATARIO"]),
        ("Correo asignatario", solicitud["CORREO_ASIGNATARIO"]),
    ])


# ============================================================
# VENTANA TIPO OVERLAY PARA INFORMACIÓN + NUEVA GESTIÓN
# ============================================================
@st.dialog(" ", width="large")
def ventana_gestion(id_solicitud):

    encabezado_ventana("Gestionar Solicitud")

    solicitud = df_filtrado[
        df_filtrado["ID_SOLICITUD"] == id_solicitud
    ].iloc[0]

    ficha_solicitud(solicitud)

    seccion("Nueva gestión", "Registre la fecha, la hora y la observación de la gestión realizada.")

    with st.form(f"form_gestion_popup_{id_solicitud}"):

        ahora = datetime.now(ZoneInfo('America/Bogota'))
        c_fecha, c_hora = st.columns(2)

        with c_fecha:
            fecha_seleccionada = st.date_input(
                "Fecha de gestión",
                value=ahora.date(),
                format="DD/MM/YYYY"
            )

        with c_hora:
            # step=1 muestra horas, minutos y segundos (HH:MM:SS).
            hora_gestion_valor = st.time_input(
                "Hora de gestión",
                value=None,
                step=1,
                key=f"hora_gestion_{id_solicitud}",
                help="Seleccione o digite la hora de la gestión (HH:MM:SS)."
            )

        observacion = st.text_area(
            "Observación",
            placeholder="Digite la observación de la gestión...",
            height=130
        )

        with st.container(key="acciones_dlg_gestion", horizontal=True,
                          horizontal_alignment="right", gap="small"):
            guardar = st.form_submit_button("", icon=":material/save:", key="btn_ok_gestion", help="Guardar gestión")

    if guardar:

        observacion = observacion.strip()

        if not observacion:
            st.warning("⚠️ Debe ingresar una observación.")
            return

        # Guardar EXACTAMENTE la fecha y hora seleccionadas por el usuario.
        if hora_gestion_valor is None:
            st.error("❌ Debe seleccionar la hora de gestión.")
            return

        hora_gestion = hora_gestion_valor.strftime("%H:%M:%S")

        fecha_db = f"{fecha_seleccionada:%Y-%m-%d} {hora_gestion}"

        db = Database()

        try:
            db.conectar()

            db.execute(
                """
                SELECT 1
                FROM public."GESTIONES"
                WHERE "ID_SOLICITUD" = %s
                  AND "OBSERVACION" = %s
                LIMIT 1
                """,
                (id_solicitud, observacion)
            )

            if db.fetchone():
                st.warning(
                    "⚠️ Esta observación ya existe para esta solicitud."
                )
                return

            db.execute(
                """
                INSERT INTO public."GESTIONES"
                ("FECHA_GESTION","ID_SOLICITUD","OBSERVACION","USUARIO_REGISTRO")
                VALUES (CAST(%s AS timestamp without time zone), %s, %s, %s)
                RETURNING "FECHA_GESTION"
                """,
                # FECHA_REGISTRO la asigna la base de datos (hora de Bogotá).
                (fecha_db, id_solicitud, observacion, usuario_actual)
            )

            fecha_guardada = db.fetchone()[0]

            db.commit()
            st.cache_data.clear()

            st.toast(f"✅ Gestión guardada: {fecha_guardada:%Y-%m-%d %H:%M:%S}")
            st.rerun()

        except Exception as e:
            db.rollback()
            st.error("❌ No fue posible guardar la gestión.")
            st.exception(e)

        finally:
            db.cerrar()


# ============================================================
# VENTANA TIPO OVERLAY PARA VER GESTIONES
# ============================================================
@st.dialog(" ", width="large")
def ventana_ver_gestion(id_solicitud):

    encabezado_ventana("Ver Gestión")

    solicitud = df_filtrado[
        df_filtrado["ID_SOLICITUD"] == id_solicitud
    ].iloc[0]

    ficha_solicitud(solicitud)

    seccion("Gestiones registradas")

    try:
        gestiones = obtener_gestiones(id_solicitud)
    except Exception as e:
        st.error("❌ No fue posible consultar las gestiones de la solicitud.")
        st.exception(e)
        return

    if gestiones.empty:
        st.info("ℹ️ Esta solicitud no tiene gestiones registradas.")
        return

    gestiones_mostrar = gestiones.copy()

    for columna in ("FECHA_GESTION", "FECHA_REGISTRO"):
        gestiones_mostrar[columna] = pd.to_datetime(
            gestiones_mostrar[columna],
            errors="coerce"
        ).dt.strftime("%Y-%m-%d %H:%M:%S")

    # Las gestiones anteriores a este registro no tienen usuario ni fecha.
    gestiones_mostrar = gestiones_mostrar.fillna("—")

    # ID_GESTION NO se consulta ni se muestra.
    st.dataframe(
        gestiones_mostrar,
        width="stretch",
        hide_index=True,
        column_config={
            "FECHA_GESTION": st.column_config.TextColumn(
                "Fecha gestión",
                width="medium"
            ),
            "OBSERVACION": st.column_config.TextColumn(
                "Observación",
                width="large"
            ),
            "USUARIO_REGISTRO": st.column_config.TextColumn(
                "Registrado por",
                width="small"
            ),
            "FECHA_REGISTRO": st.column_config.TextColumn(
                "Fecha registro",
                width="medium"
            )
        }
    )


# ============================================================
# VENTANA TIPO OVERLAY PARA ACTUALIZAR SOLICITUD
# ============================================================
@st.dialog(" ", width="large")
def ventana_actualizar(id_solicitud):

    encabezado_ventana("Actualizar Solicitud")

    solicitud = df_filtrado[
        df_filtrado["ID_SOLICITUD"] == id_solicitud
    ].iloc[0]


    ficha_solicitud(solicitud)

    seccion("Actualizar solicitud", "Cambie el estado o registre el código, la fecha y la hora de cierre.")

    estados = [
        "Cancelled",
        "Categorize",
        "Fulfilled",
        "In Progress",
        "Open",
        "Pending",
        "Pending Customer",
        "Pending Force",
        "Pending Parent Incident",
        "Pending Vendor",
        "Planned",
        "Ready",
        "Resolved",
        "Suspended",
        "Work In Progress"
    ]

    codigos = [
        "Cancelado por incumplimiento de politicas",
        "Cancelado por duplicidad",
        "Cancelado por el usuario",
        "Cerrado por automatización",
        "Resuelto por soporte funcional",
        "Resuelto por soporte técnico"
    ]

    status_opciones = [""] + estados
    codigo_opciones = [""] + codigos

    status_actual = solicitud["STATUS"]
    codigo_actual = solicitud.get("CODIGO_CIERRE", None)
    fecha_actual = solicitud.get("FECHA_CIERRE", None)

    i_status = (
        status_opciones.index(status_actual)
        if status_actual in status_opciones
        else 0
    )

    i_codigo = (
        codigo_opciones.index(codigo_actual)
        if codigo_actual in codigo_opciones
        else 0
    )

    fecha_inicial = (
        pd.to_datetime(fecha_actual)
        if pd.notna(fecha_actual)
        else pd.Timestamp.now()
    )

    # ========================================================
    # BLOQUE DE ACTUALIZACIÓN
    # Todos los campos quedan dentro del mismo contenedor visual.
    # Código de cierre queda fuera del st.form para que su cambio
    # habilite/deshabilite dinámicamente fecha y hora.
    # El botón permanece dentro del st.form.
    # ========================================================
    with st.container(border=True):

        a, b = st.columns(2)

        with a:
            nuevo_status = st.selectbox(
                "Estado",
                status_opciones,
                index=i_status,
                key=f"status_actualizar_{id_solicitud}"
            )

        with b:
            nuevo_codigo = st.selectbox(
                "Código de cierre",
                codigo_opciones,
                index=i_codigo,
                key=f"codigo_cierre_{id_solicitud}"
            )

        codigo_seleccionado = bool(nuevo_codigo)

        if not codigo_seleccionado:
            fecha_default = None
            hora_default = None
        else:
            fecha_default = (
                fecha_inicial.date()
                if pd.notna(fecha_actual)
                else pd.Timestamp.now().date()
            )
            hora_default = (
                fecha_inicial.time()
                if pd.notna(fecha_actual)
                else None
            )

        with st.form(f"form_actualizar_popup_{id_solicitud}"):

            c_fecha, c_hora = st.columns(2)

            with c_fecha:
                fecha_cierre_fecha = st.date_input(
                    "Fecha de cierre",
                    value=fecha_default,
                    format="DD/MM/YYYY",
                    disabled=not codigo_seleccionado,
                    key=f"fecha_cierre_{id_solicitud}"
                )

            with c_hora:
                # step=1 muestra horas, minutos y segundos (HH:MM:SS).
                hora_cierre_valor = st.time_input(
                    "Hora de cierre",
                    value=hora_default,
                    step=1,
                    help="Seleccione o digite la hora de cierre (HH:MM:SS).",
                    disabled=not codigo_seleccionado,
                    key=f"hora_cierre_{id_solicitud}"
                )

            with st.container(key="acciones_dlg_actualizar", horizontal=True,
                              horizontal_alignment="right", gap="small"):
                actualizar = st.form_submit_button("", icon=":material/edit_document:", key="btn_warn_actualizar", help="Actualizar solicitud")

    if actualizar:

        # Si no hay código de cierre, se limpia fecha y hora.
        if not nuevo_codigo:
            fecha_cierre_db = None
        else:
            # Si hay código de cierre, fecha y hora son obligatorias.
            if fecha_cierre_fecha is None:
                st.error("❌ Debe seleccionar la fecha de cierre.")
                return

            if hora_cierre_valor is None:
                st.error("❌ Debe seleccionar la hora de cierre.")
                return

            hora_cierre = hora_cierre_valor.strftime("%H:%M:%S")

            fecha_cierre_db = (
                f"{fecha_cierre_fecha:%Y-%m-%d} {hora_cierre}"
            )

        db = Database()

        try:
            db.conectar()

            db.execute(
                """
                UPDATE public."SOLICITUDES"
                SET "FECHA_CIERRE" = CAST(%(fecha_cierre)s AS timestamp without time zone),
                    "STATUS" = %(status)s,
                    "CODIGO_CIERRE" = %(codigo)s,
                    -- Al cerrar se registra quién y cuándo (hora de Bogotá)
                    -- lo hizo en PODEX; si se quita el cierre, se limpian.
                    "USUARIO_CIERRE" = CASE
                        WHEN %(codigo)s::varchar IS NULL THEN NULL
                        ELSE %(usuario)s::varchar
                    END,
                    "FECHA_REGISTRO_CIERRE" = CASE
                        WHEN %(codigo)s::varchar IS NULL THEN NULL
                        ELSE now() AT TIME ZONE 'America/Bogota'
                    END
                WHERE "ID_SOLICITUD" = %(id_solicitud)s
                RETURNING "FECHA_CIERRE"
                """,
                {
                    "fecha_cierre": fecha_cierre_db,
                    "status": nuevo_status or None,
                    "codigo": nuevo_codigo or None,
                    "usuario": usuario_actual,
                    "id_solicitud": id_solicitud,
                }
            )

            fecha_cierre_guardada = db.fetchone()[0]

            db.commit()

            st.cache_data.clear()

            if fecha_cierre_guardada is not None:
                fecha_hora_mensaje = fecha_cierre_guardada.strftime("%Y-%m-%d %H:%M:%S")
            else:
                fecha_hora_mensaje = "sin fecha/hora de cierre"

            st.toast(f"✅ Solicitud {id_solicitud} actualizada ({fecha_hora_mensaje}).")
            st.rerun()

        except Exception as e:
            db.rollback()
            st.error(
                "❌ No fue posible actualizar la solicitud."
            )
            st.exception(e)

        finally:
            db.cerrar()


# ============================================================
# TABLA PRINCIPAL
# Misma cuadrícula que la vista previa de "Cargar solicitudes":
# se selecciona una fila y se gestiona con los botones superiores.
# ============================================================
if df_filtrado.empty:
    st.info(
        "ℹ️ No existen solicitudes que coincidan con el criterio de búsqueda."
    )
    st.stop()

tabla_solicitudes = df_filtrado[[
    "ID_SOLICITUD", "TITULO", "SUBSERVICIO_AFECTADO", "PRODUCT_OWNER", "STATUS"
]].reset_index(drop=True)

c_sel, c_acciones = st.columns([3, 1], vertical_alignment="center")

seleccion = st.session_state.get("tabla_solicitudes")
filas = seleccion.selection.rows if seleccion else []
sid = (
    tabla_solicitudes.iloc[filas[0]]["ID_SOLICITUD"]
    if filas and filas[0] < len(tabla_solicitudes)
    else None
)

with c_sel:
    if sid:
        st.markdown(f"**Solicitud seleccionada:** {sid}")
    else:
        st.caption("☝️ Seleccione una solicitud en la tabla para gestionarla.")


with c_acciones:
    with st.container(key="acciones_solicitud", horizontal=True,
                      horizontal_alignment="right", gap="small"):
        if st.button("", icon=":material/edit:", key="btn_gestionar",
                     disabled=not sid, help="Gestionar"):
            ventana_gestion(sid)
        if st.button("", icon=":material/search:", key="btn_ver_gestion",
                     disabled=not sid, help="Ver gestión"):
            ventana_ver_gestion(sid)
        if st.button("", icon=":material/edit_document:", key="btn_actualizar",
                     disabled=not sid, help="Actualizar"):
            ventana_actualizar(sid)

st.markdown('<div style="height:14px"></div>', unsafe_allow_html=True)

st.dataframe(
    tabla_solicitudes,
    key="tabla_solicitudes",
    on_select="rerun",
    selection_mode="single-row",
    hide_index=True,
    width="stretch",
    height=min(38 + 35 * len(tabla_solicitudes), 640),
    column_config={
        "ID_SOLICITUD": st.column_config.TextColumn("ID_SOLICITUD", width="small"),
        "TITULO": st.column_config.TextColumn("TITULO", width="large"),
        "SUBSERVICIO_AFECTADO": st.column_config.TextColumn("SUBSERVICIO_AFECTADO", width="medium"),
        "PRODUCT_OWNER": st.column_config.TextColumn("PRODUCT_OWNER", width="medium"),
        "STATUS": st.column_config.TextColumn("STATUS", width="small"),
    },
)
