"""
Módulo de administración de PODs de PODEX (solo Administrador).

Un POD es un Product Owner (public."PODS": ID_POD, NOMBRE). Las solicitudes
se asocian a un POD por PRODUCT_OWNER = NOMBRE. La asignación de PODs a los
usuarios (public."USUARIOS_PODS") se hace solo desde el módulo de Usuarios;
aquí únicamente se consulta.
"""

import re

import pandas as pd
import streamlit as st

from database import Database
from excel_web import normalizar_product_owner
from usuarios import encabezado_ventana, ficha, seccion

PATRON_ID_POD = re.compile(r"^[A-Z0-9_-]{1,10}$")


# ============================================================
# CONSULTAS
# ============================================================
@st.cache_data(ttl=60, show_spinner=False)
def obtener_pods_detalle():
    """PODs con el número de solicitudes abiertas de cada uno."""
    db = Database()
    try:
        db.conectar()
        db.execute('''
            SELECT
                p."ID_POD",
                p."NOMBRE",
                (SELECT COUNT(*)
                 FROM public."SOLICITUDES" s
                 WHERE UPPER(TRIM(s."PRODUCT_OWNER")) = UPPER(TRIM(p."NOMBRE"))
                   AND s."FECHA_CIERRE" IS NULL
                   AND s."CODIGO_CIERRE" IS NULL) AS "ABIERTAS"
            FROM public."PODS" p
            ORDER BY p."ID_POD"
        ''')
        return pd.DataFrame(
            db.fetchall(),
            columns=["ID_POD", "NOMBRE", "ABIERTAS"]
        )
    finally:
        db.cerrar()


def siguiente_id_pod(ids):
    """Sugiere el siguiente ID con el patrón E<n> (E1, E2, ...)."""
    numeros = [int(m.group(1)) for i in ids if (m := re.fullmatch(r"E(\d+)", str(i)))]
    return f"E{max(numeros, default=0) + 1}"


def notificar(mensaje, tipo="success"):
    """Guarda un mensaje para mostrarlo después del st.rerun() y descarta los
    datos en caché (los PODs afectan la carga y las solicitudes visibles)."""
    st.cache_data.clear()
    st.session_state["mensaje_pods"] = (tipo, mensaje)
    st.rerun()


# ============================================================
# VENTANAS (OVERLAY)
# ============================================================
@st.dialog(" ", width="large")
def ventana_crear_pod(pods_df):

    encabezado_ventana("Nuevo POD")

    with st.form("form_crear_pod"):
        c1, c2 = st.columns([1, 3])
        with c1:
            id_pod = st.text_input(
                "ID del POD",
                value=siguiente_id_pod(pods_df["ID_POD"]),
                max_chars=10,
                help="Identificador corto, por ejemplo E7. Se guarda en MAYÚSCULAS."
            )
        with c2:
            nombre = st.text_input(
                "Product Owner",
                placeholder="Nombre completo tal como aparece en el Excel de solicitudes",
                help="Las solicitudes se asocian al POD cuando su PRODUCT_OWNER coincide con este nombre."
            )

        with st.container(key="acciones_dlg_crear_pod", horizontal=True,
                          horizontal_alignment="right", gap="small"):
            crear = st.form_submit_button("", icon=":material/add:", key="btn_ok_crear_pod",
                                          help="Crear POD")

    if not crear:
        return

    id_pod = (id_pod or "").strip().upper()
    nombre = normalizar_product_owner(nombre)

    if not PATRON_ID_POD.match(id_pod):
        st.error("❌ El ID del POD debe tener entre 1 y 10 caracteres: letras, números, guion o guion bajo.")
        return
    if not nombre:
        st.error("❌ Debe ingresar el nombre del Product Owner.")
        return
    if id_pod in set(pods_df["ID_POD"].str.upper()):
        st.error(f"❌ Ya existe el POD {id_pod}.")
        return
    if nombre in set(pods_df["NOMBRE"].map(normalizar_product_owner)):
        st.error(f"❌ Ya existe un POD para el Product Owner {nombre}.")
        return

    db = Database()
    try:
        db.conectar()
        db.execute(
            'INSERT INTO public."PODS" ("ID_POD","NOMBRE") VALUES (%s,%s)',
            (id_pod, nombre)
        )
        db.commit()
    except Exception as e:
        db.rollback()
        st.error(f"❌ No fue posible crear el POD: {e}")
        return
    finally:
        db.cerrar()

    notificar(
        f"✅ POD {id_pod} · {nombre} creado correctamente. "
        "Asígnelo a los usuarios desde el módulo Usuarios."
    )


@st.dialog(" ", width="large")
def ventana_editar_pod(fila, pods_df):

    encabezado_ventana("Editar POD")
    ficha([
        ("ID del POD", fila["ID_POD"]),
        ("Product Owner actual", fila["NOMBRE"]),
        ("Solicitudes abiertas", int(fila["ABIERTAS"])),
    ])

    with st.form(f"form_editar_pod_{fila['ID_POD']}"):
        nombre = st.text_input("Product Owner", value=fila["NOMBRE"])

        with st.container(key="acciones_dlg_editar_pod", horizontal=True,
                          horizontal_alignment="right", gap="small"):
            guardar = st.form_submit_button("", icon=":material/save:", key="btn_info_editar_pod",
                                            help="Guardar cambios")

    if not guardar:
        return

    nombre = normalizar_product_owner(nombre)

    if not nombre:
        st.error("❌ Debe ingresar el nombre del Product Owner.")
        return

    otros = pods_df[pods_df["ID_POD"] != fila["ID_POD"]]
    if nombre in set(otros["NOMBRE"].map(normalizar_product_owner)):
        st.error(f"❌ Ya existe otro POD para el Product Owner {nombre}.")
        return

    db = Database()
    try:
        db.conectar()
        db.execute(
            'UPDATE public."PODS" SET "NOMBRE" = %s WHERE "ID_POD" = %s',
            (nombre, fila["ID_POD"])
        )
        db.commit()
    except Exception as e:
        db.rollback()
        st.error(f"❌ No fue posible guardar los cambios: {e}")
        return
    finally:
        db.cerrar()

    notificar(f"✅ POD {fila['ID_POD']} actualizado correctamente.")


@st.dialog(" ", width="large")
def ventana_eliminar_pod(fila):

    encabezado_ventana("Eliminar POD")
    ficha([
        ("ID del POD", fila["ID_POD"]),
        ("Product Owner", fila["NOMBRE"]),
        ("Solicitudes abiertas", int(fila["ABIERTAS"])),
    ])

    abiertas = int(fila["ABIERTAS"])
    seccion(
        "¿Está seguro que desea eliminar este POD?",
        "El POD se quitará de los usuarios que lo tienen asignado. Las solicitudes no se borran, "
        "pero ya no se cargarán nuevas solicitudes de este Product Owner y los Operador "
        "dejarán de verlas"
        + (f" (hoy tiene {abiertas} solicitud(es) abierta(s))." if abiertas else ".")
        + " Esta acción no se puede deshacer."
    )

    with st.form(f"form_eliminar_pod_{fila['ID_POD']}"):
        with st.container(key="acciones_dlg_eliminar_pod", horizontal=True,
                          horizontal_alignment="right", gap="small"):
            cancelar = st.form_submit_button("", icon=":material/close:", key="btn_cancel_eliminar_pod",
                                             help="Cancelar")
            confirmar = st.form_submit_button("", icon=":material/delete:", key="btn_danger_eliminar_pod",
                                              help="Sí, eliminar")

    if cancelar:
        st.rerun()
    if not confirmar:
        return

    db = Database()
    try:
        db.conectar()
        db.execute('DELETE FROM public."USUARIOS_PODS" WHERE "ID_POD" = %s', (fila["ID_POD"],))
        db.execute('DELETE FROM public."PODS" WHERE "ID_POD" = %s', (fila["ID_POD"],))
        db.commit()
    except Exception as e:
        db.rollback()
        st.error(f"❌ No fue posible eliminar el POD: {e}")
        return
    finally:
        db.cerrar()

    notificar(f"✅ POD {fila['ID_POD']} eliminado correctamente.")


# ============================================================
# PÁGINA PRINCIPAL DEL MÓDULO
# ============================================================
def mostrar_modulo_pods():

    mensaje = st.session_state.pop("mensaje_pods", None)
    if mensaje:
        tipo, texto_mensaje = mensaje
        (st.warning if tipo == "warning" else st.success)(texto_mensaje)

    try:
        pods = obtener_pods_detalle()
    except Exception as e:
        st.error("❌ No fue posible consultar los PODs.")
        st.exception(e)
        return

    texto = st.text_input(
        "🔎 Buscar POD",
        placeholder="Digite ID o Product Owner..."
    )

    todos = pods
    if texto:
        texto_busqueda = texto.lower()
        mascara = pods.apply(
            lambda f: texto_busqueda in " ".join(
                [str(f["ID_POD"]), str(f["NOMBRE"])]
            ).lower(),
            axis=1
        )
        pods = pods[mascara]

    pods = pods.reset_index(drop=True)

    seleccion = st.session_state.get("tabla_pods")
    filas = seleccion.selection.rows if seleccion else []
    fila = pods.iloc[filas[0]] if filas and filas[0] < len(pods) else None

    c_sel, c_acciones = st.columns([3, 1], vertical_alignment="center")

    with c_sel:
        if fila is not None:
            st.markdown(f"**POD seleccionado:** {fila['ID_POD']} · {fila['NOMBRE']}")
        else:
            st.caption("☝️ Seleccione un POD en la tabla para administrarlo.")

    with c_acciones:
        with st.container(key="acciones_pods", horizontal=True,
                          horizontal_alignment="right", gap="small"):
            if st.button("", icon=":material/add:", key="btn_pod_nuevo", help="Nuevo POD"):
                ventana_crear_pod(todos)
            if st.button("", icon=":material/edit:", key="btn_pod_editar",
                         disabled=fila is None, help="Editar POD"):
                ventana_editar_pod(fila, todos)
            if st.button("", icon=":material/delete:", key="btn_pod_eliminar",
                         disabled=fila is None, help="Eliminar POD"):
                ventana_eliminar_pod(fila)

    if pods.empty:
        st.info("ℹ️ No existen PODs que coincidan con el criterio de búsqueda.")
        return

    tabla = pd.DataFrame({
        "ID_POD": pods["ID_POD"],
        "PRODUCT_OWNER": pods["NOMBRE"],
        "SOLICITUDES_ABIERTAS": pods["ABIERTAS"].astype(int),
    })

    st.markdown('<div style="height:14px"></div>', unsafe_allow_html=True)

    st.dataframe(
        tabla,
        key="tabla_pods",
        on_select="rerun",
        selection_mode="single-row",
        hide_index=True,
        width="stretch",
        height=min(38 + 35 * len(tabla), 640),
        column_config={
            "ID_POD": st.column_config.TextColumn("ID_POD", width="small"),
            "PRODUCT_OWNER": st.column_config.TextColumn("PRODUCT_OWNER", width="large"),
            "SOLICITUDES_ABIERTAS": st.column_config.NumberColumn("SOLICITUDES_ABIERTAS", width="small"),
        },
    )
