"""El modelo cargado reproduce su metrica, y la API tiene respaldo si no carga."""

import json
import os
from pathlib import Path

import mlflow.sklearn
import pandas as pd
from sklearn.metrics import average_precision_score

FIXTURES = Path(__file__).parent / "fixtures"

# Tolerancia: la muestra se guarda en CSV, que redondea algunos decimales.
# 0.001 es 20 veces menor que la desviacion entre pliegues de la CV (0.022):
# cualquier cambio real del modelo la superaria.
TOLERANCIA = 0.001


def test_modelo_reproduce_la_metrica_registrada():
    modelo = mlflow.sklearn.load_model(os.environ["MODELO_LOCAL"])
    muestra = pd.read_csv(FIXTURES / "muestra_prueba.csv")
    X, y = muestra.drop(columns="paga_7d"), muestra["paga_7d"]
    registrada = json.loads((FIXTURES / "metrica_registrada.json").read_text())["pr_auc_prueba"]

    pr_auc = average_precision_score(y, modelo.predict_proba(X)[:, 1])
    assert abs(pr_auc - registrada) <= TOLERANCIA


def test_si_el_modelo_no_carga_usa_el_respaldo(cliente, credito, monkeypatch):
    monkeypatch.setenv("MODELO_LOCAL", "ruta/que/no/existe")
    cuerpo = cliente.post("/predecir", json=credito).json()
    assert cuerpo["uso_respaldo"] is True
    assert cuerpo["probabilidad"] is None
    assert cuerpo["puntaje"] == credito["capital_insoluto"]


def test_interruptor_de_respaldo(cliente, credito, monkeypatch):
    monkeypatch.setenv("MODO_RESPALDO", "true")
    cuerpo = cliente.post("/predecir", json=credito).json()
    assert cuerpo["uso_respaldo"] is True