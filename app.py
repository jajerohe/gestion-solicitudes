import streamlit as st
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo

from database import Database
from excel_web import analizar_excel, cargar_excel
from auth import iniciar_sesion, cerrar_sesion

st.set_page_config(
    page_title="SIGPI",
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
    """Obtiene el usuario de SIGPI asociado al usuario autenticado en Supabase."""
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
    """Muestra el inicio de sesión con un diseño de dos paneles."""

    st.markdown(
        """
        <style>
        /* ======================================================
           PANTALLA DE LOGIN
           ====================================================== */
        [data-testid="stSidebar"] { display: none !important; }
        header[data-testid="stHeader"] { display: none !important; }
        .block-container {
            padding: 0 !important;
            max-width: 100% !important;
        }

        /* Primer panel: identidad SIGPI */
        div[data-testid="stHorizontalBlock"] > div:first-child {
            background:
                radial-gradient(circle at 20% 18%, rgba(196,229,47,.16), transparent 28%),
                linear-gradient(145deg, #0b2824 0%, #153e34 52%, #0d2b27 100%);
            min-height: 100vh;
            padding: 72px 7% !important;
            position: relative;
            overflow: hidden;
            box-sizing: border-box;
        }

        div[data-testid="stHorizontalBlock"] > div:first-child:after {
            content: "";
            position: absolute;
            width: 560px;
            height: 560px;
            right: -290px;
            bottom: -280px;
            border-radius: 50%;
            border: 1px solid rgba(201,229,46,.20);
            box-shadow:
                0 0 0 45px rgba(201,229,46,.035),
                0 0 0 95px rgba(201,229,46,.025);
            pointer-events: none;
        }

        /* Segundo panel: formulario */
        div[data-testid="stHorizontalBlock"] > div:nth-child(2) {
            background: #f7f8fa;
            min-height: 100vh;
            padding: 35px 6% !important;
            display: flex;
            align-items: center;
            justify-content: center;
            box-sizing: border-box;
        }

        .sigpi-login-brand {
            max-width: 620px;
            margin: 55px auto 0 auto;
            position: relative;
            z-index: 2;
        }
        .sigpi-login-brand h1 {
            font-size: 34px;
            line-height: 1.12;
            margin: 24px 0 12px 0;
            color: #ffffff;
            font-weight: 800;
        }
        .sigpi-login-brand h1 span { color: #c9e52e; }
        .sigpi-login-brand p {
            font-size: 16px;
            line-height: 1.55;
            color: rgba(255,255,255,.82);
            max-width: 560px;
            margin-bottom: 28px;
        }
        .sigpi-feature {
            display: flex;
            align-items: center;
            gap: 12px;
            margin: 15px 0;
            color: #f4f7f4;
            font-size: 14px;
        }
        .sigpi-dot {
            width: 9px;
            height: 9px;
            min-width: 9px;
            border-radius: 50%;
            background: #c9e52e;
            box-shadow: 0 0 10px rgba(201,229,46,.45);
        }

        .sigpi-login-title {
            text-align: center;
            color: #24344d;
            font-size: 30px;
            font-weight: 800;
            margin: 0 0 7px 0;
        }
        .sigpi-login-subtitle {
            text-align: center;
            color: #7b8490;
            font-size: 14px;
            margin: 0 0 24px 0;
        }
        .sigpi-login-footer {
            text-align: center;
            color: #9aa1aa;
            font-size: 11px;
            line-height: 1.5;
            margin-top: 18px;
        }

        /* Tarjeta del formulario */
        div[data-testid="stForm"] {
            background: #ffffff;
            border: 1px solid #e5e9ee;
            border-radius: 14px;
            padding: 32px 34px 26px 34px;
            box-shadow: 0 16px 42px rgba(28,42,58,.11);
            max-width: 430px;
            margin-left: auto;
            margin-right: auto;
        }
        div[data-testid="stForm"] label {
            color: #4c5663 !important;
            font-weight: 600 !important;
        }
        div[data-testid="stForm"] input {
            border-radius: 8px !important;
            border: 1px solid #d9dee5 !important;
        }
        div[data-testid="stForm"] input:focus {
            border-color: #789c38 !important;
            box-shadow: 0 0 0 1px #789c38 !important;
        }
        div[data-testid="stFormSubmitButton"] button {
            background: #789c38 !important;
            border: none !important;
            color: white !important;
            border-radius: 7px !important;
            min-height: 44px !important;
            font-weight: 700 !important;
            font-size: 15px !important;
        }
        div[data-testid="stFormSubmitButton"] button:hover {
            background: #66872f !important;
        }

        @media (max-width: 900px) {
            div[data-testid="stHorizontalBlock"] > div:first-child,
            div[data-testid="stHorizontalBlock"] > div:nth-child(2) {
                min-height: auto;
            }
            div[data-testid="stHorizontalBlock"] > div:first-child {
                padding: 40px 8% !important;
            }
            div[data-testid="stHorizontalBlock"] > div:nth-child(2) {
                padding: 35px 8% 55px 8% !important;
            }
            .sigpi-login-brand {
                margin-top: 20px;
            }
            .sigpi-login-brand h1 {
                font-size: 28px;
            }
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    left, right = st.columns([1.15, 0.85], gap="small")

    with left:
        st.image("Logo_SIGPI.png", width=430)
        st.markdown(
            """
            <div class="sigpi-login-brand">
                <h1>Gestión inteligente de <span>peticiones e incidentes</span></h1>
                <p>
                    Seguimiento centralizado de solicitudes y gestiones,
                    con información trazable y segura.
                </p>
                <div class="sigpi-feature"><span class="sigpi-dot"></span>Seguimiento centralizado de solicitudes</div>
                <div class="sigpi-feature"><span class="sigpi-dot"></span>Control y trazabilidad de la información</div>
                <div class="sigpi-feature"><span class="sigpi-dot"></span>Acceso seguro según usuario y POD asignado</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with right:
        st.markdown(
            """
            <div style="max-width:430px;width:100%;margin:0 auto;">
                <div class="sigpi-login-title">Bienvenido de nuevo</div>
                <div class="sigpi-login-subtitle">Ingresa con tus credenciales para continuar</div>
            </div>
            """,
            unsafe_allow_html=True
        )

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
                use_container_width=True
            )

        st.markdown(
            """
            <div class="sigpi-login-footer">
                SIGPI · Sistema Integrado de Gestión de Peticiones e Incidentes<br>
                Acceso protegido mediante autenticación segura.
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
                        "pero no está registrado en SIGPI."
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

if "usuario_actual" not in st.session_state:
    mostrar_login()
    st.stop()

usuario_actual = st.session_state["usuario_actual"]
perfil_actual = st.session_state.get("perfil_actual", "")
nombre_actual = st.session_state.get("nombre_actual", "")

# Perfil Administrador: acceso completo a carga y solicitudes.
# Perfil Operador: acceso restringido a las solicitudes de sus POD asignados.
es_administrador = str(perfil_actual or "").strip().lower() == "administrador"

# ============================================================
# ESTILO GENERAL DE LA APLICACIÓN
# Diseño interno inspirado en Supervisor Operativo:
# sidebar claro, verde institucional, tarjetas y flujo por pasos.
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
.sigpi-side-brand{padding:4px 7px 13px;border-bottom:1px solid #edf0f1;margin-bottom:10px}
.sigpi-side-title{color:var(--dark);font-size:10px;font-weight:800;text-transform:uppercase;letter-spacing:.4px;margin-top:3px}
.sigpi-menu-section{color:#7b8582;font-size:10px;font-weight:800;text-transform:uppercase;margin:16px 7px 6px;letter-spacing:.6px}
.sigpi-menu-item{display:flex;align-items:center;gap:9px;padding:9px;margin:3px 0;border-radius:7px;color:#40514d;font-size:12px;font-weight:600}
.sigpi-menu-item.active{color:#fff;background:linear-gradient(90deg,#0b5b4d,#147b66);box-shadow:0 3px 10px rgba(11,91,77,.16)}
.sigpi-menu-icon{width:21px;height:21px;display:inline-flex;align-items:center;justify-content:center;border-radius:5px;background:#edf6f2;font-size:12px}
.sigpi-menu-item.active .sigpi-menu-icon{background:rgba(255,255,255,.18)}
.sigpi-session-card{margin-top:14px;padding:10px;border:1px solid #e3e8e6;border-radius:9px;background:#f8faf9;font-size:10px;color:#5f6d69;line-height:1.65}
.sigpi-session-card strong{color:var(--dark)}
.sigpi-topbar{background:#fff;border:1px solid var(--border);border-radius:8px;min-height:64px;padding:9px 16px;display:flex;align-items:center;justify-content:space-between;box-shadow:0 2px 7px rgba(20,45,40,.04);margin-bottom:12px}
.sigpi-top-title{color:var(--dark);font-size:18px;font-weight:800}.sigpi-top-subtitle{color:#7b8582;font-size:10px;margin-top:2px}.sigpi-user-pill{background:#f1f6f4;border:1px solid #dce9e4;color:#28564d;border-radius:20px;padding:7px 12px;font-size:10px;font-weight:700}
.sigpi-step-card{background:#fff;border:1px solid var(--border);border-radius:8px;min-height:66px;padding:10px 13px;box-shadow:0 2px 7px rgba(20,45,40,.035)}
.sigpi-step-card.active{border-color:#9ec91f;box-shadow:inset 0 3px 0 var(--lime)}
.sigpi-step-number{color:#7b8582;font-size:9px;font-weight:800;text-transform:uppercase}.sigpi-step-name{color:#1b4038;font-size:12px;font-weight:800;margin-top:3px}.sigpi-step-state{color:#73807c;font-size:9px;margin-top:3px}
.sigpi-section-title{color:#16473e;font-size:15px;font-weight:800;margin:2px 0 5px}.sigpi-section-caption{color:#7b8582;font-size:10px;margin-bottom:8px}
div[data-testid="stVerticalBlockBorderWrapper"]{border-color:var(--border)!important;border-radius:8px!important;background:#fff!important}
div[data-testid="stFileUploader"]{background:#f7f9f8!important;border:1px dashed #b9c9c4!important;border-radius:7px!important}
div[data-testid="stTextInput"] input,div[data-testid="stTextArea"] textarea,div[data-baseweb="select"]>div{border-radius:6px!important}
button[kind="primary"]{background:var(--dark)!important;border-color:var(--dark)!important;border-radius:6px!important;font-weight:700!important}button[kind="primary"]:hover{background:#08493e!important;border-color:#08493e!important}
[data-testid="stMetric"]{background:#fff;border:1px solid var(--border);border-radius:7px;padding:9px 11px}[data-testid="stMetricLabel"]{color:#70807a!important}[data-testid="stMetricValue"]{color:var(--dark)!important}
div[data-testid="stAlert"]{border-radius:7px!important}
.tabla-header{color:#356158!important;font-size:10px!important;font-weight:800!important;text-transform:uppercase;letter-spacing:.2px;line-height:1.1!important;white-space:nowrap;padding:0!important}.tabla-cell{color:#40514d!important;font-size:10px!important;line-height:1.15!important;min-height:24px!important;padding:5px 3px!important;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;border-bottom:1px solid #edf0ef}div[data-testid="column"]{padding-top:0!important;padding-bottom:0!important}
div[data-testid="stButton"]>button{border-radius:6px!important;min-height:27px!important;height:27px!important;padding:0 7px!important;font-size:11px!important;color:var(--dark)!important;border:1px solid #cfe0db!important;background:#f5f9f7!important}div[data-testid="stButton"]>button:hover{background:#e8f2ee!important;border-color:#9fc3b8!important}
div[data-testid="stFormSubmitButton"]>button{border-radius:6px!important;min-height:32px!important;font-weight:700!important}hr{margin:8px 0!important;border-color:#e3e8e6!important}
@media(max-width:900px){.block-container{padding:.7rem .75rem 1.5rem!important}section[data-testid="stSidebar"]{min-width:200px!important;width:200px!important}.sigpi-topbar{min-height:58px}}
</style>
""",unsafe_allow_html=True)

# ============================================================
# ENCABEZADO DE SESIÓN / SIDEBAR
# ============================================================
with st.sidebar:
    st.markdown('<div class="sigpi-side-brand">',unsafe_allow_html=True)
    st.image("Logo_SIGPI.png",width=175)
    st.markdown('<div class="sigpi-side-title">Sistema Integrado de Gestión</div></div>',unsafe_allow_html=True)
    st.markdown("""
    <div class="sigpi-menu-section">Operaciones</div>
    <div class="sigpi-menu-item active"><span class="sigpi-menu-icon">▣</span>Solicitudes</div>
    <div class="sigpi-menu-item"><span class="sigpi-menu-icon">↻</span>Gestiones</div>
    """,unsafe_allow_html=True)

    if es_administrador:
        st.markdown("""
        <div class="sigpi-menu-item"><span class="sigpi-menu-icon">⇧</span>Carga de información</div>
        """,unsafe_allow_html=True)

    st.markdown('<div class="sigpi-menu-section">Sesión</div>',unsafe_allow_html=True)
    st.markdown(f"""
    <div class="sigpi-session-card"><strong>{nombre_actual or usuario_actual}</strong><br>
    Usuario: {usuario_actual}<br>Perfil: {perfil_actual or 'Sin perfil'}</div>
    """,unsafe_allow_html=True)
    if st.button("🚪 Cerrar sesión",use_container_width=True):
        cerrar_sesion()
        for clave in ["auth_user_id","usuario_actual","perfil_actual","nombre_actual","email_actual"]:
            st.session_state.pop(clave,None)
        st.rerun()

# ============================================================
# ENCABEZADO INTERNO
# ============================================================
st.markdown(f"""
<div class="sigpi-topbar"><div><div class="sigpi-top-title">Gestión de Solicitudes</div>
<div class="sigpi-top-subtitle">Sistema Integrado de Gestión de Peticiones e Incidentes · SIGPI</div></div>
<div class="sigpi-user-pill">👤 {nombre_actual or usuario_actual} · {perfil_actual or 'Usuario'}</div></div>
""",unsafe_allow_html=True)

step1,step2,step3=st.columns([1,1,1],gap="small")
with step1: st.markdown('<div class="sigpi-step-card active"><div class="sigpi-step-number">PASO 1</div><div class="sigpi-step-name">Consultar solicitudes</div><div class="sigpi-step-state">Gestión y seguimiento</div></div>',unsafe_allow_html=True)
with step2: st.markdown('<div class="sigpi-step-card"><div class="sigpi-step-number">PASO 2</div><div class="sigpi-step-name">Registrar gestión</div><div class="sigpi-step-state">Observaciones y trazabilidad</div></div>',unsafe_allow_html=True)
with step3: st.markdown('<div class="sigpi-step-card"><div class="sigpi-step-number">PASO 3</div><div class="sigpi-step-name">Actualizar solicitud</div><div class="sigpi-step-state">Cierre y estado</div></div>',unsafe_allow_html=True)
st.markdown('<div style="height:8px"></div>',unsafe_allow_html=True)

# ============================================================
# CARGA DE EXCEL — SOLO ADMINISTRADOR
# ============================================================
archivo_excel = None

if es_administrador:
    with st.container(border=True):
        st.markdown('<div class="sigpi-section-title">📥 Cargar solicitudes desde Excel</div>',unsafe_allow_html=True)
        st.markdown('<div class="sigpi-section-caption">Seleccione el archivo de origen para analizar y cargar las solicitudes en SIGPI.</div>',unsafe_allow_html=True)
        archivo_excel=st.file_uploader(
            "Seleccione un archivo Excel",
            type=["xlsx"],
            help="Se procesarán únicamente DETALLE_GENERAL y DETALLE_FUNCIONALES."
        )

st.caption(f"👤 Sesión activa: {nombre_actual or usuario_actual} · Usuario: {usuario_actual}")


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
                SELECT DISTINCT
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
                INNER JOIN public."PODS" p
                    ON UPPER(TRIM(s."PRODUCT_OWNER"))
                     = UPPER(TRIM(p."NOMBRE"))
                INNER JOIN public."USUARIOS_PODS" up
                    ON up."ID_POD" = p."ID_POD"
                INNER JOIN public."USUARIOS" u
                    ON u."USUARIO" = up."USUARIO"
                WHERE u."USUARIO" = %s
                  AND s."CODIGO_CIERRE" IS NULL
                  AND s."FECHA_CIERRE" IS NULL
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

def obtener_gestiones(id_solicitud):
    db = Database()
    try:
        db.conectar()
        db.execute("SET TIME ZONE 'America/Bogota'")
        db.execute('''
            SELECT "FECHA_GESTION","OBSERVACION"
            FROM public."Gestiones"
            WHERE "ID_SOLICITUD" = %s
            ORDER BY "FECHA_GESTION" DESC
        ''', (id_solicitud,))
        return pd.DataFrame(
            db.fetchall(),
            columns=["FECHA_GESTION","OBSERVACION"]
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
    usuario_carga="Janssen Rodríguez"
):
    """Guarda la auditoría de la carga en public."Auditoria"."""
    fecha_actual = pd.Timestamp.now().to_pydatetime()

    db.execute("""
        INSERT INTO public."Auditoria"
        (
            "NOMBREARCHIVO",
            "FECHACARGUE",
            "REGISTROSGENERALES",
            "REGISTROSFUNCIONALES",
            "ESTADO",
            "OBSERVACIONES",
            "USUARIOCARGA",
            "FECHAREGISTRO"
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

if es_administrador and archivo_excel is not None:
    st.info(f"📄 Archivo seleccionado: {archivo_excel.name}")
    c1, c2 = st.columns(2)

    with c1:
        analizar = st.button("🔎 Analizar archivo", use_container_width=True)
    with c2:
        cargar = st.button("💾 Cargar a Supabase", type="primary", use_container_width=True)

    if analizar:
        try:
            with st.spinner("Analizando archivo Excel..."):
                preview = analizar_excel(archivo_excel)

            st.success(
                f"✅ Análisis terminado. {len(preview)} registro(s) "
                "cumplen el filtro de Product Owner."
            )

            a, b, c = st.columns(3)
            with a:
                st.metric("Registros filtrados", len(preview))
            with b:
                st.metric("DETALLE_GENERAL", len(preview[preview["ORIGEN"].astype(str).str.upper() == "DETALLE_GENERAL"]))
            with c:
                st.metric("DETALLE_FUNCIONALES", len(preview[preview["ORIGEN"].astype(str).str.upper() == "DETALLE_FUNCIONALES"]))

            if not preview.empty:
                st.subheader("👥 Product Owner encontrados")
                resumen = preview["PRODUCT_OWNER"].value_counts().reset_index()
                resumen.columns = ["PRODUCT_OWNER", "CANTIDAD"]
                st.dataframe(resumen, use_container_width=True, hide_index=True)

                st.subheader("📋 Registros que cumplen el filtro")
                st.dataframe(preview, use_container_width=True, hide_index=True)
            else:
                st.warning("⚠️ No se encontraron registros de los tres Product Owner autorizados.")
        except Exception as e:
            st.error("❌ Error analizando el archivo.")
            st.exception(e)

    if cargar:
        db = Database()

        try:
            db.conectar()

            with st.spinner("Cargando solicitudes en Supabase..."):
                # Cargar las solicitudes
                resultado = cargar_excel(archivo_excel, db)

                # Garantizar que todos los TITULO queden almacenados en MAYÚSCULAS.
                db.execute("""
                    UPDATE public."SOLICITUDES"
                    SET "TITULO" = UPPER("TITULO")
                    WHERE "TITULO" IS NOT NULL
                """)

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
                    nombre_archivo=archivo_excel.name,
                    registros_generales=generales,
                    registros_funcionales=funcionales,
                    estado=estado_auditoria,
                    observaciones=observaciones,
                    usuario_carga="Janssen Rodríguez"
                )

                # Confirmar solicitudes + auditoría
                db.commit()

            st.success(
                "✅ Archivo cargado y auditoría registrada correctamente."
            )

            a, b, c, d = st.columns(4)
            a.metric("Generales", generales)
            b.metric("Funcionales", funcionales)
            c.metric("Duplicados", duplicados)
            d.metric("Errores", errores)

            st.rerun()

        except Exception as e:
            db.rollback()
            st.error(
                "❌ No fue posible cargar el archivo ni registrar la auditoría."
            )
            st.error(f"Detalle del error: {e}")
            st.exception(e)

        finally:
            db.cerrar()

try:
    df = obtener_solicitudes(usuario_actual, es_administrador)
except Exception as e:
    st.error("❌ No fue posible consultar las solicitudes.")
    st.exception(e)
    st.stop()

st.success(f"✅ Se han encontrado — {len(df)} solicitud(es) pendiente(s) de gestión")

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



st.subheader(f"Solicitudes ({len(df_filtrado)})")


# ============================================================
# VENTANA TIPO OVERLAY PARA INFORMACIÓN + NUEVA GESTIÓN
# ============================================================
@st.dialog("📄 Información de la solicitud", width="large")
def ventana_gestion(id_solicitud):

    solicitud = df_filtrado[
        df_filtrado["ID_SOLICITUD"] == id_solicitud
    ].iloc[0]

    # Información de la solicitud
    st.markdown("### 📄 Información de la solicitud")

    a, b, c = st.columns(3)

    with a:
        st.markdown(f"**ID_SOLICITUD**  \n{solicitud['ID_SOLICITUD']}")
        st.markdown(f"**TÍTULO**  \n{solicitud['TITULO']}")
        st.markdown(
            f"**SUBSERVICIO AFECTADO**  \n"
            f"{solicitud['SUBSERVICIO_AFECTADO']}"
        )

    with b:
        st.markdown(f"**PRODUCT OWNER**  \n{solicitud['PRODUCT_OWNER']}")
        st.markdown(f"**ASIGNADO A**  \n{solicitud['ASIGNADO_A']}")
        st.markdown(
            f"**NOMBRE ASIGNATARIO**  \n"
            f"{solicitud['NOMBRE_ASIGNATARIO']}"
        )

    with c:
        st.markdown(
            f"**CORREO ASIGNATARIO**  \n"
            f"{solicitud['CORREO_ASIGNATARIO']}"
        )
        st.markdown(f"**ESTADO**  \n{solicitud['STATUS']}")
        st.markdown(
            f"**FECHA APERTURA**  \n"
            f"{solicitud['FECHA_APERTURA']}"
        )

    st.divider()
    st.markdown("### 📝 Nueva gestión")

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
            hora_gestion_texto = st.text_input(
                "Hora de gestión 🕐",
                value="",
                max_chars=8,
                key=f"hora_gestion_{id_solicitud}",
                placeholder="HH:MM:SS",
                help="Digite la hora exactamente en formato HH:MM:SS. Ejemplo: 15:30:42"
            )

        observacion = st.text_area(
            "Observación",
            placeholder="Digite la observación de la gestión...",
            height=130
        )

        guardar = st.form_submit_button(
            "💾 Guardar Gestión",
            use_container_width=False
        )

    if guardar:

        observacion = observacion.strip()

        if not observacion:
            st.warning("⚠️ Debe ingresar una observación.")
            return

        # Guardar EXACTAMENTE la fecha y hora digitadas por el usuario.
        hora_gestion_texto = hora_gestion_texto.strip()

        try:
            hora_gestion = datetime.strptime(
                hora_gestion_texto, "%H:%M:%S"
            ).strftime("%H:%M:%S")
        except ValueError:
            st.error("❌ La hora de gestión debe tener el formato HH:MM:SS. Ejemplo: 15:30:42")
            return

        fecha_db = f"{fecha_seleccionada:%Y-%m-%d} {hora_gestion}"

        db = Database()

        try:
            db.conectar()

            db.execute(
                """
                SELECT 1
                FROM public."Gestiones"
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
                INSERT INTO public."Gestiones"
                ("FECHA_GESTION","ID_SOLICITUD","OBSERVACION")
                VALUES (CAST(%s AS timestamp without time zone), %s, %s)
                RETURNING "FECHA_GESTION"
                """,
                (fecha_db, id_solicitud, observacion)
            )

            fecha_guardada = db.fetchone()[0]

            db.commit()

            st.success(
                f"✅ Gestión guardada correctamente: {fecha_guardada:%Y-%m-%d %H:%M:%S}"
            )
            st.caption(
                f"PostgreSQL devolvió exactamente: {fecha_guardada:%Y-%m-%d %H:%M:%S}"
            )
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
@st.dialog("👁️ Información de la solicitud", width="large")
def ventana_ver_gestion(id_solicitud):

    solicitud = df_filtrado[
        df_filtrado["ID_SOLICITUD"] == id_solicitud
    ].iloc[0]

    # ========================================================
    # INFORMACIÓN DE LA SOLICITUD
    # ========================================================
    st.markdown("### 📄 Información de la solicitud")

    a, b, c = st.columns(3)

    with a:
        st.markdown(
            f"**ID_SOLICITUD**  \n{solicitud['ID_SOLICITUD']}"
        )
        st.markdown(
            f"**TÍTULO**  \n{solicitud['TITULO']}"
        )
        st.markdown(
            f"**SUBSERVICIO AFECTADO**  \n{solicitud['SUBSERVICIO_AFECTADO']}"
        )

    with b:
        st.markdown(
            f"**PRODUCT OWNER**  \n{solicitud['PRODUCT_OWNER']}"
        )
        st.markdown(
            f"**ASIGNADO A**  \n{solicitud['ASIGNADO_A']}"
        )
        st.markdown(
            f"**NOMBRE ASIGNATARIO**  \n{solicitud['NOMBRE_ASIGNATARIO']}"
        )

    with c:
        st.markdown(
            f"**CORREO ASIGNATARIO**  \n{solicitud['CORREO_ASIGNATARIO']}"
        )
        st.markdown(
            f"**ESTADO**  \n{solicitud['STATUS']}"
        )

        fecha_apertura = solicitud['FECHA_APERTURA']
        if pd.notna(fecha_apertura):
            fecha_apertura = pd.to_datetime(
                fecha_apertura
            ).strftime("%Y-%m-%d %H:%M:%S")

        st.markdown(
            f"**FECHA APERTURA**  \n{fecha_apertura}"
        )

    # ========================================================
    # GESTIONES REGISTRADAS
    # ========================================================
    st.divider()
    st.markdown("### 📝 Gestiones registradas")

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

    if "FECHA_GESTION" in gestiones_mostrar.columns:
        gestiones_mostrar["FECHA_GESTION"] = pd.to_datetime(
            gestiones_mostrar["FECHA_GESTION"],
            errors="coerce"
        ).dt.strftime("%Y-%m-%d %H:%M:%S")

    # Se muestran únicamente Fecha de gestión y Observación.
    # ID_GESTION NO se consulta ni se muestra.
    st.dataframe(
        gestiones_mostrar,
        use_container_width=True,
        hide_index=True,
        column_config={
            "FECHA_GESTION": st.column_config.TextColumn(
                "Fecha gestión",
                width="medium"
            ),
            "OBSERVACION": st.column_config.TextColumn(
                "Observación",
                width="large"
            )
        }
    )


# ============================================================
# VENTANA TIPO OVERLAY PARA ACTUALIZAR SOLICITUD
# ============================================================
@st.dialog("⚙️ Actualizar solicitud", width="large")
def ventana_actualizar(id_solicitud):

    solicitud = df_filtrado[
        df_filtrado["ID_SOLICITUD"] == id_solicitud
    ].iloc[0]

    st.markdown("### 📄 Información de la solicitud")

    a, b, c = st.columns(3)

    with a:
        st.markdown(f"**ID_SOLICITUD**  \n{solicitud['ID_SOLICITUD']}")
        st.markdown(f"**TÍTULO**  \n{solicitud['TITULO']}")
        st.markdown(
            f"**SUBSERVICIO AFECTADO**  \n"
            f"{solicitud['SUBSERVICIO_AFECTADO']}"
        )

    with b:
        st.markdown(f"**PRODUCT OWNER**  \n{solicitud['PRODUCT_OWNER']}")
        st.markdown(f"**ASIGNADO A**  \n{solicitud['ASIGNADO_A']}")
        st.markdown(
            f"**NOMBRE ASIGNATARIO**  \n"
            f"{solicitud['NOMBRE_ASIGNATARIO']}"
        )

    with c:
        st.markdown(
            f"**CORREO ASIGNATARIO**  \n"
            f"{solicitud['CORREO_ASIGNATARIO']}"
        )
        st.markdown(f"**ESTADO**  \n{solicitud['STATUS']}")
        st.markdown(
            f"**FECHA APERTURA**  \n"
            f"{solicitud['FECHA_APERTURA']}"
        )

    st.divider()
    st.markdown("### ⚙️ Actualizar solicitud")

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
            hora_default = ""
        else:
            fecha_default = (
                fecha_inicial.date()
                if pd.notna(fecha_actual)
                else pd.Timestamp.now().date()
            )
            hora_default = (
                fecha_inicial.strftime("%H:%M:%S")
                if pd.notna(fecha_actual)
                else ""
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
                hora_cierre_texto = st.text_input(
                    "Hora de cierre 🕐",
                    value=hora_default,
                    max_chars=8,
                    placeholder="HH:MM:SS",
                    help="Digite la hora exactamente en formato HH:MM:SS. Ejemplo: 18:12:34",
                    disabled=not codigo_seleccionado,
                    key=f"hora_cierre_{id_solicitud}"
                )

            actualizar = st.form_submit_button(
                "🔄 Actualizar Solicitud",
                use_container_width=False
            )

    if actualizar:

        # Si no hay código de cierre, se limpia fecha y hora.
        if not nuevo_codigo:
            fecha_cierre_db = None
        else:
            # Si hay código de cierre, fecha y hora son obligatorias.
            hora_cierre_texto = hora_cierre_texto.strip()

            if fecha_cierre_fecha is None:
                st.error("❌ Debe seleccionar la fecha de cierre.")
                return

            if not hora_cierre_texto:
                st.error("❌ Debe ingresar la hora de cierre.")
                return

            try:
                hora_cierre = datetime.strptime(
                    hora_cierre_texto, "%H:%M:%S"
                ).strftime("%H:%M:%S")
            except ValueError:
                st.error(
                    "❌ La hora de cierre debe tener el formato HH:MM:SS. "
                    "Ejemplo: 18:12:34"
                )
                return

            fecha_cierre_db = (
                f"{fecha_cierre_fecha:%Y-%m-%d} {hora_cierre}"
            )

        db = Database()

        try:
            db.conectar()

            db.execute(
                """
                UPDATE public."SOLICITUDES"
                SET "FECHA_CIERRE" = CAST(%s AS timestamp without time zone),
                    "STATUS" = %s,
                    "CODIGO_CIERRE" = %s
                WHERE "ID_SOLICITUD" = %s
                RETURNING "FECHA_CIERRE"
                """,
                (
                    fecha_cierre_db,
                    nuevo_status or None,
                    nuevo_codigo or None,
                    id_solicitud
                )
            )

            fecha_cierre_guardada = db.fetchone()[0]

            db.commit()

            if fecha_cierre_guardada is not None:
                fecha_hora_mensaje = fecha_cierre_guardada.strftime("%Y-%m-%d %H:%M:%S")
            else:
                fecha_hora_mensaje = "Sin fecha/hora de cierre"

            st.success(
                f"✅ Solicitud actualizada. Fecha/hora guardada: {fecha_hora_mensaje}"
            )
            st.caption(
                f"PostgreSQL devolvió exactamente: {fecha_hora_mensaje}"
            )
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
# ESTILO TABLA PRINCIPAL
# ============================================================
st.markdown("""
<style>
/* Encabezados de la tabla */
.tabla-header {
    font-size: 13px !important;
    font-weight: 700 !important;
    line-height: 1 !important;
    white-space: nowrap;
    color: #24344D;
    padding: 0 !important;
    margin: 0 !important;
}

/* Celdas de la tabla */
.tabla-cell {
    font-size: 12px !important;
    line-height: 1 !important;
    height: 22px !important;
    min-height: 22px !important;
    padding: 0 !important;
    margin: 0 !important;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

/* Reducir espacios internos de las columnas */
div[data-testid="column"] {
    padding-top: 0 !important;
    padding-bottom: 0 !important;
}

/* Botones + de gestión y actualización */
div[data-testid="stButton"] > button {
    min-height: 24px !important;
    height: 24px !important;
    padding: 0 4px !important;
    margin: 0 !important;
    font-size: 11px !important;
    line-height: 1 !important;
    border-radius: 50% !important;
}

/* Botones de los formularios: misma forma que "Guardar Gestión" */
div[data-testid="stFormSubmitButton"] > button,
div[data-testid="stFormSubmitButton"] button {
    min-height: 26px !important;
    height: 26px !important;
    width: auto !important;
    min-width: 0 !important;
    padding: 0 10px !important;
    margin: 0 !important;
    font-size: 11px !important;
    line-height: 1 !important;
    border-radius: 6px !important;
}


/* Separador del encabezado */
hr {
    margin: 2px 0 !important;
}
</style>
""", unsafe_allow_html=True)

# ============================================================
# TABLA PRINCIPAL
# ============================================================
anchos_tabla = [
    1.0, 3.5, 1.5, 2.1, 1.8, 1.5,
    1.0, 1.8, 2.5, 0.8, 0.9, 0.9
]

headers = st.columns(anchos_tabla)

titulos_tabla = [
    "Solicitud",
    "Titulo",
    "Apertura",
    "Servicio",
    "Product Owner",
    "Estado",
    "Registro",
    "Nombre Asignatario",
    "Correo Asignatario",
    "Gestionar",
    "Ver Gestión",
    "Actualizar"
]

for col, title in zip(headers, titulos_tabla):
    with col:
        st.markdown(
            f'<div class="tabla-header">{title}</div>',
            unsafe_allow_html=True
        )

st.divider()

for _, fila in df_filtrado.iterrows():

    sid = fila["ID_SOLICITUD"]

    cols = st.columns(anchos_tabla)

    valores = [
        fila["ID_SOLICITUD"],
        fila["TITULO"],
        fila["FECHA_APERTURA"],
        fila["SUBSERVICIO_AFECTADO"],
        fila["PRODUCT_OWNER"],
        fila["STATUS"],
        fila["ASIGNADO_A"],
        fila["NOMBRE_ASIGNATARIO"],
        fila["CORREO_ASIGNATARIO"]
    ]

    for i, valor in enumerate(valores):

        with cols[i]:

            if i == 2 and pd.notna(valor):
                valor = pd.to_datetime(valor).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )

            # Título y demás campos conservan el contenido,
            # pero se muestran compactos y sin aumentar la altura.
            valor = "" if pd.isna(valor) else str(valor)

            st.markdown(
                f'<div class="tabla-cell" title="{valor}">{valor}</div>',
                unsafe_allow_html=True
            )

    # Botón para adicionar gestión
    with cols[9]:
        if st.button(
            "✏️",
            key=f"gestion_{sid}",
            help=f"Adicionar gestión a {sid}",
            use_container_width=True
        ):
            ventana_gestion(sid)

    # Botón para ver las gestiones registradas
    with cols[10]:
        if st.button(
            "🔍",
            key=f"ver_gestion_{sid}",
            help=f"Ver gestión de {sid}",
            use_container_width=True
        ):
            ventana_ver_gestion(sid)

    # Botón para actualizar solicitud
    with cols[11]:
        if st.button(
            "📝",
            key=f"actualizar_{sid}",
            help=f"Actualizar solicitud {sid}",
            use_container_width=True
        ):
            ventana_actualizar(sid)


if df_filtrado.empty:
    st.info(
        "ℹ️ No existen solicitudes que coincidan con el criterio de búsqueda."
    )
