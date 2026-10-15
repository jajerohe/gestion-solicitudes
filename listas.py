"""
Módulo de Listas de correo de PODEX (solo Administrador).

Cada lista se asocia a un envío del sistema (ENVIOS) y tiene destinatarios
Para, CC o CCO: usuarios de PODEX, correos externos o el grupo especial
OPERADORES ("Operadores activos de PODEX"), que se resuelve en cada envío
con los usuarios activos de perfil Operador que tienen correo.

Tablas: public."LISTAS_CORREO" y public."LISTAS_CORREO_DESTINATARIOS".
"""

import re

import pandas as pd
import streamlit as st

from database import Database
from usuarios import encabezado_ventana, ficha, obtener_usuarios, seccion

# Envíos del sistema que usan listas de correo.
ENVIOS = {
    "BACKLOG": "📥 Backlog después de cada carga de Excel",
    "SEGUIMIENTO": "✉️ Seguimiento de solicitudes abiertas",
}
TIPOS = ["PARA", "CC", "CCO"]
OPERADORES = "@OPERADORES"
NOMBRE_OPERADORES = "Operadores activos de PODEX"
PATRON_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# ============================================================
# CONSULTAS
# ============================================================
@st.cache_data(ttl=60, show_spinner=False)
def obtener_listas():
    """Listas con sus destinatarios: (listas_df, destinatarios_df)."""
    db = Database()
    try:
        db.conectar()
        db.execute('''
            SELECT "ID_LISTA", "NOMBRE", "ENVIO", "ACTIVA"
            FROM public."LISTAS_CORREO"
            ORDER BY "ENVIO", "NOMBRE"
        ''')
        listas = pd.DataFrame(db.fetchall(), columns=["ID_LISTA", "NOMBRE", "ENVIO", "ACTIVA"])
        db.execute('''
            SELECT "ID_LISTA", "CORREO", "NOMBRE", "TIPO"
            FROM public."LISTAS_CORREO_DESTINATARIOS"
            ORDER BY "ID_LISTA", "TIPO" DESC, "CORREO"
        ''')
        destinatarios = pd.DataFrame(db.fetchall(), columns=["ID_LISTA", "CORREO", "NOMBRE", "TIPO"])
    finally:
        db.cerrar()
    return listas, destinatarios


def listas_activas(envio):
    """Listas activas de un envío: DataFrame con ID_LISTA y NOMBRE."""
    listas, _ = obtener_listas()
    return listas[(listas["ENVIO"] == envio) & (listas["ACTIVA"] == True)].reset_index(drop=True)  # noqa: E712


def correos_operadores():
    """Correos de los usuarios activos con perfil Operador."""
    usuarios = obtener_usuarios()
    return usuarios.loc[
        (usuarios["ACTIVO"] == True)  # noqa: E712
        & usuarios["CORREO"].notna()
        & (usuarios["PERFIL"].astype(str).str.strip().str.upper() == "OPERADOR"),
        "CORREO"
    ].tolist()


def resolver_destinatarios(id_lista):
    """{"PARA": [...], "CC": [...], "CCO": [...]} con los correos de la lista.

    El grupo OPERADORES se reemplaza por los correos de los Operadores
    activos. Un correo aparece una sola vez, en el primer tipo en que esté
    (PARA, luego CC, luego CCO).
    """
    _, destinatarios = obtener_listas()
    filas = destinatarios[destinatarios["ID_LISTA"] == id_lista]
    resultado, vistos = {t: [] for t in TIPOS}, set()
    for tipo in TIPOS:
        for correo in filas.loc[filas["TIPO"] == tipo, "CORREO"]:
            correos = correos_operadores() if correo == OPERADORES else [correo]
            for c in correos:
                c = str(c).strip().lower()
                if c and c not in vistos:
                    vistos.add(c)
                    resultado[tipo].append(c)
    return resultado


def notificar(mensaje, tipo="success"):
    st.cache_data.clear()
    st.session_state["mensaje_listas"] = (tipo, mensaje)
    st.rerun()


# ============================================================
# EDITOR DE DESTINATARIOS (crear y editar)
# ============================================================
def _preparar_editor(destinatarios):
    """Deja en sesión los destinatarios que mostrará la ventana de edición."""
    operadores = destinatarios[destinatarios["CORREO"] == OPERADORES]
    st.session_state["lista_operadores"] = operadores["TIPO"].iloc[0] if len(operadores) else "No incluir"
    st.session_state["lista_destinatarios"] = (
        destinatarios[destinatarios["CORREO"] != OPERADORES][["CORREO", "NOMBRE", "TIPO"]]
        .reset_index(drop=True)
    )
    st.session_state["lista_editor_version"] = st.session_state.get("lista_editor_version", 0) + 1


def _editor_destinatarios():
    """Controles para armar los destinatarios. Devuelve (operadores, DataFrame)."""
    seccion("Destinatarios",
            "Para = destinatario principal · CC = con copia · CCO = copia oculta (los demás no lo ven).")

    operadores = st.selectbox(
        f"👥 {NOMBRE_OPERADORES}",
        ["No incluir", *TIPOS],
        key="lista_operadores",
        help="Grupo que se actualiza solo: en cada envío incluye a los usuarios activos con perfil Operador.",
    )

    try:
        usuarios = obtener_usuarios()
        usuarios = usuarios[usuarios["CORREO"].notna()]
    except Exception:
        usuarios = pd.DataFrame(columns=["USUARIO", "NOMBRE", "CORREO"])

    c1, c2, c3 = st.columns([3, 1, 0.5], vertical_alignment="bottom")
    with c1:
        elegidos = st.multiselect(
            "Agregar usuarios de PODEX",
            usuarios["USUARIO"].tolist(),
            format_func=lambda u: (lambda f: f"{f['NOMBRE']} · {f['CORREO']}")(
                usuarios[usuarios["USUARIO"] == u].iloc[0]),
            key=f"lista_usuarios_{st.session_state.get('lista_editor_version', 0)}",
            placeholder="Seleccione uno o varios usuarios",
        )
    with c2:
        tipo_usuarios = st.selectbox("Tipo", TIPOS, index=1, key="lista_tipo_usuarios")
    version = st.session_state.get("lista_editor_version", 0)
    with c3:
        with st.container(key="acciones_lista_agregar"):
            agregar = st.button("", icon=":material/person_add:", key="btn_ok_lista_agregar",
                                disabled=not elegidos, help="Agregar a la lista")

    editado = st.data_editor(
        st.session_state["lista_destinatarios"],
        key=f"lista_editor_{version}",
        num_rows="dynamic",
        hide_index=True,
        width="stretch",
        column_config={
            "CORREO": st.column_config.TextColumn("CORREO", required=True, width="large"),
            "NOMBRE": st.column_config.TextColumn("NOMBRE", width="medium"),
            "TIPO": st.column_config.SelectboxColumn("TIPO", options=TIPOS, required=True,
                                                     default="PARA", width="small"),
        },
    )
    st.caption("Escriba correos externos en la última fila de la tabla. Para quitar uno, "
               "selecciónelo y use el ícono de la papelera de la tabla.")

    if agregar:
        nuevos = usuarios[usuarios["USUARIO"].isin(elegidos)]
        filas = pd.DataFrame({"CORREO": nuevos["CORREO"], "NOMBRE": nuevos["NOMBRE"], "TIPO": tipo_usuarios})
        existentes = set(editado["CORREO"].dropna().str.strip().str.lower())
        filas = filas[~filas["CORREO"].str.strip().str.lower().isin(existentes)]
        st.session_state["lista_destinatarios"] = pd.concat([editado, filas], ignore_index=True)
        st.session_state["lista_editor_version"] = version + 1
        st.rerun(scope="fragment")

    return operadores, editado


def _validar(nombre, destinatarios, operadores, otros_nombres):
    """Devuelve (error, filas_limpias)."""
    nombre = " ".join((nombre or "").split())
    if not nombre:
        return "Debe ingresar el nombre de la lista.", None
    if nombre.upper() in {n.upper() for n in otros_nombres}:
        return f"Ya existe una lista llamada {nombre}.", None

    filas, vistos = [], set()
    for _, f in destinatarios.iterrows():
        correo = str(f.get("CORREO") or "").strip().lower()
        if not correo:
            continue
        if not PATRON_CORREO.match(correo):
            return f"El correo {correo} no es válido.", None
        if correo in vistos:
            return f"El correo {correo} está repetido.", None
        tipo = f.get("TIPO") if f.get("TIPO") in TIPOS else "PARA"
        vistos.add(correo)
        nombre_dest = " ".join(str(f.get("NOMBRE") or "").split()) or None
        filas.append((correo, nombre_dest, tipo))
    if operadores in TIPOS:
        filas.append((OPERADORES, NOMBRE_OPERADORES, operadores))
    if not filas:
        return "Agregue al menos un destinatario.", None
    return None, (nombre, filas)


def _guardar(db, id_lista, filas):
    db.execute('DELETE FROM public."LISTAS_CORREO_DESTINATARIOS" WHERE "ID_LISTA" = %s', (id_lista,))
    for correo, nombre, tipo in filas:
        db.execute(
            'INSERT INTO public."LISTAS_CORREO_DESTINATARIOS" ("ID_LISTA","CORREO","NOMBRE","TIPO") '
            'VALUES (%s,%s,%s,%s)',
            (id_lista, correo, nombre, tipo)
        )


# ============================================================
# VENTANAS (OVERLAY)
# ============================================================
@st.dialog(" ", width="large")
def ventana_crear_lista(listas, usuario_actual):
    encabezado_ventana("Nueva lista de correo")

    c1, c2 = st.columns(2)
    with c1:
        nombre = st.text_input("Nombre de la lista", placeholder="Ej: Seguimiento Florinda", max_chars=100)
    with c2:
        envio = st.selectbox("Envío del sistema", list(ENVIOS), format_func=ENVIOS.get)

    operadores, destinatarios = _editor_destinatarios()

    with st.container(key="acciones_dlg_crear_lista", horizontal=True,
                      horizontal_alignment="right", gap="small"):
        crear = st.button("", icon=":material/add:", key="btn_ok_lista_crear", help="Crear lista")
    if not crear:
        return

    error, datos = _validar(nombre, destinatarios, operadores, listas["NOMBRE"].tolist())
    if error:
        st.error(f"❌ {error}")
        return
    nombre, filas = datos

    db = Database()
    try:
        db.conectar()
        db.execute(
            'INSERT INTO public."LISTAS_CORREO" ("NOMBRE","ENVIO","USUARIO_REGISTRO") '
            'VALUES (%s,%s,%s) RETURNING "ID_LISTA"',
            (nombre, envio, usuario_actual)
        )
        _guardar(db, db.fetchone()[0], filas)
        db.commit()
    except Exception as e:
        db.rollback()
        st.error(f"❌ No fue posible crear la lista: {e}")
        return
    finally:
        db.cerrar()

    notificar(f"✅ Lista {nombre} creada con {len(filas)} destinatario(s).")


@st.dialog(" ", width="large")
def ventana_editar_lista(fila, listas):
    encabezado_ventana("Editar lista de correo")

    c1, c2 = st.columns(2)
    with c1:
        nombre = st.text_input("Nombre de la lista", value=fila["NOMBRE"], max_chars=100)
    with c2:
        envios = list(ENVIOS)
        envio = st.selectbox("Envío del sistema", envios, format_func=ENVIOS.get,
                             index=envios.index(fila["ENVIO"]) if fila["ENVIO"] in envios else 0)

    operadores, destinatarios = _editor_destinatarios()

    with st.container(key="acciones_dlg_editar_lista", horizontal=True,
                      horizontal_alignment="right", gap="small"):
        guardar = st.button("", icon=":material/save:", key="btn_info_lista_guardar", help="Guardar cambios")
    if not guardar:
        return

    otros = listas.loc[listas["ID_LISTA"] != fila["ID_LISTA"], "NOMBRE"].tolist()
    error, datos = _validar(nombre, destinatarios, operadores, otros)
    if error:
        st.error(f"❌ {error}")
        return
    nombre, filas = datos

    db = Database()
    try:
        db.conectar()
        db.execute('UPDATE public."LISTAS_CORREO" SET "NOMBRE" = %s, "ENVIO" = %s WHERE "ID_LISTA" = %s',
                   (nombre, envio, int(fila["ID_LISTA"])))
        _guardar(db, int(fila["ID_LISTA"]), filas)
        db.commit()
    except Exception as e:
        db.rollback()
        st.error(f"❌ No fue posible guardar los cambios: {e}")
        return
    finally:
        db.cerrar()

    notificar(f"✅ Lista {nombre} actualizada.")


@st.dialog(" ", width="large")
def ventana_estado_lista(fila):
    activa = bool(fila["ACTIVA"])
    encabezado_ventana("Desactivar lista" if activa else "Activar lista")
    ficha([("Lista", fila["NOMBRE"]), ("Envío", ENVIOS.get(fila["ENVIO"], fila["ENVIO"])),
           ("Estado", "ACTIVA" if activa else "INACTIVA")])
    seccion(
        "¿Está seguro que desea desactivar esta lista?" if activa else "¿Está seguro que desea activar esta lista?",
        "Una lista inactiva no aparece al enviar correos; sus destinatarios se conservan."
        if activa else "La lista volverá a aparecer al enviar correos."
    )
    with st.container(key="acciones_dlg_estado_lista", horizontal=True,
                      horizontal_alignment="right", gap="small"):
        cancelar = st.button("", icon=":material/close:", key="btn_cancel_lista_estado", help="Cancelar")
        confirmar = st.button("", icon=":material/power_settings_new:", key="btn_warn_lista_estado",
                              help="Sí, desactivar" if activa else "Sí, activar")
    if cancelar:
        st.rerun()
    if not confirmar:
        return

    db = Database()
    try:
        db.conectar()
        db.execute('UPDATE public."LISTAS_CORREO" SET "ACTIVA" = %s WHERE "ID_LISTA" = %s',
                   (not activa, int(fila["ID_LISTA"])))
        db.commit()
    except Exception as e:
        db.rollback()
        st.error(f"❌ No fue posible cambiar el estado: {e}")
        return
    finally:
        db.cerrar()

    notificar(f"✅ Lista {fila['NOMBRE']} {'desactivada' if activa else 'activada'}.")


@st.dialog(" ", width="large")
def ventana_eliminar_lista(fila):
    encabezado_ventana("Eliminar lista")
    ficha([("Lista", fila["NOMBRE"]), ("Envío", ENVIOS.get(fila["ENVIO"], fila["ENVIO"])),
           ("Destinatarios", int(fila["TOTAL"]))])
    seccion("¿Está seguro que desea eliminar esta lista?",
            "Se eliminan la lista y sus destinatarios. Esta acción no se puede deshacer; "
            "si solo quiere dejar de usarla, desactívela.")
    with st.container(key="acciones_dlg_eliminar_lista", horizontal=True,
                      horizontal_alignment="right", gap="small"):
        cancelar = st.button("", icon=":material/close:", key="btn_cancel_lista_eliminar", help="Cancelar")
        confirmar = st.button("", icon=":material/delete:", key="btn_danger_lista_eliminar", help="Sí, eliminar")
    if cancelar:
        st.rerun()
    if not confirmar:
        return

    db = Database()
    try:
        db.conectar()
        db.execute('DELETE FROM public."LISTAS_CORREO" WHERE "ID_LISTA" = %s', (int(fila["ID_LISTA"]),))
        db.commit()
    except Exception as e:
        db.rollback()
        st.error(f"❌ No fue posible eliminar la lista: {e}")
        return
    finally:
        db.cerrar()

    notificar(f"✅ Lista {fila['NOMBRE']} eliminada.")


# ============================================================
# PÁGINA PRINCIPAL DEL MÓDULO
# ============================================================
def mostrar_modulo_listas(usuario_actual):

    mensaje = st.session_state.pop("mensaje_listas", None)
    if mensaje:
        tipo, texto_mensaje = mensaje
        (st.warning if tipo == "warning" else st.success)(texto_mensaje)

    try:
        listas, destinatarios = obtener_listas()
    except Exception as e:
        st.error("❌ No fue posible consultar las listas de correo.")
        st.exception(e)
        return

    conteo = destinatarios.groupby(["ID_LISTA", "TIPO"]).size().unstack(fill_value=0)
    for tipo in TIPOS:
        listas[tipo] = listas["ID_LISTA"].map(conteo[tipo] if tipo in conteo else {}).fillna(0).astype(int)
    listas["TOTAL"] = listas[TIPOS].sum(axis=1)
    correos_por_lista = destinatarios.groupby("ID_LISTA")["CORREO"].apply(" ".join)

    texto = st.text_input("🔎 Buscar lista", placeholder="Digite nombre, envío o correo...")
    todas = listas
    if texto:
        t = texto.lower()
        listas = listas[listas.apply(
            lambda f: t in " ".join([str(f["NOMBRE"]), ENVIOS.get(f["ENVIO"], ""),
                                     str(correos_por_lista.get(f["ID_LISTA"], ""))]).lower(),
            axis=1
        )]
    listas = listas.reset_index(drop=True)

    seleccion = st.session_state.get("tabla_listas")
    filas = seleccion.selection.rows if seleccion else []
    fila = listas.iloc[filas[0]] if filas and filas[0] < len(listas) else None

    c_sel, c_acciones = st.columns([3, 1], vertical_alignment="center")
    with c_sel:
        if fila is not None:
            st.markdown(f"**Lista seleccionada:** {fila['NOMBRE']}")
        else:
            st.caption("☝️ Seleccione una lista en la tabla para administrarla.")
    with c_acciones:
        with st.container(key="acciones_listas", horizontal=True,
                          horizontal_alignment="right", gap="small"):
            if st.button("", icon=":material/add:", key="btn_lista_nueva", help="Nueva lista"):
                _preparar_editor(destinatarios.iloc[0:0])
                ventana_crear_lista(todas, usuario_actual)
            if st.button("", icon=":material/edit:", key="btn_lista_editar",
                         disabled=fila is None, help="Editar lista y destinatarios"):
                _preparar_editor(destinatarios[destinatarios["ID_LISTA"] == fila["ID_LISTA"]])
                ventana_editar_lista(fila, todas)
            if st.button("", icon=":material/power_settings_new:", key="btn_lista_estado",
                         disabled=fila is None, help="Activar / desactivar"):
                ventana_estado_lista(fila)
            if st.button("", icon=":material/delete:", key="btn_lista_eliminar",
                         disabled=fila is None, help="Eliminar lista"):
                ventana_eliminar_lista(fila)

    if listas.empty:
        st.info("ℹ️ No existen listas que coincidan con el criterio de búsqueda.")
        return

    st.markdown('<div style="height:14px"></div>', unsafe_allow_html=True)
    tabla = pd.DataFrame({
        "LISTA": listas["NOMBRE"],
        "ENVÍO DEL SISTEMA": listas["ENVIO"].map(lambda e: ENVIOS.get(e, e)),
        "PARA": listas["PARA"], "CC": listas["CC"], "CCO": listas["CCO"],
        "ESTADO": listas["ACTIVA"].map(lambda a: "ACTIVA" if a else "INACTIVA"),
    })
    st.dataframe(
        tabla,
        key="tabla_listas",
        on_select="rerun",
        selection_mode="single-row",
        hide_index=True,
        width="stretch",
        height=min(38 + 35 * len(tabla), 640),
        column_config={
            "LISTA": st.column_config.TextColumn("LISTA", width="medium"),
            "ENVÍO DEL SISTEMA": st.column_config.TextColumn("ENVÍO DEL SISTEMA", width="large"),
            "PARA": st.column_config.NumberColumn("PARA", width="small"),
            "CC": st.column_config.NumberColumn("CC", width="small"),
            "CCO": st.column_config.NumberColumn("CCO", width="small"),
            "ESTADO": st.column_config.TextColumn("ESTADO", width="small"),
        },
    )
    st.caption(f"👥 «{NOMBRE_OPERADORES}» cuenta como un destinatario; en cada envío incluye a todos "
               "los usuarios activos con perfil Operador.")
