# -*- coding: utf-8 -*-

"""
Procesamiento de archivos Excel para la aplicación web.

Este módulo realiza:

1. Lectura de archivos Excel.
2. Procesamiento de las hojas:
   - DETALLE_GENERAL
   - DETALLE_FUNCIONALES
3. Normalización de columnas.
4. Validación de columnas obligatorias.
5. Filtro por Product Owner.
6. Conversión de fechas.
7. Preparación de registros.
8. Análisis previo sin insertar.
9. Inserción de solicitudes en Supabase.
10. Control de registros duplicados.
"""

import unicodedata

import pandas as pd

from database import Database


# ============================================================
# CONFIGURACIÓN
# ============================================================

HOJAS = [
    "DETALLE_GENERAL",
    "DETALLE_FUNCIONALES"
]


# ============================================================
# PRODUCT OWNER AUTORIZADOS
# ============================================================

PRODUCT_OWNERS = {
    "ALIRIO GUERRERO PEÑA",
    "DAVID CABAL ORDONEZ",
    "WILLIAM ANTONIO DELGADO PEÑA"
}


# ============================================================
# COLUMNAS OBLIGATORIAS
# ============================================================

COLUMNAS_OBLIGATORIAS = {
    "ID_SOLICITUD",
    "PRODUCT_OWNER",
    "STATUS",
    "FECHA_APERTURA"
}


# ============================================================
# COLUMNAS QUE SE INSERTAN EN SOLICITUDES
# ============================================================

COLUMNAS_SQL = [
    "ORIGEN",
    "TIPO",
    "ID_SOLICITUD",
    "TI_PRESTADOR",
    "GRUPO_ASIGNACION",
    "ASIGNADO_A",
    "NOMBRE_ASIGNATARIO",
    "CORREO_ASIGNATARIO",
    "CATEGORIA",
    "CURRENT_PHASE",
    "CONTACTO",
    "DESTINATARIO",
    "STATUS",
    "FECHA_APERTURA",
    "RANGTIEMPO",
    "TITULO",
    "DESCRIPCION",
    "SUBSERVICIO_AFECTADO",
    "PRODUCT_OWNER",
    "DIFDIAS"
]


# ============================================================
# NORMALIZAR TEXTO
# ============================================================

def quitar_acentos(texto):

    """
    Elimina acentos de un texto.

    Ejemplo:

    DifDías
    ↓
    DifDias
    """

    texto = unicodedata.normalize(
        "NFKD",
        str(texto)
    )

    return "".join(
        caracter
        for caracter in texto
        if not unicodedata.combining(caracter)
    )


# ============================================================
# NORMALIZAR NOMBRE DE COLUMNA
# ============================================================

def normalizar_nombre_columna(nombre):

    nombre = str(nombre).strip()

    nombre = quitar_acentos(nombre)

    nombre = nombre.upper()

    nombre = (
        nombre
        .replace(" ", "_")
        .replace("/", "_")
        .replace("-", "_")
    )

    # Eliminar posibles dobles guiones bajos

    while "__" in nombre:

        nombre = nombre.replace(
            "__",
            "_"
        )

    return nombre


# ============================================================
# NORMALIZAR COLUMNAS
# ============================================================

def normalizar_columnas(df):

    """
    Normaliza los nombres de las columnas del Excel.

    Ejemplos:

    Product Owner
        ↓
    PRODUCT_OWNER

    RangTiempo
        ↓
    RANGTIEMPO

    Suma de DifDías
        ↓
    SUMA_DE_DIFDIAS
        ↓
    DIFDIAS
    """

    df = df.copy()

    # --------------------------------------------------------
    # Normalizar nombres
    # --------------------------------------------------------

    df.columns = [
        normalizar_nombre_columna(columna)
        for columna in df.columns
    ]


    # --------------------------------------------------------
    # Equivalencias del Excel real
    # --------------------------------------------------------

    equivalencias = {

        "SUMA_DE_DIFDIAS":
            "DIFDIAS",

        "SUMA_DE_DIAS":
            "DIFDIAS",

        "DIFDIAS":
            "DIFDIAS",

        "RANGTIEMPO":
            "RANGTIEMPO"
    }


    df = df.rename(
        columns=equivalencias
    )


    return df


# ============================================================
# VALIDAR COLUMNAS
# ============================================================

def validar_columnas(df):

    """
    Valida que el Excel contenga las columnas mínimas
    necesarias para procesar solicitudes.
    """

    faltantes = (
        COLUMNAS_OBLIGATORIAS
        - set(df.columns)
    )


    if faltantes:

        raise ValueError(
            "Columnas obligatorias faltantes: "
            + ", ".join(
                sorted(faltantes)
            )
        )


# ============================================================
# LIMPIAR VALOR
# ============================================================

def limpiar_valor(valor):

    """
    Convierte valores de pandas a valores compatibles
    con PostgreSQL.
    """

    # --------------------------------------------------------
    # Valores nulos
    # --------------------------------------------------------

    if pd.isna(valor):

        return None


    # --------------------------------------------------------
    # Timestamp de pandas
    # --------------------------------------------------------

    if isinstance(
        valor,
        pd.Timestamp
    ):

        return valor.to_pydatetime()


    # --------------------------------------------------------
    # Fechas de Python
    # --------------------------------------------------------

    if hasattr(
        valor,
        "to_pydatetime"
    ):

        return valor.to_pydatetime()


    # --------------------------------------------------------
    # Texto
    # --------------------------------------------------------

    if isinstance(
        valor,
        str
    ):

        valor = valor.strip()


        if valor == "":

            return None


        return valor


    return valor


# ============================================================
# PROCESAR HOJA
# ============================================================

def procesar_hoja(
    df,
    hoja
):

    """
    Procesa una hoja individual del Excel.

    Aplica:

    - Normalización.
    - Validación.
    - Filtro Product Owner.
    - Conversión de fechas.
    """

    df = df.copy()


    # --------------------------------------------------------
    # Normalizar columnas
    # --------------------------------------------------------

    df = normalizar_columnas(
        df
    )


    # --------------------------------------------------------
    # Validar columnas
    # --------------------------------------------------------

    validar_columnas(
        df
    )


    # --------------------------------------------------------
    # Normalizar Product Owner
    # --------------------------------------------------------

    df["PRODUCT_OWNER"] = (

        df["PRODUCT_OWNER"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.upper()
    )


    # --------------------------------------------------------
    # Filtrar Product Owner
    # --------------------------------------------------------

    df = df[
        df["PRODUCT_OWNER"].isin(
            PRODUCT_OWNERS
        )
    ].copy()


    # --------------------------------------------------------
    # Convertir fechas
    # --------------------------------------------------------

    if "FECHA_APERTURA" in df.columns:

        df["FECHA_APERTURA"] = pd.to_datetime(
            df["FECHA_APERTURA"],
            errors="coerce"
        )


    if "FECHA_CIERRE" in df.columns:

        df["FECHA_CIERRE"] = pd.to_datetime(
            df["FECHA_CIERRE"],
            errors="coerce"
        )


    # --------------------------------------------------------
    # Convertir DIFDIAS
    # --------------------------------------------------------

    if "DIFDIAS" in df.columns:

        df["DIFDIAS"] = pd.to_numeric(
            df["DIFDIAS"],
            errors="coerce"
        )


    return df


# ============================================================
# PREPARAR REGISTRO
# ============================================================

def preparar_registro(
    fila,
    hoja
):

    """
    Convierte una fila del DataFrame en una tupla
    compatible con INSERT de PostgreSQL.
    """

    valores = []


    for columna in COLUMNAS_SQL:


        # ----------------------------------------------------
        # ORIGEN
        # ----------------------------------------------------

        if columna == "ORIGEN":

            valores.append(
                hoja
            )

            continue


        # ----------------------------------------------------
        # CURRENT_PHASE
        # ----------------------------------------------------

        if columna == "CURRENT_PHASE":

            valores.append(
                None
            )

            continue


        # ----------------------------------------------------
        # Obtener valor de la fila
        # ----------------------------------------------------

        if columna in fila.index:

            valor = fila[columna]

        else:

            valor = None


        # ----------------------------------------------------
        # Limpiar
        # ----------------------------------------------------

        valor = limpiar_valor(
            valor
        )


        valores.append(
            valor
        )


    return tuple(
        valores
    )


# ============================================================
# ANALIZAR EXCEL SIN INSERTAR
# ============================================================

def analizar_excel(
    archivo
):

    """
    Analiza el archivo Excel sin modificar Supabase.

    Devuelve únicamente los registros que cumplen
    el filtro de Product Owner.
    """

    resultados = []


    # ========================================================
    # LEER ARCHIVO
    # ========================================================

    excel = pd.ExcelFile(
        archivo
    )


    # ========================================================
    # PROCESAR HOJAS
    # ========================================================

    for hoja in HOJAS:


        # ----------------------------------------------------
        # Verificar existencia de hoja
        # ----------------------------------------------------

        if hoja not in excel.sheet_names:

            continue


        # ----------------------------------------------------
        # Leer hoja
        # ----------------------------------------------------

        df = pd.read_excel(
            excel,
            sheet_name=hoja
        )


        # ----------------------------------------------------
        # Procesar hoja
        # ----------------------------------------------------

        df = procesar_hoja(
            df,
            hoja
        )


        # ----------------------------------------------------
        # Crear resultado de análisis
        # ----------------------------------------------------

        for _, fila in df.iterrows():

            resultados.append({

                "HOJA":
                    hoja,

                "ID_SOLICITUD":
                    limpiar_valor(
                        fila.get(
                            "ID_SOLICITUD"
                        )
                    ),

                "PRODUCT_OWNER":
                    limpiar_valor(
                        fila.get(
                            "PRODUCT_OWNER"
                        )
                    ),

                "STATUS":
                    limpiar_valor(
                        fila.get(
                            "STATUS"
                        )
                    ),

                "FECHA_APERTURA":
                    limpiar_valor(
                        fila.get(
                            "FECHA_APERTURA"
                        )
                    ),

                "TITULO":
                    limpiar_valor(
                        fila.get(
                            "TITULO"
                        )
                    ),

                "RANGTIEMPO":
                    limpiar_valor(
                        fila.get(
                            "RANGTIEMPO"
                        )
                    ),

                "DIFDIAS":
                    limpiar_valor(
                        fila.get(
                            "DIFDIAS"
                        )
                    )
            })


    # ========================================================
    # DATAFRAME RESULTADO
    # ========================================================

    return pd.DataFrame(
        resultados
    )


# ============================================================
# CARGAR EXCEL A SUPABASE
# ============================================================

def cargar_excel(
    archivo,
    db
):

    """
    Procesa e inserta el Excel en Supabase.

    Los duplicados por ID_SOLICITUD se ignoran.
    """

    resultados = {

        "generales":
            0,

        "funcionales":
            0,

        "duplicados":
            0,

        "errores":
            0,

        "hojas":
            []
    }


    # ========================================================
    # LEER EXCEL
    # ========================================================

    excel = pd.ExcelFile(
        archivo
    )


    # ========================================================
    # RECORRER HOJAS
    # ========================================================

    for hoja in HOJAS:


        # ----------------------------------------------------
        # Verificar hoja
        # ----------------------------------------------------

        if hoja not in excel.sheet_names:

            continue


        # ----------------------------------------------------
        # Leer hoja
        # ----------------------------------------------------

        df = pd.read_excel(
            excel,
            sheet_name=hoja
        )


        # ----------------------------------------------------
        # Procesar
        # ----------------------------------------------------

        df = procesar_hoja(
            df,
            hoja
        )


        # ----------------------------------------------------
        # Registrar resumen
        # ----------------------------------------------------

        resultados["hojas"].append({

            "hoja":
                hoja,

            "registros":
                len(df)
        })


        # ----------------------------------------------------
        # Insertar registros
        # ----------------------------------------------------

        for _, fila in df.iterrows():


            valores = preparar_registro(
                fila,
                hoja
            )


            sql = """
                INSERT INTO public."Solicitudes"
                (
                    "ORIGEN",
                    "TIPO",
                    "ID_SOLICITUD",
                    "TI_PRESTADOR",
                    "GRUPO_ASIGNACION",
                    "ASIGNADO_A",
                    "NOMBRE_ASIGNATARIO",
                    "CORREO_ASIGNATARIO",
                    "CATEGORIA",
                    "CURRENT_PHASE",
                    "CONTACTO",
                    "DESTINATARIO",
                    "STATUS",
                    "FECHA_APERTURA",
                    "RANGTIEMPO",
                    "TITULO",
                    "DESCRIPCION",
                    "SUBSERVICIO_AFECTADO",
                    "PRODUCT_OWNER",
                    "DIFDIAS"
                )
                VALUES
                (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )
                ON CONFLICT ("ID_SOLICITUD")
                DO NOTHING
                RETURNING "ID_SOLICITUD"
            """


            try:

                db.execute(
                    sql,
                    valores
                )


                insertado = db.fetchone()


                # ------------------------------------------------
                # Registro nuevo
                # ------------------------------------------------

                if insertado:

                    if hoja == "DETALLE_GENERAL":

                        resultados[
                            "generales"
                        ] += 1

                    elif hoja == "DETALLE_FUNCIONALES":

                        resultados[
                            "funcionales"
                        ] += 1


                # ------------------------------------------------
                # Registro duplicado
                # ------------------------------------------------

                else:

                    resultados[
                        "duplicados"
                    ] += 1


            except Exception:

                resultados[
                    "errores"
                ] += 1

                raise


    return resultados
