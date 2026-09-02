# -*- coding: utf-8 -*-
"""
============================================================
utilidades.py
Funciones auxiliares
============================================================
"""

import os
import time
import shutil
import pandas as pd

from config import (
    CARPETA_PROCESADOS,
    CARPETA_ERROR,
    COLUMNAS_OBLIGATORIAS
)

from logger import configurar_logger

logger = configurar_logger()


# ==========================================================
# NORMALIZAR NOMBRES DE COLUMNAS
# ==========================================================

def normalizar_columnas(df):

    df.columns = (
        df.columns
        .str.strip()
        .str.upper()
        .str.replace(" ", "_", regex=False)
        .str.replace("/", "_", regex=False)
        .str.replace("-", "_", regex=False)
    )

    return df


# ==========================================================
# VALIDAR COLUMNAS OBLIGATORIAS
# ==========================================================

def validar_columnas(df):

    faltantes = COLUMNAS_OBLIGATORIAS - set(df.columns)

    if faltantes:

        raise Exception(
            f"Columnas obligatorias faltantes: {', '.join(sorted(faltantes))}"
        )


# ==========================================================
# CONVERTIR FECHA
# ==========================================================

def convertir_fecha(valor):

    if pd.isna(valor):
        return None

    try:

        fecha = pd.to_datetime(
            valor,
            errors="coerce"
        )

        if pd.isna(fecha):
            return None

        return fecha.to_pydatetime()

    except Exception:

        return None


# ==========================================================
# LIMPIAR TEXTO
# ==========================================================

def limpiar_texto(valor):

    if pd.isna(valor):
        return None

    valor = str(valor).strip()

    if valor == "":
        return None

    return valor


# ==========================================================
# MOVER A PROCESADOS
# ==========================================================

def mover_a_procesados(ruta_archivo):

    nombre = os.path.basename(ruta_archivo)

    destino = os.path.join(
        CARPETA_PROCESADOS,
        nombre
    )

    try:

        if os.path.exists(destino):
            os.remove(destino)

        # Espera para asegurar que Excel liberó el archivo
        time.sleep(0.5)

        shutil.move(ruta_archivo, destino)

        # Validación adicional
        if os.path.exists(ruta_archivo):
            os.remove(ruta_archivo)

        logger.info(f"Archivo movido a Procesados: {nombre}")

    except Exception as ex:

        logger.exception(ex)

        raise


# ==========================================================
# MOVER A ERROR
# ==========================================================

def mover_a_error(ruta_archivo):

    nombre = os.path.basename(ruta_archivo)

    destino = os.path.join(
        CARPETA_ERROR,
        nombre
    )

    try:

        if os.path.exists(destino):
            os.remove(destino)

        time.sleep(0.5)

        shutil.move(ruta_archivo, destino)

        if os.path.exists(ruta_archivo):
            os.remove(ruta_archivo)

        logger.warning(f"Archivo movido a Error: {nombre}")

    except Exception as ex:

        logger.exception(ex)


# ==========================================================
# CONTAR REGISTROS
# ==========================================================

def contar_registros(df):

    if df is None:
        return 0

    return len(df.index)


# ==========================================================
# VALIDAR HOJA
# ==========================================================

def validar_hoja(excel, hoja):

    return hoja in excel.sheet_names


# ==========================================================
# RESUMEN FINAL
# ==========================================================

def imprimir_resumen(
    archivos,
    generales,
    funcionales,
    duplicados,
    errores
):

    logger.info("")
    logger.info("=" * 70)
    logger.info("RESUMEN DEL PROCESO")
    logger.info("=" * 70)

    logger.info(f"Archivos procesados : {archivos}")
    logger.info(f"Registros Generales : {generales}")
    logger.info(f"Registros Funcionales : {funcionales}")
    logger.info(f"Duplicados : {duplicados}")
    logger.info(f"Errores : {errores}")

    logger.info("=" * 70)