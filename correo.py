"""
Correos de PODEX: bienvenida a los usuarios nuevos (plantilla PODEX) y
backlog de cada carga de solicitudes a los usuarios Operador activos.

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

import streamlit as st

NOMBRE_SISTEMA = "PODEX"
DESCRIPCION_SISTEMA = "Sistema Integrado de Gestión de Peticiones, Incidentes y Vulnerabilidades"
APP_URL_DEFECTO = "https://podexweb.streamlit.app"
LOGO = Path(__file__).with_name("Logo_PODEX_correo.png")

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


def _plantilla(titulo, cuerpo):
    """Estructura común de los correos: franja de colores, logo, título,
    cuerpo y pie con el nombre del sistema."""
    anio = datetime.now().year
    return f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:{FONDO};font-family:'Segoe UI',Arial,sans-serif;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{FONDO};padding:24px 12px;">
<tr><td align="center">
<table role="presentation" width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background:#fff;border-radius:10px;overflow:hidden;border:1px solid {BORDE};">

  <tr><td style="height:6px;background:linear-gradient(90deg,{AMARILLO},{LIMA},{VERDE_OSCURO});background-color:{LIMA};font-size:0;line-height:0;">&nbsp;</td></tr>
  <tr><td align="center" style="padding:26px 24px 10px;">
    <img src="cid:logo_podex" width="170" alt="{NOMBRE_SISTEMA}" style="display:block;border:0;width:170px;height:auto;">
  </td></tr>
  <tr><td align="center" style="padding:0 24px 22px;">
    <div style="color:{VERDE_OSCURO};font-size:22px;font-weight:800;">{titulo}</div>
    <div style="color:{GRIS_TEXTO};font-size:12px;margin-top:4px;">{DESCRIPCION_SISTEMA}</div>
  </td></tr>

{cuerpo}  <tr><td style="background:{VERDE_OSCURO};padding:16px 24px;" align="center">
    <div style="color:#fff;font-size:13px;font-weight:700;">{NOMBRE_SISTEMA}</div>
    <div style="color:#cfe3dc;font-size:11px;margin-top:2px;">{DESCRIPCION_SISTEMA}</div>
    <div style="color:#9fbfb5;font-size:10px;margin-top:8px;">Este es un mensaje automático, por favor no responda a este correo. © {anio} {NOMBRE_SISTEMA}</div>
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

    cuerpo = f"""  <tr><td style="padding:0 32px;">
    <p style="color:#17342f;font-size:15px;line-height:1.6;margin:0 0 6px;">Hola <strong>{escape(nombre)}</strong>,</p>
    <p style="color:#17342f;font-size:14px;line-height:1.6;margin:0 0 18px;">
      Se ha creado su cuenta en <strong>{NOMBRE_SISTEMA}</strong>. A continuación encontrará la información
      necesaria para ingresar al sistema.</p>
  </td></tr>

  <tr><td style="padding:0 32px 8px;">
    <div style="border:1px solid #9ec91f;border-radius:8px;box-shadow:inset 0 3px 0 {LIMA};padding:16px 18px 8px;">
      <div style="color:{VERDE_OSCURO};font-size:15px;font-weight:800;margin-bottom:6px;">Datos de su cuenta</div>
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0">{filas}</table>
    </div>
  </td></tr>

  <tr><td style="padding:18px 32px 4px;">
    <div style="color:{VERDE_OSCURO};font-size:15px;font-weight:800;margin-bottom:6px;">Procedimiento de acceso</div>
    <table role="presentation" cellpadding="0" cellspacing="0">{pasos}</table>
  </td></tr>

  <tr><td align="center" style="padding:16px 32px 8px;">
    <a href="{escape(app_url)}" style="display:inline-block;background:{VERDE_APP};background:linear-gradient(90deg,{VERDE_APP},#147b66);
       color:#fff;text-decoration:none;font-size:14px;font-weight:700;padding:12px 34px;border-radius:24px;">Ingresar a {NOMBRE_SISTEMA}</a>
  </td></tr>

  <tr><td style="padding:16px 32px 24px;">
    <div style="background:#fffbea;border:1px solid {AMARILLO};border-radius:8px;padding:12px 16px;color:#5a4a00;font-size:13px;line-height:1.55;">
      <strong>Recomendaciones de seguridad</strong><br>
      • No comparta su usuario ni su contraseña.<br>
      • Si necesita cambiar la contraseña o no puede ingresar, comuníquese con el administrador del sistema.
    </div>
  </td></tr>

"""
    html = _plantilla(f"¡Bienvenido a {NOMBRE_SISTEMA}!", cuerpo)

    return asunto, texto, html


def enviar_correo_bienvenida(nombre, usuario, correo, perfil, pods, contrasena,
                             descripcion_perfil=None):
    """Envía el correo de bienvenida. Lanza una excepción si no es posible."""
    config = configuracion_correo()
    if config is None:
        raise RuntimeError("Falta configurar la sección [email] en los secretos de la aplicación.")

    app_url = config.get("app_url") or APP_URL_DEFECTO
    asunto, texto, html = construir_correo_bienvenida(
        nombre, usuario, correo, perfil, pods, contrasena, app_url, descripcion_perfil
    )

    with _servidor_smtp(config) as servidor:
        servidor.send_message(_armar_mensaje(config, correo, asunto, texto, html))


def _armar_mensaje(config, destinatario, asunto, texto, html):
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

    if LOGO.exists():
        logo = MIMEImage(LOGO.read_bytes(), _subtype="png")
        logo.add_header("Content-ID", "<logo_podex>")
        logo.add_header("Content-Disposition", "inline", filename=LOGO.name)
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

ORDEN_RANGOS = ["0-5 días", "6-10 días", "11-20 días", ">20 días"]

# Colores de la tabla dinámica (estilo Excel).
AZUL_ENCABEZADO = "#DDEBF7"
AZUL_BORDE = "#9BC2E6"
GRIS_TOTAL = "#D9D9D9"
AMARILLO_CELDA = "#FFC000"
ROJO_CELDA = "#FF0000"

TEXTO_BACKLOG = """Les comparto el archivo adjunto ({nombre_archivo}) para lograr gestionar y seguir reduciendo al máximo el tiempo de gestión de los incidentes y requerimientos de la JDU para el indicador global de salud del servicio.

Para recordar que las metas son:
  • IMs (Incidentes) = 24 horas calendario desde la fecha inicio a cierre satisfactorio.
  • RFs (Requerimientos) = 48 horas calendario desde la fecha inicio a cierre satisfactorio.
Acciones que se sugieren realizar ASAP:
  • Revisar casos con aliados para gestionar el cierre en SM.
  • Revisar casos con funcionarios de ECP para gestionar el cierre en SM.
  • Gestionar con aliados, automatizaciones en flujos de gestión de accesos y demás requerimientos, que permitan seguir disminuyendo los tiempos que a hoy tenemos.
"""


def _orden_rango(rango):
    return ORDEN_RANGOS.index(rango) if rango in ORDEN_RANGOS else len(ORDEN_RANGOS)


def _tabla_dinamica(registros):
    """Tabla dinámica HTML: Product Owner por filas; TIPO x RANGTIEMPO por
    columnas, con totales por tipo y total general (como en Excel).
    registros: [(product_owner, tipo, rango), ...]."""
    conteo, tipos = {}, {}
    for po, tipo, rango in registros:
        conteo[(po, tipo, rango)] = conteo.get((po, tipo, rango), 0) + 1
        tipos.setdefault(tipo, set()).add(rango)

    tipos = {t: sorted(r, key=_orden_rango) for t, r in sorted(tipos.items())}
    total_po = {}
    for (po, _, _), c in conteo.items():
        total_po[po] = total_po.get(po, 0) + c
    filas = sorted(total_po, key=lambda po: (-total_po[po], po))

    fuente = "font-family:Aptos Narrow,Calibri,Arial,sans-serif;font-size:12px;"
    celda = f"{fuente}padding:2px 6px;white-space:nowrap;"
    enc = f"{celda}background:{AZUL_ENCABEZADO};font-weight:700;color:#000;"
    gris = f"{celda}background:{GRIS_TOTAL};text-align:right;"

    # Encabezados: tipos (con su total) y rangos de días.
    h1 = f'<td style="{enc}">Cuenta de ID_SOLICITUD</td>'
    h2 = f'<td style="{enc}">Etiquetas de fila</td>'
    for tipo, rangos in tipos.items():
        h1 += f'<td colspan="{len(rangos)}" style="{enc}">&#8863; {escape(str(tipo))}</td>'
        h1 += f'<td rowspan="2" style="{enc}background:{GRIS_TOTAL};vertical-align:top;">Total {escape(str(tipo))}</td>'
        h2 += "".join(f'<td style="{enc}">{escape(str(r))}</td>' for r in rangos)
    h1 += f'<td rowspan="2" style="{enc}vertical-align:top;">Total general</td>'

    cuerpo = ""
    for po in filas:
        fila = f'<td style="{celda}border-bottom:1px solid #eee;">{escape(str(po))}</td>'
        for tipo, rangos in tipos.items():
            subtotal = 0
            for r in rangos:
                c = conteo.get((po, tipo, r), 0)
                subtotal += c
                color = AMARILLO_CELDA if r == "0-5 días" else ROJO_CELDA
                fila += (f'<td style="{celda}text-align:right;background:{color};">{c}</td>' if c
                         else f'<td style="{celda}"></td>')
            fila += f'<td style="{gris}">{subtotal or ""}</td>'
        fila += f'<td style="{celda}text-align:right;">{total_po[po]}</td>'
        cuerpo += f"<tr>{fila}</tr>"

    tot = f"{enc}border-top:1px solid {AZUL_BORDE};text-align:right;"
    total = f'<td style="{enc}border-top:1px solid {AZUL_BORDE};">Total general</td>'
    for tipo, rangos in tipos.items():
        for r in rangos:
            total += f'<td style="{tot}">{sum(conteo.get((po, tipo, r), 0) for po in filas)}</td>'
        total += f'<td style="{tot}">{sum(c for (_, t, _), c in conteo.items() if t == tipo)}</td>'
    total += f'<td style="{tot}">{sum(conteo.values())}</td>'

    return (
        f'<table cellpadding="0" cellspacing="0" style="border-collapse:collapse;margin:6px 0 18px;">'
        f"<tr>{h1}</tr><tr>{h2}</tr>{cuerpo}<tr>{total}</tr></table>"
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

    resumen: dict con fecha (ddmmaaaa), usuario_carga, general y funcional
    (listas de (product_owner, tipo, rango) de las solicitudes cargadas).
    """
    nombre_archivo = f"{resumen['fecha']} - Backlog"
    asunto = nombre_archivo
    intro = TEXTO_BACKLOG.format(nombre_archivo=nombre_archivo)

    texto = intro + "\nDETALLE GENERAL\n" + (_tabla_texto(resumen["general"]) or "  Sin solicitudes")
    if resumen["funcional"]:
        texto += "\n\nGRUPO FUNCIONAL ECOPETROL\n" + _tabla_texto(resumen["funcional"])
    texto += f"\n\nCordialmente,\n{resumen['usuario_carga']}\n"

    p = "font-family:Aptos,Calibri,Arial,sans-serif;font-size:14px;color:#000;margin:0;"
    li = "font-family:Aptos,Calibri,Arial,sans-serif;font-size:14px;color:#000;"
    html = f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8"></head>
<body style="margin:0;padding:16px;background:#fff;">
<p style="{p}">Les comparto el archivo adjunto ({escape(nombre_archivo)}) para lograr gestionar y seguir reduciendo al máximo el tiempo de gestión de los incidentes y requerimientos de la JDU para el indicador global de salud del servicio.</p>
<br>
<p style="{p}">Para recordar que las metas son:</p>
<ul style="margin:0 0 0 18px;padding-left:18px;">
  <li style="{li}"><b>IMs (Incidentes) = 24 horas calendario</b> desde la fecha inicio a cierre satisfactorio.</li>
  <li style="{li}"><b>RFs (Requerimientos) = 48 horas calendario</b> desde la fecha inicio a cierre satisfactorio.</li>
</ul>
<p style="{p}">Acciones que se sugieren realizar ASAP:</p>
<ul style="margin:0 0 14px 18px;padding-left:18px;">
  <li style="{li}">Revisar casos con aliados para gestionar el cierre en SM.</li>
  <li style="{li}">Revisar casos con funcionarios de ECP para gestionar el cierre en SM.</li>
  <li style="{li}">Gestionar con aliados, automatizaciones en flujos de gestión de accesos y demás requerimientos, que permitan seguir disminuyendo los tiempos que a hoy tenemos.</li>
</ul>
{_tabla_dinamica(resumen["general"]) if resumen["general"] else f'<p style="{p}">Sin solicitudes en DETALLE_GENERAL.</p><br>'}
{(f'<table cellpadding="0" cellspacing="0" style="border-collapse:collapse;"><tr><td style="font-family:Aptos Narrow,Calibri,Arial,sans-serif;font-size:12px;font-weight:700;background:{AZUL_ENCABEZADO};padding:2px 6px;">Grupo Funcional Ecopetrol</td></tr></table>'
  + _tabla_dinamica(resumen["funcional"])) if resumen["funcional"] else ""}
<p style="{p}">Cordialmente,</p>
<p style="{p}"><b>{escape(resumen["usuario_carga"])}</b></p>
</body></html>"""

    return asunto, texto, html


def enviar_correo_backlog(correos, resumen, archivo_bytes):
    """Envía UN solo correo de backlog con el Excel adjunto a todos los
    correos recibidos. Van en copia oculta (CCO) para no exponer las
    direcciones entre sí; el destinatario visible es la cuenta de PODEX.
    Devuelve el número de destinatarios."""
    config = configuracion_correo()
    if config is None:
        raise RuntimeError("Falta configurar la sección [email] en los secretos de la aplicación.")

    correos = sorted({c.strip().lower() for c in correos if c and c.strip()})
    if not correos:
        return 0

    asunto, texto, html = construir_correo_backlog(resumen)

    remitente = config.get("remitente") or formataddr((NOMBRE_SISTEMA, config["usuario"]))
    nombre_rem, correo_rem = parseaddr(remitente)

    mensaje = MIMEMultipart("mixed")
    mensaje["Subject"] = asunto
    mensaje["From"] = formataddr((nombre_rem or NOMBRE_SISTEMA, correo_rem or config["usuario"]))
    mensaje["To"] = correo_rem or config["usuario"]
    mensaje["Bcc"] = ", ".join(correos)

    alternativa = MIMEMultipart("alternative")
    alternativa.attach(MIMEText(texto, "plain", "utf-8"))
    alternativa.attach(MIMEText(html, "html", "utf-8"))
    mensaje.attach(alternativa)

    adjunto = MIMEApplication(
        archivo_bytes,
        _subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    adjunto.add_header("Content-Disposition", "attachment",
                       filename=f"{resumen['fecha']} - Backlog.xlsx")
    mensaje.attach(adjunto)

    # send_message() envía a To + Bcc y no incluye el encabezado Bcc en el mensaje.
    with _servidor_smtp(config) as servidor:
        servidor.send_message(mensaje)

    return len(correos)
