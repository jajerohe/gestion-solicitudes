import streamlit as st
import pandas as pd

from database import Database
from excel_web import cargar_excel


# ============================================================
# CONFIGURACIÓN
# ============================================================

st.set_page_config(
    page_title="Gestión de Solicitudes - ECP",
    page_icon="📋",
    layout="wide"
)


# ============================================================
# TÍTULO
# ============================================================

st.title("📋 Gestión de Solicitudes - ECP")

# ============================================================
# CARGA DE EXCEL
# ============================================================

st.subheader("📤 Cargar solicitudes desde Excel")

archivo_excel = st.file_uploader(
    "Seleccione un archivo Excel",
    type=["xlsx"],
    help=(
        "El archivo debe contener las hojas "
        "DETALLE_GENERAL y/o DETALLE_FUNCIONALES."
    )
)

# ============================================================
# PROCESAR EXCEL
# ============================================================

if archivo_excel is not None:

    st.info(
        f"📄 Archivo seleccionado: "
        f"{archivo_excel.name}"
    )


    if st.button(
        "🚀 Procesar archivo",
        type="primary"
    ):

        db = Database()

        try:

            db.conectar()


            with st.spinner(
                "Procesando archivo Excel..."
            ):

                resultado = cargar_excel(
                    archivo_excel,
                    db
                )


            db.commit()


            st.success(
                "✅ Archivo procesado correctamente."
            )


            # ------------------------------------------------
            # RESUMEN
            # ------------------------------------------------

            col1, col2, col3 = st.columns(3)


            with col1:

                st.metric(
                    "Registros generales",
                    resultado["generales"]
                )


            with col2:

                st.metric(
                    "Registros funcionales",
                    resultado["funcionales"]
                )


            with col3:

                st.metric(
                    "Duplicados",
                    resultado["duplicados"]
                )


        except Exception as e:

            db.rollback()

            st.error(
                "❌ Error procesando el archivo."
            )

            st.exception(e)


        finally:

            db.cerrar()


# ============================================================
# CONEXIÓN
# ============================================================

db = Database()

try:

    db.conectar()

except Exception as e:

    st.error("❌ No fue posible conectar con Supabase")
    st.exception(e)
    st.stop()


# ============================================================
# CARGAR SOLICITUDES
# ============================================================

sql_solicitudes = """
    SELECT
        "ID_SOLICITUD",
        "TITULO",
        "FECHA_APERTURA",
        "SUBSERVICIO_AFECTADO",
        "PRODUCT_OWNER",
        "STATUS",
        "ASIGNADO_A",
        "NOMBRE_ASIGNATARIO",
        "CORREO_ASIGNATARIO",
        "FECHA_CIERRE",
        "CODIGO_CIERRE"
    FROM public."Solicitudes"
    WHERE "STATUS" NOT IN ('RESOLVED', 'COMPLETADO')
      AND "FECHA_CIERRE" IS NULL
    ORDER BY "FECHA_APERTURA" ASC
"""


try:

    db.execute(sql_solicitudes)

    registros = db.fetchall()

except Exception as e:

    st.error("❌ Error consultando las solicitudes")
    st.exception(e)

    db.cerrar()

    st.stop()


db.cerrar()


# ============================================================
# DATAFRAME
# ============================================================

columnas = [
    "ID_SOLICITUD",
    "TITULO",
    "FECHA_APERTURA",
    "SUBSERVICIO_AFECTADO",
    "PRODUCT_OWNER",
    "STATUS",
    "ASIGNADO_A",
    "NOMBRE_ASIGNATARIO",
    "CORREO_ASIGNATARIO",
    "FECHA_CIERRE",
    "CODIGO_CIERRE"
]


df = pd.DataFrame(
    registros,
    columns=columnas
)


# ============================================================
# INFORMACIÓN
# ============================================================

st.success(
    f"✅ Conexión con Supabase exitosa — "
    f"{len(df)} solicitud(es) encontrada(s)"
)


# ============================================================
# BUSCADOR
# ============================================================

texto_busqueda = st.text_input(
    "🔎 Buscar solicitud",
    placeholder="Digite ID, título, estado, asignado, Product Owner..."
)


# ============================================================
# FILTRAR
# ============================================================

if texto_busqueda:

    texto = texto_busqueda.lower()

    mascara = df.astype(str).apply(
        lambda columna: columna.str.lower().str.contains(
            texto,
            na=False
        )
    )

    df_filtrado = df[
        mascara.any(axis=1)
    ]

else:

    df_filtrado = df


# ============================================================
# MOSTRAR SOLICITUDES
# ============================================================

st.subheader(
    f"Solicitudes ({len(df_filtrado)})"
)


st.dataframe(
    df_filtrado,
    use_container_width=True,
    hide_index=True
)


# ============================================================
# SELECCIONAR SOLICITUD
# ============================================================

if len(df_filtrado) > 0:

    st.divider()

    st.subheader("📌 Seleccionar solicitud")


    opciones = df_filtrado["ID_SOLICITUD"].tolist()


    id_seleccionado = st.selectbox(
        "Solicitud",
        opciones
    )


    # ========================================================
    # OBTENER DATOS DE LA SOLICITUD
    # ========================================================

    solicitud = df_filtrado[
        df_filtrado["ID_SOLICITUD"] == id_seleccionado
    ].iloc[0]


    # ========================================================
    # INFORMACIÓN DE LA SOLICITUD
    # ========================================================

    st.subheader("📄 Información de la solicitud")


    col1, col2, col3 = st.columns(3)


    with col1:

        st.markdown(
            f"**ID_SOLICITUD**  \n"
            f"{solicitud['ID_SOLICITUD']}"
        )

        st.markdown(
            f"**TÍTULO**  \n"
            f"{solicitud['TITULO']}"
        )

        st.markdown(
            f"**SUBSERVICIO AFECTADO**  \n"
            f"{solicitud['SUBSERVICIO_AFECTADO']}"
        )


    with col2:

        st.markdown(
            f"**PRODUCT OWNER**  \n"
            f"{solicitud['PRODUCT_OWNER']}"
        )

        st.markdown(
            f"**ASIGNADO A**  \n"
            f"{solicitud['ASIGNADO_A']}"
        )

        st.markdown(
            f"**NOMBRE ASIGNATARIO**  \n"
            f"{solicitud['NOMBRE_ASIGNATARIO']}"
        )


    with col3:

        st.markdown(
            f"**CORREO ASIGNATARIO**  \n"
            f"{solicitud['CORREO_ASIGNATARIO']}"
        )

        st.markdown(
            f"**ESTADO**  \n"
            f"{solicitud['STATUS']}"
        )

        st.markdown(
            f"**FECHA APERTURA**  \n"
            f"{solicitud['FECHA_APERTURA']}"
        )


    # ========================================================
    # HISTORIAL DE GESTIONES
    # ========================================================

    st.divider()

    st.subheader("📜 Historial de gestiones")


    db = Database()


    try:

        db.conectar()


        sql_gestiones = """
            SELECT
                "ID_GESTION",
                "FECHA_GESTION",
                "OBSERVACION"
            FROM public."Gestiones"
            WHERE "ID_SOLICITUD" = %s
            ORDER BY "FECHA_GESTION" DESC
        """


        db.execute(
            sql_gestiones,
            (id_seleccionado,)
        )


        gestiones = db.fetchall()


    except Exception as e:

        st.error("❌ Error consultando el historial")
        st.exception(e)

        gestiones = []


    finally:

        db.cerrar()


        # ========================================================
    # MOSTRAR HISTORIAL
    # ========================================================

    if gestiones:

        df_gestiones = pd.DataFrame(
            gestiones,
            columns=[
                "ID_GESTION",
                "FECHA_GESTION",
                "OBSERVACION"
            ]
        )

        st.dataframe(
            df_gestiones,
            use_container_width=True,
            hide_index=True
        )

    else:

        st.info(
            "ℹ️ No existen gestiones registradas "
            "para esta solicitud."
        )


    # ========================================================
    # NUEVA GESTIÓN
    # ========================================================

    st.divider()

    st.subheader("📝 Nueva gestión")


    with st.form("form_gestion"):

        fecha_gestion = st.text_input(
            "Fecha de gestión",
            value=pd.Timestamp.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        )


        observacion = st.text_area(
            "Observación",
            placeholder="Digite la observación de la gestión...",
            height=150
        )


        guardar = st.form_submit_button(
            "💾 Guardar Gestión"
        )


    # ========================================================
    # GUARDAR GESTIÓN
    # ========================================================

    if guardar:

        observacion = observacion.strip()


        # ----------------------------------------------------
        # VALIDAR OBSERVACIÓN
        # ----------------------------------------------------

        if not observacion:

            st.warning(
                "⚠️ Debe ingresar una observación."
            )

            st.stop()


        # ----------------------------------------------------
        # VALIDAR FECHA
        # ----------------------------------------------------

        try:

            fecha = pd.to_datetime(
                fecha_gestion
            ).to_pydatetime()

        except Exception:

            st.error(
                "❌ La fecha no tiene un formato válido."
            )

            st.stop()


        # ----------------------------------------------------
        # CONECTAR
        # ----------------------------------------------------

        db = Database()


        try:

            db.conectar()


            # ------------------------------------------------
            # VALIDAR DUPLICADO
            # ------------------------------------------------

            sql_duplicado = """
                SELECT 1
                FROM public."Gestiones"
                WHERE "ID_SOLICITUD" = %s
                  AND "OBSERVACION" = %s
                LIMIT 1
            """


            db.execute(
                sql_duplicado,
                (
                    id_seleccionado,
                    observacion
                )
            )


            duplicado = db.fetchone()


            if duplicado:

                st.warning(
                    "⚠️ Esta observación ya existe "
                    "para esta solicitud."
                )

                db.cerrar()

                st.stop()


            # ------------------------------------------------
            # INSERTAR GESTIÓN
            # ------------------------------------------------

            sql_insert = """
                INSERT INTO public."Gestiones"
                (
                    "FECHA_GESTION",
                    "ID_SOLICITUD",
                    "OBSERVACION"
                )
                VALUES (%s, %s, %s)
            """


            db.execute(
                sql_insert,
                (
                    fecha,
                    id_seleccionado,
                    observacion
                )
            )


            db.commit()


            st.success(
                "✅ Gestión guardada correctamente."
            )


        except Exception as e:

            db.rollback()

            st.error(
                "❌ No fue posible guardar la gestión."
            )

            st.exception(e)


        finally:

            db.cerrar()


        # ----------------------------------------------------
        # RECARGAR PÁGINA
        # ----------------------------------------------------

        st.rerun()

    # ========================================================
    # ACTUALIZAR SOLICITUD
    # ========================================================

    st.divider()

    st.subheader("⚙️ Actualizar solicitud")


    estados = [
        "Cancelled",
        "Completado",
        "En curso",
        "Fulfilled",
        "In Progress",
        "Pendiente de cliente",
        "Pendiente de proveedor",
        "Resuelto",
        "Suspendido",
        "Trabajo en curso"
    ]


    codigos_cierre = [
        "Cancelado por incumplimiento de politicas",
        "Cancelado por el usuario",
        "Resuelto por soporte tecnico"
    ]


    # --------------------------------------------------------
    # VALORES ACTUALES
    # --------------------------------------------------------

    status_actual = solicitud["STATUS"]

    codigo_actual = solicitud["CODIGO_CIERRE"]

    fecha_cierre_actual = solicitud["FECHA_CIERRE"]


    # --------------------------------------------------------
    # FORMULARIO
    # --------------------------------------------------------

    with st.form("form_actualizar_solicitud"):

        col1, col2 = st.columns(2)


        with col1:

            status_opciones = [""] + estados

            indice_status = 0

            if status_actual in estados:

                indice_status = (
                    status_opciones.index(status_actual)
                )


            nuevo_status = st.selectbox(
                "Estado",
                status_opciones,
                index=indice_status
            )


        with col2:

            codigo_opciones = [""] + codigos_cierre

            indice_codigo = 0

            if codigo_actual in codigos_cierre:

                indice_codigo = (
                    codigo_opciones.index(codigo_actual)
                )


            nuevo_codigo = st.selectbox(
                "Código de cierre",
                codigo_opciones,
                index=indice_codigo
            )


        # ----------------------------------------------------
        # FECHA DE CIERRE
        # ----------------------------------------------------

        if pd.notna(fecha_cierre_actual):

            fecha_texto_actual = pd.to_datetime(
                fecha_cierre_actual
            ).strftime(
                "%Y-%m-%d %H:%M:%S"
            )

        else:

            fecha_texto_actual = ""


        fecha_cierre = st.text_input(
            "Fecha de cierre",
            value=fecha_texto_actual,
            placeholder="YYYY-MM-DD HH:MM:SS"
        )


        actualizar = st.form_submit_button(
            "🔄 Actualizar Solicitud"
        )


    # ========================================================
    # PROCESAR ACTUALIZACIÓN
    # ========================================================

    if actualizar:

        # ----------------------------------------------------
        # VALIDAR FECHA
        # ----------------------------------------------------

        fecha_cierre_limpia = fecha_cierre.strip()


        if fecha_cierre_limpia == "":

            fecha_cierre_db = None

        else:

            try:

                fecha_cierre_db = pd.to_datetime(
                    fecha_cierre_limpia
                ).to_pydatetime()

            except Exception:

                st.warning(
                    "⚠️ La fecha de cierre debe tener el formato "
                    "YYYY-MM-DD HH:MM:SS"
                )

                st.stop()


        # ----------------------------------------------------
        # PREPARAR VALORES
        # ----------------------------------------------------

        status_db = (
            nuevo_status
            if nuevo_status
            else None
        )


        codigo_db = (
            nuevo_codigo
            if nuevo_codigo
            else None
        )


        # ----------------------------------------------------
        # CONECTAR
        # ----------------------------------------------------

        db = Database()


        try:

            db.conectar()


            sql_update = """
                UPDATE public."Solicitudes"
                SET
                    "FECHA_CIERRE" = %s,
                    "STATUS" = %s,
                    "CODIGO_CIERRE" = %s
                WHERE "ID_SOLICITUD" = %s
            """


            db.execute(
                sql_update,
                (
                    fecha_cierre_db,
                    status_db,
                    codigo_db,
                    id_seleccionado
                )
            )


            db.commit()


            st.success(
                "✅ La solicitud fue actualizada correctamente."
            )


        except Exception as e:

            db.rollback()

            st.error(
                "❌ No fue posible actualizar la solicitud."
            )

            st.exception(e)


        finally:

            db.cerrar()


        st.rerun()

else:

    st.info(
        "ℹ️ No existen solicitudes que coincidan "
        "con el criterio de búsqueda."
    )
