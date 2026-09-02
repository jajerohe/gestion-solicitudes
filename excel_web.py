import unicodedata
import pandas as pd

HOJAS = ["DETALLE_GENERAL", "DETALLE_FUNCIONALES"]

PRODUCT_OWNERS = {
    "ALIRIO GUERRERO PEÑA",
    "DAVID CABAL ORDONEZ",
    "WILLIAM ANTONIO DELGADO PEÑA",
}

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

def procesar_hoja(df, hoja):
    df = normalizar_columnas(df)
    validar_columnas(df)

    df["PRODUCT_OWNER"] = (
        df["PRODUCT_OWNER"].fillna("").astype(str).str.strip().str.upper()
    )
    df = df[df["PRODUCT_OWNER"].isin(PRODUCT_OWNERS)].copy()

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
            valores.append(limpiar_valor(fila.get(columna)))
    return tuple(valores)

def analizar_excel(archivo):
    resultados = []
    excel = pd.ExcelFile(archivo)

    for hoja in HOJAS:
        if hoja not in excel.sheet_names:
            continue
        df = pd.read_excel(excel, sheet_name=hoja)
        df = procesar_hoja(df, hoja)

        for _, fila in df.iterrows():
            resultados.append({
                "HOJA": hoja,
                "ID_SOLICITUD": limpiar_valor(fila.get("ID_SOLICITUD")),
                "PRODUCT_OWNER": limpiar_valor(fila.get("PRODUCT_OWNER")),
                "STATUS": limpiar_valor(fila.get("STATUS")),
                "FECHA_APERTURA": limpiar_valor(fila.get("FECHA_APERTURA")),
                "TITULO": limpiar_valor(fila.get("TITULO")),
                "RANGTIEMPO": limpiar_valor(fila.get("RANGTIEMPO")),
                "DIFDIAS": limpiar_valor(fila.get("DIFDIAS")),
            })

    return pd.DataFrame(resultados)

def cargar_excel(archivo, db):
    resultado = {
        "generales": 0, "funcionales": 0, "duplicados": 0,
        "errores": 0, "hojas": []
    }

    excel = pd.ExcelFile(archivo)

    sql = '''
        INSERT INTO public."Solicitudes"
        ("ORIGEN","TIPO","ID_SOLICITUD","TI_PRESTADOR","GRUPO_ASIGNACION",
         "ASIGNADO_A","NOMBRE_ASIGNATARIO","CORREO_ASIGNATARIO","CATEGORIA",
         "CURRENT_PHASE","CONTACTO","DESTINATARIO","STATUS","FECHA_APERTURA",
         "RANGTIEMPO","TITULO","DESCRIPCION","SUBSERVICIO_AFECTADO",
         "PRODUCT_OWNER","DIFDIAS")
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                %s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT ("ID_SOLICITUD") DO NOTHING
        RETURNING "ID_SOLICITUD"
    '''

    for hoja in HOJAS:
        if hoja not in excel.sheet_names:
            continue

        df = procesar_hoja(
            pd.read_excel(excel, sheet_name=hoja), hoja
        )
        resultado["hojas"].append({"hoja": hoja, "registros": len(df)})

        for _, fila in df.iterrows():
            try:
                db.execute(sql, preparar_registro(fila, hoja))
                if db.fetchone():
                    if hoja == "DETALLE_GENERAL":
                        resultado["generales"] += 1
                    else:
                        resultado["funcionales"] += 1
                else:
                    resultado["duplicados"] += 1
            except Exception:
                resultado["errores"] += 1
                raise

    return resultado
