-- SILVER: gestiones con reglas de negocio marcadas. No se elimina ninguna gestion.
--  * Las gestiones identicas se marcan como posible duplicado (en Gold se cuentan una sola vez).
--  * Se marcan las acciones que no son de call center.
--  * contacto vacio se reemplaza por 'NO REGISTRADO'.
with numeradas as (
    select
        *,
        row_number() over (
            partition by numero_operacion, cliente_id, fecha_gestion, cobrador_id, accion,
                         respuesta, gestion_resultado, contacto, motivo_no_pago, fecha_compromiso
            order by fecha_gestion
        ) as copia
    from {{ ref('stg_gestiones') }}
    where numero_operacion is not null
      and fecha_gestion is not null
)

select
    hash(numero_operacion, cliente_id, fecha_gestion, cobrador_id, accion, respuesta,
         gestion_resultado, contacto, motivo_no_pago, fecha_compromiso, copia)   as gestion_id,
    numero_operacion,
    cliente_id,
    fecha_gestion,
    cobrador_id,
    accion,
    respuesta,
    gestion_resultado,
    coalesce(contacto, 'NO REGISTRADO')     as contacto,
    motivo_no_pago,
    fecha_compromiso,
    copia > 1                                as es_posible_duplicado,
    coalesce(accion, '') not in ('BLOQUEO DISPOSITIVO', 'VISITA TERRENO')   as es_call_center,
    substr(numero_operacion, 10) = ''        as es_auto
from numeradas