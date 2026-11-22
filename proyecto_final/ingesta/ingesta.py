"""Ingesta de un dia de cartera hacia Snowflake (esquema RAW).
Uso:  python ingesta.py --fecha 2026-10-01
"""
import argparse
import io
import os
from datetime import datetime, timezone

import pandas as pd
import requests
import snowflake.connector
from snowflake.connector.pandas_tools import write_pandas

FUENTE_URL = os.environ["FUENTE_URL"]


def descargar(nombre_archivo):
    """Devuelve el CSV como tabla de texto, o None si el archivo no existe."""
    respuesta = requests.get(f"{FUENTE_URL}/{nombre_archivo}", timeout=120)
    if respuesta.status_code == 404:
        return None
    respuesta.raise_for_status()
    df = pd.read_csv(io.StringIO(respuesta.text), dtype=str, keep_default_na=False)
    df["_archivo"] = nombre_archivo
    df["_fecha_carga"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    return df


def conectar():
    return snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        password=os.environ["SNOWFLAKE_PAT"],
        role=os.environ["SNOWFLAKE_ROLE"],
        warehouse=os.environ["SNOWFLAKE_WAREHOUSE"],
        database="CARTERA",
        schema="RAW",
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fecha", required=True)
    fecha = parser.parse_args().fecha[:10]

    cartera = descargar(f"cartera_{fecha}.csv")
    if cartera is None:
        print(f"No hay archivo de cartera para {fecha}. Nada que cargar.")
        return

    con = conectar()
    cur = con.cursor()

    columnas = ", ".join(f"{c} VARCHAR" for c in cartera.columns)
    cur.execute(f"CREATE TABLE IF NOT EXISTS CARTERA_DIARIA ({columnas})")
    cur.execute("DELETE FROM CARTERA_DIARIA WHERE FECHA_CORTE = %s", (fecha,))
    write_pandas(con, cartera, "CARTERA_DIARIA", quote_identifiers=False)
    print(f"CARTERA_DIARIA: {len(cartera)} filas cargadas para {fecha}")

    for nombre in ["operaciones", "gestiones", "pagos"]:
        df = descargar(f"{nombre}.csv")
        write_pandas(con, df, nombre.upper(), auto_create_table=True,
                     overwrite=True, quote_identifiers=False)
        print(f"{nombre.upper()}: {len(df)} filas (recarga completa)")

    con.close()


if __name__ == "__main__":
    main()
    