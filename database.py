# -*- coding: utf-8 -*-

"""
Conexión a PostgreSQL / Supabase
"""

import streamlit as st
import psycopg


class Database:

    def __init__(self):
        self.conn = None
        self.cursor = None

    # ======================================================
    # CONECTAR
    # ======================================================

    def conectar(self):

        try:

            self.conn = psycopg.connect(
                host=st.secrets["database"]["host"],
                port=st.secrets["database"]["port"],
                dbname=st.secrets["database"]["database"],
                user=st.secrets["database"]["user"],
                password=st.secrets["database"]["password"],
            )

            self.conn.autocommit = False

            self.cursor = self.conn.cursor()

            return self.cursor

        except Exception as ex:

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

        except Exception:
            pass

        try:

            if self.conn:
                self.conn.close()

        except Exception:
            pass

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
