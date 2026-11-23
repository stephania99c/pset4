"""SPARK: construye la OBT (One Big Table) a partir del star schema de GOLD.
GRANO de la OBT: una operacion de auto en un dia de corte (igual que fct_cartera_diaria).
Uso:  spark-submit job_obt.py
"""
import os

import pandas as pd
import snowflake.connector
from pyspark.sql import SparkSession, functions as F
from snowflake.connector.pandas_tools import write_pandas

CARPETA = "/tmp/obt"


def conectar():
    return snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"], user=os.environ["SNOWFLAKE_USER"],
        password=os.environ["SNOWFLAKE_PAT"], role=os.environ["SNOWFLAKE_ROLE"],
        warehouse=os.environ["SNOWFLAKE_WAREHOUSE"], database="CARTERA", schema="GOLD")


def leer(spark, con, tabla):
    """Lee una tabla de GOLD y la convierte en DataFrame de Spark (pasando por un archivo parquet)."""
    df = con.cursor().execute(f"select * from {tabla}").fetch_pandas_all()
    df.columns = df.columns.str.lower()
    for columna in df.columns:              # columnas totalmente vacias: se guardan como texto
        if df[columna].isna().all():
            df[columna] = df[columna].astype("string")
    ruta = f"{CARPETA}/{tabla}.parquet"
    df.to_parquet(ruta, index=False)
    return spark.read.parquet(ruta)


def main():
    os.makedirs(CARPETA, exist_ok=True)
    spark = SparkSession.builder.appName("obt_cartera").master("local[*]").getOrCreate()
    con = conectar()

    # 1. Leer el star schema
    cartera = leer(spark, con, "fct_cartera_diaria")
    pagos = leer(spark, con, "fct_pagos")
    gestiones = leer(spark, con, "fct_gestiones")
    operaciones = leer(spark, con, "dim_operacion")
    fechas = leer(spark, con, "dim_fecha")

    # 2. Llevar pagos y gestiones al grano de la OBT (operacion + dia)
    pagos_dia = (
        pagos.groupBy("numero_operacion", F.col("fecha_pago").alias("fecha_corte"))
        .agg(F.count("*").alias("num_pagos_dia"),
             F.round(F.sum("monto"), 2).alias("monto_pagado_dia"))
    )
    gestiones_dia = (
        gestiones.groupBy("numero_operacion", F.col("fecha_gestion").alias("fecha_corte"))
        .agg(F.count("*").alias("num_gestiones_dia"),
             F.max(F.col("hubo_contacto_efectivo").cast("int")).alias("contacto_efectivo_dia"),
             F.max(F.col("tiene_compromiso").cast("int")).alias("compromiso_pago_dia"))
    )

    # 3. Unir todo a la cartera diaria (la cartera define las filas de la OBT)
    obt = (
        cartera
        .join(pagos_dia, ["numero_operacion", "fecha_corte"], "left")
        .join(gestiones_dia, ["numero_operacion", "fecha_corte"], "left")
        .join(operaciones.drop("cliente_id"), "numero_operacion", "left")
        .join(fechas.withColumnRenamed("fecha", "fecha_corte"), "fecha_corte", "left")
        .fillna(0, subset=["num_pagos_dia", "monto_pagado_dia", "num_gestiones_dia",
                           "contacto_efectivo_dia", "compromiso_pago_dia"])
    )

    # 4. Validar los joins
    filas_cartera = cartera.count()
    filas_obt = obt.count()
    duplicados = filas_obt - obt.select("numero_operacion", "fecha_corte").distinct().count()
    pagos_total = pagos.count()
    pagos_en_obt = obt.agg(F.sum("num_pagos_dia")).first()[0]
    print(f"Filas fct_cartera_diaria: {filas_cartera}")
    print(f"Filas OBT:                {filas_obt}")
    print(f"Duplicados en el grano:   {duplicados}")
    print(f"Pagos en fct_pagos: {pagos_total} | pagos que caen en un dia de cartera: {pagos_en_obt}")
    print(f"Pagos fuera de los dias de cartera (en_obt = false): {pagos.filter(~F.col('en_obt')).count()}")
    if filas_obt != filas_cartera or duplicados != 0:
        raise ValueError("La OBT no respeta el grano: revisar los joins")

    # 5. Guardar la OBT en Snowflake (esquema GOLD)
    obt.write.mode("overwrite").parquet(f"{CARPETA}/obt")
    resultado = pd.read_parquet(f"{CARPETA}/obt")
    write_pandas(con, resultado, "OBT_CARTERA_DIARIA", auto_create_table=True,
                 overwrite=True, quote_identifiers=False, use_logical_type=True)
    print(f"OBT_CARTERA_DIARIA guardada en GOLD: {len(resultado)} filas")

    con.close()
    spark.stop()


if __name__ == "__main__":
    main()
