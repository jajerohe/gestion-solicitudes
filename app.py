import streamlit as st
import pandas as pd

from database import Database


st.set_page_config(
    page_title="Gestión de Solicitudes - ECP",
    page_icon="📋",
    layout="wide"
)


# ============================================================
# TÍTULO
# ============================================================

st.title("📋 Gestión de Solicitudes")


# ============================================================
# CONEXIÓN
# ============================================================

db = Database()

try:

    db.conectar()

except Exception as e:

    st.error("❌ No fue posible conectar con Supabase")

    st.exception(e)

    st.stop()


# ============================================================
# CARGAR SOLICITUDES
# ============================================================

sql = """
    SELECT
        "ID_SOLICITUD",
        "TITULO",
        "FECHA_APERTURA",
        "SUBSERVICIO_AFECTADO",
        "PRODUCT_OWNER",
        "STATUS",
        "ASIGNADO_A",
        "NOMBRE_ASIGNATARIO",
        "CORREO_ASIGNATARIO"
    FROM public."Solicitudes"
    WHERE "STATUS" NOT IN ('RESOLVED', 'COMPLETADO')
      AND "FECHA_CIERRE" IS NULL
    ORDER BY "FECHA_APERTURA" ASC
"""


try:

    db.execute(sql)

    registros = db.fetchall()

except Exception as e:

    st.error("❌ Error consultando las solicitudes")

    st.exception(e)

    db.cerrar()

    st.stop()


db.cerrar()


# ============================================================
# CONVERTIR A DATAFRAME
# ============================================================

columnas = [
    "ID_SOLICITUD",
    "TITULO",
    "FECHA_APERTURA",
    "SUBSERVICIO_AFECTADO",
    "PRODUCT_OWNER",
    "STATUS",
    "ASIGNADO_A",
    "NOMBRE_ASIGNATARIO",
    "CORREO_ASIGNATARIO"
]


df = pd.DataFrame(
    registros,
    columns=columnas
)


# ============================================================
# INFORMACIÓN
# ============================================================

st.success(
    f"✅ Conexión con Supabase exitosa — "
    f"{len(df)} solicitud(es) encontrada(s)"
)


# ============================================================
# BUSCADOR
# ============================================================

texto_busqueda = st.text_input(
    "🔎 Buscar solicitud",
    placeholder="Digite ID, título, estado, asignado, Product Owner..."
)


# ============================================================
# FILTRO
# ============================================================

if texto_busqueda:

    texto = texto_busqueda.lower()

    mascara = df.astype(str).apply(
        lambda columna: columna.str.lower().str.contains(
            texto,
            na=False
        )
    )

    df_filtrado = df[
        mascara.any(axis=1)
    ]

else:

    df_filtrado = df


# ============================================================
# MOSTRAR RESULTADOS
# ============================================================

st.subheader(
    f"Solicitudes ({len(df_filtrado)})"
)


st.dataframe(
    df_filtrado,
    use_container_width=True,
    hide_index=True
)
