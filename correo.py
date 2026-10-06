"""
Envío del correo de bienvenida a los usuarios nuevos de PODEX.

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

    html = f"""<!DOCTYPE html>
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
    <div style="color:{VERDE_OSCURO};font-size:22px;font-weight:800;">¡Bienvenido a {NOMBRE_SISTEMA}!</div>
    <div style="color:{GRIS_TEXTO};font-size:12px;margin-top:4px;">{DESCRIPCION_SISTEMA}</div>
  </td></tr>

  <tr><td style="padding:0 32px;">
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

  <tr><td style="background:{VERDE_OSCURO};padding:16px 24px;" align="center">
    <div style="color:#fff;font-size:13px;font-weight:700;">{NOMBRE_SISTEMA}</div>
    <div style="color:#cfe3dc;font-size:11px;margin-top:2px;">{DESCRIPCION_SISTEMA}</div>
    <div style="color:#9fbfb5;font-size:10px;margin-top:8px;">Este es un mensaje automático, por favor no responda a este correo. © {anio} {NOMBRE_SISTEMA}</div>
  </td></tr>
  <tr><td style="height:4px;background:{LIMA};font-size:0;line-height:0;">&nbsp;</td></tr>

</table>
</td></tr></table>
</body></html>"""

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

    remitente = config.get("remitente") or formataddr((NOMBRE_SISTEMA, config["usuario"]))
    nombre_rem, correo_rem = parseaddr(remitente)

    mensaje = MIMEMultipart("related")
    mensaje["Subject"] = asunto
    mensaje["From"] = formataddr((nombre_rem or NOMBRE_SISTEMA, correo_rem or config["usuario"]))
    mensaje["To"] = correo

    alternativa = MIMEMultipart("alternative")
    alternativa.attach(MIMEText(texto, "plain", "utf-8"))
    alternativa.attach(MIMEText(html, "html", "utf-8"))
    mensaje.attach(alternativa)

    if LOGO.exists():
        logo = MIMEImage(LOGO.read_bytes(), _subtype="png")
        logo.add_header("Content-ID", "<logo_podex>")
        logo.add_header("Content-Disposition", "inline", filename=LOGO.name)
        mensaje.attach(logo)

    host = config["smtp_host"]
    puerto = int(config["smtp_port"])
    contexto = ssl.create_default_context()

    if puerto == 465:
        with smtplib.SMTP_SSL(host, puerto, context=contexto, timeout=30) as servidor:
            servidor.login(config["usuario"], config["password"])
            servidor.send_message(mensaje)
    else:
        with smtplib.SMTP(host, puerto, timeout=30) as servidor:
            servidor.starttls(context=contexto)
            servidor.login(config["usuario"], config["password"])
            servidor.send_message(mensaje)
