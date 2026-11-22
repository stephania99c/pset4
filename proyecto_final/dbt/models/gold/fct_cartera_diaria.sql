-- GOLD: hechos de la cartera. GRANO: una operacion de auto en un dia de corte.
select
    hash(numero_operacion, fecha_corte)   as cartera_diaria_id,
    numero_operacion,
    cliente_id,
    fecha_corte,
    estado_operacion,
    dias_mora,
    rango_mora,
    cuotas_por_pagar,
    cuotas_pagadas,
    cuotas_mora,
    dia_pago,
    capital_insoluto,
    capital_vencido,
    saldo_cuota_mas_vencida,
    valor_deuda_exigible,
    valor_cuota_exigible_vigente,
    fecha_proxima_cuota,
    fecha_primera_cuota_mora
from {{ ref('slv_cartera_diaria') }}
where es_auto and es_principal