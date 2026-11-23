-- GOLD: dimension de clientes. Una fila por cliente con creditos de auto.
-- Atributos que sirven para priorizar la gestion: cuantos creditos de auto tiene,
-- cuanto se le financio en total y si tiene algun credito en mora en su ultimo corte.
with clientes as (
    select cliente_id from {{ ref('slv_cartera_diaria') }} where es_auto and es_principal
    union
    select cliente_id from {{ ref('slv_pagos') }} where es_auto and es_aplicado and es_recaudacion
    union
    select cliente_id from {{ ref('slv_gestiones') }} where es_auto and es_call_center
),

ultimo_corte as (
    select numero_operacion, dias_mora
    from {{ ref('fct_cartera_diaria') }}
    qualify row_number() over (partition by numero_operacion order by fecha_corte desc) = 1
)

select
    c.cliente_id,
    count(distinct o.numero_operacion)       as num_creditos_auto,
    sum(o.monto_financiado)                  as monto_financiado_total,
    coalesce(max(u.dias_mora) > 0, false)    as tiene_credito_en_mora
from clientes c
left join {{ ref('dim_operacion') }} o on c.cliente_id = o.cliente_id
left join ultimo_corte u on o.numero_operacion = u.numero_operacion
where c.cliente_id is not null
group by c.cliente_id