"""Tablero de monitoreo (seccion 6.4): metricas lote por lote, alertas y reentrenamientos.

Se levanta con docker compose (servicio "tablero") en el puerto 8501.
Lee las tablas MONITOREO y ALERTAS de Snowflake.
"""

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))
from datos import leer_tabla  # noqa: E402

UMBRAL_PR_AUC = 0.415
UMBRAL_PSI = 0.25

st.set_page_config(page_title="Monitoreo de la priorizacion de cartera", layout="wide")
st.title("Monitoreo del modelo de priorizacion de cartera")

monitoreo = leer_tabla("MONITOREO")
alertas = leer_tabla("ALERTAS")
if monitoreo.empty:
    st.info("Todavia no hay lotes procesados.")
    st.stop()
monitoreo["variable"] = monitoreo["variable"].fillna("")


def serie(tipo, metricas):
    datos = monitoreo[(monitoreo["tipo"] == tipo) & monitoreo["metrica"].isin(metricas)]
    return datos.pivot_table(index="fecha_lote", columns="metrica", values="valor")


# Reentrenamientos y alertas por lote
reentrenamientos = alertas[alertas["metrica"] == "reentrenamiento"] if len(alertas) else alertas
if len(reentrenamientos):
    st.warning("Reentrenamiento disparado al evaluar los lotes: "
               + ", ".join(sorted(reentrenamientos["fecha_lote"].unique())))
if len(alertas):
    st.subheader("Alertas por lote")
    st.bar_chart(alertas.pivot_table(index="fecha_lote", columns="severidad",
                                     values="metrica", aggfunc="count").fillna(0))

st.subheader("Modelo")
col1, col2 = st.columns(2)
col1.caption(f"PR-AUC por lote (cuando llega el target) y umbral de alerta ({UMBRAL_PR_AUC})")
col1.line_chart(serie("desempeno", ["pr_auc"]).assign(umbral=UMBRAL_PR_AUC))
col2.caption("Pagos capturados en la lista de 600: modelo vs. linea base (mayor capital)")
col2.line_chart(serie("desempeno", ["pagos_capturados", "pagos_linea_base"]))
col1.caption("Distribucion de las predicciones y tasa de cada decision")
col1.line_chart(serie("modelo", ["probabilidad_media", "tasa_gestionar_lista", "tasa_gestionar_api"]))
col2.caption("Uso del respaldo (regla de negocio)")
col2.line_chart(serie("modelo", ["tasa_respaldo"]))

st.subheader("Deriva de datos")
psi = monitoreo[monitoreo["metrica"] == "psi"].pivot_table(index="fecha_lote", columns="variable",
                                                           values="valor")
st.caption(f"PSI de cada variable frente al entrenamiento (alerta si supera {UMBRAL_PSI})")
st.line_chart(psi)

st.subheader("Sistema")
col1, col2 = st.columns(2)
col1.caption("Latencia de la API (ms)")
col1.line_chart(serie("sistema", ["latencia_p50_ms", "latencia_p95_ms"]))
col2.caption("Tasa de errores")
col2.line_chart(serie("sistema", ["tasa_4xx", "tasa_5xx"]))

st.subheader("Registro de alertas")
st.dataframe(alertas.sort_values(["fecha_proceso", "severidad"]) if len(alertas) else alertas,
             width="stretch")