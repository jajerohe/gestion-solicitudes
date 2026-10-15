"""
Reporte "Seguimiento de solicitudes abiertas" (perfil Operador).

Arma el correo de seguimiento del backlog para los Product Owner de los POD
asignados al usuario: solo solicitudes sin FECHA_CIERRE ni CODIGO_CIERRE, con
la última gestión registrada en PODEX como observación. Se puede copiar con
formato para pegarlo en Outlook o descargar en Excel.
"""

import html
import io
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from database import Database

ZONA = ZoneInfo("America/Bogota")

# Hoja de origen → título de la tabla (los mismos del correo de backlog).
SECCIONES = {
    "DETALLE_GENERAL": "DETALLE GENERAL",
    "DETALLE_FUNCIONALES": "GRUPO FUNCIONAL ECOPETROL",
}

# Columna → ancho en % de la tabla del correo (suman 100).
COLUMNAS = [
    ("SOLICITUD", 16), ("CATEGORIA", 12), ("STATUS", 8), ("FECHA_APERTURA", 8),
    ("RANGO_TIEMPO", 7), ("SUBSERVICIO_AFECTADO", 11), ("PRODUCT_OWNER", 10),
    ("# DÍAS", 4), ("OBSERVACIÓN", 24),
]

# Color de fondo de la celda STATUS (mismo criterio en el correo y en Excel).
COLORES_STATUS = {
    "IN PROGRESS": "FFFF00",
    "WORK IN PROGRESS": "FFFF00",
    "PENDING CUSTOMER": "92D050",
    "PENDING VENDOR": "F4B183",
    "OPEN": "BDD7EE",
    "SUSPENDED": "D9D9D9",
}


# ============================================================
# CONSULTAS
# ============================================================
@st.cache_data(ttl=60, show_spinner=False)
def obtener_pods_usuario(usuario):
    """Product Owner (NOMBRE de PODS) de los POD asignados al usuario."""
    db = Database()
    try:
        db.conectar()
        db.execute('''
            SELECT p."NOMBRE"
            FROM public."PODS" p
            JOIN public."USUARIOS_PODS" up ON up."ID_POD" = p."ID_POD"
            WHERE up."USUARIO" = %s
            ORDER BY p."NOMBRE"
        ''', (usuario,))
        return [fila[0] for fila in db.fetchall()]
    finally:
        db.cerrar()


@st.cache_data(ttl=60, show_spinner=False)
def obtener_abiertas_usuario(usuario):
    """Solicitudes abiertas de los POD del usuario con su última gestión."""
    db = Database()
    try:
        db.conectar()
        db.execute('''
            SELECT
                s."ORIGEN", s."ID_SOLICITUD", s."TITULO", s."CATEGORIA",
                s."STATUS", s."FECHA_APERTURA", s."RANGTIEMPO",
                s."SUBSERVICIO_AFECTADO", s."PRODUCT_OWNER",
                g."FECHA_GESTION", g."OBSERVACION"
            FROM public."SOLICITUDES" s
            LEFT JOIN LATERAL (
                SELECT x."FECHA_GESTION", x."OBSERVACION"
                FROM public."GESTIONES" x
                WHERE x."ID_SOLICITUD" = s."ID_SOLICITUD"
                ORDER BY x."FECHA_GESTION" DESC, x."ID_GESTION" DESC
                LIMIT 1
            ) g ON TRUE
            WHERE s."FECHA_CIERRE" IS NULL
              AND s."CODIGO_CIERRE" IS NULL
              AND EXISTS (
                  SELECT 1
                  FROM public."PODS" p
                  JOIN public."USUARIOS_PODS" up ON up."ID_POD" = p."ID_POD"
                  WHERE up."USUARIO" = %s
                    AND UPPER(TRIM(p."NOMBRE")) = UPPER(TRIM(s."PRODUCT_OWNER"))
              )
            ORDER BY s."FECHA_APERTURA" ASC
        ''', (usuario,))
        df = pd.DataFrame(db.fetchall(), columns=[
            "ORIGEN", "ID_SOLICITUD", "TITULO", "CATEGORIA", "STATUS",
            "FECHA_APERTURA", "RANGTIEMPO", "SUBSERVICIO_AFECTADO",
            "PRODUCT_OWNER", "FECHA_GESTION", "OBSERVACION",
        ])
    finally:
        db.cerrar()
    df["FECHA_APERTURA"] = pd.to_datetime(df["FECHA_APERTURA"])
    df["FECHA_GESTION"] = pd.to_datetime(df["FECHA_GESTION"])
    return df


@st.cache_data(ttl=60, show_spinner=False)
def fecha_ultimo_archivo():
    """Fecha de la última carga de Excel (la del archivo de Control Operativo)."""
    db = Database()
    try:
        db.conectar()
        db.execute('SELECT MAX("FECHA_CARGUE") FROM public."AUDITORIA"')
        fila = db.fetchone()
        return fila[0].date() if fila and fila[0] else None
    finally:
        db.cerrar()


# ============================================================
# ARMADO DEL REPORTE
# ============================================================
def _texto(valor):
    return "" if valor is None or (isinstance(valor, float) and pd.isna(valor)) else str(valor).strip()


def _nombre_propio(nombre):
    return " ".join(p.capitalize() for p in _texto(nombre).split())


def preparar_filas(df, hoy):
    """Filas del reporte, en el orden y con el formato de la tabla del correo."""
    filas = []
    for _, r in df.iterrows():
        apertura = r["FECHA_APERTURA"]
        gestion = r["FECHA_GESTION"]
        filas.append({
            "ORIGEN": r["ORIGEN"],
            "SOLICITUD": f'{_texto(r["ID_SOLICITUD"])} - {_texto(r["TITULO"])}'.rstrip(" -"),
            "CATEGORIA": _texto(r["CATEGORIA"]),
            "STATUS": _texto(r["STATUS"]),
            "FECHA_APERTURA": f"{apertura.day}/{apertura.month}/{apertura.year} {apertura.hour}:{apertura:%M}"
                              if pd.notna(apertura) else "",
            "RANGO_TIEMPO": _texto(r["RANGTIEMPO"]),
            "SUBSERVICIO_AFECTADO": _texto(r["SUBSERVICIO_AFECTADO"]),
            "PRODUCT_OWNER": _texto(r["PRODUCT_OWNER"]),
            "# DÍAS": (hoy - apertura.date()).days if pd.notna(apertura) else None,
            "FECHA_OBS": f"{gestion:%d/%m/%Y}" if pd.notna(gestion) else "",
            "OBSERVACIÓN": _texto(r["OBSERVACION"]),
        })
    return filas


def _saludo(ahora):
    if ahora.hour < 12:
        return "buenos días"
    return "buenas tardes" if ahora.hour < 19 else "buenas noches"


def asunto(fecha):
    return f"ECOPETROL | Control Operativo – Backlog Diario - Seguimiento {fecha:%d/%m/%Y}"


# Etiqueta de STATUS en el correo enviado desde PODEX (paleta del sistema):
# (fondo, texto).
ETIQUETAS_STATUS = {
    "IN PROGRESS": ("#CCD32A", "#17342f"),
    "WORK IN PROGRESS": ("#CCD32A", "#17342f"),
    "PENDING CUSTOMER": ("#F7DB17", "#17342f"),
    "PENDING VENDOR": ("#FF5F00", "#ffffff"),
    "OPEN": ("#2f6db5", "#ffffff"),
    "SUSPENDED": ("#C3C5C6", "#17342f"),
}


def correo_para_enviar(filas, product_owners, destinatario, fecha, ahora):
    """(asunto, texto, html) del seguimiento con el diseño del correo de
    backlog: marca Ecopetrol, tarjetas por sección y la paleta del sistema."""
    from correo import MARCA_ECOPETROL, _plantilla, _tarjeta, _vinetas

    p = "color:#17342f;font-size:14px;line-height:1.6;margin:0 0 10px;"
    celda = ("font-family:'Segoe UI',Arial,sans-serif;font-size:11px;color:#17342f;padding:6px 7px;"
             "border-bottom:1px solid #e0e5e5;vertical-align:top;")
    encabezado = (celda + "background:#f4f5f7;color:#5f6d69;font-size:10px;font-weight:700;"
                  "text-transform:uppercase;letter-spacing:.3px;")
    etiqueta = "display:inline-block;padding:2px 6px;border-radius:4px;font-weight:700;white-space:nowrap;"

    saludo = (f"{html.escape(destinatario.strip())}, {_saludo(ahora)}:" if destinatario.strip()
              else f"{_saludo(ahora).capitalize()}:")
    tarjetas, texto_tablas = [], []
    for origen, titulo in SECCIONES.items():
        filas_seccion = [f for f in filas if f["ORIGEN"] == origen]
        if not filas_seccion:
            if origen == "DETALLE_GENERAL":
                tarjetas.append(_tarjeta(titulo.title(), f'<p style="{p}">Sin solicitudes abiertas.</p>'))
            continue
        tabla = ['<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
                 'style="border-collapse:collapse;"><tr>']
        tabla += [f'<td style="{encabezado}">{c}</td>' for c in
                  ["Solicitud", "Categoría", "Status", "Apertura", "Rango", "Subservicio",
                   "Product Owner", "# Días", "Última gestión"]]
        tabla.append("</tr>")
        for f in filas_seccion:
            fondo, color = ETIQUETAS_STATUS.get(f["STATUS"].upper(), ("#eef4e6", "#17342f"))
            dias = f["# DÍAS"]
            fondo_dias, color_dias = (("#F7DB17", "#17342f") if dias is not None and dias <= 5
                                      else ("#FF5F00", "#ffffff"))
            obs = (f'<strong>{f["FECHA_OBS"]}:</strong> {html.escape(f["OBSERVACIÓN"])}' if f["OBSERVACIÓN"]
                   else '<em style="color:#5f6d69;">Sin gestión registrada</em>')
            tabla.append(
                "<tr>"
                f'<td style="{celda}width:18%;">{html.escape(f["SOLICITUD"])}</td>'
                f'<td style="{celda}width:12%;">{html.escape(f["CATEGORIA"])}</td>'
                f'<td style="{celda}"><span style="{etiqueta}background:{fondo};color:{color};">'
                f'{html.escape(f["STATUS"])}</span></td>'
                f'<td style="{celda}white-space:nowrap;">{f["FECHA_APERTURA"]}</td>'
                f'<td style="{celda}white-space:nowrap;">{html.escape(f["RANGO_TIEMPO"])}</td>'
                f'<td style="{celda}">{html.escape(f["SUBSERVICIO_AFECTADO"])}</td>'
                f'<td style="{celda}">{html.escape(f["PRODUCT_OWNER"])}</td>'
                f'<td style="{celda}text-align:center;">' + ("" if dias is None else
                    f'<span style="{etiqueta}background:{fondo_dias};color:{color_dias};">{dias}</span>') + "</td>"
                f'<td style="{celda}width:28%;">{obs}</td>'
                "</tr>"
            )
            texto_tablas.append(f'  - {f["SOLICITUD"]} | {f["STATUS"]} | {dias} días | '
                                f'{f["OBSERVACIÓN"] or "Sin gestión registrada"}')
        tabla.append("</table>")
        tarjetas.append(_tarjeta(titulo.title(), "".join(tabla)))

    nombres = [_nombre_propio(po) for po in product_owners]
    separador = '<tr><td height="24" style="height:24px;font-size:0;line-height:0;">&nbsp;</td></tr>'
    cuerpo = f"""  <tr><td style="padding:0 32px;">
    <p style="{p}">{saludo}</p>
    <p style="{p}">Envío el estado actual del seguimiento a las solicitudes de los siguientes Product Owner, de acuerdo con el archivo de Control Operativo suministrado el día <strong>{fecha:%d/%m/%Y}</strong>:</p>
    {_vinetas([html.escape(n) for n in nombres])}
  </td></tr>
  {separador.join(f'<tr><td style="padding:0 32px;">{t}</td></tr>' for t in tarjetas)}
  <tr><td height="28" style="height:28px;font-size:0;line-height:0;">&nbsp;</td></tr>

"""
    html_correo = _plantilla(f"Seguimiento {fecha:%d/%m/%Y}", cuerpo, ancho=900, marca=MARCA_ECOPETROL,
                             subtitulo="Control Operativo – Seguimiento de solicitudes abiertas")
    texto = (f"{saludo}\n\nEnvío el estado actual del seguimiento a las solicitudes de los siguientes "
             f"Product Owner, de acuerdo con el archivo de Control Operativo suministrado el día "
             f"{fecha:%d/%m/%Y}:\n" + "\n".join(f"  • {n}" for n in nombres) + "\n\n" + "\n".join(texto_tablas) + "\n")
    return asunto(fecha), texto, html_correo


def correo_excel(filas, product_owners, destinatario, fecha, ahora):
    """El mismo seguimiento en Excel: encabezado del correo y una tabla por sección."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    libro = Workbook()
    ws = libro.active
    ws.title = "SEGUIMIENTO"
    ws.sheet_view.showGridLines = False

    delgado = Side(style="thin", color="7F7F7F")
    borde = Border(left=delgado, right=delgado, top=delgado, bottom=delgado)
    arriba = Alignment(vertical="top", wrap_text=True)
    normal = Font(name="Calibri", size=10)

    ws.cell(1, 1, asunto(fecha)).font = Font(name="Calibri", size=13, bold=True)
    ws.cell(2, 1, f"Product Owner: {', '.join(_nombre_propio(po) for po in product_owners)}").font = normal
    ws.cell(3, 1, f"Archivo de Control Operativo del {fecha:%d/%m/%Y} · Generado el {ahora:%d/%m/%Y %H:%M}").font = normal

    fila = 5
    for origen, titulo in SECCIONES.items():
        filas_seccion = [f for f in filas if f["ORIGEN"] == origen]
        ws.cell(fila, 1, titulo).font = Font(name="Calibri", size=11, bold=True, underline="single")
        fila += 1
        if not filas_seccion:
            ws.cell(fila, 1, "Sin solicitudes abiertas.").font = normal
            fila += 2
            continue
        for c, (columna, _) in enumerate(COLUMNAS, start=1):
            celda = ws.cell(fila, c, columna)
            celda.font, celda.border, celda.alignment = normal, borde, arriba
            celda.fill = PatternFill("solid", fgColor="D9D9D9")
        fila += 1
        for f in filas_seccion:
            obs = f'{f["FECHA_OBS"]}: {f["OBSERVACIÓN"]}' if f["OBSERVACIÓN"] else "Sin gestión registrada"
            valores = [f["SOLICITUD"], f["CATEGORIA"], f["STATUS"], f["FECHA_APERTURA"],
                       f["RANGO_TIEMPO"], f["SUBSERVICIO_AFECTADO"], f["PRODUCT_OWNER"], f["# DÍAS"], obs]
            for c, valor in enumerate(valores, start=1):
                celda = ws.cell(fila, c, valor)
                celda.font, celda.border, celda.alignment = normal, borde, arriba
            color = COLORES_STATUS.get(f["STATUS"].upper())
            if color:
                ws.cell(fila, 3).fill = PatternFill("solid", fgColor=color)
            fila += 1
        fila += 1

    for c, ancho in enumerate([42, 30, 16, 16, 12, 22, 24, 8, 70], start=1):
        ws.column_dimensions[get_column_letter(c)].width = ancho

    salida = io.BytesIO()
    libro.save(salida)
    return salida.getvalue()


# ============================================================
# REPORTE
# ============================================================
def reporte_seguimiento(usuario):
    try:
        pods = obtener_pods_usuario(usuario)
        abiertas = obtener_abiertas_usuario(usuario)
        fecha_archivo = fecha_ultimo_archivo()
    except Exception as e:
        st.error("❌ No fue posible consultar las solicitudes abiertas.")
        st.exception(e)
        return

    if not pods:
        st.info("ℹ️ No tiene POD asignados. Solicite al administrador que se los asigne desde el módulo Usuarios.")
        return

    ahora = datetime.now(ZONA).replace(tzinfo=None)

    # Sin filtros: todos los Product Owner de los POD del usuario, saludo
    # general y la fecha de la última carga del archivo de Control Operativo.
    seleccion = pods
    destinatario = ""
    fecha = fecha_archivo or ahora.date()

    elegidos = {" ".join(str(po).split()).upper() for po in seleccion}
    datos = abiertas[abiertas["PRODUCT_OWNER"].map(lambda po: " ".join(str(po or "").split()).upper()).isin(elegidos)]
    filas = preparar_filas(datos, ahora.date())

    dias = [f["# DÍAS"] for f in filas if f["# DÍAS"] is not None]
    a, b, c, d = st.columns(4)
    a.metric("Solicitudes abiertas", len(filas))
    b.metric("0-5 días", sum(1 for x in dias if x <= 5))
    c.metric("Más de 5 días", sum(1 for x in dias if x > 5))
    d.metric("Sin gestión registrada", sum(1 for f in filas if not f["OBSERVACIÓN"]))


    with st.container(border=True):
        c_titulo, c_acciones = st.columns([4, 1], vertical_alignment="center")
        with c_titulo:
            st.markdown('<div class="podex-section-title">✉️ Seguimiento de solicitudes abiertas</div>', unsafe_allow_html=True)
            st.markdown('<div class="podex-section-caption">Solo solicitudes sin FECHA_CIERRE ni CODIGO_CIERRE · '
                        'Observación = última gestión registrada en PODEX · # DÍAS calculado a hoy.</div>',
                        unsafe_allow_html=True)
        with c_acciones:
            with st.container(key="acciones_rep_seguimiento", horizontal=True,
                              horizontal_alignment="right", vertical_alignment="center"):
                enviar = st.button("", icon=":material/send:", key="btn_ok_rep_enviar_seguimiento",
                                   help="Enviar por correo (con vista previa)")
                st.download_button(
                    "",
                    data=correo_excel(filas, seleccion, destinatario, fecha, ahora),
                    file_name=f"Seguimiento_backlog_{fecha:%d%m%Y}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    icon=":material/download:",
                    key="btn_rep_descargar_seguimiento",
                    help="Descargar en Excel",
                )

        if enviar:
            from envios import programar_envio  # aquí para evitar la importación circular

            asunto_correo, texto, html_correo = correo_para_enviar(filas, seleccion, destinatario, fecha, ahora)
            programar_envio(
                "Seguimiento de solicitudes abiertas", asunto_correo, texto, html_correo,
                envio="SEGUIMIENTO",
                adjuntos=[(f"Seguimiento_backlog_{fecha:%d%m%Y}.xlsx",
                           correo_excel(filas, seleccion, destinatario, fecha, ahora))],
                aviso_ok="Correo de seguimiento enviado",
            )
            st.rerun()

        # Misma cuadrícula de Gestión de Solicitudes, con los títulos de columna del correo.
        for origen, titulo in SECCIONES.items():
            filas_seccion = [f for f in filas if f["ORIGEN"] == origen]
            st.markdown(f'<div class="podex-section-title" style="margin-top:14px">{titulo.title()}</div>',
                        unsafe_allow_html=True)
            if not filas_seccion:
                st.caption("Sin solicitudes abiertas.")
                continue
            tabla = pd.DataFrame({
                "SOLICITUD": [f["SOLICITUD"] for f in filas_seccion],
                "CATEGORÍA": [f["CATEGORIA"] for f in filas_seccion],
                "STATUS": [f["STATUS"] for f in filas_seccion],
                "APERTURA": [f["FECHA_APERTURA"] for f in filas_seccion],
                "RANGO": [f["RANGO_TIEMPO"] for f in filas_seccion],
                "SUBSERVICIO": [f["SUBSERVICIO_AFECTADO"] for f in filas_seccion],
                "PRODUCT OWNER": [f["PRODUCT_OWNER"] for f in filas_seccion],
                "# DÍAS": [f["# DÍAS"] for f in filas_seccion],
                "ÚLTIMA GESTIÓN": [f'{f["FECHA_OBS"]}: {f["OBSERVACIÓN"]}' if f["OBSERVACIÓN"]
                                   else "Sin gestión registrada" for f in filas_seccion],
            })
            # STATUS con su color de fondo (los mismos colores del Excel).
            estilo = tabla.style.map(
                lambda v: (f"background-color:#{COLORES_STATUS[str(v).upper()]}"
                           if str(v).upper() in COLORES_STATUS else ""),
                subset=["STATUS"],
            )
            st.dataframe(
                estilo,
                key=f"tabla_seguimiento_{origen}",
                hide_index=True,
                width="stretch",
                height=min(38 + 35 * len(tabla), 640),
                column_config={
                    "SOLICITUD": st.column_config.TextColumn("SOLICITUD", width=220),
                    "CATEGORÍA": st.column_config.TextColumn("CATEGORÍA", width=140),
                    "STATUS": st.column_config.TextColumn("STATUS", width=115),
                    "APERTURA": st.column_config.TextColumn("APERTURA", width=105),
                    "RANGO": st.column_config.TextColumn("RANGO", width=70),
                    "SUBSERVICIO": st.column_config.TextColumn("SUBSERVICIO", width=130),
                    "PRODUCT OWNER": st.column_config.TextColumn("PRODUCT OWNER", width=190),
                    "# DÍAS": st.column_config.NumberColumn("# DÍAS", width=55),
                    "ÚLTIMA GESTIÓN": st.column_config.TextColumn("ÚLTIMA GESTIÓN", width=320),
                },
            )
        st.caption("✈ envía el correo desde PODEX (con vista previa y el diseño del correo de backlog). "
                   "Colores de STATUS: amarillo = In Progress / Work In Progress · verde = Pending Customer · "
                   "naranja = Pending Vendor · azul = Open · gris = Suspended.")
