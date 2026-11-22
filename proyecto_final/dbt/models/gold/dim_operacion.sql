-- GOLD: dimension de operaciones de auto. Una fila por operacion.
-- Incluye las operaciones de auto de todas las tablas, para que todos los hechos tengan su operacion
-- (el 35% de los pagos son de operaciones que no estan en el historico).
with operaciones as (
    select numero_operacion from {{ ref('slv_cartera_diaria') }} where es_auto and es_principal
    union
    select numero_operacion from {{ ref('slv_pagos') }} where es_auto and es_aplicado and es_recaudacion
    union
    select numero_operacion from {{ ref('slv_gestiones') }} where es_auto and es_call_center
),

-- atributos del credito, tomados del ultimo corte disponible
ultimo_corte as (
    select *
    from {{ ref('slv_cartera_diaria') }}
    where es_auto and es_principal
    qualify row_number() over (partition by numero_operacion order by fecha_corte desc) = 1
),

-- cliente para las operaciones que no estan en la cartera
cliente_otras as (
    select numero_operacion, max(cliente_id) as cliente_id
    from (
        select numero_operacion, cliente_id from {{ ref('slv_pagos') }}
        union all
        select numero_operacion, cliente_id from {{ ref('slv_gestiones') }}
    )
    group by numero_operacion
)

select
    o.numero_operacion,
    coalesce(u.cliente_id, c.cliente_id)            as cliente_id,
    u.monto_financiado,
    u.tasa_nominal,
    u.total_cuotas,
    u.fecha_efectiva,
    u.fecha_primera_cuota,
    u.tipo_garantia,
    coalesce(h.estado_actual = 'CANCELADO', false)  as es_cancelada,
    u.numero_operacion is not null                  as tiene_cartera
from operaciones o
left join ultimo_corte u on o.numero_operacion = u.numero_operacion
left join cliente_otras c on o.numero_operacion = c.numero_operacion
left join {{ ref('slv_operaciones') }} h on o.numero_operacion = h.numero_operacion