-- SILVER: cartera con las reglas de negocio marcadas (no se borra nada).
select
    *,
    substr(numero_operacion, 10) = ''   as es_auto,
    tipo_pagare = 'PRINCIPAL'           as es_principal
from {{ ref('stg_cartera_diaria') }}
where numero_operacion is not null
  and fecha_corte is not null
qualify row_number() over (
    partition by numero_operacion, tipo_pagare, fecha_corte
    order by fecha_carga desc
) = 1