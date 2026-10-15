"""
Vista previa de los correos de PODEX antes de enviarlos.

Cualquier módulo prepara el correo con programar_envio() y hace st.rerun();
app.py llama a mostrar_envio_pendiente() en cada página, que abre la ventana
con el correo tal como llegará y los botones para enviarlo o no enviarlo.

Los destinatarios salen de la lista del reporte (Administración → Listas de
correo) o, como en la bienvenida, vienen fijos. No se eligen al enviar.
"""

import html as html_lib

import streamlit as st

from correo import MARCA_ECOPETROL, enviar_correo, remitente, vista_previa_html
from listas import REPORTES, TIPOS, destinatarios_reporte
from usuarios import encabezado_ventana, ficha

CLAVE = "envio_pendiente"


def programar_envio(titulo, asunto, texto, html, envio=None, destinatarios=None,
                    adjuntos=(), aviso_ok="Correo enviado"):
    """Deja el correo listo para la vista previa (se abre en el siguiente rerun).

    envio: clave de REPORTES (los destinatarios son los de su lista), o
    destinatarios: {"PARA": [...], "CC": [...], "CCO": [...]} fijos.
    adjuntos: [(nombre_archivo, bytes)].
    """
    st.session_state[CLAVE] = {
        "titulo": titulo, "asunto": asunto, "texto": texto, "html": html,
        "envio": envio, "destinatarios": destinatarios,
        "adjuntos": list(adjuntos), "aviso_ok": aviso_ok,
    }


def _chips(correos):
    if not correos:
        return "—"
    return " ".join(
        '<span style="display:inline-block;background:#eef5f2;border:1px solid #cfe0db;border-radius:99px;'
        f'padding:1px 8px;margin:0 4px 3px 0;font-size:11px">{html_lib.escape(c)}</span>'
        for c in correos
    )


@st.dialog(" ", width="large")
def ventana_envio(datos):
    encabezado_ventana(f"Vista previa · {datos['titulo']}")

    destinatarios = datos["destinatarios"]
    nombre_lista = None
    if datos["envio"]:
        nombre_lista = REPORTES[datos["envio"]]
        try:
            destinatarios = destinatarios_reporte(datos["envio"])
        except Exception as e:
            st.error(f"❌ No fue posible obtener los destinatarios del reporte: {e}")
            destinatarios = None
        if destinatarios is not None and not any(destinatarios.values()):
            st.warning(f"⚠️ «{nombre_lista}» no tiene destinatarios configurados. El administrador "
                       "puede agregarlos en Administración → Listas de correo.")

    destinatarios = destinatarios or {t: [] for t in TIPOS}
    total = sum(len(destinatarios[t]) for t in TIPOS)

    campos = [("Asunto", f"<b>{html_lib.escape(datos['asunto'])}</b>"),
              ("Envía", html_lib.escape(remitente() or "Sin configurar"))]
    if nombre_lista:
        campos.append(("Lista de destinatarios", html_lib.escape(nombre_lista)))
    campos += [("Para", _chips(destinatarios["PARA"])), ("CC", _chips(destinatarios["CC"]))]
    if destinatarios["CCO"]:
        campos.append(("CCO (copia oculta)", f"{len(destinatarios['CCO'])} destinatario(s)"))
    if datos["adjuntos"]:
        campos.append(("Adjunto", " · ".join(f"📎 {html_lib.escape(n)}" for n, _ in datos["adjuntos"])))
    ficha(campos, columnas=2)
    if destinatarios["CCO"]:
        with st.expander(f"Ver los {len(destinatarios['CCO'])} destinatario(s) en copia oculta"):
            st.markdown(_chips(destinatarios["CCO"]), unsafe_allow_html=True)

    st.iframe(vista_previa_html(datos["html"], MARCA_ECOPETROL), height=560)

    sin_config = remitente() is None
    if sin_config:
        st.warning("⚠️ Falta configurar la sección [email] en los secretos; no es posible enviar.")

    c_nota, c_acciones = st.columns([3, 1], vertical_alignment="center")
    with c_nota:
        st.caption("El correo no se envía hasta que pulse ✈. Si cierra esta ventana, no se envía.")
    with c_acciones:
        with st.container(key="acciones_dlg_envio", horizontal=True,
                          horizontal_alignment="right", gap="small"):
            no_enviar = st.button("", icon=":material/close:", key="btn_cancel_envio", help="No enviar")
            enviar = st.button("", icon=":material/send:", key="btn_ok_envio", help="Enviar",
                               disabled=sin_config or total == 0)

    if no_enviar:
        st.session_state["mensaje_envio"] = ("info", f"ℹ️ {datos['titulo']}: el correo no se envió.")
        st.rerun()
    if not enviar:
        return

    try:
        with st.spinner("Enviando el correo..."):
            enviados = enviar_correo(
                datos["asunto"], datos["texto"], datos["html"],
                para=destinatarios["PARA"], cc=destinatarios["CC"], cco=destinatarios["CCO"],
                adjuntos=datos["adjuntos"], marca=MARCA_ECOPETROL,
            )
    except Exception as e:
        st.error(f"❌ No fue posible enviar el correo: {e}")
        return

    st.session_state["mensaje_envio"] = (
        "success", f"📧 {datos['aviso_ok']} a {enviados} destinatario(s)"
                   + (f" de la lista «{nombre_lista}»." if nombre_lista else ".")
    )
    st.rerun()


def mostrar_envio_pendiente():
    """Muestra el resultado del último envío y abre la vista previa pendiente."""
    mensaje = st.session_state.pop("mensaje_envio", None)
    if mensaje:
        tipo, texto = mensaje
        {"success": st.success, "info": st.info}.get(tipo, st.warning)(texto)

    datos = st.session_state.pop(CLAVE, None)
    if datos:
        ventana_envio(datos)
