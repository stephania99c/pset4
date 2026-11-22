# Registro de cambios

Cada observación recibida en los PSets #1 a #3, qué se cambió y en qué archivo. También las decisiones de PSets anteriores que se actualizaron en el proyecto final.

## PSet #1 

| Observación | Qué se cambió | Archivo |
|---|---|---|
| La regla prioriza créditos que pagarían sin intervención; considerar el efecto incremental de la gestión. | Se estimó el efecto incremental con un S-learner (tratamiento `gestionado_7d`) en el PSet 3. | `src/pipeline.py`, `notebooks/05_seleccion.ipynb` |

## PSet #2 

| Observación | Qué se cambió | Archivo |
|---|---|---|
| Kestra: agregar el bloque de errores e integrar la ejecución de dbt y Spark. | Pendiente | `kestra/ingesta.yml` |
| dbt: test que valide que Gold conserva exactamente las filas esperadas después de los filtros de Silver. | Pendiente | `dbt/tests/` |
| Star schema: revisar la utilidad de `dim_cliente`. | Pendiente | `dbt/models/gold/dim_cliente.sql` |
| Spark y OBT: los 378 pagos fuera de los días de cartera deben seguir identificados y documentados. | Pendiente | `dbt/models/gold/fct_pagos.sql` |
| Infraestructura: eliminar la ejecución manual de dbt y de Spark. | Pendiente | `kestra/ingesta.yml`, `README.md` |
| Documento: reemplazar los diagramas en texto por diagramas visuales. | Pendiente | `docs/arquitectura.png`, `docs/modelo_dimensional.png` |

## PSet #3

Pendiente: retroalimentación aún no recibida.

## Cambios de estructura al unir los PSets

| Cambio | Motivo |
|---|---|
| Todo el proyecto vive en `proyecto_final/`. | Estructura pedida en el PSet #4. |
| `kestra/flow_ingesta_cartera.yml` pasa a `kestra/ingesta.yml`. | Nombre pedido en el PSet #4. |
| Un solo `docker-compose.yml` con Kestra, MLflow, dbt y Spark. | Levantar todo con un solo comando. |
| Memos de los PSets #2 y #3 en `docs/historial/`. | Estructura pedida en el PSet #4. |
| Los workflows (`ci.yml`, `cd.yml`) van en `.github/workflows/` en la raíz del repo, no dentro de `proyecto_final/`. | GitHub Actions solo lee los workflows desde la raíz del repositorio. |