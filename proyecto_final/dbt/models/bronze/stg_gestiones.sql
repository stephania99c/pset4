-- BRONZE: gestiones de cobranza con tipos corregidos.
-- fecha_compromiso llega como texto con hora ("2026-10-05 00:00:00.000"): se toma solo la fecha.
select
    nullif(trim(numero_operacion), '')              as numero_operacion,
    nullif(trim(identificacion), '')                as cliente_id,
    try_to_date(fecha_gestion)                      as fecha_gestion,
    nullif(trim(usuario), '')                       as cobrador_id,
    upper(nullif(trim(accion), ''))                 as accion,
    upper(nullif(trim(respuesta), ''))              as respuesta,
    upper(nullif(trim(gestion_resultado), ''))      as gestion_resultado,
    upper(nullif(trim(contacto), ''))               as contacto,
    upper(nullif(trim(motivo_no_pago), ''))         as motivo_no_pago,
    try_to_date(left(fecha_compromiso, 10))         as fecha_compromiso
from {{ source('raw', 'gestiones') }}