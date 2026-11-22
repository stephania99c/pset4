-- GOLD: hechos de gestiones. GRANO: una gestion de call center sobre un credito de auto.
-- Las gestiones duplicadas se cuentan una sola vez.
select
    gestion_id,
    numero_operacion,
    cliente_id,
    cobrador_id,
    fecha_gestion,
    accion,
    respuesta,
    gestion_resultado,
    gestion_resultado = 'EFECTIVO'     as hubo_contacto_efectivo,
    contacto,
    motivo_no_pago,
    fecha_compromiso,
    fecha_compromiso is not null       as tiene_compromiso
from {{ ref('slv_gestiones') }}
where es_auto and es_call_center and not es_posible_duplicado