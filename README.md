# PODEX · Gestión de Solicitudes

Sistema Integrado de Gestión de Peticiones, Incidentes y Vulnerabilidades, en Streamlit con Supabase (PostgreSQL + Auth).

## Estructura

| Archivo | Contenido |
|---|---|
| `app.py` | Inicio de sesión, menú, estilos, página de Solicitudes y página de Cargar solicitudes |
| `usuarios.py` | Módulo de Usuarios y funciones de interfaz compartidas (`encabezado_ventana`, `ficha`, `seccion`) |
| `pods.py` | Módulo de POD's |
| `excel_web.py` | Lectura, vista previa y carga del Excel (`DETALLE_GENERAL`, `DETALLE_FUNCIONALES`) |
| `correo.py` | Correo de bienvenida a los usuarios nuevos |
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
