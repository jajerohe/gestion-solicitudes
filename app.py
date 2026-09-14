import streamlit as st
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo

from database import Database
from excel_web import analizar_excel, cargar_excel

st.set_page_config(
    page_title="SIGPI",
    page_icon="📋",
    layout="wide"
)

# ============================================================
# ENCABEZADO: LOGO A LA IZQUIERDA + CARGA DE EXCEL A LA DERECHA
# ============================================================
col_logo, col_carga = st.columns([1.25, 1], gap="large")

with col_logo:
    st.image("Logo_SIGPI.png", width=500)

with col_carga:
    st.markdown(
        '<div style="margin-top: 28px;">'
        '<h3 style="margin-bottom: 8px; color: #24344D;">'
        '📤 Cargar solicitudes desde Excel'
        '</h3>'
        '</div>',
        unsafe_allow_html=True
    )

    archivo_excel = st.file_uploader(
        "Seleccione un archivo Excel",
        type=["xlsx"],
        help="Se procesarán únicamente DETALLE_GENERAL y DETALLE_FUNCIONALES."
    )

def obtener_solicitudes():
    db = Database()
    try:
        db.conectar()
        sql = '''
            SELECT "ID_SOLICITUD","TITULO","FECHA_APERTURA",
                   "SUBSERVICIO_AFECTADO","PRODUCT_OWNER","STATUS",
                   "ASIGNADO_A","NOMBRE_ASIGNATARIO","CORREO_ASIGNATARIO",
                   "FECHA_CIERRE","CODIGO_CIERRE"
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
    # Todo queda dentro del mismo contenedor visual.
    # Estado y Código de cierre permanecen en la primera fila.
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

        # Cuando no hay código de cierre, los campos se muestran vacíos
        # y deshabilitados. Al seleccionar un código, se habilitan.
        if codigo_seleccionado:
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
        else:
            fecha_default = None
            hora_default = ""

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

        actualizar = st.button(
            "🔄 Actualizar Solicitud",
            key=f"btn_actualizar_{id_solicitud}",
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
                UPDATE public."Solicitudes"
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

            st.success(
                f"✅ Solicitud actualizada. Fecha/hora guardada: {fecha_cierre_guardada:%Y-%m-%d %H:%M:%S}"
            )
            st.caption(
                f"PostgreSQL devolvió exactamente: {fecha_cierre_guardada:%Y-%m-%d %H:%M:%S}"
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

/* Botón "Actualizar Solicitud": mantener la forma rectangular
   redondeada de la figura 2, sin afectar los botones +. */
div[data-testid="stForm"] div[data-testid="stButton"] > button {
    min-height: 26px !important;
    height: 26px !important;
    width: auto !important;
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
    "VER GESTIÓN",
    "ACTUALIZAR"
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
            "➕",
            key=f"gestion_{sid}",
            help=f"Adicionar gestión a {sid}",
            use_container_width=True
        ):
            ventana_gestion(sid)

    # Botón para ver las gestiones registradas
    with cols[10]:
        if st.button(
            "👁️",
            key=f"ver_gestion_{sid}",
            help=f"Ver gestión de {sid}",
            use_container_width=True
        ):
            ventana_ver_gestion(sid)

    # Botón para actualizar solicitud
    with cols[11]:
        if st.button(
            "➕",
            key=f"actualizar_{sid}",
            help=f"Actualizar solicitud {sid}",
            use_container_width=True
        ):
            ventana_actualizar(sid)


if df_filtrado.empty:
    st.info(
        "ℹ️ No existen solicitudes que coincidan con el criterio de búsqueda."
    )
