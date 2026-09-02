import streamlit as st
import pandas as pd

from database import Database
from excel_web import analizar_excel, cargar_excel

st.set_page_config(
    page_title="Gestión de Solicitudes - ECP",
    page_icon="📋",
    layout="wide"
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
            WHERE "STATUS" NOT IN ('RESOLVED', 'COMPLETADO')
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

st.title("📋 Gestión de Solicitudes - ECP")

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
                resultado = cargar_excel(archivo_excel, db)
            db.commit()

            st.success("✅ Archivo cargado correctamente.")
            a, b, c, d = st.columns(4)
            a.metric("Generales", resultado["generales"])
            b.metric("Funcionales", resultado["funcionales"])
            c.metric("Duplicados", resultado["duplicados"])
            d.metric("Errores", resultado["errores"])
            st.rerun()
        except Exception as e:
            db.rollback()
            st.error("❌ No fue posible cargar el archivo.")
            st.exception(e)
        finally:
            db.cerrar()

try:
    df = obtener_solicitudes()
except Exception as e:
    st.error("❌ No fue posible consultar las solicitudes.")
    st.exception(e)
    st.stop()

st.success(f"✅ Conexión con Supabase exitosa — {len(df)} solicitud(es) encontrada(s)")

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
st.dataframe(df_filtrado, use_container_width=True, hide_index=True)

if not df_filtrado.empty:
    st.divider()
    st.subheader("📌 Seleccionar solicitud")
    id_seleccionado = st.selectbox("Solicitud", df_filtrado["ID_SOLICITUD"].tolist())
    solicitud = df_filtrado[
        df_filtrado["ID_SOLICITUD"] == id_seleccionado
    ].iloc[0]

    st.subheader("📄 Información de la solicitud")
    a, b, c = st.columns(3)
    with a:
        st.markdown(f"**ID_SOLICITUD**  \n{solicitud['ID_SOLICITUD']}")
        st.markdown(f"**TÍTULO**  \n{solicitud['TITULO']}")
        st.markdown(f"**SUBSERVICIO AFECTADO**  \n{solicitud['SUBSERVICIO_AFECTADO']}")
    with b:
        st.markdown(f"**PRODUCT OWNER**  \n{solicitud['PRODUCT_OWNER']}")
        st.markdown(f"**ASIGNADO A**  \n{solicitud['ASIGNADO_A']}")
        st.markdown(f"**NOMBRE ASIGNATARIO**  \n{solicitud['NOMBRE_ASIGNATARIO']}")
    with c:
        st.markdown(f"**CORREO ASIGNATARIO**  \n{solicitud['CORREO_ASIGNATARIO']}")
        st.markdown(f"**ESTADO**  \n{solicitud['STATUS']}")
        st.markdown(f"**FECHA APERTURA**  \n{solicitud['FECHA_APERTURA']}")

    st.divider()
    st.subheader("📜 Historial de gestiones")
    try:
        gestiones = obtener_gestiones(id_seleccionado)
        if not gestiones.empty:
            st.dataframe(gestiones, use_container_width=True, hide_index=True)
        else:
            st.info("ℹ️ No existen gestiones registradas para esta solicitud.")
    except Exception as e:
        st.error("❌ Error consultando el historial.")
        st.exception(e)

    st.divider()
    st.subheader("📝 Nueva gestión")
    with st.form("form_gestion"):
        # Selector visual de fecha y hora.
        # La fecha se selecciona mediante calendario y la hora mediante
        # un control independiente de hora/minutos/segundos.
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
                "Hora de gestión",
                value=ahora.time().replace(microsecond=0),
                step=1
            )

        observacion = st.text_area(
            "Observación",
            placeholder="Digite la observación de la gestión...",
            height=150
        )
        guardar = st.form_submit_button("💾 Guardar Gestión")

    if guardar:
        observacion = observacion.strip()
        if not observacion:
            st.warning("⚠️ Debe ingresar una observación.")
            st.stop()

        try:
            # Combinar la fecha seleccionada en el calendario con la hora.
            fecha = pd.Timestamp.combine(
                fecha_seleccionada,
                hora_seleccionada
            ).to_pydatetime()
        except Exception:
            st.error("❌ La fecha y hora no tienen un formato válido.")
            st.stop()

        db = Database()
        try:
            db.conectar()
            db.execute('''
                SELECT 1 FROM public."Gestiones"
                WHERE "ID_SOLICITUD" = %s
                  AND "OBSERVACION" = %s
                LIMIT 1
            ''', (id_seleccionado, observacion))

            if db.fetchone():
                st.warning("⚠️ Esta observación ya existe para esta solicitud.")
                st.stop()

            db.execute('''
                INSERT INTO public."Gestiones"
                ("FECHA_GESTION","ID_SOLICITUD","OBSERVACION")
                VALUES (%s,%s,%s)
            ''', (fecha, id_seleccionado, observacion))
            db.commit()
            st.success("✅ Gestión guardada correctamente.")
        except Exception as e:
            db.rollback()
            st.error("❌ No fue posible guardar la gestión.")
            st.exception(e)
        finally:
            db.cerrar()
        st.rerun()

    st.divider()
    st.subheader("⚙️ Actualizar solicitud")

    estados = [
        "Cancelled","Completado","En curso","Fulfilled","In Progress",
        "Pendiente de cliente","Pendiente de proveedor","Resuelto",
        "Suspendido","Trabajo en curso"
    ]
    codigos = [
        "Cancelado por incumplimiento de politicas",
        "Cancelado por el usuario",
        "Resuelto por soporte tecnico"
    ]

    status_opciones = [""] + estados
    codigo_opciones = [""] + codigos
    status_actual = solicitud["STATUS"]
    codigo_actual = solicitud["CODIGO_CIERRE"]
    fecha_actual = solicitud["FECHA_CIERRE"]

    i_status = status_opciones.index(status_actual) if status_actual in status_opciones else 0
    i_codigo = codigo_opciones.index(codigo_actual) if codigo_actual in codigo_opciones else 0

    fecha_texto = (
        pd.to_datetime(fecha_actual).strftime("%Y-%m-%d %H:%M:%S")
        if pd.notna(fecha_actual) else ""
    )

    # Valores iniciales para el selector de fecha/hora.
    if fecha_texto:
        fecha_cierre_inicial = pd.to_datetime(fecha_texto)
    else:
        fecha_cierre_inicial = pd.Timestamp.now()

    with st.form("form_actualizar"):
        a, b = st.columns(2)
        with a:
            nuevo_status = st.selectbox("Estado", status_opciones, index=i_status)
        with b:
            nuevo_codigo = st.selectbox("Código de cierre", codigo_opciones, index=i_codigo)

        # Mismo modelo utilizado en "Nueva gestión":
        # calendario para la fecha + selector para hora, minutos y segundos.
        c_fecha, c_hora = st.columns(2)

        with c_fecha:
            fecha_cierre_fecha = st.date_input(
                "Fecha de cierre",
                value=fecha_cierre_inicial.date(),
                format="DD/MM/YYYY"
            )

        with c_hora:
            fecha_cierre_hora = st.time_input(
                "Hora de cierre",
                value=fecha_cierre_inicial.time().replace(microsecond=0),
                step=1
            )

        actualizar = st.form_submit_button("🔄 Actualizar Solicitud")

    if actualizar:
        try:
            fecha_db = pd.Timestamp.combine(
                fecha_cierre_fecha,
                fecha_cierre_hora
            ).to_pydatetime()
        except Exception:
            st.warning("⚠️ La fecha y hora de cierre no tienen un formato válido.")
            st.stop()

        db = Database()
        try:
            db.conectar()
            db.execute('''
                UPDATE public."Solicitudes"
                SET "FECHA_CIERRE" = %s,
                    "STATUS" = %s,
                    "CODIGO_CIERRE" = %s
                WHERE "ID_SOLICITUD" = %s
            ''', (
                fecha_db,
                nuevo_status or None,
                nuevo_codigo or None,
                id_seleccionado
            ))
            db.commit()
            st.success("✅ La solicitud fue actualizada correctamente.")
        except Exception as e:
            db.rollback()
            st.error("❌ No fue posible actualizar la solicitud.")
            st.exception(e)
        finally:
            db.cerrar()
        st.rerun()
else:
    st.info("ℹ️ No existen solicitudes que coincidan con el criterio de búsqueda.")
