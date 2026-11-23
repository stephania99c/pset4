"""Reentrenamiento del modelo (seccion 7 del PSet 4). Lo ejecuta reentrenamiento.yml.

Paso 1, entrenar el challenger y compararlo con el champion:

    python src/reentrenar.py entrenar 2026-10-27 "motivo del disparo"

Paso 2, despues de la aprobacion humana en Kestra:

    python src/reentrenar.py decidir 3 true "comentario"

Ventana de entrenamiento: todo el historico etiquetado, con mas peso en los
lotes recientes (peso 1 para el entrenamiento original del 1 al 13 de octubre,
peso 3 para los lotes de produccion). Se usa la misma preparacion de
src/pipeline.py y los hiperparametros del champion, sin repetir el tuning.

Regla de promocion: el challenger se recomienda si, sobre el mismo lote
etiquetado mas reciente (que ninguno de los dos vio), captura mas pagos en la
lista de 600 Y su PR-AUC supera la del champion por mas de una desviacion
estandar de la CV (0.022). Una persona aprueba o rechaza el cambio.
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

import mlflow
import mlflow.sklearn
import pandas as pd
from mlflow import MlflowClient
from mlflow.models import infer_signature
from sklearn.base import clone
from sklearn.metrics import average_precision_score

sys.path.insert(0, str(Path(__file__).parent))
from datos import leer_tabla  # noqa: E402
from nota_corte import calcular_notas  # noqa: E402
from pipeline import CATEGORICAS, NUMERICAS, OBJETIVO, YA_LISTAS  # noqa: E402

MODELO = "priorizacion-cartera-modelo"
EXPERIMENTO = "priorizacion-cartera"
COLUMNAS = NUMERICAS + CATEGORICAS + YA_LISTAS
HORIZONTE = 7
CAPACIDAD = 600
PESO_LOTES = 3
DESVIACION_CV = 0.022


def evaluar(modelo, lote):
    """PR-AUC y pagos capturados en la lista de 600 (como en produccion: gestionado_7d = 1)."""
    probabilidad = modelo.predict_proba(lote[COLUMNAS].assign(gestionado_7d=1))[:, 1]
    puntaje = probabilidad * lote["capital_insoluto"]
    en_lista = puntaje.rank(ascending=False, method="first") <= CAPACIDAD
    return {"pr_auc": average_precision_score(lote[OBJETIVO], probabilidad),
            "pagos_capturados": int((en_lista & (lote[OBJETIVO] == 1)).sum())}


def entrenar(fecha_proceso, motivo):
    # Lote etiquetado mas reciente: d - 7. Se reserva para comparar.
    fecha_eval = (datetime.strptime(fecha_proceso, "%Y-%m-%d")
                  - timedelta(days=HORIZONTE)).strftime("%Y-%m-%d")
    lotes = leer_tabla("LOTES")
    lotes = lotes[lotes[OBJETIVO].notna() & (lotes["fecha_lote"] <= fecha_eval)]
    evaluacion = lotes[lotes["fecha_lote"] == fecha_eval]

    referencia = leer_tabla("REFERENCIA").assign(peso=1)
    recientes = lotes[lotes["fecha_lote"] < fecha_eval].assign(peso=PESO_LOTES)
    entrenamiento = pd.concat([referencia, recientes], ignore_index=True)
    X, y = entrenamiento[COLUMNAS], entrenamiento[OBJETIVO].astype(int)

    cliente = MlflowClient()
    version_champion = cliente.get_model_version_by_alias(MODELO, "champion").version
    champion = mlflow.sklearn.load_model(f"models:/{MODELO}/{version_champion}")
    challenger = clone(champion).fit(X, y, modelo__sample_weight=entrenamiento["peso"].to_numpy())

    m_champion, m_challenger = evaluar(champion, evaluacion), evaluar(challenger, evaluacion)
    gana_negocio = m_challenger["pagos_capturados"] > m_champion["pagos_capturados"]
    gana_tecnica = m_challenger["pr_auc"] - m_champion["pr_auc"] > DESVIACION_CV
    recomendacion = "promover" if (gana_negocio and gana_tecnica) else "mantener champion"

    mlflow.set_experiment(EXPERIMENTO)
    with mlflow.start_run(run_name=f"reentrenamiento {fecha_proceso}") as corrida:
        mlflow.set_tags({"fase": "reentrenamiento", "motivo": motivo, "recomendacion": recomendacion})
        mlflow.log_params({"fecha_proceso": fecha_proceso, "lote_evaluacion": fecha_eval,
                           "ventana": f"entrenamiento original + lotes hasta {fecha_eval} (sin incluirlo)",
                           "peso_lotes_recientes": PESO_LOTES, "filas": len(X),
                           "version_champion": version_champion})
        mlflow.log_metrics({"pr_auc_challenger": m_challenger["pr_auc"],
                            "pr_auc_champion": m_champion["pr_auc"],
                            "pagos_challenger": m_challenger["pagos_capturados"],
                            "pagos_champion": m_champion["pagos_capturados"]})
        firma = infer_signature(X.head(100), challenger.predict_proba(X.head(100))[:, 1])
        mlflow.sklearn.log_model(challenger, "modelo", signature=firma, input_example=X.head(5))

    version = mlflow.register_model(f"runs:/{corrida.info.run_id}/modelo", MODELO).version
    cliente.set_registered_model_alias(MODELO, "challenger", version)
    notas = calcular_notas(challenger, entrenamiento.rename(columns={"fecha_lote": "fecha_corte"}))
    cliente.set_model_version_tag(MODELO, version, "nota_corte",
                                  round(notas["modelo (probabilidad x capital)"], 2))

    print(f"Lote de evaluacion: {fecha_eval} ({len(evaluacion)} creditos)")
    print(f"Champion   (version {version_champion}): PR-AUC {m_champion['pr_auc']:.3f} | "
          f"pagos en la lista {m_champion['pagos_capturados']}")
    print(f"Challenger (version {version}): PR-AUC {m_challenger['pr_auc']:.3f} | "
          f"pagos en la lista {m_challenger['pagos_capturados']}")
    print(f"Regla de promocion: {recomendacion.upper()} (mas pagos: {gana_negocio}; "
          f"PR-AUC +{DESVIACION_CV}: {gana_tecnica})")
    print("::" + json.dumps({"outputs": {"version": str(version), "run_id": corrida.info.run_id,
                                         "recomendacion": recomendacion}}) + "::")


def decidir(version, aprobar, comentario):
    cliente = MlflowClient()
    run_id = cliente.get_model_version(MODELO, version).run_id
    decision = "aprobado" if aprobar else "rechazado"
    cliente.set_model_version_tag(MODELO, version, "decision", decision)
    cliente.set_model_version_tag(MODELO, version, "comentario", comentario)
    cliente.set_tag(run_id, "decision", decision)
    cliente.set_tag(run_id, "comentario", comentario)
    if aprobar:
        cliente.set_registered_model_alias(MODELO, "champion", version)
        print(f"Aprobado: la version {version} es el nuevo champion. Comentario: {comentario}")
    else:
        print(f"Rechazado: el champion no cambia. Motivo: {comentario}")


if __name__ == "__main__":
    if sys.argv[1] == "entrenar":
        entrenar(sys.argv[2], sys.argv[3])
    else:
        decidir(sys.argv[2], sys.argv[3].lower() == "true", sys.argv[4])