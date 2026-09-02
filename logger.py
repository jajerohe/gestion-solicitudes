# -*- coding: utf-8 -*-
"""
============================================================
logger.py
Configuración del sistema de logs
============================================================
"""

import logging
import os

from config import LOG_FILE


def configurar_logger():

    logger = logging.getLogger("CargarSolicitudes")

    # Evita agregar múltiples handlers si ya existe
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    # ======================================================
    # Formato
    # ======================================================

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # ======================================================
    # Consola
    # ======================================================

    console = logging.StreamHandler()

    console.setLevel(logging.INFO)

    console.setFormatter(formatter)

    logger.addHandler(console)

    # ======================================================
    # Archivo
    # ======================================================

    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

    file_handler = logging.FileHandler(
        LOG_FILE,
        mode="a",
        encoding="utf-8"
    )

    file_handler.setLevel(logging.INFO)

    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)

    logger.info("=" * 70)
    logger.info("Inicio del proceso de carga")
    logger.info("=" * 70)

    return logger