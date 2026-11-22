"""Crea las copias que usan las pruebas en CI, donde no hay MLflow ni Snowflake.

- modelo/: copia del champion guardada con mlflow.sklearn.save_model
- muestra_prueba.csv: conjunto de prueba fijo (21 al 24 de octubre) con su target
- metrica_registrada.json: PR-AUC de prueba registrada en MLflow

Uso (desde proyecto_final, con MLflow encendido):

    python tests/fixtures/crear_fixtures.py
"""

import json
import shutil
import sys
from pathlib import Path

import mlflow.sklearn
from mlflow import MlflowClient

sys.path.insert(0, str(Path(__file__).parents[2] / "src"))
from pipeline import OBJETIVO, cargar_y_dividir  # noqa: E402

MODELO = "priorizacion-cartera-modelo"
CARPETA = Path(__file__).parent

# 1. Copia del champion, con su version, run_id y nota de corte
cliente = MlflowClient()
version = cliente.get_model_version_by_alias(MODELO, "champion")
modelo = mlflow.sklearn.load_model(f"models:/{MODELO}/{version.version}")
destino = CARPETA / "modelo"
shutil.rmtree(destino, ignore_errors=True)
mlflow.sklearn.save_model(modelo, destino, metadata={
    "version": version.version,
    "run_id": version.run_id,
    "nota_corte": float(version.tags["nota_corte"]),
})

# 2. Muestra fija: el conjunto de prueba del PSet 3 con su target
_, X_prueba, _, y_prueba, _ = cargar_y_dividir()
muestra = X_prueba.assign(**{OBJETIVO: y_prueba.to_numpy()})
muestra.to_csv(CARPETA / "muestra_prueba.csv", index=False)

# 3. Metrica registrada en MLflow por la corrida del champion
pr_auc = cliente.get_run(version.run_id).data.metrics["pr_auc_prueba"]
(CARPETA / "metrica_registrada.json").write_text(json.dumps(
    {"version": version.version, "pr_auc_prueba": pr_auc}, indent=2))

print(f"Champion version {version.version} | filas de la muestra: {len(muestra)} | PR-AUC registrada: {pr_auc}")