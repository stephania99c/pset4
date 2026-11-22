# Diagramas

## Arquitectura

```mermaid
flowchart LR
    F[GitHub Release datos-v1<br/>CSV sintéticos] -->|Kestra diario 7:00| R[(RAW)]
    R -->|dbt| B[(BRONZE<br/>tipos y nombres)]
    B -->|dbt| S[(SILVER<br/>reglas marcadas)]
    S -->|dbt| G[(GOLD<br/>star schema)]
    G -->|Spark| O[(GOLD.OBT_CARTERA_DIARIA)]
```

## Star schema (Gold)

```mermaid
erDiagram
    DIM_OPERACION ||--o{ FCT_CARTERA_DIARIA : numero_operacion
    DIM_OPERACION ||--o{ FCT_PAGOS : numero_operacion
    DIM_OPERACION ||--o{ FCT_GESTIONES : numero_operacion
    DIM_CLIENTE ||--o{ FCT_CARTERA_DIARIA : cliente_id
    DIM_COBRADOR ||--o{ FCT_GESTIONES : cobrador_id
    DIM_FECHA ||--o{ FCT_CARTERA_DIARIA : fecha_corte
    DIM_FECHA ||--o{ FCT_PAGOS : fecha_pago
    DIM_FECHA ||--o{ FCT_GESTIONES : fecha_gestion
```

| Tabla | Grano |
|---|---|
| fct_cartera_diaria | una operación de auto (pagaré PRINCIPAL) por día de corte |
| fct_pagos | un pago aplicado de recaudación |
| fct_gestiones | una gestión de call center (sin duplicados) |
| dim_operacion | una operación de auto |
| dim_cliente | un cliente |
| dim_cobrador | un gestor de call center |
| dim_fecha | un día |

## OBT

```mermaid
flowchart LR
    C[fct_cartera_diaria<br/>define las filas] --> J{left join<br/>operación + día}
    P[fct_pagos<br/>agregado por día] --> J
    GE[fct_gestiones<br/>agregado por día] --> J
    DO[dim_operacion] --> J
    DF[dim_fecha] --> J
    J --> OBT[OBT_CARTERA_DIARIA<br/>261,255 filas]
```
