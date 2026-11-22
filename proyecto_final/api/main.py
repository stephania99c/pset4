"""API de prediccion: prioriza la cartera en mora del call center.

Endpoints:
    GET  /salud     estado del servicio y si el modelo cargo
    GET  /modelo    nombre, version, alias y run_id del modelo en uso
    POST /predecir  probabilidad, decision, version del modelo e id de la prediccion

El modelo se lee de models:/priorizacion-cartera-modelo@champion. En cada
solicitud se revisa a que version apunta el alias: si cambio (promocion o
rollback), se carga la nueva sin reconstruir la imagen.
"""

import csv
import json
import os
import time
import uuid
from datetime import datetime
from pathlib import Path

import mlflow.sklearn
import pandas as pd
from fastapi import FastAPI
from mlflow import MlflowClient
from mlflow.models import Model

from esquemas import Credito, Prediccion

MODELO = "priorizacion-cartera-modelo"
ALIAS = "champion"

# Respaldo: linea base del PSet 3 ("mayor capital insoluto primero").
# Nota de corte = capital insoluto promedio del credito numero 600 de cada dia
# de entrenamiento (calculada con src/nota_corte.py).
NOTA_CORTE_RESPALDO = 18399.41

# Archivo donde se registra cada prediccion (Kestra lo carga a Snowflake)
REGISTRO = Path(os.getenv("REGISTRO_PREDICCIONES", "registros/predicciones.csv"))

app = FastAPI(title="Priorizacion de cartera")
en_uso = {"modelo": None, "version": None, "run_id": None, "nota_corte": None}


def cargar_champion():
    """Devuelve el modelo en uso, o None si hay que usar el respaldo."""
    # Interruptor de respaldo: obliga a usar la regla de negocio
    if os.getenv("MODO_RESPALDO", "false").lower() == "true":
        return None
    try:
        # En CI no hay servidor de MLflow: se usa una copia local del modelo
        if os.getenv("MODELO_LOCAL"):
            ruta = os.environ["MODELO_LOCAL"]
            datos = Model.load(ruta).metadata
            version, run_id, nota_corte = datos["version"], datos["run_id"], datos["nota_corte"]
        else:
            info = MlflowClient().get_model_version_by_alias(MODELO, ALIAS)
            ruta = f"models:/{MODELO}/{info.version}"
            version, run_id, nota_corte = info.version, info.run_id, info.tags["nota_corte"]

        if version != en_uso["version"]:
            en_uso["modelo"] = mlflow.sklearn.load_model(ruta)
            en_uso.update(version=str(version), run_id=run_id, nota_corte=float(nota_corte))
        return en_uso
    except Exception:
        return None


def registrar(respuesta, entrada, latencia_ms):
    """Agrega la prediccion al archivo de registro (una fila por prediccion)."""
    fila = {"id_prediccion": respuesta.id_prediccion,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "entradas": json.dumps(entrada),
            "decision": respuesta.decision,
            "probabilidad": respuesta.probabilidad,
            "puntaje": respuesta.puntaje,
            "version_modelo": respuesta.version_modelo,
            "run_id": en_uso["run_id"] if not respuesta.uso_respaldo else None,
            "uso_respaldo": respuesta.uso_respaldo,
            "latencia_ms": round(latencia_ms, 2)}
    REGISTRO.parent.mkdir(parents=True, exist_ok=True)
    nuevo = not REGISTRO.exists()
    with open(REGISTRO, "a", newline="") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=fila.keys())
        if nuevo:
            escritor.writeheader()
        escritor.writerow(fila)


@app.get("/salud")
def salud():
    actual = cargar_champion()
    return {"estado": "ok",
            "modelo_cargado": actual is not None,
            "modo_respaldo": actual is None}


@app.get("/modelo")
def modelo():
    actual = cargar_champion()
    if actual is None:
        return {"nombre": "regla de respaldo: mayor capital insoluto",
                "version": None, "alias": None, "run_id": None,
                "nota_corte": NOTA_CORTE_RESPALDO}
    return {"nombre": MODELO, "version": actual["version"], "alias": ALIAS,
            "run_id": actual["run_id"], "nota_corte": actual["nota_corte"]}


@app.post("/predecir", response_model=Prediccion)
def predecir(credito: Credito):
    inicio = time.perf_counter()
    entrada = credito.model_dump()
    actual = cargar_champion()

    if actual is None:
        # Respaldo: se prioriza por capital insoluto, sin modelo
        probabilidad, efecto, version = None, None, None
        puntaje = entrada["capital_insoluto"]
        nota_corte = NOTA_CORTE_RESPALDO
        interpretacion = "No disponible: se uso la regla de respaldo (mayor capital insoluto)."
    else:
        X = pd.DataFrame([entrada])
        X["dia_pago"] = X["dia_pago"].astype(float)
        # Se predice dos veces: como gestionado y como no gestionado
        probabilidad = float(actual["modelo"].predict_proba(X.assign(gestionado_7d=1))[0, 1])
        sin_gestion = float(actual["modelo"].predict_proba(X.assign(gestionado_7d=0))[0, 1])
        efecto = probabilidad - sin_gestion
        puntaje = probabilidad * entrada["capital_insoluto"]
        nota_corte = actual["nota_corte"]
        version = actual["version"]
        interpretacion = (f"Gestionar cambiaria la probabilidad de pago en {efecto * 100:+.1f} "
                          "puntos porcentuales. Es una estimacion orientativa: la decision "
                          "usa probabilidad x capital.")

    respuesta = Prediccion(
        id_prediccion=str(uuid.uuid4()),
        decision="gestionar" if puntaje >= nota_corte else "no gestionar",
        probabilidad=probabilidad,
        puntaje=round(puntaje, 2),
        nota_corte=nota_corte,
        efecto_incremental=efecto,
        interpretacion_efecto=interpretacion,
        version_modelo=version,
        uso_respaldo=actual is None,
    )
    registrar(respuesta, entrada, (time.perf_counter() - inicio) * 1000)
    return respuesta