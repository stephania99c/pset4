"""Lectura de la OBT del PSet 2 desde Snowflake y construccion del target."""

import os
from pathlib import Path
import hashlib

import pandas as pd
import snowflake.connector
from dotenv import load_dotenv
from snowflake.connector.pandas_tools import write_pandas

load_dotenv(Path(__file__).parent.parent / ".env")

TABLA = "CARTERA.GOLD.OBT_CARTERA_DIARIA"
PRODUCCION = "CARTERA.PRODUCCION"  # tablas de la simulacion de produccion (PSet 4)


def conectar():
    return snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        password=os.environ["SNOWFLAKE_PAT"],
        role=os.environ["SNOWFLAKE_ROLE"],
        warehouse=os.environ["SNOWFLAKE_WAREHOUSE"],
    )


def cargar_obt():
    con = conectar()
    df = con.cursor().execute(f"SELECT * FROM {TABLA}").fetch_pandas_all()
    con.close()
    df.columns = [c.lower() for c in df.columns]
    return df


def agregar_target(obt, dias=7):
    """paga_7d = 1 si el credito mejora en los `dias` siguientes al corte:
    sube cuotas_pagadas (pago una cuota completa) o baja dias_mora (cubrio la cuota mas vencida)."""
    obt = obt.copy()
    obt["fecha_corte"] = pd.to_datetime(obt["fecha_corte"])
    obt = obt.sort_values(["numero_operacion", "fecha_corte"])

    # Dias en que cada credito mejora respecto a su corte anterior
    por_credito = obt.groupby("numero_operacion")
    sube_pagadas = por_credito["cuotas_pagadas"].diff() > 0
    baja_mora = por_credito["dias_mora"].diff() < 0
    mejoras = obt.loc[sube_pagadas | baja_mora, ["numero_operacion", "fecha_corte"]]

    # Una mejora en el dia M marca como positivos los cortes M-1, M-2, ..., M-7
    positivos = []
    for k in range(1, dias + 1):
        positivos.append(mejoras.assign(fecha_corte=mejoras["fecha_corte"] - pd.Timedelta(days=k)))
    positivos = pd.concat(positivos).drop_duplicates()
    positivos["paga_7d"] = 1

    obt = obt.merge(positivos, on=["numero_operacion", "fecha_corte"], how="left")
    obt["paga_7d"] = obt["paga_7d"].fillna(0).astype(int)

    # Los ultimos dias no tienen 7 dias de futuro observados: se excluyen
    ultima = obt["fecha_corte"].max() - pd.Timedelta(days=dias)
    return obt[obt["fecha_corte"] <= ultima].reset_index(drop=True)

def huella(df):
    """Primeros 12 caracteres del hash MD5 de una tabla: si cambia un solo dato, cambia la huella."""
    valores = pd.util.hash_pandas_object(df, index=False).values
    return hashlib.md5(valores.tobytes()).hexdigest()[:12]


# --- Tablas de la simulacion de produccion (PSet 4) ---

def leer_tabla(nombre):
    """Lee una tabla del esquema PRODUCCION. Si todavia no existe, devuelve una tabla vacia."""
    con = conectar()
    try:
        df = con.cursor().execute(f"SELECT * FROM {PRODUCCION}.{nombre}").fetch_pandas_all()
    except snowflake.connector.errors.ProgrammingError:
        df = pd.DataFrame()
    con.close()
    df.columns = [c.lower() for c in df.columns]
    return df


def escribir_tabla(df, nombre, reemplazar=False):
    """Agrega filas a una tabla del esquema PRODUCCION (o la reemplaza). La crea si no existe."""
    con = conectar()
    write_pandas(con, df, nombre.upper(), database="CARTERA", schema="PRODUCCION",
                 auto_create_table=True, overwrite=reemplazar, quote_identifiers=False)
    con.close()


def borrar_tabla(nombre):
    """Borra una tabla del esquema PRODUCCION, para repetir la simulacion desde cero."""
    con = conectar()
    con.cursor().execute(f"DROP TABLE IF EXISTS {PRODUCCION}.{nombre}")
    con.close()