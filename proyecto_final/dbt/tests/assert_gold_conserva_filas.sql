-- Gold debe conservar exactamente las filas de Silver que cumplen los filtros de alcance:
-- ni mas (un join que duplica) ni menos (un filtro de mas). Si alguna tabla no cuadra, falla.
with conteos as (
    select 'fct_cartera_diaria' as tabla,
           (select count(*) from {{ ref('fct_cartera_diaria') }}) as filas_gold,
           (select count(*) from {{ ref('slv_cartera_diaria') }}
            where es_auto and es_principal) as filas_esperadas
    union all
    select 'fct_pagos',
           (select count(*) from {{ ref('fct_pagos') }}),
           (select count(*) from {{ ref('slv_pagos') }}
            where es_auto and es_aplicado and es_recaudacion)
    union all
    select 'fct_gestiones',
           (select count(*) from {{ ref('fct_gestiones') }}),
           (select count(*) from {{ ref('slv_gestiones') }}
            where es_auto and es_call_center and not es_posible_duplicado)
)

select * from conteos where filas_gold <> filas_esperadas