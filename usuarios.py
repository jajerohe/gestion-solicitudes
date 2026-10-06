"""
Módulo de creación y administración de usuarios de PODEX (solo Administrador).

Cada usuario existe en dos lugares:
  - Supabase Auth: correo, contraseña y estado (activo / desactivado).
  - public."USUARIOS" + public."USUARIOS_PODS": usuario, nombre, perfil y PODs.

Las operaciones sobre Supabase Auth requieren la llave service_role del
proyecto en los secretos de Streamlit:

    [supabase]
    url = "..."
    key = "..."
    service_role_key = "..."
"""

import re

import pandas as pd
import streamlit as st
from supabase import create_client, Client

from database import Database

# Duración usada para desactivar una cuenta en Supabase Auth (~100 años).
DURACION_DESACTIVACION = "876000h"
LONGITUD_MINIMA_CONTRASENA = 8
PATRON_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PATRON_USUARIO = re.compile(r"^[A-Z0-9_.-]{3,30}$")


# ============================================================
# CLIENTE ADMINISTRADOR DE SUPABASE AUTH
# ============================================================
@st.cache_resource
def obtener_cliente_admin() -> Client | None:
    """Cliente de Supabase con la llave service_role, o None si no está configurada."""
    try:
        service_key = st.secrets["supabase"]["service_role_key"]
    except (KeyError, FileNotFoundError):
        return None
    return create_client(st.secrets["supabase"]["url"], service_key)


def cliente_admin_requerido() -> Client:
    cliente = obtener_cliente_admin()
    if cliente is None:
        raise RuntimeError(
            "Falta configurar supabase.service_role_key en los secretos de la aplicación."
        )
    return cliente


# ============================================================
# CONSULTAS
# ============================================================
def obtener_perfiles():
    db = Database()
    try:
        db.conectar()
        db.execute('SELECT "PERFIL" FROM public."PERFILES" ORDER BY "PERFIL"')
        return [fila[0] for fila in db.fetchall()]
    finally:
        db.cerrar()


def obtener_pods():
    db = Database()
    try:
        db.conectar()
        db.execute('SELECT "ID_POD","NOMBRE" FROM public."PODS" ORDER BY "ID_POD"')
        return pd.DataFrame(db.fetchall(), columns=["ID_POD", "NOMBRE"])
    finally:
        db.cerrar()


def obtener_usuarios():
    """Usuarios de PODEX con sus PODs, completados con correo y estado de Supabase Auth."""
    db = Database()
    try:
        db.conectar()
        db.execute('''
            SELECT
                u."USUARIO",
                u."NOMBRE",
                u."PERFIL",
                u."AUTH_USER_ID",
                COALESCE(
                    ARRAY_AGG(up."ID_POD" ORDER BY up."ID_POD")
                        FILTER (WHERE up."ID_POD" IS NOT NULL),
                    ARRAY[]::varchar[]
                ) AS "PODS"
            FROM public."USUARIOS" u
            LEFT JOIN public."USUARIOS_PODS" up
                ON up."USUARIO" = u."USUARIO"
            GROUP BY u."USUARIO", u."NOMBRE", u."PERFIL", u."AUTH_USER_ID"
            ORDER BY u."USUARIO"
        ''')
        df = pd.DataFrame(
            db.fetchall(),
            columns=["USUARIO", "NOMBRE", "PERFIL", "AUTH_USER_ID", "PODS"]
        )
    finally:
        db.cerrar()

    df["AUTH_USER_ID"] = df["AUTH_USER_ID"].map(
        lambda v: str(v) if v is not None and not pd.isna(v) else None
    )
    df["CORREO"] = None
    df["ACTIVO"] = None

    cliente = obtener_cliente_admin()
    if cliente is not None:
        cuentas = {}
        pagina = 1
        while True:
            lote = cliente.auth.admin.list_users(page=pagina, per_page=1000)
            for cuenta in lote:
                cuentas[str(cuenta.id)] = cuenta
            if len(lote) < 1000:
                break
            pagina += 1

        def correo(auth_id):
            cuenta = cuentas.get(auth_id)
            return cuenta.email if cuenta else None

        def activo(auth_id):
            cuenta = cuentas.get(auth_id)
            if not cuenta:
                return None
            baneado = getattr(cuenta, "banned_until", None)
            if not baneado:
                return True
            return pd.Timestamp(baneado) <= pd.Timestamp.now(tz="UTC")

        df["CORREO"] = df["AUTH_USER_ID"].map(correo)
        df["ACTIVO"] = df["AUTH_USER_ID"].map(activo)

    return df


# ============================================================
# VALIDACIONES
# ============================================================
def validar_contrasena(contrasena, confirmacion):
    if len(contrasena or "") < LONGITUD_MINIMA_CONTRASENA:
        return f"La contraseña debe tener al menos {LONGITUD_MINIMA_CONTRASENA} caracteres."
    if contrasena != confirmacion:
        return "La contraseña y su confirmación no coinciden."
    return None


def validar_datos(nombre, correo, perfil):
    if not nombre:
        return "Debe ingresar el nombre."
    if not PATRON_CORREO.match(correo or ""):
        return "Debe ingresar un correo electrónico válido."
    if not perfil:
        return "Debe seleccionar el perfil."
    return None


def etiqueta_pod(pods_df):
    nombres = dict(zip(pods_df["ID_POD"], pods_df["NOMBRE"]))
    return lambda id_pod: f"{id_pod} · {nombres.get(id_pod, '')}"


def guardar_pods(db, usuario, pods):
    db.execute('DELETE FROM public."USUARIOS_PODS" WHERE "USUARIO" = %s', (usuario,))
    for id_pod in pods:
        db.execute(
            'INSERT INTO public."USUARIOS_PODS" ("USUARIO","ID_POD") VALUES (%s,%s)',
            (usuario, id_pod)
        )


def notificar(mensaje):
    """Guarda un mensaje para mostrarlo después del st.rerun()."""
    st.session_state["mensaje_usuarios"] = mensaje
    st.rerun()


# ============================================================
# VENTANAS (OVERLAY)
# ============================================================
@st.dialog("➕ Nuevo usuario", width="large")
def ventana_crear_usuario(perfiles, pods_df):

    with st.form("form_crear_usuario"):
        c1, c2 = st.columns(2)
        with c1:
            usuario = st.text_input(
                "Usuario",
                max_chars=30,
                placeholder="Ej: JPEREZ",
                help="Letras, números, punto, guion o guion bajo. Se guarda en MAYÚSCULAS."
            )
        with c2:
            nombre = st.text_input("Nombre completo")

        c3, c4 = st.columns(2)
        with c3:
            correo = st.text_input("Correo electrónico", placeholder="usuario@dominio.com")
        with c4:
            perfil = st.selectbox(
                "Perfil",
                perfiles,
                index=perfiles.index("OPERADOR") if "OPERADOR" in perfiles else 0
            )

        c5, c6 = st.columns(2)
        with c5:
            contrasena = st.text_input("Contraseña temporal", type="password")
        with c6:
            confirmacion = st.text_input("Confirmar contraseña", type="password")

        pods = st.multiselect(
            "PODs asignados",
            pods_df["ID_POD"].tolist(),
            format_func=etiqueta_pod(pods_df),
            help="El perfil Operador solo verá las solicitudes de estos PODs."
        )

        with st.container(key="acciones_dlg_crear", horizontal=True,
                          horizontal_alignment="right", gap="small"):
            crear = st.form_submit_button("", icon=":material/person_add:", key="btn_ok_crear", help="Crear usuario")

    if not crear:
        return

    usuario = (usuario or "").strip().upper()
    nombre = (nombre or "").strip()
    correo = (correo or "").strip().lower()

    if not PATRON_USUARIO.match(usuario):
        st.error("❌ El usuario debe tener entre 3 y 30 caracteres: letras, números, punto, guion o guion bajo.")
        return
    error = validar_datos(nombre, correo, perfil) or validar_contrasena(contrasena, confirmacion)
    if error:
        st.error(f"❌ {error}")
        return

    db = Database()
    auth_id = None
    try:
        cliente = cliente_admin_requerido()
        db.conectar()

        db.execute('SELECT 1 FROM public."USUARIOS" WHERE UPPER("USUARIO") = %s', (usuario,))
        if db.fetchone():
            st.error(f"❌ Ya existe el usuario {usuario}.")
            return

        respuesta = cliente.auth.admin.create_user({
            "email": correo,
            "password": contrasena,
            "email_confirm": True,
        })
        auth_id = str(respuesta.user.id)

        db.execute(
            '''INSERT INTO public."USUARIOS" ("USUARIO","NOMBRE","PERFIL","AUTH_USER_ID")
               VALUES (%s,%s,%s,%s)''',
            (usuario, nombre, perfil, auth_id)
        )
        guardar_pods(db, usuario, pods)
        db.commit()

    except Exception as e:
        db.rollback()
        # Si la cuenta de Supabase Auth alcanzó a crearse, se elimina
        # para no dejar una cuenta huérfana.
        if auth_id:
            try:
                obtener_cliente_admin().auth.admin.delete_user(auth_id)
            except Exception:
                pass
        st.error(f"❌ No fue posible crear el usuario: {e}")
        return
    finally:
        db.cerrar()

    notificar(f"✅ Usuario {usuario} creado correctamente.")


@st.dialog("✏️ Editar usuario", width="large")
def ventana_editar_usuario(fila, perfiles, pods_df, usuario_actual):

    es_mismo_usuario = fila["USUARIO"] == usuario_actual
    tiene_cuenta = bool(fila["AUTH_USER_ID"])

    st.markdown(f"### 👤 {fila['USUARIO']}")

    with st.form(f"form_editar_{fila['USUARIO']}"):
        c1, c2 = st.columns(2)
        with c1:
            nombre = st.text_input("Nombre completo", value=fila["NOMBRE"] or "")
        with c2:
            correo = st.text_input(
                "Correo electrónico",
                value=fila["CORREO"] or "",
                disabled=not tiene_cuenta,
                help=None if tiene_cuenta else "El usuario no tiene cuenta en Supabase Auth."
            )

        perfil = st.selectbox(
            "Perfil",
            perfiles,
            index=perfiles.index(fila["PERFIL"]) if fila["PERFIL"] in perfiles else 0,
            disabled=es_mismo_usuario,
            help="No puede cambiar su propio perfil." if es_mismo_usuario else None
        )

        pods = st.multiselect(
            "PODs asignados",
            pods_df["ID_POD"].tolist(),
            default=[p for p in fila["PODS"] if p in set(pods_df["ID_POD"])],
            format_func=etiqueta_pod(pods_df)
        )

        with st.container(key="acciones_dlg_editar", horizontal=True,
                          horizontal_alignment="right", gap="small"):
            guardar = st.form_submit_button("", icon=":material/save:", key="btn_info_editar", help="Guardar cambios")

    if not guardar:
        return

    nombre = (nombre or "").strip()
    correo = (correo or "").strip().lower()
    if es_mismo_usuario:
        perfil = fila["PERFIL"]

    if not nombre:
        st.error("❌ Debe ingresar el nombre.")
        return
    if tiene_cuenta and not PATRON_CORREO.match(correo):
        st.error("❌ Debe ingresar un correo electrónico válido.")
        return

    db = Database()
    try:
        db.conectar()
        db.execute(
            'UPDATE public."USUARIOS" SET "NOMBRE" = %s, "PERFIL" = %s WHERE "USUARIO" = %s',
            (nombre, perfil, fila["USUARIO"])
        )
        guardar_pods(db, fila["USUARIO"], pods)

        # El correo se cambia en Supabase Auth antes de confirmar la
        # transacción: si falla, no se guarda ningún cambio.
        if tiene_cuenta and correo != (fila["CORREO"] or ""):
            cliente_admin_requerido().auth.admin.update_user_by_id(
                fila["AUTH_USER_ID"],
                {"email": correo, "email_confirm": True}
            )

        db.commit()
    except Exception as e:
        db.rollback()
        st.error(f"❌ No fue posible guardar los cambios: {e}")
        return
    finally:
        db.cerrar()

    if es_mismo_usuario:
        st.session_state["nombre_actual"] = nombre

    notificar(f"✅ Usuario {fila['USUARIO']} actualizado correctamente.")


@st.dialog("🔑 Cambiar contraseña", width="large")
def ventana_contrasena(fila):

    st.markdown(f"### 👤 {fila['USUARIO']} · {fila['NOMBRE']}")

    with st.form(f"form_contrasena_{fila['USUARIO']}"):
        c1, c2 = st.columns(2)
        with c1:
            contrasena = st.text_input("Nueva contraseña", type="password")
        with c2:
            confirmacion = st.text_input("Confirmar contraseña", type="password")
        with st.container(key="acciones_dlg_clave", horizontal=True,
                          horizontal_alignment="right", gap="small"):
            cambiar = st.form_submit_button("", icon=":material/key:", key="btn_neutral_clave", help="Cambiar contraseña")

    if not cambiar:
        return

    error = validar_contrasena(contrasena, confirmacion)
    if error:
        st.error(f"❌ {error}")
        return

    try:
        cliente_admin_requerido().auth.admin.update_user_by_id(
            fila["AUTH_USER_ID"], {"password": contrasena}
        )
    except Exception as e:
        st.error(f"❌ No fue posible cambiar la contraseña: {e}")
        return

    notificar(f"✅ Contraseña de {fila['USUARIO']} actualizada correctamente.")


@st.dialog("⚙️ Cambiar estado del usuario", width="large")
def ventana_estado(fila):

    activar = not fila["ACTIVO"]
    accion = "activar" if activar else "desactivar"

    st.markdown(f"### 👤 {fila['USUARIO']} · {fila['NOMBRE']}")
    if not activar:
        st.caption("Un usuario desactivado no puede iniciar sesión en PODEX. Sus datos y PODs se conservan.")
    st.markdown(f"### ❓ ¿Está seguro que desea {accion} este usuario?")

    with st.form(f"form_estado_{fila['USUARIO']}"):
        with st.container(key="acciones_dlg_estado", horizontal=True,
                          horizontal_alignment="right", gap="small"):
            cancelar = st.form_submit_button("", icon=":material/close:", key="btn_cancel_estado", help="Cancelar")
            confirmar = st.form_submit_button("", icon=":material/check:", key="btn_warn_estado", help=f"Sí, {accion}")

    if cancelar:
        st.rerun()
    if not confirmar:
        return

    try:
        cliente_admin_requerido().auth.admin.update_user_by_id(
            fila["AUTH_USER_ID"],
            {"ban_duration": "none" if activar else DURACION_DESACTIVACION}
        )
    except Exception as e:
        st.error(f"❌ No fue posible {accion} el usuario: {e}")
        return

    estado = "activado" if activar else "desactivado"
    notificar(f"✅ Usuario {fila['USUARIO']} {estado} correctamente.")


@st.dialog("🗑️ Eliminar usuario", width="large")
def ventana_eliminar(fila):

    st.markdown(f"### 👤 {fila['USUARIO']} · {fila['NOMBRE']}")
    st.caption(
        "Se eliminan el usuario, sus PODs asignados y su cuenta de acceso. "
        "Las solicitudes y gestiones registradas no se modifican. "
        "Esta acción no se puede deshacer."
    )
    st.markdown("### ❓ ¿Está seguro que desea eliminar este usuario?")

    with st.form(f"form_eliminar_{fila['USUARIO']}"):
        with st.container(key="acciones_dlg_eliminar", horizontal=True,
                          horizontal_alignment="right", gap="small"):
            cancelar = st.form_submit_button("", icon=":material/close:", key="btn_cancel_eliminar", help="Cancelar")
            confirmar = st.form_submit_button("", icon=":material/delete:", key="btn_danger_eliminar", help="Sí, eliminar")

    if cancelar:
        st.rerun()
    if not confirmar:
        return

    db = Database()
    try:
        db.conectar()
        db.execute('DELETE FROM public."USUARIOS_PODS" WHERE "USUARIO" = %s', (fila["USUARIO"],))
        db.execute('DELETE FROM public."USUARIOS" WHERE "USUARIO" = %s', (fila["USUARIO"],))

        # La cuenta de acceso se elimina antes de confirmar la transacción:
        # si falla, el usuario se conserva completo.
        if fila["AUTH_USER_ID"]:
            cliente_admin_requerido().auth.admin.delete_user(fila["AUTH_USER_ID"])

        db.commit()
    except Exception as e:
        db.rollback()
        st.error(f"❌ No fue posible eliminar el usuario: {e}")
        return
    finally:
        db.cerrar()

    notificar(f"✅ Usuario {fila['USUARIO']} eliminado correctamente.")


# ============================================================
# PÁGINA PRINCIPAL DEL MÓDULO
# ============================================================
def mostrar_modulo_usuarios(usuario_actual):

    mensaje = st.session_state.pop("mensaje_usuarios", None)
    if mensaje:
        st.success(mensaje)

    if obtener_cliente_admin() is None:
        st.warning(
            "⚠️ Para crear usuarios, cambiar contraseñas, activar/desactivar o eliminar "
            "cuentas, agregue `service_role_key` en la sección `[supabase]` de los "
            "secretos de la aplicación (Supabase → Project Settings → API → service_role)."
        )

    try:
        perfiles = obtener_perfiles()
        pods_df = obtener_pods()
        usuarios = obtener_usuarios()
    except Exception as e:
        st.error("❌ No fue posible consultar los usuarios.")
        st.exception(e)
        return

    hay_admin_auth = obtener_cliente_admin() is not None

    texto = st.text_input(
        "🔎 Buscar usuario",
        placeholder="Digite usuario, nombre, correo, perfil o POD..."
    )

    if texto:
        texto_busqueda = texto.lower()
        mascara = usuarios.apply(
            lambda f: texto_busqueda in " ".join(
                str(v) for v in [f["USUARIO"], f["NOMBRE"], f["PERFIL"], f["CORREO"], *f["PODS"]]
            ).lower(),
            axis=1
        )
        usuarios = usuarios[mascara]

    usuarios = usuarios.reset_index(drop=True)

    # Fila seleccionada en la cuadrícula (se dibuja más abajo).
    seleccion = st.session_state.get("tabla_usuarios")
    filas = seleccion.selection.rows if seleccion else []
    fila = (
        usuarios.iloc[filas[0]]
        if filas and filas[0] < len(usuarios)
        else None
    )

    if fila is not None:
        es_mismo_usuario = fila["USUARIO"] == usuario_actual
        tiene_cuenta = bool(fila["AUTH_USER_ID"])
        activo = fila["ACTIVO"]
    else:
        es_mismo_usuario = tiene_cuenta = False
        activo = None

    c_sel, c_acciones = st.columns([3, 1.4], vertical_alignment="center")

    with c_sel:
        if fila is not None:
            st.markdown(f"**Usuario seleccionado:** {fila['USUARIO']} · {fila['NOMBRE']}")
        else:
            st.caption("☝️ Seleccione un usuario en la tabla para administrarlo.")

    with c_acciones:
        with st.container(key="acciones_usuarios", horizontal=True,
                          horizontal_alignment="right", gap="small"):
            if st.button("", icon=":material/person_add:", key="btn_usr_nuevo",
                         disabled=not hay_admin_auth, help="Nuevo usuario"):
                ventana_crear_usuario(perfiles, pods_df)

            if st.button("", icon=":material/edit:", key="btn_usr_editar",
                         disabled=fila is None, help="Editar usuario"):
                ventana_editar_usuario(fila, perfiles, pods_df, usuario_actual)

            if st.button("", icon=":material/key:", key="btn_usr_clave",
                         disabled=fila is None or not (hay_admin_auth and tiene_cuenta),
                         help="Cambiar contraseña"):
                ventana_contrasena(fila)

            if st.button("", icon=":material/person_off:" if activo is not False else ":material/person_check:",
                         key="btn_usr_estado",
                         disabled=fila is None or es_mismo_usuario or activo is None,
                         help="Activar usuario" if activo is False else "Desactivar usuario"):
                ventana_estado(fila)

            if st.button("", icon=":material/delete:", key="btn_usr_eliminar",
                         disabled=fila is None or es_mismo_usuario or not hay_admin_auth,
                         help="Eliminar usuario"):
                ventana_eliminar(fila)

    if usuarios.empty:
        st.info("ℹ️ No existen usuarios que coincidan con el criterio de búsqueda.")
        return

    def estado(valor):
        if valor is None or pd.isna(valor):
            return "Sin cuenta" if hay_admin_auth else "—"
        return "🟢 Activo" if valor else "🔴 Inactivo"

    tabla = pd.DataFrame({
        "USUARIO": usuarios["USUARIO"],
        "NOMBRE": usuarios["NOMBRE"],
        "PERFIL": usuarios["PERFIL"],
        "CORREO": usuarios["CORREO"].fillna("—"),
        "PODS": usuarios["PODS"].map(lambda p: ", ".join(p) or "—"),
        "ESTADO": usuarios["ACTIVO"].map(estado),
    })

    st.markdown('<div style="height:14px"></div>', unsafe_allow_html=True)

    st.dataframe(
        tabla,
        key="tabla_usuarios",
        on_select="rerun",
        selection_mode="single-row",
        hide_index=True,
        use_container_width=True,
        height=min(38 + 35 * len(tabla), 640),
        column_config={
            "USUARIO": st.column_config.TextColumn("USUARIO", width="small"),
            "NOMBRE": st.column_config.TextColumn("NOMBRE", width="medium"),
            "PERFIL": st.column_config.TextColumn("PERFIL", width="small"),
            "CORREO": st.column_config.TextColumn("CORREO", width="medium"),
            "PODS": st.column_config.TextColumn("PODS", width="small"),
            "ESTADO": st.column_config.TextColumn("ESTADO", width="small"),
        },
    )
