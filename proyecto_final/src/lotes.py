"""Construccion de los lotes de la simulacion de produccion (seccion 5 del PSet 4).

- REFERENCIA: los cortes de entrenamiento (1 al 13 de octubre) con su target.
  Es la distribucion contra la que se compara cada lote (deriva) y la base del
  reentrenamiento.
- LOTES: un lote por dia, del 14 al 31 de octubre (18 lotes), posteriores a la
  fecha de corte del entrenamiento. El target (paga_7d) solo existe hasta el
  24 de octubre: los ultimos 7 dias no tienen 7 dias de futuro observados.

Deriva inducida (desde el lote del 18 de octubre en adelante): se simula un
error de integracion con el sistema de cartera. En cada lote alterado,
dias_mora se desordena entre los creditos del lote (rompe su relacion con el
target) y se le suman 90 dias (cambia su distribucion).
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from datos import agregar_target, cargar_obt  # noqa: E402
from pipeline import (CATEGORICAS, FIN_ENTRENAMIENTO, NUMERICAS, OBJETIVO,  # noqa: E402
                      YA_LISTAS, agregar_features)

PRIMER_LOTE = "2026-10-14"
INICIO_DERIVA = "2026-10-18"
DIAS_AGREGADOS = 90
SEMILLA = 42
COLUMNAS = ["numero_operacion", "fecha_lote"] + NUMERICAS + CATEGORICAS + YA_LISTAS + [OBJETIVO]


def construir_tablas():
    """Devuelve (referencia, lotes), solo con creditos en mora."""
    obt = agregar_features(cargar_obt())
    target = agregar_target(obt)[["numero_operacion", "fecha_corte", OBJETIVO]]
    base = obt.merge(target, on=["numero_operacion", "fecha_corte"], how="left")
    base = base[base["dias_mora"] > 0].copy()
    base["fecha_lote"] = base["fecha_corte"].dt.strftime("%Y-%m-%d")

    referencia = base[base["fecha_lote"] <= FIN_ENTRENAMIENTO][COLUMNAS]
    lotes = base[base["fecha_lote"] >= PRIMER_LOTE][COLUMNAS]
    return referencia.reset_index(drop=True), inducir_deriva(lotes.reset_index(drop=True))


def inducir_deriva(lotes):
    """Altera dias_mora en los lotes desde INICIO_DERIVA (ver descripcion arriba)."""
    lotes = lotes.copy()
    rng = np.random.default_rng(SEMILLA)
    lotes["alterado"] = (lotes["fecha_lote"] >= INICIO_DERIVA).astype(int)
    for fecha in sorted(lotes.loc[lotes["alterado"] == 1, "fecha_lote"].unique()):
        filas = lotes["fecha_lote"] == fecha
        desordenado = rng.permutation(lotes.loc[filas, "dias_mora"].to_numpy())
        lotes.loc[filas, "dias_mora"] = desordenado + DIAS_AGREGADOS
    return lotes