"""Comportamientos que el modelo debe cumplir segun el negocio de cobranzas.

Se comparan los mismos 500 creditos de la muestra fija cambiando una sola
variable. Los modelos de arboles no garantizan que una variable empuje siempre
hacia el mismo lado, asi que se exige el promedio y al menos el 90% de los creditos.
"""

import os
from pathlib import Path

import mlflow.sklearn
import pandas as pd
import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="module")
def modelo():
    return mlflow.sklearn.load_model(os.environ["MODELO_LOCAL"])


@pytest.fixture(scope="module")
def creditos():
    muestra = pd.read_csv(FIXTURES / "muestra_prueba.csv").head(500)
    return muestra.drop(columns="paga_7d").assign(gestionado_7d=1)


def probabilidad(modelo, X):
    return modelo.predict_proba(X)[:, 1]


def test_compromiso_de_pago_no_reduce_la_probabilidad(modelo, creditos):
    sin_compromiso = probabilidad(modelo, creditos.assign(compromiso_semana_previa=0))
    con_compromiso = probabilidad(modelo, creditos.assign(compromiso_semana_previa=1))
    assert con_compromiso.mean() >= sin_compromiso.mean()
    assert (con_compromiso >= sin_compromiso).mean() >= 0.90


def test_mas_dias_de_mora_no_aumenta_la_probabilidad(modelo, creditos):
    poca_mora = probabilidad(modelo, creditos.assign(dias_mora=10))
    mucha_mora = probabilidad(modelo, creditos.assign(dias_mora=400))
    assert mucha_mora.mean() <= poca_mora.mean()
    assert (mucha_mora <= poca_mora).mean() >= 0.90