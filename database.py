# -*- coding: utf-8 -*-
"""
============================================================
database.py
Manejo de la conexión a SQL Server
============================================================
"""

import pyodbc

from config import SERVER
from config import DATABASE
from config import DRIVER

from logger import configurar_logger

logger = configurar_logger()


class Database:

    def __init__(self):

        self.conn = None
        self.cursor = None

    # ======================================================
    # CONECTAR
    # ======================================================

    def conectar(self):

        try:

            logger.info("Conectando a SQL Server...")

            self.conn = pyodbc.connect(

                f"DRIVER={{{DRIVER}}};"
                f"SERVER={SERVER};"
                f"DATABASE={DATABASE};"
                f"Trusted_Connection=yes;"

            )

            self.conn.autocommit = False

            self.cursor = self.conn.cursor()

            # Acelera los INSERT masivos
            self.cursor.fast_executemany = True

            logger.info("Conexión establecida.")

            return self.cursor

        except Exception as ex:

            logger.exception("Error conectando a SQL Server")

            raise ex

    # ======================================================
    # COMMIT
    # ======================================================

    def commit(self):

        if self.conn:

            self.conn.commit()

    # ======================================================
    # ROLLBACK
    # ======================================================

    def rollback(self):

        if self.conn:

            self.conn.rollback()

    # ======================================================
    # CERRAR
    # ======================================================

    def cerrar(self):

        try:

            if self.cursor:

                self.cursor.close()

        except:

            pass

        try:

            if self.conn:

                self.conn.close()

        except:

            pass

        logger.info("Conexión cerrada.")

    # ======================================================
    # EJECUTAR CONSULTA
    # ======================================================

    def execute(self, sql, parametros=None):

        if parametros is None:

            self.cursor.execute(sql)

        else:

            self.cursor.execute(sql, parametros)

    # ======================================================
    # EJECUTAR MUCHOS REGISTROS
    # ======================================================

    def executemany(self, sql, datos):

        self.cursor.executemany(sql, datos)

    # ======================================================
    # OBTENER UN REGISTRO
    # ======================================================

    def fetchone(self):

        return self.cursor.fetchone()

    # ======================================================
    # OBTENER TODOS
    # ======================================================

    def fetchall(self):

        return self.cursor.fetchall()

    # ======================================================
    # VALIDAR SI EXISTE UNA SOLICITUD
    # ======================================================

    #def existe_solicitud(self, id_solicitud):

    #    sql = """

    #        SELECT 1
    #        FROM dbo.Solicitudes
    #        WHERE ID_SOLICITUD = ?

    #    """

    #    self.cursor.execute(sql, id_solicitud)

    #    return self.cursor.fetchone() is not None

    # ======================================================
    # VALIDAR SI EL ARCHIVO YA FUE PROCESADO
    # ======================================================

    def existe_archivo(self, nombre_archivo):

        sql = """

            SELECT 1
            FROM dbo.Auditoria
            WHERE NombreArchivo = ?

        """

        self.cursor.execute(sql, nombre_archivo)

        return self.cursor.fetchone() is not None