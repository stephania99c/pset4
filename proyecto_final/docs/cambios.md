# Registro de cambios

Cada observación recibida en los PSets #1 a #3, qué se cambió y en qué archivo. También las decisiones de PSets anteriores que se actualizaron en el proyecto final.

## PSet #1 

| Observación | Qué se cambió | Archivo |
|---|---|---|
| La regla prioriza créditos que pagarían sin intervención; considerar el efecto incremental de la gestión. | Se estimó el efecto incremental con un S-learner (tratamiento `gestionado_7d`) en el PSet 3. En el proyecto final, la API devuelve ese efecto con una interpretación para quien consulta. Es informativo: por sesgo de selección no se usa para decidir. | `src/pipeline.py`, `notebooks/05_seleccion.ipynb`, `api/main.py` |

## PSet #2 

| Observación | Qué se cambió | Archivo |
|---|---|---|
| Kestra: agregar el bloque de errores e integrar la ejecución de dbt y Spark. | Hecho. El flujo `ingesta` corre en orden `cargar_raw` → `construir_gold_dbt` → `construir_obt_spark`, tiene bloque `errors`, reintentos en la carga y se programa todos los días a las 07:00. | `kestra/ingesta.yml` |
| dbt: test que valide que Gold conserva exactamente las filas esperadas después de los filtros de Silver. | Hecho. Test singular que compara el conteo de `fct_cartera_diaria`, `fct_pagos` y `fct_gestiones` con los filtros de Silver. Resultado: PASS (`dbt build`: PASS=53, ERROR=0). | `dbt/tests/assert_gold_conserva_filas.sql` |
| Star schema: revisar la utilidad de `dim_cliente`. | Hecho. `dim_cliente` ahora resume al cliente: número de créditos de auto, monto financiado total y si tiene algún crédito en mora en su último corte. | `dbt/models/gold/dim_cliente.sql` |
| Spark y OBT: los 378 pagos fuera de los días de cartera deben seguir identificados y documentados. | Hecho. `fct_pagos` conserva todos los pagos y marca con `en_obt = false` los que caen fuera de los días de cartera; Spark imprime el conteo (378). | `dbt/models/gold/fct_pagos.sql`, `spark/job_obt.py` |
| Infraestructura: eliminar la ejecución manual de dbt y de Spark. | Hecho. dbt y Spark se ejecutan desde Kestra; ya no se corren a mano. | `kestra/ingesta.yml`, `docker-compose.yml` |
| Documento: reemplazar los diagramas en texto por diagramas visuales. | Hecho. Se eliminó `docs/diagramas.md` y se agregaron dos diagramas visuales: arquitectura completa y modelo dimensional de Gold. | `docs/arquitectura.png`, `docs/modelo_dimensional.png` |

## PSet #3

Sin observaciones (calificación 100/100). No se requirieron cambios.

## Decisiones actualizadas en el proyecto final

| Decisión anterior | Decisión nueva | Motivo |
|---|---|---|
| Línea base (PSet 1): priorización según PAR 30, PAR 60, nuevo y viejo vencido. | Línea base: los 600 créditos con mayor capital insoluto. | Hoy la elección dentro de cada grupo no tiene una regla escrita; "mayor capital primero" es la aproximación que se puede reproducir con los datos. |
| Métrica técnica (PSet 1): AUC y precision@60 por cobrador. | PR-AUC y pagos captados en la lista de 600 del call center. | Solo 18.7 % paga (la PR-AUC refleja mejor la clase minoritaria) y los datos no guardan el historial de asignación por cobrador. |
| Unidad (PSet 1): crédito en mora asignado a un cobrador, cada día. | Crédito de auto en mora (pagaré principal), cada día; la lista es del call center. | Sin historial de asignación no se puede armar la lista por cobrador. |
| Meta del pitch (PSet 1): +10 % de recuperación en un piloto. | Resultado de la simulación: +52 % de pagos captados frente a la regla actual (2 651 vs. 1 745). | Coherencia pedida en el PSet 4: las cifras del pitch se reemplazan por las de la sección 9 del memo. |
| Juicio humano (PSet 1): el cobrador puede sacar créditos registrando el motivo. | Se mantiene y se amplía: exclusiones de casos especiales, aprobación humana de cada modelo nuevo y estrategia aparte para castigadas. | Lo que mostró la simulación y el conocimiento del negocio. |
| La lista diaria se armaba en un notebook. | El modelo `champion` se sirve con una API (FastAPI + Docker) que valida la entrada, decide gestionar / no gestionar y registra cada predicción. | Despliegue pedido en el PSet #4. |
| Umbral de decisión fijo. | "Nota de corte": puntaje promedio del crédito número 600 en los días de entrenamiento; se guarda como etiqueta de cada versión del modelo. | La capacidad es de 600 llamadas al día (10 cobradores × 60). |
| Sin plan de respaldo. | Si el modelo no carga o se activa `MODO_RESPALDO`, la API ordena por capital insoluto (regla actual del negocio). | Continuidad de la operación. |
| PSI por deciles para todas las variables. | `dias_mora` usa tramos de negocio (0, 30, 60, 90, 120, 180, 360 días). | Con deciles, los lotes normales daban falsas alarmas (PSI 1.2–1.4) por efectos de calendario. |
| Reentrenar ante cualquier deriva. | Se reentrena solo si el PR-AUC está bajo 0.415 en 3 lotes evaluados seguidos; la deriva de datos sola genera alerta pero no reentrena. El challenger se promueve solo con aprobación humana. | Evitar reentrenar por ruido y mantener supervisión humana. |
| Kestra con `pluginDefaults` y `ForEach`. | Configuración escrita en cada tarea y `Loop` en lugar de `ForEach`. | Kestra 2.0 eliminó esas opciones. |

## Cambios de estructura al unir los PSets

| Cambio | Motivo |
|---|---|
| Todo el proyecto vive en `proyecto_final/`. | Estructura pedida en el PSet #4. |
| `kestra/flow_ingesta_cartera.yml` pasa a `kestra/ingesta.yml`. | Nombre pedido en el PSet #4. |
| Un solo `docker-compose.yml` con Kestra, MLflow, la API, el tablero, dbt y Spark. | Levantar todo con un solo comando. |
| Memos de los PSets #2 y #3 en `docs/historial/`. | Estructura pedida en el PSet #4. |
| Los workflows (`ci.yml`, `cd.yml`) van en `.github/workflows/` en la raíz del repo, no dentro de `proyecto_final/`. | GitHub Actions solo lee los workflows desde la raíz del repositorio. |
| Kestra limitado a 1.5 GB de memoria y con reinicio automático. | El Codespace tiene 8 GB de RAM y Kestra se apagaba por falta de memoria. |
