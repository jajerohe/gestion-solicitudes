import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import calendar
import pyodbc

# ============================================================
# CONFIGURACIÓN SQL SERVER
# ============================================================
SERVER = "localhost"
DATABASE = "Seguimiento"
DRIVER = "ODBC Driver 17 for SQL Server"

CONNECTION_STRING = (
    f"DRIVER={{{DRIVER}}};"
    f"SERVER={SERVER};"
    f"DATABASE={DATABASE};"
    "Trusted_Connection=yes;"
)

# ============================================================
# CONEXIÓN
# ============================================================
def conectar():
    return pyodbc.connect(CONNECTION_STRING)


# ============================================================
# CREAR TABLA DE GESTIONES SI NO EXISTE
# ============================================================
def crear_tabla_gestiones():
    conn = conectar()
    cursor = conn.cursor()

    sql = """
    IF OBJECT_ID('dbo.Gestiones', 'U') IS NULL
    BEGIN
        CREATE TABLE dbo.Gestiones
        (
            ID_GESTION INT IDENTITY(1,1) NOT NULL,
            FECHA_GESTION DATETIME NOT NULL,
            ID_SOLICITUD VARCHAR(50) NOT NULL,
            OBSERVACION NVARCHAR(MAX) NULL,

            CONSTRAINT PK_Gestiones
                PRIMARY KEY (ID_GESTION),

            CONSTRAINT FK_Gestiones_Solicitudes
                FOREIGN KEY (ID_SOLICITUD)
                REFERENCES dbo.Solicitudes(ID_SOLICITUD)
        );
    END
    """

    cursor.execute(sql)
    conn.commit()
    cursor.close()
    conn.close()


# ============================================================
# APLICACIÓN
# ============================================================
class GestionSolicitudesApp:

    def __init__(self, root):
        self.root = root
        self.root.title("GESTIÓN DE SOLICITUDES")
        self.root.geometry("1450x850")
        self.root.minsize(1200, 700)

        self.id_solicitud_actual = None

        self.crear_interfaz()
        self.cargar_solicitudes()

    # --------------------------------------------------------
    # INTERFAZ
    # --------------------------------------------------------
    def crear_interfaz(self):

        titulo = tk.Label(
            self.root,
            text="GESTIÓN DE SOLICITUDES",
            font=("Arial", 18, "bold")
        )
        titulo.pack(pady=10)

        # =========================
        # BUSCADOR
        # =========================
        frame_busqueda = tk.Frame(self.root)
        frame_busqueda.pack(fill="x", padx=15, pady=5)

        tk.Label(
            frame_busqueda,
            text="Buscar solicitud:",
            font=("Arial", 10, "bold")
        ).pack(side="left")

        self.txt_busqueda = tk.Entry(
            frame_busqueda,
            width=35,
            font=("Arial", 10)
        )
        self.txt_busqueda.pack(side="left", padx=8)

        self.txt_busqueda.bind(
            "<KeyRelease>",
            lambda event: self.filtrar_solicitudes()
        )

        tk.Button(
            frame_busqueda,
            text="Actualizar",
            command=self.cargar_solicitudes,
            width=12
        ).pack(side="left", padx=5)

        # =========================
        # TABLA SOLICITUDES
        # =========================
        frame_tabla = tk.Frame(self.root)
        frame_tabla.pack(fill="both", expand=False, padx=15, pady=5)

        columnas = (
            "ID_SOLICITUD",
            "TITULO",
            "FECHA_APERTURA",
            "SUBSERVICIO_AFECTADO",
            "PRODUCT_OWNER",
            "STATUS",
            "ASIGNADO_A",
            "NOMBRE_ASIGNATARIO",
            "CORREO_ASIGNATARIO"
        )

        self.tree = ttk.Treeview(
            frame_tabla,
            columns=columnas,
            show="headings",
            height=12
        )

        encabezados = {
            "ID_SOLICITUD": "Id_Solicitud",
            "TITULO": "Titulo_Solicitud",
            "FECHA_APERTURA": "Fecha_Apertura",
            "SUBSERVICIO_AFECTADO": "Subservicio_Afectado",
            "PRODUCT_OWNER": "Product_Owner",
            "STATUS": "Estado",
            "ASIGNADO_A": "Asignado_A",
            "NOMBRE_ASIGNATARIO": "Nombre_Asignatario",
            "CORREO_ASIGNATARIO": "Correo_Asignatario"
        }

        anchos = {
            "ID_SOLICITUD": 120,
            "TITULO": 300,
            "FECHA_APERTURA": 160,
            "SUBSERVICIO_AFECTADO": 180,
            "PRODUCT_OWNER": 220,
            "STATUS": 120,
            "ASIGNADO_A": 120,
            "NOMBRE_ASIGNATARIO": 230,
            "CORREO_ASIGNATARIO": 250
        }

        for col in columnas:
            self.tree.heading(col, text=encabezados[col])
            self.tree.column(
                col,
                width=anchos[col],
                minwidth=80,
                anchor="w"
            )

        scroll_y = ttk.Scrollbar(
            frame_tabla,
            orient="vertical",
            command=self.tree.yview
        )

        scroll_x = ttk.Scrollbar(
            frame_tabla,
            orient="horizontal",
            command=self.tree.xview
        )

        self.tree.configure(
            yscrollcommand=scroll_y.set,
            xscrollcommand=scroll_x.set
        )

        self.tree.grid(row=0, column=0, sticky="nsew")
        scroll_y.grid(row=0, column=1, sticky="ns")
        scroll_x.grid(row=1, column=0, sticky="ew")

        frame_tabla.grid_rowconfigure(0, weight=1)
        frame_tabla.grid_columnconfigure(0, weight=1)

        self.tree.bind(
            "<<TreeviewSelect>>",
            self.seleccionar_solicitud
        )

        # =========================
        # DATOS SOLICITUD
        # =========================
        frame_datos = tk.LabelFrame(
            self.root,
            text="Información de la solicitud",
            font=("Arial", 10, "bold")
        )
        frame_datos.pack(fill="x", padx=15, pady=8)

        self.lbl_id = tk.Label(frame_datos, text="ID_SOLICITUD: -")
        self.lbl_id.grid(row=0, column=0, sticky="w", padx=10, pady=5)

        self.lbl_titulo = tk.Label(
            frame_datos,
            text="TITULO: -",
            anchor="w"
        )
        self.lbl_titulo.grid(
            row=0, column=1,
            sticky="w",
            padx=10,
            pady=5
        )

        self.lbl_owner = tk.Label(
            frame_datos,
            text="PRODUCT_OWNER: -"
        )
        self.lbl_owner.grid(
            row=0, column=2,
            sticky="w",
            padx=10,
            pady=5
        )

        self.lbl_asignado = tk.Label(
            frame_datos,
            text="ASIGNADO: -"
        )
        self.lbl_asignado.grid(
            row=1, column=0,
            sticky="w",
            padx=10,
            pady=5
        )

        self.lbl_correo = tk.Label(
            frame_datos,
            text="CORREO: -"
        )
        self.lbl_correo.grid(
            row=1, column=1,
            sticky="w",
            padx=10,
            pady=5
        )

        # =========================
        # FECHA DE OBSERVACIÓN
        # =========================
        tk.Label(
            self.root,
            text="Fecha_Observacion",
            font=("Arial", 10, "bold")
        ).pack(anchor="w", padx=85, pady=(5, 2))

        frame_fecha_observacion = tk.Frame(self.root)
        frame_fecha_observacion.pack(
            fill="x",
            padx=85,
            pady=(0, 6)
        )

        self.txt_fecha_observacion = tk.Entry(
            frame_fecha_observacion,
            width=22
        )
        self.txt_fecha_observacion.pack(side="left")

        tk.Button(
            frame_fecha_observacion,
            text="📅 Seleccionar",
            command=self.seleccionar_fecha_observacion,
            width=13
        ).pack(side="left", padx=(6, 0))

        # =========================
        # OBSERVACIÓN
        # =========================
        tk.Label(
            self.root,
            text="Observación",
            font=("Arial", 10, "bold")
        ).pack(anchor="w", padx=85, pady=(5, 2))

        self.txt_observacion = tk.Text(
            self.root,
            height=5,
            font=("Arial", 10),
            wrap="word"
        )
        self.txt_observacion.pack(
            fill="x",
            padx=85,
            pady=2
        )

        # =========================
        # CAMPOS DE ACTUALIZACIÓN
        # =========================
        frame_actualizacion = tk.Frame(self.root)
        frame_actualizacion.pack(fill="x", padx=85, pady=10)

        # Fecha cierre
        tk.Label(
            frame_actualizacion,
            text="Fecha_Cierre",
            font=("Arial", 10, "bold")
        ).grid(row=0, column=0, sticky="w")

        frame_fecha_cierre = tk.Frame(frame_actualizacion)
        frame_fecha_cierre.grid(
            row=1, column=0,
            padx=(0, 50),
            pady=3,
            sticky="w"
        )

        self.txt_fecha_cierre = tk.Entry(
            frame_fecha_cierre,
            width=22
        )
        self.txt_fecha_cierre.pack(side="left")

        tk.Button(
            frame_fecha_cierre,
            text="📅 Seleccionar",
            command=self.seleccionar_fecha_cierre,
            width=13
        ).pack(side="left", padx=(6, 0))

        # Status
        tk.Label(
            frame_actualizacion,
            text="Estado",
            font=("Arial", 10, "bold")
        ).grid(row=0, column=2, sticky="w")

        self.cmb_status = ttk.Combobox(
            frame_actualizacion,
            width=25,
            state="readonly",
            values=[
                "Cancelled",
                "Completado",
                "En curso",
                "Fulfilled",
                "In Progress",
                "Pendiente de cliente",
                "Pendiente de proveedor",
                "Resuelto",
                "Suspendido",
                "Trabajo en curso"
            ]
        )
        self.cmb_status.grid(
            row=1, column=2,
            padx=(0, 50),
            pady=3
        )

        # Current phase
        tk.Label(
            frame_actualizacion,
            text="Codigo_Cierre",
            font=("Arial", 10, "bold")
        ).grid(row=0, column=3, sticky="w")

        self.cmb_codigo_cierre = ttk.Combobox(
            frame_actualizacion,
            width=25,
            state="readonly",
            values=[
                "Cancelado por incumplimiento de politicas",
                "Cancelado por el usuario",
                "Resuelto por soporte tecnico"
            ]
        )
        self.cmb_codigo_cierre.grid(
            row=1, column=3,
            pady=3
        )

        # =========================
        # BOTONES
        # =========================
        frame_botones = tk.Frame(self.root)
        frame_botones.pack(pady=8)

        tk.Button(
            frame_botones,
            text="Guardar Gestion",
            command=self.guardar_gestion,
            width=22,
            height=2
        ).pack(side="left", padx=10)

        tk.Button(
            frame_botones,
            text="Actualizar Solicitud",
            command=self.actualizar_solicitud,
            width=22,
            height=2
        ).pack(side="left", padx=10)

        tk.Button(
            frame_botones,
            text="Limpiar Formulario",
            command=self.limpiar_formulario,
            width=22,
            height=2
        ).pack(side="left", padx=10)

        # =========================
        # HISTORIAL
        # =========================
        frame_historial = tk.LabelFrame(
            self.root,
            text="Historial de gestiones",
            font=("Arial", 10, "bold")
        )
        frame_historial.pack(
            fill="both",
            expand=True,
            padx=15,
            pady=8
        )

        columnas_hist = (
            "ID_GESTION",
            "FECHA_GESTION",
            "OBSERVACION"
        )

        self.tree_historial = ttk.Treeview(
            frame_historial,
            columns=columnas_hist,
            show="headings",
            height=6
        )

        self.tree_historial.heading(
            "ID_GESTION",
            text="Id_Gestión"
        )
        self.tree_historial.heading(
            "FECHA_GESTION",
            text="Fecha_Gestión"
        )
        self.tree_historial.heading(
            "OBSERVACION",
            text="Observación"
        )

        self.tree_historial.column(
            "ID_GESTION",
            width=100
        )
        self.tree_historial.column(
            "FECHA_GESTION",
            width=170
        )
        self.tree_historial.column(
            "OBSERVACION",
            width=1000
        )

        self.tree_historial.pack(
            fill="both",
            expand=True,
            padx=5,
            pady=5
        )

    # --------------------------------------------------------
    # CARGAR SOLICITUDES
    # --------------------------------------------------------
    def cargar_solicitudes(self):

        try:
            conn = conectar()
            cursor = conn.cursor()

            sql = """
            SELECT ID_SOLICITUD,
                TITULO,
                FECHA_APERTURA,
                SUBSERVICIO_AFECTADO,
                PRODUCT_OWNER,
                STATUS,
                ASIGNADO_A,
                NOMBRE_ASIGNATARIO,
                CORREO_ASIGNATARIO
            FROM Solicitudes
            WHERE STATUS NOT IN ('RESOLVED','COMPLETADO')
            AND FECHA_CIERRE IS NULL
            ORDER BY FECHA_APERTURA ASC
            """

            cursor.execute(sql)
            registros = cursor.fetchall()

            self.todos_los_registros = registros

            self.mostrar_registros(registros)

            cursor.close()
            conn.close()

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No fue posible cargar las solicitudes:\n\n{e}"
            )

    # --------------------------------------------------------
    # MOSTRAR REGISTROS
    # --------------------------------------------------------
    def mostrar_registros(self, registros):

        for item in self.tree.get_children():
            self.tree.delete(item)

        for registro in registros:

            valores = []

            for valor in registro:

                if valor is None:
                    valores.append("")
                elif isinstance(valor, datetime):
                    valores.append(
                        valor.strftime("%Y-%m-%d %H:%M:%S")
                    )
                else:
                    valores.append(str(valor))

            self.tree.insert(
                "",
                "end",
                values=valores
            )

    # --------------------------------------------------------
    # FILTRAR
    # --------------------------------------------------------
    def filtrar_solicitudes(self):

        texto = self.txt_busqueda.get().strip().lower()

        if not texto:
            self.mostrar_registros(
                self.todos_los_registros
            )
            return

        filtrados = []

        for registro in self.todos_los_registros:

            registro_texto = " ".join(
                "" if x is None else str(x)
                for x in registro
            ).lower()

            if texto in registro_texto:
                filtrados.append(registro)

        self.mostrar_registros(filtrados)

    # --------------------------------------------------------
    # SELECCIONAR SOLICITUD
    # --------------------------------------------------------
    def seleccionar_solicitud(self, event=None):

        seleccion = self.tree.selection()

        if not seleccion:
            return

        item = self.tree.item(seleccion[0])
        valores = item["values"]

        if not valores:
            return

        self.id_solicitud_actual = valores[0]

        self.lbl_id.config(
            text=f"ID_SOLICITUD: {valores[0]}"
        )

        self.lbl_titulo.config(
            text=f"TITULO: {valores[1]}"
        )

        self.lbl_owner.config(
            text=f"PRODUCT_OWNER: {valores[5]}"
        )

        self.lbl_asignado.config(
            text=f"ASIGNADO: {valores[7]}"
        )

        self.lbl_correo.config(
            text=f"CORREO: {valores[8]}"
        )

        self.cargar_datos_actuales(
            self.id_solicitud_actual
        )

        self.cargar_historial(
            self.id_solicitud_actual
        )

    # --------------------------------------------------------
    # CARGAR DATOS ACTUALES
    # --------------------------------------------------------
    def cargar_datos_actuales(self, id_solicitud):

        try:
            conn = conectar()
            cursor = conn.cursor()

            sql = """
            SELECT
                FECHA_CIERRE,
                STATUS,
                CODIGO_CIERRE
            FROM dbo.Solicitudes
            WHERE ID_SOLICITUD = ?
            """

            cursor.execute(
                sql,
                id_solicitud
            )

            registro = cursor.fetchone()

            if registro:

                fecha_cierre = registro[0]

                if fecha_cierre:
                    self.txt_fecha_cierre.delete(
                        0, tk.END
                    )
                    self.txt_fecha_cierre.insert(
                        0,
                        fecha_cierre.strftime(
                            "%Y-%m-%d %H:%M:%S"
                        )
                    )
                else:
                    self.txt_fecha_cierre.delete(
                        0, tk.END
                    )

                self.cmb_status.set(
                    registro[1] or ""
                )

                self.cmb_codigo_cierre.set(
                    registro[2] or ""
                )

            cursor.close()
            conn.close()

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No fue posible consultar la solicitud:\n\n{e}"
            )

    # --------------------------------------------------------
    # SELECCIONAR FECHA Y HORA DE CIERRE
    # --------------------------------------------------------
    def seleccionar_fecha_cierre(self):

        ventana = tk.Toplevel(self.root)
        ventana.title("Seleccionar fecha y hora de cierre")
        ventana.resizable(False, False)
        ventana.transient(self.root)
        ventana.grab_set()

        # Fecha inicial: la que ya esté en el textbox, si es válida;
        # de lo contrario, fecha/hora actual.
        texto_actual = self.txt_fecha_cierre.get().strip()

        try:
            fecha_actual = datetime.strptime(
                texto_actual,
                "%Y-%m-%d %H:%M:%S"
            )
        except ValueError:
            fecha_actual = datetime.now()

        estado = {
            "anio": fecha_actual.year,
            "mes": fecha_actual.month,
            "dia": fecha_actual.day
        }

        # --------------------------------------------------------
        # Encabezado del calendario
        # --------------------------------------------------------
        frame_calendario = tk.Frame(ventana)
        frame_calendario.pack(padx=12, pady=10)

        lbl_mes = tk.Label(
            frame_calendario,
            font=("Arial", 12, "bold")
        )
        lbl_mes.grid(row=0, column=1, padx=20, pady=5)

        def cambiar_mes(delta):
            mes = estado["mes"] + delta
            anio = estado["anio"]

            if mes < 1:
                mes = 12
                anio -= 1
            elif mes > 12:
                mes = 1
                anio += 1

            estado["mes"] = mes
            estado["anio"] = anio

            # Ajustar día si el nuevo mes tiene menos días
            ultimo_dia = calendar.monthrange(anio, mes)[1]
            if estado["dia"] > ultimo_dia:
                estado["dia"] = ultimo_dia

            dibujar_calendario()

        tk.Button(
            frame_calendario,
            text="◀",
            width=4,
            command=lambda: cambiar_mes(-1)
        ).grid(row=0, column=0)

        tk.Button(
            frame_calendario,
            text="▶",
            width=4,
            command=lambda: cambiar_mes(1)
        ).grid(row=0, column=2)

        frame_dias = tk.Frame(frame_calendario)
        frame_dias.grid(
            row=1,
            column=0,
            columnspan=3,
            pady=5
        )

        def seleccionar_dia(dia):
            estado["dia"] = dia
            dibujar_calendario()

        def dibujar_calendario():
            for widget in frame_dias.winfo_children():
                widget.destroy()

            meses = [
                "",
                "Enero", "Febrero", "Marzo", "Abril",
                "Mayo", "Junio", "Julio", "Agosto",
                "Septiembre", "Octubre", "Noviembre", "Diciembre"
            ]

            lbl_mes.config(
                text=f"{meses[estado['mes']]} {estado['anio']}"
            )

            dias_semana = ["L", "M", "X", "J", "V", "S", "D"]

            for columna, nombre in enumerate(dias_semana):
                tk.Label(
                    frame_dias,
                    text=nombre,
                    width=4,
                    font=("Arial", 10, "bold")
                ).grid(row=0, column=columna)

            calendario_mes = calendar.monthcalendar(
                estado["anio"],
                estado["mes"]
            )

            for fila, semana in enumerate(calendario_mes, start=1):
                for columna, dia in enumerate(semana):
                    if dia == 0:
                        tk.Label(
                            frame_dias,
                            text="",
                            width=4
                        ).grid(row=fila, column=columna)
                    else:
                        boton = tk.Button(
                            frame_dias,
                            text=str(dia),
                            width=4,
                            command=lambda d=dia: seleccionar_dia(d)
                        )

                        if dia == estado["dia"]:
                            boton.config(relief="sunken")

                        boton.grid(
                            row=fila,
                            column=columna,
                            padx=1,
                            pady=1
                        )

        # --------------------------------------------------------
        # Hora
        # --------------------------------------------------------
        frame_hora = tk.Frame(ventana)
        frame_hora.pack(pady=(2, 8))

        tk.Label(
            frame_hora,
            text="Hora:",
            font=("Arial", 10, "bold")
        ).pack(side="left", padx=(0, 8))

        hora_var = tk.StringVar(
            value=f"{fecha_actual.hour:02d}"
        )
        minuto_var = tk.StringVar(
            value=f"{fecha_actual.minute:02d}"
        )
        segundo_var = tk.StringVar(
            value=f"{fecha_actual.second:02d}"
        )

        cmb_hora = ttk.Combobox(
            frame_hora,
            textvariable=hora_var,
            values=[f"{i:02d}" for i in range(24)],
            width=4,
            state="readonly"
        )
        cmb_hora.pack(side="left")

        tk.Label(frame_hora, text=":").pack(side="left")

        cmb_minuto = ttk.Combobox(
            frame_hora,
            textvariable=minuto_var,
            values=[f"{i:02d}" for i in range(60)],
            width=4,
            state="readonly"
        )
        cmb_minuto.pack(side="left")

        tk.Label(frame_hora, text=":").pack(side="left")

        cmb_segundo = ttk.Combobox(
            frame_hora,
            textvariable=segundo_var,
            values=[f"{i:02d}" for i in range(60)],
            width=4,
            state="readonly"
        )
        cmb_segundo.pack(side="left")

        # --------------------------------------------------------
        # Botones
        # --------------------------------------------------------
        frame_botones_fecha = tk.Frame(ventana)
        frame_botones_fecha.pack(pady=(0, 12))

        def aceptar_fecha():
            try:
                hora = int(hora_var.get())
                minuto = int(minuto_var.get())
                segundo = int(segundo_var.get())

                fecha = datetime(
                    estado["anio"],
                    estado["mes"],
                    estado["dia"],
                    hora,
                    minuto,
                    segundo
                )

                self.txt_fecha_cierre.delete(0, tk.END)
                self.txt_fecha_cierre.insert(
                    0,
                    fecha.strftime("%Y-%m-%d %H:%M:%S")
                )

                ventana.destroy()

            except Exception as e:
                messagebox.showerror(
                    "Fecha inválida",
                    f"No fue posible establecer la fecha y hora:\n\n{e}",
                    parent=ventana
                )

        tk.Button(
            frame_botones_fecha,
            text="ACEPTAR",
            command=aceptar_fecha,
            width=12
        ).pack(side="left", padx=5)

        tk.Button(
            frame_botones_fecha,
            text="CANCELAR",
            command=ventana.destroy,
            width=12
        ).pack(side="left", padx=5)

        dibujar_calendario()

        # Centrar la ventana respecto a la aplicación
        ventana.update_idletasks()
        x = self.root.winfo_x() + (
            self.root.winfo_width() - ventana.winfo_width()
        ) // 2
        y = self.root.winfo_y() + (
            self.root.winfo_height() - ventana.winfo_height()
        ) // 2

        ventana.geometry(f"+{max(x, 0)}+{max(y, 0)}")


    # --------------------------------------------------------
    # SELECCIONAR FECHA Y HORA DE OBSERVACIÓN
    # --------------------------------------------------------
    def seleccionar_fecha_observacion(self):

        ventana = tk.Toplevel(self.root)
        ventana.title("Seleccionar fecha y hora de observación")
        ventana.resizable(False, False)
        ventana.transient(self.root)
        ventana.grab_set()

        texto_actual = self.txt_fecha_observacion.get().strip()

        try:
            fecha_actual = datetime.strptime(
                texto_actual,
                "%Y-%m-%d %H:%M:%S"
            )
        except ValueError:
            fecha_actual = datetime.now()

        estado = {
            "anio": fecha_actual.year,
            "mes": fecha_actual.month,
            "dia": fecha_actual.day
        }

        frame_calendario = tk.Frame(ventana)
        frame_calendario.pack(padx=12, pady=10)

        lbl_mes = tk.Label(
            frame_calendario,
            font=("Arial", 12, "bold")
        )
        lbl_mes.grid(row=0, column=1, padx=20, pady=5)

        def cambiar_mes(delta):
            mes = estado["mes"] + delta
            anio = estado["anio"]

            if mes < 1:
                mes = 12
                anio -= 1
            elif mes > 12:
                mes = 1
                anio += 1

            estado["mes"] = mes
            estado["anio"] = anio

            ultimo_dia = calendar.monthrange(anio, mes)[1]
            if estado["dia"] > ultimo_dia:
                estado["dia"] = ultimo_dia

            dibujar_calendario()

        tk.Button(
            frame_calendario,
            text="◀",
            width=4,
            command=lambda: cambiar_mes(-1)
        ).grid(row=0, column=0)

        tk.Button(
            frame_calendario,
            text="▶",
            width=4,
            command=lambda: cambiar_mes(1)
        ).grid(row=0, column=2)

        frame_dias = tk.Frame(frame_calendario)
        frame_dias.grid(
            row=1,
            column=0,
            columnspan=3,
            pady=5
        )

        def seleccionar_dia(dia):
            estado["dia"] = dia
            dibujar_calendario()

        def dibujar_calendario():

            for widget in frame_dias.winfo_children():
                widget.destroy()

            meses = [
                "",
                "Enero", "Febrero", "Marzo", "Abril",
                "Mayo", "Junio", "Julio", "Agosto",
                "Septiembre", "Octubre", "Noviembre", "Diciembre"
            ]

            lbl_mes.config(
                text=f"{meses[estado['mes']]} {estado['anio']}"
            )

            dias_semana = ["L", "M", "X", "J", "V", "S", "D"]

            for columna, nombre in enumerate(dias_semana):
                tk.Label(
                    frame_dias,
                    text=nombre,
                    width=4,
                    font=("Arial", 10, "bold")
                ).grid(row=0, column=columna)

            calendario_mes = calendar.monthcalendar(
                estado["anio"],
                estado["mes"]
            )

            for fila, semana in enumerate(calendario_mes, start=1):

                for columna, dia in enumerate(semana):

                    if dia == 0:
                        tk.Label(
                            frame_dias,
                            text="",
                            width=4
                        ).grid(row=fila, column=columna)

                    else:

                        boton = tk.Button(
                            frame_dias,
                            text=str(dia),
                            width=4,
                            command=lambda d=dia: seleccionar_dia(d)
                        )

                        if dia == estado["dia"]:
                            boton.config(relief="sunken")

                        boton.grid(
                            row=fila,
                            column=columna,
                            padx=1,
                            pady=1
                        )

        frame_hora = tk.Frame(ventana)
        frame_hora.pack(pady=(2, 8))

        tk.Label(
            frame_hora,
            text="Hora:",
            font=("Arial", 10, "bold")
        ).pack(side="left", padx=(0, 8))

        hora_var = tk.StringVar(
            value=f"{fecha_actual.hour:02d}"
        )
        minuto_var = tk.StringVar(
            value=f"{fecha_actual.minute:02d}"
        )
        segundo_var = tk.StringVar(
            value=f"{fecha_actual.second:02d}"
        )

        ttk.Combobox(
            frame_hora,
            textvariable=hora_var,
            values=[f"{i:02d}" for i in range(24)],
            width=4,
            state="readonly"
        ).pack(side="left")

        tk.Label(frame_hora, text=":").pack(side="left")

        ttk.Combobox(
            frame_hora,
            textvariable=minuto_var,
            values=[f"{i:02d}" for i in range(60)],
            width=4,
            state="readonly"
        ).pack(side="left")

        tk.Label(frame_hora, text=":").pack(side="left")

        ttk.Combobox(
            frame_hora,
            textvariable=segundo_var,
            values=[f"{i:02d}" for i in range(60)],
            width=4,
            state="readonly"
        ).pack(side="left")

        frame_botones_fecha = tk.Frame(ventana)
        frame_botones_fecha.pack(pady=(0, 12))

        def aceptar_fecha():

            try:
                fecha = datetime(
                    estado["anio"],
                    estado["mes"],
                    estado["dia"],
                    int(hora_var.get()),
                    int(minuto_var.get()),
                    int(segundo_var.get())
                )

                self.txt_fecha_observacion.delete(0, tk.END)
                self.txt_fecha_observacion.insert(
                    0,
                    fecha.strftime("%Y-%m-%d %H:%M:%S")
                )

                ventana.destroy()

            except Exception as e:

                messagebox.showerror(
                    "Fecha inválida",
                    f"No fue posible establecer la fecha y hora:\n\n{e}",
                    parent=ventana
                )

        tk.Button(
            frame_botones_fecha,
            text="ACEPTAR",
            command=aceptar_fecha,
            width=12
        ).pack(side="left", padx=5)

        tk.Button(
            frame_botones_fecha,
            text="CANCELAR",
            command=ventana.destroy,
            width=12
        ).pack(side="left", padx=5)

        dibujar_calendario()

        ventana.update_idletasks()

        x = self.root.winfo_x() + (
            self.root.winfo_width() - ventana.winfo_width()
        ) // 2

        y = self.root.winfo_y() + (
            self.root.winfo_height() - ventana.winfo_height()
        ) // 2

        ventana.geometry(
            f"+{max(x, 0)}+{max(y, 0)}"
        )


    # --------------------------------------------------------
    # HISTORIAL
    # --------------------------------------------------------
    def cargar_historial(self, id_solicitud):

        for item in self.tree_historial.get_children():
            self.tree_historial.delete(item)

        try:
            conn = conectar()
            cursor = conn.cursor()

            sql = """
            SELECT
                ID_GESTION,
                FECHA_GESTION,
                OBSERVACION
            FROM dbo.Gestiones
            WHERE ID_SOLICITUD = ?
            ORDER BY FECHA_GESTION DESC
            """

            cursor.execute(
                sql,
                id_solicitud
            )

            registros = cursor.fetchall()

            for registro in registros:

                fecha = registro[1]

                if isinstance(fecha, datetime):
                    fecha = fecha.strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )

                self.tree_historial.insert(
                    "",
                    "end",
                    values=(
                        registro[0],
                        fecha,
                        registro[2] or ""
                    )
                )

            cursor.close()
            conn.close()

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No fue posible cargar el historial:\n\n{e}"
            )

    # --------------------------------------------------------
    # GUARDAR GESTIÓN
    # --------------------------------------------------------
    def guardar_gestion(self):

        if not self.id_solicitud_actual:
            messagebox.showwarning(
                "Solicitud",
                "Seleccione primero una solicitud."
            )
            return

        observacion = self.txt_observacion.get(
            "1.0",
            tk.END
        ).strip()

        fecha_observacion = self.txt_fecha_observacion.get().strip()

        if not fecha_observacion:
            messagebox.showwarning(
                "Fecha de observación",
                "Debe seleccionar la fecha y hora de la observación."
            )
            return

        try:
            fecha_observacion = datetime.strptime(
                fecha_observacion,
                "%Y-%m-%d %H:%M:%S"
            )
        except ValueError:
            messagebox.showwarning(
                "Fecha inválida",
                "La fecha de observación debe tener el formato:\n"
                "YYYY-MM-DD HH:MM:SS"
            )
            return

        if not observacion:
            messagebox.showwarning(
                "Observación",
                "Debe ingresar una observación."
            )
            return

        try:
            conn = conectar()
            cursor = conn.cursor()

            # Evitar duplicados exactos
            sql_validacion = """
            SELECT COUNT(*)
            FROM dbo.Gestiones
            WHERE ID_SOLICITUD = ?
              AND OBSERVACION = ?
            """

            cursor.execute(
                sql_validacion,
                self.id_solicitud_actual,
                observacion
            )

            existe = cursor.fetchone()[0]

            if existe > 0:
                conn.close()

                messagebox.showwarning(
                    "Gestión duplicada",
                    "Ya existe una gestión con la misma observación para esta solicitud."
                )
                return

            sql = """
            INSERT INTO dbo.Gestiones
            (
                FECHA_GESTION,
                ID_SOLICITUD,
                OBSERVACION
            )
            VALUES
            (
                ?,
                ?,
                ?
            )
            """

            cursor.execute(
                sql,
                fecha_observacion,
                self.id_solicitud_actual,
                observacion
            )

            conn.commit()
            cursor.close()
            conn.close()

            self.txt_observacion.delete(
                "1.0",
                tk.END
            )

            self.cargar_historial(
                self.id_solicitud_actual
            )

            messagebox.showinfo(
                "Gestión",
                "La gestión fue registrada correctamente."
            )

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No fue posible guardar la gestión:\n\n{e}"
            )

    # --------------------------------------------------------
    # ACTUALIZAR SOLICITUD
    # --------------------------------------------------------
    def actualizar_solicitud(self):

        if not self.id_solicitud_actual:
            messagebox.showwarning(
                "Solicitud",
                "Seleccione primero una solicitud."
            )
            return

        fecha_cierre = self.txt_fecha_cierre.get().strip()
        status = self.cmb_status.get().strip()
        codigo_cierre = self.cmb_codigo_cierre.get().strip()

        opciones_codigo_cierre = (
            "Cancelado por incumplimiento de politicas",
            "Cancelado por el usuario",
            "Resuelto por soporte tecnico"
        )

        if codigo_cierre and codigo_cierre not in opciones_codigo_cierre:
            messagebox.showwarning(
                "Código de cierre",
                "Seleccione un Código_Cierre válido."
            )
            return

        # Convertir fecha vacía a NULL
        if fecha_cierre == "":
            fecha_cierre = None
        else:
            try:
                fecha_cierre = datetime.strptime(
                    fecha_cierre,
                    "%Y-%m-%d %H:%M:%S"
                )
            except ValueError:
                messagebox.showwarning(
                    "Fecha inválida",
                    "La fecha de cierre debe tener el formato:\n"
                    "YYYY-MM-DD HH:MM:SS"
                )
                return

        try:
            conn = conectar()
            cursor = conn.cursor()

            sql = """
            UPDATE dbo.Solicitudes
            SET
                FECHA_CIERRE = ?,
                STATUS = ?,
                CODIGO_CIERRE = ?
            WHERE ID_SOLICITUD = ?
            """

            cursor.execute(
                sql,
                fecha_cierre,
                status if status else None,
                codigo_cierre if codigo_cierre else None,
                self.id_solicitud_actual
            )

            if cursor.rowcount == 0:
                raise Exception(
                    "No se encontró la solicitud."
                )

            conn.commit()
            cursor.close()
            conn.close()

            self.cargar_solicitudes()

            messagebox.showinfo(
                "Solicitud actualizada",
                "La información de la solicitud fue actualizada correctamente."
            )

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No fue posible actualizar la solicitud:\n\n{e}"
            )

    # --------------------------------------------------------
    # LIMPIAR
    # --------------------------------------------------------
    def limpiar_formulario(self):

        self.id_solicitud_actual = None

        self.tree.selection_remove(
            self.tree.selection()
        )

        self.lbl_id.config(
            text="ID_SOLICITUD: -"
        )

        self.lbl_titulo.config(
            text="TITULO: -"
        )

        self.lbl_owner.config(
            text="PRODUCT_OWNER: -"
        )

        self.lbl_asignado.config(
            text="ASIGNADO: -"
        )

        self.lbl_correo.config(
            text="CORREO: -"
        )

        self.txt_observacion.delete(
            "1.0",
            tk.END
        )

        self.txt_fecha_cierre.delete(
            0,
            tk.END
        )

        self.txt_fecha_observacion.delete(
            0,
            tk.END
        )

        self.cmb_status.set("")
        self.cmb_codigo_cierre.set("")

        for item in self.tree_historial.get_children():
            self.tree_historial.delete(item)


# ============================================================
# EJECUCIÓN
# ============================================================
if __name__ == "__main__":

    try:
        crear_tabla_gestiones()

        root = tk.Tk()

        app = GestionSolicitudesApp(root)

        root.mainloop()

    except Exception as e:

        try:
            messagebox.showerror(
                "Error de conexión",
                f"No fue posible iniciar la aplicación:\n\n{e}"
            )
        except Exception:
            print(
                "No fue posible iniciar la aplicación:"
            )
            print(e)
