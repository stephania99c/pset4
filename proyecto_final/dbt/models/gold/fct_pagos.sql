-- GOLD: hechos de pagos. GRANO: un pago de recaudacion aplicado a un credito de auto.
-- en_obt = false marca los pagos que no caen en un dia de cartera de su operacion
-- (pagos de septiembre o de operaciones canceladas): siguen aqui, pero no entran a la OBT.
with dias_cartera as (
    select distinct numero_operacion, fecha_corte
    from {{ ref('slv_cartera_diaria') }}
    where es_auto and es_principal
)

select
    p.pago_id,
    p.numero_operacion,
    p.cliente_id,
    p.fecha_pago,
    p.fecha_emision,
    p.monto,
    p.tipo_pago,
    p.forma_pago,
    p.es_posible_duplicado,
    d.numero_operacion is not null   as en_obt
from {{ ref('slv_pagos') }} p
left join dias_cartera d
    on p.numero_operacion = d.numero_operacion and p.fecha_pago = d.fecha_corte
where p.es_auto and p.es_aplicado and p.es_recaudacion