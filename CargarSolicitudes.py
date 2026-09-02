# -*- coding: utf-8 -*-
"""
============================================================
CargarSolicitudes.py

Programa principal

Autor: Janssen Rodríguez
Versión: 2.0
============================================================
"""

import os
import traceback

from config import CARPETA_ENTRADA

from database import Database
from auditoria import Auditoria
from excel import ExcelProcessor

from utilidades import (
    mover_a_procesados,
    mover_a_error,
    imprimir_resumen
)

from logger import configurar_logger


logger = configurar_logger()


def main():

    archivos_procesados = 0
    total_generales = 0
    total_funcionales = 0
    total_duplicados = 0
    total_errores = 0

    db = Database()

    try:

        db.conectar()

        auditoria = Auditoria(db)

        excel = ExcelProcessor(db)

        logger.info("")
        logger.info("=" * 80)
        logger.info("INICIO DEL PROCESO")
        logger.info("=" * 80)

        archivos = sorted(os.listdir(CARPETA_ENTRADA))

        for archivo in archivos:

            if not archivo.lower().endswith(".xlsx"):
                continue

            ruta_archivo = os.path.join(
                CARPETA_ENTRADA,
                archivo
            )

            logger.info("")
            logger.info("-" * 80)
            logger.info(f"Archivo: {archivo}")
            logger.info("-" * 80)

            # ============================================
            # Validar si ya fue procesado
            # ============================================

            if auditoria.existe(archivo):

                logger.warning(
                    "Archivo ya procesado."
                )

                continue

            try:

                resultado = excel.ejecutar(
                    ruta_archivo
                )

                auditoria.registrar_exitoso(

                    archivo,

                    resultado["generales"],

                    resultado["funcionales"]

                )

                db.commit()

                mover_a_procesados(
                    ruta_archivo
                )

                archivos_procesados += 1

                total_generales += resultado["generales"]

                total_funcionales += resultado["funcionales"]

                total_duplicados += resultado["duplicados"]

                logger.info(
                    "Archivo procesado correctamente."
                )

            except Exception as ex:

                db.rollback()

                total_errores += 1

                logger.exception(ex)

                try:

                    auditoria.registrar_error(

                        archivo,

                        excel.get_generales(),

                        excel.get_funcionales(),

                        str(ex)

                    )

                    db.commit()

                except Exception:

                    db.rollback()

                mover_a_error(
                    ruta_archivo
                )

        imprimir_resumen(

            archivos_procesados,

            total_generales,

            total_funcionales,

            total_duplicados,

            total_errores

        )

    except Exception as ex:

        logger.exception(ex)

        traceback.print_exc()

    finally:

        db.cerrar()

        logger.info("")
        logger.info("=" * 80)
        logger.info("FIN DEL PROCESO")
        logger.info("=" * 80)


# ======================================================
# INICIO
# ======================================================

if __name__ == "__main__":

    main()