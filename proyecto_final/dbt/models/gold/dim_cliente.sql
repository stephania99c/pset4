-- GOLD: dimension de clientes. Una fila por cliente con creditos de auto.
with clientes as (
    select cliente_id from {{ ref('slv_cartera_diaria') }} where es_auto and es_principal
    union
    select cliente_id from {{ ref('slv_pagos') }} where es_auto and es_aplicado and es_recaudacion
    union
    select cliente_id from {{ ref('slv_gestiones') }} where es_auto and es_call_center
)

select
    c.cliente_id,
    count(o.numero_operacion)   as num_creditos_auto
from clientes c
left join {{ ref('dim_operacion') }} o on c.cliente_id = o.cliente_id
where c.cliente_id is not null
group by c.cliente_id