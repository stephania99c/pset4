"""Deriva de datos: compara cada variable de un lote contra el entrenamiento.

- PSI (indice de estabilidad poblacional): decide la alerta.
    < 0.10        estable
    0.10 a 0.25   cambio moderado: vigilar
    > 0.25        cambio fuerte: alerta
- Prueba estadistica de respaldo: Kolmogorov-Smirnov (numericas) y
  chi-cuadrado (categoricas). Con miles de filas detectan hasta diferencias
  minimas, por eso no deciden la alerta: solo la respaldan.

dias_mora se agrupa con los tramos de mora del negocio y no con deciles: su
distribucion fina cambia con el calendario (los creditos comparten dias de
pago), y con deciles los lotes normales daban PSI de 1.2 a 1.4 (falsa alarma).
Con tramos, los lotes normales dan 0.01 a 0.08.
"""

import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency, ks_2samp

MINIMO = 1e-4  # evita dividir entre cero o calcular log(0) en grupos vacios
TRAMOS_MORA = [0, 30, 60, 90, 120, 180, 360, np.inf]


def psi(referencia, actual, categorica=False, cortes=None):
    if categorica:
        grupos = sorted(set(referencia.astype(str)) | set(actual.astype(str)))
        p_ref = referencia.astype(str).value_counts(normalize=True).reindex(grupos, fill_value=0)
        p_act = actual.astype(str).value_counts(normalize=True).reindex(grupos, fill_value=0)
    else:
        if cortes is None:
            # 10 grupos con los deciles del entrenamiento
            cortes = np.unique(np.quantile(referencia, np.linspace(0, 1, 11)))
            cortes[0], cortes[-1] = -np.inf, np.inf
        p_ref = pd.Series(np.histogram(referencia, cortes)[0] / len(referencia))
        p_act = pd.Series(np.histogram(actual, cortes)[0] / len(actual))
    p_ref, p_act = p_ref.clip(lower=MINIMO), p_act.clip(lower=MINIMO)
    return float(((p_act - p_ref) * np.log(p_act / p_ref)).sum())


def p_valor(referencia, actual, categorica=False):
    if categorica:
        tabla = pd.crosstab(
            pd.concat([referencia, actual]).astype(str),
            ["referencia"] * len(referencia) + ["lote"] * len(actual))
        return float(chi2_contingency(tabla)[1])
    return float(ks_2samp(referencia, actual).pvalue)


def comparar(referencia, lote, numericas, categoricas):
    """Tabla con el PSI y el p-valor de cada variable."""
    filas = []
    for variable in numericas + categoricas:
        categorica = variable in categoricas
        cortes = TRAMOS_MORA if variable == "dias_mora" else None
        filas.append({
            "variable": variable,
            "psi": psi(referencia[variable], lote[variable], categorica, cortes),
            "p_valor": p_valor(referencia[variable], lote[variable], categorica),
            "prueba": "chi-cuadrado" if categorica else "Kolmogorov-Smirnov",
        })
    return pd.DataFrame(filas)