# PODEX · Gestión de Solicitudes

Sistema Integrado de Gestión de Peticiones, Incidentes y Vulnerabilidades, en Streamlit con Supabase (PostgreSQL + Auth).

## Estructura

| Archivo | Contenido |
|---|---|
| `app.py` | Inicio de sesión, menú, estilos, página de Solicitudes y página de Cargar solicitudes |
| `usuarios.py` | Módulo de Usuarios y funciones de interfaz compartidas (`encabezado_ventana`, `ficha`, `seccion`) |
| `pods.py` | Módulo de POD's |
| `listas.py` | Módulo de Listas de correo: destinatarios (Para, CC, CCO) de cada reporte que se envía por correo |
| `reportes.py` | Módulo de Reportes: Auditoría de carga (Administrador) y Seguimiento de solicitudes abiertas (Operador) |
| `seguimiento.py` | Reporte de seguimiento del backlog para el correo (Operador) |
| `excel_web.py` | Lectura, vista previa y carga del Excel (`DETALLE_GENERAL`, `DETALLE_FUNCIONALES`) |
| `correo.py` | Diseño común de los correos (marca Ecopetrol), correo de bienvenida y de backlog, y envío con Para, CC, CCO y adjuntos |
| `envios.py` | Vista previa de cada correo antes de enviarlo (enviar / no enviar) |
| `auth.py` | Inicio de sesión con Supabase Auth |
| `database.py` | Conexión a PostgreSQL |

## Secretos (`.streamlit/secrets.toml` o Settings → Secrets en Streamlit Cloud)

```toml
[database]
host = "..."
port = 5432
database = "postgres"
user = "..."
password = "..."

[supabase]
url = "https://<proyecto>.supabase.co"
key = "<llave publishable/anon>"
service_role_key = "<llave secret/service_role>"   # módulo de Usuarios

[email]                                            # correo de bienvenida (opcional)
smtp_host = "smtp.gmail.com"
smtp_port = 587
usuario = "cuenta@gmail.com"
password = "<contraseña de aplicación>"
remitente = "PODEX <cuenta@gmail.com>"
app_url = "https://podexweb.streamlit.app"
```

## Ejecución local

```bash
pip install -r requirements.txt
streamlit run app.py
```
