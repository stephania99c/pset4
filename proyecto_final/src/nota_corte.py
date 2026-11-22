"""Nota de corte de la decision "gestionar" para la API.

La lista diaria gestiona los 600 creditos de mayor puntaje (probabilidad x capital).
La API recibe un credito a la vez, asi que usa una nota de corte: el puntaje
promedio del credito numero 600 de cada dia de entrenamiento.

Uso (desde proyecto_final, con MLflow encendido):

    python src/nota_corte.py              # para el champion
    python src/nota_corte.py challenger   # para el challenger
"""

import sys
from pathlib import Path

import mlflow.sklearn
from mlflow import MlflowClient

sys.path.insert(0, str(Path(__file__).parent))
from pipeline import CATEGORICAS, FIN_ENTRENAMIENTO, NUMERICAS, YA_LISTAS, cargar_base  # noqa: E402

MODELO = "priorizacion-cartera-modelo"
CAPACIDAD = 600


def nota_de_corte(base, puntaje):
    """Promedio, entre dias, del puntaje del credito en el puesto 600."""
    tabla = base[["fecha_corte"]].assign(puntaje=puntaje)
    puesto_600 = tabla.groupby("fecha_corte")["puntaje"].apply(lambda p: p.nlargest(CAPACIDAD).min())
    return float(puesto_600.mean())


def calcular_notas(modelo, base):
    X = base[NUMERICAS + CATEGORICAS + YA_LISTAS].assign(gestionado_7d=1)
    probabilidad = modelo.predict_proba(X)[:, 1]
    return {
        "modelo (probabilidad x capital)": nota_de_corte(base, probabilidad * base["capital_insoluto"]),
        "respaldo (solo capital)": nota_de_corte(base, base["capital_insoluto"]),
    }


if __name__ == "__main__":
    alias = sys.argv[1] if len(sys.argv) > 1 else "champion"

    base = cargar_base()
    base = base[base["fecha_corte"] <= FIN_ENTRENAMIENTO]

    cliente = MlflowClient()
    version = cliente.get_model_version_by_alias(MODELO, alias).version
    modelo = mlflow.sklearn.load_model(f"models:/{MODELO}@{alias}")

    notas = calcular_notas(modelo, base)
    nota_modelo = round(notas["modelo (probabilidad x capital)"], 2)
    cliente.set_model_version_tag(MODELO, version, "nota_corte", nota_modelo)

    print(f"{alias}: version {version}")
    for nombre, valor in notas.items():
        print(f"Nota de corte {nombre}: {valor:,.2f}")