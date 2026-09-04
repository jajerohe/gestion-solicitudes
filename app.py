import streamlit as st
import pandas as pd

from database import Database
from excel_web import analizar_excel, cargar_excel

st.set_page_config(
    page_title="Gestión de Solicitudes - ECP",
    page_icon="📋",
    layout="wide"
)

st.markdown(
    """
    <div style="display: flex; align-items: center; gap: 15px;">
        <span style="font-size: 42px;">📋</span>
        <span style="font-size: 42px; font-weight: 700; color: #24344D;">
            Gestión de Solicitudes - ECP
        </span>
    </div>

    <div style="margin-left: 2px; margin-top: 2px;
                color: #666; font-size: 13px;">
        Desarrollado por <b>Janssen Rodríguez</b>
    </div>
    """,
    unsafe_allow_html=True
)

def obtener_solicitudes():
    db = Database()
    try:
        db.conectar()
        sql = '''
            SELECT "ID_SOLICITUD","TITULO","FECHA_APERTURA",
                   "SUBSERVICIO_AFECTADO","PRODUCT_OWNER","STATUS",
                   "ASIGNADO_A","NOMBRE_ASIGNATARIO","CORREO_ASIGNATARIO"
            FROM public."Solicitudes"
            WHERE "CODIGO_CIERRE" IS NULL
              AND "FECHA_CIERRE" IS NULL
            ORDER BY "FECHA_APERTURA" ASC
        '''
        db.execute(sql)
        registros = db.fetchall()
        columnas = [
            "ID_SOLICITUD","TITULO","FECHA_APERTURA","SUBSERVICIO_AFECTADO",
            "PRODUCT_OWNER","STATUS","ASIGNADO_A","NOMBRE_ASIGNATARIO",
            "CORREO_ASIGNATARIO"
        ]
        return pd.DataFrame(registros, columns=columnas)
    finally:
        db.cerrar()

def obtener_gestiones(id_solicitud):
    db = Database()
    try:
        db.conectar()
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

st.subheader("📤 Cargar solicitudes desde Excel")
archivo_excel = st.file_uploader(
    "Seleccione un archivo Excel",
    type=["xlsx"],
    help="Se procesarán únicamente DETALLE_GENERAL y DETALLE_FUNCIONALES."
)

if archivo_excel is not None:
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
                st.metric("DETALLE_GENERAL", len(preview[preview["HOJA"] == "DETALLE_GENERAL"]))
            with c:
                st.metric("DETALLE_FUNCIONALES", len(preview[preview["HOJA"] == "DETALLE_FUNCIONALES"]))

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
                    UPDATE public."Solicitudes"
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
    df = obtener_solicitudes()
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



# ============================================================
# ESTILO TABLA COMPACTA
# ============================================================
st.markdown("""
<style>
/* Encabezados de la tabla */
.tabla-header {
    font-size: 10px !important;
    font-weight: 700;
    line-height: 1.05;
    white-space: nowrap;
    color: #24344D;
}

/* Celdas */
.tabla-cell {
    font-size: 10px !important;
    line-height: 1.1;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    padding-top: 2px;
    padding-bottom: 2px;
}

/* Botones de acción */
div[data-testid="stButton"] > button {
    min-height: 27px;
    height: 27px;
    padding: 0px 4px;
    font-size: 12px;
    border-radius: 50%;
}

/* Separadores más compactos */
hr {
    margin: 3px 0px !important;
}
</style>
""", unsafe_allow_html=True)

st.subheader(f"Solicitudes ({len(df_filtrado)})")

# Solicitud y acción seleccionadas para mostrar el panel dentro de la página.
if "solicitud_seleccionada" not in st.session_state:
    st.session_state.solicitud_seleccionada = None

if "accion_solicitud" not in st.session_state:
    st.session_state.accion_solicitud = None

def seleccionar_solicitud(id_solicitud, accion):
    st.session_state.solicitud_seleccionada = id_solicitud
    st.session_state.accion_solicitud = accion


# ============================================================
# PANEL DE ACCIÓN - APARECE SOBRE LA TABLA
# ============================================================
id_panel = st.session_state.solicitud_seleccionada
accion_panel = st.session_state.accion_solicitud

if id_panel is not None and id_panel in df_filtrado["ID_SOLICITUD"].tolist():

    solicitud_panel = df_filtrado[
        df_filtrado["ID_SOLICITUD"] == id_panel
    ].iloc[0]

    st.markdown(
        """
        <div style="
            border: 1px solid #d9d9d9;
            border-radius: 10px;
            padding: 18px 22px 20px 22px;
            margin: 10px 0 20px 0;
            background: #ffffff;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        ">
        """,
        unsafe_allow_html=True
    )

    titulo_panel = (
        "📝 Nueva gestión"
        if accion_panel == "gestion"
        else "⚙️ Actualizar solicitud"
    )

    c_titulo, c_cerrar = st.columns([8, 1])

    with c_titulo:
        st.subheader(f"{titulo_panel} — {id_panel}")

    with c_cerrar:
        if st.button("✖ Cerrar", key="cerrar_panel", use_container_width=True):
            st.session_state.solicitud_seleccionada = None
            st.session_state.accion_solicitud = None
            st.rerun()

    # Información de la solicitud.
    a, b, c = st.columns(3)

    with a:
        st.markdown(f"**ID_SOLICITUD**  \n{solicitud_panel['ID_SOLICITUD']}")
        st.markdown(f"**TÍTULO**  \n{solicitud_panel['TITULO']}")
        st.markdown(
            f"**SUBSERVICIO AFECTADO**  \n"
            f"{solicitud_panel['SUBSERVICIO_AFECTADO']}"
        )

    with b:
        st.markdown(f"**PRODUCT OWNER**  \n{solicitud_panel['PRODUCT_OWNER']}")
        st.markdown(f"**ASIGNADO A**  \n{solicitud_panel['ASIGNADO_A']}")
        st.markdown(
            f"**NOMBRE ASIGNATARIO**  \n"
            f"{solicitud_panel['NOMBRE_ASIGNATARIO']}"
        )

    with c:
        st.markdown(
            f"**CORREO ASIGNATARIO**  \n"
            f"{solicitud_panel['CORREO_ASIGNATARIO']}"
        )
        st.markdown(f"**ESTADO**  \n{solicitud_panel['STATUS']}")
        st.markdown(
            f"**FECHA APERTURA**  \n"
            f"{solicitud_panel['FECHA_APERTURA']}"
        )

    st.divider()

    # ========================================================
    # NUEVA GESTIÓN
    # ========================================================
    if accion_panel == "gestion":

        with st.form(f"form_gestion_panel_{id_panel}"):

            ahora = pd.Timestamp.now()
            c_fecha, c_hora = st.columns(2)

            with c_fecha:
                fecha_seleccionada = st.date_input(
                    "Fecha de gestión",
                    value=ahora.date(),
                    format="DD/MM/YYYY"
                )

            with c_hora:
                hora_seleccionada = st.time_input(
                    "Hora de gestión 🕐",
                    value=ahora.time().replace(microsecond=0),
                    step=1,
                    format="24h"
                )

            observacion = st.text_area(
                "Observación",
                placeholder="Digite la observación de la gestión...",
                height=130
            )

            guardar = st.form_submit_button(
                "💾 Guardar Gestión",
                use_container_width=True
            )

        if guardar:

            observacion = observacion.strip()

            if not observacion:
                st.warning("⚠️ Debe ingresar una observación.")
            else:

                try:
                    fecha = pd.Timestamp.combine(
                        fecha_seleccionada,
                        hora_seleccionada
                    ).to_pydatetime()

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
                            (id_panel, observacion)
                        )

                        if db.fetchone():
                            st.warning(
                                "⚠️ Esta observación ya existe para esta solicitud."
                            )
                        else:
                            db.execute(
                                """
                                INSERT INTO public."Gestiones"
                                ("FECHA_GESTION","ID_SOLICITUD","OBSERVACION")
                                VALUES (%s,%s,%s)
                                """,
                                (fecha, id_panel, observacion)
                            )

                            db.commit()

                            st.success(
                                "✅ Gestión guardada correctamente."
                            )

                            st.session_state.solicitud_seleccionada = None
                            st.session_state.accion_solicitud = None
                            st.rerun()

                    except Exception as e:
                        db.rollback()
                        st.error("❌ No fue posible guardar la gestión.")
                        st.exception(e)

                    finally:
                        db.cerrar()

                except Exception as e:
                    st.error("❌ La fecha y hora no tienen un formato válido.")
                    st.exception(e)

    # ========================================================
    # ACTUALIZAR SOLICITUD
    # ========================================================
    elif accion_panel == "actualizar":

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
            "Cancelado por el usuario",
            "Resuelto por soporte tecnico"
        ]

        status_opciones = [""] + estados
        codigo_opciones = [""] + codigos

        status_actual = solicitud_panel["STATUS"]
        codigo_actual = solicitud_panel.get("CODIGO_CIERRE", None)
        fecha_actual = solicitud_panel.get("FECHA_CIERRE", None)

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

        with st.form(f"form_actualizar_panel_{id_panel}"):

            a, b = st.columns(2)

            with a:
                nuevo_status = st.selectbox(
                    "Estado",
                    status_opciones,
                    index=i_status
                )

            with b:
                nuevo_codigo = st.selectbox(
                    "Código de cierre",
                    codigo_opciones,
                    index=i_codigo
                )

            c_fecha, c_hora = st.columns(2)

            with c_fecha:
                fecha_cierre_fecha = st.date_input(
                    "Fecha de cierre",
                    value=fecha_inicial.date(),
                    format="DD/MM/YYYY"
                )

            with c_hora:
                fecha_cierre_hora = st.time_input(
                    "Hora de cierre 🕐",
                    value=fecha_inicial.time().replace(microsecond=0),
                    step=1,
                    format="24h"
                )

            actualizar = st.form_submit_button(
                "🔄 Actualizar Solicitud",
                use_container_width=True
            )

        if actualizar:

            try:
                fecha_db = pd.Timestamp.combine(
                    fecha_cierre_fecha,
                    fecha_cierre_hora
                ).to_pydatetime()

                db = Database()

                try:
                    db.conectar()

                    db.execute(
                        """
                        UPDATE public."Solicitudes"
                        SET "FECHA_CIERRE" = %s,
                            "STATUS" = %s,
                            "CODIGO_CIERRE" = %s
                        WHERE "ID_SOLICITUD" = %s
                        """,
                        (
                            fecha_db,
                            nuevo_status or None,
                            nuevo_codigo or None,
                            id_panel
                        )
                    )

                    db.commit()

                    st.success(
                        "✅ La solicitud fue actualizada correctamente."
                    )

                    st.session_state.solicitud_seleccionada = None
                    st.session_state.accion_solicitud = None
                    st.rerun()

                except Exception as e:
                    db.rollback()
                    st.error(
                        "❌ No fue posible actualizar la solicitud."
                    )
                    st.exception(e)

                finally:
                    db.cerrar()

            except Exception as e:
                st.warning(
                    "⚠️ La fecha y hora de cierre no tienen un formato válido."
                )
                st.exception(e)

    st.markdown("</div>", unsafe_allow_html=True)


# ============================================================
# TABLA DE SOLICITUDES
# ============================================================
headers = st.columns([
    1.25, 3.7, 1.55, 2.15, 1.75, 1.45, 1.05, 2.25, 2.65, 0.65, 0.75
])

for col, title in zip(headers, [
    "ID_SOLICITUD",
    "TITULO",
    "FECHA_APERTURA",
    "SUBSERVICIO_AFECTADO",
    "PRODUCT_OWNER",
    "STATUS",
    "ASIGNADO_A",
    "NOMBRE_ASIGNATARIO",
    "CORREO_ASIGNATARIO",
    "GESTIÓN",
    "ACTUALIZAR"
]):
    col.markdown(
        f'<div class="tabla-header">{title}</div>',
        unsafe_allow_html=True
    )

st.divider()

for _, fila in df_filtrado.iterrows():

    sid = fila["ID_SOLICITUD"]

    cols = st.columns([
        1.25, 3.7, 1.55, 2.15, 1.75, 1.45, 1.05, 2.25, 2.65, 0.65, 0.75
    ])

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

            st.markdown(
                f'<div class="tabla-cell" title="{str(valor)}">{str(valor)}</div>',
                unsafe_allow_html=True
            )

    with cols[9]:
        if st.button(
            "➕",
            key=f"gestion_{sid}",
            help=f"Adicionar gestión a {sid}",
            use_container_width=True
        ):
            seleccionar_solicitud(sid, "gestion")
            st.rerun()

    with cols[10]:
        if st.button(
            "➕",
            key=f"actualizar_{sid}",
            help=f"Actualizar solicitud {sid}",
            use_container_width=True
        ):
            seleccionar_solicitud(sid, "actualizar")
            st.rerun()

    st.divider()


if df_filtrado.empty:
    st.info(
        "ℹ️ No existen solicitudes que coincidan con el criterio de búsqueda."
    )
