import streamlit as st

st.set_page_config(
    page_title="Gestión de Solicitudes",
    page_icon="📋",
    layout="wide"
)

st.title("📋 Gestión de Solicitudes")
st.write("Aplicación web de seguimiento de solicitudes")

st.success("¡La aplicación está funcionando!")

st.info(
    "Este es el primer paso de la migración. "
    "Posteriormente conectaremos la aplicación con la base de datos."
)
