"""Preparacion de los datos del modelo de priorizacion de cartera.

Los notebooks importan este archivo en vez de copiar el codigo:

    from src.pipeline import cargar_y_dividir, construir_preparacion

Para comprobar que corre de principio a fin, sin notebook (desde la raiz del repo):

    python src/pipeline.py
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder, StandardScaler

sys.path.insert(0, str(Path(__file__).parent))
from datos import agregar_target, cargar_obt  # noqa: E402

OBJETIVO = "paga_7d"
NUMERICAS = ["dias_mora", "cuotas_mora", "cuotas_por_pagar", "cuotas_pagadas", "total_cuotas",
             "capital_insoluto", "capital_vencido", "saldo_cuota_mas_vencida",
             "valor_deuda_exigible", "valor_cuota_exigible_vigente", "monto_financiado",
             "tasa_nominal", "num_gestiones_dia"]
CATEGORICAS = ["estado_operacion", "dia_pago"]
YA_LISTAS = ["plazo_terminado", "compromiso_semana_previa", "gestionado_7d"]

# Division temporal: entrenamiento hasta el 13-oct, prueba del 21 al 24-oct.
# Los 7 dias del medio se dejan fuera para que el target del entrenamiento
# (que mira 7 dias hacia adelante) nunca use dias del periodo de prueba.
FIN_ENTRENAMIENTO = "2026-10-13"
INICIO_PRUEBA = "2026-10-21"


def suma_ventana(obt, columna, desde, hasta):
    """Para cada credito y corte d, suma `columna` en los dias d+desde ... d+hasta."""
    eventos = obt.loc[obt[columna] > 0, ["numero_operacion", "fecha_corte", columna]]
    partes = []
    for k in range(desde, hasta + 1):
        partes.append(eventos.assign(fecha_corte=eventos["fecha_corte"] - pd.Timedelta(days=k)))
    total = pd.concat(partes).groupby(["numero_operacion", "fecha_corte"], as_index=False)[columna].sum()
    unido = obt[["numero_operacion", "fecha_corte"]].merge(total, on=["numero_operacion", "fecha_corte"], how="left")
    return unido[columna].fillna(0).to_numpy()


def agregar_features(obt):
    obt = obt.copy()
    obt["fecha_corte"] = pd.to_datetime(obt["fecha_corte"])

    # 1. Plazo terminado: todas las cuotas pendientes ya vencieron
    obt["plazo_terminado"] = ((obt["cuotas_por_pagar"] > 0)
                              & (obt["cuotas_por_pagar"] == obt["cuotas_mora"])).astype(int)

    # 2. Compromiso de pago registrado en la ultima semana (dias d-6 a d)
    obt["compromiso_semana_previa"] = (suma_ventana(obt, "compromiso_pago_dia", -6, 0) > 0).astype(int)

    # Tratamiento para el efecto incremental: gestionado en los dias d+1 a d+7
    obt["gestionado_7d"] = (suma_ventana(obt, "num_gestiones_dia", 1, 7) > 0).astype(int)
    return obt


def cargar_base():
    """OBT con features y target, solo creditos en mora, ordenada por fecha."""
    base = agregar_target(agregar_features(cargar_obt()))
    base = base[base["dias_mora"] > 0]
    return base.sort_values("fecha_corte").reset_index(drop=True)

def cargar_y_dividir():
    base = cargar_base()
    entrenamiento = base[base["fecha_corte"] <= FIN_ENTRENAMIENTO]
    prueba = base[base["fecha_corte"] >= INICIO_PRUEBA]
    columnas = NUMERICAS + CATEGORICAS + YA_LISTAS
    return (entrenamiento[columnas], prueba[columnas],
            entrenamiento[OBJETIVO], prueba[OBJETIVO],
            entrenamiento["numero_operacion"])


def construir_preparacion():
    return ColumnTransformer([
        ("numericas", Pipeline([
            ("imputar", SimpleImputer(strategy="median")),
            ("log", FunctionTransformer(np.log1p, feature_names_out="one-to-one")),
            ("escalar", StandardScaler()),
        ]), NUMERICAS),
        ("categoricas", Pipeline([
            ("imputar", SimpleImputer(strategy="most_frequent")),
            ("codificar", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ]), CATEGORICAS),
        ("ya_listas", "passthrough", YA_LISTAS),
    ])


# Esto corre con "python src/pipeline.py", pero no cuando un notebook lo importa.
if __name__ == "__main__":
    X_ent, X_prueba, y_ent, y_prueba, grupos_ent = cargar_y_dividir()
    preparacion = construir_preparacion()
    X_ent_listo = preparacion.fit_transform(X_ent)
    X_prueba_listo = preparacion.transform(X_prueba)
    print("Entrenamiento:", X_ent_listo.shape, "| % paga:", round(y_ent.mean() * 100, 2))
    print("Prueba:       ", X_prueba_listo.shape, "| % paga:", round(y_prueba.mean() * 100, 2))
    print(list(preparacion.get_feature_names_out()))