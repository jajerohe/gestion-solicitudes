"""
Módulo de Reportes de PODEX (solo Administrador).

Cada reporte es una función que dibuja su contenido; se registran en REPORTES
y la página muestra un selector para elegir cuál ver.

Reportes disponibles:
  - Auditoría de carga de Excel: historial de public."AUDITORIA", que se
    llena en cada carga de solicitudes (app.py → guardar_auditoria).
"""

import io
import re
from datetime import date, timedelta

import pandas as pd
import streamlit as st

from database import Database


# ============================================================
# CONSULTAS
# ============================================================
@st.cache_data(ttl=60, show_spinner=False)
def obtener_auditoria_cargas():
    """Historial completo de cargas de Excel, de la más reciente a la más antigua."""
    db = Database()
    try:
        db.conectar()
        db.execute('''
            SELECT
                "ID_AUDITORIA",
                "FECHA_CARGUE",
                "NOMBRE_ARCHIVO",
                "USUARIO_CARGA",
                "REGISTROS_GENERALES",
                "REGISTROS_FUNCIONALES",
                COALESCE("TOTAL_REGISTROS",
                         COALESCE("REGISTROS_GENERALES", 0)
                         + COALESCE("REGISTROS_FUNCIONALES", 0)) AS "TOTAL_REGISTROS",
                "ESTADO",
                "OBSERVACIONES"
            FROM public."AUDITORIA"
            ORDER BY "FECHA_CARGUE" DESC, "ID_AUDITORIA" DESC
        ''')
        df = pd.DataFrame(db.fetchall(), columns=[
            "ID_AUDITORIA", "FECHA_CARGUE", "NOMBRE_ARCHIVO", "USUARIO_CARGA",
            "REGISTROS_GENERALES", "REGISTROS_FUNCIONALES", "TOTAL_REGISTROS",
            "ESTADO", "OBSERVACIONES",
        ])
    finally:
        db.cerrar()

    df["FECHA_CARGUE"] = pd.to_datetime(df["FECHA_CARGUE"])
    for columna in ("REGISTROS_GENERALES", "REGISTROS_FUNCIONALES", "TOTAL_REGISTROS"):
        df[columna] = pd.to_numeric(df[columna], errors="coerce").fillna(0).astype(int)

    # Duplicados y errores solo quedan en el texto de OBSERVACIONES
    # ("Archivo procesado. Duplicados: N. Errores: N.").
    df["DUPLICADOS"] = df["OBSERVACIONES"].map(lambda t: _numero_en(t, "Duplicados"))
    df["ERRORES"] = df["OBSERVACIONES"].map(lambda t: _numero_en(t, "Errores"))
    return df


def _numero_en(texto, etiqueta):
    m = re.search(rf"{etiqueta}:\s*(\d+)", str(texto or ""))
    return int(m.group(1)) if m else 0


def a_excel(df, hoja):
    """Devuelve el DataFrame como archivo .xlsx (bytes) con anchos ajustados."""
    salida = io.BytesIO()
    with pd.ExcelWriter(salida, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name=hoja, index=False)
        ws = writer.sheets[hoja]
        for i, columna in enumerate(df.columns, start=1):
            ancho = max([len(str(columna))] + [len(str(v)) for v in df[columna]]) + 2
            ws.column_dimensions[ws.cell(1, i).column_letter].width = min(ancho, 60)
        ws.freeze_panes = "A2"
    return salida.getvalue()


# ============================================================
# REPORTE: AUDITORÍA DE CARGA DE EXCEL
# ============================================================
def reporte_auditoria_cargas():

    try:
        auditoria = obtener_auditoria_cargas()
    except Exception as e:
        st.error("❌ No fue posible consultar la auditoría de cargas.")
        st.exception(e)
        return

    if auditoria.empty:
        st.info("ℹ️ Aún no se ha registrado ninguna carga de Excel.")
        return

    # ---------------- Filtros ----------------
    fecha_min = auditoria["FECHA_CARGUE"].min().date()
    fecha_max = max(auditoria["FECHA_CARGUE"].max().date(), date.today())

    with st.container(border=True):
        st.markdown('<div class="podex-section-title">🔎 Filtros</div>', unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns([1.3, 1, 1, 1.4])
        with c1:
            rango = st.date_input(
                "Fecha de carga",
                value=(max(fecha_min, fecha_max - timedelta(days=30)), fecha_max),
                min_value=fecha_min,
                max_value=fecha_max,
                format="YYYY-MM-DD",
                key="rep_aud_fechas",
            )
        with c2:
            usuarios = st.multiselect(
                "Usuario",
                sorted(auditoria["USUARIO_CARGA"].dropna().unique()),
                placeholder="Todos",
                key="rep_aud_usuarios",
            )
        with c3:
            estados = st.multiselect(
                "Estado",
                sorted(auditoria["ESTADO"].dropna().unique()),
                placeholder="Todos",
                key="rep_aud_estados",
            )
        with c4:
            texto = st.text_input(
                "Archivo",
                placeholder="Nombre del archivo...",
                key="rep_aud_archivo",
            )

    # Mientras se elige la segunda fecha el selector devuelve solo una.
    rango = list(rango) if isinstance(rango, (tuple, list)) else [rango]
    if not rango:
        st.info("ℹ️ Seleccione el rango de fechas de carga.")
        return
    desde, hasta = rango[0], rango[-1]

    datos = auditoria[
        (auditoria["FECHA_CARGUE"].dt.date >= desde)
        & (auditoria["FECHA_CARGUE"].dt.date <= hasta)
    ]
    if usuarios:
        datos = datos[datos["USUARIO_CARGA"].isin(usuarios)]
    if estados:
        datos = datos[datos["ESTADO"].isin(estados)]
    if texto:
        datos = datos[datos["NOMBRE_ARCHIVO"].astype(str).str.contains(texto, case=False, na=False, regex=False)]

    if datos.empty:
        st.info("ℹ️ No hay cargas que coincidan con los filtros seleccionados.")
        return

    # ---------------- Indicadores ----------------
    exitosas = int((datos["ESTADO"].astype(str).str.upper() == "EXITOSO").sum())
    a, b, c, d, e = st.columns(5)
    a.metric("Cargas", len(datos))
    b.metric("Exitosas", f"{exitosas} ({exitosas / len(datos):.0%})")
    c.metric("Registros cargados", f"{int(datos['TOTAL_REGISTROS'].sum()):,}".replace(",", "."))
    d.metric("Duplicados", int(datos["DUPLICADOS"].sum()))
    e.metric("Errores", int(datos["ERRORES"].sum()))

    # ---------------- Gráfica ----------------
    with st.container(border=True):
        st.markdown('<div class="podex-section-title">📈 Registros cargados por día</div>', unsafe_allow_html=True)
        st.markdown('<div class="podex-section-caption">Suma de las solicitudes de DETALLE_GENERAL y DETALLE_FUNCIONALES cargadas cada día.</div>', unsafe_allow_html=True)
        por_dia = (
            datos.assign(DIA=datos["FECHA_CARGUE"].dt.normalize())
            .groupby("DIA")[["REGISTROS_GENERALES", "REGISTROS_FUNCIONALES"]]
            .sum()
            .rename(columns={"REGISTROS_GENERALES": "Generales",
                             "REGISTROS_FUNCIONALES": "Funcionales"})
        )
        st.bar_chart(por_dia, color=["#0b5b4d", "#b7d51f"], height=260,
                     x_label="Fecha de carga", y_label="Registros")

    # ---------------- Detalle ----------------
    tabla = datos[[
        "ID_AUDITORIA", "FECHA_CARGUE", "NOMBRE_ARCHIVO", "USUARIO_CARGA",
        "REGISTROS_GENERALES", "REGISTROS_FUNCIONALES", "TOTAL_REGISTROS",
        "DUPLICADOS", "ERRORES", "ESTADO", "OBSERVACIONES",
    ]].reset_index(drop=True)

    with st.container(border=True):
        c_titulo, c_descarga = st.columns([4, 1], vertical_alignment="center")
        with c_titulo:
            st.markdown('<div class="podex-section-title">📋 Detalle de cargas</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="podex-section-caption">{len(tabla)} carga(s) entre {desde:%Y-%m-%d} y {hasta:%Y-%m-%d}.</div>', unsafe_allow_html=True)
        with c_descarga:
            with st.container(key="acciones_rep_auditoria", horizontal=True,
                              horizontal_alignment="right"):
                st.download_button(
                    "",
                    data=a_excel(tabla.assign(FECHA_CARGUE=tabla["FECHA_CARGUE"].dt.strftime("%Y-%m-%d %H:%M:%S")),
                                 "AUDITORIA_CARGAS"),
                    file_name=f"Auditoria_cargas_{desde:%Y%m%d}_{hasta:%Y%m%d}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    icon=":material/download:",
                    key="btn_rep_descargar",
                    help="Descargar en Excel",
                )

        st.dataframe(
            tabla,
            hide_index=True,
            width="stretch",
            height=min(38 + 35 * len(tabla), 640),
            column_config={
                "ID_AUDITORIA": st.column_config.NumberColumn("ID", width="small", format="%d"),
                "FECHA_CARGUE": st.column_config.DatetimeColumn("FECHA_CARGUE", format="YYYY-MM-DD HH:mm:ss"),
                "NOMBRE_ARCHIVO": st.column_config.TextColumn("NOMBRE_ARCHIVO"),
                "USUARIO_CARGA": st.column_config.TextColumn("USUARIO_CARGA"),
                "REGISTROS_GENERALES": st.column_config.NumberColumn("GENERALES", width="small"),
                "REGISTROS_FUNCIONALES": st.column_config.NumberColumn("FUNCIONALES", width="small"),
                "TOTAL_REGISTROS": st.column_config.NumberColumn("TOTAL", width="small"),
                "DUPLICADOS": st.column_config.NumberColumn("DUPLICADOS", width="small"),
                "ERRORES": st.column_config.NumberColumn("ERRORES", width="small"),
                "ESTADO": st.column_config.TextColumn("ESTADO", width="small"),
                "OBSERVACIONES": st.column_config.TextColumn("OBSERVACIONES", width="large"),
            },
        )


# ============================================================
# PÁGINA PRINCIPAL DEL MÓDULO
# ============================================================
# Clave → (nombre, descripción, función). Para agregar un reporte nuevo basta
# con escribir su función y registrarla aquí.
REPORTES = {
    "auditoria_cargas": (
        "Auditoría de carga de Excel",
        "Historial de los archivos cargados: quién, cuándo, cuántos registros y con qué resultado.",
        reporte_auditoria_cargas,
    ),
}


def mostrar_modulo_reportes():
    claves = list(REPORTES)
    c_sel, c_desc = st.columns([1, 2], vertical_alignment="bottom")
    with c_sel:
        clave = st.selectbox(
            "Reporte",
            claves,
            format_func=lambda k: REPORTES[k][0],
            key="reporte_actual",
        )
    nombre, descripcion, funcion = REPORTES[clave]
    with c_desc:
        st.markdown(f'<div class="podex-section-caption" style="margin-bottom:12px">{descripcion}</div>',
                    unsafe_allow_html=True)

    funcion()
