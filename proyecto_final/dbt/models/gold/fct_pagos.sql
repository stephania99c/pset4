-- GOLD: hechos de pagos. GRANO: un pago de recaudacion aplicado a un credito de auto.
select
    pago_id,
    numero_operacion,
    cliente_id,
    fecha_pago,
    fecha_emision,
    monto,
    tipo_pago,
    forma_pago,
    es_posible_duplicado
from {{ ref('slv_pagos') }}
where es_auto and es_aplicado and es_recaudacion