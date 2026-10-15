"""
Correos de PODEX, todos con el diseño del correo de backlog (marca Ecopetrol):
bienvenida a los usuarios nuevos, backlog de cada carga de solicitudes y
seguimiento de solicitudes abiertas (el cuerpo de este último se arma en
seguimiento.py). Antes de enviarse pasan por la vista previa de envios.py.

Se usa un servidor SMTP configurado en los secretos de Streamlit:

    [email]
    smtp_host = "smtp.office365.com"     # o smtp.gmail.com, etc.
    smtp_port = 587                      # 587 (STARTTLS) o 465 (SSL)
    usuario = "notificaciones@dominio.com"
    password = "..."
    remitente = "PODEX <notificaciones@dominio.com>"   # opcional
    app_url = "https://podexweb.streamlit.app"         # opcional
"""

import smtplib
import ssl
from datetime import datetime
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, parseaddr
from html import escape
from pathlib import Path

import base64

import streamlit as st

from excel_web import ORDEN_RANGOS, _orden_rango, calcular_tabla_jdu

NOMBRE_SISTEMA = "PODEX"
DESCRIPCION_SISTEMA = "Sistema Integrado de Gestión de Peticiones, Incidentes y Vulnerabilidades"
APP_URL_DEFECTO = "https://podexweb.streamlit.app"
LOGO = Path(__file__).with_name("Logo_PODEX_correo.png")
LOGO_ECP = Path(__file__).with_name("Logo_ECP.png")

# Marca del encabezado y el pie de cada correo.
MARCA_PODEX = {
    "logo": LOGO, "cid": "logo_podex", "alt": NOMBRE_SISTEMA, "ancho_logo": 170,
    "subtitulo": DESCRIPCION_SISTEMA,
    "pie_titulo": NOMBRE_SISTEMA, "pie_subtitulo": DESCRIPCION_SISTEMA,
    "copyright": NOMBRE_SISTEMA,
}
MARCA_ECOPETROL = {
    "logo": LOGO_ECP, "cid": "logo_ecp", "alt": "ECOPETROL", "ancho_logo": 240,
    "subtitulo": "Control Operativo – Backlog Diario",
    "pie_titulo": "ECOPETROL S.A", "pie_subtitulo": "Jefatura de Soluciones Digitales Upstream",
    "copyright": "",
}

# Paleta corporativa usada en la aplicación.
VERDE_OSCURO = "#004236"
VERDE_APP = "#0b5b4d"
LIMA = "#CCD32A"
AMARILLO = "#F7DB17"
GRIS_TEXTO = "#5f6d69"
FONDO = "#f4f5f7"
BORDE = "#e0e5e5"

DESCRIPCION_PERFILES = {
    "ADMINISTRADOR": (
        "Acceso completo: consulta de todas las solicitudes, carga de solicitudes "
        "desde Excel y administración de usuarios."
    ),
    "OPERADOR": (
        "Consulta y gestión de las solicitudes de los PODs asignados: registrar "
        "gestiones, ver el historial y actualizar el estado o el cierre."
    ),
}


def configuracion_correo():
    """Devuelve la sección [email] de los secretos o None si no está configurada."""
    try:
        config = dict(st.secrets["email"])
    except (KeyError, FileNotFoundError):
        return None
    if not all(config.get(c) for c in ("smtp_host", "smtp_port", "usuario", "password")):
        return None
    return config


def _fila(etiqueta, valor):
    return (
        f'<tr><td style="padding:8px 0;border-bottom:1px solid {BORDE};color:{GRIS_TEXTO};'
        f'font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.4px;width:42%;">'
        f'{escape(etiqueta)}</td>'
        f'<td style="padding:8px 0;border-bottom:1px solid {BORDE};color:#17342f;font-size:14px;">'
        f'{valor}</td></tr>'
    )


def _paso(numero, texto):
    return (
        f'<tr><td style="vertical-align:top;padding:6px 12px 6px 0;">'
        f'<div style="width:26px;height:26px;border-radius:50%;background:{VERDE_APP};color:#fff;'
        f'font-size:13px;font-weight:700;text-align:center;line-height:26px;">{numero}</div></td>'
        f'<td style="padding:6px 0;color:#17342f;font-size:14px;line-height:1.5;">{texto}</td></tr>'
    )


def _plantilla(titulo, cuerpo, ancho=600, marca=MARCA_PODEX, subtitulo=None):
    """Estructura común de los correos: franja de colores, logo, título,
    subtítulo (el de la marca si no se indica otro), cuerpo y pie con la
    marca recibida (PODEX por defecto)."""
    anio = datetime.now().year
    copyright = f"© {anio} {marca['copyright']}".strip()
    return f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:{FONDO};font-family:'Segoe UI',Arial,sans-serif;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{FONDO};padding:24px 12px;">
<tr><td align="center">
<table role="presentation" width="{ancho}" cellpadding="0" cellspacing="0" style="max-width:{ancho}px;width:100%;background:#fff;border-radius:10px;overflow:hidden;border:1px solid {BORDE};">

  <tr><td style="height:6px;background:linear-gradient(90deg,{AMARILLO},{LIMA},{VERDE_OSCURO});background-color:{LIMA};font-size:0;line-height:0;">&nbsp;</td></tr>
  <tr><td align="center" style="padding:26px 24px 10px;">
    <img src="cid:{marca['cid']}" width="{marca['ancho_logo']}" alt="{marca['alt']}" style="display:block;border:0;width:{marca['ancho_logo']}px;height:auto;">
  </td></tr>
  <tr><td align="center" style="padding:0 24px 22px;">
    <div style="color:{VERDE_OSCURO};font-size:22px;font-weight:800;">{titulo}</div>
    <div style="color:{GRIS_TEXTO};font-size:12px;margin-top:4px;">{subtitulo or marca['subtitulo']}</div>
  </td></tr>

{cuerpo}  <tr><td style="background:{VERDE_OSCURO};padding:16px 24px;" align="center">
    <div style="color:#fff;font-size:13px;font-weight:700;">{marca['pie_titulo']}</div>
    <div style="color:#cfe3dc;font-size:11px;margin-top:2px;">{marca['pie_subtitulo']}</div>
    <div style="color:#9fbfb5;font-size:10px;margin-top:8px;">Este es un mensaje automático, por favor no responda a este correo. {copyright}</div>
  </td></tr>
  <tr><td style="height:4px;background:{LIMA};font-size:0;line-height:0;">&nbsp;</td></tr>

</table>
</td></tr></table>
</body></html>"""


def construir_correo_bienvenida(nombre, usuario, correo, perfil, pods, contrasena,
                                app_url, descripcion_perfil=None):
    """Devuelve (asunto, texto_plano, html) del correo de bienvenida."""
    perfil = (perfil or "").upper()
    descripcion_perfil = descripcion_perfil or DESCRIPCION_PERFILES.get(perfil, "")
    pods_texto = ", ".join(f"{i} · {n}" for i, n in pods) if pods else "Sin PODs asignados"
    pods_html = "<br>".join(f"{escape(i)} · {escape(n)}" for i, n in pods) if pods else "Sin PODs asignados"
    anio = datetime.now().year

    asunto = f"Bienvenido a {NOMBRE_SISTEMA} · Datos de acceso de su cuenta"

    texto = f"""Hola {nombre},

Se ha creado su cuenta en {NOMBRE_SISTEMA} - {DESCRIPCION_SISTEMA}.

DATOS DE SU CUENTA
- Dirección de acceso: {app_url}
- Nombre: {nombre}
- Usuario: {usuario}
- Correo de acceso: {correo}
- Contraseña temporal: {contrasena}
- Perfil: {perfil}{f" ({descripcion_perfil})" if descripcion_perfil else ""}
- PODs asignados: {pods_texto}

PROCEDIMIENTO DE ACCESO
1. Ingrese a {app_url}
2. Escriba su correo de acceso y la contraseña temporal, y pulse "Ingresar".
3. Use el menú lateral para consultar y gestionar las solicitudes.
4. Al terminar, cierre la sesión con el botón circular de la parte superior derecha.

RECOMENDACIONES
- No comparta su usuario ni su contraseña.
- Si necesita cambiar la contraseña o no puede ingresar, comuníquese con el administrador del sistema.

{NOMBRE_SISTEMA} · {DESCRIPCION_SISTEMA}
Este es un mensaje automático, por favor no responda a este correo.
© {anio} {NOMBRE_SISTEMA}
"""

    filas = "".join([
        _fila("Dirección de acceso",
              f'<a href="{escape(app_url)}" style="color:{VERDE_APP};font-weight:700;">{escape(app_url)}</a>'),
        _fila("Nombre", escape(nombre)),
        _fila("Usuario", f"<strong>{escape(usuario)}</strong>"),
        _fila("Correo de acceso", escape(correo)),
        _fila("Contraseña temporal",
              f'<span style="font-family:Consolas,monospace;background:{FONDO};padding:3px 8px;'
              f'border-radius:4px;border:1px solid {BORDE};">{escape(contrasena)}</span>'),
        _fila("Perfil",
              f"<strong>{escape(perfil)}</strong>"
              + (f'<br><span style="color:{GRIS_TEXTO};font-size:12px;">{escape(descripcion_perfil)}</span>'
                 if descripcion_perfil else "")),
        _fila("PODs asignados", pods_html),
    ])

    pasos = "".join([
        _paso(1, f'Ingrese a <a href="{escape(app_url)}" style="color:{VERDE_APP};font-weight:700;">'
                 f'{escape(app_url)}</a>.'),
        _paso(2, "Escriba su <strong>correo de acceso</strong> y la <strong>contraseña temporal</strong>, "
                 "y pulse <strong>Ingresar</strong>."),
        _paso(3, "Use el menú lateral para consultar y gestionar las solicitudes."),
        _paso(4, "Al terminar, cierre la sesión con el botón circular de la parte superior derecha."),
    ])

    p = "color:#17342f;font-size:14px;line-height:1.6;margin:0 0 10px;"
    cuerpo = f"""  <tr><td style="padding:0 32px;">
    <p style="{p}">Hola <strong>{escape(nombre)}</strong>,</p>
    <p style="{p}">Se ha creado su cuenta en <strong>{NOMBRE_SISTEMA}</strong> · {DESCRIPCION_SISTEMA}. A continuación encontrará la información necesaria para ingresar al sistema.</p>
  </td></tr>

  <tr><td style="padding:4px 32px 0;">{_tarjeta("Datos de su cuenta",
      f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0">{filas}</table>')}</td></tr>
  <tr><td height="24" style="height:24px;font-size:0;line-height:0;">&nbsp;</td></tr>

  <tr><td style="padding:0 32px;">{_tarjeta("Procedimiento de acceso",
      f'<table role="presentation" cellpadding="0" cellspacing="0">{pasos}</table>')}</td></tr>

  <tr><td align="center" style="padding:22px 32px 6px;">
    <a href="{escape(app_url)}" style="display:inline-block;background:{VERDE_OSCURO};color:#fff;text-decoration:none;
       font-size:14px;font-weight:700;padding:12px 34px;border-radius:24px;">Ingresar a {NOMBRE_SISTEMA}</a>
  </td></tr>

  <tr><td style="padding:18px 32px 28px;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" bgcolor="#fffbea"
           style="border-collapse:separate;background:#fffbea;border:1px solid {AMARILLO};border-radius:8px;">
      <tr><td style="padding:12px 16px 6px;">
        <div style="color:{VERDE_OSCURO};font-size:14px;font-weight:800;margin:0 0 4px;">Recomendaciones de seguridad</div>
        {_vinetas([
            "No comparta su usuario ni su contraseña.",
            "Si necesita cambiar la contraseña o no puede ingresar, comuníquese con el administrador del sistema.",
        ])}
      </td></tr>
    </table>
  </td></tr>

"""
    html = _plantilla(f"¡Bienvenido a {NOMBRE_SISTEMA}!", cuerpo, ancho=900, marca=MARCA_ECOPETROL,
                      subtitulo=f"{NOMBRE_SISTEMA} · {DESCRIPCION_SISTEMA}")

    return asunto, texto, html


def _armar_mensaje(config, destinatario, asunto, texto, html, marca=MARCA_PODEX):
    """Mensaje MIME con versión de texto, HTML y el logo incrustado."""
    remitente = config.get("remitente") or formataddr((NOMBRE_SISTEMA, config["usuario"]))
    nombre_rem, correo_rem = parseaddr(remitente)

    mensaje = MIMEMultipart("related")
    mensaje["Subject"] = asunto
    mensaje["From"] = formataddr((nombre_rem or NOMBRE_SISTEMA, correo_rem or config["usuario"]))
    mensaje["To"] = destinatario

    alternativa = MIMEMultipart("alternative")
    alternativa.attach(MIMEText(texto, "plain", "utf-8"))
    alternativa.attach(MIMEText(html, "html", "utf-8"))
    mensaje.attach(alternativa)

    if marca["logo"].exists():
        logo = MIMEImage(marca["logo"].read_bytes(), _subtype="png")
        logo.add_header("Content-ID", f"<{marca['cid']}>")
        logo.add_header("Content-Disposition", "inline", filename=marca["logo"].name)
        mensaje.attach(logo)

    return mensaje


def _servidor_smtp(config):
    """Conexión SMTP autenticada (465 = SSL; otro puerto = STARTTLS)."""
    host = config["smtp_host"]
    puerto = int(config["smtp_port"])
    contexto = ssl.create_default_context()

    if puerto == 465:
        servidor = smtplib.SMTP_SSL(host, puerto, context=contexto, timeout=30)
    else:
        servidor = smtplib.SMTP(host, puerto, timeout=30)
        servidor.starttls(context=contexto)
    servidor.login(config["usuario"], config["password"])
    return servidor


# ============================================================
# CORREO DE BACKLOG DESPUÉS DE CADA CARGA
# ============================================================


# Colores de la tabla dinámica con la paleta corporativa del sistema.
VERDE_TOTAL = "#eef4e6"      # columnas de total por tipo
AMARILLO_CELDA = "#F7DB17"   # 0-5 días (dentro de meta cercana)
NARANJA_CELDA = "#FF5F00"    # más de 5 días

TEXTO_BACKLOG = """Les comparto el archivo adjunto ({nombre_archivo}) para lograr gestionar y seguir reduciendo al máximo el tiempo de gestión de los incidentes y requerimientos de la JDU para el indicador global de salud del servicio.

Para recordar que las metas son:
  • IMs (Incidentes) = 24 horas calendario desde la fecha inicio a cierre satisfactorio.
  • RFs (Requerimientos) = 48 horas calendario desde la fecha inicio a cierre satisfactorio.
Acciones que se sugieren realizar ASAP:
  • Revisar casos con aliados para gestionar el cierre en SM.
  • Revisar casos con funcionarios de ECP para gestionar el cierre en SM.
  • Gestionar con aliados, automatizaciones en flujos de gestión de accesos y demás requerimientos, que permitan seguir disminuyendo los tiempos que a hoy tenemos.
"""


def nombre_backlog(nombre_archivo):
    """'29092026.xlsx' -> '29092026 - Backlog' (sin duplicar 'Backlog' si el
    archivo ya lo trae en el nombre)."""
    base = Path(nombre_archivo).stem.strip()
    return base if base.lower().endswith("backlog") else f"{base} - Backlog"


def _tabla_dinamica(registros):
    """Tabla dinámica HTML: Product Owner por filas; TIPO x RANGTIEMPO por
    columnas, con totales por tipo y total general (como en Excel), con los
    colores del sistema. registros: [(product_owner, tipo, rango), ...]."""
    conteo, tipos, filas, total_po = calcular_tabla_jdu(registros)

    celda = (f"font-family:'Segoe UI',Arial,sans-serif;font-size:12px;color:#17342f;"
             f"padding:6px 8px;border-bottom:1px solid {BORDE};white-space:nowrap;")
    enc = (f"{celda}background:{FONDO};color:{GRIS_TEXTO};font-size:10px;font-weight:700;"
           f"text-transform:uppercase;letter-spacing:.3px;")
    num = f"{celda}text-align:right;"
    total_tipo = f"{num}background:{VERDE_TOTAL};font-weight:700;color:{VERDE_OSCURO};"

    # Encabezados: tipos (con su total) y rangos de días.
    h1 = f'<td rowspan="2" style="{enc}vertical-align:bottom;">Product Owner</td>'
    h2 = ""
    for tipo, rangos in tipos.items():
        h1 += (f'<td colspan="{len(rangos)}" align="center" style="{enc}text-align:center;'
               f'color:{VERDE_OSCURO};border-bottom:2px solid {LIMA};">{escape(str(tipo))}</td>')
        h1 += (f'<td rowspan="2" style="{enc}background:{VERDE_TOTAL};color:{VERDE_OSCURO};'
               f'text-align:right;vertical-align:bottom;">Total<br>{escape(str(tipo).lower())}</td>')
        h2 += "".join(f'<td style="{enc}text-align:right;">{escape(str(r))}</td>' for r in rangos)
    h1 += (f'<td rowspan="2" style="{enc}text-align:right;vertical-align:bottom;'
           f'color:{VERDE_OSCURO};">Total<br>general</td>')

    cuerpo = ""
    for po in filas:
        fila = f'<td style="{celda}">{escape(str(po))}</td>'
        for tipo, rangos in tipos.items():
            subtotal = 0
            for r in rangos:
                c = conteo.get((po, tipo, r), 0)
                subtotal += c
                if not c:
                    fila += f'<td style="{num}"></td>'
                elif r == "0-5 días":
                    fila += f'<td style="{num}background:{AMARILLO_CELDA};font-weight:700;">{c}</td>'
                else:
                    fila += (f'<td style="{num}background:{NARANJA_CELDA};color:#fff;'
                             f'font-weight:700;">{c}</td>')
            fila += f'<td style="{total_tipo}">{subtotal or ""}</td>'
        fila += f'<td style="{num}font-weight:700;">{total_po[po]}</td>'
        cuerpo += f"<tr>{fila}</tr>"

    pie = (f"font-family:'Segoe UI',Arial,sans-serif;font-size:12px;font-weight:700;"
           f"color:#fff;background:{VERDE_OSCURO};padding:7px 8px;white-space:nowrap;")
    total = f'<td style="{pie}">Total general</td>'
    for tipo, rangos in tipos.items():
        for r in rangos:
            total += (f'<td style="{pie}text-align:right;">'
                      f'{sum(conteo.get((po, tipo, r), 0) for po in filas)}</td>')
        total += f'<td style="{pie}text-align:right;">{sum(c for (_, t, _), c in conteo.items() if t == tipo)}</td>'
    total += f'<td style="{pie}text-align:right;">{sum(conteo.values())}</td>'

    return (
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        f'style="border-collapse:collapse;border:1px solid {BORDE};">'
        f"<tr>{h1}</tr><tr>{h2}</tr>{cuerpo}<tr>{total}</tr></table>"
    )


def _tarjeta(titulo, contenido):
    """Tarjeta con borde lima y franja superior, armada con una tabla para que
    Outlook (que ignora box-shadow y desalinea bordes de <div>) la muestre igual."""
    return (
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" bgcolor="#ffffff" '
        f'style="border-collapse:separate;border:1px solid #9ec91f;border-top:3px solid {LIMA};'
        f'border-radius:8px;background:#ffffff;">'
        f'<tr><td style="padding:14px 18px 18px;">'
        f'<div style="color:{VERDE_OSCURO};font-size:15px;font-weight:800;margin:0 0 10px;">'
        f'{escape(titulo)}</div>{contenido}</td></tr></table>'
    )


def _vinetas(items):
    """Lista con viñetas en tabla (Outlook desalinea los <ul>/<li>)."""
    filas = "".join(
        f'<tr><td valign="top" width="16" style="color:#17342f;font-size:14px;line-height:1.55;'
        f'padding:0 0 4px;">&#8226;</td>'
        f'<td valign="top" style="color:#17342f;font-size:14px;line-height:1.55;padding:0 0 4px;">'
        f'{item}</td></tr>'
        for item in items
    )
    return (f'<table role="presentation" cellpadding="0" cellspacing="0" '
            f'style="margin:0 0 8px 6px;">{filas}</table>')


def _leyenda():
    """Leyenda de colores con celdas de tabla (Outlook no muestra los <span>
    con display:inline-block)."""
    texto = f"color:{GRIS_TEXTO};font-size:11px;padding:0 12px 0 5px;"
    cuadro = "width:10px;height:10px;font-size:0;line-height:0;"
    return (
        f'<table role="presentation" cellpadding="0" cellspacing="0" style="margin-top:8px;"><tr>'
        f'<td width="10" height="10" bgcolor="{AMARILLO_CELDA}" style="{cuadro}background:{AMARILLO_CELDA};">&nbsp;</td>'
        f'<td style="{texto}">0-5 días</td>'
        f'<td width="10" height="10" bgcolor="{NARANJA_CELDA}" style="{cuadro}background:{NARANJA_CELDA};">&nbsp;</td>'
        f'<td style="{texto}">Más de 5 días</td>'
        f'</tr></table>'
    )


def _tabla_texto(registros):
    conteo = {}
    for po, tipo, rango in registros:
        conteo[(po, tipo, rango)] = conteo.get((po, tipo, rango), 0) + 1
    return "\n".join(
        f"  - {po} · {tipo} · {rango}: {c}"
        for (po, tipo, rango), c in sorted(conteo.items(), key=lambda x: (x[0][0], x[0][1], _orden_rango(x[0][2])))
    )


def construir_correo_backlog(resumen):
    """Devuelve (asunto, texto_plano, html) del correo de backlog.

    resumen: dict con archivo (nombre del Excel cargado), usuario_carga,
    general y funcional (listas de (product_owner, tipo, rango) de las
    solicitudes cargadas).
    """
    nombre_archivo = nombre_backlog(resumen["archivo"])
    asunto = nombre_archivo
    intro = TEXTO_BACKLOG.format(nombre_archivo=nombre_archivo)

    texto = intro + "\nDETALLE GENERAL\n" + (_tabla_texto(resumen["general"]) or "  Sin solicitudes")
    if resumen["funcional"]:
        texto += "\n\nGRUPO FUNCIONAL ECOPETROL\n" + _tabla_texto(resumen["funcional"])
    texto += "\n"

    p = "color:#17342f;font-size:14px;line-height:1.6;margin:0 0 10px;"
    leyenda = _leyenda()

    tarjeta_general = _tarjeta(
        "Detalle General",
        (_tabla_dinamica(resumen["general"]) + leyenda) if resumen["general"]
        else f'<p style="{p}">Sin solicitudes en DETALLE_GENERAL.</p>'
    )
    tarjeta_funcional = (
        _tarjeta("Grupo Funcional Ecopetrol", _tabla_dinamica(resumen["funcional"]) + leyenda)
        if resumen["funcional"] else ""
    )

    cuerpo = f"""  <tr><td style="padding:0 32px;">
    <p style="{p}">Les comparto el archivo adjunto (<strong>{escape(nombre_archivo)}</strong>) para lograr gestionar y seguir reduciendo al máximo el tiempo de gestión de los incidentes y requerimientos de la JDU para el indicador global de salud del servicio.</p>
  </td></tr>

  <tr><td style="padding:4px 32px 18px;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" bgcolor="#fffbea"
           style="border-collapse:separate;background:#fffbea;border:1px solid {AMARILLO};border-radius:8px;">
      <tr><td style="padding:12px 16px 6px;">
        <div style="color:{VERDE_OSCURO};font-size:14px;font-weight:800;margin:0 0 4px;">Para recordar que las metas son:</div>
        {_vinetas([
            "<strong>IMs (Incidentes) = 24 horas calendario</strong> desde la fecha inicio a cierre satisfactorio.",
            "<strong>RFs (Requerimientos) = 48 horas calendario</strong> desde la fecha inicio a cierre satisfactorio.",
        ])}
        <div style="color:{VERDE_OSCURO};font-size:14px;font-weight:800;margin:0 0 4px;">Acciones que se sugieren realizar ASAP:</div>
        {_vinetas([
            "Revisar casos con aliados para gestionar el cierre en SM.",
            "Revisar casos con funcionarios de ECP para gestionar el cierre en SM.",
            "Gestionar con aliados, automatizaciones en flujos de gestión de accesos y demás requerimientos, que permitan seguir disminuyendo los tiempos que a hoy tenemos.",
        ])}
      </td></tr>
    </table>
  </td></tr>

  <tr><td style="padding:0 32px;">{tarjeta_general}</td></tr>
  {f'<tr><td height="24" bgcolor="#ffffff" style="height:24px;background:#ffffff;font-size:0;line-height:0;">&nbsp;</td></tr><tr><td style="padding:0 32px;">{tarjeta_funcional}</td></tr>' if tarjeta_funcional else ""}

  <tr><td height="28" style="height:28px;font-size:0;line-height:0;">&nbsp;</td></tr>

"""
    html = _plantilla(nombre_archivo, cuerpo, ancho=900, marca=MARCA_ECOPETROL)

    return asunto, texto, html


# ============================================================
# ENVÍO Y VISTA PREVIA (comunes a todos los correos)
# ============================================================
def remitente():
    """Remitente configurado ("PODEX <cuenta@...>") o None si no hay correo configurado."""
    config = configuracion_correo()
    if config is None:
        return None
    return config.get("remitente") or formataddr((NOMBRE_SISTEMA, config["usuario"]))


def vista_previa_html(html, marca=MARCA_ECOPETROL):
    """El HTML del correo con el logo incrustado, para mostrarlo en pantalla
    (en el correo real el logo va como imagen adjunta cid:)."""
    if marca["logo"].exists():
        datos = base64.b64encode(marca["logo"].read_bytes()).decode()
        html = html.replace(f"cid:{marca['cid']}", f"data:image/png;base64,{datos}")
    return html


def enviar_correo(asunto, texto, html, para=(), cc=(), cco=(), adjuntos=(), marca=MARCA_ECOPETROL):
    """Envía UN correo con el diseño de PODEX.

    para, cc, cco: listas de correos (CCO no se muestra a los demás). Si no
    hay destinatarios Para, el visible es la propia cuenta de PODEX.
    adjuntos: [(nombre_archivo, bytes)]. Devuelve el número de destinatarios.
    """
    config = configuracion_correo()
    if config is None:
        raise RuntimeError("Falta configurar la sección [email] en los secretos de la aplicación.")

    def limpiar(correos):
        return [c.strip() for c in correos if c and c.strip()]

    para, cc, cco = limpiar(para), limpiar(cc), limpiar(cco)
    if not (para or cc or cco):
        raise ValueError("El correo no tiene destinatarios.")

    _, correo_rem = parseaddr(remitente())
    cuerpo = _armar_mensaje(config, ", ".join(para) or correo_rem or config["usuario"],
                            asunto, texto, html, marca=marca)

    if adjuntos:
        # mixed = [related (texto/HTML + logo incrustado), adjuntos]
        mensaje = MIMEMultipart("mixed")
        for encabezado in ("Subject", "From", "To"):
            mensaje[encabezado] = cuerpo[encabezado]
            del cuerpo[encabezado]
        mensaje.attach(cuerpo)
        for nombre, contenido in adjuntos:
            subtipo = ("vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                       if nombre.lower().endswith(".xlsx") else "octet-stream")
            adjunto = MIMEApplication(contenido, _subtype=subtipo)
            adjunto.add_header("Content-Disposition", "attachment", filename=nombre)
            mensaje.attach(adjunto)
    else:
        mensaje = cuerpo

    if cc:
        mensaje["Cc"] = ", ".join(cc)
    if cco:
        mensaje["Bcc"] = ", ".join(cco)

    # send_message() envía a To + Cc + Bcc y no incluye el encabezado Bcc en el mensaje.
    with _servidor_smtp(config) as servidor:
        servidor.send_message(mensaje)

    return len(set(c.lower() for c in para + cc + cco))
