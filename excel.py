# -*- coding: utf-8 -*-

import pandas as pd
import pyodbc
import math

from config import (
    HOJAS,
    PRODUCT_OWNERS,
    COLUMNAS_SQL,
    INSERT_SQL
)

from utilidades import (
    normalizar_columnas,
    validar_columnas,
    convertir_fecha,
    limpiar_texto
)

from logger import configurar_logger

logger = configurar_logger()


class ExcelProcessor:

    def __init__(self, db):

        self.db = db

        self.registros_generales = 0
        self.registros_funcionales = 0
        self.registros_duplicados = 0

    # ======================================================
    # Procesa un archivo completo
    # ======================================================

    def procesar_archivo(self, ruta_archivo):

        logger.info(f"Procesando archivo: {ruta_archivo}")

        with pd.ExcelFile(ruta_archivo) as excel:

            for hoja in HOJAS:

                if hoja not in excel.sheet_names:

                    logger.warning(
                        f"La hoja {hoja} no existe."
                    )

                    continue

                self.procesar_hoja(
                    excel,
                    hoja
                )

    # ======================================================
    # Procesa una hoja
    # ======================================================

    def procesar_hoja(
        self,
        excel,
        hoja
    ):

        logger.info(
            f"Leyendo hoja {hoja}"
        )

        df = pd.read_excel(
            excel,
            sheet_name=hoja
        )

        df = normalizar_columnas(df)

        validar_columnas(df)

        # ------------------------------------------
        # Filtrar Product Owner
        # ------------------------------------------

        df["PRODUCT_OWNER"] = (

            df["PRODUCT_OWNER"]

            .fillna("")

            .astype(str)

            .str.upper()

            .str.strip()

        )

        df = df[
            df["PRODUCT_OWNER"].isin(
                PRODUCT_OWNERS
            )
        ]

        logger.info(
            f"Registros encontrados: {len(df)}"
        )

        if df.empty:

            return

        # ------------------------------------------
        # Convertir fechas
        # ------------------------------------------

        for campo in [

            "FECHA_APERTURA",
            "FECHA_CIERRE"

        ]:

            if campo in df.columns:

                df[campo] = df[campo].apply(
                    convertir_fecha
                )

        # ------------------------------------------
        # Recorrer registros
        # ------------------------------------------

        for _, fila in df.iterrows():

            self.insertar_registro(
                hoja,
                fila
            )

    # ======================================================
    # Preparar registro
    # ======================================================

    def preparar_registro(
        self,
        hoja,
        fila
    ):

        valores = []

        for columna in COLUMNAS_SQL:

            if columna == "ORIGEN":

                valores.append(hoja)

                continue

            # ============================================
            # CURRENT_PHASE SIEMPRE SE INSERTA COMO NULL
            # ============================================
            if columna == "CURRENT_PHASE":

                valores.append(None)

                continue

            if columna in fila.index:
                valor = fila[columna]
            else:
                valor = None

            # Para depuración (temporal)
            logger.info(f"{columna} = {repr(valor)} ({type(valor).__name__})")

            # Convierte NaN, NaT y pd.NA en None
            if pd.isna(valor):
                valor = None

            # Convierte Timestamp de pandas a datetime de Python
            elif hasattr(valor, "to_pydatetime"):
                valor = valor.to_pydatetime()

            # Limpia textos
            elif isinstance(valor, str):
                valor = limpiar_texto(valor)

            # Evita infinitos
            elif isinstance(valor, int):
                if math.isnan(valor) or math.isinf(valor):
                    valor = None

            valores.append(valor)

        return tuple(valores)
    
    # ======================================================
    # Insertar registro
    # ======================================================

    def insertar_registro(
        self,
        hoja,
        fila
    ):

        try:

            valores = self.preparar_registro(
                hoja,
                fila
            )

            # ===== DEPURACIÓN =====
            for i, v in enumerate(valores, start=1):
                logger.info(f"{i:02d}: {type(v).__name__} -> {repr(v)}")
            # ======================

            self.db.execute(
                INSERT_SQL,
                valores
            )

            if hoja == "DETALLE_GENERAL":

                self.registros_generales += 1

            else:

                self.registros_funcionales += 1

        except pyodbc.IntegrityError:

            # La PK ID_SOLICITUD ya existe
            self.registros_duplicados += 1

            logger.warning(
                f"Solicitud duplicada: {fila['ID_SOLICITUD']}"
            )

        except Exception as ex:

            logger.exception(ex)

            raise


    # ======================================================
    # Reiniciar contadores
    # ======================================================

    def reiniciar(self):

        self.registros_generales = 0
        self.registros_funcionales = 0
        self.registros_duplicados = 0


    # ======================================================
    # Ejecutar proceso
    # ======================================================

    def ejecutar(
        self,
        ruta_archivo
    ):

        self.reiniciar()

        logger.info("=" * 70)
        logger.info(
            f"Procesando archivo: {ruta_archivo}"
        )
        logger.info("=" * 70)

        self.procesar_archivo(
            ruta_archivo
        )

        logger.info(
            f"Generales : {self.registros_generales}"
        )

        logger.info(
            f"Funcionales : {self.registros_funcionales}"
        )

        logger.info(
            f"Duplicados : {self.registros_duplicados}"
        )

        logger.info(
            f"Total : {self.get_total()}"
        )

        return {

            "generales": self.registros_generales,

            "funcionales": self.registros_funcionales,

            "duplicados": self.registros_duplicados,

            "total": self.get_total()

        }


    # ======================================================
    # Getters
    # ======================================================

    def get_generales(self):

        return self.registros_generales


    def get_funcionales(self):

        return self.registros_funcionales


    def get_duplicados(self):

        return self.registros_duplicados


    def get_total(self):

        return (

            self.registros_generales +

            self.registros_funcionales

        )