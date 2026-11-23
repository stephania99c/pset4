"""Monitoreo de un lote: metricas de sistema, datos, deriva y modelo; alertas.

Lo ejecuta el flujo de Kestra monitoreo.yml despues de puntuar cada lote:

    python monitoreo/alertas.py 2026-10-21

- Guarda las metricas en la tabla MONITOREO (una fila por metrica).
- Guarda las alertas en la tabla ALERTAS y las escribe en el log de Kestra.
- El target de un lote llega 7 dias despues: al procesar el lote del dia d se
  evalua el desempeno del lote d - 7.
- Decide si hay que reentrenar y se lo avisa a Kestra.
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from sklearn.metrics import average_precision_score

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parents[1] / "src"))
from datos import escribir_tabla, leer_tabla  # noqa: E402
from deriva import comparar  # noqa: E402
from pipeline import CATEGORICAS, NUMERICAS  # noqa: E402

HORIZONTE = 7
CAPACIDAD = 600
CATEGORICAS_MON = CATEGORICAS + ["plazo_terminado", "compromiso_semana_previa"]

# Umbrales (justificados en el documento tecnico)
PSI_MEDIA, PSI_ALTA = 0.10, 0.25
PR_AUC_CV, DESVIACION_CV = 0.459, 0.022          # CV por credito del PSet 3
UMBRAL_PR_AUC = PR_AUC_CV - 2 * DESVIACION_CV    # 0.415
LOTES_SEGUIDOS = 3                               # lotes bajo el umbral para reentrenar
UMBRAL_ERRORES = 0.05                            # 5% de solicitudes con error
UMBRAL_LATENCIA_P95 = 1000                       # milisegundos


def metricas_lote(fecha, lote, predicciones, referencia):
    """Metricas que se pueden calcular el mismo dia: sistema, datos, deriva y predicciones."""
    filas = []

    def agregar(tipo, metrica, valor, variable=""):
        filas.append({"fecha_lote": fecha, "tipo": tipo, "metrica": metrica,
                      "variable": variable, "valor": float(valor)})

    # Sistema
    agregar("sistema", "volumen", len(predicciones))
    agregar("sistema", "latencia_p50_ms", predicciones["latencia_ms"].quantile(0.50))
    agregar("sistema", "latencia_p95_ms", predicciones["latencia_ms"].quantile(0.95))
    codigo = predicciones["codigo_http"]
    agregar("sistema", "tasa_4xx", codigo.between(400, 499).mean())
    agregar("sistema", "tasa_5xx", codigo.between(500, 599).mean())

    # Datos
    for variable in NUMERICAS + CATEGORICAS_MON:
        agregar("datos", "faltantes", lote[variable].isna().mean(), variable)
    for variable in NUMERICAS:
        fuera = ~lote[variable].between(referencia[variable].min(), referencia[variable].max())
        agregar("datos", "fuera_de_rango", fuera.mean(), variable)
    for variable in CATEGORICAS:
        no_vistas = ~lote[variable].astype(str).isin(referencia[variable].astype(str).unique())
        agregar("datos", "categorias_no_vistas", no_vistas.mean(), variable)

    # Deriva de datos
    deriva = comparar(referencia, lote, NUMERICAS, CATEGORICAS_MON)
    for _, fila in deriva.iterrows():
        agregar("deriva", "psi", fila["psi"], fila["variable"])
        agregar("deriva", "p_valor", fila["p_valor"], fila["variable"])

    # Modelo: distribucion de las predicciones y tasa de cada decision
    validas = predicciones[predicciones["codigo_http"] == 200]
    agregar("modelo", "probabilidad_media", validas["probabilidad"].mean())
    agregar("modelo", "tasa_gestionar_lista", validas["en_lista"].mean())
    agregar("modelo", "tasa_gestionar_api", (validas["decision_api"] == "gestionar").mean())
    agregar("modelo", "tasa_respaldo", validas["uso_respaldo"].mean())
    return filas


def metricas_desempeno(fecha_lote, lote, predicciones):
    """Metrica tecnica y de negocio de un lote cuyo target ya llego."""
    datos = predicciones[predicciones["codigo_http"] == 200].merge(
        lote[["numero_operacion", "capital_insoluto", "paga_7d"]], on="numero_operacion")
    linea_base = datos["capital_insoluto"].rank(ascending=False, method="first") <= CAPACIDAD
    valores = {
        "pr_auc": average_precision_score(datos["paga_7d"], datos["probabilidad"]),
        "pagos_capturados": ((datos["en_lista"] == 1) & (datos["paga_7d"] == 1)).sum(),
        "pagos_linea_base": (linea_base & (datos["paga_7d"] == 1)).sum(),
        "pagos_totales": datos["paga_7d"].sum(),
    }
    return [{"fecha_lote": fecha_lote, "tipo": "desempeno", "metrica": metrica,
             "variable": "", "valor": float(valor)} for metrica, valor in valores.items()]


def revisar_alertas(metricas):
    """Compara las metricas con los umbrales y devuelve la lista de alertas."""
    alertas = []

    def alerta(fila, umbral, severidad, recibe, accion):
        alertas.append({"fecha_lote": fila["fecha_lote"], "metrica": fila["metrica"],
                        "variable": fila["variable"], "valor": fila["valor"], "umbral": umbral,
                        "severidad": severidad, "recibe": recibe, "accion": accion})

    for fila in metricas:
        m, v = fila["metrica"], fila["valor"]
        if m == "psi" and v > PSI_ALTA:
            alerta(fila, PSI_ALTA, "Alta", "Equipo de datos",
                   "Revisar la fuente; reentrenar solo si cae el desempeno")
        elif m == "psi" and v > PSI_MEDIA:
            alerta(fila, PSI_MEDIA, "Media", "Equipo de datos", "Vigilar en los siguientes lotes")
        elif m == "categorias_no_vistas" and v > 0:
            alerta(fila, 0, "Media", "Equipo de datos", "Revisar nuevas categorias en la fuente")
        elif m in ("tasa_4xx", "tasa_5xx") and v > UMBRAL_ERRORES:
            alerta(fila, UMBRAL_ERRORES, "Alta", "Equipo de TI", "Revisar la API y los datos de entrada")
        elif m == "latencia_p95_ms" and v > UMBRAL_LATENCIA_P95:
            alerta(fila, UMBRAL_LATENCIA_P95, "Media", "Equipo de TI", "Revisar recursos de la API")
        elif m == "pr_auc" and v < UMBRAL_PR_AUC:
            alerta(fila, round(UMBRAL_PR_AUC, 3), "Alta", "Equipo de modelos",
                   f"Reentrenar si se repite {LOTES_SEGUIDOS} lotes seguidos")
    return alertas


def hay_que_reentrenar(monitoreo, alertas_previas):
    """True si los ultimos LOTES_SEGUIDOS lotes evaluados, desde el ultimo reentrenamiento,
    quedaron bajo el umbral de PR-AUC."""
    pr_auc = monitoreo[monitoreo["metrica"] == "pr_auc"].sort_values("fecha_lote")
    if len(alertas_previas) and (alertas_previas["metrica"] == "reentrenamiento").any():
        ultimo = alertas_previas.loc[alertas_previas["metrica"] == "reentrenamiento", "fecha_lote"].max()
        pr_auc = pr_auc[pr_auc["fecha_lote"] > ultimo]
    ultimos = pr_auc.tail(LOTES_SEGUIDOS)
    return len(ultimos) == LOTES_SEGUIDOS and (ultimos["valor"] < UMBRAL_PR_AUC).all()


def monitorear(fecha):
    lotes = leer_tabla("LOTES")
    predicciones = leer_tabla("PREDICCIONES")
    referencia = leer_tabla("REFERENCIA")

    metricas = metricas_lote(fecha, lotes[lotes["fecha_lote"] == fecha],
                             predicciones[predicciones["fecha_lote"] == fecha], referencia)

    # Desempeno del lote cuyo target ya llego (d - 7)
    fecha_eval = (datetime.strptime(fecha, "%Y-%m-%d") - timedelta(days=HORIZONTE)).strftime("%Y-%m-%d")
    lote_eval = lotes[(lotes["fecha_lote"] == fecha_eval) & lotes["paga_7d"].notna()]
    if len(lote_eval):
        metricas += metricas_desempeno(fecha_eval, lote_eval,
                                       predicciones[predicciones["fecha_lote"] == fecha_eval])

    proceso = datetime.now().isoformat(timespec="seconds")
    tabla_metricas = pd.DataFrame(metricas).assign(fecha_proceso=fecha)
    escribir_tabla(tabla_metricas, "MONITOREO")

    alertas = revisar_alertas(metricas)
    alertas_previas = leer_tabla("ALERTAS")
    reentrenar = hay_que_reentrenar(leer_tabla("MONITOREO"), alertas_previas)
    motivo = ""
    if reentrenar:
        motivo = (f"PR-AUC bajo {UMBRAL_PR_AUC:.3f} (promedio de la CV menos 2 desviaciones) "
                  f"durante {LOTES_SEGUIDOS} lotes seguidos; ultimo lote evaluado: {fecha_eval}")
        alertas.append({"fecha_lote": fecha_eval, "metrica": "reentrenamiento", "variable": "",
                        "valor": 1.0, "umbral": float(LOTES_SEGUIDOS), "severidad": "Alta",
                        "recibe": "Equipo de modelos", "accion": "Se dispara el reentrenamiento"})

    for a in alertas:
        print(f"ALERTA {a['severidad']} | lote {a['fecha_lote']} | {a['metrica']} {a['variable']} = "
              f"{a['valor']:.3f} (umbral {a['umbral']}) | {a['recibe']}: {a['accion']}")
    if alertas:
        escribir_tabla(pd.DataFrame(alertas).assign(fecha_proceso=fecha, registrada=proceso), "ALERTAS")

    print(f"Lote {fecha}: {len(metricas)} metricas | {len(alertas)} alertas | reentrenar: {reentrenar}")
    # Salidas para Kestra
    print("::" + json.dumps({"outputs": {"reentrenar": bool(reentrenar), "motivo": motivo}}) + "::")


if __name__ == "__main__":
    monitorear(sys.argv[1])