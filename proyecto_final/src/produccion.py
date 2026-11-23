"""Puntua un lote llamando a la API y guarda las predicciones en PREDICCIONES.

Lo ejecuta el flujo de Kestra produccion_lotes.yml, un lote a la vez:

    python src/produccion.py 2026-10-14

La lista oficial del dia (patron batch) son los 600 creditos de mayor puntaje
del lote: columna en_lista. La columna decision_api es la decision de la API
para un credito suelto (con la nota de corte).
"""

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).parent))
from datos import escribir_tabla, leer_tabla  # noqa: E402
from pipeline import CATEGORICAS, NUMERICAS  # noqa: E402

API = os.getenv("API_URL", "http://localhost:8000")
CAPACIDAD = 600
# Lo que recibe la API: todo menos gestionado_7d (la API lo fija en 1)
ENTRADAS = NUMERICAS + CATEGORICAS + ["plazo_terminado", "compromiso_semana_previa"]


def puntuar_lote(fecha):
    lotes = leer_tabla("LOTES")
    lote = lotes[lotes["fecha_lote"] == fecha]
    entradas = json.loads(lote[ENTRADAS].to_json(orient="records"))

    filas = []
    sesion = requests.Session()
    for operacion, entrada in zip(lote["numero_operacion"], entradas):
        inicio = time.perf_counter()
        respuesta = sesion.post(f"{API}/predecir", json=entrada)
        latencia_ms = (time.perf_counter() - inicio) * 1000
        cuerpo = respuesta.json() if respuesta.status_code == 200 else {}
        filas.append({
            "id_prediccion": cuerpo.get("id_prediccion"),
            "fecha_hora": datetime.now().isoformat(timespec="seconds"),
            "fecha_lote": fecha,
            "numero_operacion": operacion,
            "entradas": json.dumps(entrada),
            "codigo_http": respuesta.status_code,
            "probabilidad": cuerpo.get("probabilidad"),
            "efecto_incremental": cuerpo.get("efecto_incremental"),
            "puntaje": cuerpo.get("puntaje"),
            "decision_api": cuerpo.get("decision"),
            "version_modelo": cuerpo.get("version_modelo"),
            "uso_respaldo": cuerpo.get("uso_respaldo"),
            "latencia_ms": round(latencia_ms, 2),
        })

    predicciones = pd.DataFrame(filas)
    for columna in ["probabilidad", "efecto_incremental", "puntaje"]:
        predicciones[columna] = predicciones[columna].astype(float)
    predicciones["uso_respaldo"] = (predicciones["uso_respaldo"] == True).astype(int)

    # Lista oficial del dia: los 600 de mayor puntaje entre las predicciones validas
    posicion = predicciones["puntaje"].rank(ascending=False, method="first")
    predicciones["en_lista"] = (posicion <= CAPACIDAD).astype(int)

    escribir_tabla(predicciones, "PREDICCIONES")
    validas = predicciones["codigo_http"] == 200
    print(f"Lote {fecha}: {len(predicciones)} creditos | {validas.sum()} predicciones validas | "
          f"{(~validas).sum()} rechazadas | {predicciones['en_lista'].sum()} en la lista")


if __name__ == "__main__":
    puntuar_lote(sys.argv[1])