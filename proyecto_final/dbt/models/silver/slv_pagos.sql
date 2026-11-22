-- SILVER: pagos con reglas de negocio marcadas. No se elimina ningun pago.
--  * Los pagos identicos se conservan (pueden ser legitimos) y se marcan como posible duplicado.
--  * Se marcan los pagos aplicados y los de motivo RECAUDACION (los unicos que cuentan como recaudo).
with numerados as (
    select
        *,
        row_number() over (
            partition by numero_operacion, fecha_emision, fecha_pago, monto,
                         tipo_pago, estado, forma_pago, motivo
            order by fecha_pago
        ) as copia
    from {{ ref('stg_pagos') }}
    where numero_operacion is not null
      and monto > 0
)

select
    hash(numero_operacion, fecha_emision, fecha_pago, monto,
         tipo_pago, estado, forma_pago, motivo, copia)  as pago_id,
    id_operacion,
    numero_operacion,
    cliente_id,
    fecha_emision,
    fecha_pago,
    monto,
    tipo_pago,
    estado,
    forma_pago,
    motivo,
    copia > 1                           as es_posible_duplicado,
    estado = 'APLICADA'                 as es_aplicado,
    motivo = 'RECAUDACION'              as es_recaudacion,
    substr(numero_operacion, 10) = ''   as es_auto
from numerados