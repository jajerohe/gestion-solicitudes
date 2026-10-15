"""
Módulo de Listas de correo de PODEX (solo Administrador).

Cada reporte que envía correos (REPORTES) tiene UNA lista de destinatarios,
que se arma aquí: se elige el reporte, se agregan correos con su tipo (Para,
CC o CCO) y se quitan de la lista de registrados. Al enviar un reporte, el
correo va únicamente a los destinatarios de su lista; no se eligen en ese
momento.

Tablas: public."LISTAS_CORREO" (una fila por reporte, ENVIO único) y
public."LISTAS_CORREO_DESTINATARIOS".
"""

import re

import pandas as pd
import streamlit as st

from database import Database

# Reportes (envíos del sistema) que tienen lista de destinatarios.
REPORTES = {
    "SEGUIMIENTO": "Seguimiento de solicitudes abiertas",
    "BACKLOG": "Control Operativo – Backlog Diario",
}
TIPOS = ["PARA", "CC", "CCO"]
NOMBRES_TIPO = {"PARA": "Para", "CC": "CC (con copia)", "CCO": "CCO (copia oculta)"}
PATRON_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# ============================================================
# CONSULTAS
# ============================================================
@st.cache_data(ttl=60, show_spinner=False)
def obtener_destinatarios(envio):
    """Destinatarios registrados del reporte: DataFrame con CORREO y TIPO.

    Solo correos válidos: filas antiguas que no son un correo (como el grupo
    de Operadores que existió antes) se ignoran.
    """
    db = Database()
    try:
        db.conectar()
        db.execute('''
            SELECT d."CORREO", d."TIPO"
            FROM public."LISTAS_CORREO_DESTINATARIOS" d
            JOIN public."LISTAS_CORREO" l ON l."ID_LISTA" = d."ID_LISTA"
            WHERE l."ENVIO" = %s
            ORDER BY CASE d."TIPO" WHEN 'PARA' THEN 1 WHEN 'CC' THEN 2 ELSE 3 END, d."CORREO"
        ''', (envio,))
        df = pd.DataFrame(db.fetchall(), columns=["CORREO", "TIPO"])
    finally:
        db.cerrar()
    return df[df["CORREO"].astype(str).str.match(PATRON_CORREO)].reset_index(drop=True)


def destinatarios_reporte(envio):
    """{"PARA": [...], "CC": [...], "CCO": [...]} con los correos de la lista del reporte."""
    df = obtener_destinatarios(envio)
    return {t: df.loc[df["TIPO"] == t, "CORREO"].tolist() for t in TIPOS}


def _agregar(envio, correo, tipo, usuario_actual):
    db = Database()
    try:
        db.conectar()
        db.execute('''
            INSERT INTO public."LISTAS_CORREO" ("NOMBRE","ENVIO","USUARIO_REGISTRO")
            VALUES (%s,%s,%s)
            ON CONFLICT ("ENVIO") DO UPDATE SET "NOMBRE" = EXCLUDED."NOMBRE"
            RETURNING "ID_LISTA"
        ''', (REPORTES[envio], envio, usuario_actual))
        id_lista = db.fetchone()[0]
        db.execute('''
            INSERT INTO public."LISTAS_CORREO_DESTINATARIOS" ("ID_LISTA","CORREO","TIPO")
            VALUES (%s,%s,%s)
        ''', (id_lista, correo, tipo))
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.cerrar()


def _quitar(envio, correo):
    db = Database()
    try:
        db.conectar()
        db.execute('''
            DELETE FROM public."LISTAS_CORREO_DESTINATARIOS" d
            USING public."LISTAS_CORREO" l
            WHERE l."ID_LISTA" = d."ID_LISTA" AND l."ENVIO" = %s AND d."CORREO" = %s
        ''', (envio, correo))
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.cerrar()


def notificar(mensaje, tipo="success"):
    st.cache_data.clear()
    st.session_state["mensaje_listas"] = (tipo, mensaje)
    st.rerun()


# ============================================================
# PÁGINA PRINCIPAL DEL MÓDULO
# ============================================================
def mostrar_modulo_listas(usuario_actual):

    mensaje = st.session_state.pop("mensaje_listas", None)
    if mensaje:
        tipo, texto_mensaje = mensaje
        (st.warning if tipo == "warning" else st.success)(texto_mensaje)

    with st.container(border=True):
        st.markdown('<div class="podex-section-title">📧 Destinatarios por reporte</div>', unsafe_allow_html=True)
        st.markdown('<div class="podex-section-caption">Cada reporte se envía únicamente a los correos registrados '
                    'en su lista. Para = destinatario principal · CC = con copia · CCO = copia oculta '
                    '(los demás destinatarios no lo ven).</div>', unsafe_allow_html=True)

        envio = st.selectbox("Reporte", list(REPORTES), format_func=REPORTES.get, key="lista_reporte")

        c_correo, c_tipo, c_boton = st.columns([3, 1.2, 0.4], vertical_alignment="bottom")
        with c_correo:
            correo = st.text_input("Destinatario", placeholder="correo@dominio.com",
                                   key=f"lista_correo_{st.session_state.get('lista_version', 0)}")
        with c_tipo:
            tipo = st.selectbox("Tipo", TIPOS, format_func=NOMBRES_TIPO.get, key="lista_tipo")
        with c_boton:
            with st.container(key="acciones_lista_agregar"):
                agregar = st.button("", icon=":material/add:", key="btn_ok_lista_agregar",
                                    help="Agregar a la lista")

        try:
            registrados = obtener_destinatarios(envio)
        except Exception as e:
            st.error("❌ No fue posible consultar los destinatarios.")
            st.exception(e)
            return

        if agregar:
            correo = (correo or "").strip().lower()
            if not PATRON_CORREO.match(correo):
                st.error("❌ Escriba un correo válido, por ejemplo nombre@dominio.com.")
            elif correo in set(registrados["CORREO"].str.lower()):
                st.error(f"❌ {correo} ya está en la lista de este reporte.")
            else:
                try:
                    _agregar(envio, correo, tipo, usuario_actual)
                except Exception as e:
                    st.error(f"❌ No fue posible agregar el destinatario: {e}")
                else:
                    st.session_state["lista_version"] = st.session_state.get("lista_version", 0) + 1
                    notificar(f"✅ {correo} agregado a «{REPORTES[envio]}» como {NOMBRES_TIPO[tipo]}.")

        st.markdown('<div style="height:10px"></div>', unsafe_allow_html=True)
        c_titulo, c_quitar = st.columns([4, 0.4], vertical_alignment="bottom")
        with c_titulo:
            st.markdown("**Lista de destinatarios registrados**")
        seleccion = st.session_state.get(f"tabla_lista_{envio}")
        filas = seleccion.selection.rows if seleccion else []
        fila = registrados.iloc[filas[0]] if filas and filas[0] < len(registrados) else None
        with c_quitar:
            with st.container(key="acciones_lista_quitar"):
                quitar = st.button("", icon=":material/remove:", key="btn_danger_lista_quitar",
                                   disabled=fila is None, help="Quitar el destinatario seleccionado")

        if quitar and fila is not None:
            try:
                _quitar(envio, fila["CORREO"])
            except Exception as e:
                st.error(f"❌ No fue posible quitar el destinatario: {e}")
            else:
                notificar(f"✅ {fila['CORREO']} quitado de «{REPORTES[envio]}».")

        if registrados.empty:
            st.info("ℹ️ Este reporte aún no tiene destinatarios; no se podrá enviar hasta que agregue al menos uno.")
            return

        st.dataframe(
            pd.DataFrame({"DESTINATARIO": registrados["CORREO"],
                          "TIPO": registrados["TIPO"].map(NOMBRES_TIPO)}),
            key=f"tabla_lista_{envio}",
            on_select="rerun",
            selection_mode="single-row",
            hide_index=True,
            width="stretch",
            height=min(38 + 35 * len(registrados), 520),
            column_config={
                "DESTINATARIO": st.column_config.TextColumn("DESTINATARIO", width="large"),
                "TIPO": st.column_config.TextColumn("TIPO", width="medium"),
            },
        )
        st.caption("☝️ Seleccione un destinatario y use − para quitarlo de la lista.")
