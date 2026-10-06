import unicodedata
import pandas as pd

HOJAS = ["DETALLE_GENERAL", "DETALLE_FUNCIONALES"]

COLUMNAS_OBLIGATORIAS = {
    "ID_SOLICITUD", "PRODUCT_OWNER", "STATUS", "FECHA_APERTURA"
}

COLUMNAS_SQL = [
    "ORIGEN", "TIPO", "ID_SOLICITUD", "TI_PRESTADOR",
    "GRUPO_ASIGNACION", "ASIGNADO_A", "NOMBRE_ASIGNATARIO",
    "CORREO_ASIGNATARIO", "CATEGORIA", "CURRENT_PHASE",
    "CONTACTO", "DESTINATARIO", "STATUS", "FECHA_APERTURA",
    "RANGTIEMPO", "TITULO", "DESCRIPCION", "SUBSERVICIO_AFECTADO",
    "PRODUCT_OWNER", "DIFDIAS"
]

def quitar_acentos(texto):
    texto = unicodedata.normalize("NFKD", str(texto))
    return "".join(c for c in texto if not unicodedata.combining(c))

def normalizar_nombre_columna(nombre):
    nombre = quitar_acentos(str(nombre).strip()).upper()
    for c in (" ", "/", "-"):
        nombre = nombre.replace(c, "_")
    while "__" in nombre:
        nombre = nombre.replace("__", "_")
    return nombre

def normalizar_columnas(df):
    df = df.copy()
    df.columns = [normalizar_nombre_columna(c) for c in df.columns]
    return df.rename(columns={
        "SUMA_DE_DIFDIAS": "DIFDIAS",
        "SUMA_DE_DIAS": "DIFDIAS",
    })

def validar_columnas(df):
    faltantes = COLUMNAS_OBLIGATORIAS - set(df.columns)
    if faltantes:
        raise ValueError(
            "Columnas obligatorias faltantes: " + ", ".join(sorted(faltantes))
        )

def limpiar_valor(valor):
    if pd.isna(valor):
        return None
    if isinstance(valor, pd.Timestamp):
        return valor.to_pydatetime()
    if hasattr(valor, "to_pydatetime"):
        return valor.to_pydatetime()
    if isinstance(valor, str):
        valor = valor.strip()
        return valor if valor else None
    return valor

def normalizar_product_owner(valor):
    return " ".join(str(valor or "").split()).upper()

def procesar_hoja(df, hoja, product_owners):
    """Filtra la hoja dejando solo las solicitudes de los Product Owner
    recibidos (los NOMBRE de la tabla PODS)."""
    df = normalizar_columnas(df)
    validar_columnas(df)

    permitidos = {normalizar_product_owner(po) for po in product_owners}
    df["PRODUCT_OWNER"] = df["PRODUCT_OWNER"].map(normalizar_product_owner)
    df = df[df["PRODUCT_OWNER"].isin(permitidos)].copy()

    if "FECHA_APERTURA" in df.columns:
        df["FECHA_APERTURA"] = pd.to_datetime(df["FECHA_APERTURA"], errors="coerce")
    if "FECHA_CIERRE" in df.columns:
        df["FECHA_CIERRE"] = pd.to_datetime(df["FECHA_CIERRE"], errors="coerce")
    if "DIFDIAS" in df.columns:
        df["DIFDIAS"] = pd.to_numeric(df["DIFDIAS"], errors="coerce")

    return df

def preparar_registro(fila, hoja):
    valores = []
    for columna in COLUMNAS_SQL:
        if columna == "ORIGEN":
            valores.append(hoja)
        elif columna == "CURRENT_PHASE":
            valores.append(None)
        else:
            valor = limpiar_valor(fila.get(columna))
            # Los títulos se guardan siempre en MAYÚSCULAS.
            if columna == "TITULO" and isinstance(valor, str):
                valor = valor.upper()
            valores.append(valor)
    return tuple(valores)

def leer_hojas(archivo, product_owners):
    """Lee el Excel una sola vez y devuelve [(hoja, df_filtrado), ...] con las
    solicitudes de los Product Owner recibidos (los NOMBRE de la tabla PODS)."""
    excel = pd.ExcelFile(archivo)
    return [
        (hoja, procesar_hoja(pd.read_excel(excel, sheet_name=hoja), hoja, product_owners))
        for hoja in HOJAS
        if hoja in excel.sheet_names
    ]

COLUMNAS_VISTA_PREVIA = [
    "ID_SOLICITUD", "PRODUCT_OWNER", "STATUS", "FECHA_APERTURA", "TITULO",
    "SUBSERVICIO_AFECTADO", "RANGTIEMPO", "DIFDIAS",
]

def analizar_excel(hojas):
    """Vista previa de las solicitudes a cargar a partir de leer_hojas()."""
    partes = []
    for hoja, df in hojas:
        parte = pd.DataFrame({"HOJA": hoja}, index=df.index)
        for columna in COLUMNAS_VISTA_PREVIA:
            parte[columna] = df[columna].map(limpiar_valor) if columna in df.columns else None
        partes.append(parte)
    if not partes:
        return pd.DataFrame(columns=["HOJA", *COLUMNAS_VISTA_PREVIA])
    return pd.concat(partes, ignore_index=True)

SQL_CARGA = '''
    INSERT INTO public."SOLICITUDES"
    ("ORIGEN","TIPO","ID_SOLICITUD","TI_PRESTADOR","GRUPO_ASIGNACION",
     "ASIGNADO_A","NOMBRE_ASIGNATARIO","CORREO_ASIGNATARIO","CATEGORIA",
     "CURRENT_PHASE","CONTACTO","DESTINATARIO","STATUS","FECHA_APERTURA",
     "RANGTIEMPO","TITULO","DESCRIPCION","SUBSERVICIO_AFECTADO",
     "PRODUCT_OWNER","DIFDIAS")
    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
            %s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    ON CONFLICT ("ID_SOLICITUD") DO UPDATE
    SET
        "ORIGEN" = EXCLUDED."ORIGEN",
        "TIPO" = EXCLUDED."TIPO",
        "TI_PRESTADOR" = EXCLUDED."TI_PRESTADOR",
        "GRUPO_ASIGNACION" = EXCLUDED."GRUPO_ASIGNACION",
        "ASIGNADO_A" = EXCLUDED."ASIGNADO_A",
        "NOMBRE_ASIGNATARIO" = EXCLUDED."NOMBRE_ASIGNATARIO",
        "CORREO_ASIGNATARIO" = EXCLUDED."CORREO_ASIGNATARIO",
        "CATEGORIA" = EXCLUDED."CATEGORIA",
        "CONTACTO" = EXCLUDED."CONTACTO",
        "DESTINATARIO" = EXCLUDED."DESTINATARIO",
        "STATUS" = EXCLUDED."STATUS",
        "FECHA_APERTURA" = EXCLUDED."FECHA_APERTURA",
        "RANGTIEMPO" = EXCLUDED."RANGTIEMPO",
        "TITULO" = EXCLUDED."TITULO",
        "DESCRIPCION" = EXCLUDED."DESCRIPCION",
        "SUBSERVICIO_AFECTADO" = EXCLUDED."SUBSERVICIO_AFECTADO",
        "PRODUCT_OWNER" = EXCLUDED."PRODUCT_OWNER",
        "DIFDIAS" = EXCLUDED."DIFDIAS"
    WHERE public."SOLICITUDES"."FECHA_CIERRE" IS NULL
      AND public."SOLICITUDES"."CODIGO_CIERRE" IS NULL
    RETURNING "ID_SOLICITUD"
'''

def cargar_excel(hojas, db):
    """Carga las solicitudes de leer_hojas() en public."SOLICITUDES".

    Si el ID ya existe, el UPDATE solo se ejecuta cuando la solicitud sigue
    abierta (FECHA_CIERRE y CODIGO_CIERRE son NULL); las cerradas quedan
    protegidas. Todas las filas de una hoja se envían en un solo lote.
    """
    resultado = {
        "generales": 0, "funcionales": 0, "duplicados": 0,
        "errores": 0, "hojas": []
    }

    for hoja, df in hojas:
        resultado["hojas"].append({"hoja": hoja, "registros": len(df)})
        if df.empty:
            continue

        registros = [preparar_registro(fila, hoja) for _, fila in df.iterrows()]
        db.cursor.executemany(SQL_CARGA, registros, returning=True)

        for _ in db.cursor.results():
            # INSERT nuevo o UPDATE de una solicitud abierta.
            if db.cursor.fetchone():
                if hoja == "DETALLE_GENERAL":
                    resultado["generales"] += 1
                else:
                    resultado["funcionales"] += 1
            else:
                # Sin fila en RETURNING: el ID existía y estaba cerrado.
                resultado["duplicados"] += 1

    return resultado
