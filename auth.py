import streamlit as st
from supabase import create_client, Client


def obtener_cliente_supabase() -> Client:
    """Cliente nuevo por operación: la sesión de Supabase Auth no se comparte
    entre los usuarios que usan la aplicación al mismo tiempo."""
    return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])


def iniciar_sesion(email: str, password: str):
    try:
        return obtener_cliente_supabase().auth.sign_in_with_password(
            {"email": email, "password": password}
        )
    except Exception as e:
        raise Exception(f"No fue posible iniciar sesión: {e}")


def cerrar_sesion():
    # La aplicación no conserva el token de Supabase después del inicio de
    # sesión (la sesión de PODEX vive en st.session_state), así que no hay
    # una sesión remota que revocar.
    pass
