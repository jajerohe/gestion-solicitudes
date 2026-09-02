# -*- coding: utf-8 -*-

"""
Procesamiento de archivos Excel para la aplicación web.

Migración de la lógica de excel.py de la aplicación de escritorio.
"""

import pandas as pd

from database import Database


# ============================================================
# CONFIGURACIÓN
# ============================================================

HOJAS = [
    "DETALLE_GENERAL",
    "DETALLE_FUNCIONALES"
]


PRODUCT_OWNERS = {
    "ALIRIO GUERRERO PEÑA",
    "DAVID CABAL ORDONEZ",
    "WILLIAM ANTONIO DELGADO PEÑA"
}


COLUMNAS_OBLIGATORIAS = {
    "ID_SOLICITUD",
    "PRODUCT_OWNER",
    "STATUS",
    "FECHA_APERTURA"
}


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
# NORMALIZAR COLUMNAS
# ============================================================

def normalizar_columnas(df):

    df.columns = (
        df.columns
        .astype(str)
        .str.strip()
        .str.upper()
        .str.replace(" ", "_", regex=False)
        .str.replace("/", "_", regex=False)
        .str.replace("-", "_", regex=False)
    )

    # Adaptar nombres específicos del Excel real
    equivalencias = {
        "SUMA_DE_DÍAS": "DIFDIAS",
        "SUMA_DE_DIAS": "DIFDIAS",
        "SUMA_DE_DIFDÍAS": "DIFDIAS",
        "SUMA_DE_DIFDIAS": "DIFDIAS",
        "RANGTIEMPO": "RANGTIEMPO",
    }

    df = df.rename(
        columns=equivalencias
    )

    return df


# ============================================================
# VALIDAR COLUMNAS
# ============================================================

def validar_columnas(df):

    faltantes = (
        COLUMNAS_OBLIGATORIAS
        - set(df.columns)
    )

    if faltantes:

        raise ValueError(
            "Columnas obligatorias faltantes: "
            + ", ".join(sorted(faltantes))
        )


# ============================================================
# LIMPIAR VALOR
# ============================================================

def limpiar_valor(valor):

    if pd.isna(valor):

        return None

    if hasattr(valor, "to_pydatetime"):

        return valor.to_pydatetime()

    if isinstance(valor, str):

        valor = valor.strip()

        if valor == "":

            return None

        return valor

    return valor


# ============================================================
# PROCESAR HOJA
# ============================================================

def procesar_hoja(df, hoja):

    # --------------------------------------------------------
    # Normalizar columnas
    # --------------------------------------------------------

    df = normalizar_columnas(df)

    # --------------------------------------------------------
    # Validar columnas obligatorias
    # --------------------------------------------------------

    validar_columnas(df)

    # --------------------------------------------------------
    # Normalizar Product Owner
    # --------------------------------------------------------

    df["PRODUCT_OWNER"] = (
        df["PRODUCT_OWNER"]
        .fillna("")
        .astype(str)
        .str.upper()
        .str.strip()
    )

    # --------------------------------------------------------
    # Filtrar Product Owner autorizados
    # --------------------------------------------------------

    df = df[
        df["PRODUCT_OWNER"].isin(
            PRODUCT_OWNERS
        )
    ].copy()

    # --------------------------------------------------------
    # Convertir fechas
    # --------------------------------------------------------

    for campo in [
        "FECHA_APERTURA",
        "FECHA_CIERRE"
    ]:

        if campo in df.columns:

            df[campo] = pd.to_datetime(
                df[campo],
                errors="coerce"
            )

    return df


# ============================================================
# PREPARAR REGISTRO
# ============================================================

def preparar_registro(fila, hoja):

    valores = []

    for columna in COLUMNAS_SQL:

        # ----------------------------------------------------
        # ORIGEN
        # ----------------------------------------------------

        if columna == "ORIGEN":

            valores.append(hoja)

            continue

        # ----------------------------------------------------
        # CURRENT_PHASE
        # ----------------------------------------------------

        if columna == "CURRENT_PHASE":

            valores.append(None)

            continue

        # ----------------------------------------------------
        # Obtener valor
        # ----------------------------------------------------

        if columna in fila.index:

            valor = fila[columna]

        else:

            valor = None

        valor = limpiar_valor(valor)

        valores.append(valor)

    return tuple(valores)


# ============================================================
# CARGAR ARCHIVO
# ============================================================

def cargar_excel(archivo, db):

    resultados = {
        "generales": 0,
        "funcionales": 0,
        "duplicados": 0,
        "errores": 0,
        "hojas": []
    }


    # ========================================================
    # LEER EXCEL
    # ========================================================

    excel = pd.ExcelFile(archivo)


    # ========================================================
    # RECORRER HOJAS
    # ========================================================

    for hoja in HOJAS:

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


        resultados["hojas"].append({
            "hoja": hoja,
            "registros": len(df)
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
                VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s
                )
                ON CONFLICT ("ID_SOLICITUD")
                DO NOTHING
                RETURNING "ID_SOLICITUD"
            """


            db.execute(
                sql,
                valores
            )


            insertado = db.fetchone()


            if insertado:

                if hoja == "DETALLE_GENERAL":

                    resultados["generales"] += 1

                else:

                    resultados["funcionales"] += 1

            else:

                resultados["duplicados"] += 1


    return resultados
