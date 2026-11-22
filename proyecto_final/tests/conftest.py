"""Configuracion compartida por todas las pruebas.

En CI no hay servidor de MLflow: la API usa la copia del champion guardada en
tests/fixtures/modelo (variable MODELO_LOCAL).
"""

import os
import sys
import tempfile
from pathlib import Path

import pytest

CARPETA = Path(__file__).parent
os.environ["MODELO_LOCAL"] = str(CARPETA / "fixtures" / "modelo")
os.environ["REGISTRO_PREDICCIONES"] = str(Path(tempfile.gettempdir()) / "predicciones_prueba.csv")
sys.path.insert(0, str(CARPETA.parent / "api"))

from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402


@pytest.fixture
def cliente():
    return TestClient(main.app)


@pytest.fixture
def credito():
    """Un credito valido de ejemplo."""
    return {
        "dias_mora": 12, "cuotas_mora": 1, "cuotas_por_pagar": 30, "cuotas_pagadas": 30,
        "total_cuotas": 60, "capital_insoluto": 15000, "capital_vencido": 250,
        "saldo_cuota_mas_vencida": 420, "valor_deuda_exigible": 480,
        "valor_cuota_exigible_vigente": 420, "monto_financiado": 25000, "tasa_nominal": 0.16,
        "num_gestiones_dia": 1, "estado_operacion": "VENCIDO", "dia_pago": 10,
        "plazo_terminado": 0, "compromiso_semana_previa": 1,
    }