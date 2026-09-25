import streamlit as st
from supabase import create_client, Client


@st.cache_resource
def obtener_cliente_supabase() -> Client:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]

    return create_client(url, key)


def iniciar_sesion(email: str, password: str):
    supabase = obtener_cliente_supabase()

    try:
        respuesta = supabase.auth.sign_in_with_password(
            {
                "email": email,
                "password": password,
            }
        )

        return respuesta

    except Exception as e:
        raise Exception(f"No fue posible iniciar sesión: {e}")


def cerrar_sesion():
    supabase = obtener_cliente_supabase()

    try:
        supabase.auth.sign_out()
    except Exception:
        pass
