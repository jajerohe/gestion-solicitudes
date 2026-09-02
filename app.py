import streamlit as st

from database import Database


st.set_page_config(
    page_title="Gestión de Solicitudes",
    page_icon="📋",
    layout="wide"
)


st.title("📋 Gestión de Solicitudes")

st.write(
    "Prueba de conexión entre Streamlit y Supabase"
)


# ======================================================
# PRUEBA DE CONEXIÓN
# ======================================================

try:

    db = Database()

    db.conectar()

    st.success("✅ Conexión con Supabase exitosa")


    # ==================================================
    # CONSULTAR SOLICITUD DE PRUEBA
    # ==================================================

    sql = """
        SELECT
            "ID_SOLICITUD",
            "TITULO",
            "STATUS",
            "PRODUCT_OWNER"
        FROM public."Solicitudes"
        WHERE "ID_SOLICITUD" = %s
    """

    db.execute(sql, ("TEST-0001",))

    solicitud = db.fetchone()


    if solicitud:

        st.success("✅ Solicitud TEST-0001 encontrada")

        st.write("### Datos encontrados")

        st.write(
            {
                "ID_SOLICITUD": solicitud[0],
                "TITULO": solicitud[1],
                "STATUS": solicitud[2],
                "PRODUCT_OWNER": solicitud[3],
            }
        )

    else:

        st.warning(
            "⚠️ La conexión funciona, "
            "pero no se encontró TEST-0001."
        )


    db.cerrar()


except Exception as e:

    st.error("❌ Error de conexión")

    st.exception(e)
